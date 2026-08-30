#!/usr/bin/env python3
"""Compile a finished run into the cross-run wiki. Deterministic — no model calls.

Runs from finish-up step 0, next to build_sources_csv.py, so it fires at EVERY depth.
A shallow run costs nothing to ingest and its sources are exactly as reusable as a deep
run's; gating the write on depth would have starved the wiki of most of its input and
left phase 5.7 with nothing to compare against.

What it writes:
  sources/<slug>.md   one page per canonical URL/DOI, accumulating runs, roots, caveats
  entities/<key>.md   one page per tracked entity, accumulating runs and aliases
  claims/<id>.md      one page per claim OBSERVATION (never merged across runs)
  .wiki/*.csv         the registries those pages are rendered from
  INDEX.md            navigation, regenerated

Claims are appended, not reconciled. Deciding two runs made the same claim is phase
5.7's job and its verdicts live in .wiki/pairs.jsonl — this script must never fuse two
records, because a wrong fusion is unrecoverable while a wrong edge is one line to fix.

Usage:
    python scripts/wiki_ingest.py --research-dir research/<slug>
    python scripts/wiki_ingest.py --research-dir research/<slug> --dry-run
    python scripts/wiki_ingest.py --research-dir research/<slug> --wiki-root /tmp/w
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runner.wiki import (  # noqa: E402
    ClaimPage,
    EntityPage,
    SourcePage,
    claim_uid,
    ensure_wiki,
    entity_key,
    fold,
    load_claims,
    load_entities,
    load_sources,
    save_claims,
    save_entities,
    save_sources,
    source_key,
    wiki_dir,
)

ENTITY_SECTION_RE = re.compile(
    r"^##\s+\d*\.?\s*Entities to track\s*$", re.MULTILINE | re.I
)
ENTITY_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
NEXT_H2_RE = re.compile(r"^##\s+", re.MULTILINE)


def _bullets(items: list[str], empty: str = "- —") -> list[str]:
    """`*(gen) or [fallback]` never fires the fallback — a generator is always truthy."""
    return [f"- {i}" for i in items] or [empty]


def _merge(existing: list[str], *values: str) -> list[str]:
    """Union preserving first-seen order — a page's history reads chronologically."""
    out = list(existing)
    for v in values:
        for part in re.split(r"[;,]", v or ""):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


def read_run_sources(d: Path) -> list[dict[str, str]]:
    p = d / "sources.csv"
    if not p.is_file():
        return []
    with p.open(encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if (r.get("url") or "").strip()]


def read_run_claims(d: Path) -> list[dict[str, str]]:
    p = d / "claims.csv"
    if not p.is_file():
        return []
    with p.open(encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if (r.get("claim_id") or "").strip()]


def read_run_entities(d: Path) -> list[str]:
    """Entity names from refresh_targets.md §1. Absent file → no entities, not a guess.

    Nothing here invents an entity from prose. A shallow run without refresh_targets.md
    still contributes claims; those claims just attach to entities already known to the
    wiki (see attach_entities), which is the conservative direction — an unknown entity
    produces no pairs, while an invented one produces wrong ones.
    """
    p = d / "refresh_targets.md"
    if not p.is_file():
        return []
    text = p.read_text(encoding="utf-8")
    m = ENTITY_SECTION_RE.search(text)
    if not m:
        return []
    rest = text[m.end() :]
    nxt = NEXT_H2_RE.search(rest)
    block = rest[: nxt.start()] if nxt else rest
    names = []
    for h in ENTITY_HEADING_RE.finditer(block):
        name = h.group(1).strip().strip("`*_")
        # The Z11 template writes headings as `### Company X — Seed $5M (2026-07-15)`,
        # so the raw heading is a phrase, not a name. Keeping the tail produced keys like
        # `rosy-закрыт` and `ami-labs-ян-лекун`, which never occur in a claim's text and
        # therefore never matched anything. Head before the dash is the name; the rest is
        # descriptive and dropped.
        head = re.split(r"\s+[—–-]\s+|\s*\(", name)[0].strip()
        if head and not head.startswith("<") and entity_key(head):
            names.append(head)
    return names


def attach_entities(text: str, known: dict[str, EntityPage]) -> list[str]:
    """Which known entities this claim mentions. Whole-word match on folded text."""
    folded = fold(text)
    hits = []
    for key, ent in known.items():
        for name in [ent.name, *ent.aliases]:
            n = fold(name)
            if n and re.search(
                rf"(?<![0-9a-zа-я]){re.escape(n)}(?![0-9a-zа-я])", folded
            ):
                hits.append(key)
                break
    return sorted(set(hits))


