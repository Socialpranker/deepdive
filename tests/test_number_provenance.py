"""Tests for scripts/check_number_provenance.py — fail-closed rule + circulation.

Every check here is paired with a control case that must stay green: a validator
that flags everything is as useless as one that flags nothing, and only the pair
proves which of the two we have.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import check_number_provenance as cnp  # noqa: E402

CLEAN_SOURCE = """---
id: s01
url: https://sec.gov/filing
type: Primary
root: own
origin_kind: filing
origin_url: https://sec.gov/filing
data_as_of: 2025-Q3
chain_len: 0
---

# Filing

> «Revenue reached 4.72 billion in the quarter.»
"""

UNTRACEABLE_SOURCE = """---
id: s02
url: https://contentfarm.example/post
type: General-media
root: unclear
origin_kind: unknown
origin_url: -
data_as_of: -
chain_len: 3
---

# Post

> «The market is worth 38.4 billion by 2030.»
"""


def make_run(
    tmp_path: Path, sources: dict[str, str], *, memo: str = "", ledger: str = ""
) -> Path:
    d = tmp_path / "run"
    (d / "sources").mkdir(parents=True)
    for name, text in sources.items():
        (d / "sources" / name).write_text(text, encoding="utf-8")
    if memo:
        (d / "memo.md").write_text(memo, encoding="utf-8")
    if ledger:
        (d / "claims.csv").write_text(ledger, encoding="utf-8")
    return d


def run(d: Path) -> cnp.Report:
    r = cnp.Report()
    sources = cnp.load_sources(d)
    cnp.check_fail_closed(d, sources, r)
    cnp.check_circulation(sources, r)
    cnp.check_ledger(d, r)
    return r


def test_clean_source_produces_no_findings(tmp_path):
    # Control: a fully-traceable number must not be flagged, or every later
    # assertion would pass for the wrong reason.
    d = make_run(tmp_path, {"01_filing.md": CLEAN_SOURCE})
    r = run(d)
    assert r.errors == []
    assert r.warnings == []


def test_untraceable_number_is_quarantined(tmp_path):
    d = make_run(tmp_path, {"02_farm.md": UNTRACEABLE_SOURCE})
    r = run(d)
    joined = " ".join(r.warnings)
    assert "origin_kind unknown" in joined
    assert "chain_len=3" in joined
    assert "no data_as_of" in joined


def test_quarantined_number_in_memo_is_an_error(tmp_path):
    d = make_run(
        tmp_path,
        {"02_farm.md": UNTRACEABLE_SOURCE},
        memo="# Memo\nМаркет будет 38.4 млрд [s02].\n",
    )
    r = run(d)
    assert any("memo.md cites s02" in e for e in r.errors)


def test_quarantined_number_outside_memo_is_only_a_warning(tmp_path):
    # Control for the rule above: quarantine limits WHERE a number may appear,
    # it does not delete the source.
    d = make_run(
        tmp_path,
        {"02_farm.md": UNTRACEABLE_SOURCE},
        memo="# Memo\nБез чисел, только рекомендация.\n",
    )
    r = run(d)
    assert r.errors == []
    assert r.warnings


def test_same_value_across_different_roots_flags_circulation(tmp_path):
    a = CLEAN_SOURCE.replace("id: s01", "id: s03").replace(
        "root: own", "root: study-smith-2024"
    )
    b = CLEAN_SOURCE.replace("id: s01", "id: s04").replace(
        "root: own", "root: acme-pr-2026"
    )
    d = make_run(tmp_path, {"03_a.md": a, "04_b.md": b})
    r = run(d)
    assert any("appears in" in w and "different" in w for w in r.warnings)


def test_same_value_same_root_is_not_circulation(tmp_path):
    # Control: two files retelling ONE material share a root — that is honest
    # provenance, already handled by the single-root rule, not a new finding.
    a = CLEAN_SOURCE.replace("id: s01", "id: s05").replace(
        "root: own", "root: acme-pr-2026"
    )
    b = CLEAN_SOURCE.replace("id: s01", "id: s06").replace(
        "root: own", "root: acme-pr-2026"
    )
    d = make_run(tmp_path, {"05_a.md": a, "06_b.md": b})
    r = run(d)
    assert not any("appears in" in w for w in r.warnings)


def test_years_are_not_treated_as_findings(tmp_path):
    src = CLEAN_SOURCE.replace(
        "Revenue reached 4.72 billion", "Published in 2024, revised 2025"
    )
    other = src.replace("id: s01", "id: s07").replace("root: own", "root: other-2024")
    d = make_run(tmp_path, {"01_a.md": src, "07_b.md": other})
    r = run(d)
    assert not any("appears in" in w for w in r.warnings)


def test_high_confidence_on_undated_number_is_an_error(tmp_path):
    ledger = (
        "claim_id,claim,status,confidence,as_of\n"
        'CL1,"Market reaches 38.4 billion",triangulated,high,unknown\n'
    )
    d = make_run(tmp_path, {"01_filing.md": CLEAN_SOURCE}, ledger=ledger)
    r = run(d)
    assert any("confidence=high on a number with no data date" in e for e in r.errors)


def test_dated_number_at_high_confidence_passes(tmp_path):
    # Control for the rule above.
    ledger = (
        "claim_id,claim,status,confidence,as_of\n"
        'CL1,"Market reaches 38.4 billion",triangulated,high,2025-Q3\n'
    )
    d = make_run(tmp_path, {"01_filing.md": CLEAN_SOURCE}, ledger=ledger)
    r = run(d)
    assert r.errors == []
