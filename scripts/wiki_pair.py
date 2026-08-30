#!/usr/bin/env python3
"""Phase 5.7 — confront this run's claims with what earlier runs already established.

Two invocations, and the split between them is the whole safety argument:

  build    mechanical. Emits only pairs that are comparable at all (shared entity plus a
           shared unit or enough shared content), then decides by itself every pair that
           needs no judgement — a figure that is merely newer, a unit mismatch, a
           different scope. Those never reach a model, so no amount of model confidence
           can turn them into a contradiction. What is left goes to .verify/wiki_pairs.json.

  record   takes the adjudicator's verdicts back and appends them to the wiki's
           pairs.jsonl. Refuses a conflict that is not fully attributed on both sides,
           because a half-populated conflict is a bug in the caller, not a finding, and
           it would otherwise land in a report as one.

A conflict here is not automatically a defect in either run. Two well-sourced claims can
disagree because the world is contested — that is what phase 5's `dissent` machinery is
already for. What this adds is that the disagreement is now visible ACROSS runs instead
of only inside one.

Usage:
    python scripts/wiki_pair.py build  --research-dir research/<slug>
    python scripts/wiki_pair.py record --research-dir research/<slug> --verdicts <file.json>
    python scripts/wiki_pair.py build  --research-dir research/<slug> --wiki-root /tmp/w
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.wiki import (  # noqa: E402
    VERDICTS,
    ClaimPage,
    candidate_pairs,
    claim_uid,
    load_claims,
    load_entities,
)
from scripts.wiki_ingest import attach_entities, read_run_claims  # noqa: E402

# A model asked to compare N×M pairs will find something in all of them. The prefilter
# already culls hard, but a broad landscape run against a mature wiki can still produce
# hundreds — and a phase that silently truncates reads as "nothing else conflicted".
# So the cap is loud: whatever is dropped is named in the output and in the report.
MAX_ADJUDICATED = 40


def run_claims_as_pages(run_dir: Path, wiki_root: Path | None) -> list[ClaimPage]:
    """The run's claims in wiki shape, WITHOUT ingesting them.

    5.7 happens before synthesis and ingest happens after, so this cannot read them back
    from the registry. claim_uid is (run, claim_id) precisely so the ids built here are
    the ids ingest will write later.
    """
    entities = load_entities(wiki_root)
    run = run_dir.name
    today = date.today().isoformat()
    out = []
    for row in read_run_claims(run_dir):
        text = (row.get("claim") or row.get("text") or "").strip()
        if not text:
            continue
        out.append(
            ClaimPage(
                id=claim_uid(run, row.get("claim_id", "")),
                run=run,
                claim_id=row.get("claim_id", "").strip(),
                text=text,
                status=row.get("status", "").strip(),
                confidence=row.get("confidence", "").strip(),
                as_of=row.get("as_of", "").strip(),
                entities=attach_entities(text, entities),
                sources=[
                    s.strip()
                    for s in re.split(r"[;,]", row.get("sources", ""))
                    if s.strip()
                ],
                roots=[
                    r.strip()
                    for r in re.split(r"[;,]", row.get("roots", ""))
                    if r.strip()
                ],
                ingested=today,
            )
        )
    return out


def build(run_dir: Path, wiki_root: Path | None) -> dict:
    from runner.wiki import (
        append_pairs,
    )  # local: keeps the import graph honest in tests

    new = run_claims_as_pages(run_dir, wiki_root)
    wiki = {k: v for k, v in load_claims(wiki_root).items() if v.run != run_dir.name}
    auto, todo = candidate_pairs(new, wiki)

    dropped = 0
    if len(todo) > MAX_ADJUDICATED:
        # Newest counterpart first: a disagreement with last month's research is worth a
        # model call before one with a two-year-old run.
        todo.sort(key=lambda p: p.get("left_as_of", ""), reverse=True)
        dropped = len(todo) - MAX_ADJUDICATED
        todo = todo[:MAX_ADJUDICATED]

    stamped = [dict(p, ts=date.today().isoformat()) for p in auto]
    append_pairs(stamped, wiki_root)

    out = run_dir / ".verify" / "wiki_pairs.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run": run_dir.name,
        "generated": date.today().isoformat(),
        "wiki_claims_compared": len(wiki),
        "auto_resolved": len(auto),
        "dropped_over_cap": dropped,
        "verdict_values": list(VERDICTS),
        "pairs": todo,
    }
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def record(
    run_dir: Path, wiki_root: Path | None, verdicts_path: Path
) -> tuple[int, list[str]]:
    from runner.wiki import append_pairs

    data = json.loads(verdicts_path.read_text(encoding="utf-8"))
    rows = data["pairs"] if isinstance(data, dict) else data
    errors: list[str] = []
    ok: list[dict] = []
    today = date.today().isoformat()

    for i, p in enumerate(rows):
        v = (p.get("verdict") or "").strip()
        if v not in VERDICTS:
            errors.append(f"pair[{i}]: verdict '{v}' не из {VERDICTS}")
            continue
        if not p.get("left") or not p.get("right"):
            errors.append(f"pair[{i}]: нет left/right")
            continue
        if v == "same-claim-conflict":
            # Both sides fully attributed or it is not a conflict. Without two as_of
            # dates nobody downstream can tell a disagreement from a stale figure, and
            # without two root sets they cannot tell it from one source cited twice.
            for fld in ("left_run", "right_run", "left_as_of", "right_as_of"):
                if not str(p.get(fld) or "").strip():
                    errors.append(f"pair[{i}] conflict: пустое поле '{fld}'")
            if not p.get("left_roots") or not p.get("right_roots"):
                errors.append(f"pair[{i}] conflict: нет корней с обеих сторон")
            if not str(p.get("reason") or "").strip():
                errors.append(f"pair[{i}] conflict: нет reason")
        ok.append(dict(p, by=p.get("by") or "adjudicator", ts=today))

    if errors:
        return 0, errors
    append_pairs(ok, wiki_root)
    return len(ok), []


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("mode", choices=("build", "record"))
    ap.add_argument("--research-dir", required=True, type=Path)
    ap.add_argument(
        "--verdicts", type=Path, help="record: JSON с вердиктами адъюдикатора"
    )
    ap.add_argument(
        "--wiki-root", type=Path, default=None, help="override ~/.claude (tests)"
    )
    args = ap.parse_args()

    if not args.research_dir.is_dir():
        print(f"ERROR: not a directory: {args.research_dir}")
        return 2

    if args.mode == "build":
        p = build(args.research_dir, args.wiki_root)
        print(
            f"Сравнено с {p['wiki_claims_compared']} утверждениями вики: "
            f"{p['auto_resolved']} закрыто механически, {len(p['pairs'])} на адъюдикацию"
            + (
                f", {p['dropped_over_cap']} срезано лимитом {MAX_ADJUDICATED}"
                if p["dropped_over_cap"]
                else ""
            )
        )
        if p["dropped_over_cap"]:
            print(
                "  ⚠ срез назвать в отчёте: непроверенные пары ≠ отсутствие противоречий"
            )
        return 0

    if not args.verdicts or not args.verdicts.is_file():
        print("ERROR: record требует --verdicts <file.json>")
        return 2
    n, errors = record(args.research_dir, args.wiki_root, args.verdicts)
    if errors:
        print("ОТКЛОНЕНО, ничего не записано:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"Записано вердиктов: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
