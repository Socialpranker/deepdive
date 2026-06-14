import pytest
from runner.orchestrator import Orchestrator
from runner.providers import DryRunProvider


def test_orchestrator_writes_deviations_file(tmp_path):
    orch = Orchestrator(DryRunProvider())
    run_dir = orch.run("Is approach X better than Y?", "medium", tmp_path)
    dev = run_dir / "deviations.md"
    assert dev.exists(), "search() must write deviations.md"
    assert "# Deviations —" in dev.read_text(encoding="utf-8")


def test_orchestrator_run_still_validates_structure(tmp_path):
    # the existing scaffold contract: plan.md, sources/, a report all still produced
    orch = Orchestrator(DryRunProvider())
    run_dir = orch.run("How does X work?", "shallow", tmp_path)
    assert (run_dir / "plan.md").exists()
    assert (run_dir / "sources").is_dir()
    assert list(run_dir.glob("*_*.md"))  # the dated report


@pytest.mark.live
def test_live_loop_smoke(tmp_path):
    """Opt-in (-m live): a real provider run that exercises the loop end-to-end.
    Skipped by default; needs ANTHROPIC_API_KEY. Not required for CI to pass."""
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("no ANTHROPIC_API_KEY")
    from runner.providers import build_provider
    orch = Orchestrator(build_provider("claude"))
    run_dir = orch.run("What caused the 2023 SVB collapse?", "shallow", tmp_path)
    assert (run_dir / "deviations.md").exists()