def render_source_page(rec: SourcePage) -> str:
    return "\n".join(
        [
            "---",
            f"key: {rec.key}",
            f"url: {rec.url}",
            f"title: {rec.title}",
            f"type: {rec.type}",
            f"channel: {rec.channel}",
            f"doi: {rec.doi}",
            f"credibility: {rec.credibility}",
            f"first_seen: {rec.first_seen}",
            f"last_seen: {rec.last_seen}",
            "---",
            "",
            f"# {rec.title or rec.url}",
            "",
            f"<{rec.url}>",
            "",
            "## Прогоны",
            "",
            *(f"- `{r}`" for r in rec.runs),
            "",
            "## Корни (root:)",
            "",
            *_bullets(rec.roots),
            "",
            "## Оговорки",
            "",
            *_bullets(rec.caveats),
            "",
        ]
    )


def render_entity_page(rec: EntityPage, claims: list[ClaimPage]) -> str:
    lines = [
        "---",
        f"key: {rec.key}",
        f"name: {rec.name}",
        f"aliases: {', '.join(rec.aliases) or '—'}",
        f"first_seen: {rec.first_seen}",
        f"last_seen: {rec.last_seen}",
        "---",
        "",
        f"# {rec.name}",
        "",
        "## Прогоны",
        "",
        *(f"- `{r}`" for r in rec.runs),
        "",
        "## Утверждения",
        "",
    ]
    if claims:
        lines += [
            f"- [[{c.id}]] ({c.run}, {c.as_of or 'as_of —'}, {c.status or '—'}) — {c.text}"
            for c in claims
        ]
    else:
        lines.append("- —")
    return "\n".join(lines) + "\n"


def render_claim_page(rec: ClaimPage) -> str:
    return "\n".join(
        [
            "---",
            f"id: {rec.id}",
            f"run: {rec.run}",
            f"claim_id: {rec.claim_id}",
            f"status: {rec.status}",
            f"confidence: {rec.confidence}",
            f"as_of: {rec.as_of}",
            f"ingested: {rec.ingested}",
            "---",
            "",
            f"# {rec.id}",
            "",
            rec.text,
            "",
            "## Сущности",
            "",
            *_bullets([f"[[{e}]]" for e in rec.entities]),
            "",
            "## Источники прогона",
            "",
            *_bullets(rec.sources),
            "",
            f"Корни: {', '.join(rec.roots) or '—'}",
            "",
        ]
    )


def render_index(
    sources: dict[str, SourcePage],
    entities: dict[str, EntityPage],
    claims: dict[str, ClaimPage],
) -> str:
    runs = sorted(
        {r for c in claims.values() for r in [c.run]}
        | {r for s in sources.values() for r in s.runs}
    )
    reused = [s for s in sources.values() if len(s.runs) > 1]
    lines = [
        "# Deepdive wiki — кросс-прогонный слой",
        "",
        "Пишется `scripts/wiki_ingest.py` из finish-up, читается `scripts/wiki_query.py`",
        "в `discover existing` и фазой 5.7. Руками не редактируется: правка переживёт",
        "ровно до следующего ingest. Спорное — в `.wiki/pairs.jsonl`.",
        "",
        f"- Источников: **{len(sources)}** (в ≥2 прогонах: {len(reused)})",
        f"- Сущностей: **{len(entities)}**",
        f"- Наблюдений-утверждений: **{len(claims)}**",
        f"- Прогонов: **{len(runs)}**",
        "",
        "## Сущности",
        "",
    ]
    for key in sorted(entities):
        e = entities[key]
        lines.append(f"- [{e.name}]({e.page}) — {len(e.runs)} прогон(ов)")
    lines += ["", "## Источники, переиспользованные между прогонами", ""]
    for s in sorted(reused, key=lambda s: -len(s.runs))[:50]:
        lines.append(
            f"- [{s.title or s.url}]({s.page}) — {len(s.runs)}× ({', '.join(s.runs)})"
        )
    if not reused:
        lines.append("- —")
    lines += ["", "## Прогоны", ""] + [f"- `{r}`" for r in runs] + [""]
    return "\n".join(lines)


