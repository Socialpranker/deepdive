from runner.capabilities import KNOWN_KEYS, audit_env, render_capabilities


def test_audit_env_marks_present_key():
    audit = audit_env({"FRED_API_KEY": "abc"})
    fred = next(a for a in audit if a["key"] == "FRED_API_KEY")
    assert fred["present"] is True


def test_audit_env_marks_absent_keys():
    audit = audit_env({"FRED_API_KEY": "abc"})
    github = next(a for a in audit if a["key"] == "GITHUB_TOKEN")
    assert github["present"] is False


def test_audit_env_empty_env_all_absent():
    audit = audit_env({})
    assert all(a["present"] is False for a in audit)


def test_audit_env_covers_all_known_keys():
    audit = audit_env({})
    assert {a["key"] for a in audit} == set(KNOWN_KEYS)
    assert len(KNOWN_KEYS) == 18


def test_audit_env_empty_string_is_absent():
    audit = audit_env({"FRED_API_KEY": ""})
    fred = next(a for a in audit if a["key"] == "FRED_API_KEY")
    assert fred["present"] is False


def test_render_capabilities_has_header_and_keys():
    audit = [{"key": "FRED_API_KEY", "present": True},
             {"key": "BRAVE_API_KEY", "present": False}]
    md = render_capabilities(audit, "Use FRED for macro context.")
    assert "## Capabilities check (Phase 3.5)" in md
    assert "✅ FRED_API_KEY" in md
    assert "❌ BRAVE_API_KEY" in md
    assert "Use FRED for macro context." in md


def test_render_capabilities_starts_with_blank_line_for_append():
    md = render_capabilities([{"key": "FRED_API_KEY", "present": True}], "m")
    assert md.startswith("\n")
