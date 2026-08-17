"""Tests for scripts/check_number_arithmetic.py — recompute, shares, fail-closed.

Every check is paired with a control case that must stay green. A validator that
flags a correct computation is worse than none: it trains the run to delete the
column instead of fixing the number.
"""

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import check_number_arithmetic as cna  # noqa: E402

HEADER = "num_id,value,unit,kind,formula,inputs,group,claim_id,sources,as_of"


def rows_from(*lines: str) -> list[dict[str, str]]:
    return list(csv.DictReader([HEADER, *lines]))


def run(*lines: str, claim_ids: set[str] | None = None):
    r = cna.Report()
    result = cna.check_rows(rows_from(*lines), claim_ids or set(), r)
    return r, result


# --- derived: recompute --------------------------------------------------------

GOOD_DERIVED = "N1,34.2,%,derived,a/b*100,a=1710[s03];b=5000[s03],-,CL4,s03,2026-Q1"
BAD_DERIVED = "N1,43.2,%,derived,a/b*100,a=1710[s03];b=5000[s03],-,CL4,s03,2026-Q1"


def test_correct_derived_number_passes():
    r, result = run(GOOD_DERIVED)
    assert r.errors == []
    assert result["recomputed"] == 1
    assert result["mismatches"] == []


def test_transposed_digits_are_caught():
    """The control above and this differ only in the stated value."""
    r, result = run(BAD_DERIVED)
    assert len(result["mismatches"]) == 1
    assert result["mismatches"][0]["num_id"] == "N1"
    assert any("recomputed" in e for e in r.errors)


def test_tolerance_admits_rounding():
    # 1710/5000*100 = 34.2 exactly; a report rounding to 34 is not a defect.
    r, _ = run("N1,34,%,derived,a/b*100,a=1710[s03];b=5000[s03],-,CL4,s03,2026-Q1")
    assert r.errors == []


def test_tolerance_does_not_admit_a_real_error():
    r, _ = run("N1,36,%,derived,a/b*100,a=1710[s03];b=5000[s03],-,CL4,s03,2026-Q1")
    assert any("recomputed" in e for e in r.errors)


def test_derived_without_formula_is_an_error():
    r, _ = run("N1,34.2,%,derived,-,-,-,CL4,s03,2026-Q1")
    assert any("without a formula" in e for e in r.errors)


def test_derived_without_inputs_is_an_error():
    r, _ = run("N1,34.2,%,derived,a/b*100,-,-,CL4,s03,2026-Q1")
    assert any("without usable inputs" in e for e in r.errors)


def test_division_by_zero_reports_instead_of_crashing():
    r, _ = run("N1,34.2,%,derived,a/b,a=1710[s03];b=0[s03],-,CL4,s03,2026-Q1")
    assert any("could not be evaluated" in e for e in r.errors)


def test_growth_rate_formula():
    # (120-80)/80*100 = 50
    r, _ = run("N2,50,%,derived,(b-a)/a*100,a=80[s01];b=120[s02],-,CL1,s01;s02,2026-Q1")
    assert r.errors == []


# --- formula safety -----------------------------------------------------------


def test_function_calls_are_not_evaluated():
    assert cna.safe_eval("len(a)", {"a": 2.0}) is None


def test_dunder_access_is_not_evaluated():
    assert cna.safe_eval("a.__class__", {"a": 2.0}) is None


def test_import_expression_is_not_evaluated():
    assert cna.safe_eval("__import__('os').system('true')", {}) is None


def test_undeclared_name_is_not_evaluated():
    assert cna.safe_eval("a/b", {"a": 1.0}) is None


def test_plain_arithmetic_still_evaluates():
    """Control for the four tests above: the allowed subset must work."""
    assert cna.safe_eval("(a+b)/2", {"a": 3.0, "b": 5.0}) == 4.0
    assert cna.safe_eval("-a", {"a": 3.0}) == -3.0
    assert cna.safe_eval("2**3", {}) == 8.0


def test_absurd_exponent_is_refused():
    assert cna.safe_eval("2**a", {"a": 1e6}) is None


# --- shares -------------------------------------------------------------------

SHARE_OK = (
    "N1,61,%,share,-,-,browsers,CL1,s01,2026-Q1",
    "N2,25,%,share,-,-,browsers,CL1,s01,2026-Q1",
    "N3,14,%,share,-,-,browsers,CL1,s01,2026-Q1",
)


def test_shares_that_make_a_whole_pass():
    r, result = run(*SHARE_OK)
    assert r.errors == []
    assert result["share_flags"] == []


def test_shares_that_do_not_sum_to_100_are_caught():
    lines = list(SHARE_OK)
    lines[2] = "N3,9,%,share,-,-,browsers,CL1,s01,2026-Q1"
    r, result = run(*lines)
    assert len(result["share_flags"]) == 1
    assert result["share_flags"][0]["group"] == "browsers"
    assert any("sum to" in e for e in r.errors)


def test_share_without_group_is_an_error():
    r, _ = run("N1,61,%,share,-,-,-,CL1,s01,2026-Q1")
    assert any("without a group" in e for e in r.errors)


def test_separate_groups_are_summed_separately():
    r, _ = run(
        *SHARE_OK,
        "N4,70,%,share,-,-,os,CL2,s02,2026-Q1",
        "N5,30,%,share,-,-,os,CL2,s02,2026-Q1",
    )
    assert r.errors == []


