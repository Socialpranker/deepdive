#!/usr/bin/env python3
"""Отрисовка фигур отчёта из `numbers.csv` и `figures.csv`.

Ключевая гарантия: **число, которого нет в `numbers.csv`, нарисовать нельзя.**
Фигура ссылается на `num_id`, значение и провенанс берутся из ledger'а, а
неизвестный id роняет сборку. Поэтому график не может утверждать больше, чем
таблица чисел, и каждая метка несёт свой `[sNN]` и `as_of`.

Направление — e-ink/paper: тонированная бумага, чернила не чистый чёрный, ноль
теней и градиентов, иерархия кеглем и ритмом. Палитра прогнана через
`dataviz/scripts/validate_palette.js` на бумажной подложке — шесть проверок
(полоса светлоты, пол хромы, CVD-разделение, порог нормального зрения, контраст).

Формы — по эвристике dataviz «работа данных → форма»:
    bar    величина по категориям        (не пирог: доли не сравниваются углами)
    slope  изменение между двумя точками (не два столбца)
    share  часть от целого               (знаменатель виден рамкой)
    dot    сравнение по объектам         (отсутствие данных — пунктир, не ноль)
    line   ряд во времени                (N8 historical-data)
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PAPER = "#f5f2ea"
INK = "#2b2926"
MUTED = "#6f6a62"
RULE = "#d8d2c6"
# Валидировано на подложке #f5f2ea и на тёмной #1c1b19 — все шесть проверок PASS.
SERIES = ["#0072a8", "#c9560c", "#8a4fb0"]
SANS = "'Avenir Next', 'Helvetica Neue', Helvetica, sans-serif"

W = 520
THIN_SP = "&#8201;"


class FigureError(Exception):
    """Фигура ссылается на то, чего нет в ledger'е, или просит неизвестную форму."""


def ru(v) -> str:
    """Русский разделитель дробной части — как в тексте документа."""
    text = f"{v:g}" if isinstance(v, float) else str(v)
    return text.replace(".", ",")


def esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def load_numbers(run: Path) -> dict:
    path = run / "numbers.csv"
    if not path.exists():
        raise FigureError(f"нет {path} — рисовать не из чего")
    with open(path, encoding="utf-8") as fh:
        return {r["num_id"]: r for r in csv.DictReader(fh)}


def load_figures(run: Path) -> list[dict]:
    path = run / "figures.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def resolve(fig: dict, nums: dict) -> list[dict]:
    """Развернуть `numbers` фигуры в строки ledger'а. Неизвестный id — отказ."""
    ids = [i.strip() for i in (fig.get("numbers") or "").split(";") if i.strip()]
    if not ids:
        raise FigureError(f"{fig.get('fig_id')}: пустое поле numbers")
    missing = [i for i in ids if i not in nums]
    if missing:
        raise FigureError(
            f"{fig.get('fig_id')}: в numbers.csv нет {', '.join(missing)} — "
            "число без строки в ledger'е не рисуется"
        )
    return [nums[i] for i in ids]


def provenance(rows: list[dict]) -> str:
    """Подвал фигуры: источники и дата данных — из ledger'а, не из головы."""
    srcs, dates = [], []
    for r in rows:
        for s in (r.get("sources") or "").split(";"):
            s = s.strip()
            if s and s not in srcs:
                srcs.append(s)
        d = (r.get("as_of") or "").strip()
        if d and d not in dates:
            dates.append(d)
    parts = []
    if srcs:
        parts.append("Источник: " + ", ".join(f"[{s}]" for s in srcs))
    if dates:
        span = min(dates) if len(dates) == 1 else f"{min(dates)} … {max(dates)}"
        parts.append(f"данные на {span}")
    derived = [
        r for r in rows if r.get("kind") == "derived" and r.get("formula", "-") != "-"
    ]
    for r in derived:
        parts.append(f"{r['num_id']} = {r['formula']}")
    return " · ".join(parts)


