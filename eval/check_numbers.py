#!/usr/bin/env python3
"""
Number integrity: every number in a report sentence that cites [sNN] must occur
in that source's quotes.

The judge sees, under each sampled thesis, only the quote lines of the cited
source (score_run.source_quotes). A number missing there is the most common
defect the judge found on 2026-11-07 («124×» in sqlite-A, «+69%» in sqlite-C),
and it needs no model to catch. The same evidence lines are searched here, so
a fetcher's own notes or conclusions in the source file do not count as proof.

Citation scope: the sentence holding the number; if that sentence cites nothing,
the whole line (paragraph, list item, table row). [Nxx] resolves through
numbers.csv `sources`. Numbers in sentences without citations are not checked.

Status per unique (number, cited sources): ok — found in a cited source;
derived — the sentence cites an [Nxx] row of kind `derived` with this value
(check_number_arithmetic recomputes it), not scored; task — the number is a
parameter of the question itself (plan.md), not scored; missing. Unlike
check_quotes there is no half credit for a match in another source: on
sqlite-C «69%» matched an unrelated «68.8x» elsewhere. Such sources are listed
as `elsewhere`, a hint only. A report number with ≥2 significant digits may
round its source (15 for 14.7); a 1-digit one must match exactly, otherwise any
small number would match some decimal in a long source. A number marked
approximate (~, ≈, около, примерно) claims only its significant figures:
«~200x» is backed by 209.3x. Two numbers that both
carry a unit match only within one unit kind (% / times / bytes / time).

Usage:
    python eval/check_numbers.py --research-dir path/to/run
    python eval/check_numbers.py --research-dir path/to/run --json
    python eval/check_numbers.py --research-dir path/to/run --fail-on-missing  # exit 1, finish.py
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from check_quotes import find_report  # noqa: E402

SPACES = "    "
NUM = rf"\d{{1,3}}(?:[{SPACES}]\d{{3}})+(?!\d)|\d+(?:[.,]\d+)*"
SUFFIX = (r"x|×|%|п\.\s?п\.|[kKMGT]i?B|[КМГТ]Б|ms|мс|млн|тыс|M|K|k"
          r"|раз[а]?(?!\w)|-?кратн\w*")
NUM_RE = re.compile(rf"(?<![\w.,])({NUM})(?:\s?({SUFFIX}))?(?![\wа-яА-ЯёЁ])")
SCALE = {"k": 1e3, "K": 1e3, "тыс": 1e3, "M": 1e6, "млн": 1e6}


def unit_kind(suffix: str | None) -> str | None:
    if not suffix or suffix in SCALE:
        return None
    if suffix == "%" or suffix.startswith("п"):
        return "pct"
    if suffix in ("x", "×") or "раз" in suffix or "кратн" in suffix:
        return "times"
    if suffix in ("ms", "мс"):
        return "time"
    return "bytes"

REF = r"(?:s\d{2,3}|N\d+)"
CITE_GROUP_RE = re.compile(rf"\[({REF}(?:\s*[,;]\s*{REF})*)\]")
# Evidence only: «about twice as fast» backs a report's «~2x».
TIMES_WORDS = re.compile(r"\b(twice|thrice|вдвое|втрое)\b", re.IGNORECASE)
TIMES_VALUE = {"twice": 2.0, "thrice": 3.0, "вдвое": 2.0, "втрое": 3.0}
STRIP_RES = [
    re.compile(r"https?://\S+"),
    re.compile(r"`[^`]*`"),
    CITE_GROUP_RE,
    re.compile(r"\[\d+\]"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}\.\d{1,2}\.\d{4}\b"),
    re.compile(r"^\s*(?:[-*]\s+)?\d+[.)]\s"),  # list markers
]
APPROX_BEFORE = re.compile(r"(?:[~≈]|около|примерно|порядка|about|around|roughly)\s?$", re.IGNORECASE)
SENTENCE_SPLIT =re.compile(r"(?<=[.!?…])\s+(?=[«\"“(\[]?[A-ZА-ЯЁ0-9])")


def parse_number(raw: str, suffix: str | None) -> dict | None:
    """Interpretations of one token: version strings compare as text, the rest as values."""
    compact = re.sub(f"[{SPACES}]", "", raw)
    if compact.count(".") + compact.count(",") >= 2 and not re.search(f"[{SPACES}]", raw):
        return {"version": compact.replace(",", ".")}
    values = set()
    if "," in compact:
        head, tail = compact.split(",", 1)
        values.add(float(f"{head}.{tail}"))
        if len(tail) == 3:  # 1,000 — English thousands
            values.add(float(head + tail))
    else:
        values.add(float(compact))
    if suffix in SCALE:
        values |= {v * SCALE[suffix] for v in values}
    decimals = len(re.split(r"[.,]", compact, maxsplit=1)[1]) if re.search(r"[.,]", compact) else 0
    sig = len(re.sub(r"[.,]", "", compact).lstrip("0"))
    return {"values": values, "decimals": decimals, "sig": sig}


def numbers_in(text: str) -> list[dict]:
    for rx in STRIP_RES:
        text = rx.sub(" ", text)
    found = list(NUM_RE.finditer(text))
    out = []
    for i, m in enumerate(found):
        suffix = m.group(2)
        nxt = found[i + 1] if i + 1 < len(found) else None
        # 3–5x: the range's suffix belongs to both ends
        if not suffix and nxt and re.fullmatch(r"\s*[–—-]\s*", text[m.end():nxt.start()]):
            suffix = nxt.group(2)
        parsed = parse_number(m.group(1), suffix)
        if parsed:
            approx = bool(APPROX_BEFORE.search(text[max(0, m.start() - 12):m.start()]))
            out.append({"raw": m.group(0).strip(), "suffix": suffix, "approx": approx, **parsed})
    return out


def worth_checking(n: dict) -> bool:
    if "version" in n:
        return True
    if n["suffix"]:
        return True
    v = next(iter(n["values"]))
    if n["decimals"] == 0 and 1980 <= v <= 2035:
        return False  # years: mostly publication dates that live in frontmatter
    return n["sig"] >= 2


def matches(n: dict, evidence: list[dict]) -> bool:
    if "version" in n:
        return any(e.get("version") == n["version"] for e in evidence)
    tols = {v: tolerance(v, n) for v in n["values"]}
    kind = unit_kind(n["suffix"])
    for e in evidence:
        other = unit_kind(e.get("suffix"))
        if kind and other and kind != other:
            continue
        for ev in e.get("values", ()):
            for v, tol in tols.items():
                if abs(ev - v) <= tol + 1e-9 * max(abs(v), 1):
                    return True
    return False


def tolerance(v: float, n: dict) -> float:
    if n.get("approx"):
        # «~200x» claims one significant figure: 209.3x backs it.
        s = f"{v:.{n['decimals']}f}".replace(".", "")
        trailing = len(s) - len(s.rstrip("0"))
        return 0.5 * 10 ** (trailing - n["decimals"])
    return 0.5 * 10 ** -n["decimals"] if n["sig"] >= 2 else 0.0


def load_ncsv(research_dir: Path) -> dict[str, dict]:
    """num_id -> {sources, derived: parsed value or None}."""
    path = research_dir / "numbers.csv"
    if not path.is_file():
        return {}
    out = {}
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r.get("num_id"):
                continue
            derived = None
            if (r.get("kind") or "").strip() == "derived":
                derived = numbers_in(r.get("value") or "")
            out[r["num_id"]] = {"sources": re.findall(r"s\d{2,3}", r.get("sources") or ""),
                                "derived": derived}
    return out


def evidence_numbers(text: str) -> list[dict]:
    words = [{"raw": m.group(0), "suffix": "x", "values": {TIMES_VALUE[m.group(1).lower()]},
              "decimals": 0, "sig": 1} for m in TIMES_WORDS.finditer(text)]
    return numbers_in(text) + words


def source_titles(research_dir: Path) -> dict[str, str]:
    """sid -> title: the page's own words, «PostgreSQL 18 Documentation» backs «PG 18»."""
    out = {}
    for p in sorted((research_dir / "sources").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        sid = re.search(r"^id:\s*(s\d+)", text, re.MULTILINE)
        title = re.search(r"^title:\s*(.+)", text, re.MULTILINE)
        if title:
            out[sid.group(1) if sid else p.stem.split("_")[0]] = title.group(1)
    return out


def cites_in(text: str) -> list[str]:
    return [ref for group in CITE_GROUP_RE.findall(text) for ref in re.findall(REF, group)]


TASK_HEADING_RE = re.compile(r"^#+\s.*(context|контекст|вопрос|question|decision spec)", re.IGNORECASE)


def task_numbers(research_dir: Path) -> list[dict]:
    """Numbers stated by the task itself (pg-cdc «~50 таблиц»): not claims about sources.

    Only the question, the title and context/question/decision-spec sections:
    the hypotheses section of plan.md already guesses at source numbers.
    """
    plan = research_dir / "plan.md"
    if not plan.is_file():
        return []
    picked, in_section = [], False
    for ln in plan.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#"):
            in_section = bool(TASK_HEADING_RE.match(ln))
            if ln.startswith("# "):
                picked.append(ln)
            continue
        if in_section or ln.startswith("question:"):
            picked.append(ln)
    return [n for n in numbers_in("\n".join(picked)) if worth_checking(n)]


def report_units(report: str):
    """(line number, sentence, cites) for every body sentence.

    A table cell is a sentence of its own: the SQLite column cites one source,
    the DuckDB column another.
    """
    for no, line in enumerate(report.splitlines(), 1):
        if line.lstrip().startswith("#") or not line.strip():
            continue
        line_cites = cites_in(line)
        parts = line.strip().strip("|").split("|") if line.lstrip().startswith("|") else [line]
        for part in parts:
            for sentence in SENTENCE_SPLIT.split(part):
                yield no, sentence, cites_in(sentence) or line_cites


def check(research_dir: Path) -> dict:
    # Lazy: score_run imports this module at the top.
    from score_run import source_quotes

    report = find_report(research_dir)
    if report is None:
        return {"number_integrity": None, "note": "no dated report", "unmatched": []}
    titles = source_titles(research_dir)
    evidence = {sid: evidence_numbers("\n".join([titles.get(sid, ""), *lines]))
                for sid, lines in source_quotes(research_dir).items()}
    ncsv = load_ncsv(research_dir)
    task = task_numbers(research_dir)

    seen: dict[tuple, dict] = {}
    for no, sentence, cites in report_units(report.read_text(encoding="utf-8")):
        sids, derived = [], []
        for c in cites:
            if c.startswith("N"):
                row = ncsv.get(c, {})
                sids += row.get("sources", [])
                derived += row.get("derived") or []
            else:
                sids.append(c)
        sids = sorted(set(sids))
        if not sids:
            continue
        for n in filter(worth_checking, numbers_in(sentence)):
            key = (n["raw"], tuple(sids))
            if key in seen:
                if no not in seen[key]["lines"]:
                    seen[key]["lines"].append(no)
                continue
            row = {"number": n["raw"], "cites": list(sids), "lines": [no]}
            if any(matches(n, evidence.get(s, [])) for s in sids):
                row["status"] = "ok"
            elif matches(n, derived):
                row["status"] = "derived"
            elif matches({**n, "approx": False}, task):
                row["status"] = "task"
            else:
                row["status"] = "missing"
                row["elsewhere"] = [s for s, ev in evidence.items()
                                    if s not in sids and matches(n, ev)]
            seen[key] = row

    rows = list(seen.values())
    scored = [r for r in rows if r["status"] in ("ok", "missing")]
    ok = sum(r["status"] == "ok" for r in scored)
    return {
        "report": report.name,
        "number_integrity": round(ok / len(scored), 3) if scored else None,
        "checked": len(scored),
        "missing": len(scored) - ok,
        "derived": sum(r["status"] == "derived" for r in rows),
        "task": sum(r["status"] == "task" for r in rows),
        "unmatched": [r for r in rows if r["status"] == "missing"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--research-dir", required=True, type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on-missing", action="store_true", help="exit 1 if any number is missing")
    args = ap.parse_args()
    res = check(args.research_dir)
    code = 1 if args.fail_on_missing and res.get("missing") else 0
    if args.json:
        print(json.dumps(res, ensure_ascii=False))
        return code
    ni = res["number_integrity"]
    print(f"number_integrity = {'n/a' if ni is None else ni}  "
          f"(checked {res.get('checked', 0)}, missing {res.get('missing', 0)}, "
          f"derived {res.get('derived', 0)}, task {res.get('task', 0)})")
    for r in res["unmatched"]:
        hint = f"  (found in {'/'.join(r['elsewhere'])})" if r["elsewhere"] else ""
        print(f"  missing  {'/'.join(r['cites']):10} {r['number']:<14} "
              f"line {','.join(map(str, r['lines']))}{hint}")
    return code


if __name__ == "__main__":
    sys.exit(main())
