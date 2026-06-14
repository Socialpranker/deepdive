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
import re
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

    @property
    def dir(self) -> Path:
        return self.root / self.slug


class Orchestrator:
    def __init__(self, provider: LLMProvider):
        self.p = provider

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
            collected.extend(blobs)
            return blobs

        deviations, _rounds = run_search_loop(self.p, s.depth, run_round)
        s.deviations = deviations
        write_deviations(s.dir, s.slug, deviations)

        # sources from collected blobs (dedup by url), capped at n
        srcdir = s.dir / "sources"
        srcdir.mkdir(exist_ok=True)
        seen: set[str] = set()
        flat = [src for blob in collected for src in blob.get("sources", [])]
        for i, src in enumerate(flat, start=1):
            if i > n or src["url"] in seen:
                continue
            seen.add(src["url"])
            sid = src.get("id", f"s{i:02d}")
            url = src["url"]
            stype = "Primary" if i % 2 else "Academic"
            s.sources.append({"id": sid, "url": url, "type": stype})
            fm = (f"---\nid: {sid}\nurl: {url}\ntitle: {src.get('title', 'Source')}\n"
                  f"access: OPEN\ntype: {stype}\n---\n{src.get('claim', '')}\n")
            (srcdir / f"{i:02d}_{sid}.md").write_text(fm, encoding="utf-8")

        rows = ["id,title,url,type,used"]
        rows += [f"{x['id']},Source {x['id']},{x['url']},{x['type']},Y" for x in s.sources]
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

    def run(self, question: str, depth: str, root: Path) -> Path:
        s = RunState(question=question, depth=depth, root=root)
        self.reframe(s)
        self.choose_genre(s)
        self.plan(s)
        self.search(s)
        self.synthesize(s)
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