def ingest(
    run_dir: Path, wiki_root: Path | None, dry_run: bool = False
) -> dict[str, int]:
    run = run_dir.name
    today = date.today().isoformat()

    sources = load_sources(wiki_root)
    entities = load_entities(wiki_root)
    claims = load_claims(wiki_root)
    stats = {"sources_new": 0, "sources_seen": 0, "entities_new": 0, "claims_new": 0}

    for row in read_run_sources(run_dir):
        key = source_key(row.get("url", ""), row.get("doi", ""))
        if not key:
            continue
        rec = sources.get(key)
        if rec is None:
            rec = SourcePage(key=key, url=row.get("url", "").strip(), first_seen=today)
            sources[key] = rec
            stats["sources_new"] += 1
        else:
            stats["sources_seen"] += 1
        rec.title = rec.title or row.get("title", "").strip()
        rec.type = rec.type or row.get("type", "").strip()
        rec.channel = rec.channel or row.get("channel", "").strip()
        rec.doi = rec.doi or row.get("doi", "").strip()
        # Highest score ever assigned wins; a later run scoring the same source lower is
        # a signal to look, not a reason to silently downgrade a page other runs cite.
        rec.credibility = max(
            [
                v
                for v in (rec.credibility, row.get("credibility", "").strip())
                if v.isdigit()
            ],
            key=int,
            default=rec.credibility or row.get("credibility", "").strip(),
        )
        rec.runs = _merge(rec.runs, run)
        rec.roots = _merge(rec.roots, row.get("root", ""))
        caveat = (row.get("caveat", "") or "").strip()
        if caveat and caveat != "-":
            rec.caveats = _merge(rec.caveats, caveat)
        rec.last_seen = today

    for name in read_run_entities(run_dir):
        key = entity_key(name)
        rec = entities.get(key)
        if rec is None:
            rec = EntityPage(key=key, name=name.strip(), first_seen=today)
            entities[key] = rec
            stats["entities_new"] += 1
        elif fold(name) != fold(rec.name):
            rec.aliases = _merge(rec.aliases, name.strip())
        rec.runs = _merge(rec.runs, run)
        rec.last_seen = today

    for row in read_run_claims(run_dir):
        text = (row.get("claim") or row.get("text") or "").strip()
        if not text:
            continue
        uid = claim_uid(run, row.get("claim_id", ""))
        if uid not in claims:
            stats["claims_new"] += 1
        # Upsert, not skip: the id is stable under wording changes on purpose, so a
        # re-ingest after phase 6 remediation must carry the corrected text into the
        # wiki. Skipping would freeze whatever 5.7 saw and quietly diverge from the
        # report. Pair edges keep pointing at the same id either way.
        claims[uid] = ClaimPage(
            id=uid,
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
                r.strip() for r in re.split(r"[;,]", row.get("roots", "")) if r.strip()
            ],
            ingested=today,
        )

    # Re-attach entities across the WHOLE store, not just this run's claims. Attachment
    # depends on which entities were known at the time, so computing it once at insert
    # made it order-dependent: a company first named in run 8 stayed invisible to the
    # claims of runs 1-7, which are exactly the ones 5.7 would pair against. Cheap —
    # a substring scan over claims already in memory — and it makes the wiki converge on
    # the same state regardless of the order runs were ingested in.
    for rec in claims.values():
        rec.entities = attach_entities(rec.text, entities)

    if dry_run:
        return stats

    d = ensure_wiki(wiki_root)
    save_sources(sources, wiki_root)
    save_entities(entities, wiki_root)
    save_claims(claims, wiki_root)
    for rec in sources.values():
        (d / rec.page).write_text(render_source_page(rec), encoding="utf-8")
    by_entity: dict[str, list[ClaimPage]] = {}
    for c in claims.values():
        for e in c.entities:
            by_entity.setdefault(e, []).append(c)
    for rec in entities.values():
        (d / rec.page).write_text(
            render_entity_page(
                rec, sorted(by_entity.get(rec.key, []), key=lambda c: c.as_of)
            ),
            encoding="utf-8",
        )
    for rec in claims.values():
        (d / rec.page).write_text(render_claim_page(rec), encoding="utf-8")
    (d / "INDEX.md").write_text(
        render_index(sources, entities, claims), encoding="utf-8"
    )

    # Receipt inside the run, so the phase gate has something to check. The wiki itself
    # lives outside the run directory, and a step whose only evidence is somewhere the
    # validator never looks is a step that quietly stops running.
    receipt = run_dir / ".verify" / "wiki_ingest.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(
        json.dumps(
            {"run": run, "ingested": today, "wiki": str(d), **stats},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--research-dir", required=True, type=Path)
    ap.add_argument(
        "--wiki-root", type=Path, default=None, help="override ~/.claude (tests)"
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="считать и напечатать, не писать"
    )
    args = ap.parse_args()

    d = args.research_dir
    if not d.is_dir():
        print(f"ERROR: not a directory: {d}")
        return 2
    if not (d / "claims.csv").is_file() and not (d / "sources.csv").is_file():
        print(
            f"ERROR: neither claims.csv nor sources.csv under {d} — run finish-up step 0 first"
        )
        return 2

    rows = read_run_claims(d)
    if rows:
        missing = [c for c in ("status", "as_of", "roots") if c not in rows[0]]
        if missing:
            # Not fatal — the wiki still gets the claim text and its run. But as_of and
            # roots are what stops a stale figure from reading as a contradiction in
            # 5.7, so a run missing them contributes claims that pair badly.
            print(
                f"WARNING: claims.csv без колонок {missing} — 5.7 будет сравнивать вслепую"
            )

    s = ingest(d, args.wiki_root, dry_run=args.dry_run)
    where = wiki_dir(args.wiki_root)
    prefix = "DRY-RUN — would write" if args.dry_run else "Wrote"
    print(
        f"{prefix} {where}: +{s['sources_new']} источников (уже было {s['sources_seen']}), "
        f"+{s['entities_new']} сущностей, +{s['claims_new']} утверждений"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
