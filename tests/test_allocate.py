import random
from pathlib import Path

from runner.adaptive import Budget
from runner.priors import load_channel_groups
from runner.state import Prior

FIXTURE = Path(__file__).parent / "fixtures" / "channels_mini.md"
CANDIDATES = ["academic", "web-general", "api-direct"]


def groups():
    return load_channel_groups(FIXTURE)


def test_allocate_returns_requested_number_of_slots():
    b = Budget.for_depth("deep")
    got, _ = b.allocate("pricing", 2, CANDIDATES, {}, groups(), random.Random(1))
    assert len(got) == 2


def test_missing_priors_report_fallback_flag():
    b = Budget.for_depth("deep")
    channels, fallback = b.allocate(
        "pricing", 2, CANDIDATES, {}, groups(), random.Random(1)
    )
    assert len(channels) == 2
    assert fallback is True  # пустые приоры — это фолбэк, и он виден снаружи


def test_populated_priors_report_no_fallback():
    b = Budget.for_depth("deep")
    priors = {"academic|pricing": Prior(3.0, 1.0, 4, "t")}
    _, fallback = b.allocate(
        "pricing", 1, CANDIDATES, priors, groups(), random.Random(1)
    )
    assert fallback is False


def test_fallback_is_logged_not_silent(caplog):
    import logging

    b = Budget.for_depth("deep")
    with caplog.at_level(logging.WARNING):
        b.allocate("pricing", 1, CANDIDATES, {}, groups(), random.Random(1))
    assert any("uniform" in r.message.lower() for r in caplog.records)


def test_allocate_never_repeats_a_channel():
    b = Budget.for_depth("deep")
    got, _ = b.allocate("pricing", 3, CANDIDATES, {}, groups(), random.Random(1))
    assert len(set(got)) == len(got)


def test_allocate_caps_at_candidate_count():
    b = Budget.for_depth("deep")
    got, _ = b.allocate("pricing", 99, CANDIDATES, {}, groups(), random.Random(1))
    assert len(got) == 3


def test_allocate_is_deterministic_under_a_fixed_seed():
    b = Budget.for_depth("deep")
    a, _ = b.allocate("pricing", 2, CANDIDATES, {}, groups(), random.Random(42))
    c, _ = b.allocate("pricing", 2, CANDIDATES, {}, groups(), random.Random(42))
    assert a == c


# NOTE (поправка принята автором задачи): исходные Beta(30,1) / Beta(1,30) из брифа
# практически не пересекаются (P(слабый > сильный) ~ 1e-20) — тест на exploration
# был обречён падать всегда. Проверено Monte-Carlo и на менее экстремальных
# Beta(8,2)/Beta(2,8) — P(weak wins) ~ 0.0018, ожидание < 1 события на 200 сэмплов,
# 0/200 в детерминированном прогоне seeds 0..199. Взяты Beta(6,4)/Beta(4,6):
# strong 67/100 (> 60), weak 22/200 (>= 1) — оба свойства держатся с запасом.
def test_strong_channel_wins_the_majority_of_draws():
    priors = {
        "academic|pricing": Prior(6.0, 4.0, 10, "t"),
        "web-general|pricing": Prior(4.0, 6.0, 10, "t"),
        "api-direct|pricing": Prior(4.0, 6.0, 10, "t"),
    }
    b = Budget.for_depth("deep")
    picks = [
        b.allocate("pricing", 1, CANDIDATES, priors, groups(), random.Random(s))[0][0]
        for s in range(100)
    ]
    assert picks.count("academic") > 60


def test_weak_channel_still_gets_explored():
    priors = {
        "academic|pricing": Prior(6.0, 4.0, 10, "t"),
        "web-general|pricing": Prior(4.0, 6.0, 10, "t"),
        "api-direct|pricing": Prior(4.0, 6.0, 10, "t"),
    }
    b = Budget.for_depth("deep")
    picks = [
        b.allocate("pricing", 1, CANDIDATES, priors, groups(), random.Random(s))[0][0]
        for s in range(200)
    ]
    assert picks.count("web-general") >= 1  # Thompson не запирает слабый канал навсегда


def test_zero_free_slots_yields_nothing():
    b = Budget.for_depth("shallow")
    assert b.allocate("pricing", 0, CANDIDATES, {}, groups(), random.Random(1)) == (
        [],
        False,
    )
