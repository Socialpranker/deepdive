from pathlib import Path

from runner.qclass import QCLASSES

ROOT = Path(__file__).resolve().parent.parent
DISPATCH = ROOT / "references" / "source_dispatch.md"
CAPS_MD = ROOT / "references" / "capability_discovery.md"
CAPS_PY = ROOT / "runner" / "capabilities.py"

DEAD_SEARCH_KEYS = ("TAVILY_API_KEY", "BRAVE_API_KEY", "EXA_API_KEY", "SERPAPI_KEY")


def test_dispatch_documents_qclass_field():
    text = DISPATCH.read_text(encoding="utf-8")
    assert "qclass" in text
    assert "market-size" in text


def test_every_qclass_appears_in_dispatch_doc():
    text = DISPATCH.read_text(encoding="utf-8")
    missing = [q for q in QCLASSES if q not in text]
    assert missing == [], f"классы без описания в диспатче: {missing}"


def test_dead_search_keys_are_not_advertised_as_configurable():
    text = CAPS_MD.read_text(encoding="utf-8")
    for key in DEAD_SEARCH_KEYS:
        if key in text:
            idx = text.index(key)
            window = text[max(0, idx - 400) : idx + 400]
            assert "не используется" in window, (
                f"{key} упомянут без пометки о том, что скилл его не вызывает"
            )


def test_capabilities_py_does_not_audit_unused_search_keys():
    text = CAPS_PY.read_text(encoding="utf-8")
    for key in DEAD_SEARCH_KEYS:
        assert key not in text, f"{key} аудируется, но нигде не вызывается"


def _fenced_blocks(text: str, lang: str) -> list[str]:
    """Bodies of every ```<lang> ... ``` fence, in document order."""
    marker = f"```{lang}"
    out: list[str] = []
    pos = 0
    while True:
        start = text.find(marker, pos)
        if start == -1:
            return out
        body_start = start + len(marker)
        end = text.find("```", body_start)
        if end == -1:
            return out
        out.append(text[body_start:end])
        pos = end + 3


def test_step1_pseudocode_does_not_gate_on_dead_search_keys():
    # Step 1's ```bash pseudocode instructs the skill to treat "env $KEY exists"
    # as a live authenticated/not-authenticated toggle. A dead search key sitting
    # there contradicts the "не используется" note in the table below it, in the
    # same file — the file argues with itself and nothing catches it.
    text = CAPS_MD.read_text(encoding="utf-8")
    blocks = _fenced_blocks(text, "bash")
    assert blocks, "ожидался ```bash блок с псевдокодом Step 1"
    pseudocode = blocks[0]
    for key in DEAD_SEARCH_KEYS:
        assert key not in pseudocode, (
            f"{key} проверяется в псевдокоде Step 1 как переключатель статуса"
        )
