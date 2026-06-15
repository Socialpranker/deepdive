#!/usr/bin/env python3
"""
Model-agnostic deep-research orchestrator (SCAFFOLD).

Owns the two Claude-specific responsibilities so the methodology doesn't have to:
  - sub-agent fan-out  (delegated to provider.fanout)
  - source-file I/O     (this module writes sources/NN.md, plan.md, the report)

Phases call the provider through the LLMProvider interface only. Swap the model by
swapping the provider — no phase logic changes. With the DryRunProvider this runs
end-to-end and produces a run directory that validates clean against
eval/validate_structure.py.

Real web search, retrieval, and per-phase prompt assembly from references/* are TODO.
This proves the shape, not the product.

Usage:
    python runner/orchestrator.py "your question" --depth medium --provider dryrun --out research
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    from .providers import LLMProvider, build_provider
except ImportError:  # run as a script
    from providers import LLMProvider, build_provider

try:
    from .adaptive import run_search_loop, write_deviations
except ImportError:  # run as a script
    from adaptive import run_search_loop, write_deviations

try:
    from .scoring import compute_total, triangulate, render_triangulation
except ImportError:  # run as a script
    from scoring import compute_total, triangulate, render_triangulation

try:
    from .capabilities import audit_env, render_capabilities
except ImportError:  # run as a script
    from capabilities import audit_env, render_capabilities

try:
    from .verify import PLACEHOLDER, render_verification
except ImportError:  # run as a script
    from verify import PLACEHOLDER, render_verification

DEPTH_SOURCES = {"shallow": 6, "medium": 14, "deep": 28}
DEPTH_FANOUT = {"shallow": 0, "medium": 3, "deep": 5}
GENRE_BY_HINT = [
    (r"\bvs\b|or |trade-?off|choose|should i", "decision"),
    (r"how does|how do|under the hood|work", "explainer"),
    (r"is it true|is the claim|validate|really", "validation"),
    (r"who('?s| is)|landscape|players|market map", "landscape"),
]


def slugify(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")[:60] or "research"


def pick_genre(question: str) -> str:
    for pat, genre in GENRE_BY_HINT:
        if re.search(pat, question, re.IGNORECASE):
            return genre
    return "qa"


@dataclass
class RunState:
    question: str
    depth: str
    root: Path
    slug: str = ""
    genre: str = ""
    hypotheses: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    deviations: list = field(default_factory=list)
    round_source_ids: dict = field(default_factory=dict)  # round_index -> [source_id]
    triangulation: list = field(default_factory=list)     # Phase 5 output
    capabilities: list = field(default_factory=list)      # Phase 3.5: env-key audit

    @property
    def dir(self) -> Path:
        return self.root / self.slug


class Orchestrator:
    def __init__(self, provider: LLMProvider, *, verify_live: bool = False):
        self.p = provider
        self.verify_live = verify_live

    # --- Phase 1: reframing ------------------------------------------------
    def reframe(self, s: RunState) -> None:
        s.slug = slugify(s.question)
        out = self.p.complete(f"Reframe and form 2-4 falsifiable hypotheses:\n{s.question}",
                              model_tier="strong")
        # scaffold: synthesize placeholder hypotheses
        s.hypotheses = [f"H{i}: hypothesis about '{s.question[:40]}' [{out[:0]}]" for i in (1, 2, 3)]

    # --- Phase 2: genre ----------------------------------------------------
    def choose_genre(self, s: RunState) -> None:
        s.genre = pick_genre(s.question)

    # --- Phase 3: plan -----------------------------------------------------
    def plan(self, s: RunState) -> None:
        s.dir.mkdir(parents=True, exist_ok=True)
        body = [
            f"# Plan — {s.slug}",
            "",
            s.question,
            "",
            f"depth: {s.depth}",
            f"genre: {s.genre}",
            "",
            "## Hypotheses",
            *[f"- {h}" for h in s.hypotheses],
            "",
            "## Sourcing strategy",
            "- (TODO: channels + stat/api sources per subtopic from references/)",
        ]
        (s.dir / "plan.md").write_text("\n".join(body), encoding="utf-8")

    # --- Phase 3.5: capability discovery -----------------------------------
    def discover_capabilities(self, s: RunState) -> None:
        s.capabilities = audit_env(dict(os.environ))
        available = [a["key"] for a in s.capabilities if a["present"]]
        prompt = (
            "Map the research subtopics to information sources, given the available "
            "API keys. For any source whose key is missing, note the fallback.\n\n"
            f"Question: {s.question}\n"
            f"Hypotheses:\n" + "\n".join(f"- {h}" for h in s.hypotheses) + "\n\n"
            f"Available API keys: {', '.join(available) or '(none)'}\n"
        )
        mapping = self.p.complete(prompt, model_tier="mid")
        block = render_capabilities(s.capabilities, mapping)
        plan_path = s.dir / "plan.md"
        existing = plan_path.read_text(encoding="utf-8")
        plan_path.write_text(existing + block, encoding="utf-8")

    # --- Phase 4: search (fan-out) ----------------------------------------
    def search(self, s: RunState) -> None:
        n = DEPTH_SOURCES[s.depth]
        k = DEPTH_FANOUT[s.depth]
        collected: list[dict] = []

        def run_round(round_index, _round_depth, directives):
            blobs = [
                self.p.search(f"[r{round_index}] subtopic {i} for: {s.question}",
                              subquestion_id=f"Q{i}", model_tier="cheap")
                for i in range(max(1, k))
            ]
            for b in blobs:
                b["_round"] = round_index
            collected.extend(blobs)
            return blobs

        deviations, _rounds = run_search_loop(self.p, s.depth, run_round)
        s.deviations = deviations
        write_deviations(s.dir, s.slug, deviations)

        # sources from collected blobs: dedup by url, keep the first n unique.
        # `written` (not the scan index) is the cap gate, so early duplicates don't
        # burn slots and under-fill below n. NOTE (stage 2): src["id"] is provider-
        # supplied and not guaranteed unique across sub-agents; the numeric prefix
        # keeps filenames distinct, but the `id` field itself could clash on a live
        # provider — revisit (dedup/disambiguate on id) when web_search lands.
        srcdir = s.dir / "sources"
        srcdir.mkdir(exist_ok=True)
        seen: set[str] = set()
        flat = [(blob.get("_round", 1), src)
                for blob in collected for src in blob.get("sources", [])]
        written = 0
        for round_index, src in flat:
            if written >= n or src["url"] in seen:
                continue
            seen.add(src["url"])
            written += 1
            sid = src.get("id", f"s{written:02d}")
            url = src["url"]
            stype = "Primary" if written % 2 else "Academic"  # scaffold: type is placeholder, not derived from the source
            s.sources.append({"id": sid, "url": url, "type": stype,
                              "title": src.get("title", "Source"),
                              "claim": src.get("claim", "")})
            s.round_source_ids.setdefault(round_index, []).append(sid)
            fm = (f"---\nid: {sid}\nurl: {url}\ntitle: {src.get('title', 'Source')}\n"
                  f"access: OPEN\ntype: {stype}\n---\n{src.get('claim', '')}\n")
            (srcdir / f"{written:02d}_{sid}.md").write_text(fm, encoding="utf-8")

        rows = ["id,title,url,type,used"]
        rows += [f"{x['id']},Source {x['id']},{x['url']},{x['type']},Y" for x in s.sources]
        (s.dir / "sources.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    # --- Phase 5: scoring + triangulation ---------------------------------
    def score(self, s: RunState) -> None:
        if not s.sources:
            (s.dir / "triangulation.md").write_text(
                f"# Triangulation — {s.slug}\n\n(no sources)\n", encoding="utf-8")
            return

        # step 1: per-source scoring (cheap tier).
        lookup = {x["id"]: x for x in s.sources}
        payload = [{"id": x["id"], "url": x["url"], "title": x.get("title", ""),
                    "claim": x.get("claim", "")} for x in s.sources]
        result = self.p.score(payload, s.hypotheses, model_tier="cheap")

        for item in result.get("sources", []):
            tgt = lookup.get(item.get("id"))
            if tgt is None:  # provider returned an id we never sent — ignore
                continue
            tgt["credibility"] = item["credibility"]
            tgt["recency"] = item["recency"]
            tgt["bias"] = item["bias"]
            tgt["type"] = item["type"]
            tgt["hypothesis_evidence"] = item.get("hypothesis_evidence", {})
            tgt["total"] = compute_total(item)

        # step 2: triangulation over scored sources.
        s.triangulation = triangulate(
            [x for x in s.sources if x.get("total") is not None], s.hypotheses)

        # step 3: persist.
        self._rewrite_sources(s)
        (s.dir / "triangulation.md").write_text(
            render_triangulation(s.slug, s.triangulation), encoding="utf-8")

        # step 4: backfill deviations now that sources are scored (closes the
        # TODO(Phase 5) in adaptive.py). For each pursued deviation, attach the
        # source ids produced by the round it spawned.
        for d in s.deviations:
            if d.status != "pursued":
                continue
            ids = s.round_source_ids.get(d.round_to, [])
            d.new_source_ids = list(ids)
            if ids:
                totals = [lookup[i]["total"] for i in ids
                          if i in lookup and lookup[i].get("total") is not None]
                avg = round(sum(totals) / len(totals), 1) if totals else "n/a"
                d.outcome = f"{len(ids)} sources, avg total {avg}"
            else:
                d.outcome = "no unique sources"
        write_deviations(s.dir, s.slug, s.deviations)

    def _rewrite_sources(self, s: RunState) -> None:
        srcdir = s.dir / "sources"
        srcdir.mkdir(exist_ok=True)
        for i, x in enumerate(s.sources, start=1):
            ev = x.get("hypothesis_evidence", {})
            ev_lines = "".join(f"  {h}: {v}\n" for h, v in ev.items())
            total = x.get("total")
            fm = (
                f"---\nid: {x['id']}\nurl: {x['url']}\n"
                f"title: {x.get('title', 'Source')}\naccess: OPEN\n"
                f"type: {x.get('type', 'Other')}\n"
                f"credibility: {x.get('credibility', '')}\n"
                f"recency: {x.get('recency', '')}\n"
                f"bias: {x.get('bias', '')}\n"
                f"total: {total if total is not None else 'null'}\n"
                f"used: Y\nhypothesis_evidence:\n{ev_lines}"
                f"---\n{x.get('claim', '')}\n"
            )
            (srcdir / f"{i:02d}_{x['id']}.md").write_text(fm, encoding="utf-8")

        rows = ["id,title,url,type,credibility,recency,bias,total,used"]
        for x in s.sources:
            total = x.get("total")
            rows.append(
                f"{x['id']},Source {x['id']},{x['url']},{x.get('type', 'Other')},"
                f"{x.get('credibility', '')},{x.get('recency', '')},{x.get('bias', '')},"
                f"{total if total is not None else ''},Y")
        (s.dir / "sources.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    # --- Phase 6: synthesis + adversarial ---------------------------------
    def synthesize(self, s: RunState) -> None:
        date = dt.date.today().isoformat()
        refs = " ".join(f"[{x['id']}]" for x in s.sources[:5])
        report = [
            f"# {s.question}",
            "",
            "> **Citation integrity: pending — run eval/check_citations.py (Phase 6.5)**",
            "",
            "## TL;DR",
            f"- Placeholder claim A {refs} [confidence: medium]",
            "",
            "## Counter-arguments (steel-man)",
            "- CA1: (scaffold) — strongest opposing view, with conditions it fails under.",
        ]
        (s.dir / f"{date}_{s.genre}.md").write_text("\n".join(report), encoding="utf-8")

    # --- Phase 6.5: verify (citation checking) -----------------------------
    def verify(self, s: RunState) -> None:
        citations = None
        if self.verify_live:
            verify_dir = s.dir / ".verify"
            verify_dir.mkdir(exist_ok=True)
            out_base = verify_dir / "citations"
            checker = Path(__file__).parent.parent / "eval" / "check_citations.py"
            try:
                subprocess.run(
                    [sys.executable, str(checker),
                     "--research-dir", str(s.dir), "--out", str(out_base), "--json"],
                    check=False,
                )
            except (FileNotFoundError, OSError):
                citations = None
            json_path = out_base.with_suffix(".json")
            if json_path.exists():
                try:
                    citations = json.loads(json_path.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    citations = None
        block = render_verification(citations)

        date = dt.date.today().isoformat()
        report_path = s.dir / f"{date}_{s.genre}.md"
        try:
            text = report_path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            # no report to patch (synthesize skipped / date rolled) — write the block alone
            text = ""
        if PLACEHOLDER in text:
            text = text.replace(PLACEHOLDER, block)
        elif text:
            text = text.rstrip() + "\n\n" + block + "\n"
        else:
            text = block + "\n"
        report_path.write_text(text, encoding="utf-8")

    def run(self, question: str, depth: str, root: Path) -> Path:
        s = RunState(question=question, depth=depth, root=root)
        self.reframe(s)
        self.choose_genre(s)
        self.plan(s)
        if s.depth != "shallow":
            self.discover_capabilities(s)
        self.search(s)
        self.score(s)
        self.synthesize(s)
        self.verify(s)
        return s.dir


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question")
    ap.add_argument("--depth", choices=DEPTH_SOURCES, default="medium")
    ap.add_argument("--provider", default="dryrun")
    ap.add_argument("--model", default=None, help="override the tier→model mapping (all tiers use this model)")
    ap.add_argument("--base-url", default=None, help="OpenAI-compatible endpoint base URL")
    ap.add_argument("--out", type=Path, default=Path("research"))
    args = ap.parse_args()

    orch = Orchestrator(build_provider(args.provider, model=args.model, base_url=args.base_url))
    run_dir = orch.run(args.question, args.depth, args.out)
    print(f"Run written to: {run_dir}")
    print("Validate with: python3 eval/validate_structure.py --research-dir", run_dir, "--strict")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