# --- hygiene ------------------------------------------------------------------


def test_unknown_kind_is_an_error():
    r, _ = run("N1,34.2,%,estimate,-,-,-,CL4,s03,2026-Q1")
    assert any("is not one of" in e for e in r.errors)


def test_duplicate_num_id_is_an_error():
    r, _ = run(GOOD_DERIVED, GOOD_DERIVED)
    assert any("duplicate num_id" in e for e in r.errors)


def test_missing_sources_is_an_error():
    r, _ = run("N1,4.5,$B,verbatim,-,-,-,CL7,-,2025-Q4")
    assert any("no sources" in e for e in r.errors)


def test_verbatim_with_formula_warns_but_does_not_fail():
    r, _ = run("N1,4.5,$B,verbatim,a/b,a=9[s01];b=2[s01],-,CL7,s01,2025-Q4")
    assert r.errors == []
    assert any("kind=verbatim" in w for w in r.warnings)


def test_input_without_citation_warns_only():
    r, _ = run("N1,34.2,%,derived,a/b*100,a=1710;b=5000,-,CL4,s03,2026-Q1")
    assert r.errors == []
    assert any("no [sNN]" in w for w in r.warnings)


def test_unresolvable_claim_id_warns():
    r, _ = run(GOOD_DERIVED, claim_ids={"CL1", "CL2"})
    assert r.errors == []
    assert any("not in claims.csv" in w for w in r.warnings)


def test_known_claim_id_is_silent():
    r, _ = run(GOOD_DERIVED, claim_ids={"CL4"})
    assert r.warnings == []


# --- number parsing -----------------------------------------------------------


def test_human_number_formats():
    assert cna.to_float("1 710") == 1710.0
    assert cna.to_float("1,710") == 1710.0
    assert cna.to_float("34,2") == 34.2
    assert cna.to_float("34.2") == 34.2
    assert cna.to_float("-") is None


# --- memo fail-closed ---------------------------------------------------------


def make_run(tmp_path: Path, *, memo: str = "", numbers: str = "") -> Path:
    d = tmp_path / "run"
    d.mkdir(parents=True, exist_ok=True)
    if memo:
        (d / "memo.md").write_text(memo, encoding="utf-8")
    if numbers:
        (d / "numbers.csv").write_text(numbers, encoding="utf-8")
    return d


MEMO_REGISTERED = "Доля выросла до 34.2% [s03] (as_of 2026-Q1).\n"
MEMO_UNREGISTERED = "Доля выросла до 34.2% [s03], а издержки упали на 51% [s09].\n"


def test_registered_memo_figure_passes(tmp_path):
    d = make_run(tmp_path, memo=MEMO_REGISTERED)
    r = cna.Report()
    result = cna.check_memo(d, rows_from(GOOD_DERIVED), r)
    assert result["memo_unregistered"] == []
    assert r.errors == []


def test_unregistered_memo_figure_is_caught(tmp_path):
    d = make_run(tmp_path, memo=MEMO_UNREGISTERED)
    r = cna.Report()
    result = cna.check_memo(d, rows_from(GOOD_DERIVED), r)
    assert result["memo_unregistered"] == ["51"]
    assert any("no row in numbers.csv" in e for e in r.errors)


def test_multiplier_and_percentage_point_shapes_are_seen():
    found = cna.derived_shaped_numbers("быстрее в 3.5 раза, спред 4 п.п., рост 12×")
    assert found == {"3.5", "4", "12"}


def test_plain_counts_are_not_treated_as_derived():
    """Control: a bare magnitude is not arithmetic and must not be demanded."""
    assert cna.derived_shaped_numbers("рынок $4.5B в 2026 году, 18 игроков") == set()


def test_citation_ids_are_not_mistaken_for_numbers():
    assert cna.derived_shaped_numbers("подтверждено [s03][s11]") == set()


def test_missing_numbers_csv_is_not_run_not_clean(tmp_path, monkeypatch, capsys):
    d = make_run(tmp_path, memo=MEMO_UNREGISTERED)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_number_arithmetic.py", "--research-dir", str(d), "--strict"],
    )
    assert cna.main() == 0
    assert "not run" in capsys.readouterr().out


def test_strict_exits_nonzero_on_mismatch(tmp_path, monkeypatch):
    d = make_run(tmp_path, memo=MEMO_REGISTERED, numbers=f"{HEADER}\n{BAD_DERIVED}\n")
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_number_arithmetic.py", "--research-dir", str(d), "--strict"],
    )
    assert cna.main() == 1


def test_strict_exits_zero_on_a_clean_run(tmp_path, monkeypatch):
    d = make_run(tmp_path, memo=MEMO_REGISTERED, numbers=f"{HEADER}\n{GOOD_DERIVED}\n")
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_number_arithmetic.py", "--research-dir", str(d), "--strict"],
    )
    assert cna.main() == 0


def test_missing_required_column_is_a_usage_error(tmp_path, monkeypatch):
    d = make_run(
        tmp_path,
        memo=MEMO_REGISTERED,
        numbers="num_id,value,unit\nN1,34.2,%\n",
    )
    monkeypatch.setattr(
        sys, "argv", ["check_number_arithmetic.py", "--research-dir", str(d)]
    )
    assert cna.main() == 2
