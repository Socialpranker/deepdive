from pathlib import Path

from runner.priors import load_channel_groups
from runner.session_bandit import SessionBandit
from runner.state import Prior

FIXTURE = Path(__file__).parent / "fixtures" / "channels_mini.md"


def bandit(priors=None):
    return SessionBandit(priors or {}, load_channel_groups(FIXTURE))


def test_view_starts_equal_to_base_priors():
    base = {"academic|pricing": Prior(3.0, 1.0, 4, "t")}
    assert bandit(base).view()["academic|pricing"].alpha == 3.0


def test_passing_filter_raises_channel_within_session():
    b = bandit({"academic|pricing": Prior(1.0, 1.0, 0, "t")})
    before = b.view()["academic|pricing"].alpha
    b.observe("academic", "pricing", passed_filter=True)
    assert b.view()["academic|pricing"].alpha > before


def test_failing_filter_lowers_channel_within_session():
    b = bandit({"academic|pricing": Prior(1.0, 1.0, 0, "t")})
    b.observe("academic", "pricing", passed_filter=False)
    assert b.view()["academic|pricing"].beta > 1.0


def test_unknown_cell_is_seeded_from_pooled_prior():
    b = bandit({})
    b.observe("api-direct", "market-size", passed_filter=True)
    assert "api-direct|market-size" in b.view()


def test_session_learning_is_never_persisted():
    b = bandit({"academic|pricing": Prior(1.0, 1.0, 0, "t")})
    for _ in range(10):
        b.observe("academic", "pricing", passed_filter=True)
    assert b.persisted_delta() == {}  # быстрый сигнал не уезжает в priors.json


def test_base_priors_are_not_mutated():
    base = {"academic|pricing": Prior(1.0, 1.0, 0, "t")}
    b = SessionBandit(base, load_channel_groups(FIXTURE))
    b.observe("academic", "pricing", passed_filter=True)
    assert (
        base["academic|pricing"].alpha == 1.0
    )  # прогон не портит межпрогонное состояние
