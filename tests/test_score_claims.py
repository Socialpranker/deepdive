"""Tests for scripts/score_claims.py — status and confidence ceiling by counting."""

import csv
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import build_sources_csv as bsc  # noqa: E402
import score_claims as sc  # noqa: E402
import validate_phases as vp  # noqa: E402

FAT = "> quote one\n\n> quote two\n"


def src(
    d: Path,
    num: str,
    *,
    url: str,
    type_: str = "Industry-media",
    cred: int = 3,
    root: str = "",
    path: str = "",
    thin: bool = False,
    **extra: str | int,
) -> None:
    sd = d / "sources"
    sd.mkdir(exist_ok=True)
    fm = [f"url: {url}", f"type: {type_}", f"credibility: {cred}"]
    fm += [f"{k}: {v}" for k, v in extra.items()]
    if root:
        fm.append(f"root: {root}")
    if path:
        fm.append(f"discovery_path: {path}")
    (sd / f"{num}_s.md").write_text(
        "---\n" + "\n".join(fm) + "\n---\n" + ("no quotes\n" if thin else FAT),
        encoding="utf-8",
    )


def ledger(d: Path, *rows: dict, extra: tuple[str, ...] = ()) -> None:
    cols = list(vp.CLAIMS_CORE) + list(extra)
    with (d / "claims.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "-") for c in cols})


def build(d: Path) -> None:
    (d / "sources.csv").write_text(
        bsc.render_csv(bsc.collect_rows(d)), encoding="utf-8"
    )


def three_independent(d: Path, *, primary: bool = True) -> None:
    src(
        d,
        "01",
        url="https://a.org/1",
        type_="Primary" if primary else "Academic",
        cred=5,
        root="r1",
        path="web|q1|en",
    )
    src(
        d,
        "02",
        url="https://b.org/2",
        type_="Academic",
        cred=4,
        root="r2",
        path="academic|q2|en",
    )
    src(d, "03", url="https://c.org/3", root="r3", path="news|q3|ru")


def scored(d: Path) -> dict:
    results, _ = sc.run(d, write=False)
    return results[0]


def test_triangulated_with_primary_allows_high(tmp_path):
    three_independent(tmp_path)
    ledger(
        tmp_path,
        {
            "claim_id": "CL1",
            "claim": "X grew",
            "sources": "s01;s02;s03",
            "status": "triangulated",
            "confidence": "high",
        },
    )
    build(tmp_path)
    r = scored(tmp_path)
    assert (r["status"], r["ceiling"], r["violations"]) == ("triangulated", "high", [])


def test_triangulated_without_primary_caps_medium(tmp_path):
    three_independent(tmp_path, primary=False)
    ledger(
        tmp_path,
        {
            "claim_id": "CL1",
            "claim": "X grew",
            "sources": "s01;s02;s03",
            "status": "triangulated",
            "confidence": "high",
        },
    )
    build(tmp_path)
    r = scored(tmp_path)
    assert r["ceiling"] == "medium"
    assert any("confidence high -> medium" in v for v in r["violations"])


def test_model_triangulated_on_two_sources_is_downgraded(tmp_path):
    """The audit's 18: `triangulated` typed on fewer than 3 sources."""
    three_independent(tmp_path)
    ledger(
        tmp_path,
        {
            "claim_id": "CL1",
            "claim": "X grew",
            "sources": "s01;s02",
            "status": "triangulated",
            "confidence": "high",
        },
    )
    build(tmp_path)
    r = scored(tmp_path)
    assert r["status"] == "weak"
    assert any("status triangulated -> weak" in v for v in r["violations"])


def test_same_url_twice_is_one_leg(tmp_path):
    """The audit's co-citing duplicates: two files of one document are one voice."""
    three_independent(tmp_path)
    src(
        tmp_path,
        "04",
        url="http://www.C.org/3/?utm_source=x#top",
        root="r4",
        path="x|q|en",
    )
    ledger(
        tmp_path,
        {
            "claim_id": "CL1",
            "claim": "X grew",
            "sources": "s01;s03;s04",
            "status": "triangulated",
            "confidence": "high",
        },
    )
    build(tmp_path)
    r = scored(tmp_path)
    assert r["legs"] == 2 and r["status"] == "weak"
    assert any("s04=s03" in v for v in r["violations"])
    _, dups = sc.run(tmp_path, write=False)
    assert dups == [["s03", "s04"]]


def test_thin_source_is_not_a_leg(tmp_path):
    three_independent(tmp_path)
    src(tmp_path, "03", url="https://c.org/3", root="r3", path="news|q3|ru", thin=True)
    ledger(
        tmp_path,
        {
            "claim_id": "CL1",
            "claim": "X grew",
            "sources": "s01;s02;s03",
            "status": "triangulated",
            "confidence": "high",
        },
    )
    build(tmp_path)
    assert scored(tmp_path)["legs"] == 2


def test_missing_roots_count_as_one_unknown_root(tmp_path):
    src(tmp_path, "01", url="https://a.org", type_="Primary", cred=5, path="a|1|en")
    src(tmp_path, "02", url="https://b.org", type_="Academic", path="b|2|en")
    src(tmp_path, "03", url="https://c.org", path="c|3|en")
    ledger(
        tmp_path,
        {
            "claim_id": "CL1",
            "claim": "X grew",
            "sources": "s01;s02;s03",
            "status": "triangulated",
            "confidence": "high",
        },
    )
    build(tmp_path)
    assert scored(tmp_path)["status"] == "single-root"


def test_one_source_empirical_high_goes_low(tmp_path):
    """The audit's 282: `high` on a single source."""
    three_independent(tmp_path)
    ledger(
        tmp_path,
        {
            "claim_id": "CL1",
            "claim": "X grew",
            "sources": "s01",
            "status": "weak",
            "confidence": "high",
        },
    )
    build(tmp_path)
    assert scored(tmp_path)["confidence"] == "low"


def test_documentary_high_on_one_primary_is_legal(tmp_path):
    three_independent(tmp_path)
    ledger(
        tmp_path,
        {
            "claim_id": "CL1",
            "claim": "Закон 152-ФЗ требует согласия родителя",
            "sources": "s01",
            "status": "weak",
            "confidence": "high",
            "claim_class": "documentary",
        },
        extra=("claim_class",),
    )
    build(tmp_path)
    r = scored(tmp_path)
    assert (r["ceiling"], r["violations"]) == ("high", [])


def test_documentary_on_secondary_is_not_high(tmp_path):
    """Control: the class does not bless any single source, only a primary one."""
    three_independent(tmp_path)
    ledger(
        tmp_path,
        {
            "claim_id": "CL1",
            "claim": "Закон требует согласия",
            "sources": "s03",
            "status": "weak",
            "confidence": "high",
            "claim_class": "documentary",
        },
        extra=("claim_class",),
    )
    build(tmp_path)
    assert scored(tmp_path)["ceiling"] == "medium"


@pytest.mark.parametrize(
    "caveat,ceiling",
    [("vendor", "medium"), ("self-reported", "medium"), ("disputed:s02", "low")],
)
def test_caveat_caps_ceiling(tmp_path, caveat, ceiling):
    three_independent(tmp_path)
    ledger(
        tmp_path,
        {
            "claim_id": "CL1",
            "claim": "X grew",
            "sources": "s01;s02;s03",
            "status": "triangulated",
            "confidence": "high",
            "source_caveat": caveat,
        },
    )
    build(tmp_path)
    assert scored(tmp_path)["ceiling"] == ceiling


def test_primary_dissent_makes_contested(tmp_path):
    three_independent(tmp_path)
    src(
        tmp_path,
        "09",
        url="https://reg.gov",
        type_="Primary",
        cred=5,
        root="reg",
        path="r|q|ru",
    )
    ledger(
        tmp_path,
        {
            "claim_id": "CL1",
            "claim": "X is allowed",
            "sources": "s01;s02;s03",
            "dissent": "s09",
            "status": "triangulated",
            "confidence": "high",
        },
    )
    build(tmp_path)
    r = scored(tmp_path)
    assert (r["status"], r["ceiling"]) == ("contested", "medium")


def test_content_verdict_is_kept(tmp_path):
    three_independent(tmp_path)
    ledger(
        tmp_path,
        {
            "claim_id": "CL1",
            "claim": "X grew",
            "sources": "s01;s02;s03",
            "status": "data-insufficient",
            "confidence": "low",
        },
    )
    build(tmp_path)
    r = scored(tmp_path)
    assert (r["status"], r["violations"]) == ("data-insufficient", [])


@pytest.mark.parametrize(
    "claim,compound",
    [
        ("X grew 20%; Y fell 5%", True),
        ("X grew 20%. Y fell 5%.", True),
        ("Рынок вырос. Лидер — Roblox", True),
        ("X grew 20% in 2025.", False),
        ("Vendors, e.g. Apple, ship it", False),
        ("Норма ст. 7 т. е. Минпросвещения отвечает", False),
    ],
)
def test_compound_detection(claim, compound):
    assert sc.is_compound(claim) is compound


def test_write_fixes_ledger_and_leaves_only_unfixable(tmp_path):
    three_independent(tmp_path)
    src(tmp_path, "04", url="https://c.org/3", root="r4", path="x|q|en")
    ledger(
        tmp_path,
        {
            "claim_id": "CL1",
            "claim": "X grew",
            "sources": "s01;s03;s04",
            "roots": "own;own;own",
            "status": "triangulated",
            "confidence": "high",
        },
        {
            "claim_id": "CL2",
            "claim": "A rose; B fell",
            "sources": "s01;s02;s03",
            "status": "triangulated",
            "confidence": "high",
        },
    )
    build(tmp_path)
    results, _ = sc.run(tmp_path, write=True)
    rows = list(csv.DictReader((tmp_path / "claims.csv").read_text().splitlines()))
    assert rows[0]["sources"] == "s01;s03"
    assert rows[0]["roots"] == "r1;r3"
    assert (rows[0]["status"], rows[0]["confidence"], rows[0]["primary_source"]) == (
        "weak",
        "low",
        "Y",
    )
    assert results[0]["violations"] == []
    assert results[1]["violations"] == ["compound claim — split into atomic rows"]
    data = json.loads((tmp_path / ".verify" / "claim_scores.json").read_text())
    assert data["results"][1]["violations"] == ["compound claim — split into atomic rows"]


def test_off_contract_ledger_is_refused(tmp_path):
    three_independent(tmp_path)
    (tmp_path / "claims.csv").write_text("claim_id,status\nCL1,triangulated\n")
    build(tmp_path)
    with pytest.raises(SystemExit, match="off-contract"):
        sc.run(tmp_path, write=False)


def test_duplicate_keeps_lowest_id_in_every_claim(tmp_path):
    """Order in the cell must not decide which file survives the merge."""
    three_independent(tmp_path)
    src(tmp_path, "04", url="https://c.org/3", root="r4", path="x|q|en")
    ledger(
        tmp_path,
        {"claim_id": "CL1", "claim": "A", "sources": "s04;s01", "status": "weak", "confidence": "low"},
        {"claim_id": "CL2", "claim": "B", "sources": "s04", "status": "weak", "confidence": "low"},
    )
    build(tmp_path)
    results, _ = sc.run(tmp_path, write=True)
    rows = list(csv.DictReader((tmp_path / "claims.csv").read_text().splitlines()))
    assert [r["sources"] for r in rows] == ["s03;s01", "s03"]
    assert all(r["violations"] == [] for r in results)


def test_arxiv_abs_and_pdf_are_one_leg(tmp_path):
    """Same identity rule as the cross-run wiki (runner.wiki.canonical_url)."""
    three_independent(tmp_path)
    src(tmp_path, "04", url="https://arxiv.org/abs/2401.01234v2", root="r4", path="a|q|en")
    src(tmp_path, "05", url="https://arxiv.org/pdf/2401.01234.pdf", root="r5", path="b|q|en")
    ledger(tmp_path, {"claim_id": "CL1", "claim": "X", "sources": "s04;s05", "status": "weak", "confidence": "low"})
    build(tmp_path)
    assert scored(tmp_path)["legs"] == 1


def _own_claim(d: Path, roots: tuple[str, str, str]) -> dict:
    src(d, "01", url="https://a.org/1", type_="Primary", cred=5, root=roots[0], path="web|q1|en")
    src(d, "02", url="https://b.org/2", type_="Academic", cred=5, root=roots[1], path="academic|q2|en")
    src(d, "03", url="https://c.org/3", type_="Primary", cred=5, root=roots[2], path="news|q3|ru")
    ledger(
        d,
        {
            "claim_id": "CL1",
            "claim": "X grew",
            "sources": "s01;s02;s03",
            "status": "triangulated",
            "confidence": "high",
        },
    )
    build(d)
    return scored(d)


def test_own_root_each_source_is_its_own_root(tmp_path):
    # source_scoring.md: `own` is a class, not an id — two independent studies are two roots.
    r = _own_claim(tmp_path, ("own", "own", "own"))
    assert (r["status"], r["ceiling"]) == ("triangulated", "high")


def test_own_root_case_insensitive(tmp_path):
    assert _own_claim(tmp_path, ("Own", "OWN", "own"))["status"] == "triangulated"


def test_own_root_lab_experiment_stays_one_root(tmp_path):
    assert _own_claim(tmp_path, ("own-lab-x", "own-lab-x", "own-lab-x"))["status"] == "single-root"


def test_own_root_unclear_is_not_a_root(tmp_path):
    assert _own_claim(tmp_path, ("r1", "unclear", "unclear"))["status"] == "single-root"


def _total_claim(d: Path, third: dict) -> dict:
    src(d, "01", url="https://a.org/1", type_="Primary", cred=5, root="r1", path="web|q1|en", recency=4, bias=4)
    src(d, "02", url="https://b.org/2", type_="Academic", cred=4, root="r2", path="academic|q2|en", recency=4, bias=4)
    src(d, "03", url="https://c.org/3", root="r3", path="news|q3|ru", **third)
    ledger(d, {"claim_id": "CL1", "claim": "X grew", "sources": "s01;s02;s03",
               "status": "triangulated", "confidence": "high"})
    build(d)
    return scored(d)


def test_total_below_8_is_not_a_leg(tmp_path):
    # rules.md: no conclusions on sources with total < 8 — such a source is no leg.
    r = _total_claim(tmp_path, {"cred": 2, "recency": 3, "bias": 2})
    assert (r["legs"], r["status"]) == (2, "weak")


def test_total_8_is_a_leg(tmp_path):
    assert _total_claim(tmp_path, {"cred": 3, "recency": 3, "bias": 2})["status"] == "triangulated"


def test_total_is_recomputed_not_trusted(tmp_path):
    # The written total (13) is ignored: the sum of the three axes is 6.
    r = _total_claim(tmp_path, {"cred": 2, "recency": 2, "bias": 2, "total": 13})
    assert r["status"] == "weak"


def test_total_unknown_axes_keep_the_leg(tmp_path):
    # Archived runs often lack recency/bias: no total is not a low total.
    assert _total_claim(tmp_path, {"cred": 3})["status"] == "triangulated"


def test_total_low_dissent_does_not_contest(tmp_path):
    src(tmp_path, "04", url="https://d.org/4", type_="Primary", cred=4, recency=1, bias=2)
    _total_claim(tmp_path, {"cred": 3, "recency": 3, "bias": 2})
    ledger(tmp_path, {"claim_id": "CL1", "claim": "X grew", "sources": "s01;s02;s03",
                      "dissent": "s04", "status": "triangulated", "confidence": "high"})
    assert scored(tmp_path)["status"] == "triangulated"
