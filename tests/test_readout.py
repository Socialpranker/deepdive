"""Человеческая версия прогона: readout.md -> страница + полный PDF/DOCX."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_readout as rd  # noqa: E402
import build_report as br  # noqa: E402

needs_pandoc = pytest.mark.skipif(not br.shutil.which("pandoc"), reason="нужен pandoc")

SOURCES = [
    {
        "id": "s01",
        "url": "https://a.example/x",
        "title": "Первый",
        "author": "unknown",
        "date": "2026-09-01",
        "type": "Primary",
        "credibility": "5",
        "access": "OPEN",
        "used": "Y",
    },
    {
        "id": "s02",
        "url": "https://www.b.example/y",
        "title": "Второй",
        "author": "Автор",
        "date": "2026-08-01",
        "type": "Expert-blog",
        "credibility": "2",
        "access": "PARTIAL",
        "used": "Y",
    },
]
CLAIMS = [
    {
        "claim_id": "CL1",
        "claim": "тех. формулировка",
        "sources": "s01",
        "status": "triangulated",
        "confidence": "high",
        "source_caveat": "vendor",
        "dissent": "-",
        "as_of": "2026-09",
        "evidence_kind": "fact",
        "plain": "Компания купила другую",
        "detail": "Объявлено 18.09",
    },
    {
        "claim_id": "CL2",
        "claim": "второй",
        "sources": "s02",
        "status": "contested",
        "confidence": "low",
        "source_caveat": "-",
        "dissent": "s01",
        "as_of": "-",
        "evidence_kind": "position",
        "plain": "Практик против",
        "detail": "",
    },
    {
        "claim_id": "CL3",
        "claim": "без типа",
        "sources": "s01",
        "status": "weak",
        "confidence": "low",
        "source_caveat": "-",
        "dissent": "-",
        "as_of": "-",
    },
]
NUMBERS = [
    {
        "num_id": "N1",
        "value": "9.5",
        "unit": "$/мес",
        "kind": "verbatim",
        "formula": "-",
        "claim_id": "CL1",
        "sources": "s01",
        "as_of": "2026-09-29",
        "label": "Цена",
    },
]
READOUT = """---
title: "Вопрос: есть ли ниша"
question: "Есть ли место?"
date: 2026-09-29
---

## Ответ

Нет.
Уверенность: средняя — один замер.

## Делать

- Ждать.

## Не делать

- Не покупать.

## Что поменяет решение

- **Если** X, **то** Y.

## Находки

### Компания купила другую {.high claims="CL1"}

Описание [s01][s02].

## Что говорит против

### Практик против {.contested claims="CL2"}

Мнение [s02].

## Чего не знаем

