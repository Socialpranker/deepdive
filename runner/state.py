#!/usr/bin/env python3
"""Persistent state for the Bayesian swarm: observations log + priors + candidates.

Lives OUTSIDE the skill directory on purpose: the skill dir is not under version
control, so a reinstall would wipe everything accumulated. observations.jsonl is
the primary record; priors.json is a derived rollup that can be rebuilt from it.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_ROOT = Path.home() / ".claude"
STATE_DIRNAME = "deepdive-state"


@dataclass
class Observation:
    run_id: str
    channel: str
    qclass: str
    reward: int
    ts: str


@dataclass
class Prior:
    alpha: float
    beta: float
    n: int
    last_seen: str


def state_dir(root: Path | None = None) -> Path:
    return (Path(root) if root is not None else DEFAULT_ROOT) / STATE_DIRNAME


def prior_key(channel: str, qclass: str) -> str:
    return f"{channel}|{qclass}"


def append_observation(obs: Observation, root: Path | None = None) -> None:
    d = state_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    with (d / "observations.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(obs), ensure_ascii=False) + "\n")


def read_observations(root: Path | None = None) -> list[Observation]:
    p = state_dir(root) / "observations.jsonl"
    if not p.exists():
        return []
    out: list[Observation] = []
    for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(Observation(**json.loads(line)))
        except (json.JSONDecodeError, TypeError) as exc:
            log.warning("observations.jsonl:%d unreadable (%s) — skipped", lineno, exc)
    return out


def load_priors(root: Path | None = None) -> dict[str, Prior]:
    """Missing or corrupt priors are NOT fatal — caller falls back to uniform.

    Returning {} here is what makes the allocator degrade loudly instead of dying;
    the caller is responsible for logging the fallback.
    """
    p = state_dir(root) / "priors.json"
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return {k: Prior(**v) for k, v in raw.items()}
    except (json.JSONDecodeError, TypeError) as exc:
        log.warning("priors.json unreadable (%s) — falling back to uniform", exc)
        return {}


def save_priors(priors: dict[str, Prior], root: Path | None = None) -> None:
    d = state_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    target = d / "priors.json"
    tmp = d / "priors.json.tmp"
    tmp.write_text(
        json.dumps(
            {k: asdict(v) for k, v in priors.items()}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    os.replace(tmp, target)
