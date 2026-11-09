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


def test_root_column_passthrough(tmp_path):
    # provenance root (anti circular-reporting) must survive into the index
    d = make_run(tmp_path, [
        {"id": "s01", "url": "http://a", "title": "A", "root": "press-release-acme-2026-03"},
        {"id": "s02", "url": "http://b", "title": "B"},  # root absent → empty cell
    ])
    bs_run(d)
    rows = read_csv(d)
    assert rows[0]["root"] == "press-release-acme-2026-03"
    assert rows[1]["root"] == ""


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


def test_free_form_type_is_rejected(tmp_path):
    # Контроль: enum ловится, иначе «≥2 типа» в триангуляции набирается синонимами.
    sd = tmp_path / "sources"
    sd.mkdir()
    (sd / "01_a.md").write_text(
        "---\nid: s01\nurl: https://example.com\ntype: Vendor-docs\n---\n", encoding="utf-8"
    )
    rows = bs.collect_rows(tmp_path)
    assert bs.enum_violations(rows) == ["s01: type=Vendor-docs"]


def test_enum_type_passes(tmp_path):
    sd = tmp_path / "sources"
    sd.mkdir()
    (sd / "01_a.md").write_text(
        "---\nid: s01\nurl: https://example.com\ntype: Primary\n---\n", encoding="utf-8"
    )
    assert bs.enum_violations(bs.collect_rows(tmp_path)) == []


# --- strict enums: error at write time (--lint), warning for archived runs ---
def lint(*files: Path) -> int:
    old = sys.argv
    sys.argv = ["build_sources_csv.py", "--lint", *map(str, files)]
    try:
        return bs.main()
    finally:
        sys.argv = old


GOOD = {
    "id": "s01", "url": "https://a.org", "title": "A", "type": "Primary", "caveat": "-",
    "origin_kind": "measurement", "access": "OPEN", "fetch_tier": "webfetch", "used": "Y",
}


def test_enum_strict_normalizes_case_quotes_and_comments(tmp_path):
    d = make_run(tmp_path, [{
        **GOOD, "type": '"primary"', "access": "open", "used": "y",
        "caveat": "Self-Reported", "origin_kind": "'-'", "fetch_tier": "HTTP   # чем взят",
    }])
    rows = bs.collect_rows(d)
    assert bs.enum_violations(rows) == []
    r = rows[0]
    assert (r["type"], r["access"], r["used"], r["caveat"]) == ("Primary", "OPEN", "Y", "self-reported")
    assert lint(*sorted((d / "sources").glob("*.md"))) == 0


def test_enum_strict_lint_rejects_each_bad_field(tmp_path, capsys):
    d = make_run(tmp_path, [{
        **GOOD, "type": "docs", "caveat": "vendor. not a basis for anything", "origin_kind": "guess",
        "access": "full", "fetch_tier": "curl", "used": "maybe",
    }])
    assert lint(*(d / "sources").glob("*.md")) == 1
    out = capsys.readouterr().out
    for bad in ("type=docs", "caveat=vendor. not", "origin_kind=guess", "access=full",
                "fetch_tier=curl", "used=maybe"):
        assert bad in out
    assert "ERROR" in out


def test_enum_strict_disputed_needs_source_id(tmp_path):
    d = make_run(tmp_path, [{**GOOD, "caveat": "disputed:s07"}, {**GOOD, "id": "s02", "caveat": "disputed"}])
    assert bs.enum_violations(bs.collect_rows(d)) == ["s02: caveat=disputed"]


def test_enum_strict_absent_optional_fields_pass(tmp_path):
    d = make_run(tmp_path, [{"id": "s01", "url": "https://a.org", "title": "A", "type": "Academic"}])
    assert lint(*(d / "sources").glob("*.md")) == 0


def test_enum_strict_lint_rejects_missing_frontmatter(tmp_path, capsys):
    f = tmp_path / "01_x.md"
    f.write_text("# no frontmatter\n", encoding="utf-8")
    assert lint(f) == 1
    assert "no frontmatter" in capsys.readouterr().out


def test_enum_strict_archived_run_still_builds(tmp_path):
    # Archived runs: 91 files without frontmatter, free-form values. finish.py's first
    # step must stay green on them — warn, never fail.
    import subprocess
    import finish
    d = make_run(tmp_path, [{**GOOD, "type": "docs", "access": "full", "caveat": "long free text"}])
    (d / "sources" / "02_legacy.md").write_text("# legacy source, no frontmatter\n", encoding="utf-8")
    step = next(s for s in finish.STEPS if s.name == "sources_csv")
    argv = [sys.executable, str(step.script), "--research-dir", str(d), *step.extra(d, None, None)]
    proc = subprocess.run(argv, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "WARN" in proc.stdout and "ERROR" not in proc.stdout
    assert read_csv(d)[0]["type"] == "docs"


def test_total_column_is_sum_of_axes(tmp_path):
    d = make_run(tmp_path, [
        {"id": "s01", "url": "https://a", "title": "A", "credibility": 5, "recency": 4, "bias": 3, "total": 99},
        {"id": "s02", "url": "https://b", "title": "B", "credibility": 5, "total": 13},
        {"id": "s03", "url": "https://c", "title": "C", "credibility": 5},
    ])
    assert [r["total"] for r in bs.collect_rows(d)] == ["12", "13", ""]


def test_total_non_numeric_axis_is_no_total(tmp_path):
    d = make_run(tmp_path, [{"id": "s01", "url": "https://a", "title": "A",
                             "credibility": "high", "recency": 2, "bias": 2, "total": 13}])
    assert bs.collect_rows(d)[0]["total"] == ""


def test_enum_strict_access_matches_validate_structure_vocab():
    # Both gates must accept the same access values, or a fetcher is told to "fix" a valid one.
    sys.path.insert(0, str(REPO / "eval"))
    import validate_structure as vs  # noqa: E402
    assert {v.upper() for v in bs.ENUMS["access"]} == vs.ACCESS_VOCAB
