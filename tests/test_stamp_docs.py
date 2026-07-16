"""Tests for scripts/stamp_docs.py — the marker stamper. All on temp files."""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import stamp_docs  # noqa: E402

VALUES = {"count:blocks": "103", "count:phases": "9"}


def test_stamps_between_markers_only():
    src = "Library has <!--gen:count:blocks-->75<!--/gen--> blocks. Keep this."
    out = stamp_docs.stamp_text(src, VALUES, path="x")
    assert out == "Library has <!--gen:count:blocks-->103<!--/gen--> blocks. Keep this."


def test_idempotent():
    src = "n=<!--gen:count:blocks-->103<!--/gen-->"
    once = stamp_docs.stamp_text(src, VALUES, path="x")
    twice = stamp_docs.stamp_text(once, VALUES, path="x")
    assert once == twice == "n=<!--gen:count:blocks-->103<!--/gen-->"


def test_multiple_markers_same_text():
    src = "<!--gen:count:blocks-->0<!--/gen--> and <!--gen:count:phases-->0<!--/gen-->"
    out = stamp_docs.stamp_text(src, VALUES, path="x")
    assert out == "<!--gen:count:blocks-->103<!--/gen--> and <!--gen:count:phases-->9<!--/gen-->"


def test_unbalanced_marker_raises():
    src = "open <!--gen:count:blocks-->75 but no close"
    with pytest.raises(ValueError, match="unbalanced|unclosed"):
        stamp_docs.stamp_text(src, VALUES, path="x")


def test_nested_markers_raise():
    # an open before the previous open's close = overlapping markers → must raise,
    # never silently mis-stamp (regression: README phase-table wrapped count markers)
    src = "<!--gen:count:blocks-->x <!--gen:count:phases-->y<!--/gen--> z<!--/gen-->"
    with pytest.raises(ValueError, match="nested|overlap"):
        stamp_docs.stamp_text(src, VALUES, path="x")


def test_unknown_key_raises():
    src = "<!--gen:count:bogus-->x<!--/gen-->"
    with pytest.raises(ValueError, match="unknown key"):
        stamp_docs.stamp_text(src, VALUES, path="x")


def test_render_values_has_all_keys():
    v = stamp_docs.render_values(REPO)
    for k in ("count:blocks", "count:channels", "count:stat_sources", "count:api",
              "count:genres", "count:phases", "phases:list:ru",
              "phases:table:en"):
        assert k in v
    assert v["count:blocks"] == "105"
    assert v["count:phases"] == "10"


def test_check_mode_detects_drift(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("n=<!--gen:count:blocks-->75<!--/gen-->", encoding="utf-8")
    rc = stamp_docs.run(REPO, [f], write=False)
    assert rc == 1  # 75 != 105 → drift


def test_write_mode_fixes_and_check_passes(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("n=<!--gen:count:blocks-->75<!--/gen-->", encoding="utf-8")
    assert stamp_docs.run(REPO, [f], write=True) == 0
    assert "105" in f.read_text(encoding="utf-8")
    assert stamp_docs.run(REPO, [f], write=False) == 0  # now synced


def test_zero_count_refused(monkeypatch, tmp_path):
    # if a regex returns 0, render_values must refuse (never stamp zero silently)
    monkeypatch.setattr(stamp_docs.catalog_counts, "counts", lambda repo: {
        "blocks": 0, "channels": 29, "stat_sources": 460, "api": 39, "genres": 6})
    with pytest.raises(ValueError, match="suspicious|zero"):
        stamp_docs.render_values(REPO)


def test_unused_key_warns_not_fails(tmp_path, capsys):
    # a doc using only ONE key → the other keys are "stamped nowhere" → WARNING, rc 0
    f = tmp_path / "doc.md"
    f.write_text("n=<!--gen:count:blocks-->105<!--/gen-->", encoding="utf-8")
    rc = stamp_docs.run(REPO, [f], write=False)
    out = capsys.readouterr().out
    assert rc == 0  # warning, not drift
    assert "stamped nowhere" in out
