"""Tests for the cross-run wiki layer.

The pairing tests come in matched pairs on purpose. A prefilter that emits nothing
passes every negative control there is, and a suite made only of negative controls would
report that as success — the failure mode this skill has hit before, where a green check
meant the check never ran. So every "must not become a conflict" case is accompanied by
a "must reach adjudication" case that would fail if the filter went silent.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from runner.wiki import (  # noqa: E402
    ClaimPage,
    canonical_url,
    candidate_pairs,
    claim_uid,
    entity_key,
    load_claims,
    load_sources,
    numbers,
    prefilter,
    source_key,
)

SCRIPTS = ROOT / "scripts"


# ------------------------------------------------------------------ normalization


@pytest.mark.parametrize(
    "a,b",
    [
        ("https://arxiv.org/abs/2608.27454", "https://arxiv.org/pdf/2608.27454"),
        ("https://arxiv.org/abs/2608.27454", "https://arxiv.org/html/2608.27454"),
        ("https://arxiv.org/abs/2608.27454", "https://arxiv.org/pdf/2608.27454v2"),
        ("https://example.com/a", "http://www.example.com/a/"),
        ("https://example.com/a", "https://example.com/a?utm_source=x&fbclid=y"),
        ("https://example.com/a#intro", "https://example.com/a"),
    ],
)
def test_same_document_folds_to_one_key(a, b):
    assert canonical_url(a) == canonical_url(b)


@pytest.mark.parametrize(
    "a,b",
    [
        ("https://arxiv.org/abs/2608.27454", "https://arxiv.org/abs/2608.27455"),
        ("https://example.com/a", "https://example.com/b"),
        ("https://example.com/a?page=2", "https://example.com/a?page=3"),
    ],
)
def test_different_documents_stay_apart(a, b):
    assert canonical_url(a) != canonical_url(b)


def test_doi_outranks_url():
    assert source_key("https://old.publisher/x", "10.1234/abc") == source_key(
        "https://new.publisher/y", "https://doi.org/10.1234/ABC"
    )


def test_entity_key_folds_corporate_noise_and_case():
    assert entity_key("Acme Inc.") == entity_key("acme") == "acme"
    assert entity_key("Ёлка") == entity_key("елка")


def test_claim_uid_is_stable_under_rewording():
    """5.7 pairs before synthesis, ingest writes after — the id must survive edits."""
    assert claim_uid("run-a", "C1") == claim_uid("run-a", "C1")
    assert claim_uid("run-a", "C1") != claim_uid("run-b", "C1")


def test_numbers_parses_both_decimal_conventions():
    assert (1234.56, "$") in numbers("стоит 1 234,56 $")
    assert (1234.56, "$") in numbers("costs 1,234.56 $")
    assert (40.0, "%") in numbers("выросло на 40%")


# ------------------------------------------------------- pairing: negative controls


def _claim(cid, run, text, as_of="2026-01-01", entities=("acme",), roots=("r1",)):
    return ClaimPage(
        id=cid,
        run=run,
        claim_id=cid,
        text=text,
        as_of=as_of,
        status="triangulated",
        entities=list(entities),
        roots=list(roots),
    )


NEGATIVE = {
    "stale figure is a version, not a disagreement": (
        _claim("n1", "new", "Acme занимает 40% рынка", as_of="2026-08-01"),
        _claim("o1", "old", "Acme занимает 25% рынка", as_of="2025-01-01"),
    ),
    "different units measure different quantities": (
        _claim("n2", "new", "у Acme 40% рынка", as_of="2026-08-01"),
        _claim("o2", "old", "у Acme 40 млн выручки", as_of="2026-07-01"),
    ),
    "different geography is a different claim": (
        _claim("n3", "new", "Acme держит 40% рынка в США", as_of="2026-08-01"),
        _claim("o3", "old", "Acme держит 12% рынка в ЕС", as_of="2026-07-01"),
    ),
    "median vs average is a different claim": (
        _claim("n4", "new", "медианная цена Acme 30 $", as_of="2026-08-01"),
        _claim("o4", "old", "средняя цена Acme 45 $", as_of="2026-07-01"),
    ),
    "no shared entity is never comparable": (
        _claim("n5", "new", "Acme держит 40% рынка", entities=("acme",)),
        _claim("o5", "old", "Globex держит 40% рынка", entities=("globex",)),
    ),
    "same entity, unrelated predicates": (
        _claim("n6", "new", "Acme основана в Берлине выходцами из телекома"),
        _claim("o6", "old", "Acme поддерживает импорт из Parquet и ORC"),
    ),
}


@pytest.mark.parametrize("label", sorted(NEGATIVE))
def test_negative_control_never_reaches_adjudication_as_conflict(label):
    new, old = NEGATIVE[label]
    _auto, todo = candidate_pairs([new], {old.id: old})
    assert todo == [], f"{label}: пара ушла бы к адъюдикатору и могла стать конфликтом"


# ------------------------------------------------------- pairing: positive controls


POSITIVE = {
    "same quantity, same period, different value": (
        _claim("p1", "new", "Acme занимает 40% рынка", as_of="2026-08-01"),
        _claim("q1", "old", "Acme занимает 25% рынка", as_of="2026-06-01"),
    ),
    "same predicate in prose, no numbers": (
        _claim("p2", "new", "Acme поддерживает логическую репликацию из коробки"),
        _claim("q2", "old", "Acme не поддерживает логическую репликацию без плагина"),
    ),
}


@pytest.mark.parametrize("label", sorted(POSITIVE))
def test_positive_control_does_reach_adjudication(label):
    new, old = POSITIVE[label]
    _auto, todo = candidate_pairs([new], {old.id: old})
    assert len(todo) == 1, (
        f"{label}: префильтр молчит — тогда и негативные тесты ничего не значат"
    )


def test_auto_resolution_labels_the_stale_pair_rather_than_dropping_it():
    """Superseded is recorded, not discarded: the wiki should show the version history."""
    new, old = NEGATIVE["stale figure is a version, not a disagreement"]
    auto, todo = candidate_pairs([new], {old.id: old})
    assert todo == []
    assert [p["verdict"] for p in auto] == ["superseded"]
    assert auto[0]["by"] == "auto"


def test_claims_from_the_same_run_never_pair():
    a = _claim("s1", "same", "Acme занимает 40% рынка")
    b = _claim("s2", "same", "Acme занимает 25% рынка")
    auto, todo = candidate_pairs([a], {b.id: b})
    assert (auto, todo) == ([], [])


# ------------------------------------------------------------------ ingest / record


def _make_run(
    tmp_path: Path, name: str, sources: list[dict], claims: list[dict]
) -> Path:
    d = tmp_path / name
    (d / "sources").mkdir(parents=True)
    with (d / "sources.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["id", "url", "title", "type", "credibility", "root", "caveat"],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(sources)
    with (d / "claims.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "claim_id",
                "claim",
                "status",
                "confidence",
                "as_of",
                "sources",
                "roots",
            ],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(claims)
    (d / "refresh_targets.md").write_text(
        "# Refresh targets\n\n## 1. Entities to track\n\n### Acme\n- **Type:** company\n",
        encoding="utf-8",
    )
    return d


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


@pytest.fixture()
def wiki_root(tmp_path):
    return tmp_path / "home"


def test_ingest_dedupes_one_source_across_two_runs(tmp_path, wiki_root):
    a = _make_run(
        tmp_path,
        "run-a",
        [
            {
                "id": "s01",
                "url": "https://arxiv.org/abs/2608.27454",
                "title": "P",
                "type": "academic",
                "credibility": "4",
                "root": "arxiv",
                "caveat": "-",
            }
        ],
        [
            {
                "claim_id": "C1",
                "claim": "Acme занимает 25% рынка",
                "status": "triangulated",
                "confidence": "high",
                "as_of": "2026-06-01",
                "sources": "s01",
                "roots": "arxiv",
            }
        ],
    )
    b = _make_run(
        tmp_path,
        "run-b",
        [
            {
                "id": "s01",
                "url": "https://arxiv.org/pdf/2608.27454v2",
                "title": "P",
                "type": "academic",
                "credibility": "5",
                "root": "arxiv",
                "caveat": "-",
            }
        ],
        [
            {
                "claim_id": "C1",
                "claim": "Acme занимает 40% рынка",
                "status": "triangulated",
                "confidence": "high",
                "as_of": "2026-08-01",
                "sources": "s01",
                "roots": "arxiv",
            }
        ],
    )

    for d in (a, b):
        r = _run(
            "wiki_ingest.py", "--research-dir", str(d), "--wiki-root", str(wiki_root)
        )
        assert r.returncode == 0, r.stderr

    sources = load_sources(wiki_root)
    assert len(sources) == 1, "три рендера одной статьи должны быть одной страницей"
    only = next(iter(sources.values()))
    assert only.runs == ["run-a", "run-b"]
    assert only.credibility == "5", "накопленная оценка — максимум из виденных"
    assert len(load_claims(wiki_root)) == 2, "утверждения разных прогонов не сливаются"


def test_ingest_is_idempotent_and_refreshes_edited_text(tmp_path, wiki_root):
    d = _make_run(
        tmp_path,
        "run-a",
        [
            {
                "id": "s01",
                "url": "https://example.com/x",
                "title": "X",
                "type": "web",
                "credibility": "3",
                "root": "example",
                "caveat": "-",
            }
        ],
        [
            {
                "claim_id": "C1",
                "claim": "Acme растёт",
                "status": "single-root",
                "confidence": "medium",
                "as_of": "2026-06-01",
                "sources": "s01",
                "roots": "example",
            }
        ],
    )
    _run("wiki_ingest.py", "--research-dir", str(d), "--wiki-root", str(wiki_root))
    (d / "claims.csv").write_text(
        (d / "claims.csv")
        .read_text(encoding="utf-8")
        .replace("Acme растёт", "Acme растёт в США"),
        encoding="utf-8",
    )
    _run("wiki_ingest.py", "--research-dir", str(d), "--wiki-root", str(wiki_root))

    claims = load_claims(wiki_root)
    assert len(claims) == 1, "повторный ingest не должен плодить записи"
    assert next(iter(claims.values())).text == "Acme растёт в США"


def test_pair_build_then_lint_is_clean(tmp_path, wiki_root):
    a = _make_run(
        tmp_path,
        "run-a",
        [
            {
                "id": "s01",
                "url": "https://example.com/a",
                "title": "A",
                "type": "web",
                "credibility": "4",
                "root": "example",
                "caveat": "-",
            }
        ],
        [
            {
                "claim_id": "C1",
                "claim": "Acme занимает 25% рынка",
                "status": "triangulated",
                "confidence": "high",
                "as_of": "2026-06-01",
                "sources": "s01",
                "roots": "example",
            }
        ],
    )
    _run("wiki_ingest.py", "--research-dir", str(a), "--wiki-root", str(wiki_root))

    b = _make_run(
        tmp_path,
        "run-b",
        [
            {
                "id": "s01",
                "url": "https://example.com/b",
                "title": "B",
                "type": "web",
                "credibility": "4",
                "root": "other",
                "caveat": "-",
            }
        ],
        [
            {
                "claim_id": "C1",
                "claim": "Acme занимает 40% рынка",
                "status": "triangulated",
                "confidence": "high",
                "as_of": "2026-08-01",
                "sources": "s01",
                "roots": "other",
            }
        ],
    )
    r = _run(
        "wiki_pair.py", "build", "--research-dir", str(b), "--wiki-root", str(wiki_root)
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(
        (b / ".verify" / "wiki_pairs.json").read_text(encoding="utf-8")
    )
    assert len(payload["pairs"]) == 1, "живое расхождение обязано дойти до адъюдикатора"

    _run("wiki_ingest.py", "--research-dir", str(b), "--wiki-root", str(wiki_root))
    lint = _run("wiki_lint.py", "--wiki-root", str(wiki_root))
    assert lint.returncode == 0, lint.stdout + lint.stderr


def test_record_refuses_a_half_populated_conflict(tmp_path, wiki_root):
    d = _make_run(tmp_path, "run-a", [], [])
    bad = tmp_path / "verdicts.json"
    bad.write_text(
        json.dumps(
            {
                "pairs": [
                    {
                        "left": "c-1",
                        "right": "c-2",
                        "verdict": "same-claim-conflict",
                        "left_run": "run-a",
                        "right_run": "run-b",
                        "left_as_of": "2026-06-01",
                        "right_as_of": "",
                        "left_roots": ["x"],
                        "right_roots": [],
                        "reason": "",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    r = _run(
        "wiki_pair.py",
        "record",
        "--research-dir",
        str(d),
        "--verdicts",
        str(bad),
        "--wiki-root",
        str(wiki_root),
    )
    assert r.returncode == 1
    assert "right_as_of" in r.stdout and "ничего не записано" in r.stdout
    assert not (wiki_root / "research/wiki/.wiki/pairs.jsonl").exists()


def test_record_rejects_an_invented_verdict_value(tmp_path, wiki_root):
    d = _make_run(tmp_path, "run-a", [], [])
    bad = tmp_path / "v.json"
    bad.write_text(
        json.dumps([{"left": "c-1", "right": "c-2", "verdict": "probably-conflict"}]),
        encoding="utf-8",
    )
    r = _run(
        "wiki_pair.py",
        "record",
        "--research-dir",
        str(d),
        "--verdicts",
        str(bad),
        "--wiki-root",
        str(wiki_root),
    )
    assert r.returncode == 1


def test_query_reports_an_empty_wiki_honestly(tmp_path, wiki_root):
    r = _run("wiki_query.py", "--topic", "что угодно", "--wiki-root", str(wiki_root))
    assert r.returncode == 0
    assert "первый ресёрч" in r.stdout or "молчит" in r.stdout


def test_prefilter_requires_a_shared_entity():
    a = _claim("x1", "new", "рынок вырос на 40%", entities=())
    b = _claim("x2", "old", "рынок вырос на 25%", entities=())
    assert prefilter(a, b) is None


def test_entity_attachment_is_order_independent(tmp_path, wiki_root):
    """A company first named in a later run must attach to earlier runs' claims too.

    Attachment depends on what the registry knew at the time, so computing it only at
    insert made the wiki's contents depend on ingest order — and the claims left without
    entities are exactly the ones phase 5.7 would have paired against.
    """
    early = _make_run(tmp_path, "run-early", [],
                      [{"claim_id": "C1", "claim": "Globex занимает 25% рынка",
                        "status": "triangulated", "confidence": "high",
                        "as_of": "2026-06-01", "sources": "s01", "roots": "example"}])
    (early / "refresh_targets.md").unlink()  # early run never named the entity
    _run("wiki_ingest.py", "--research-dir", str(early), "--wiki-root", str(wiki_root))
    assert not any(c.entities for c in load_claims(wiki_root).values())

    late = _make_run(tmp_path, "run-late", [],
                     [{"claim_id": "C1", "claim": "Globex вырос", "status": "single-root",
                       "confidence": "medium", "as_of": "2026-08-01", "sources": "s02",
                       "roots": "other"}])
    (late / "refresh_targets.md").write_text(
        "## 1. Entities to track\n\n### Globex — Series B $20M (2026-07-15)\n",
        encoding="utf-8")
    _run("wiki_ingest.py", "--research-dir", str(late), "--wiki-root", str(wiki_root))

    claims = load_claims(wiki_root)
    early_claim = next(c for c in claims.values() if c.run == "run-early")
    assert early_claim.entities == ["globex"], "ретро-привязка не сработала"


def test_entity_name_drops_the_descriptive_tail():
    """Z11 headings are phrases: `### Rosy — закрыт` must key on `rosy`, not the phrase."""
    from wiki_ingest import read_run_entities

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "refresh_targets.md").write_text(
            "## 1. Entities to track\n\n### Rosy — закрыт (2026-01)\n"
            "### AMI Labs — Ян Лекун\n### <Company placeholder>\n",
            encoding="utf-8")
        assert read_run_entities(d) == ["Rosy", "AMI Labs"]
