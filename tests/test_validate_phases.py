"""Tests for scripts/validate_phases.py — phase-gate completeness validator."""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import validate_phases as vp  # noqa: E402


def make_run(root: Path, *, mode: str, phases: set[str]) -> Path:
    """Build a synthetic run dir containing artifacts for the given phase ids."""
    d = root / "run"
    d.mkdir()
    if "report" in phases:
        (d / "2026-07-16_landscape.md").write_text(
            f"---\nmode: {mode}\n---\nbody\n", encoding="utf-8"
        )
    if "3" in phases:
        (d / "plan.md").write_text(f"---\nmode: {mode}\n---\nplan\n", encoding="utf-8")
    if "4" in phases:
        sd = d / "sources"
        sd.mkdir()
        (sd / "01_x.md").write_text("---\nurl: http://x\n---\n", encoding="utf-8")
    if "state" in phases:
        (d / "state.md").write_text(
            "---\nround: 2\n---\n"
            "## Known\n- Q1 closed: c1\n## Gaps\n- Q2 no primary\n## Next\n- registry pass\n",
            encoding="utf-8",
        )
    if "5" in phases:
        (d / "claims.csv").write_text(
            "claim_id,claim,roots,paths,status,confidence,dissent,as_of\n"
            "c1,a claim,own;study-x,academic|q|en;web-general|q2|en,triangulated,high,-,-\n",
            encoding="utf-8",
        )
    if "5.5" in phases:
        ed = d / "evidence"
        ed.mkdir()
        (ed / "C1.md").write_text("quote\n", encoding="utf-8")
        vd = d / ".verify"
        vd.mkdir(exist_ok=True)
        (vd / "authority.json").write_text(
            '{"pairs": [], "quarantined": []}', encoding="utf-8"
        )
    if "6.5" in phases:
        vd = d / ".verify"
        vd.mkdir(exist_ok=True)
        (vd / "citations.json").write_text("{}", encoding="utf-8")
        (vd / "faithfulness.json").write_text("{}", encoding="utf-8")
        (vd / "qualifiers.json").write_text("{}", encoding="utf-8")
        (vd / "constructs.json").write_text(
            '{"construct_integrity": 1.0, "results": [{"name": "IterResearch", '
            '"status": "sourced", "sources": ["s01"], "locations": ["E3"]}]}',
            encoding="utf-8",
        )
    if "7" in phases:
        (d / "refresh_targets.md").write_text("targets\n", encoding="utf-8")
    if "memo" in phases:
        (d / "memo.md").write_text("# Memo\nрекомендация\n", encoding="utf-8")
    if "outline" in phases:
        (d / "outline.md").write_text(
            "# Outline\n\n| section | block | claims |\n|---|---|---|\n"
            "| TL;DR | F1 | c1 |\n",
            encoding="utf-8",
        )
    if "numbers" in phases:
        (d / "numbers.csv").write_text(
            "num_id,value,unit,kind,formula,inputs,group,claim_id,sources,as_of\n"
            "N1,4.5,$B,verbatim,-,-,-,c1,s01,2026-Q1\n",
            encoding="utf-8",
        )
    if "8" in phases:
        (d / "application.md").write_text(
            "---\nstatus: deferred\n---\n", encoding="utf-8"
        )
    return d


SHALLOW_SET = {"3", "4", "5", "report", "memo", "8"}
# From medium up the run also keeps the machine-checkable bookkeeping: the round
# workspace (state.md), the section->claim map (outline.md) and the number registry.
FULL_SET = SHALLOW_SET | {"5.5", "6.5", "7", "state", "outline", "numbers"}


def run_validate(d: Path, mode: str):
    phases = vp.phases_manifest.load_phases(REPO / "phases.yaml")
    r = vp.Report()
    vp.validate(d, mode, phases, r)
    return r


def test_shallow_run_with_shallow_artifacts_passes(tmp_path):
    d = make_run(tmp_path, mode="shallow", phases=SHALLOW_SET)
    r = run_validate(d, "shallow")
    assert r.errors == []


def test_shallow_does_not_require_medium_artifacts(tmp_path):
    # evidence/.verify/refresh_targets are medium-gated — a shallow run without them is fine.
    d = make_run(tmp_path, mode="shallow", phases=SHALLOW_SET)
    r = run_validate(d, "shallow")
    assert not any("evidence" in e or "verify" in e or "refresh" in e for e in r.errors)


def test_full_run_passes_for_deep(tmp_path):
    d = make_run(tmp_path, mode="deep", phases=FULL_SET)
    r = run_validate(d, "deep")
    assert r.errors == []


def test_deep_run_missing_evidence_fails(tmp_path):
    d = make_run(tmp_path, mode="deep", phases=FULL_SET - {"5.5"})
    r = run_validate(d, "deep")
    assert any("phase 5.5" in e for e in r.errors)