def frame(height: int, body: str, title: str, subtitle: str, footer: str) -> str:
    sub = (
        f'<text x="0" y="32" font-family="{SANS}" font-size="10.5" fill="{MUTED}">{esc(subtitle)}</text>'
        if subtitle
        else ""
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" width="{W}" height="{height}" role="img" aria-label="{esc(title)}">
<rect width="{W}" height="{height}" fill="{PAPER}"/>
<text x="0" y="16" font-family="{SANS}" font-size="12.5" font-weight="600" fill="{INK}">{esc(title)}</text>
{sub}
{body}
<text x="0" y="{height - 5}" font-family="{SANS}" font-size="8.5" fill="{MUTED}">{esc(footer)}</text>
</svg>"""


def _rounded_bar(x, y, width, height, color) -> str:
    """Скруглённый конец 4px, прижат к базовой линии — спека марок dataviz."""
    if width < 6:
        return f'<rect x="{x}" y="{y}" width="{max(width, 1)}" height="{height}" fill="{color}"/>'
    return (
        f'<path d="M{x} {y} H{x + width - 4} a4 4 0 0 1 4 4 V{y + height - 4} '
        f'a4 4 0 0 1 -4 4 H{x} Z" fill="{color}"/>'
    )


def form_bar(rows, fig):
    """Величина по категориям. Один тон: цвет тут не несёт идентичности."""
    x0, top, bh, gap, plot = 178, 48, 26, 14, 268
    top_val = max(float(r["value"]) for r in rows) or 1
    body = []
    for i, r in enumerate(rows):
        y = top + i * (bh + gap)
        val = float(r["value"])
        width = val / top_val * plot
        body.append(
            f'<text x="{x0 - 10}" y="{y + bh / 2 + 4}" text-anchor="end" font-family="{SANS}" '
            f'font-size="11" fill="{INK}">{esc(r.get("label") or r["num_id"])}</text>'
        )
        body.append(_rounded_bar(x0, y, width, bh, SERIES[0]))
        body.append(
            f'<text x="{x0 + width + 8}" y="{y + bh / 2 + 4}" font-family="{SANS}" font-size="11" '
            f'font-weight="600" fill="{INK}">{ru(val)}{THIN_SP}{esc(r.get("unit", ""))}</text>'
        )
        body.append(
            f'<text x="{x0 + width + 62}" y="{y + bh / 2 + 4}" font-family="{SANS}" font-size="9" '
            f'fill="{MUTED}">[{esc(r.get("sources", ""))}]</text>'
        )
    h = top + len(rows) * (bh + gap) + 16
    body.append(
        f'<line x1="{x0}" y1="{top - 6}" x2="{x0}" y2="{h - 30}" stroke="{RULE}" stroke-width="1"/>'
    )
    return frame(
        h, "\n".join(body), fig["title"], fig.get("subtitle", ""), provenance(rows)
    )


def form_slope(rows, fig):
    """Изменение между двумя точками. Наклон читается мгновенно, два столбца — нет."""
    if len(rows) != 2:
        raise FigureError(
            f"{fig['fig_id']}: форма slope требует ровно 2 числа, дано {len(rows)}"
        )
    a, b = (float(r["value"]) for r in rows)
    x1, x2, top, plot_h = 200, 390, 58, 84
    top_val = max(a, b) * 1.25 or 1
    def y(v: float) -> float:
        return top + plot_h - (v / top_val * plot_h)

    y1, y2 = y(a), y(b)
    unit = esc(rows[0].get("unit", ""))
    la, lb = rows[0].get("as_of", "")[:4], rows[1].get("as_of", "")[:4]
    delta = (b - a) / a * 100 if a else 0
    body = [
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{SERIES[1]}" stroke-width="2"/>',
        f'<circle cx="{x1}" cy="{y1}" r="4.5" fill="{SERIES[1]}" stroke="{PAPER}" stroke-width="2"/>',
        f'<circle cx="{x2}" cy="{y2}" r="4.5" fill="{SERIES[1]}" stroke="{PAPER}" stroke-width="2"/>',
        f'<text x="{x1 - 12}" y="{y1 + 4}" text-anchor="end" font-family="{SANS}" font-size="12" font-weight="600" fill="{INK}">{ru(a)}{THIN_SP}{unit}</text>',
        f'<text x="{x2 + 12}" y="{y2 + 4}" font-family="{SANS}" font-size="12" font-weight="600" fill="{INK}">{ru(b)}{THIN_SP}{unit}</text>',
        f'<text x="{x1 - 12}" y="{y1 + 18}" text-anchor="end" font-family="{SANS}" font-size="9.5" fill="{MUTED}">{esc(la)}</text>',
        f'<text x="{x2 + 12}" y="{y2 + 18}" font-family="{SANS}" font-size="9.5" fill="{MUTED}">{esc(lb)}</text>',
        f'<text x="{(x1 + x2) / 2}" y="{top - 8}" text-anchor="middle" font-family="{SANS}" '
        f'font-size="11" font-weight="600" fill="{SERIES[1]}">{"+" if delta >= 0 else ""}{delta:.0f}%</text>',
    ]
    return frame(
        top + plot_h + 46,
        "\n".join(body),
        fig["title"],
        fig.get("subtitle", ""),
        provenance(rows),
    )


def form_share(rows, fig):
    """Часть от целого. Рамка — знаменатель: доля без него врёт."""
    x0, plot, bh = 178, 268, 30
    body = []
    for i, r in enumerate(rows):
        y = 52 + i * (bh + 18)
        val = float(r["value"])
        width = min(val, 100) / 100 * plot
        body.append(
            f'<rect x="{x0}" y="{y}" width="{plot}" height="{bh}" fill="none" stroke="{RULE}" stroke-width="1"/>'
        )
        body.append(_rounded_bar(x0, y, width, bh, SERIES[i % len(SERIES)]))
        body.append(
            f'<text x="{x0 - 10}" y="{y + bh / 2 + 4}" text-anchor="end" font-family="{SANS}" '
            f'font-size="11" fill="{INK}">{esc(r.get("label") or r["num_id"])}</text>'
        )
        body.append(
            f'<text x="{x0 + plot + 10}" y="{y + bh / 2 + 4}" font-family="{SANS}" font-size="11" '
            f'font-weight="600" fill="{INK}">{ru(val)}{THIN_SP}%</text>'
        )
    return frame(
        52 + len(rows) * (bh + 18) + 22,
        "\n".join(body),
        fig["title"],
        fig.get("subtitle", ""),
        provenance(rows),
    )


def form_dot(rows, fig):
    """Сравнение по объектам. Пустое значение рисуется пунктиром: отсутствие — тоже находка."""
    x0, top, rh, plot = 178, 64, 24, 186
    vals = [float(r["value"]) for r in rows if r.get("value") not in ("", "-", None)]
    top_val = (max(vals) * 1.03) if vals else 1
    unit = esc(rows[0].get("unit", ""))
    body = [
        f'<circle cx="{x0 + 112}" cy="46" r="4" fill="{SERIES[2]}"/>',
        f'<text x="{x0 + 121}" y="49" font-family="{SANS}" font-size="9.5" fill="{MUTED}">{esc(fig.get("legend") or unit)}</text>',
    ]
    for i, r in enumerate(rows):
        y = top + i * rh
        raw = r.get("value")
        body.append(
            f'<text x="{x0 - 10}" y="{y + 4}" text-anchor="end" font-family="{SANS}" font-size="11" '
            f'fill="{INK}">{esc(r.get("label") or r["num_id"])}</text>'
        )
        if raw in ("", "-", None):
            body.append(
                f'<line x1="{x0 + 108}" y1="{y}" x2="{x0 + 130}" y2="{y}" stroke="{RULE}" '
                f'stroke-width="2" stroke-dasharray="2 3"/>'
            )
            body.append(
                f'<text x="{x0 + 138}" y="{y + 4}" font-family="{SANS}" font-size="10" '
                f'fill="{MUTED}">{esc(r.get("note") or "нет данных")}</text>'
            )
            continue
        w = float(raw) / top_val * plot
        body.append(
            f'<line x1="{x0 + 108}" y1="{y}" x2="{x0 + 108 + w}" y2="{y}" stroke="{SERIES[2]}" stroke-width="2"/>'
        )
        body.append(
            f'<circle cx="{x0 + 108 + w}" cy="{y}" r="4.5" fill="{SERIES[2]}" stroke="{PAPER}" stroke-width="2"/>'
        )
        body.append(
            f'<text x="{x0 + 108 + w + 10}" y="{y + 4}" font-family="{SANS}" font-size="10.5" fill="{INK}">{ru(float(raw))}</text>'
        )
    return frame(
        top + len(rows) * rh + 30,
        "\n".join(body),
        fig["title"],
        fig.get("subtitle", ""),
        provenance(rows),
    )


def form_line(rows, fig):
    """Ряд во времени. Точки подписываются выборочно — не число на каждой."""
    if len(rows) < 3:
        raise FigureError(
            f"{fig['fig_id']}: форма line требует ≥3 точек, дано {len(rows)}"
        )
    x0, top, plot_w, plot_h = 60, 56, 430, 92
    vals = [float(r["value"]) for r in rows]
    lo, hi = min(vals), max(vals) * 1.08
    span = (hi - lo) or 1
    step = plot_w / (len(rows) - 1)
    pts = [
        (x0 + i * step, top + plot_h - (v - lo) / span * plot_h)
        for i, v in enumerate(vals)
    ]
    unit = esc(rows[0].get("unit", ""))
    body = [
        '<polyline points="'
        + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        + f'" fill="none" stroke="{SERIES[0]}" stroke-width="2"/>'
    ]
    for i, ((x, y), r) in enumerate(zip(pts, rows)):
        last = i in (0, len(rows) - 1)
        body.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{4.5 if last else 3}" fill="{SERIES[0]}" stroke="{PAPER}" stroke-width="2"/>'
        )
        if last:
            body.append(
                f'<text x="{x:.1f}" y="{y - 11:.1f}" text-anchor="middle" font-family="{SANS}" '
                f'font-size="10.5" font-weight="600" fill="{INK}">{ru(float(r["value"]))}{THIN_SP}{unit}</text>'
            )
            body.append(
                f'<text x="{x:.1f}" y="{top + plot_h + 16}" text-anchor="middle" font-family="{SANS}" '
                f'font-size="9.5" fill="{MUTED}">{esc((r.get("as_of") or "")[:7])}</text>'
            )
    body.append(
        f'<line x1="{x0}" y1="{top + plot_h}" x2="{x0 + plot_w}" y2="{top + plot_h}" stroke="{RULE}" stroke-width="1"/>'
    )
    return frame(
        top + plot_h + 46,
        "\n".join(body),
        fig["title"],
        fig.get("subtitle", ""),
        provenance(rows),
    )


FORMS = {
    "bar": form_bar,
    "slope": form_slope,
    "share": form_share,
    "dot": form_dot,
    "line": form_line,
}


def render(fig: dict, nums: dict) -> str:
    form = (fig.get("form") or "").strip()
    if form not in FORMS:
        raise FigureError(
            f"{fig.get('fig_id')}: неизвестная форма {form!r}; доступны {', '.join(sorted(FORMS))}"
        )
    if not (fig.get("title") or "").strip():
        raise FigureError(
            f"{fig.get('fig_id')}: пустой заголовок — фигура без заголовка нечитаема"
        )
    rows = resolve(fig, nums)
    # Метка и примечание живут в figures.csv, значение и провенанс — в numbers.csv.
    labels = [x.strip() for x in (fig.get("labels") or "").split(";")]
    notes = [x.strip() for x in (fig.get("notes") or "").split(";")]
    for i, r in enumerate(rows):
        if i < len(labels) and labels[i]:
            r = dict(r, label=labels[i])
        if i < len(notes) and notes[i]:
            r = dict(r, note=notes[i])
        rows[i] = r
    return FORMS[form](rows, fig)


def build(run: Path, out_dir: Path | None = None) -> list[Path]:
    nums = load_numbers(run)
    figs = load_figures(run)
    out_dir = out_dir or (run / ".build")
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for fig in figs:
        svg = render(fig, nums)
        path = out_dir / f"{fig['fig_id']}.svg"
        path.write_text(svg, encoding="utf-8")
        written.append(path)
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Отрисовать фигуры отчёта из numbers.csv + figures.csv"
    )
    ap.add_argument("run", type=Path, help="папка прогона")
    ap.add_argument(
        "--out", type=Path, help="куда класть SVG (по умолчанию <run>/.build)"
    )
    args = ap.parse_args(argv)
    try:
        written = build(args.run, args.out)
    except FigureError as exc:
        print(f"ОШИБКА: {exc}", file=sys.stderr)
        return 2
    for p in written:
        print(f"  {p.name}  {p.stat().st_size} B")
    if not written:
        print("  фигур нет (figures.csv отсутствует или пуст)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
