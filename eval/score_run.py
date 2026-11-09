#!/usr/bin/env python3
"""
Score one deepdive run across the 6-axis rubric (see eval/rubric.md).

Splits work the way the rubric does:
  - deterministic axes (citation integrity, quote integrity, number integrity,
    source diversity, cost proxy) → here
  - semantic axes (factual accuracy, coverage, adversarial honesty, readout
    clarity) → LLM-judge,
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
import random
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from check_numbers import check as check_numbers  # noqa: E402
from check_quotes import check as check_quotes  # noqa: E402

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
    cfg = {
        k.strip(): float(v)
        for k, v in re.findall(r"^([\w.]+)\s*=\s*([\d.]+)", block, re.MULTILINE)
    }
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
        [
            sys.executable,
            str(EVAL_DIR / "check_citations.py"),
            "--research-dir",
            str(research_dir),
            "--out",
            str(out_base),
            "--json",
        ],
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
    key = (
        "type"
        if rows[0].get("type")
        else ("channel" if rows[0].get("channel") else None)
    )
    if not key:
        return None, "no type/channel column — diversity unscorable"
    kinds = {
        (r.get(key) or "").strip().lower() for r in rows if (r.get(key) or "").strip()
    }
    distinct = len(kinds)

    used_col = "used" in rows[0]
    if used_col:
        used_ratio = sum(
            (r.get("used") or "").strip().upper() == "Y" for r in rows
        ) / len(rows)
    else:
        used_ratio = 1.0  # old schema doesn't track it; don't penalise

    diversity = 0.7 * min(distinct, 4) / 4 + 0.3 * used_ratio
    return diversity, f"{distinct} distinct {key}s, used_ratio={used_ratio:.2f}"


def token_proxy(research_dir: Path) -> int:
    report = find_report(research_dir)
    total_chars = len(report.read_text(encoding="utf-8")) if report else 0
    sources_dir = research_dir / "sources"
    if sources_dir.is_dir():
        total_chars += sum(
            len(p.read_text(encoding="utf-8")) for p in sources_dir.glob("*.md")
        )
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


SAMPLE_SIZE = 8
QUOTE_BUDGET = 1500  # chars of quotes per source, keeps deep runs inside the judge's context


def sample_claims(claim_lines: list[str], run_id: str) -> list[str]:
    # The first N lines are always the TL;DR, so the judge never saw the body.
    # Seeding by run_id keeps a re-render of the same run identical.
    if len(claim_lines) <= SAMPLE_SIZE:
        return claim_lines
    picked = sorted(random.Random(run_id).sample(range(len(claim_lines)), SAMPLE_SIZE))
    return [claim_lines[i] for i in picked]


QUOTE_SECTION_RE = re.compile(r"^#+\s.*(quote|цитат|числа)", re.IGNORECASE)


def source_quotes(research_dir: Path) -> dict[str, list[str]]:
    """sid -> blockquote lines plus every line of the quotes section of sources/*.md.

    Fetchers often keep a verbatim fragment inside a prose line of that section
    ('Выигрыш: "3-5 times faster" на ...'); reading only '>' lines hid it from the
    judge and sqlite-B/C theses were marked unsupported (2026-11-07).
    """
    out: dict[str, list[str]] = {}
    for p in sorted((research_dir / "sources").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        sid = re.search(r"^id:\s*(s\d+)", text, re.MULTILINE)
        key = sid.group(1) if sid else p.stem.split("_")[0]
        body = text.split("\n---\n", 1)[1] if text.startswith("---\n") else text
        lines, in_section = [], False
        for ln in body.splitlines():
            if ln.startswith("#"):
                in_section = bool(QUOTE_SECTION_RE.match(ln))
                continue
            if ln.startswith(">") or (in_section and ln.strip()):
                lines.append(ln.lstrip(">-* ").strip())
        out[key] = [ln for ln in dict.fromkeys(lines) if ln]
    return out


def render_sampled_claims(claims: list[str], quotes: dict[str, list[str]]) -> str:
    # Without the quotes the judge can only check internal consistency and, by its
    # own rule, scores factual_accuracy down for unverifiability (N4-N6 stuck at 3).
    blocks = []
    for claim in claims:
        lines = [f"- {claim.lstrip('-* ')}"]
        for sid in dict.fromkeys(re.findall(r"\b(s\d{2,3})\b", claim)):
            if sid not in quotes:
                lines.append(f"  - [{sid}] source file not found")
                continue
            if not quotes[sid]:
                lines.append(f"  - [{sid}] source file has no verbatim quotes")
                continue
            lines.append(f"  - [{sid}] quotes and notes from the source file:")
            used = 0
            for q in quotes[sid]:
                if used + len(q) > QUOTE_BUDGET:
                    lines.append("    > … (truncated)")
                    break
                lines.append(f"    > {q}")
                used += len(q)
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


def render_judge_input(research_dir: Path, run_id: str) -> Path:
    report = find_report(research_dir)
    report_text = report.read_text(encoding="utf-8") if report else "(no report found)"
    plan = research_dir / "plan.md"
    hypotheses = ""
    if plan.is_file():
        ptext = plan.read_text(encoding="utf-8")
        hyp_lines = [
            ln
            for ln in ptext.splitlines()
            if re.search(r"\bH\d\b|hypothes", ln, re.IGNORECASE)
        ]
        hypotheses = "\n".join(hyp_lines) or "(no hypotheses found in plan.md)"

    claim_lines = [
        ln.strip()
        for ln in report_text.splitlines()
        if re.search(r"\bs\d{2}\b|\[\d+\]|https?://", ln) and len(ln.strip()) > 40
    ]
    sampled = (
        render_sampled_claims(
            sample_claims(claim_lines, run_id), source_quotes(research_dir)
        )
        or "(no source-linked theses auto-found; judge picks 3-5)"
    )

    template = JUDGE_TEMPLATE.read_text(encoding="utf-8")
    # Use only the prompt body (after the first '---' separator) as the runnable prompt.
    body = template.split("\n---\n", 1)[1] if "\n---\n" in template else template
    filled = (
        body.replace("{{QUESTION}}", _question_from_plan(research_dir))
        .replace("{{HYPOTHESES}}", hypotheses)
        .replace("{{REPORT}}", report_text)
        .replace("{{READOUT}}", _readout(research_dir))
        .replace("{{SAMPLED_CLAIMS}}", sampled)
    )
    out = OUTPUT_DIR / f"{run_id}_judge_input.md"
    out.write_text(filled, encoding="utf-8")
    return out


def _readout(research_dir: Path) -> str:
    path = research_dir / "readout.md"
    return path.read_text(encoding="utf-8") if path.is_file() else "(no readout.md)"


QUESTION_HEADING_RE = re.compile(r"^#+\s.*\b(вопрос|question)", re.IGNORECASE)
PLAN_TITLE_RE = re.compile(r"^#\s+(?:plan|план)\s*[—:-]\s*", re.IGNORECASE)


def _question_from_plan(research_dir: Path) -> str:
    """`question:` field (frontmatter or body) → first line of a «вопрос/question» section → plan title.

    The old version returned the first plain line, which on every bench run was a
    frontmatter field: judges were asked about «mode: medium» (found 2026-11-07).
    """
    plan = research_dir / "plan.md"
    if not plan.is_file():
        return "(question not found — see plan.md)"
    text = plan.read_text(encoding="utf-8")
    q = re.search(r"^question:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    if q:
        return q.group(1).strip().strip("\"'")
    front = re.match(r"\A---\n.*?\n---\n", text, re.DOTALL)
    lines = text[front.end() if front else 0:].splitlines()
    for i, ln in enumerate(lines):
        if QUESTION_HEADING_RE.match(ln):
            for nxt in lines[i + 1:]:
                if nxt.startswith("#"):
                    break
                if nxt.strip():
                    return nxt.strip().lstrip(">-* ").strip("*").strip()
    for ln in lines:
        if ln.startswith("# "):
            return PLAN_TITLE_RE.sub("", ln).lstrip("# ").strip()
    return "(question not found — see plan.md)"


JUDGE_AXES = ("factual_accuracy", "coverage_depth", "adversarial_honesty", "readout_clarity")
# Must match the check ids in judge_prompt.md (pinned by tests/test_judge_checks.py).
CHECKS = {
    "coverage_depth": ("C1", "C2", "C3", "C4"),
    "adversarial_honesty": ("A1", "A2", "A3", "A4", "A5"),
    "readout_clarity": ("R1", "R2", "R3", "R4", "R5", "R6", "R7"),
}
VERDICTS = {"supported", "unsupported", "unverifiable"}


def judge_axes(judge: dict) -> dict[str, tuple[float | None, str]]:
    """Axis -> (score in 0..1 or None for n/a, label for the scorecard)."""
    if "theses" not in judge:
        # 0-5 judges from before 2026-11-07; readout_clarity was added later still.
        out = {a: (judge[a] / 5, f"{judge[a]}/5") for a in JUDGE_AXES[:3]}
        rc = judge.get("readout_clarity")
        out["readout_clarity"] = (None, "n/a") if rc is None else (rc / 5, f"{rc}/5")
        return out

    verdicts = [t.get("verdict") for t in judge["theses"]]
    if not verdicts or not set(verdicts) <= VERDICTS:
        raise ValueError(f"theses: need verdicts from {sorted(VERDICTS)}, got {verdicts}")
    ok = verdicts.count("supported")
    out = {"factual_accuracy": (ok / len(verdicts), f"{ok}/{len(verdicts)} theses supported")}
    for axis, ids in CHECKS.items():
        block = judge.get(axis)
        if block is None and axis == "readout_clarity":
            out[axis] = (None, "n/a")
            continue
        if not isinstance(block, dict) or set(block) != set(ids):
            raise ValueError(f"{axis}: expected checks {list(ids)}, got {sorted(block or {})}")
        if not all(isinstance(block[i].get("pass"), bool) for i in ids):
            raise ValueError(f"{axis}: every check needs a boolean 'pass'")
        failed = [i for i in ids if not block[i]["pass"]]
        passed = len(ids) - len(failed)
        label = f"{passed}/{len(ids)} checks" + (f", failed {' '.join(failed)}" if failed else "")
        out[axis] = (passed / len(ids), label)
    return out


def build_scorecard(
    run_id: str,
    research_dir: Path,
    w: dict,
    cite: dict,
    diversity,
    div_note: str,
    tokens: int,
    real_cost: float | None,
    judge: dict | None,
    quotes: dict | None = None,
    numbers: dict | None = None,
) -> tuple[str, dict]:
    citation = cite["citation_integrity"]
    floor, penalty = w["citation_floor"], w["citation_penalty"]

    # Normalise axes into 0..1. cost_proxy: smaller is better, but its only role is a
    # mild bloat penalty — we map it relative to a soft 30k-token reference.
    cost_norm = max(0.0, 1.0 - tokens / 30000)
    div_norm = diversity if diversity is not None else 0.0
    quote = (quotes or {}).get("quote_integrity")
    quote_note = (
        f"checked {quotes['checked']}, missing {quotes['missing']}, "
        f"wrong_source {quotes['wrong_source']}"
        if quote is not None
        else "n/a — no verbatim quotes with [sNN]"
    )
    number = (numbers or {}).get("number_integrity")
    number_note = (
        f"checked {numbers['checked']}, missing {numbers['missing']}"
        if number is not None
        else "n/a — no numbers in sentences with [sNN]"
    )

    lines = [
        f"# Scorecard — run `{run_id}`",
        "",
        f"Run dir: `{research_dir}`",
        "",
        "## Deterministic axes",
        "",
        f"- **Citation integrity:** {citation:.3f}  (weight {w['weight.citation_integrity']:.2f})",
        f"- **Quote integrity:** {'n/a' if quote is None else format(quote, '.3f')}  ({quote_note})  (weight {w['weight.quote_integrity']:.2f})",
        f"- **Number integrity:** {'n/a' if number is None else format(number, '.3f')}  ({number_note})  (weight {w['weight.number_integrity']:.2f})",
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
            lines += [
                "",
                f"⚠ Citation integrity {citation:.3f} — "
                + (
                    "**below floor**, final score will be halved."
                    if citation < floor
                    else "above floor."
                ),
            ]
        return "\n".join(lines), {
            "run_id": run_id,
            "citation": citation,
            "diversity": diversity,
            "quote_integrity": quote,
            "number_integrity": number,
            "quality": None,
            "qpd": None,
            "judge": "pending",
        }

    sem = judge_axes(judge)
    (fa, _), (cov, _), (adv, _), (rc, _) = (sem[a] for a in JUDGE_AXES)
    titles = ("Factual accuracy", "Coverage / depth", "Adversarial honesty", "Readout clarity")
    for title, axis in zip(titles, JUDGE_AXES):
        norm, label = sem[axis]
        shown = "n/a" if norm is None else f"{label} → {norm:.2f}"
        lines.append(f"- **{title}:** {shown}  (weight {w['weight.' + axis]:.2f})")

    axes = {
        "citation_integrity": citation,
        "quote_integrity": quote,
        "number_integrity": number,
        "source_diversity": div_norm,
        "factual_accuracy": fa,
        "coverage_depth": cov,
        "adversarial_honesty": adv,
        "readout_clarity": rc,
        "cost_proxy": cost_norm,
    }
    scored = {k: v for k, v in axes.items() if v is not None}
    quality_raw = sum(v * w[f"weight.{k}"] for k, v in scored.items()) / sum(
        w[f"weight.{k}"] for k in scored
    )
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
        lines += [
            f"- **quality_per_dollar = {quality / real_cost:.3f}**  (↑ = better value)"
        ]
    else:
        lines += ["- quality_per_dollar: set `real_cost_usd` in runs.csv to compute"]
    if judge.get("notes", {}).get("biggest_weakness"):
        lines += [
            "",
            f"> Judge — biggest weakness: {judge['notes']['biggest_weakness']}",
        ]
    return "\n".join(lines), {
        "run_id": run_id,
        "citation": citation,
        "diversity": diversity,
        "quote_integrity": quote,
        "number_integrity": number,
        "readout_clarity": rc,
        "quality": quality,
        "qpd": quality / real_cost if real_cost else None,
        "judge": "scored",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--judge-json", type=Path, help="JSON returned by the LLM-judge"
    )
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

    card, metrics = build_scorecard(
        args.run_id,
        args.research_dir,
        w,
        cite,
        diversity,
        div_note,
        tokens,
        real_cost,
        judge,
        check_quotes(args.research_dir),
        check_numbers(args.research_dir),
    )
    card_path = OUTPUT_DIR / f"{args.run_id}_scorecard.md"
    card_path.write_text(card, encoding="utf-8")
    # Машина читает sidecar, человек — markdown. Без него aggregate.py парсил бы
    # цифры регуляркой и при смене формата молча показывал прочерк.
    metrics_path = OUTPUT_DIR / f"{args.run_id}_scorecard.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Scorecard: {card_path}  (+ {metrics_path.name})")
    print()
    print(card)
    return 0


if __name__ == "__main__":
    sys.exit(main())