def test_deep_run_missing_verify_reports_all_three_json(tmp_path):
    d = make_run(tmp_path, mode="deep", phases=FULL_SET - {"6.5"})
    r = run_validate(d, "deep")
    joined = " ".join(r.errors)
    assert "citations.json" in joined and "faithfulness.json" in joined
    assert "qualifiers.json" in joined


def test_deep_run_missing_only_qualifiers_still_blocks(tmp_path):
    # Layer 3 is not optional at deep: liveness+faithfulness passing is not enough
    # if nothing checked that the report still says what the ledger said.
    d = make_run(tmp_path, mode="deep", phases=FULL_SET)
    (d / ".verify" / "qualifiers.json").unlink()
    r = run_validate(d, "deep")
    joined = " ".join(r.errors)
    assert "qualifiers.json" in joined
    assert "citations.json" not in joined and "faithfulness.json" not in joined


def test_medium_requires_same_files_as_deep(tmp_path):
    # no phase has depth_gate: deep, so medium and deep demand the same file set.
    d = make_run(tmp_path, mode="medium", phases=SHALLOW_SET)
    r = run_validate(d, "medium")
    ids = {e.split(":")[0] for e in r.errors}
    assert "phase 5.5" in ids and "phase 6.5" in ids and "phase 7" in ids


def test_missing_plan_fails(tmp_path):
    d = make_run(tmp_path, mode="shallow", phases=SHALLOW_SET - {"3"})
    r = run_validate(d, "shallow")
    assert any("phase 3" in e and "plan.md" in e for e in r.errors)


def test_sources_csv_satisfies_phase_4(tmp_path):
    d = make_run(tmp_path, mode="shallow", phases={"3", "5", "report"})
    (d / "sources.csv").write_text("url,title\nhttp://x,X\n", encoding="utf-8")
    r = run_validate(d, "shallow")
    assert not any("phase 4" in e for e in r.errors)


def test_empty_sources_dir_does_not_satisfy_phase_4(tmp_path):
    d = make_run(tmp_path, mode="shallow", phases={"3", "5", "report"})
    (d / "sources").mkdir()  # empty dir must not count
    r = run_validate(d, "shallow")
    assert any("phase 4" in e for e in r.errors)


def test_missing_report_fails(tmp_path):
    d = make_run(tmp_path, mode="shallow", phases=SHALLOW_SET - {"report"})
    r = run_validate(d, "shallow")
    assert any("phase 6" in e and "report" in e.lower() for e in r.errors)


def test_missing_memo_fails_even_shallow(tmp_path):
    # memo.md is the phase 6 companion artifact, mandatory at every depth.
    d = make_run(tmp_path, mode="shallow", phases=SHALLOW_SET - {"memo"})
    r = run_validate(d, "shallow")
    assert any("phase 6" in e and "memo.md" in e for e in r.errors)


def test_missing_application_fails_even_shallow(tmp_path):
    # phase 8 (decision walkthrough) must leave application.md at every depth.
    d = make_run(tmp_path, mode="shallow", phases=SHALLOW_SET - {"8"})
    r = run_validate(d, "shallow")
    assert any("phase 8" in e and "application.md" in e for e in r.errors)


def test_report_present_but_memo_missing_reports_only_memo(tmp_path):
    # the report check must not short-circuit the memo check (and vice versa).
    d = make_run(tmp_path, mode="shallow", phases=SHALLOW_SET - {"memo"})
    r = run_validate(d, "shallow")
    phase6 = [e for e in r.errors if e.startswith("phase 6")]
    assert phase6 and all("memo.md" in e for e in phase6)


def test_detect_mode_from_report(tmp_path):
    d = make_run(tmp_path, mode="deep", phases=FULL_SET)
    assert vp.detect_mode(d) == "deep"


def test_detect_mode_falls_back_to_plan(tmp_path):
    d = make_run(tmp_path, mode="medium", phases={"3"})  # plan.md only, no report
    assert vp.detect_mode(d) == "medium"


def test_detect_mode_none_when_absent(tmp_path):
    d = tmp_path / "run"
    d.mkdir()
    assert vp.detect_mode(d) is None


def test_self_check_clean_for_current_phases():
    # every phase in phases.yaml is either mapped or explicitly artifact-less.
    phases = vp.phases_manifest.load_phases(REPO / "phases.yaml")
    r = vp.Report()
    vp.self_check(phases, r)
    assert r.warnings == []


def test_self_check_warns_on_unmapped_phase():
    phases = [
        {
            "id": "9.9",
            "name_en": "Ghost",
            "depth_gate": "medium",
            "name_ru": "x",
            "model": "haiku",
            "effort": "low",
        },
    ]
    r = vp.Report()
    vp.self_check(phases, r)
    assert any("9.9" in w for w in r.warnings)


