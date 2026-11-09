#!/usr/bin/env python3
"""
Claim status and confidence ceiling computed from sources.csv, not typed by the model.

Audit of 70 real runs: 18 claims marked `triangulated` on fewer than 3 sources, 282
`high` on a single source, 10 claims counting the same URL twice as two legs. The
rules in references/source_scoring.md were right; the model applying them was not.
This script applies them by counting:

  legs      cited sources minus thin ones (validate_phases.source_is_thin) and minus
            total < 8 (credibility+recency+bias; no total = no verdict), one leg
            per normalized URL — two files of one document are one voice
  status    contested (strong dissent) > triangulated (>=3 legs, >=2 types, >=2 roots,
            >=2 discovery paths) > weak (<3 legs) > single-type > single-root >
            single-path. `contradicted` / `data-insufficient` are content verdicts
            and are kept when the model chose them.
  ceiling   empirical: high only if triangulated AND a primary leg; weak -> low;
            everything else -> medium. documentary (`claim_class`: "document
            X says Y") -> high on one primary leg, the document is its own proof.
            caveat vendor/self-reported caps at medium, disputed:sNN at low.
  atomicity a claim with `;` or two sentences is two claims — split it.

Missing root / discovery_path counts as one shared unknown value (fail-closed: an
independence nobody recorded is not independence).
root `own` is a class: every own source is a separate root. `unclear` is not a root.

Usage:
    python scripts/score_claims.py --research-dir <run>            # report
    python scripts/score_claims.py --research-dir <run> --write    # rewrite claims.csv
    python scripts/score_claims.py --research-dir <run> --strict   # exit 1 on mismatch
Writes .verify/claim_scores.json either way.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import validate_phases as vp  # noqa: E402
from quiet import CAP_ERRORS, capped  # noqa: E402
from runner.wiki import canonical_url  # noqa: E402

CONF_RANK = {"low": 0, "medium": 1, "high": 2}
CONTENT_STATUSES = {"contradicted", "data-insufficient"}
# Sentence break = terminal punctuation, space, capital. The lookbehind list keeps
# abbreviations ("e.g. Apple", "т. е. Минпросвещения") from splitting a claim.
ABBREV = r"(?<!\be\.g)(?<!\bi\.e)(?<!\bvs)(?<!\bInc)(?<!\bNo)(?<!\bDr)(?<!\bSt)(?<!\bт\. е)(?<!\bт\.е)(?<!\bг)(?<!\bст)"
SENTENCE_BREAK_RE = re.compile(ABBREV + r"[.!?]\s+(?=[A-ZА-ЯЁ])")


def sid(key: str) -> str:
    return "s" + key.zfill(2)


def field(src: dict[str, str], key: str) -> str:
    """Empty counts as one shared unknown — see module docstring."""
    return (src.get(key) or "").strip() or "?"


def root_key(i: str, src: dict[str, str]) -> str | None:
    """`own` is a class, not an id: each own source is its own root. `unclear` is no
    root at all — unknown provenance confirms no independence (source_scoring.md)."""
    root = field(src, "root")
    low = root.lower()
    if low == "own":
        return f"own:{i}"
    if low == "unclear":
        return None
    return root


def source_key(row: dict[str, str]) -> str | None:
    m = vp.SOURCE_ID_FILE_RE.match(Path(row.get("file") or "").name)
    return vp._norm_source_id(m.group(1) if m else row.get("id") or "")


def cited_ids(cell: str) -> list[str]:
    keys = (vp._norm_source_id(t) for t in vp.SOURCE_ID_SPLIT_RE.split(cell or ""))
    return list(dict.fromkeys(k for k in keys if k is not None))


def is_compound(claim: str) -> bool:
    text = claim.strip().rstrip(".!? ")
    return ";" in text or bool(SENTENCE_BREAK_RE.search(text))


def _int(v: str) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def is_primary(src: dict[str, str]) -> bool:
    return field(src, "type") == "Primary" and _int(src.get("credibility")) >= 5


LOW_TOTAL = 8  # rules.md: no conclusions on sources with total < 8


def is_low_total(src: dict[str, str]) -> bool:
    try:
        return float((src.get("total") or "").strip()) < LOW_TOTAL
    except ValueError:
        return False  # no total is no verdict


def low_total(by_id: dict[str, dict[str, str]]) -> set[str]:
    return {i for i, s in by_id.items() if is_low_total(s)}


def is_strong_dissent(src: dict[str, str]) -> bool:
    return field(src, "type") == "Primary" or _int(src.get("credibility")) >= 4


def url_groups(by_id: dict[str, dict[str, str]]) -> list[list[str]]:
    """Source ids grouped by document, each group sorted by id. Sources without a URL
    are left out: no URL is no evidence of sameness."""
    groups: dict[str, list[str]] = {}
    for i in sorted(by_id, key=int):
        url = canonical_url(by_id[i].get("url") or "")
        if url:
            groups.setdefault(url, []).append(i)
    return list(groups.values())


def score(
    claim: dict[str, str],
    by_id: dict[str, dict[str, str]],
    thin: set[str],
    keeper: dict[str, str],
) -> tuple[dict, dict[str, str]]:
    """-> (result, the ledger cells the script owns)."""
    unknown: list[str] = []
    kept: list[str] = []
    dup_of: dict[str, str] = {}
    for i in cited_ids(claim.get("sources", "")):
        if i not in by_id:
            unknown.append(i)
            continue
        # One id per document, the same one in every claim (lowest of its URL group):
        # keeping "whichever came first in this cell" left different survivors in
        # different claims, so merging the files broke some citations.
        k = keeper.get(i, i)
        if k != i:
            dup_of[i] = k
        if k not in kept:
            kept.append(k)
    leg_ids = [i for i in kept if i not in thin]
    legs = [by_id[i] for i in leg_ids]
    n = len(legs)
    types = {field(s, "type") for s in legs}
    roots = {root_key(i, by_id[i]) for i in leg_ids} - {None}
    paths = {field(s, "discovery_path") for s in legs}
    primary = any(is_primary(s) for s in legs)

    model_status = (claim.get("status") or "").strip().lower()
    if model_status in CONTENT_STATUSES:
        status = model_status
    elif any(
        is_strong_dissent(by_id[i])
        for i in cited_ids(claim.get("dissent", ""))
        if i in by_id and not is_low_total(by_id[i])
    ):
        status = "contested"
    elif n >= 3 and len(types) >= 2 and len(roots) >= 2 and len(paths) >= 2:
        status = "triangulated"
    elif n < 3:
        status = "weak"
    elif len(types) < 2:
        status = "single-type"
    elif len(roots) < 2:
        status = "single-root"
    else:
        status = "single-path"

    documentary = (claim.get("claim_class") or "").strip().lower() == "documentary"
    if documentary:
        ceiling = "high" if primary else ("medium" if n else "low")
    elif status == "triangulated":
        ceiling = "high" if primary else "medium"
    elif status in CONTENT_STATUSES | {"weak"}:
        ceiling = "low"
    else:
        ceiling = "medium"
    caveat = (claim.get("source_caveat") or "-").strip().lower()
    if caveat.startswith("disputed"):
        ceiling = "low"
    elif caveat in {"vendor", "self-reported"} and ceiling == "high":
        ceiling = "medium"

    model_conf = (claim.get("confidence") or "").strip().lower()
    conf = model_conf if CONF_RANK.get(model_conf, 99) <= CONF_RANK[ceiling] else ceiling

    violations = []
    if unknown:
        violations.append(f"cites {', '.join(map(sid, unknown))} absent from sources.csv")
    if dup_of:
        violations.append(
            "duplicate of a lower id (same URL): "
            + ", ".join(f"{sid(a)}={sid(b)}" for a, b in dup_of.items())
        )
    if model_status != status:
        violations.append(f"status {model_status or '(empty)'} -> {status}")
    if model_conf != conf:
        violations.append(f"confidence {model_conf or '(empty)'} -> {conf} (ceiling {ceiling})")
    if is_compound(claim.get("claim", "")):
        violations.append("compound claim — split into atomic rows")

    cited = [by_id[i] for i in kept]
    fill = {
        "sources": ";".join(map(sid, kept + unknown)),
        "source_types": ";".join(field(s, "type") for s in cited),
        "roots": ";".join(field(s, "root") for s in cited),
        "paths": ";".join(field(s, "discovery_path") for s in cited),
        "primary_source": "Y" if primary else "N",
        "status": status,
        "confidence": conf,
    }
    result = {
        "claim_id": (claim.get("claim_id") or "").strip(),
        "class": "documentary" if documentary else "empirical",
        "legs": n,
        "status": status,
        "ceiling": ceiling,
        "confidence": conf,
        "violations": violations,
    }
    return result, fill


def load(d: Path) -> tuple[list[str], list[dict[str, str]], dict[str, dict[str, str]]]:
    claims_p, sources_p = d / "claims.csv", d / "sources.csv"
    if not claims_p.is_file():
        raise SystemExit(f"ERROR: no claims.csv in {d} — nothing to score")
    if not sources_p.is_file():
        raise SystemExit(f"ERROR: no sources.csv in {d} — run scripts/build_sources_csv.py first")
    reader = csv.DictReader(claims_p.read_text(encoding="utf-8").splitlines())
    header = list(reader.fieldnames or [])
    why = vp.header_violation(header, vp.CLAIMS_CORE, vp.CLAIMS_OPTIONAL)
    if why:
        raise SystemExit(f"ERROR: claims.csv off-contract: {why}")
    claims = list(reader)
    rows = csv.DictReader(sources_p.read_text(encoding="utf-8").splitlines())
    by_id = {k: row for row in rows if (k := source_key(row)) is not None}
    return header, claims, by_id


def render_claims(header: list[str], claims: list[dict[str, str]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(claims)
    return buf.getvalue()


def run(d: Path, *, write: bool) -> tuple[list[dict], list[list[str]]]:
    header, claims, by_id = load(d)
    thin = set(vp.collect_thin_sources(d)[0]) | low_total(by_id)
    groups = url_groups(by_id)
    keeper = {i: g[0] for g in groups for i in g}
    scored = [score(c, by_id, thin, keeper) for c in claims]
    if write:
        for c, (_, fill) in zip(claims, scored, strict=True):
            c.update(fill)
        (d / "claims.csv").write_text(render_claims(header, claims), encoding="utf-8")
        # after the rewrite only what the script cannot fix is left
        scored = [score(c, by_id, thin, keeper) for c in claims]
    results = [r for r, _ in scored]
    dups = [list(map(sid, g)) for g in groups if len(g) > 1]
    (d / ".verify").mkdir(exist_ok=True)
    (d / ".verify" / "claim_scores.json").write_text(
        json.dumps({"results": results, "duplicate_urls": dups}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results, dups


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--research-dir", required=True, type=Path)
    ap.add_argument(
        "--write",
        action="store_true",
        help="rewrite sources/source_types/roots/paths/primary_source/status/confidence",
    )
    ap.add_argument("--strict", action="store_true", help="exit 1 on any violation")
    ap.add_argument("--verbose", action="store_true", help="print every violation, not the first few")
    args = ap.parse_args()
    results, dups = run(args.research_dir, write=args.write)

    bad = [r for r in results if r["violations"]]
    lines = [f"  {r['claim_id']}: " + "; ".join(r["violations"]) for r in bad]
    lines += [f"  sources {', '.join(g)} are one URL — keep {g[0]}, merge the rest into it" for g in dups]
    for line in capped(lines, CAP_ERRORS, args.verbose):
        print(line)
    print(
        f"{len(results)} claims, {len(bad)} with violations, {len(dups)} duplicate-URL groups"
        + (" (claims.csv rewritten)" if args.write else "")
    )
    return 1 if args.strict and (bad or dups) else 0


if __name__ == "__main__":
    sys.exit(main())
