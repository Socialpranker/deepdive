from pathlib import Path

from runner.state import Observation, Prior
from runner.priors import (
    FLOOR,
    posterior_mean,
    apply_decay,
    load_channel_groups,
    rebuild_priors,
    effective_prior,
)

FIXTURE = Path(__file__).parent / "fixtures" / "channels_mini.md"


def test_posterior_mean_is_alpha_over_total():
    assert posterior_mean(Prior(3.0, 1.0, 4, "t")) == 0.75


def test_decay_discounts_history_and_adds_new_evidence():
    p = apply_decay(Prior(10.0, 10.0, 20, "t"), wins=1, losses=0, lam=0.5)
    assert p.alpha == 6.0  # 10*0.5 + 1
    assert p.beta == 5.0  # 10*0.5 + 0
    assert p.n == 21


def test_floor_keeps_channel_samplable_after_long_failure():
    p = Prior(1.0, 40.0, 41, "t")
    for _ in range(50):
        p = apply_decay(p, wins=0, losses=1)
    assert p.alpha >= FLOOR  # канал не умирает навсегда
    assert posterior_mean(p) > 0.0


def test_channel_groups_parsed_from_channels_md():
    groups = load_channel_groups(FIXTURE)
    assert groups["academic"] == "B"
    assert groups["web-general"] == "A"
    assert groups["api-direct"] == "M"


def test_rebuild_aggregates_observations_per_key():
    obs = [
        Observation("r1", "academic", "scientific-claim", 1, "2026-08-01"),
        Observation("r1", "academic", "scientific-claim", 1, "2026-08-01"),
        Observation("r2", "academic", "scientific-claim", 0, "2026-08-02"),
        Observation("r2", "web-general", "pricing", 1, "2026-08-02"),
    ]
    priors = rebuild_priors(obs)
    assert priors["academic|scientific-claim"].n == 3
    assert priors["web-general|pricing"].n == 1
    assert posterior_mean(priors["academic|scientific-claim"]) > 0.5


def test_rebuild_is_deterministic_from_the_same_log():
    obs = [Observation("r1", "academic", "pricing", 1, "2026-08-01")]
    assert rebuild_priors(obs) == rebuild_priors(obs)


def test_effective_prior_pools_from_group_when_cell_is_empty():
    groups = load_channel_groups(FIXTURE)
    priors = {"academic|scientific-claim": Prior(9.0, 1.0, 10, "t")}
    # preprint-servers в группе B, своей ячейки нет -> наследует репутацию группы
    got = effective_prior(priors, "preprint-servers", "scientific-claim", groups)
    assert posterior_mean(got) > 0.5
    assert got.n == 0  # пулинг даёт форму, но не выдаёт себя за собственные наблюдения


def test_effective_prior_is_uniform_when_group_is_empty_too():
    groups = load_channel_groups(FIXTURE)
    got = effective_prior({}, "academic", "pricing", groups)
    assert got.alpha == FLOOR and got.beta == FLOOR


def test_registry_channels_start_above_web_general():
    groups = load_channel_groups(FIXTURE)
    api = effective_prior({}, "api-direct", "market-size", groups)
    web = effective_prior({}, "web-general", "market-size", groups)
    assert posterior_mean(api) > posterior_mean(
        web
    )  # registry-first закодирован в приоре