def test_deep_run_missing_authority_json_fails(tmp_path):
    # The authority axis of 5.5 is fail-closed: an absent verdict file means the
    # axis never ran, not that every source qualified.
    d = make_run(tmp_path, mode="deep", phases=FULL_SET)
    (d / ".verify" / "authority.json").unlink()
    r = run_validate(d, "deep")
    assert any("authority.json" in e for e in r.errors)


def test_duplicate_source_id_is_an_error(tmp_path):
    # Two files claiming one id == a sub-agent wrote outside its assigned range.
    d = make_run(tmp_path, mode="deep", phases=FULL_SET)
    (d / "sources" / "01_y.md").write_text(
        "---\nurl: http://y\n---\n", encoding="utf-8"
    )
    r = run_validate(d, "deep")
    assert any("source id 1 claimed by 2 files" in e for e in r.errors)


def test_distinct_source_ids_are_not_flagged(tmp_path):
    # Control group: without this the duplicate check could be passing for the
    # wrong reason (e.g. flagging every run).
    d = make_run(tmp_path, mode="deep", phases=FULL_SET)
    (d / "sources" / "02_y.md").write_text(
        "---\nurl: http://y\n---\n", encoding="utf-8"
    )
    r = run_validate(d, "deep")
    assert not any("claimed by" in e for e in r.errors)


def test_ledger_missing_new_columns_warns(tmp_path):
    d = make_run(tmp_path, mode="deep", phases=FULL_SET)
    (d / "claims.csv").write_text(
        "claim_id,status\nc1,triangulated\n", encoding="utf-8"
    )
    r = run_validate(d, "deep")
    joined = " ".join(r.warnings)
    assert "dissent" in joined and "paths" in joined
    assert not any("claims.csv" in e for e in r.errors)  # warning, never a blocker


def test_real_research_dir_flagged_incomplete_for_deep():
    # research/deepdive-skill-improvements is a real deep run that predates the
    # evidence/verify/refresh phases — the gate must catch it as incomplete.
    real = REPO / "research" / "deepdive-skill-improvements"
    if not real.is_dir():
        pytest.skip("sample research dir not present")
    r = run_validate(real, "deep")
    assert r.errors  # missing evidence/.verify/refresh_targets


# --- state.md: the round workspace --------------------------------------------


def test_medium_run_without_state_window_fails(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET - {"state"})
    r = run_validate(d, "medium")
    assert any("state.md" in e for e in r.errors)


def test_shallow_run_needs_no_state_window(tmp_path):
    """Control: the workspace rebuild is medium+ bookkeeping, not a universal rule."""
    d = make_run(tmp_path, mode="shallow", phases=SHALLOW_SET)
    r = run_validate(d, "shallow")
    assert r.errors == []


