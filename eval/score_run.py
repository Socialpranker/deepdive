#!/usr/bin/env python3
"""
Score one deepdive run across the 6-axis rubric (see eval/rubric.md).

Splits work the way the rubric does:
  - deterministic axes (citation integrity, source diversity, cost proxy) → here
  - semantic axes (factual accuracy, coverage, adversarial honesty) → LLM-judge,
    via a rendered prompt the user runs through Opus and pastes back

Without the judge JSON it prints a partial scorecard (deterministic axes only).
With --judge-json <file> it folds in the semantic scores and computes the final
weighted quality_score (+ quality-per-dollar if real_cost is in runs.csv).

Usage:
    # 1. deterministic pass + render judge input
    python eval/score_run.py --research-dir research/<slug> --run-id A
    # 2. run output/A_judge_input.md through Opus, save its JSON to output/A_judge.json
    # 3. final scorecard
    python eval/score_run.py --research-dir research/<slug> --run-id A --judge-json eval/output/A_judge.json
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).parent
OUTPUT_DIR = EVAL_DIR / "output"
RUBRIC = EVAL_DIR / "rubric.md"
JUDGE_TEMPLATE = EVAL_DIR / "judge_prompt.md"
RUNS_CSV = EVAL_DIR / "runs" / "runs.csv"

CHARS_PER_TOKEN = 4  # rough token proxy; only used to compare runs on the same question


def load_weights() -> dict[str, float]:
    """Parse the ini block between SCORE_CONFIG markers in rubric.md."""
    text = RUBRIC.read_text(encoding="utf-8")
    block = text.split("SCORE_CONFIG_START", 1)[1].split("SCORE_CONFIG_END", 1)[0]
    cfg = {k.strip(): float(v) for k, v in re.findall(r"^([\w.]+)\s*=\s*([\d.]+)", block, re.MULTILINE)}
    return cfg


def find_report(research_dir: Path) -> Path | None:
    """The final report is <date>_<genre>.md at the run root (not plan.md, not sources)."""
    candidates = [p for p in research_dir.glob("*.md") if p.name != "plan.md"]
    dated = [p for p in candidates if re.match(r"\d{4}-\d{2}-\d{2}_", p.name)]
    if dated:
        return max(dated, key=lambda p: p.name)
    return candidates[0] if candidates else None


def run_citation_check(research_dir: Path, run_id: str) -> dict:
    """Invoke check_citations.py as a subprocess, return its JSON."""
    out_base = OUTPUT_DIR / f"{run_id}_citations"
    subprocess.run(
        [sys.executable, str(EVAL_DIR / "check_citations.py"),
         "--research-dir", str(research_dir), "--out", str(out_base), "--json"],
        check=True,
    )
    return json.loads(out_base.with_suffix(".json").read_text(encoding="utf-8"))


def source_diversity(research_dir: Path) -> tuple[float | None, str]:
    """0..1 from sources.csv. Returns (score, explanation). None when no type/channel data."""
    csv_path = research_dir / "sources.csv"
    if not csv_path.is_file():
        return None, "no sources.csv"
    with csv_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return None, "empty sources.csv"

    # Prefer explicit `type`; fall back to `channel` (older schema has channel, no type).
    key = "type" if rows[0].get("type") else ("channel" if rows[0].get("channel") else None)
    if not key:
        return None, "no type/channel column — diversity unscorable"
    kinds = {(r.get(key) or "").strip().lower() for r in rows if (r.get(key) or "").strip()}
    distinct = len(kinds)

    used_col = "used" in rows[0]
    if used_col:
        used_ratio = sum((r.get("used") or "").strip().upper() == "Y" for r in rows) / len(rows)
    else:
        used_ratio = 1.0  # old schema doesn't track it; don't penalise

    diversity = 0.7 * min(distinct, 4) / 4 + 0.3 * used_ratio
    return diversity, f"{distinct} distinct {key}s, used_ratio={used_ratio:.2f}"


def token_proxy(research_dir: Path) -> int:
    report = find_report(research_dir)
    total_chars = len(report.read_text(encoding="utf-8")) if report else 0
    sources_dir = research_dir / "sources"
    if sources_dir.is_dir():
        total_chars += sum(len(p.read_text(encoding="utf-8")) for p in sources_dir.glob("*.md"))
    csv_path = research_dir / "sources.csv"
    if csv_path.is_file():
        total_chars += len(csv_path.read_text(encoding="utf-8"))
    return total_chars // CHARS_PER_TOKEN


def read_real_cost(run_id: str) -> float | None:
    if not RUNS_CSV.is_file():
        return None
    with RUNS_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("run_id") == run_id:
                raw = (row.get("real_cost_usd") or "").strip()
                return float(raw) if raw else None
    return None


def render_judge_input(research_dir: Path, run_id: str) -> Path:
    report = find_report(research_dir)
    report_text = report.read_text(encoding="utf-8") if report else "(no report found)"
    plan = research_dir / "plan.md"
    hypotheses = ""
    if plan.is_file():
        ptext = plan.read_text(encoding="utf-8")
        hyp_lines = [ln for ln in ptext.splitlines() if re.search(r"\bH\d\b|hypothes", ln, re.IGNORECASE)]
        hypotheses = "\n".join(hyp_lines) or "(no hypotheses found in plan.md)"

    # Sample theses: report lines that reference a source (sNN / [N] / a URL).
    claim_lines = [ln.strip() for ln in report_text.splitlines()
                   if re.search(r"\bs\d{2}\b|\[\d+\]|https?://", ln) and len(ln.strip()) > 40]
    sampled = "\n".join(f"- {ln}" for ln in claim_lines[:8]) or "(no source-linked theses auto-found; judge picks 3-5)"

    template = JUDGE_TEMPLATE.read_text(encoding="utf-8")
    # Use only the prompt body (after the first '---' separator) as the runnable prompt.
    body = template.split("\n---\n", 1)[1] if "\n---\n" in template else template
    filled = (body
              .replace("{{QUESTION}}", _question_from_plan(research_dir))
              .replace("{{HYPOTHESES}}", hypotheses)
              .replace("{{REPORT}}", report_text)
              .replace("{{SAMPLED_CLAIMS}}", sampled))
    out = OUTPUT_DIR / f"{run_id}_judge_input.md"
    out.write_text(filled, encoding="utf-8")
    return out


def _question_from_plan(research_dir: Path) -> str:
    plan = research_dir / "plan.md"
    if plan.is_file():
        for ln in plan.read_text(encoding="utf-8").splitlines():
            if ln.strip() and not ln.startswith(("#", "-", "*", "|")):
                return ln.strip()
    return "(question not found — see plan.md)"


def build_scorecard(run_id: str, research_dir: Path, w: dict, cite: dict, diversity, div_note: str,
                    tokens: int, real_cost: float | None, judge: dict | None) -> str:
    citation = cite["citation_integrity"]
    floor, penalty = w["citation_floor"], w["citation_penalty"]

    # Normalise axes into 0..1. cost_proxy: smaller is better, but its only role is a
    # mild bloat penalty — we map it relative to a soft 30k-token reference.
    cost_norm = max(0.0, 1.0 - tokens / 30000)
    div_norm = diversity if diversity is not None else 0.0

    lines = [
        f"# Scorecard — run `{run_id}`",
        "",
        f"Run dir: `{research_dir}`",
        "",
        "## Deterministic axes",
        "",
        f"- **Citation integrity:** {citation:.3f}  (weight {w['weight.citation_integrity']:.2f})",
        f"- **Source diversity:** {'n/a — ' + div_note if diversity is None else f'{diversity:.3f}  ({div_note})'}  (weight {w['weight.source_diversity']:.2f})",
        f"- **Cost proxy:** ~{tokens} tokens (artifacts), norm {cost_norm:.2f}  (weight {w['weight.cost_proxy']:.2f})",
        f"- **Real cost:** {'$' + format(real_cost, '.2f') if real_cost is not None else 'not set in runs.csv'}",
        "",
        "## Semantic axes (LLM-judge)",
        "",
    ]

    if judge is None:
        lines += [
            "_Pending._ Run the rendered judge input through Opus, then re-run with",
            f"`--judge-json eval/output/{run_id}_judge.json`.",
            "",
            f"Judge input: `eval/output/{run_id}_judge_input.md`",
        ]
        if diversity is None:
            lines += ["", f"⚠ Citation integrity {citation:.3f} — " +
                      ("**below floor**, final score will be halved." if citation < floor else "above floor.")]
        return "\n".join(lines)

    fa, cov, adv = judge["factual_accuracy"] / 5, judge["coverage_depth"] / 5, judge["adversarial_honesty"] / 5
    lines += [
        f"- **Factual accuracy:** {judge['factual_accuracy']}/5 → {fa:.2f}  (weight {w['weight.factual_accuracy']:.2f})",
        f"- **Coverage / depth:** {judge['coverage_depth']}/5 → {cov:.2f}  (weight {w['weight.coverage_depth']:.2f})",
        f"- **Adversarial honesty:** {judge['adversarial_honesty']}/5 → {adv:.2f}  (weight {w['weight.adversarial_honesty']:.2f})",
    ]

    quality_raw = (citation * w["weight.citation_integrity"]
                   + div_norm * w["weight.source_diversity"]
                   + fa * w["weight.factual_accuracy"]
                   + cov * w["weight.coverage_depth"]
                   + adv * w["weight.adversarial_honesty"]
                   + cost_norm * w["weight.cost_proxy"])
    floored = citation < floor
    quality = quality_raw * (penalty if floored else 1.0)

    lines += [
        "",
        "## Verdict",
        "",
        f"- quality_raw = {quality_raw:.3f}",
        f"- citation floor ({floor:.2f}): {'**TRIGGERED** → ×' + format(penalty, '.2f') if floored else 'ok'}",
        f"- **quality_score = {quality:.3f}**",
    ]
    if real_cost:
        lines += [f"- **quality_per_dollar = {quality / real_cost:.3f}**  (↑ = better value)"]
    else:
        lines += ["- quality_per_dollar: set `real_cost_usd` in runs.csv to compute"]
    if judge.get("notes", {}).get("biggest_weakness"):
        lines += ["", f"> Judge — biggest weakness: {judge['notes']['biggest_weakness']}"]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--judge-json", type=Path, help="JSON returned by the LLM-judge")
    args = parser.parse_args()

    if not args.research_dir.is_dir():
        print(f"ERROR: not a directory: {args.research_dir}")
        return 2
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    w = load_weights()
    cite = run_citation_check(args.research_dir, args.run_id)
    diversity, div_note = source_diversity(args.research_dir)
    tokens = token_proxy(args.research_dir)
    real_cost = read_real_cost(args.run_id)

    judge = None
    if args.judge_json:
        judge = json.loads(args.judge_json.read_text(encoding="utf-8"))
    else:
        ji = render_judge_input(args.research_dir, args.run_id)
        print(f"Judge input rendered: {ji}")

    card = build_scorecard(args.run_id, args.research_dir, w, cite, diversity, div_note, tokens, real_cost, judge)
    card_path = OUTPUT_DIR / f"{args.run_id}_scorecard.md"
    card_path.write_text(card, encoding="utf-8")
    print(f"Scorecard: {card_path}")
    print()
    print(card)
    return 0


if __name__ == "__main__":
    sys.exit(main())
