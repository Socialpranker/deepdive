from runner.state import Observation, append_observation, load_priors
from scripts.update_priors import update


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
