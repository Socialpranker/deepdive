import time
import pytest
from runner.providers import run_parallel


def test_run_parallel_preserves_order():
    thunks = [(lambda i=i: f"r{i}") for i in range(5)]
    assert run_parallel(thunks) == ["r0", "r1", "r2", "r3", "r4"]


def test_run_parallel_is_concurrent():
    def slow(i):
        time.sleep(0.2)
        return i
    thunks = [(lambda i=i: slow(i)) for i in range(5)]
    start = time.monotonic()
    out = run_parallel(thunks, limit=5)
    elapsed = time.monotonic() - start
    assert out == [0, 1, 2, 3, 4]
    assert elapsed < 0.8  # parallel ~0.2s (4x headroom); serial would be ~1.0s — still discriminates


def test_run_parallel_fails_loud():
    def boom():
        raise ValueError("boom")
    thunks = [lambda: "ok", boom]
    with pytest.raises(ValueError, match="boom"):
        run_parallel(thunks)


def test_run_parallel_empty():
    assert run_parallel([]) == []
