#!/usr/bin/env python3
"""Собрать отчёт прогона в HTML, PDF и DOCX из одного семантического источника.

Вход  — `<run>/<YYYY-MM-DD>_<genre>.md` плюс `numbers.csv`, `figures.csv`, `sources.csv`.
Выход — те же три формата рядом. Руками ни один из них не поддерживается: три
расходящихся файла это три разных отчёта, а не один в трёх видах.

Что делает сборка сверх конвертации:

* **Фигуры.** `report_charts.py` рисует SVG из ledger'а. Число без строки в
  `numbers.csv` нарисовать нельзя — сборка падает. График не может утверждать
  больше таблицы чисел.
* **Сноски на поля.** Автор пишет обычные markdown-сноски `[^1]`; для HTML и PDF
  они переносятся на поле ровно напротив своей строки (аппарат Тафти). В 15–20
  страницах источник у каждого утверждения иначе превращается в беготню по концу
  документа. В DOCX поля недоступны — там сноски остаются сносками.
* **Приложение источников** генерируется из `sources.csv`, и каждая ссылка `[sNN]`
  в тексте резолвится в него. Битая ссылка роняет сборку: в 20-страничном
  документе её не находят глазами.

Направление вёрстки — e-ink/paper (`assets/report.css`): тонированная бумага,
чернила не чистый чёрный, колонка 62 знака, ноль теней и градиентов, иерархия
кеглем и вертикальным ритмом. Убери цвет — структура не изменится.

Зависимости: pandoc (обязателен), Chromium/Chrome (только для PDF).
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

import mermaid_figures
import report_charts

SKILL = Path(__file__).resolve().parents[1]
CSS = SKILL / "assets" / "report.css"

REPORT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[a-z]+\.md$")

CHROME_CANDIDATES = [
    Path.home()
    / "Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell",
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
]


class BuildError(Exception):
    pass


def find_report(run: Path) -> Path:
    hits = sorted(p for p in run.glob("*.md") if REPORT_RE.match(p.name))
    if not hits:
        raise BuildError(f"в {run} нет файла вида YYYY-MM-DD_<genre>.md")
    return hits[-1]


def find_chrome() -> Path | None:
    for c in CHROME_CANDIDATES:
        if c.exists():
            return c
    found = shutil.which("chromium") or shutil.which("google-chrome")
    return Path(found) if found else None


def load_sources(run: Path) -> list[dict]:
    path = run / "sources.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def md_to_html(md_path: Path) -> str:
    """pandoc -> фрагмент HTML. Сноски пока обычные, на поля их уводит postprocess."""
    proc = subprocess.run(
        [
            "pandoc",
            str(md_path),
            "-f",
            "markdown+footnotes",
            "-t",
            "html5",
            "--no-highlight",
            # без этого pandoc переносит строки ВНУТРИ тега (`<a\nhref=...`),
            # и разбор по атрибутам молча теряет часть сносок
            "--wrap=none",
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise BuildError(f"pandoc не смог собрать HTML: {proc.stderr.strip()[:400]}")
    return proc.stdout


FOOTNOTE_REF = re.compile(
    r'<a\s(?=[^>]*class="footnote-ref")[^>]*?href="#fn(\d+)"[^>]*>.*?</a>', re.S
)
# Контейнер сносок у pandoc меняет ТЕГ между версиями: 2.x и 3.10 дают
# <section class="footnotes …">, а 3.1.x (он же в apt у ubuntu-latest) — <aside>.
# Привязка к <section> означала «сносок нет» на CI при живом документе.
FOOTNOTE_BLOCK = re.compile(
    r'<(section|aside|div)[^>]*class="[^"]*\bfootnotes\b[^"]*"[^>]*>.*?</\1>', re.S
)
# Атрибуты у <li> разнятся по версиям pandoc: 2.x пишет
# `<li id="fn1" role="doc-endnote">`, 3.x — просто `<li id="fn1">`. Привязка к
# точной форме тега давала ноль перенесённых сносок на ubuntu и единицу на macOS.
FOOTNOTE_ITEM = re.compile(r'<li\s(?=[^>]*\bid="fn(\d+)")[^>]*>(.*?)</li>', re.S)
FOOTNOTE_BACK = re.compile(r'<a\s(?=[^>]*class="footnote-back")[^>]*>.*?</a>', re.S)


def sidenotes(body: str) -> tuple[str, int]:
    """Перенести сноски на поле — каждую туда, где стоит её ссылка.

    Это и есть причина выбрать аппарат Тафти: источник виден, не покидая абзаца.
    Возвращает (html, сколько перенесено).
    """
    items = {}
    block = FOOTNOTE_BLOCK.search(body)
    if not block:
        if FOOTNOTE_REF.search(body):
            # Ссылки на сноски есть, а контейнера не видно — значит не совпал
            # разбор, а не «сносок нет». Без этой ветки такой случай возвращал
            # ноль и выглядел успехом (ровно так CI и пропускал pandoc 3.1.x).
            raise BuildError(
                "в тексте есть ссылки на сноски, но блок сносок не найден — "
                "разбор HTML сломан, все источники потерялись бы молча"
            )
        return body, 0
    for num, content in FOOTNOTE_ITEM.findall(block.group(0)):
        text = FOOTNOTE_BACK.sub("", content)
        text = re.sub(r"</?p>", "", text).strip()
        items[num] = text

    if not items:
        # Блок сносок есть, а разобрать из него нечего — значит сломан разбор,
        # а не документ. Без этого отказа сборка отдаёт «0 сносок» и выглядит
        # успешной ровно там, где потеряла все источники сразу.
        raise BuildError(
            "блок сносок найден, но ни одна не разобрана — "
            "разбор HTML сломан, все источники потерялись бы молча"
        )

    moved = 0

    def swap(m):
        nonlocal moved
        num = m.group(1)
        if num not in items:
            return m.group(0)
        moved += 1
        return f'<aside class="sidenote">{items[num]}</aside>'

    body = FOOTNOTE_REF.sub(swap, body)
    if moved != len(items):
        # Тихая потеря сноски неотличима от её отсутствия: текст выглядит целым,
        # а источник утверждения исчез. Поэтому отказ, а не предупреждение.
        raise BuildError(
            f"сносок в документе {len(items)}, на поля перенесено {moved} — "
            "разбор HTML сломан, часть источников потерялась бы молча"
        )
    body = FOOTNOTE_BLOCK.sub("", body)
    return body, moved


SRC_REF = re.compile(r"\[(s\d{2,3})\]")


def link_sources(body: str, known: set[str]) -> tuple[str, list[str]]:
    """Превратить [sNN] в ссылку на приложение. Неизвестный id — собираем и роняем."""
    dangling: list[str] = []

    def swap(m):
        sid = m.group(1)
        if sid not in known:
            dangling.append(sid)
            return m.group(0)
        return f'<a class="ref" href="#{sid}">[{sid}]</a>'

    # Не трогать то, что уже внутри тега (атрибуты, подписи фигур в SVG).
    parts = re.split(r"(<[^>]+>)", body)
    for i in range(0, len(parts), 2):
        parts[i] = SRC_REF.sub(swap, parts[i])
    return "".join(parts), sorted(set(dangling))


def sources_appendix(rows: list[dict]) -> str:
    if not rows:
        return ""
    out = [
        '<section id="sources-appendix">',
        '<h2><span class="num">A</span>Источники</h2>',
        '<dl class="sources">',
    ]
    for r in rows:
        sid = html.escape(r.get("id") or r.get("source_id") or "")
        title = html.escape(r.get("title") or r.get("url") or "без названия")
        meta = " · ".join(
            filter(
                None,
                [
                    html.escape(r.get("type") or ""),
                    f"credibility {html.escape(r.get('credibility', ''))}"
                    if r.get("credibility")
                    else "",
                    f"as_of {html.escape(r.get('as_of') or r.get('date') or '')}"
                    if (r.get("as_of") or r.get("date"))
                    else "",
                    f"access {html.escape(r.get('access', ''))}"
                    if r.get("access")
                    else "",
                    f"tier {html.escape(r.get('fetch_tier', ''))}"
                    if r.get("fetch_tier")
                    else "",
                ],
            )
        )
        url = html.escape(r.get("url") or "")
        link = f'<div class="meta"><a href="{url}">{url}</a></div>' if url else ""
        out.append(f'<dt id="{sid}">[{sid}]</dt>')
        out.append(f'<dd>{title}<div class="meta">{meta}</div>{link}</dd>')
    out += ["</dl>", "</section>"]
    return "\n".join(out)


FIG_TOKEN = re.compile(r"\{\{fig:([A-Za-z0-9_-]+)\}\}")


def inline_figures(
    body: str, build_dir: Path, figs: list[dict]
) -> tuple[str, list[str]]:
    """Заменить {{fig:F1}} на встроенный SVG с подписью. Неизвестный id — собираем."""
    captions = {f["fig_id"]: f.get("caption", "") for f in figs}
    order = {f["fig_id"]: i + 1 for i, f in enumerate(figs)}
    missing: list[str] = []

    def swap(m):
        fid = m.group(1)
        path = build_dir / f"{fid}.svg"
        if not path.exists():
            missing.append(fid)
            return m.group(0)
        svg = path.read_text(encoding="utf-8")
        cap = captions.get(fid, "")
        num = order.get(fid, "?")
        caption = f"<figcaption><b>Рис. {num}.</b> {cap}</figcaption>" if cap else ""
        return f"<figure>{svg}{caption}</figure>"

    return FIG_TOKEN.sub(swap, body), sorted(set(missing))


def wrap(body: str, title: str, css: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
{css}
</style>
</head>
<body>
<div class="doc">
{body}
</div>
</body>
</html>"""


