#!/usr/bin/env python3
"""Read the wiki before a run starts — the compounding half of the layer.

`discover existing` already looked for a similar slug in the target folder and read the
project's CLAUDE.md. That only ever finds a previous run of the SAME research. This
answers the other question: what does the accumulated wiki already know about this
topic, regardless of which run learned it.

Output is deliberately small and is meant to be pasted into phase 1 reframing:
already-scored sources (do not re-score them from zero), entities with prior claims, and
— the part that changes what gets researched — open cross-run conflicts touching the
topic. A conflict nobody has resolved is a research question that already earned its
place in the plan.

Usage:
    python scripts/wiki_query.py --topic "logical replication vs CDC"
    python scripts/wiki_query.py --topic "..." --entity postgres --json
    python scripts/wiki_query.py --stats
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.wiki import (  # noqa: E402
    entity_key,
    fold,
    load_claims,
    load_entities,
    load_sources,
    open_conflicts,
    tokens,
    wiki_dir,
)

MAX_ROWS = 12


def match_entities(topic: str, explicit: list[str], entities) -> list:
    """Explicit --entity wins; otherwise match entity names against the topic string."""
    if explicit:
        keys = {entity_key(e) for e in explicit}
        return [e for k, e in entities.items() if k in keys]
    folded = fold(topic)
    return [
        e
        for e in entities.values()
        if any(fold(n) and fold(n) in folded for n in [e.name, *e.aliases])
    ]


def query(topic: str, explicit: list[str], root: Path | None) -> dict:
    entities = load_entities(root)
    claims = load_claims(root)
    sources = load_sources(root)

    hits = match_entities(topic, explicit, entities)
    hit_keys = {e.key for e in hits}
    topic_tokens = tokens(topic)

    def relevance(text: str) -> float:
        t = tokens(text)
        return len(t & topic_tokens) / len(topic_tokens) if topic_tokens and t else 0.0

    related = [
        c
        for c in claims.values()
        if (hit_keys and set(c.entities) & hit_keys) or relevance(c.text) >= 0.25
    ]
    related.sort(key=lambda c: (c.as_of, c.ingested), reverse=True)

    claim_ids = {c.id for c in related}
    conflicts = [
        p
        for p in open_conflicts(root)
        if p.get("left") in claim_ids or p.get("right") in claim_ids
    ]

    source_ids = {s for c in related for s in c.sources}
    known_sources = [
        s
        for s in sources.values()
        if len(s.runs) > 1
        or relevance(f"{s.title} {s.url}") >= 0.25
        or s.key in source_ids
    ]
    known_sources.sort(key=lambda s: (-len(s.runs), s.title))

    return {
        "entities": [
            {"key": e.key, "name": e.name, "runs": e.runs, "page": e.page}
            for e in hits[:MAX_ROWS]
        ],
        "claims": [
            {
                "id": c.id,
                "run": c.run,
                "as_of": c.as_of,
                "status": c.status,
                "text": c.text,
                "page": c.page,
            }
            for c in related[:MAX_ROWS]
        ],
        "conflicts": conflicts[:MAX_ROWS],
        "sources": [
            {
                "key": s.key,
                "title": s.title,
                "url": s.url,
                "runs": s.runs,
                "credibility": s.credibility,
                "page": s.page,
            }
            for s in known_sources[:MAX_ROWS]
        ],
        "totals": {
            "entities": len(hits),
            "claims": len(related),
            "conflicts": len(conflicts),
            "sources": len(known_sources),
        },
    }


def render(res: dict) -> str:
    t = res["totals"]
    if not any(t.values()):
        return "Вики по теме молчит — чистый старт, ничего переиспользовать нельзя."
    out = [
        f"## Вики уже знает: {t['entities']} сущн. · {t['claims']} утв. · "
        f"{t['conflicts']} открытых противоречий · {t['sources']} источников",
        "",
    ]
    if res["conflicts"]:
        out += [
            "### ⚠ Открытые противоречия между прогонами — забрать в план как вопрос",
            "",
        ]
        for p in res["conflicts"]:
            out.append(
                f"- `{p['left']}` ({p.get('left_run')}, {p.get('left_as_of') or '—'}) "
                f"⟷ `{p['right']}` ({p.get('right_run')}, {p.get('right_as_of') or '—'})"
            )
            out.append(f"  - {p.get('reason', '')}")
        out.append("")
    if res["entities"]:
        out += ["### Сущности", ""]
        out += [
            f"- **{e['name']}** — {len(e['runs'])} прогон(ов), `{e['page']}`"
            for e in res["entities"]
        ]
        out.append("")
    if res["claims"]:
        out += ["### Что уже утверждалось", ""]
        out += [
            f"- `{c['id']}` ({c['run']}, {c['as_of'] or '—'}, {c['status'] or '—'}) — {c['text']}"
            for c in res["claims"]
        ]
        out.append("")
    if res["sources"]:
        out += ["### Источники с готовой оценкой — не пересчитывать с нуля", ""]
        out += [
            f"- [{s['title'] or s['url']}]({s['page']}) — cred {s['credibility'] or '?'}, "
            f"{len(s['runs'])}× ({', '.join(s['runs'])})"
            for s in res["sources"]
        ]
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--topic", default="", help="тема/вопрос ресёрча")
    ap.add_argument("--entity", action="append", default=[], help="можно несколько раз")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--stats", action="store_true", help="размер вики и выход")
    ap.add_argument("--wiki-root", type=Path, default=None)
    args = ap.parse_args()

    d = wiki_dir(args.wiki_root)
    if not d.is_dir():
        print(f"Вики ещё нет ({d}) — первый ресёрч её и создаст.")
        return 0

    if args.stats:
        print(
            f"{d}: {len(load_sources(args.wiki_root))} источников, "
            f"{len(load_entities(args.wiki_root))} сущностей, "
            f"{len(load_claims(args.wiki_root))} утверждений, "
            f"{len(open_conflicts(args.wiki_root))} открытых противоречий"
        )
        return 0

    if not args.topic and not args.entity:
        print("ERROR: нужен --topic или --entity (или --stats)")
        return 2

    res = query(args.topic, args.entity, args.wiki_root)
    print(json.dumps(res, ensure_ascii=False, indent=2) if args.json else render(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
