import json
import subprocess
from runner.orchestrator import Orchestrator, RunState
from runner.providers import DryRunProvider


def _prep(tmp_path, depth="medium", verify_live=False):
    o = Orchestrator(DryRunProvider(), verify_live=verify_live)
    s = RunState(question="does X cause Y", depth=depth, root=tmp_path)
    o.reframe(s)
    o.choose_genre(s)
    o.plan(s)
    o.search(s)
    o.score(s)
    o.synthesize(s)
    return o, s


def _report_path(s):
    import datetime as dt
    return s.dir / f"{dt.date.today().isoformat()}_{s.genre}.md"


def test_verify_replaces_placeholder_with_metric(tmp_path, monkeypatch):
    o, s = _prep(tmp_path, verify_live=True)
    def fake_run(cmd, **kwargs):
        out_idx = cmd.index("--out") + 1
        base = cmd[out_idx]
        from pathlib import Path
        jp = Path(base).with_suffix(".json")
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps({
            "citation_integrity": 1.0,
            "results": [{"sid": "s01", "alive": True, "red_flag": False}],
        }), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(subprocess, "run", fake_run)

    o.verify(s)
    report = _report_path(s).read_text(encoding="utf-8")
    assert "1/1 verified" in report
    assert "pending — run eval/check_citations.py" not in report


def test_verify_unavailable_when_no_json(tmp_path, monkeypatch):
    o, s = _prep(tmp_path, verify_live=True)
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0))
    o.verify(s)
    report = _report_path(s).read_text(encoding="utf-8")
    assert "verification unavailable" in report


def test_verify_survives_subprocess_oserror(tmp_path, monkeypatch):
    o, s = _prep(tmp_path, verify_live=True)
    def boom(cmd, **kw):
        raise OSError("no python")
    monkeypatch.setattr(subprocess, "run", boom)
    o.verify(s)  # must NOT raise
    report = _report_path(s).read_text(encoding="utf-8")
    assert "verification unavailable" in report


def test_run_invokes_verify_offline(tmp_path):
    # Default offline path: no subprocess monkeypatching needed
    o = Orchestrator(DryRunProvider())  # verify_live defaults to False
    out_dir = o.run("does X cause Y", "medium", tmp_path)
    import datetime as dt
    reports = list(out_dir.glob("*_*.md"))
    report = next(p for p in reports if dt.date.today().isoformat() in p.name)
    text = report.read_text(encoding="utf-8")
    assert "pending — run eval/check_citations.py" not in text
    assert "Citation integrity" in text


def test_verify_offline_by_default_skips_subprocess(tmp_path, monkeypatch):
    called = {"n": 0}
    def spy(cmd, **kw):
        called["n"] += 1
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(subprocess, "run", spy)
    o, s = _prep(tmp_path)  # verify_live defaults to False
    o.verify(s)
    assert called["n"] == 0  # subprocess NOT invoked offline
    report = _report_path(s).read_text(encoding="utf-8")
    assert "verification unavailable" in report


def test_verify_survives_missing_report(tmp_path):
    o = Orchestrator(DryRunProvider())
    s = RunState(question="q", depth="medium", root=tmp_path)
    o.reframe(s)
    o.choose_genre(s)
    o.plan(s)
    # NOTE: synthesize() intentionally NOT called → report file is absent
    o.verify(s)  # must NOT raise
    report = _report_path(s).read_text(encoding="utf-8")  # file should now exist
    assert "Citation integrity" in report
