#!/usr/bin/env python3
"""Within-run bandit state: fast signal, memory only.

Two learning rates, one persisted. The fast signal (a source cleared
evidence_filter) steers allocation inside the current run; the slow signal (a source
grounded a claim in the final report) is the only one that reaches priors.json.

Mixing them would give the system two competing accounts of the same channel with
no way to adjudicate between them — so this class deliberately has no writer.
"""

from __future__ import annotations

from dataclasses import replace

from runner.priors import effective_prior
from runner.state import Prior, prior_key

SESSION_WEIGHT = (
    0.5  # быстрый сигнал слабее медленного: фильтр судит правдоподобие, не пользу
)


class SessionBandit:
    def __init__(self, priors: dict[str, Prior], groups: dict[str, str]) -> None:
        self._base = priors
        self._groups = groups
        self._session: dict[str, Prior] = {}

    def observe(self, channel: str, qclass: str, passed_filter: bool) -> None:
        key = prior_key(channel, qclass)
        cur = self._session.get(key)
        if cur is None:
            seed = self._base.get(key) or effective_prior(
                self._base, channel, qclass, self._groups
            )
            cur = replace(seed)  # копия: базовые приоры прогоном не портятся
        if passed_filter:
            cur.alpha += SESSION_WEIGHT
        else:
            cur.beta += SESSION_WEIGHT
        self._session[key] = cur

    def view(self) -> dict[str, Prior]:
        """Priors as the allocator should see them right now: base overlaid with session."""
        merged = dict(self._base)
        merged.update(self._session)
        return merged

    def persisted_delta(self) -> dict:
        """Always empty. Present so the contract is visible and testable, not implied."""
        return {}
