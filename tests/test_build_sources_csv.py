"""Tests for scripts/build_sources_csv.py — deterministic sources.csv generator."""
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import build_sources_csv as bs  # noqa: E402


def make_source(sd: Path, nn: str, **fm) -> None:
    lines = ["---"]
    for k, v in fm.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append(f"\n# {fm.get('title', 'x')}\n")
    (sd / f"{nn}_slug.md").write_text("\n".join(lines), encoding="utf-8")


def make_run(root: Path, sources: list[dict]) -> Path:
    d = root / "run"
    (d / "sources").mkdir(parents=True)
    for i, fm in enumerate(sources, 1):
        make_source(d / "sources", f"{i:02d}", **fm)
    return d


def read_csv(d: Path) -> list[dict]:
    with (d / "sources.csv").open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_writes_lowercase_contract_columns(tmp_path):
    d = make_run(tmp_path, [{"id": "s01", "url": "http://a", "title": "A", "type": "academic", "channel": "academic"}])
    rc = bs_run(d)
    assert rc == 0
    rows = read_csv(d)
    assert set(("url", "title")) <= set(rows[0].keys())  # validate_structure REQUIRED
    assert "type" in rows[0] and "channel" in rows[0]    # recommended for diversity
    assert rows[0]["url"] == "http://a" and rows[0]["title"] == "A"


def test_row_per_source_in_order(tmp_path):
    d = make_run(tmp_path, [
        {"id": "s01", "url": "http://a", "title": "A"},
        {"id": "s02", "url": "http://b", "title": "B"},
        {"id": "s03", "url": "http://c", "title": "C"},
    ])
    bs_run(d)
    rows = read_csv(d)
    assert [r["id"] for r in rows] == ["s01", "s02", "s03"]


def test_source_without_url_skipped(tmp_path):
    d = make_run(tmp_path, [
        {"id": "s01", "url": "http://a", "title": "A"},
        {"id": "s02", "title": "no-url"},  # no url → skipped, like the readers do
    ])
    bs_run(d)
    rows = read_csv(d)
    assert len(rows) == 1 and rows[0]["id"] == "s01"


def test_file_column_maps_back(tmp_path):
    d = make_run(tmp_path, [{"id": "s01", "url": "http://a", "title": "A"}])
    bs_run(d)
    rows = read_csv(d)
    assert rows[0]["file"] == "sources/01_slug.md"


def test_id_falls_back_to_stem(tmp_path):
    d = make_run(tmp_path, [{"url": "http://a", "title": "A"}])  # no id field
    bs_run(d)
    rows = read_csv(d)
    assert rows[0]["id"] == "01_slug"


def test_nested_frontmatter_block_ignored(tmp_path):
    # hypothesis_evidence: is a nested block — its H1/H2 lines must not leak as columns
    d = tmp_path / "run"
    (d / "sources").mkdir(parents=True)
    (d / "sources" / "01_x.md").write_text(
        "---\nid: s01\nurl: http://a\ntitle: A\nhypothesis_evidence:\n  H1: supports\n---\nbody\n",
        encoding="utf-8",
    )
    bs_run(d)
    rows = read_csv(d)
    assert rows[0]["id"] == "s01" and rows[0]["url"] == "http://a"
    assert "H1" not in rows[0]


def test_check_mode_detects_stale(tmp_path):
    d = make_run(tmp_path, [{"id": "s01", "url": "http://a", "title": "A"}])
    bs_run(d)  # write fresh
    # mutate the file so the on-disk csv is now stale
    make_source(d / "sources", "02", id="s02", url="http://b", title="B")
    rc = bs_run(d, check=True)
    assert rc == 1


def test_check_mode_passes_when_fresh(tmp_path):
    d = make_run(tmp_path, [{"id": "s01", "url": "http://a", "title": "A"}])
    bs_run(d)
    rc = bs_run(d, check=True)
    assert rc == 0


def test_no_sources_dir_errors(tmp_path):
    d = tmp_path / "run"
    d.mkdir()
    rc = bs_run(d)
    assert rc == 2


def test_output_is_valid_for_validate_structure(tmp_path):
    # the generated csv must satisfy eval/validate_structure.py's check_sources_csv
    sys.path.insert(0, str(REPO / "eval"))
    import validate_structure as vs  # noqa: E402
    d = make_run(tmp_path, [
        {"id": "s01", "url": "http://a", "title": "A", "type": "academic", "channel": "academic"},
    ])
    bs_run(d)
    r = vs.Report()
    n = vs.check_sources_csv(d, r)
    assert n == 1
    assert r.errors == []  # url+title present → no errors


# --- helper: run main() with argv patched ---------------------------------
def bs_run(d: Path, check: bool = False) -> int:
    argv = ["build_sources_csv.py", "--research-dir", str(d)]
    if check:
        argv.append("--check")
    old = sys.argv
    sys.argv = argv
    try:
        return bs.main()
    finally:
        sys.argv = old
