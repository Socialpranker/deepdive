"""Схемы Mermaid в отчёте — scripts/mermaid_figures.py и врезка в build_report.

Несущая часть, как и в остальной сборке, — отказы и тихие потери. Схема,
которая не отрисовалась, не должна уехать в документ дырой; две схемы в одном
документе не должны делить id и красить друг друга.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import build_report as br  # noqa: E402
import mermaid_figures as mf  # noqa: E402

MD = """# Отчёт

Текст до.

```mermaid
%% caption: путь запроса
flowchart TD
  A --> B
```

Текст между.

```mermaid
graph LR
  X --> Y
```

Текст после.
"""


def test_fences_are_found_in_document_order():
    dias = mf.find_diagrams(MD)
    assert [d["dia_id"] for d in dias] == ["D1", "D2"]
    assert "flowchart TD" in dias[0]["code"]
    assert "graph LR" in dias[1]["code"]


def test_caption_comes_from_the_fence_and_is_optional():
    dias = mf.find_diagrams(MD)
    assert dias[0]["caption"] == "путь запроса"
    assert dias[1]["caption"] == ""


def test_tokenize_swaps_fences_and_keeps_the_prose():
    out, dias = mf.tokenize(MD)
    assert "```mermaid" not in out
    assert "{{dia:D1}}" in out and "{{dia:D2}}" in out
    assert "Текст между." in out and "Текст после." in out
    assert len(dias) == 2


def test_document_without_diagrams_is_untouched():
    plain = "# Отчёт\n\nТолько текст.\n"
    out, dias = mf.tokenize(plain)
    assert out == plain and dias == []


def test_each_diagram_gets_its_own_svg_id(tmp_path, monkeypatch):
    # mermaid скоупит свои стили по id корневого svg: одинаковый id у двух схем
    # в одном документе означает, что стили второй красят первую.
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        Path(cmd[cmd.index("-o") + 1]).write_text("<svg/>", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(mf, "renderer_available", lambda: True)
    monkeypatch.setattr(mf.subprocess, "run", fake_run)
    _, dias = mf.tokenize(MD)
    assert mf.render(dias, tmp_path, None) == []
    ids = [c[c.index("-I") + 1] for c in calls]
    assert ids == ["dia-D1", "dia-D2"], "id схем не уникальны в пределах документа"


def test_renderer_failure_is_reported_not_swallowed(tmp_path, monkeypatch):
    monkeypatch.setattr(mf, "renderer_available", lambda: True)
    monkeypatch.setattr(
        mf.subprocess,
        "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "boom"),
    )
    _, dias = mf.tokenize(MD)
    assert mf.render(dias, tmp_path, None) == ["D1", "D2"]


def test_missing_mmdc_names_the_install_command(tmp_path, monkeypatch):
    monkeypatch.setattr(mf, "renderer_available", lambda: False)
    _, dias = mf.tokenize(MD)
    with pytest.raises(mf.MermaidError) as exc:
        mf.render(dias, tmp_path, None)
    assert "mermaid-cli" in str(exc.value)


def test_no_diagrams_needs_no_renderer(tmp_path, monkeypatch):
    monkeypatch.setattr(mf, "renderer_available", lambda: False)
    assert mf.render([], tmp_path, None) == []


def test_token_becomes_inline_svg_with_its_own_counter(tmp_path):
    (tmp_path / "D1.svg").write_text("<svg id='dia-D1'/>", encoding="utf-8")
    (tmp_path / "D2.svg").write_text("<svg id='dia-D2'/>", encoding="utf-8")
    dias = [
        {"dia_id": "D1", "caption": "первая"},
        {"dia_id": "D2", "caption": "вторая"},
    ]
    body, missing = mf.inline("<p>{{dia:D1}}</p><p>{{dia:D2}}</p>", tmp_path, dias)
    assert missing == []
    assert 'figure class="diagram"' in body
    # нумерация своя, «Схема», а не «Рис.»: у схемы нет строки в numbers.csv
    assert "<b>Схема 1.</b> первая" in body
    assert "<b>Схема 2.</b> вторая" in body
    assert "Рис." not in body


def test_diagram_without_svg_is_reported(tmp_path):
    dias = [{"dia_id": "D1", "caption": ""}]
    body, missing = mf.inline("{{dia:D1}}", tmp_path, dias)
    assert missing == ["D1"]
    assert "{{dia:D1}}" in body


def test_docx_branch_turns_tokens_into_images(tmp_path):
    md = mf.to_image_refs("текст\n\n{{dia:D1}}\n", tmp_path)
    assert f"![]({tmp_path / 'D1.svg'})" in md
    assert "{{dia:" not in md


def _run_dir(tmp_path: Path, report: str) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    (run / "2026-08-24_validation.md").write_text(report, encoding="utf-8")
    (run / "sources.csv").write_text("id,title,url\n", encoding="utf-8")
    return run


def test_strict_build_refuses_a_diagram_that_did_not_render(tmp_path, monkeypatch):
    # mf.shutil/mf.subprocess подменять нельзя: это те же объекты, что у
    # build_report, и подмена сносит заодно поиск pandoc.
    run = _run_dir(tmp_path, MD)

    def half_render(dias, build_dir, chrome):
        # D2 отрисовалась, D1 — нет: без отдельной жалобы на упавший рендер
        # отказ выглядел бы как «потерянный SVG» и чинился бы не там.
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "D1.svg").write_text("<svg/>", encoding="utf-8")
        (build_dir / "D2.svg").write_text("<svg/>", encoding="utf-8")
        return ["D1"]

    monkeypatch.setattr(mf, "render", half_render)
    with pytest.raises(br.BuildError) as exc:
        br.build(run, {"html"}, strict=True)
    assert "mmdc не отрисовал" in str(exc.value)


def test_strict_build_refuses_a_diagram_whose_svg_vanished(tmp_path, monkeypatch):
    run = _run_dir(tmp_path, MD)
    monkeypatch.setattr(mf, "render", lambda dias, build_dir, chrome: [])
    with pytest.raises(br.BuildError) as exc:
        br.build(run, {"html"}, strict=True)
    assert "схемы без SVG" in str(exc.value)


def test_no_strict_build_survives_without_a_renderer(tmp_path, monkeypatch):
    run = _run_dir(tmp_path, MD)
    monkeypatch.setattr(mf, "renderer_available", lambda: False)
    res = br.build(run, {"html"}, strict=False)
    assert res["diagrams"] == 0
    assert any("mmdc" in p for p in res["problems"])
    assert (run / "2026-08-24_validation.html").exists()


BLOCKS = REPO / "references" / "blocks"


@pytest.mark.parametrize(
    "path,block", [("explain.md", "E13"), ("map.md", "M9")]
)
def test_diagram_blocks_no_longer_cap_the_node_count(path, block):
    # Кап «>10 узлов не рисуй» был следствием ASCII-отрисовки. Рендер есть —
    # кап обязан был уйти вместе с ним, иначе шаблон противоречит конвейеру.
    text = (BLOCKS / path).read_text(encoding="utf-8")
    start = text.index(f"## {block} — ")
    # следующий блок каталога, а не любой `## ` — внутри шаблона свои заголовки
    nxt = re.compile(r"^## [A-Z]\d+ — ", re.M).search(text, start + 1)
    body = text[start : nxt.start() if nxt else len(text)]
    assert "mermaid" in body, f"{block} не предлагает Mermaid как основную форму"
    assert ">10" not in body and ">15" not in body, (
        f"{block} всё ещё режет схему по счёту узлов"
    )
