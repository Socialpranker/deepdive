#!/usr/bin/env python3
"""Derive swarm observations from a finished run. Read-only w.r.t. the run.

No new instrumentation is needed inside the run: sources/NN.md already carries
`discovery_path: <channel>|<query>|<lang>` and claims.csv already carries
sources + dissent. This script only folds what is already written.

Usage:
    python scripts/collect_observations.py --research-dir research/<slug> \
        --run-id <uuid> --requested academic=scientific-claim,web-general=market-size
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.qclass import normalize_qclass  # noqa: E402
from runner.state import Observation, append_observation  # noqa: E402

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Flat `key: value` reader — same contract as check_number_provenance.py.

    Skips blank lines, comment lines (`#`), and nested blocks (any line with
    leading whitespace, e.g. `hypothesis_evidence:` -> `H1: supports`) — those
    are not flat `key: value` pairs and must not be folded into the dict.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace():  # nested block (hypothesis_evidence) — not needed here
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        out[key.strip()] = value.split("#", 1)[0].strip()
    return out


def channel_of(fm: dict[str, str]) -> str:
    """discovery_path is `<channel>|<query>|<lang>`; the channel is the first field."""
    return (fm.get("discovery_path", "") or "").split("|", 1)[0].strip()


def rewarded_sources(rows: list[dict]) -> set[str]:
    """A source earns a reward by grounding a claim OR by dissenting unrefuted.

    Only `sources` and `dissent` are scanned — NOT `roots`. `roots` holds root
    identifiers (e.g. "study-smith-2024", "gartner-mq-2025"), not source ids
    (s1, s2, ...); matching a source id against it is a coincidental string
    collision that adds nothing real (a source that became a claim's root is
    already present in `sources`).

    Dissent counts equally on purpose: reward only for confirmation teaches the
    swarm to stop looking for counter-evidence, which is Phase 6's whole job.
    """
    out: set[str] = set()
    for row in rows:
        for field in ("sources", "dissent"):
            for token in (row.get(field) or "").split(";"):
                token = token.strip()
                if token and token != "-":
                    out.add(token)
    return out


def collect(
    research_dir: Path, run_id: str, requested: dict[str, str]
) -> list[Observation]:
    research_dir = Path(research_dir)
    ledger = research_dir / "claims.csv"
    rows = (
        list(csv.DictReader(ledger.read_text(encoding="utf-8").splitlines()))
        if ledger.exists()
        else []
    )
    rewarded = rewarded_sources(rows)

    winning_channels: set[str] = set()
    for src in sorted((research_dir / "sources").glob("*.md")):
        fm = parse_frontmatter(src.read_text(encoding="utf-8"))
        sid = fm.get("id", "")
        ch = channel_of(fm)
        if ch and sid and sid in rewarded:
            winning_channels.add(ch)

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return [
        Observation(
            run_id=run_id,
            channel=ch,
            qclass=normalize_qclass(qc),
            reward=1 if ch in winning_channels else 0,
            ts=ts,
        )
        for ch, qc in sorted(requested.items())
    ]


def parse_requested(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        ch, _, qc = pair.partition("=")
        out[ch.strip()] = qc.strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--research-dir", required=True, type=Path)
    ap.add_argument("--run-id", required=True)
    ap.add_argument(
        "--requested",
        required=True,
        help="channel=qclass через запятую — каналы, которые прогон запрашивал",
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="напечатать, ничего не записывать"
    )
    args = ap.parse_args()

    obs = collect(args.research_dir, args.run_id, parse_requested(args.requested))
    for o in obs:
        if args.dry_run:
            print(json.dumps(o.__dict__, ensure_ascii=False))
        else:
            append_observation(o)
    print(f"наблюдений: {len(obs)}, наград: {sum(o.reward for o in obs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
