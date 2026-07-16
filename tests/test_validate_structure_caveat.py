"""Tests for the caveat-vocab check in eval/validate_structure.py (F15)."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "eval"))

import validate_structure as vs  # noqa: E402


def make_source(sd: Path, caveat: str) -> None:
    sd.mkdir(exist_ok=True)
    (sd / "01_x.md").write_text(
        f"---\nid: s01\nurl: http://a\ntitle: A\naccess: OPEN\ncaveat: {caveat}\n---\nbody\n",
        encoding="utf-8",
    )


def caveat_warnings(d: Path) -> list[str]:
    r = vs.Report()
    vs.check_sources_dir(d, r)
    return [w for w in r.warnings if "caveat" in w]


def test_bare_dash_ok(tmp_path):
    make_source(tmp_path / "sources", "-")
    assert caveat_warnings(tmp_path) == []


def test_vendor_ok(tmp_path):
    make_source(tmp_path / "sources", "vendor")
    assert caveat_warnings(tmp_path) == []


def test_self_reported_ok(tmp_path):
    make_source(tmp_path / "sources", "self-reported")
    assert caveat_warnings(tmp_path) == []


def test_disputed_with_id_ok(tmp_path):
    make_source(tmp_path / "sources", "disputed:s14")
    assert caveat_warnings(tmp_path) == []


def test_disputed_without_s_prefix_ok(tmp_path):
    make_source(tmp_path / "sources", "disputed:14")
    assert caveat_warnings(tmp_path) == []


def test_missing_caveat_treated_as_dash(tmp_path):
    # a source with no caveat field at all must not warn (defaults to "-")
    sd = tmp_path / "sources"
    sd.mkdir()
    (sd / "01_x.md").write_text("---\nid: s01\nurl: http://a\ntitle: A\naccess: OPEN\n---\nbody\n", encoding="utf-8")
    assert caveat_warnings(tmp_path) == []


def test_free_text_warns(tmp_path):
    # the exact 2nd-run bug: free text ("stale — ...") instead of an enum value
    make_source(tmp_path / "sources", "stale — опубликовано 23.10.2025, до релизов")
    w = caveat_warnings(tmp_path)
    assert w and "not a valid marker" in w[0]


def test_unknown_word_warns(tmp_path):
    make_source(tmp_path / "sources", "biased")
    assert caveat_warnings(tmp_path)


def test_disputed_without_id_warns(tmp_path):
    make_source(tmp_path / "sources", "disputed")  # no :sNN → invalid
    assert caveat_warnings(tmp_path)


def test_quoted_value_not_false_flagged(tmp_path):
    # sub-agents write `caveat: "-"` (quoted) — the quotes must be stripped before
    # the vocab check, else a legit `-` false-warns (regression caught on live run).
    make_source(tmp_path / "sources", '"-"')
    assert caveat_warnings(tmp_path) == []


def test_quoted_vendor_ok(tmp_path):
    make_source(tmp_path / "sources", '"vendor"')
    assert caveat_warnings(tmp_path) == []


def test_quoted_disputed_ok(tmp_path):
    make_source(tmp_path / "sources", '"disputed:s14"')
    assert caveat_warnings(tmp_path) == []


def test_caveat_warning_is_not_an_error(tmp_path):
    # caveat problems are warnings, never errors (must not fail --strict)
    make_source(tmp_path / "sources", "garbage")
    r = vs.Report()
    vs.check_sources_dir(tmp_path, r)
    assert not any("caveat" in e for e in r.errors)
