"""Tests for scripts/phases_manifest.py — loader + validator for phases.yaml."""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import phases_manifest  # noqa: E402


def test_loads_nine_phases_in_order():
    phases = phases_manifest.load_phases(REPO / "phases.yaml")
    assert [p["id"] for p in phases] == ["1", "2", "3", "3.5", "4", "5", "6", "6.5", "7"]


def test_every_phase_has_required_fields():
    phases = phases_manifest.load_phases(REPO / "phases.yaml")
    required = {"id", "name_ru", "name_en", "model", "effort", "depth_gate"}
    for p in phases:
        assert required <= set(p), f"phase {p.get('id')} missing fields"


def test_ids_are_unique():
    phases = phases_manifest.load_phases(REPO / "phases.yaml")
    ids = [p["id"] for p in phases]
    assert len(ids) == len(set(ids))


def test_models_and_efforts_are_valid():
    phases = phases_manifest.load_phases(REPO / "phases.yaml")
    for p in phases:
        assert p["model"] in {"opus", "sonnet", "haiku"}
        assert p["effort"] in {"high", "medium", "low"}
        assert p["depth_gate"] in {"shallow", "medium", "deep"}


def test_missing_field_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text('phases:\n  - id: "1"\n    name_ru: x\n', encoding="utf-8")
    with pytest.raises(ValueError, match="missing"):
        phases_manifest.load_phases(bad)


def test_unparseable_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("not a phases doc\n", encoding="utf-8")
    with pytest.raises(ValueError):
        phases_manifest.load_phases(bad)
