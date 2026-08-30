#!/usr/bin/env python3
"""Invariants of the wiki layer. Fails loud rather than letting the layer rot quietly.

An accumulating store degrades in ways nothing else notices: pages nothing links to,
`[[links]]` to pages that were never written, pair edges pointing at claims that no
longer exist, conflicts recorded with only one side filled in, and quarantined `unknown`
verdicts that were never revisited. None of these break a run, which is exactly why they
need a check that does.

The one that actually matters is the half-populated conflict. A conflict missing an
as_of on one side is indistinguishable from a stale figure, and a conflict missing roots
is indistinguishable from one source cited twice — either way it reaches a report as a
finding it has not earned. wiki_pair.py refuses to write one; this catches any that got
in another way.

Usage:
    python scripts/wiki_lint.py
    python scripts/wiki_lint.py --strict          # warnings are errors
    python scripts/wiki_lint.py --wiki-root /tmp/w
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.wiki import (  # noqa: E402
    VERDICTS,
    latest_verdicts,
    load_claims,
    load_entities,
    load_sources,
    parse_date,
    wiki_dir,
)

# How long a pair may sit in `unknown` before it counts as debt rather than caution.
# Quarantine is a legitimate answer; a quarantine nobody revisits is an unread inbox.
UNKNOWN_STALE_DAYS = 90
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, m: str) -> None:
        self.errors.append(m)

    def warn(self, m: str) -> None:
        self.warnings.append(m)


def check_pages_exist(d: Path, recs, kind: str, r: Report) -> None:
    for rec in recs:
        if not (d / rec.page).is_file():
            r.err(
                f"{kind}: в реестре есть '{rec.page}', файла нет — перезапусти wiki_ingest"
            )


def check_orphans(d: Path, known_pages: set[str], r: Report) -> None:
    for sub in ("sources", "entities", "claims"):
        p = d / sub
        if not p.is_dir():
            continue
        for f in p.glob("*.md"):
            rel = f"{sub}/{f.name}"
            if rel not in known_pages:
                r.warn(f"сирота: {rel} нет ни в одном реестре (переименование ключа?)")


def check_wikilinks(
    d: Path, entity_keys: set[str], claim_ids: set[str], r: Report
) -> None:
    valid = entity_keys | claim_ids
    for f in sorted(d.rglob("*.md")):
        if f.name == "INDEX.md":
            continue
        for m in WIKILINK_RE.finditer(f.read_text(encoding="utf-8")):
            target = m.group(1).strip()
            if target and target not in valid:
                r.warn(f"битый [[{target}]] в {f.relative_to(d)}")


def check_pairs(claim_ids: set[str], root: Path | None, r: Report) -> None:
    today = date.today()
    for (a, b), p in latest_verdicts(root).items():
        for side in (a, b):
            if side not in claim_ids:
                r.err(f"pairs.jsonl: ребро ссылается на несуществующий claim '{side}'")
        v = (p.get("verdict") or "").strip()
        if v not in VERDICTS and v not in ("superseded",):
            r.err(f"pairs.jsonl: неизвестный вердикт '{v}' для {a}⟷{b}")
        if v == "same-claim-conflict" and not p.get("resolved"):
            for fld in ("left_run", "right_run", "left_as_of", "right_as_of"):
                if not str(p.get(fld) or "").strip():
                    r.err(
                        f"конфликт {a}⟷{b}: пустое '{fld}' — односторонний конфликт не находка"
                    )
            if not p.get("left_roots") or not p.get("right_roots"):
                r.err(f"конфликт {a}⟷{b}: нет корней с обеих сторон")
        if v == "unknown":
            seen = parse_date(str(p.get("ts") or ""))
            if seen and today - seen > timedelta(days=UNKNOWN_STALE_DAYS):
                r.warn(f"карантин {a}⟷{b} висит с {seen} — разобрать или закрыть")


def check_registries(sources, entities, claims, r: Report) -> None:
    for c in claims.values():
        if not c.run:
            r.err(f"claim {c.id}: пустой run — не с чем сопоставлять прогоны")
        for e in c.entities:
            if e not in entities:
                r.warn(f"claim {c.id}: сущность '{e}' не в реестре")
    for s in sources.values():
        if not s.runs:
            r.err(f"source {s.key}: ни одного прогона — откуда он взялся?")


def lint(root: Path | None) -> Report:
    r = Report()
    d = wiki_dir(root)
    if not d.is_dir():
        r.warn(f"вики ещё нет: {d}")
        return r

    sources, entities, claims = (
        load_sources(root),
        load_entities(root),
        load_claims(root),
    )
    check_pages_exist(d, sources.values(), "sources", r)
    check_pages_exist(d, entities.values(), "entities", r)
    check_pages_exist(d, claims.values(), "claims", r)
    known = {
        rec.page for rec in (*sources.values(), *entities.values(), *claims.values())
    }
    check_orphans(d, known, r)
    check_wikilinks(d, set(entities), set(claims), r)
    check_pairs(set(claims), root, r)
    check_registries(sources, entities, claims, r)
    return r


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--strict", action="store_true", help="warnings тоже валят")
    ap.add_argument("--wiki-root", type=Path, default=None)
    args = ap.parse_args()

    r = lint(args.wiki_root)
    for w in r.warnings:
        print(f"WARN  {w}")
    for e in r.errors:
        print(f"ERROR {e}")
    if r.errors or (args.strict and r.warnings):
        print(f"\nFAIL — {len(r.errors)} ошибок, {len(r.warnings)} предупреждений")
        return 1
    print(f"OK — вики консистентна ({len(r.warnings)} предупреждений)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
