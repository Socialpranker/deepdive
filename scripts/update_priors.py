#!/usr/bin/env python3
"""Rebuild priors.json from the observation log.

Deliberately a full rebuild, never an in-place increment: the log is primary, so a
fix to the decay formula re-derives all history instead of destroying it.

Usage:
    python scripts/update_priors.py
    python scripts/update_priors.py --lambda 0.9
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lambda", dest="lam", type=float, default=LAMBDA)
    ap.add_argument(
        "--show", action="store_true", help="напечатать топ ячеек по posterior mean"
    )
    args = ap.parse_args()

    priors = update(lam=args.lam)
    print(f"ячеек: {len(priors)}")
    if args.show:
        ranked = sorted(
            priors.items(), key=lambda kv: posterior_mean(kv[1]), reverse=True
        )
        for key, p in ranked[:20]:
            print(f"  {posterior_mean(p):.2f}  n={p.n:<4} {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
