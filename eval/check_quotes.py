#!/usr/bin/env python3
"""
Quote integrity: every verbatim quote the report attributes to a source must
actually occur in some sources/*.md.

check_citations.py only proves a URL is alive; it cannot see a quote the
synthesizer invented or "remembered" (D2 cited «intricate approach» [s12] while
no source file contains it). This is the deterministic guard for that.

A quote counts when it is wrapped in «…», “…” or "…", has ≥2 words, and a [sNN]
citation follows it in the same sentence. A quote with any Cyrillic word cited only
to English sources is a paraphrase (the report's own wording of a claim), not a
verbatim quote — reported as `paraphrase`, not scored.
Ellipsis inside a quote splits it; every fragment must be found.

Usage:
    python eval/check_quotes.py --research-dir path/to/run
    python eval/check_quotes.py --research-dir path/to/run --json
"""

import argparse
import json
import re
import sys
from pathlib import Path

QUOTE_RE = re.compile(r"«([^»]{3,400})»|“([^”]{3,400})”|\"([^\"\n]{3,400})\"")
CITE_RE = re.compile(r"\[(s\d{2,3})\]")
# Citation must sit in the same sentence as the quote: no ". " / newline between.
SAME_SENTENCE = re.compile(r"^[^\n]*?(?<![.!?])(?:\[s\d{2,3}\])")
REPORT_SKIP = {"plan.md", "readout.md", "memo.md", "outline.md", "state.md", "README.md",
               "application.md", "refresh_targets.md"}


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[«»“”„\"'‘’`*_>]", "", text)
    text = text.replace("ё", "е")
    return re.sub(r"\s+", " ", text).strip(" .,;:")


def find_report(research_dir: Path) -> Path | None:
    dated = [p for p in research_dir.glob("*.md")
             if re.match(r"\d{4}-\d{2}-\d{2}_", p.name) and p.name not in REPORT_SKIP]
    return max(dated, key=lambda p: p.name) if dated else None


def load_sources(research_dir: Path) -> dict[str, tuple[str, str]]:
    """sid -> (normalized body, language)."""
    out = {}
    for p in sorted((research_dir / "sources").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        sid = re.search(r"^id:\s*(s\d+)", text, re.MULTILINE)
        lang = re.search(r"^language:\s*(\w+)", text, re.MULTILINE)
        key = sid.group(1) if sid else p.stem.split("_")[0]
        out[key] = (normalize(text), lang.group(1) if lang else "")
    return out


def extract_quotes(report: str) -> list[dict]:
    found = []
    for m in QUOTE_RE.finditer(report):
        quote = next(g for g in m.groups() if g)
        if len(quote.split()) < 2:
            continue
        tail = report[m.end():m.end() + 200]
        if not SAME_SENTENCE.match(tail):
            continue
        cites = CITE_RE.findall(tail.split("\n", 1)[0].split(". ", 1)[0])
        if cites:
            found.append({"quote": quote, "cites": cites})
    return found


def check(research_dir: Path) -> dict:
    report = find_report(research_dir)
    if report is None:
        return {"quote_integrity": None, "note": "no dated report", "quotes": []}
    sources = load_sources(research_dir)
    corpus = " ".join(body for body, _ in sources.values())
    rows = []
    for q in extract_quotes(report.read_text(encoding="utf-8")):
        fragments = [normalize(f) for f in re.split(r"…|\.\.\.", q["quote"]) if normalize(f)]
        langs = {sources.get(c, ("", ""))[1] for c in q["cites"]}
        paraphrase = bool(re.search(r"[а-яА-ЯёЁ]", q["quote"])) and langs == {"en"}
        in_cited = all(any(f in sources.get(c, ("", ""))[0] for c in q["cites"]) for f in fragments)
        anywhere = in_cited or all(f in corpus for f in fragments)
        status = "paraphrase" if paraphrase and not anywhere else (
            "ok" if in_cited else "wrong_source" if anywhere else "missing")
        rows.append({**q, "status": status})
    scored = [r for r in rows if r["status"] != "paraphrase"]
    # wrong_source still exists in the corpus — half credit, the attribution is off.
    credit = sum(1.0 if r["status"] == "ok" else 0.5 if r["status"] == "wrong_source" else 0.0
                 for r in scored)
    return {
        "report": report.name,
        "quote_integrity": round(credit / len(scored), 3) if scored else None,
        "checked": len(scored),
        "missing": sum(r["status"] == "missing" for r in rows),
        "wrong_source": sum(r["status"] == "wrong_source" for r in rows),
        "paraphrase": sum(r["status"] == "paraphrase" for r in rows),
        "quotes": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--research-dir", required=True, type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    res = check(args.research_dir)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    qi = res["quote_integrity"]
    print(f"quote_integrity = {'n/a' if qi is None else qi}  "
          f"(checked {res.get('checked', 0)}, missing {res.get('missing', 0)}, "
          f"wrong_source {res.get('wrong_source', 0)}, paraphrase {res.get('paraphrase', 0)})")
    for r in res["quotes"]:
        if r["status"] != "ok":
            print(f"  {r['status']:12} {'/'.join(r['cites'])}  «{r['quote'][:90]}»")
    return 0


if __name__ == "__main__":
    sys.exit(main())
