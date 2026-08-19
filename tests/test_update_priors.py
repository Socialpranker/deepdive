from runner.state import Observation, append_observation, load_priors
from scripts.update_priors import update, ranked_for_qclass


def test_update_writes_priors_from_observations(tmp_path):
    append_observation(
        Observation("r1", "academic", "pricing", 1, "2026-08-18"), root=tmp_path
    )
    append_observation(
        Observation("r1", "academic", "pricing", 1, "2026-08-18"), root=tmp_path
    )
    update(root=tmp_path)
    got = load_priors(root=tmp_path)
    assert got["academic|pricing"].n == 2


def test_update_on_empty_log_writes_empty_priors(tmp_path):
    update(root=tmp_path)
    assert load_priors(root=tmp_path) == {}


def test_update_is_idempotent_rebuild_not_accumulate(tmp_path):
    append_observation(
        Observation("r1", "academic", "pricing", 1, "2026-08-18"), root=tmp_path
    )
    first = update(root=tmp_path)
    second = update(root=tmp_path)
    assert first == second  # пересчёт из лога, а не инкремент поверх записанного


def test_ranked_for_qclass_returns_only_matching_cells(tmp_path):
    append_observation(
        Observation("r1", "academic", "pricing", 1, "2026-08-18"), root=tmp_path
    )
    append_observation(
        Observation("r1", "web-general", "market-size", 1, "2026-08-18"), root=tmp_path
    )
    priors = update(root=tmp_path)
    ranked = ranked_for_qclass(priors, "pricing")
    assert [key for key, _ in ranked] == ["academic|pricing"]


def test_ranked_for_qclass_not_capped_at_twenty():
    # 25 разных каналов под одним qclass — глобальный топ-20 отрезал бы часть из них
    priors = {f"channel-{i}|pricing": _prior(0.5) for i in range(25)}
    ranked = ranked_for_qclass(priors, "pricing")
    assert len(ranked) == 25


def test_ranked_for_qclass_sorted_by_posterior_mean_desc():
    priors = {
        "weak|pricing": _prior(0.1),
        "strong|pricing": _prior(0.9),
    }
    ranked = ranked_for_qclass(priors, "pricing")
    assert [key for key, _ in ranked] == ["strong|pricing", "weak|pricing"]


def test_ranked_for_qclass_empty_when_no_observations_yet():
    assert ranked_for_qclass({}, "pricing") == []


def _prior(mean):
    from runner.state import Prior

    alpha = mean * 10
    beta = 10 - alpha
    return Prior(alpha=max(alpha, 1.0), beta=max(beta, 1.0), n=10, last_seen="t")
