"""Tests for scripts/quiet.py — capped console output of the gate scripts."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from quiet import capped  # noqa: E402


def test_short_list_passes_through():
    assert capped(["a", "b"], 5, verbose=False) == ["a", "b"]


def test_long_list_is_cut_with_a_pointer_to_verbose():
    out = capped([str(i) for i in range(20)], 5, verbose=False)
    assert out[:5] == ["0", "1", "2", "3", "4"]
    assert len(out) == 6
    assert "15 more" in out[-1] and "--verbose" in out[-1]


def test_verbose_prints_everything():
    assert len(capped([str(i) for i in range(20)], 5, verbose=True)) == 20


def test_validate_phases_caps_warnings_unless_verbose(tmp_path):
    # An empty run dir yields many missing-artifact errors: enough to hit the cap.
    (tmp_path / "plan.md").write_text("---\nmode: deep\n---\n", encoding="utf-8")
    cmd = [sys.executable, str(REPO / "scripts" / "validate_phases.py"), "--research-dir", str(tmp_path)]
    quiet = subprocess.run(cmd, capture_output=True, text=True).stdout
    loud = subprocess.run(cmd + ["--verbose"], capture_output=True, text=True).stdout
    assert len(loud.splitlines()) > len(quiet.splitlines())
    assert "--verbose" in quiet
