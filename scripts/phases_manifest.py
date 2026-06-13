#!/usr/bin/env python3
"""Loader + validator for phases.yaml — single source of truth for workflow phases.

A tiny hand-rolled parser for the flat list-of-dicts schema we own, so the CI gate
needs no PyYAML dependency. Only this exact shape is supported:

    phases:
      - id: "1"
        name_ru: Reframing
        ...

Anything else raises ValueError.
"""
from __future__ import annotations

from pathlib import Path

REQUIRED = ("id", "name_ru", "name_en", "model", "effort", "depth_gate")


def _strip_quotes(v: str) -> str:
    v = v.strip()
    if v and v[0] not in "\"'" and "#" in v:
        v = v.split("#", 1)[0].strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def load_phases(path: Path) -> list[dict]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    body = [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    if not body or body[0].strip() != "phases:":
        raise ValueError(f"{path}: expected top-level 'phases:' key")

    phases: list[dict] = []
    current: dict | None = None
    for ln in body[1:]:
        stripped = ln.strip()
        if stripped.startswith("- "):
            if current is not None:
                phases.append(current)
            current = {}
            stripped = stripped[2:].strip()
        if current is None:
            raise ValueError(f"{path}: list item expected, got: {ln!r}")
        if ":" not in stripped:
            raise ValueError(f"{path}: expected 'key: value', got: {ln!r}")
        key, _, val = stripped.partition(":")
        current[key.strip()] = _strip_quotes(val)
    if current is not None:
        phases.append(current)

    if not phases:
        raise ValueError(f"{path}: no phases found")
    for p in phases:
        missing = [f for f in REQUIRED if f not in p]
        if missing:
            raise ValueError(f"{path}: phase {p.get('id', '?')} missing {missing}")
    return phases


if __name__ == "__main__":
    import json

    print(json.dumps(load_phases(Path(__file__).resolve().parents[1] / "phases.yaml"), indent=2))