def test_state_window_without_gaps_section_fails(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    (d / "state.md").write_text(
        "---\nround: 2\n---\n## Known\n- Q1 closed\n## Next\n- registry\n",
        encoding="utf-8",
    )
    r = run_validate(d, "medium")
    assert any("## Gaps" in e for e in r.errors)


def test_state_window_over_hard_limit_fails(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    (d / "state.md").write_text(
        "---\nround: 2\n---\n## Known\n## Gaps\n## Next\n" + "x" * (13 * 1024),
        encoding="utf-8",
    )
    r = run_validate(d, "medium")
    assert any("appended to, not rebuilt" in e for e in r.errors)


def test_state_window_within_budget_is_silent(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    r = run_validate(d, "medium")
    assert not any("state.md" in m for m in r.errors + r.warnings)


# --- outline.md: the section -> claim map --------------------------------------


def test_medium_run_without_outline_fails(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET - {"outline"})
    r = run_validate(d, "medium")
    assert any("outline.md" in e for e in r.errors)


def test_outline_without_table_rows_fails(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    (d / "outline.md").write_text(
        "# Outline\n\nразделы будут позже\n", encoding="utf-8"
    )
    r = run_validate(d, "medium")
    assert any("no `| section | block | claims |` table" in e for e in r.errors)


def test_outline_section_without_claims_fails(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    (d / "outline.md").write_text(
        "| section | block | claims |\n|---|---|---|\n| TL;DR | F1 | c1 |\n"
        "| Контекст | X1 | - |\n",
        encoding="utf-8",
    )
    r = run_validate(d, "medium")
    assert any("maps to no claim_id" in e for e in r.errors)


def test_outline_citing_unknown_claim_fails(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    (d / "outline.md").write_text(
        "| section | block | claims |\n|---|---|---|\n| TL;DR | F1 | c1; c9 |\n",
        encoding="utf-8",
    )
    r = run_validate(d, "medium")
    assert any("c9" in e and "absent from claims.csv" in e for e in r.errors)


def test_triangulated_claim_left_out_of_report_blocks_deep(tmp_path):
    """The synthesis gap: found and triangulated, never written down."""
    d = make_run(tmp_path, mode="deep", phases=FULL_SET)
    (d / "claims.csv").write_text(
        "claim_id,claim,roots,paths,status,confidence,dissent,as_of\n"
        "c1,a claim,own;study-x,a|q|en;b|q2|en,triangulated,high,-,-\n"
        "c2,orphan claim,own;study-y,a|q3|en;b|q4|en,triangulated,high,-,-\n",
        encoding="utf-8",
    )
    r = run_validate(d, "deep")
    assert any("never placed in the report" in e and "c2" in e for e in r.errors)


def test_same_gap_is_a_warning_on_medium(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    (d / "claims.csv").write_text(
        "claim_id,claim,roots,paths,status,confidence,dissent,as_of\n"
        "c1,a claim,own;study-x,a|q|en;b|q2|en,triangulated,high,-,-\n"
        "c2,orphan claim,own;study-y,a|q3|en;b|q4|en,triangulated,high,-,-\n",
        encoding="utf-8",
    )
    r = run_validate(d, "medium")
    assert any("never placed in the report" in w for w in r.warnings)
    assert not any("never placed in the report" in e for e in r.errors)


def test_weak_claim_left_out_is_not_flagged(tmp_path):
    """Control: only carrying claims (triangulated/contested) must be placed."""
    d = make_run(tmp_path, mode="deep", phases=FULL_SET)
    (d / "claims.csv").write_text(
        "claim_id,claim,roots,paths,status,confidence,dissent,as_of\n"
        "c1,a claim,own;study-x,a|q|en;b|q2|en,triangulated,high,-,-\n"
        "c2,thin claim,own,a|q3|en,data-insufficient,low,-,-\n",
        encoding="utf-8",
    )
    r = run_validate(d, "deep")
    assert not any("never placed" in e for e in r.errors)


# --- constructs.json: Layer 4 -------------------------------------------------


def test_medium_run_without_constructs_json_fails(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    (d / ".verify" / "constructs.json").unlink()
    r = run_validate(d, "medium")
    assert any("constructs.json" in e for e in r.errors)


def test_unsourced_construct_in_memo_blocks(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    (d / ".verify" / "constructs.json").write_text(
        '{"results": [{"name": "закон Кэмпбелла для агентов", "status": "unsourced", '
        '"sources": [], "locations": ["memo.md"]}]}',
        encoding="utf-8",
    )
    r = run_validate(d, "medium")
    assert any("закон Кэмпбелла" in e and "unsourced" in e for e in r.errors)


def test_unsourced_construct_outside_memo_only_warns(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    (d / ".verify" / "constructs.json").write_text(
        '{"results": [{"name": "cold-start decay", "status": "unsourced", '
        '"sources": [], "locations": ["E7"]}]}',
        encoding="utf-8",
    )
    r = run_validate(d, "medium")
    assert any("cold-start decay" in w for w in r.warnings)
    assert not any("cold-start decay" in e for e in r.errors)


def test_author_construct_is_accepted(tmp_path):
    """Control: our own label, marked as ours, is legal — not every name needs a source."""
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    (d / ".verify" / "constructs.json").write_text(
        '{"results": [{"name": "провенанс-разрыв", "status": "author-construct", '
        '"sources": [], "locations": ["memo.md"]}]}',
        encoding="utf-8",
    )
    r = run_validate(d, "medium")
    assert r.errors == []


def test_unknown_construct_status_warns(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    (d / ".verify" / "constructs.json").write_text(
        '{"results": [{"name": "X", "status": "probably-fine", "locations": ["F1"]}]}',
        encoding="utf-8",
    )
    r = run_validate(d, "medium")
    assert any("not one of" in w for w in r.warnings)


def test_malformed_constructs_json_is_an_error(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    (d / ".verify" / "constructs.json").write_text("{not json", encoding="utf-8")
    r = run_validate(d, "medium")
    assert any("not valid JSON" in e for e in r.errors)


def test_constructs_json_without_results_is_an_error(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    (d / ".verify" / "constructs.json").write_text(
        '{"integrity": 1.0}', encoding="utf-8"
    )
    r = run_validate(d, "medium")
    assert any("no `results` list" in e for e in r.errors)


# --- numbers.csv --------------------------------------------------------------


def test_medium_run_without_numbers_csv_fails(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET - {"numbers"})
    r = run_validate(d, "medium")
    assert any("numbers.csv" in e for e in r.errors)


def test_shallow_run_needs_no_numbers_csv(tmp_path):
    d = make_run(tmp_path, mode="shallow", phases=SHALLOW_SET)
    r = run_validate(d, "shallow")
    assert not any("numbers.csv" in e for e in r.errors)

