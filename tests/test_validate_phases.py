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
        (d / "2026-07-16_landscape.md").write_text(f"---\nmode: {mode}\n---\nbody\n", encoding="utf-8")
    if "3" in phases:
        (d / "plan.md").write_text(f"---\nmode: {mode}\n---\nplan\n", encoding="utf-8")
    if "4" in phases:
        sd = d / "sources"
        sd.mkdir()
        (sd / "01_x.md").write_text("---\nurl: http://x\n---\n", encoding="utf-8")
    if "5" in phases:
        (d / "claims.csv").write_text("claim_id,status\nc1,triangulated\n", encoding="utf-8")
    if "5.5" in phases:
        ed = d / "evidence"
        ed.mkdir()
        (ed / "C1.md").write_text("quote\n", encoding="utf-8")
    if "6.5" in phases:
        vd = d / ".verify"
        vd.mkdir()
        (vd / "citations.json").write_text("{}", encoding="utf-8")
        (vd / "faithfulness.json").write_text("{}", encoding="utf-8")
    if "7" in phases:
        (d / "refresh_targets.md").write_text("targets\n", encoding="utf-8")
    return d


SHALLOW_SET = {"3", "4", "5", "report"}
FULL_SET = SHALLOW_SET | {"5.5", "6.5", "7"}


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


def test_deep_run_missing_verify_reports_both_json(tmp_path):
    d = make_run(tmp_path, mode="deep", phases=FULL_SET - {"6.5"})
    r = run_validate(d, "deep")
    joined = " ".join(r.errors)
    assert "citations.json" in joined and "faithfulness.json" in joined


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
        {"id": "9.9", "name_en": "Ghost", "depth_gate": "medium",
         "name_ru": "x", "model": "haiku", "effort": "low"},
    ]
    r = vp.Report()
    vp.self_check(phases, r)
    assert any("9.9" in w for w in r.warnings)


def test_real_research_dir_flagged_incomplete_for_deep():
    # research/deepdive-skill-improvements is a real deep run that predates the
    # evidence/verify/refresh phases — the gate must catch it as incomplete.
    real = REPO / "research" / "deepdive-skill-improvements"
    if not real.is_dir():
        pytest.skip("sample research dir not present")
    r = run_validate(real, "deep")
    assert r.errors  # missing evidence/.verify/refresh_targets
