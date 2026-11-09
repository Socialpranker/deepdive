"""The judge must see the source quotes next to each sampled thesis.

N4-N6 (2026-10-28) judges wrote "no source excerpts are embedded" and capped
factual_accuracy at 3 whatever the report said.
"""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "score_run", Path(__file__).resolve().parent.parent / "eval" / "score_run.py"
)
sr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sr)


def make_run(tmp_path: Path, n_claims: int) -> Path:
    run = tmp_path / "run"
    (run / "sources").mkdir(parents=True)
    (run / "sources" / "01_a.md").write_text(
        "---\nid: s01\n---\n\n> «DuckDB ran the join 14x faster»\n\nnotes\n",
        encoding="utf-8",
    )
    (run / "sources" / "02_b.md").write_text("---\nid: s02\n---\n\nno quotes here\n", encoding="utf-8")
    lines = [f"- Claim number {i:02d} padded to pass the length filter [s01]." for i in range(n_claims)]
    lines.append("- Claim about a missing source, padded to pass the filter [s09].")
    lines.append("- Claim about a source without quotes, padded past the filter [s02].")
    (run / "2026-11-07_decision.md").write_text("# R\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    (run / "plan.md").write_text("H1 something\n", encoding="utf-8")
    return run


def render(tmp_path, monkeypatch, run, run_id):
    monkeypatch.setattr(sr, "OUTPUT_DIR", tmp_path / "out")
    (tmp_path / "out").mkdir(exist_ok=True)
    return sr.render_judge_input(run, run_id).read_text(encoding="utf-8")


def test_quotes_sit_under_their_thesis(tmp_path, monkeypatch):
    text = render(tmp_path, monkeypatch, make_run(tmp_path, 3), "X")
    text = text.split("Sampled theses to fact-check", 1)[1]  # the full report precedes it
    block = text.split("Claim number 00", 1)[1].split("- Claim number 01", 1)[0]
    assert "> «DuckDB ran the join 14x faster»" in block
    assert "[s09] source file not found" in text
    assert "[s02] source file has no verbatim quotes" in text


def test_sample_is_reproducible_and_reaches_past_the_top(tmp_path, monkeypatch):
    lines = [f"line {i}" for i in range(40)]
    a = sr.sample_claims(lines, "run-A")
    assert a == sr.sample_claims(lines, "run-A")
    assert len(a) == sr.SAMPLE_SIZE
    assert a != lines[: sr.SAMPLE_SIZE]
    assert a == sorted(a, key=lines.index)


def test_prose_lines_of_the_quotes_section_reach_the_judge(tmp_path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "09_x.md").write_text(
        '---\nid: s09\ntitle: "Title with 5x Faster"\n---\n\n'
        "# Дословные цитаты и числа\n\n> \"blockquote line\"\n\n"
        'Выигрыш: "3-5 times faster" на аналитике.\n- бандл вырос с 26 MB до 44 MB.\n\n'
        "# Что отсюда следует\n\n1. Реальный выигрыш 3–5x, а не 10–200x.\n",
        encoding="utf-8",
    )
    q = sr.source_quotes(tmp_path)["s09"]
    assert q == ['"blockquote line"', 'Выигрыш: "3-5 times faster" на аналитике.', "бандл вырос с 26 MB до 44 MB."]


def test_long_quote_lists_are_truncated():
    quotes = {"s01": ["q" * 600] * 5}
    out = sr.render_sampled_claims(["thesis [s01]"], quotes)
    assert out.count("> qqq") == 2
    assert "(truncated)" in out


def test_question_is_read_from_plan_not_from_frontmatter(tmp_path):
    # Until 2026-11-07 the judge got the first plain line: «mode: medium».
    cases = {
        "front": "---\nmode: medium\nquestion: \"SQLite or DuckDB?\"\n---\n# Plan\n",
        "body_field": "# Plan\nQuestion: SQLite or DuckDB?\n\n## Hypotheses\nH1: x\n",
        "section": "---\nmode: medium\n---\n# Plan — topic\n\n## 2. Главный вопрос\nSQLite or DuckDB?\n",
        "title": "---\nmode: medium\n---\n# План: SQLite or DuckDB?\n\n## §2 Подвопросы\n- Q1 speed\n",
    }
    for name, plan in cases.items():
        run = tmp_path / name
        run.mkdir()
        (run / "plan.md").write_text(plan, encoding="utf-8")
        assert sr._question_from_plan(run) == "SQLite or DuckDB?", name
