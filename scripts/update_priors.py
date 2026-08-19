#!/usr/bin/env python3
"""Rebuild priors.json from the observation log.

Deliberately a full rebuild, never an in-place increment: the log is primary, so a
fix to the decay formula re-derives all history instead of destroying it.

Usage:
    python scripts/update_priors.py
    python scripts/update_priors.py --lambda 0.9
    python scripts/update_priors.py --qclass pricing   # все ячейки одного класса, без топ-20
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.priors import LAMBDA, rebuild_priors, posterior_mean  # noqa: E402
from runner.state import Prior, read_observations, save_priors  # noqa: E402


def update(root: Path | None = None, lam: float = LAMBDA) -> dict[str, Prior]:
    priors = rebuild_priors(read_observations(root=root), lam=lam)
    save_priors(priors, root=root)
    return priors


def ranked_for_qclass(priors: dict[str, Prior], qclass: str) -> list[tuple[str, Prior]]:
    """All cells for one qclass, ranked by posterior mean. No cap.

    A global top-20 (as --show without a filter uses) silently drops a qclass that
    isn't well-represented among the strongest cells overall — a live agent asking
    "what's known for THIS qclass" would get an empty answer that looks like "no
    signal" instead of "not in the top 20 globally". Filtering first removes that.
    """
    matching = [(k, p) for k, p in priors.items() if k.endswith(f"|{qclass}")]
    return sorted(matching, key=lambda kv: posterior_mean(kv[1]), reverse=True)


def main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lambda", dest="lam", type=float, default=LAMBDA)
    ap.add_argument(
        "--show", action="store_true", help="напечатать топ-20 ячеек по posterior mean"
    )
    ap.add_argument(
        "--qclass", help="показать все ячейки этого qclass, без ограничения топ-20"
    )
    args = ap.parse_args(argv)

    priors = update(root=root, lam=args.lam)
    print(f"ячеек: {len(priors)}")
    if args.qclass:
        for key, p in ranked_for_qclass(priors, args.qclass):
            print(f"  {posterior_mean(p):.2f}  n={p.n:<4} {key}")
    elif args.show:
        ranked = sorted(
            priors.items(), key=lambda kv: posterior_mean(kv[1]), reverse=True
        )
        for key, p in ranked[:20]:
            print(f"  {posterior_mean(p):.2f}  n={p.n:<4} {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
