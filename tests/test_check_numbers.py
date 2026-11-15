"""check_numbers: a number in a cited sentence must be in that source's quotes.

The judge found on 2026-11-07 that the main defect of reports is a number absent
from the cited source («124×» sqlite-A, «+69%» sqlite-C).
"""

import importlib.util
import sys
from pathlib import Path

import pytest

EVAL = Path(__file__).resolve().parent.parent / "eval"
sys.path.insert(0, str(EVAL))
SPEC = importlib.util.spec_from_file_location("check_numbers", EVAL / "check_numbers.py")
cn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cn)

QUOTES = "# Цитаты\n\n"


def make_run(tmp_path: Path, report: str, sources: dict[str, str], plan: str = "", ncsv: str = "") -> Path:
    run = tmp_path / "run"
    (run / "sources").mkdir(parents=True)
    for i, (sid, body) in enumerate(sources.items(), 1):
        (run / "sources" / f"{i:02d}_{sid}.md").write_text(
            f"---\nid: {sid}\ntitle: Source {sid}\n---\n\n{body}\n", encoding="utf-8")
    (run / "2026-11-07_decision.md").write_text(f"# Report\n\n{report}\n", encoding="utf-8")
    if plan:
        (run / "plan.md").write_text(plan, encoding="utf-8")
    if ncsv:
        (run / "numbers.csv").write_text(ncsv, encoding="utf-8")
    return run


def statuses(run: Path) -> dict[str, str]:
    res = cn.check(run)
    missing = {r["number"] for r in res["unmatched"]}
    return {"missing": missing, "score": res["number_integrity"], "res": res}


def test_found_and_missing_numbers_score_as_a_share(tmp_path):
    run = make_run(tmp_path, "- SQLite wins 14.7x on indexed lookups, 124x on joins [s01].",
                   {"s01": QUOTES + "> «indexed 14,7× faster»"})
    s = statuses(run)
    assert s["missing"] == {"124x"}
    assert s["score"] == 0.5


def test_versions_compare_as_text(tmp_path):
    run = make_run(tmp_path, "- Compared SQLite 3.41.2 with DuckDB 0.9.1 [s01].",
                   {"s01": QUOTES + "> SQLite 3.41.2 against DuckDB 1.0"})
    assert statuses(run)["missing"] == {"0.9.1"}


def test_range_suffix_applies_to_both_ends(tmp_path):
    run = make_run(tmp_path, "- Migration gave 3–5x on analytics [s01].",
                   {"s01": QUOTES + 'Gain: "3-5 times faster".'})
    assert statuses(run)["score"] == 1.0


def test_fetcher_notes_outside_quote_sections_are_not_evidence(tmp_path):
    body = "Данные: SQLite 3.41.2.\n\n" + QUOTES + "> «one or two orders of magnitude»"
    run = make_run(tmp_path, "- Benchmark ran SQLite 3.41.2 [s01].", {"s01": body})
    assert statuses(run)["missing"] == {"3.41.2"}


def test_prose_line_inside_quote_section_is_evidence(tmp_path):
    run = make_run(tmp_path, "- The binary is 750 kB against 20 MB [s01].",
                   {"s01": QUOTES + 'Size: SQLite "750 kB compiled"; DuckDB "a 20MB binary".'})
    assert statuses(run)["score"] == 1.0


def test_approximate_number_claims_only_its_significant_figures(tmp_path):
    src = {"s01": QUOTES + "| GROUP BY | 209.3x |\n| COUNT | 8.7x |"}
    assert statuses(make_run(tmp_path, "- Gap from ~9x to ~200x [s01].", src))["score"] == 1.0
    exact = make_run(tmp_path / "b", "- Gap is 200x [s01].", src)
    assert statuses(exact)["missing"] == {"200x"}


def test_percent_does_not_match_times(tmp_path):
    run = make_run(tmp_path, "- Bundle grew 69% [s01].", {"s01": QUOTES + "> range filter 68.8x"})
    assert statuses(run)["missing"] == {"69%"}


def test_table_cells_keep_their_own_citations(tmp_path):
    report = "| Model | B-tree, pages of 1024 [s01] | batches of 2048 values [s02] |"
    run = make_run(tmp_path, report, {"s01": QUOTES + "> 2048", "s02": QUOTES + "> 1024"})
    assert statuses(run)["missing"] == {"1024", "2048"}


def test_grouped_citation_brackets_are_parsed(tmp_path):
    run = make_run(tmp_path, "- Vectors of 2048 values [s01, s02].",
                   {"s01": QUOTES + "> nothing", "s02": QUOTES + "> 2048 values"})
    assert statuses(run)["score"] == 1.0


def test_number_without_citation_is_not_checked(tmp_path):
    run = make_run(tmp_path, "- Somebody said 938x once.", {"s01": QUOTES + "> nothing"})
    assert statuses(run)["score"] is None


NCSV = ("num_id,value,unit,claim_id,sources,kind,formula,inputs,as_of,group,note\n"
        "N12,44,MB,C7,s01,verbatim,-,-,unknown,-,after\n"
        "N13,69.2,%,C7,s01,derived,(b-a)/a*100,a=26; b=44,unknown,-,growth\n")


def test_declared_derived_number_is_not_scored(tmp_path):
    src = {"s01": QUOTES + "Bundle grew from 26 MB to 44 MB."}
    s = statuses(make_run(tmp_path, "- Bundle grew 69% [N13].", src, ncsv=NCSV))
    assert s["res"]["derived"] == 1 and s["score"] is None
    wrong_ref = statuses(make_run(tmp_path / "b", "- Bundle grew 69% [N12].", src, ncsv=NCSV))
    assert wrong_ref["missing"] == {"69%"}


def test_task_parameter_from_plan_is_not_scored(tmp_path):
    plan = "# Plan\n\n## 0. User context\nOne Postgres, ~50 таблиц.\n\n## 2. Гипотезы\nH1: 124x\n"
    report = "- For 50 tables a custom consumer is out; joins gain 124x [s01]."
    s = statuses(make_run(tmp_path, report, {"s01": QUOTES + "> nothing"}, plan=plan))
    assert s["res"]["task"] == 1
    assert s["missing"] == {"124x"}  # hypotheses are not task parameters


def test_source_title_is_evidence(tmp_path):
    run = make_run(tmp_path, "- Logical replication in PG 18 skips DDL [s01].", {"s01": QUOTES + "> DDL"})
    (run / "sources" / "01_s01.md").write_text(
        "---\nid: s01\ntitle: Restrictions, PostgreSQL 18 Documentation\n---\n\n# Цитаты\n> DDL\n",
        encoding="utf-8")
    assert statuses(run)["score"] == 1.0


RESEARCH = Path.home() / "Downloads/Code/research"


@pytest.mark.skipif(not (RESEARCH / "sqlite-vs-duckdb-analytics-C").is_dir(), reason="bench runs absent")
def test_controls_on_real_sqlite_runs():
    missing = {x: {r["number"] for r in cn.check(RESEARCH / f"sqlite-vs-duckdb-analytics-{x}")["unmatched"]}
               for x in "ABC"}
    assert {"124-кратное", "3.41.2", "0.9.1"} <= missing["A"]
    assert "69%" in missing["C"]
    assert not missing["B"]  # «750 kB» sits in a prose line of s05 and must be found
