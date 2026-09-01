#!/usr/bin/env python3
"""Схемы Mermaid в отчёте: ```mermaid → SVG → тот же конвейер, что и фигуры.

Зачем отдельный счётчик «Схема N», а не общая нумерация с «Рис. N»: фигуры
рождаются из `numbers.csv` и отвечают за числа, схема отвечает за структуру.
Смешать их в один счётчик — значит завести ссылку «Рис. 4» на картинку,
которой нет ни одной строки в ledger'е.

Рендер — `mmdc` (@mermaid-js/mermaid-cli). Свой Chromium он не тянет:
puppeteer-конфиг указывает на тот же бинарь, что печатает PDF.
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

# Тема под e-ink-палитру assets/report.css: убери цвет — структура не изменится.
THEME = {
    "theme": "base",
    "themeVariables": {
        "background": "#f5f2ea",
        "primaryColor": "#ece7db",
        "primaryTextColor": "#2b2926",
        "primaryBorderColor": "#6f6a62",
        "lineColor": "#6f6a62",
        "secondaryColor": "#e2ddd0",
        "tertiaryColor": "#f5f2ea",
        "fontFamily": "Charter, Georgia, 'Times New Roman', serif",
        "fontSize": "15px",
    },
    "flowchart": {"curve": "linear"},
}

FENCE = re.compile(r"^```mermaid[ \t]*\r?\n(.*?)^```[ \t]*$", re.S | re.M)
CAPTION = re.compile(r"^\s*%%\s*caption:\s*(.+?)\s*$", re.M)
DIA_TOKEN = re.compile(r"\{\{dia:(D\d+)\}\}")


class MermaidError(Exception):
    pass


def find_diagrams(md: str) -> list[dict]:
    """Схемы в порядке документа: id, код, подпись из `%% caption:`."""
    out = []
    for i, m in enumerate(FENCE.finditer(md), start=1):
        code = m.group(1)
        cap = CAPTION.search(code)
        out.append(
            {
                "dia_id": f"D{i}",
                "code": code,
                "caption": cap.group(1) if cap else "",
                "span": m.span(),
            }
        )
    return out


def tokenize(md: str) -> tuple[str, list[dict]]:
    """Заменить каждый ```mermaid на `{{dia:DN}}`; вернуть текст и список схем.

    Токен, а не готовый HTML: дальше по конвейеру один и тот же текст идёт
    и в pandoc→HTML, и в pandoc→DOCX, и подстановка у них разная.
    """
    dias = find_diagrams(md)
    for d in reversed(dias):  # с конца — иначе поедут смещения
        start, end = d["span"]
        md = md[:start] + f"{{{{dia:{d['dia_id']}}}}}" + md[end:]
    for d in dias:
        d.pop("span")
    return md, dias


def renderer_available() -> bool:
    return shutil.which("mmdc") is not None


def render(dias: list[dict], build_dir: Path, chrome: Path | None) -> list[str]:
    """Отрисовать каждую схему в `build_dir/DN.svg`. Вернуть id, которые упали."""
    if not dias:
        return []
    if not renderer_available():
        raise MermaidError(
            "в отчёте есть ```mermaid, но `mmdc` не найден — "
            "`npm i -g @mermaid-js/mermaid-cli puppeteer` (см. references/report_export.md)"
        )
    build_dir.mkdir(parents=True, exist_ok=True)
    cfg = build_dir / "_mermaid.json"
    cfg.write_text(json.dumps(THEME), encoding="utf-8")
    pcfg = None
    if chrome:
        pcfg = build_dir / "_puppeteer.json"
        pcfg.write_text(
            json.dumps({"executablePath": str(chrome), "args": ["--no-sandbox"]}),
            encoding="utf-8",
        )

    failed: list[str] = []
    for d in dias:
        src = build_dir / f"{d['dia_id']}.mmd"
        src.write_text(d["code"], encoding="utf-8")
        out = build_dir / f"{d['dia_id']}.svg"
        # -I: mermaid скоупит свои стили по id корневого svg. Дефолтный `my-svg`
        # одинаков у всех схем, и в одном документе стили второй начинают
        # применяться к первой — id обязан быть уникальным на документ.
        cmd = [
            "mmdc",
            "-i",
            str(src),
            "-o",
            str(out),
            "-c",
            str(cfg),
            "-b",
            "transparent",
            "-I",
            f"dia-{d['dia_id']}",
        ]
        if pcfg:
            cmd += ["-p", str(pcfg)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not out.exists():
            failed.append(d["dia_id"])
    return failed


def inline(body: str, build_dir: Path, dias: list[dict]) -> tuple[str, list[str]]:
    """`{{dia:DN}}` → `<figure class="diagram">` с встроенным SVG. Вернуть потери."""
    caps = {d["dia_id"]: d["caption"] for d in dias}
    order = {d["dia_id"]: i + 1 for i, d in enumerate(dias)}
    missing: list[str] = []

    def swap(m):
        did = m.group(1)
        path = build_dir / f"{did}.svg"
        if not path.exists():
            missing.append(did)
            return m.group(0)
        svg = path.read_text(encoding="utf-8")
        cap = caps.get(did, "")
        num = order.get(did, "?")
        caption = f"<figcaption><b>Схема {num}.</b> {cap}</figcaption>" if cap else ""
        return f'<figure class="diagram">{svg}{caption}</figure>'

    return DIA_TOKEN.sub(swap, body), sorted(set(missing))


def to_image_refs(md: str, build_dir: Path) -> str:
    """`{{dia:DN}}` → `![](DN.svg)` для ветки DOCX."""
    return DIA_TOKEN.sub(lambda m: f"![]({build_dir / (m.group(1) + '.svg')})", md)


def main(argv=None) -> int:
    """Отладочный вход: отрисовать схемы одного markdown-файла."""
    import argparse

    ap = argparse.ArgumentParser(description="Отрисовать ```mermaid из markdown в SVG")
    ap.add_argument("md", type=Path)
    ap.add_argument("--out", type=Path, default=None, help="куда класть SVG")
    args = ap.parse_args(argv)
    md = args.md.read_text(encoding="utf-8")
    _, dias = tokenize(md)
    out = args.out or Path(tempfile.mkdtemp(prefix="mermaid-"))
    failed = render(dias, out, None)
    print(f"  схем: {len(dias)} · упало: {len(failed)} · {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
