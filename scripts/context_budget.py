#!/usr/bin/env python3
"""
Context-budget instrumentation for the deep-research skill.

The skill ships ~154k tokens of markdown across SKILL.md + references/. That is
fine *only* if progressive loading is disciplined: load a reference when you reach
the phase that needs it, never preemptively. This script makes that discipline
measurable instead of aspirational.

It does three things:
  1. Inventories every .md under the skill root, grouping by directory, and prints
     a token-proxy report (bytes / 4, the same proxy score_run.py uses).
  2. Models named load-profiles (what a given depth actually pulls into context)
     and reports each as a share of a target window.
  3. In --ci mode, fails (exit 1) if the always-loaded floor or SKILL.md itself
     exceeds the configured budget — so a PR that bloats SKILL.md is caught.

Usage:
    python scripts/context_budget.py                       # full report
    python scripts/context_budget.py --window 200000       # share of a 200k window
    python scripts/context_budget.py --ci                  # enforce budgets, exit 1 on breach
    python scripts/context_budget.py --json budget.json     # machine-readable

No third-party deps. Run from the repo root (or pass --root).
"""

import argparse
import json
import re
import sys
from pathlib import Path

CHARS_PER_TOKEN = 4  # token proxy; MUST match eval/score_run.py (enforced in --ci, see check_proxy_in_sync)


def check_proxy_in_sync(root: Path) -> str | None:
    """Guard the hand-synced CHARS_PER_TOKEN contract with eval/score_run.py.

    Returns an error string if score_run.py defines a different value (or can't be
    read), else None. Cheap text scan — avoids importing score_run across packages.
    """
    src = root / "eval" / "score_run.py"
    try:
        text = src.read_text(encoding="utf-8")
    except OSError:
        return f"cannot read {src} to verify CHARS_PER_TOKEN is in sync"
    m = re.search(r"^CHARS_PER_TOKEN\s*=\s*(\d+)", text, re.MULTILINE)
    if not m:
        return f"CHARS_PER_TOKEN not found in {src} (can't verify proxies are in sync)"
    other = int(m.group(1))
    if other != CHARS_PER_TOKEN:
        return f"CHARS_PER_TOKEN drift: this file={CHARS_PER_TOKEN} but score_run.py={other}"
    return None


# Budgets in tokens. Tune as the catalog evolves; these are the guard-rails CI enforces.
BUDGET_SKILL_MD = 7500        # SKILL.md is read on EVERY invocation — keep it lean
BUDGET_ALWAYS_FLOOR = 56000   # the "base refs" SKILL.md says to always load for medium/deep
# Raised from 55000 on 2026-07-07: claims.csv artifact + gap-wave loop (Phase 5) + 2
# new report blocks (F9 background, Z12 so-what-for-you) added durable value at a
# modest, deliberately-trimmed floor cost (~1200 tok). See docs/2026-07-07-v2-design.md.

# Files SKILL.md marks as "Базовые (всегда)" — the unavoidable floor for a medium/deep run.
ALWAYS_LOAD = [
    "SKILL.md",
    "references/workflow.md",
    "references/question_reframing.md",
    "references/genres.md",
    "references/blocks/INDEX.md",
    "references/channels.md",
    "references/stat_sources/INDEX.md",
    "references/api_sources/INDEX.md",
    "references/capability_discovery.md",
    "references/awesome_lists_registry.md",
    "references/source_dispatch.md",
    "references/model_routing.md",
    "references/refresh_protocol.md",
]

# Named load-profiles: realistic context cost of a run at a given depth.
# A profile is ALWAYS_LOAD plus whatever a typical run of that depth additionally pulls.
PROFILES = {
    "shallow": [
        "SKILL.md", "references/genres.md", "references/blocks/INDEX.md",
        "references/blocks/frame.md", "references/source_scoring.md",
    ],
    "medium": ALWAYS_LOAD + [
        "references/blocks/frame.md", "references/blocks/explain.md",
        "references/blocks/compare.md", "references/blocks/close.md",
        "references/subagents_v2.md", "references/adversarial_pass.md",
        "references/source_scoring.md",
    ],
    "deep": ALWAYS_LOAD + [
        "references/subagents_v2.md", "references/adversarial_pass.md",
        "references/source_scoring.md",
        # deep pulls several block categories + a few stat/api leaf files
        "references/blocks/frame.md", "references/blocks/explain.md",
        "references/blocks/compare.md", "references/blocks/map.md",
        "references/blocks/analyze.md", "references/blocks/numbers.md",
        "references/blocks/validate.md", "references/blocks/close.md",
        "references/stat_sources/core/gov_macro.md",
        "references/stat_sources/core/companies_public.md",
    ],
}


