#!/usr/bin/env python3
"""
Build a run's sources.csv from the sources/NN_*.md frontmatter — deterministically.

sources/NN.md is the source of truth (one file per source, hand-written with quotes).
sources.csv is an index that check_citations.py, validate_structure.py and score_run.py
all read. Before this script, that index was assembled by hand each run — a grep|sed
hack that reinvents the column schema every time and drifts from what the readers
expect. This makes it one reproducible command.

Columns are emitted lowercase to match the CONTRACT the readers actually enforce
(validate_structure.py requires `url`,`title`; recommends `type`/`channel`;
check_citations.py reads `url`/`title`/`access`/`id`). The capitalized template in
references/source_scoring.md ("№,URL,Title,...") predates that contract — this script
is the one that reconciles them.

Usage:
    python scripts/build_sources_csv.py --research-dir research/<slug>
    python scripts/build_sources_csv.py --research-dir research/<slug> --check   # CI: fail if stale
    python scripts/build_sources_csv.py --lint sources/05_x.md sources/06_y.md      # fetcher: exit 1 on a bad enum
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from quiet import CAP_WARNINGS, capped  # noqa: E402
from runner.scoring import AXES, compute_total  # noqa: E402

# Order matters: url,title first (validate_structure REQUIRED), then the recommended
# and scoring columns. `file` lets a reader map a row back to its sources/NN.md.
# signal_type/value_score/access_state are appended at the end (optional per-run
# rubric extension, e.g. research/*/value_rubric.md) — new fields go last so existing
# readers keyed by column name (DictReader) are unaffected; runs without a rubric
# just emit empty strings for these three. discovery_path is read by score_claims.py
# (4th triangulation condition: distinct search paths).
COLUMNS = [
    "id",
    "url",
    "title",
    "type",
    "channel",
    "access",
    "author",
    "date",
    "credibility",
    "recency",
    "bias",
    "total",
    "caveat",
    "root",
    "used",
    "file",
    "signal_type",
    "value_score",
    "access_state",
    "discovery_path",
]
SOURCE_FILE_RE = re.compile(r"^\d{2,}_.+\.md$")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    # single-line `key: value` pairs only — nested blocks (hypothesis_evidence:) are skipped
    return dict(
        re.findall(r"^([a-z][a-z_]*):[ \t]*(.+?)[ \t]*$", parts[1], re.MULTILINE)
    )


def source_total(fm: dict[str, str]) -> str:
    """credibility + recency + bias, counted here: a typed total drifts from its axes.
    Without all three axes the written total is kept as is (archived runs); a
    non-numeric axis gives no total at all rather than the typed one."""
    if not all(k in fm for k in AXES):
        return _clean(fm.get("total", ""))
    try:
        return str(compute_total({k: float(_clean(fm[k])) for k in AXES}))
    except ValueError:
        return ""


def collect_rows(research_dir: Path) -> list[dict[str, str]]:
    sd = research_dir / "sources"
    rows: list[dict[str, str]] = []
    if not sd.is_dir():
        return rows
    for f in sorted(sd.glob("*.md")):
        fm = parse_frontmatter(f.read_text(encoding="utf-8"))
        if not fm.get("url"):
            continue  # no url → not a real source row (mirrors the readers)
        enums = normalize_enums(fm)
        row = {c: enums.get(c, fm.get(c, "")) for c in COLUMNS}
        row["total"] = source_total(fm)
        row["id"] = fm.get("id", f.stem)
        row["file"] = f"sources/{f.name}"
        rows.append(row)
    return rows


# Строгие enum'ы из source_scoring.md. Свободная форма в `type` ломает подсчёт
# «≥2 разных типа» в триангуляции: два синонима считаются двумя типами.
# Синонимы (full, free, docs) не угадываем: это решение того, кто читал источник.
ENUMS: dict[str, tuple[str, ...]] = {
    "type": ("Primary", "Academic", "Industry-media", "General-media", "Expert-blog", "Forum", "Other"),
    "caveat": ("-", "vendor", "self-reported"),
    "origin_kind": ("measurement", "registry", "filing", "survey", "model-estimate", "secondary", "unknown", "-"),
    # Общий словарь с eval/validate_structure.py ACCESS_VOCAB: два гейта не должны спорить.
    "access": ("OPEN", "PARTIAL", "PAYWALLED", "paywalled-abstract-only", "closed", "archive-restored", "GRAY-AREA-SOURCE"),
    # `-` пишет fetch_source.py, когда ни один уровень не взял страницу.
    "fetch_tier": ("webfetch", "http", "browser", "-"),
    "used": ("Y", "N"),
}
REQUIRED_ENUMS = {"type"}  # остальные поля не у каждого источника (числа, fetch)
DISPUTED_RE = re.compile(r"^disputed:s\d+$", re.IGNORECASE)


def _clean(raw: str) -> str:
    v = re.sub(r"\s+#.*$", "", raw or "").strip()
    return v.strip("\"'«»").strip()


def normalize_enum(key: str, raw: str) -> str:
    """Canonical spelling when the value is in the enum up to case/quotes/comment, else the
    cleaned value as written."""
    v = _clean(raw)
    if key == "caveat" and DISPUTED_RE.match(v):
        return v.lower()
    for allowed in ENUMS[key]:
        if v.lower() == allowed.lower():
            return allowed
    return v


def normalize_enums(fm: dict[str, str]) -> dict[str, str]:
    return {k: normalize_enum(k, fm[k]) for k in ENUMS if k in fm}


def _enum_ok(key: str, v: str) -> bool:
    return v in ENUMS[key] or (key == "caveat" and bool(DISPUTED_RE.match(v)))


def enum_violations(rows: list[dict[str, str]]) -> list[str]:
    out = []
    for r in rows:
        for key in ENUMS:
            v = r.get(key) or ""
            if not v and key not in REQUIRED_ENUMS:
                continue
            if not _enum_ok(key, v):
                out.append(f"{r['id']}: {key}={v or '(empty)'}")
    return out


def lint_files(files: list[Path]) -> list[str]:
    errors = []
    for f in files:
        fm = parse_frontmatter(f.read_text(encoding="utf-8")) if f.is_file() else {}
        if not fm:
            errors.append(f"{f}: no frontmatter" if f.is_file() else f"{f}: not a file")
            continue
        row = {"id": f.name, **normalize_enums(fm)}
        errors += [f"{v} — outside the enum in references/source_scoring.md" for v in enum_violations([row])]
    return errors


def render_csv(rows: list[dict[str, str]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--research-dir", type=Path)
    target.add_argument(
        "--lint",
        nargs="+",
        type=Path,
        metavar="FILE",
        help="check enum fields of freshly written sources/NN.md; exit 1 on any; writes nothing",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if sources.csv is stale (CI); do not write",
    )
    ap.add_argument("--verbose", action="store_true", help="print every warning, not the first few")
    args = ap.parse_args()

    if args.lint and args.check:
        ap.error("--check needs --research-dir, not --lint")
    if args.lint:
        errors = lint_files(args.lint)
        for e in errors:
            print(f"ERROR: {e}")
        if not errors:
            print(f"OK — {len(args.lint)} source file(s), enums valid")
        return 1 if errors else 0

    d = args.research_dir
    if not d.is_dir():
        print(f"ERROR: not a directory: {d}")
        return 2

    rows = collect_rows(d)
    if not rows:
        print(f"ERROR: no sources with a 'url' found under {d}/sources/")
        return 2

    # Предупреждение, не отказ: в старых прогонах словарь шире задокументированного,
    # и ронять их сборку (а с ней finish.py) задним числом дороже, чем показать
    # расхождение. Отказ — в --lint, который fetcher гоняет сразу после записи.
    warns = (f"WARN: {b} — outside the enum; triangulation counts types by value" for b in enum_violations(rows))
    for line in capped(warns, CAP_WARNINGS, args.verbose):
        print(line)

    content = render_csv(rows)
    out = d / "sources.csv"

    if args.check:
        current = out.read_text(encoding="utf-8") if out.is_file() else ""
        if current != content:
            print(
                f"sources.csv is stale — run: python scripts/build_sources_csv.py --research-dir {d}"
            )
            return 1
        print(f"OK — sources.csv up to date ({len(rows)} sources)")
        return 0

    out.write_text(content, encoding="utf-8")
    print(f"Wrote {out}  ({len(rows)} sources)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
