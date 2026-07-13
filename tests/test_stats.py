import pytest

from src.evaluation.stats import wilson_ci


def test_wilson_ci_known_value():
    lower, upper = wilson_ci(8, 10)
    assert lower == pytest.approx(0.490, abs=1e-3)
    assert upper == pytest.approx(0.943, abs=1e-3)


def test_wilson_ci_edges():
    assert wilson_ci(0, 0) == (0.0, 1.0)
    lower, upper = wilson_ci(10, 10)
    assert lower > 0.72 and upper == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("successes,n", [(-1, 10), (11, 10), (0, -1)])
def test_wilson_ci_rejects_invalid_counts(successes, n):
    with pytest.raises(ValueError):
        wilson_ci(successes, n)
