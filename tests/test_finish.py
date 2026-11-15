"""Tests for scripts/finish.py — the single finish-up command."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

import finish  # noqa: E402
from test_validate_phases import FULL_SET, make_run  # noqa: E402


def _fake_runner(fail: set[str]):
    calls: list[str] = []

    def run(name: str, argv: list[str]) -> finish.StepResult:
        calls.append(name)
        return finish.StepResult(name, rc=1 if name in fail else 0, output=f"{name} out")

    run.calls = calls  # type: ignore[attr-defined]
    return run


def test_step_order_is_fixed_and_gate_is_last(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    run = _fake_runner(fail=set())
    results = finish.run_finish(d, mode="medium", offline=False, wiki_root=None, runner=run)
    assert [r.name for r in results] == [s.name for s in finish.STEPS]
    assert results[-1].name == "phase_gate"
    assert finish.exit_code(results) == 0


def test_offline_skips_citations_but_runs_everything_else(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    run = _fake_runner(fail=set())
    results = finish.run_finish(d, mode="medium", offline=True, wiki_root=None, runner=run)
    cit = next(r for r in results if r.name == "citations")
    assert cit.skipped
    assert "citations" not in run.calls
    assert len(run.calls) == len(finish.STEPS) - 1


def test_failed_step_does_not_stop_the_rest_and_exit_is_nonzero(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    run = _fake_runner(fail={"number_arithmetic"})
    results = finish.run_finish(d, mode="medium", offline=True, wiki_root=None, runner=run)
    assert "phase_gate" in run.calls  # the gate still ran after a failure
    assert finish.exit_code(results) == 1


def test_argv_carries_mode_wiki_root_and_out_dir(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    seen: dict[str, list[str]] = {}

    def run(name, argv):
        seen[name] = [str(a) for a in argv]
        return finish.StepResult(name, rc=0, output="")

    finish.run_finish(d, mode="deep", offline=False, wiki_root=tmp_path / "w", runner=run)
    assert "--mode" in seen["phase_gate"] and "deep" in seen["phase_gate"]
    assert "--wiki-root" in seen["wiki_ingest"]
    assert str(d / ".verify" / "citations") in seen["citations"]
    assert "--strict" in seen["number_provenance"] and "--strict" in seen["phase_gate"]


def test_end_to_end_on_synthetic_run(tmp_path):
    """Real subprocesses, no network: sources.csv gets built, wiki receipt written,
    number checks pass, gate is green."""
    d = make_run(tmp_path, mode="medium", phases=FULL_SET - {"wiki"})
    (d / "sources" / "01_x.md").write_text(
        "---\nurl: https://example.org/x\ntitle: X\ntype: web\n---\n> quote\n\n> quote two\n",
        encoding="utf-8",
    )
    ledger = d / "claims.csv"
    ledger.write_text(
        ledger.read_text(encoding="utf-8").replace("triangulated,high", "weak,low"),
        encoding="utf-8",
    )
    results = finish.run_finish(
        d, mode="medium", offline=True, wiki_root=tmp_path / "wiki", runner=finish.subprocess_runner
    )
    failed = [(r.name, r.output[-600:]) for r in results if r.rc != 0 and not r.skipped]
    assert failed == []
    assert (d / "sources.csv").is_file()
    assert (d / ".verify" / "wiki_ingest.json").is_file()


def test_overclaimed_ledger_turns_finish_red(tmp_path):
    """make_run's ledger types `triangulated,high` on one source — the audit's pattern."""
    d = make_run(tmp_path, mode="medium", phases=FULL_SET - {"wiki"})
    results = finish.run_finish(
        d, mode="medium", offline=True, wiki_root=tmp_path / "wiki", runner=finish.subprocess_runner
    )
    step = next(r for r in results if r.name == "claim_scores")
    assert step.rc == 1 and "status triangulated -> weak" in step.output
    assert finish.exit_code(results) == 1


def test_number_integrity_failure_warns_but_keeps_finish_green(tmp_path):
    d = make_run(tmp_path, mode="medium", phases=FULL_SET)
    run = _fake_runner(fail={"number_integrity"})
    results = finish.run_finish(d, mode="medium", offline=True, wiki_root=None, runner=run)
    assert finish.exit_code(results) == 0
    assert "warn  number_integrity" in finish.render(results, verbose=False)
