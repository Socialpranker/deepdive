#!/usr/bin/env python3
"""Beta-Bernoulli model over (channel x qclass).

Three properties matter more than the math:
  - decay: sources rot (APIs die, paywalls appear); a two-year-old prior lies
    more confidently than no prior at all.
  - floor: a channel whose alpha hits zero is never sampled again and can never
    recover once its API is fixed.
  - pooling: a cell with no observations inherits its channel group's shape,
    so a new source starts with its type's reputation instead of a coin flip.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from runner.state import Observation, Prior, prior_key

LAMBDA = 0.95
FLOOR = 1.0

# Стартовое смещение по группам: registry-каналы начинают выше веба.
# Это кодирует registry-first правило source_dispatch.md, а не вкусовщину.
GROUP_HEAD_START: dict[str, tuple[float, float]] = {
    "I": (2.0, 1.0),  # Quantitative — data-statistical-gov, surveys
    "M": (2.0, 1.0),  # API-direct
    "H": (1.5, 1.0),  # Official / Legal
}

PART_RE = re.compile(r"^###\s+Часть\s+([A-Z])\b")
CHANNEL_RE = re.compile(r"`([a-z][a-z0-9-]{3,})`")


def posterior_mean(p: Prior) -> float:
    total = p.alpha + p.beta
    return p.alpha / total if total else 0.0


def apply_decay(p: Prior, wins: int, losses: int, lam: float = LAMBDA) -> Prior:
    alpha = max(FLOOR, p.alpha * lam + wins)
    beta = max(FLOOR, p.beta * lam + losses)
    return Prior(alpha=alpha, beta=beta, n=p.n + wins + losses, last_seen=p.last_seen)


@lru_cache(maxsize=8)
def _groups_cached(path_str: str, mtime: float) -> tuple[tuple[str, str], ...]:
    text = Path(path_str).read_text(encoding="utf-8")
    out: list[tuple[str, str]] = []
    current = ""
    for line in text.splitlines():
        m = PART_RE.match(line)
        if m:
            current = m.group(1)
            continue
        if not current:
            continue
        for cid in CHANNEL_RE.findall(line):
            out.append((cid, current))
    return tuple(out)


def load_channel_groups(channels_md: Path) -> dict[str, str]:
    """Parse channel id -> group letter straight from channels.md.

    Parsed rather than hand-copied: a hand-written table drifts silently the first
    time someone adds a channel.
    """
    p = Path(channels_md)
    return dict(_groups_cached(str(p), p.stat().st_mtime))


def rebuild_priors(
    observations: list[Observation], lam: float = LAMBDA
) -> dict[str, Prior]:
    """Fold the whole observation log into priors, oldest first.

    Rebuilt from scratch every time — that is the point of keeping the log primary:
    a fix to this formula re-derives history instead of losing it.
    """
    priors: dict[str, Prior] = {}
    for obs in observations:
        key = prior_key(obs.channel, obs.qclass)
        cur = priors.get(key, Prior(FLOOR, FLOOR, 0, obs.ts))
        updated = apply_decay(
            cur, wins=1 if obs.reward else 0, losses=0 if obs.reward else 1, lam=lam
        )
        updated.last_seen = obs.ts
        priors[key] = updated
    return priors


def effective_prior(
    priors: dict[str, Prior], channel: str, qclass: str, groups: dict[str, str]
) -> Prior:
    """Own cell if it exists; otherwise the group's pooled shape; otherwise uniform."""
    own = priors.get(prior_key(channel, qclass))
    if own is not None:
        return own

    group = groups.get(channel, "")
    siblings = [
        v
        for k, v in priors.items()
        if k.endswith(f"|{qclass}")
        and groups.get(k.split("|", 1)[0], "") == group
        and group
    ]
    if siblings:
        alpha = sum(s.alpha for s in siblings) / len(siblings)
        beta = sum(s.beta for s in siblings) / len(siblings)
        return Prior(alpha=max(FLOOR, alpha), beta=max(FLOOR, beta), n=0, last_seen="")

    head_a, head_b = GROUP_HEAD_START.get(group, (FLOOR, FLOOR))
    return Prior(alpha=head_a, beta=head_b, n=0, last_seen="")