- Спрос.
"""


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


@pytest.fixture
def run(tmp_path):
    d = tmp_path / "niche-check"
    d.mkdir()
    write_csv(d / "sources.csv", SOURCES)
    write_csv(d / "claims.csv", CLAIMS)
    write_csv(d / "numbers.csv", NUMBERS)
    (d / "readout.md").write_text(READOUT, encoding="utf-8")
    return d


# --- язык леджера не просачивается к человеку --------------------------------


def test_ledger_ids_in_readout_are_caught():
    problems = rd.lint_readout("Сканеры заняли нишу (CL17), см. R1 и H2.")
    assert (
        problems
        and "CL17" in problems[0]
        and "R1" in problems[0]
        and "H2" in problems[0]
    )


def test_skill_jargon_in_readout_is_caught():
    problems = rd.lint_readout("Вилка 2 срабатывает, тезис contested.")
    assert any("вилка" in p and "contested" in p for p in problems)


def test_source_refs_and_heading_attributes_are_legal():
    assert (
        rd.lint_readout('### Вывод {.high claims="CL1;CL2"}\n\nТекст [s01][s12].') == []
    )


@needs_pandoc
def test_ledger_language_fails_the_strict_build(run):
    (run / "readout.md").write_text(
        READOUT.replace("Нет.", "Нет (CL1)."), encoding="utf-8"
    )
    with pytest.raises(br.BuildError, match="CL1"):
        rd.build(run, {"html"})


# --- карточки -----------------------------------------------------------------


def test_counterarguments_are_numbered_apart_from_findings():
    body = (
        '<h2>Находки</h2><h3 class="high">А</h3><p>x <sup class="refs">1</sup></p>'
        '<h2>Что говорит против</h2><h3 class="low">Б</h3><p>y <sup class="refs">1</sup></p>'
    )
    html, found, problems = rd.cards(body)
    assert [f["label"] for f in found] == ["Находка 1", "Против 1"]
    assert 'id="k2"' in html and problems == []


def test_card_without_confidence_or_source_is_a_problem():
    _, _, problems = rd.cards("<h2>Находки</h2><h3>Голый вывод</h3><p>без ссылок</p>")
    assert any("уверенности" in p for p in problems)
    assert any("источника" in p for p in problems)


def test_adjacent_refs_become_one_superscript_with_titles():
    sources = {r["id"]: r for r in SOURCES}
    html, dangling = rd.human_refs("<p>Факт [s01][s02].</p>", sources)
    assert dangling == []
    assert html.count("<sup") == 1
    assert 'href="#s01"' in html and ">1</a>, <a" in html
    assert 'title="Первый · 2026-09-01"' in html  # автор unknown не показывается
def test_dangling_ref_is_reported():
    _, dangling = rd.human_refs("<p>[s99]</p>", {})
    assert dangling == ["s99"]


# --- доказательная база -------------------------------------------------------


def test_evidence_is_grouped_by_kind_and_links_back_to_cards():
    sources = {r["id"]: r for r in SOURCES}
    found = [{"label": "Находка 1", "anchor": "k1", "claims": ["CL1"]}]
    html, used_by, warnings = rd.evidence_base(CLAIMS, NUMBERS, sources, found)
    assert (
        html.index("Цифры")
        < html.index("Факты и события")
        < html.index("Позиции и мнения")
    )
    assert "9,5 $/мес" in html  # русский десятичный разделитель, как в тексте
    assert 'href="#k1">находка 1' in html
    assert "данные самого продавца" in html and "vendor" not in html
    assert "возражают" in html
    assert used_by["s01"]  # указатель знает, какие пункты опираются на источник


def test_claims_without_kind_go_to_other_with_a_warning():
    html, _, warnings = rd.evidence_base(CLAIMS, [], {}, [])
    assert "Прочее" in html
    assert warnings and "evidence_kind" in warnings[0]


def test_caveat_labels_are_translated_and_empty_dropped():
    assert rd.caveat_word('"-"') == ""
    assert rd.caveat_word("disputed:s11") == "оспаривается другими источниками"
    assert rd.caveat_word("свободный текст") == "свободный текст"


def test_index_drops_unknown_author_and_flags_partial_access():
    html = rd.source_index(SOURCES, {"s01": [1, 1, 2]})
    assert "unknown" not in html
    assert "доступ частичный" in html
    assert "пункты" in html and "b.example" in html


# --- сборка целиком -----------------------------------------------------------


@needs_pandoc
def test_page_and_full_version_differ_in_what_they_carry(run):
    res = rd.build(run, {"html", "docx"})
    assert res["problems"] == []
    page = (run / "2026-09-29_niche-check.html").read_text(encoding="utf-8")
    full = (run / ".build" / "2026-09-29_niche-check_full.html").read_text(
        encoding="utf-8"
    )
    assert 'id="evidence"' not in page  # страница короткая
    assert 'class="specialist"' in page  # кухня свёрнута
    assert 'id="evidence"' in full and 'id="source-index"' in full
    assert (run / "2026-09-29_niche-check_full.docx").exists()
    assert "CL1" not in page.split("<body>")[1].replace('data-claims="CL1"', "")


@needs_pandoc
def test_missing_readout_is_an_error(tmp_path):
    with pytest.raises(br.BuildError, match="readout.md"):
        rd.build(tmp_path, {"html"})


def test_map_lists_human_files_first_and_keeps_foreign_readme(tmp_path):
    (tmp_path / "claims.csv").write_text("x\n", encoding="utf-8")
    page = tmp_path / "2026-09-29_x.html"
    page.write_text("", encoding="utf-8")
    m = rd.write_map(tmp_path, [page])
    text = m.read_text(encoding="utf-8")
    assert text.index("Человеку") < text.index("Агенту") and "claims.csv" in text
    (tmp_path / "README.md").write_text("своё", encoding="utf-8")
    assert rd.write_map(tmp_path, [page]) is None
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "своё"


# --- рамка + ядро по жанру ------------------------------------------------------

FRAME_MD = "## Ответ\n\nа. Уверенность: низкая.\n\n## Делать\n\n- д\n\n## Не делать\n\n- н\n\n## Что поменяет решение\n\n- б\n\n## Чего не знаем\n\n- в\n"


def test_frame_is_required_for_every_genre():
    for genre in rd.GENRES:
        problems = rd.lint_structure("## Ответ\n\nтолько ответ\n", genre)
        assert any("Что поменяет решение" in p for p in problems), genre
        assert any("Чего не знаем" in p for p in problems), genre


def test_each_genre_demands_its_core():
    cores = {"decision": "Варианты", "landscape": "Карта", "validation": "Доводы за",
             "explainer": "Как устроено", "qa": "Вопросы", "custom": "Находки"}
    for genre, core in cores.items():
        problems = rd.lint_structure(FRAME_MD, genre)
        assert any(core in p for p in problems), genre


def test_validation_does_not_demand_a_separate_against_section():
    md = FRAME_MD + "## Доводы за\n\n## Доводы против\n\n## Что изменило бы вердикт\n\n- г\n"
    assert rd.lint_structure(md, "validation") == []


def test_decision_options_need_a_table():
    md = FRAME_MD + "## Варианты\n\n### А\n\nтекст\n\n## Что говорит против\n"
    assert any("таблицы" in p for p in rd.lint_structure(md, "decision"))
    md_ok = md.replace("### А", "| Вариант | Цена |\n|---|---|\n| А | дёшево |\n\n### А")
    assert rd.lint_structure(md_ok, "decision") == []


def test_landscape_map_needs_players_under_categories():
    md = FRAME_MD + "## Карта\n\n### Сканеры\n\nтекст\n\n## Где пусто\n\n## Что говорит против\n"
    assert any("игроков" in p for p in rd.lint_structure(md, "landscape"))


def test_validation_cards_carry_strength_not_confidence():
    body = (
        "<h2>Доводы за</h2><h3 class=\"strong\">А</h3><p><sup class=\"refs\">1</sup></p>"
        "<h2>Доводы против</h2><h3>Б</h3><p><sup class=\"refs\">1</sup></p>"
    )
    html, found, problems = rd.cards(body)
    assert [f["label"] for f in found] == ["За 1", "Против 1"]
    assert "сильный довод" in html
    assert any("силы довода" in p and "Б" in p for p in problems)


def test_explainer_subsections_are_not_cards():
    body = "<h2>Как устроено</h2><h3>Шаг первый</h3><p>без источника</p>"
    html, found, problems = rd.cards(body)
    assert found == [] and problems == []


def test_decision_option_cards_need_sources_but_not_confidence():
    body = "<h2>Варианты</h2><h3>Вариант А</h3><p>x <sup class=\"refs\">1</sup></p>"
    _, found, problems = rd.cards(body)
    assert found[0]["label"] == "Вариант 1" and problems == []


def test_landscape_page_keeps_only_key_players():
    body = (
        "<h2 id=\"карта\">Карта</h2><h3>Сканеры</h3>"
        "<h4 class=\"key\">VibeLegit</h4><p><sup class=\"refs\">1</sup></p>"
        "<h4>Minor</h4><p><sup class=\"refs\">1</sup></p>"
    )
    html, found, problems = rd.cards(body)
    assert [f["label"] for f in found] == ["Игрок 1", "Игрок 2"] and problems == []
    page = rd.page_cut(html)
    assert "VibeLegit" in page and "Minor" not in page
    assert "2 игроков" in page


def test_genre_falls_back_to_the_technical_report(tmp_path):
    (tmp_path / "2026-09-29_landscape.md").write_text("x", encoding="utf-8")
    assert rd.genre_of({}, tmp_path) == "landscape"
    assert rd.genre_of({"genre": "validation"}, tmp_path) == "validation"
    assert rd.genre_of({"genre": "нечто"}, tmp_path) == "custom"


def test_answer_without_confidence_is_flagged():
    md = FRAME_MD.replace(" Уверенность: низкая.", "")
    assert any("уверенност" in p for p in rd.lint_structure(md, "custom"))
