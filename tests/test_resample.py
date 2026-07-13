import numpy as np
import pandas as pd

from src.data.resample import smote_train


def test_smote_balances_training_classes():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(200, 5)), columns=list("abcde"))
    y = pd.Series([1] * 20 + [0] * 180, name="Class")

    X_resampled, y_resampled = smote_train(X, y, seed=42)

    assert (y_resampled == 1).sum() == (y_resampled == 0).sum() == 180
    assert list(X_resampled.columns) == list("abcde")
    assert y_resampled.name == "Class"


def test_smote_is_reproducible():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(100, 3)), columns=list("abc"))
    y = pd.Series([1] * 10 + [0] * 90)

    first = smote_train(X, y, seed=42)
    second = smote_train(X, y, seed=42)

    pd.testing.assert_frame_equal(first[0], second[0])
    pd.testing.assert_series_equal(first[1], second[1])


def test_smote_does_not_mutate_inputs():
    rng = np.random.default_rng(1)
    X = pd.DataFrame(rng.normal(size=(60, 2)), columns=["a", "b"])
    y = pd.Series([1] * 10 + [0] * 50)
    original_X = X.copy(deep=True)
    original_y = y.copy(deep=True)

    smote_train(X, y)

    pd.testing.assert_frame_equal(X, original_X)
    pd.testing.assert_series_equal(y, original_y)