def to_pdf(html_path: Path, pdf_path: Path) -> bool:
    chrome = find_chrome()
    if not chrome:
        return False
    proc = subprocess.run(
        [
            str(chrome),
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            f"file://{html_path}",
        ],
        capture_output=True,
        text=True,
    )
    return pdf_path.exists() and proc.returncode == 0


def to_docx(md_path: Path, docx_path: Path, build_dir: Path) -> bool:
    """DOCX для правок и согласования, не для чтения: боковых полей в Word нет.

    Сноски здесь остаются настоящими сносками — это честнее, чем сплющить их
    в абзацы посреди текста.
    """
    md = md_path.read_text(encoding="utf-8")
    md = FIG_TOKEN.sub(lambda m: f"![]({build_dir / (m.group(1) + '.svg')})", md)
    md = mermaid_figures.to_image_refs(md, build_dir)
    tmp = build_dir / "_docx_source.md"
    tmp.write_text(md, encoding="utf-8")
    proc = subprocess.run(
        [
            "pandoc",
            str(tmp),
            "-f",
            "markdown+footnotes",
            "-t",
            "docx",
            "--toc",
            "-o",
            str(docx_path),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"  DOCX не собран: {proc.stderr.strip()[:200]}", file=sys.stderr)
        return False
    return docx_path.exists()


def build(run: Path, formats: set[str], strict: bool = True) -> dict:
    if not shutil.which("pandoc"):
        raise BuildError("pandoc не найден — без него не собрать ни один формат")
    report = find_report(run)
    build_dir = run / ".build"
    build_dir.mkdir(parents=True, exist_ok=True)

    figs = report_charts.load_figures(run)
    if figs:
        report_charts.build(run, build_dir)

    # Схемы вырезаются ДО pandoc: иначе ```mermaid уедет в <pre> как код.
    source, dias = mermaid_figures.tokenize(report.read_text(encoding="utf-8"))
    failed_dias: list[str] = []
    if dias and not strict and not mermaid_figures.renderer_available():
        # --no-strict: схема останется кодом в тексте, но документ соберётся
        dias, source_path = [], report
        failed_dias = ["нет mmdc — схемы остались кодом"]
    elif dias:
        source_path = build_dir / "_source.md"
        source_path.write_text(source, encoding="utf-8")
        failed_dias = mermaid_figures.render(dias, build_dir, find_chrome())
    else:
        source_path = report

    body = md_to_html(source_path)
    body, moved = sidenotes(body)
    body, missing_figs = inline_figures(body, build_dir, figs)
    body, missing_dias = mermaid_figures.inline(body, build_dir, dias)

    rows = load_sources(run)
    known = {r.get("id") or r.get("source_id") for r in rows}
    body, dangling = link_sources(body, {k for k in known if k})
    body += "\n" + sources_appendix(rows)

    problems = []
    if missing_figs:
        problems.append(f"фигуры без SVG: {', '.join(missing_figs)}")
    if failed_dias:
        problems.append(f"схемы, которые mmdc не отрисовал: {', '.join(failed_dias)}")
    if missing_dias:
        problems.append(f"схемы без SVG: {', '.join(missing_dias)}")
    if dangling:
        problems.append(f"ссылки на несуществующие источники: {', '.join(dangling)}")
    if problems and strict:
        raise BuildError(
            "; ".join(problems)
            + " — битую ссылку в 20-страничном документе глазами не находят, поэтому сборка падает"
        )

    css = CSS.read_text(encoding="utf-8") if CSS.exists() else ""
    title = report.stem
    out = {
        "figures": len(figs),
        "diagrams": len(dias),
        "sidenotes": moved,
        "problems": problems,
        "files": [],
    }

    html_path = run / f"{report.stem}.html"
    html_path.write_text(wrap(body, title, css), encoding="utf-8")
    out["files"].append(html_path)

    if "pdf" in formats:
        pdf_path = run / f"{report.stem}.pdf"
        if to_pdf(html_path, pdf_path):
            out["files"].append(pdf_path)
        else:
            print("  PDF пропущен: не найден Chromium/Chrome", file=sys.stderr)
    if "docx" in formats:
        docx_path = run / f"{report.stem}.docx"
        if to_docx(source_path, docx_path, build_dir):
            out["files"].append(docx_path)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Собрать отчёт прогона в HTML/PDF/DOCX")
    ap.add_argument("run", type=Path, help="папка прогона")
    ap.add_argument(
        "--formats", default="html,pdf,docx", help="через запятую: html,pdf,docx"
    )
    ap.add_argument(
        "--no-strict", action="store_true", help="не падать на битых ссылках и фигурах"
    )
    args = ap.parse_args(argv)
    try:
        res = build(args.run, set(args.formats.split(",")), strict=not args.no_strict)
    except (BuildError, report_charts.FigureError, mermaid_figures.MermaidError) as exc:
        print(f"ОШИБКА: {exc}", file=sys.stderr)
        return 2
    print(
        f"  фигур: {res['figures']} · схем: {res['diagrams']}"
        f" · сносок на поля: {res['sidenotes']}"
    )
    for p in res["files"]:
        print(f"  {p.name}  {p.stat().st_size} B")
    for p in res["problems"]:
        print(f"  ⚠ {p}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
