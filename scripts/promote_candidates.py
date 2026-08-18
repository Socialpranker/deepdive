#!/usr/bin/env python3
"""Promote proven runtime sources into the catalog; flag dead ones for removal.

Promotion needs three independent facts at once, because any one of them alone is
gameable by a single lucky run: repeated wins across DISTINCT runs, a parent channel
that has not degraded, and an endpoint that answers right now.

Demotion is the other half. Without it the catalog only ever grows and its share of
dead addresses climbs silently.

Usage:
    python scripts/promote_candidates.py --dry-run
    python scripts/promote_candidates.py --write   # печатает дифф, файлы не коммитит
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.priors import effective_prior, load_channel_groups, posterior_mean  # noqa: E402
from runner.state import Prior, load_priors, state_dir  # noqa: E402

PROMOTE_THRESHOLD = 0.3
MIN_WINS = 3
MIN_DISTINCT_RUNS = 3
DEAD_STRIKES = 3

SKILL_ROOT = Path(__file__).resolve().parent.parent
CHANNELS_MD = SKILL_ROOT / "references" / "channels.md"


@dataclass
class Candidate:
    url: str
    channel: str
    qclass: str
    wins: int
    runs: list[str] = field(default_factory=list)
    first_seen: str = ""
    last_probe: str = ""
    alive: bool = True


def read_candidates(root: Path | None = None) -> list[Candidate]:
    p = state_dir(root) / "candidates.jsonl"
    if not p.exists():
        return []
    out: list[Candidate] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(Candidate(**json.loads(line)))
        except (json.JSONDecodeError, TypeError):
            continue
    return out


def write_candidates(cands: list[Candidate], root: Path | None = None) -> None:
    d = state_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    (d / "candidates.jsonl").write_text(
        "\n".join(json.dumps(asdict(c), ensure_ascii=False) for c in cands) + "\n",
        encoding="utf-8",
    )


def eligible_for_promotion(
    c: Candidate, priors: dict[str, Prior], groups: dict[str, str]
) -> bool:
    if not c.alive or c.wins < MIN_WINS:
        return False
    if len(set(c.runs)) < MIN_DISTINCT_RUNS:
        return False
    parent = effective_prior(priors, c.channel, c.qclass, groups)
    return posterior_mean(parent) >= PROMOTE_THRESHOLD


def eligible_for_demotion(c: Candidate) -> bool:
    return not c.alive and len(set(c.runs)) >= DEAD_STRIKES


def render_source_file(c: Candidate) -> str:
    return (
        "---\n"
        f"url: {c.url}\n"
        f"channel: {c.channel}\n"
        "access: api-free-no-key\n"
        f"qclass: {c.qclass}\n"
        f"first_seen: {c.first_seen}\n"
        f"promoted_after_runs: {len(set(c.runs))}\n"
        "---\n\n"
        f"# {c.url}\n\n"
        f"Промотирован автоматически: {c.wins} улик в {len(set(c.runs))} прогонах.\n"
        "Достоверность — метка разведки, не результат Фазы 5.5.\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="создать файлы в api_sources/")
    ap.add_argument("--dry-run", action="store_true", default=True)
    args = ap.parse_args()

    priors = load_priors()
    groups = load_channel_groups(CHANNELS_MD)
    cands = read_candidates()

    promote = [c for c in cands if eligible_for_promotion(c, priors, groups)]
    demote = [c for c in cands if eligible_for_demotion(c)]

    for c in promote:
        target = (
            SKILL_ROOT
            / "references"
            / "api_sources"
            / "promoted"
            / (c.url.replace("https://", "").replace("/", "_") + ".md")
        )
        print(f"[promote] {c.url} -> {target.relative_to(SKILL_ROOT)}")
        print(render_source_file(c))
        if args.write:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_source_file(c), encoding="utf-8")

    for c in demote:
        print(
            f"[demote]  {c.url} — мёртв в {len(set(c.runs))} прогонах, предлагается к удалению"
        )

    print(f"\nк промоушену: {len(promote)}, к удалению: {len(demote)}")
    if args.write:
        print("Файлы созданы. Коммит — вручную, после просмотра диффа.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
