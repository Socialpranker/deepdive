"""Тесты сборки отчёта — scripts/report_charts.py и scripts/build_report.py.

Несущая часть здесь — отказы. Сборка, которая молча пропустила сноску, битую
ссылку или число без строки в ledger'е, выглядит успешной и отдаёт документ,
у которого часть утверждений лишилась источника. Поэтому проверяется не то,
что «файл записался», а то, что расхождение роняет сборку.
"""

import csv
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import build_report as br  # noqa: E402
import report_charts as rc  # noqa: E402

NUMBERS = [
    {
        "num_id": "N1",
        "value": "19.1",
        "unit": "%",
        "kind": "verbatim",
        "formula": "-",
        "inputs": "-",
        "group": "-",
        "claim_id": "C1",
        "sources": "s01",
        "as_of": "2026-07-13",
    },
    {
        "num_id": "N2",
        "value": "44.9",
        "unit": "%",
        "kind": "verbatim",
        "formula": "-",
        "inputs": "-",
        "group": "-",
        "claim_id": "C1",
        "sources": "s01",
        "as_of": "2026-06-13",
    },
    {
        "num_id": "N3",
        "value": "82.4",
        "unit": "%",
        "kind": "verbatim",
        "formula": "-",
        "inputs": "-",
        "group": "-",
        "claim_id": "C2",
        "sources": "s02",
        "as_of": "2026-07-01",
    },
    {
        "num_id": "N7",
        "value": "135.8",
        "unit": "%",
        "kind": "derived",
        "formula": "(b-a)/a*100",
        "inputs": "a=3.63[s04]; b=8.56[s04]",
        "group": "-",
        "claim_id": "C4",
        "sources": "s04",
        "as_of": "2026-08-01",
    },
]

SOURCES = [
    {
        "id": "s01",
        "url": "https://example.com/a",
        "title": "Источник A",
        "type": "Industry-media",
        "credibility": "3",
        "as_of": "2026-07-13",
        "access": "OPEN",
        "fetch_tier": "webfetch",
    },
    {
        "id": "s02",
        "url": "https://example.com/b",
        "title": "Источник B",
        "type": "Primary",
        "credibility": "5",
        "as_of": "2026-07-01",
        "access": "OPEN",
        "fetch_tier": "http",
    },
]


def write_csv(path, rows):
    path.write_text("", encoding="utf-8")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


@pytest.fixture
def run(tmp_path):
    write_csv(tmp_path / "numbers.csv", NUMBERS)
    write_csv(tmp_path / "sources.csv", SOURCES)
    return tmp_path


def figure(**over):
    base = {
        "fig_id": "F1",
        "form": "bar",
        "numbers": "N1;N2",
        "labels": "Все;Топ",
        "notes": "",
        "title": "Заголовок",
        "subtitle": "подзаголовок",
        "caption": "подпись",
        "legend": "",
    }
    base.update(over)
    return base


# --- гарантия ledger'а -----------------------------------------------------


def test_number_absent_from_ledger_cannot_be_drawn(run):
    """Ядро всей затеи: график не может утверждать больше таблицы чисел."""
    nums = rc.load_numbers(run)
    with pytest.raises(rc.FigureError, match="N99"):
        rc.render(figure(numbers="N1;N99"), nums)


def test_known_numbers_render(run):
    svg = rc.render(figure(), rc.load_numbers(run))
    assert svg.startswith("<svg")
    assert "19,1" in svg and "44,9" in svg


def test_mark_carries_its_source_and_date(run):
    """Провенанс приезжает из ledger'а, а не пишется в подпись руками."""
    svg = rc.render(figure(numbers="N1;N3"), rc.load_numbers(run))
    assert "[s01]" in svg and "[s02]" in svg
    assert "2026-06-13" in svg or "2026-07-01" in svg or "2026-07-13" in svg


def test_derived_number_shows_its_formula(run):
    """У производного числа читатель должен иметь возможность пересчитать."""
    svg = rc.render(figure(numbers="N7;N1", form="bar"), rc.load_numbers(run))
    assert "(b-a)/a*100" in svg


def test_russian_decimal_separator_matches_the_prose():
    assert rc.ru(19.1) == "19,1"
    assert rc.ru(82.4) == "82,4"


def test_unknown_form_is_refused(run):
    with pytest.raises(rc.FigureError, match="неизвестная форма"):
        rc.render(figure(form="pie"), rc.load_numbers(run))


def test_pie_is_not_among_the_forms():
    """Доли не сравниваются углами — формы pie в наборе нет намеренно."""
    assert "pie" not in rc.FORMS
    assert set(rc.FORMS) == {"bar", "slope", "share", "dot", "line"}


