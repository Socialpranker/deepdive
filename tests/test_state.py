from runner.state import (
    Observation,
    Prior,
    prior_key,
    state_dir,
    append_observation,
    read_observations,
    load_priors,
    save_priors,
)


def test_prior_key_joins_channel_and_qclass():
    assert prior_key("academic", "scientific-claim") == "academic|scientific-claim"


def test_append_and_read_observations_roundtrip(tmp_path):
    obs = Observation(
        run_id="r1",
        channel="academic",
        qclass="scientific-claim",
        reward=1,
        ts="2026-08-18T10:00:00Z",
    )
    append_observation(obs, root=tmp_path)
    append_observation(
        Observation("r1", "web-general", "pricing", 0, "2026-08-18T10:01:00Z"),
        root=tmp_path,
    )
    got = read_observations(root=tmp_path)
    assert [o.channel for o in got] == ["academic", "web-general"]
    assert got[0].reward == 1


def test_read_observations_skips_malformed_lines(tmp_path):
    p = state_dir(tmp_path) / "observations.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        '{"run_id":"r1","channel":"academic","qclass":"pricing","reward":1,"ts":"t"}\n'
        "not json at all\n"
        '{"run_id":"r2"}\n',
        encoding="utf-8",
    )
    got = read_observations(root=tmp_path)
    assert len(got) == 1  # битые строки не роняют чтение


def test_save_and_load_priors_roundtrip(tmp_path):
    priors = {
        "academic|pricing": Prior(alpha=2.0, beta=3.0, n=5, last_seen="2026-08-18")
    }
    save_priors(priors, root=tmp_path)
    got = load_priors(root=tmp_path)
    assert got["academic|pricing"].alpha == 2.0
    assert got["academic|pricing"].n == 5


def test_load_priors_returns_empty_on_missing_file(tmp_path):
    assert load_priors(root=tmp_path) == {}


def test_load_priors_returns_empty_on_corrupt_file(tmp_path):
    d = state_dir(tmp_path)
    d.mkdir(parents=True, exist_ok=True)
    (d / "priors.json").write_text("{ broken", encoding="utf-8")
    assert load_priors(root=tmp_path) == {}


def test_save_priors_is_atomic_no_tmp_left(tmp_path):
    save_priors({"a|b": Prior(1.0, 1.0, 0, "2026-08-18")}, root=tmp_path)
    leftovers = list(state_dir(tmp_path).glob("*.tmp"))
    assert leftovers == []
