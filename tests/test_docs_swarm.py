from pathlib import Path

from runner.qclass import QCLASSES

ROOT = Path(__file__).resolve().parent.parent
DISPATCH = ROOT / "references" / "source_dispatch.md"
CAPS_MD = ROOT / "references" / "capability_discovery.md"
CAPS_PY = ROOT / "runner" / "capabilities.py"
SKILL_MD = ROOT / "SKILL.md"
SWARM_MD = ROOT / "references" / "swarm_postprocess.md"

# SERPAPI has no free tier and is the only search key the skill still does not call.
# BRAVE/TAVILY/EXA/SERPBASE became the second search engine (scripts/search_query.py).
DEAD_SEARCH_KEYS = ("SERPAPI_KEY",)
LIVE_SEARCH_KEYS = (
    "BRAVE_SEARCH_API_KEY",
    "TAVILY_API_KEY",
    "EXA_API_KEY",
    "SERPBASE_API_KEY",
)


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
    import importlib.util

    spec = importlib.util.spec_from_file_location("capabilities", CAPS_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    audited = {k[0] if isinstance(k, tuple) else k for k in mod.KNOWN_KEYS}
    for key in DEAD_SEARCH_KEYS:
        assert key not in audited, f"{key} аудируется, но нигде не вызывается"


def test_live_search_keys_are_audited_and_wired_to_search_query():
    text = CAPS_PY.read_text(encoding="utf-8")
    script = (ROOT / "scripts" / "search_query.py").read_text(encoding="utf-8")
    for key in LIVE_SEARCH_KEYS:
        assert key in text, f"{key} не аудируется, хотя search_query.py его читает"
        assert key in script, f"{key} аудируется, но search_query.py его не читает"


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


def test_swarm_ref_documents_the_observation_collection_sop():
    text = SWARM_MD.read_text(encoding="utf-8")
    for needle in (
        "collect_observations.py",
        "update_priors.py",
        "promote_candidates.py --track",
        "promote_candidates.py --write",
    ):
        assert needle in text, f"постобработка не документирует вызов {needle}"


def test_skill_md_routes_to_the_swarm_postprocess_ref():
    # SOP переехал из SKILL.md в phase-scoped ref (диета бюджета 2026-08-24).
    # Прогон дойдёт до него только если Фаза 7 явно посылает читать файл.
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "swarm_postprocess.md" in text, "Фаза 7 не отправляет читать постобработку"
    for needle in ("collect_observations.py", "update_priors.py", "promote_candidates.py"):
        assert needle in text, f"маршрут не называет вызов {needle}"


def test_swarm_ref_warns_against_one_call_per_whole_run():
    # --requested парсится в dict по ключу-каналу: один и тот же канал в двух
    # подвопросах с разным qclass в одном вызове тихо теряет одно из наблюдений.
    # Это не очевидно из сигнатуры CLI — инструкция обязана предупредить явно.
    text = SWARM_MD.read_text(encoding="utf-8")
    assert "молча затрёт" in text or "silently" in text.lower()


def test_source_dispatch_documents_prior_based_extra_channel():
    text = DISPATCH.read_text(encoding="utf-8")
    assert "update_priors.py --qclass" in text
    assert "Приор при выборе канала сверх обязательного минимума" in text


def test_source_dispatch_forbids_prior_overriding_mandatory_channels():
    text = DISPATCH.read_text(encoding="utf-8")
    assert "Приором подменять Primary/Secondary" in text


def test_documented_cli_flags_actually_exist_in_argparse():
    # Ловит дрейф: если флаг переименуют в коде, а доку забудут поправить,
    # тесты выше остаются зелёными (это просто подстроки) — этот тест не даст.
    import importlib
    import sys

    sys.path.insert(0, str(ROOT))
    for modname, expected_flags in (
        (
            "scripts.collect_observations",
            {"--research-dir", "--run-id", "--requested", "--dry-run"},
        ),
        ("scripts.update_priors", {"--lambda", "--show", "--qclass"}),
        (
            "scripts.promote_candidates",
            {"--write", "--track", "--channel", "--qclass", "--run-id", "--dead"},
        ),
    ):
        mod = importlib.import_module(modname)
        # main() строит свой ArgumentParser внутри функции — вызвать его без
        # побочных эффектов (парсинг реальных argv, sys.exit при --help) нельзя,
        # поэтому ищем регистрацию флага прямо в исходнике.
        src = Path(mod.__file__).read_text(encoding="utf-8")
        for flag in expected_flags:
            assert f'"{flag}"' in src, f"{modname}: флаг {flag} не найден в исходнике"