def test_untitled_figure_is_refused(run):
    with pytest.raises(rc.FigureError, match="заголов"):
        rc.render(figure(title=""), rc.load_numbers(run))


def test_slope_needs_exactly_two_points(run):
    nums = rc.load_numbers(run)
    with pytest.raises(rc.FigureError, match="ровно 2"):
        rc.render(figure(form="slope", numbers="N1;N2;N3"), nums)


def test_missing_numbers_csv_is_refused(tmp_path):
    with pytest.raises(rc.FigureError, match="numbers.csv"):
        rc.load_numbers(tmp_path)


# --- сноски на поля --------------------------------------------------------

WRAPPED = """<p>Текст<a href="#fn1" class="footnote-ref" id="fnref1">1</a> и ещё<a
href="#fn2" class="footnote-ref" id="fnref2">2</a>.</p>
<section class="footnotes"><ol>
<li id="fn1"><p>Первая<a href="#fnref1" class="footnote-back">↩</a></p></li>
<li id="fn2"><p>Вторая<a href="#fnref2" class="footnote-back">↩</a></p></li>
</ol></section>"""


def test_sidenotes_survive_tags_wrapped_across_lines():
    """pandoc переносит строки внутри тега; разбор обязан это пережить."""
    out, moved = br.sidenotes(WRAPPED)
    assert moved == 2
    assert out.count('class="sidenote"') == 2
    assert "Первая" in out and "Вторая" in out


def test_footnote_block_is_removed_after_the_move():
    out, _ = br.sidenotes(WRAPPED)
    assert 'class="footnotes"' not in out


def test_losing_a_sidenote_fails_the_build(monkeypatch):
    """Гард против самой опасной поломки: текст цел, источник исчез, всё зелено."""
    import re

    monkeypatch.setattr(
        br,
        "FOOTNOTE_REF",
        re.compile(r'<a href="#fn(\d+)"[^>]*class="footnote-ref"[^>]*>.*?</a>', re.S),
    )
    with pytest.raises(br.BuildError, match="потерялась бы молча"):
        br.sidenotes(WRAPPED)


# Так сноски пишет pandoc 2.x (ubuntu-latest ставит его из apt): у <li> есть
# role="doc-endnote", у backlink — role="doc-backlink". pandoc 3.x (macOS автора)
# role у <li> не пишет. Разбор обязан пережить обе формы.
WRAPPED_PANDOC2 = """<p>Текст<a href="#fn1" class="footnote-ref" id="fnref1" role="doc-noteref"><sup>1</sup></a> и ещё<a href="#fn2" class="footnote-ref" id="fnref2" role="doc-noteref"><sup>2</sup></a>.</p>
<section class="footnotes" role="doc-endnotes">
<hr />
<ol>
<li id="fn1" role="doc-endnote"><p>Первая<a href="#fnref1" class="footnote-back" role="doc-backlink">↩︎</a></p></li>
<li id="fn2" role="doc-endnote"><p>Вторая<a href="#fnref2" class="footnote-back" role="doc-backlink">↩︎</a></p></li>
</ol>
</section>"""


def test_sidenotes_survive_pandoc2_attributes():
    out, moved = br.sidenotes(WRAPPED_PANDOC2)
    assert moved == 2
    assert out.count('class="sidenote"') == 2
    assert "Первая" in out and "Вторая" in out
    assert "footnote-back" not in out and "↩" not in out


# pandoc 3.1.x (в apt у ubuntu-latest) кладёт сноски не в <section>, а в <aside>;
# 2.x и 3.10 — в <section>. Разбор обязан пережить оба тега.
ASIDE_PANDOC313 = """<p>Текст<a href="#fn1" class="footnote-ref" id="fnref1" role="doc-noteref"><sup>1</sup></a></p>
<aside id="footnotes" class="footnotes footnotes-end-of-document" role="doc-endnotes">
<hr />
<ol>
<li id="fn1"><p>Первая<a href="#fnref1" class="footnote-back" role="doc-backlink">↩︎</a></p></li>
</ol>
</aside>"""


def test_sidenotes_survive_aside_container():
    out, moved = br.sidenotes(ASIDE_PANDOC313)
    assert moved == 1
    assert '<aside class="sidenote">Первая</aside>' in out
    assert "footnotes" not in out


def test_footnote_refs_without_a_block_fail_the_build():
    """Контейнер не распознан — отказ, а не тихий ноль: так CI и молчал."""
    with pytest.raises(br.BuildError, match="блок сносок не найден"):
        br.sidenotes(
            '<p>Т<a href="#fn1" class="footnote-ref" id="fnref1">1</a></p>'
            '<figure class="footnotes"><ol></ol></figure>'
        )