def tok(nbytes: int) -> int:
    return nbytes // CHARS_PER_TOKEN


def inventory(root: Path) -> dict[str, int]:
    """Map every tracked .md path (relative to root) -> byte size."""
    out: dict[str, int] = {}
    for p in root.rglob("*.md"):
        rel = p.relative_to(root).as_posix()
        # skip top-level project docs that are not part of the skill payload
        if rel in {"README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md"} or rel.startswith(("docs/", "eval/")):
            continue
        out[rel] = p.stat().st_size
    return out


def group_sizes(inv: dict[str, int]) -> dict[str, int]:
    groups: dict[str, int] = {}
    for path, size in inv.items():
        if path == "SKILL.md":
            key = "SKILL.md"
        elif path.startswith("references/blocks/"):
            key = "references/blocks/"
        elif path.startswith("references/stat_sources/"):
            key = "references/stat_sources/"
        elif path.startswith("references/api_sources/"):
            key = "references/api_sources/"
        else:
            key = "references/ (top-level)"
        groups[key] = groups.get(key, 0) + size
    return groups


def profile_tokens(inv: dict[str, int], files: list[str]) -> tuple[int, list[str]]:
    total = 0
    missing = []
    for f in files:
        if f in inv:
            total += inv[f]
        else:
            missing.append(f)
    return tok(total), missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path("."), help="Skill repo root")
    ap.add_argument("--window", type=int, default=200000, help="Context window for share math")
    ap.add_argument("--ci", action="store_true", help="Enforce budgets, exit 1 on breach")
    ap.add_argument("--json", type=Path, help="Write machine-readable report to this path")
    args = ap.parse_args()

    inv = inventory(args.root)
    if "SKILL.md" not in inv:
        print(f"ERROR: SKILL.md not found under {args.root.resolve()} — run from repo root or pass --root")
        return 2

    total = tok(sum(inv.values()))
    groups = {k: tok(v) for k, v in group_sizes(inv).items()}
    skill_tok = tok(inv["SKILL.md"])
    always_tok, always_missing = profile_tokens(inv, ALWAYS_LOAD)

    print(f"Deep-research context budget  (proxy: {CHARS_PER_TOKEN} chars/token, window {args.window:,})")
    print("=" * 64)
    print(f"Catalog files: {len(inv)}")
    print(f"WHOLE catalog if fully loaded: ~{total:,} tok  ({total/args.window*100:.1f}% of window)")
    print()
    print("By group:")
    for k, v in sorted(groups.items(), key=lambda kv: -kv[1]):
        print(f"  {k:32} ~{v:>7,} tok  ({v/args.window*100:4.1f}%)")
    print()
    print(f"SKILL.md (loaded every call): ~{skill_tok:,} tok   budget {BUDGET_SKILL_MD:,}")
    print(f"ALWAYS floor (base refs):     ~{always_tok:,} tok   budget {BUDGET_ALWAYS_FLOOR:,}  ({always_tok/args.window*100:.1f}% of window)")
    if always_missing:
        print(f"  ! not found (rename?): {', '.join(always_missing)}")
    print()
    print("Load profiles (realistic context cost at each depth):")
    profile_report = {}
    for name, files in PROFILES.items():
        t, miss = profile_tokens(inv, files)
        profile_report[name] = t
        warn = f"  ! missing: {', '.join(miss)}" if miss else ""
        print(f"  {name:8} ~{t:>7,} tok  ({t/args.window*100:4.1f}% of window){warn}")

    if args.json:
        args.json.write_text(json.dumps({
            "total_tokens": total, "skill_md_tokens": skill_tok,
            "always_floor_tokens": always_tok, "groups": groups,
            "profiles": profile_report, "window": args.window,
        }, indent=2), encoding="utf-8")
        print(f"\nJSON: {args.json}")

    if args.ci:
        breaches = []
        if skill_tok > BUDGET_SKILL_MD:
            breaches.append(f"SKILL.md {skill_tok} > {BUDGET_SKILL_MD}")
        if always_tok > BUDGET_ALWAYS_FLOOR:
            breaches.append(f"always-floor {always_tok} > {BUDGET_ALWAYS_FLOOR}")
        # A renamed/missing base ref silently shrinks the measured floor — treat as a breach,
        # not a printed note, so the guard can't pass while measuring a smaller-than-real floor.
        if always_missing:
            breaches.append(f"always-floor files missing (rename?): {', '.join(always_missing)}")
        # The token proxy is hand-synced with score_run.py; fail if the two have drifted.
        drift = check_proxy_in_sync(args.root)
        if drift:
            breaches.append(drift)
        if breaches:
            print("\nBUDGET BREACH:\n  " + "\n  ".join(breaches))
            return 1
        print("\nBudgets OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