def test_unparsable_footnote_block_fails_the_build():
    """Блок сносок есть, разобрать нечего — отказ, а не тихий ноль."""
    with pytest.raises(br.BuildError, match="ни одна не разобрана"):
        br.sidenotes('<p>Текст.</p><section class="footnotes"><ol></ol></section>')


def test_document_without_footnotes_is_fine():
    out, moved = br.sidenotes("<p>Просто текст.</p>")
    assert moved == 0 and "sidenote" not in out


# --- ссылки на источники ---------------------------------------------------


def test_known_source_ref_becomes_a_link():
    out, dangling = br.link_sources("<p>Утверждение [s01].</p>", {"s01"})
    assert 'href="#s01"' in out
    assert dangling == []


def test_dangling_source_ref_is_reported():
    _, dangling = br.link_sources("<p>Утверждение [s77].</p>", {"s01"})
    assert dangling == ["s77"]


def test_refs_inside_tags_are_left_alone():
    """Внутри атрибутов и подписей SVG подменять нельзя — сломается разметка."""
    src = '<img alt="[s01]"><p>[s01]</p>'
    out, _ = br.link_sources(src, {"s01"})
    assert 'alt="[s01]"' in out
    assert out.count('href="#s01"') == 1


def test_sources_appendix_lists_every_row():
    out = br.sources_appendix(SOURCES)
    assert 'id="s01"' in out and 'id="s02"' in out
    assert "Источник A" in out and "Primary" in out


def test_empty_sources_produce_no_appendix():
    assert br.sources_appendix([]) == ""


# --- фигуры в тексте -------------------------------------------------------


def test_figure_token_is_replaced_by_inline_svg(tmp_path):
    (tmp_path / "F1.svg").write_text("<svg/>", encoding="utf-8")
    out, missing = br.inline_figures("{{fig:F1}}", tmp_path, [figure()])
    assert "<figure>" in out and "<svg/>" in out and "Рис. 1" in out
    assert missing == []


def test_missing_figure_is_reported(tmp_path):
    _, missing = br.inline_figures("{{fig:F9}}", tmp_path, [figure()])
    assert missing == ["F9"]


# --- сборка целиком --------------------------------------------------------


REPORT_MD = """# Отчёт

Утверждение с источником [s01].[^a]

[^a]: Оговорка к утверждению.

{{fig:F1}}
"""


def test_strict_build_refuses_a_dangling_reference(run):
    write_csv(run / "figures.csv", [figure()])
    (run / "2026-08-24_validation.md").write_text(
        REPORT_MD.replace("[s01]", "[s99]"), encoding="utf-8"
    )
    with pytest.raises(br.BuildError, match="несуществующ"):
        br.build(run, {"html"})


def test_report_file_must_exist(run):
    with pytest.raises(br.BuildError, match="YYYY-MM-DD"):
        br.build(run, {"html"})


@pytest.mark.skipif(not br.shutil.which("pandoc"), reason="нужен pandoc")
def test_end_to_end_html(run):
    write_csv(run / "figures.csv", [figure()])
    (run / "2026-08-24_validation.md").write_text(REPORT_MD, encoding="utf-8")
    res = br.build(run, {"html"})
    assert res["figures"] == 1
    assert res["sidenotes"] == 1
    assert res["problems"] == []
    html = (run / "2026-08-24_validation.html").read_text(encoding="utf-8")
    assert 'class="sidenote"' in html
    assert 'href="#s01"' in html
    assert "<svg" in html
    assert 'id="sources-appendix"' in html


@pytest.mark.skipif(not br.shutil.which("pandoc"), reason="нужен pandoc")
def test_css_is_inlined_so_the_html_stands_alone(run):
    write_csv(run / "figures.csv", [figure()])
    (run / "2026-08-24_validation.md").write_text(REPORT_MD, encoding="utf-8")
    br.build(run, {"html"})
    html = (run / "2026-08-24_validation.html").read_text(encoding="utf-8")
    assert "--paper" in html and "<link" not in html


def declarations() -> str:
    """CSS без комментариев: `#000` в пояснении «почему не #000» — не нарушение."""
    import re

    css = (REPO / "assets" / "report.css").read_text(encoding="utf-8")
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S).lower()


def test_paper_is_tinted_and_ink_is_not_pure_black():
    """Чек направления e-ink: чистый #fff/#000 — телл, а не бумага."""
    css = declarations()
    assert "#f5f2ea" in css
    assert "#ffffff" not in css
    assert "#000" not in css


def test_no_shadows_or_gradients_in_the_document_shell():
    """Ещё один чек направления: ноль теней и градиентов."""
    css = declarations()
    assert "box-shadow" not in css
    assert "text-shadow" not in css
