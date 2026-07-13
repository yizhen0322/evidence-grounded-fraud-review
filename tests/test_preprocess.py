import numpy as np
import pandas as pd

from src.data.load import CASE_ID, FEATURES
from src.data.preprocess import apply_scaler, fit_scaler


def make_df(shift=0.0, n=500, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.normal(shift, 1.0, (n, 30)), columns=FEATURES)
    df.insert(0, CASE_ID, range(n))
    df["Class"] = 0
    return df


def test_scaler_standardizes_train():
    train = make_df()
    scaled = apply_scaler(fit_scaler(train), train)
    assert abs(scaled["Amount"].mean()) < 1e-9
    assert abs(scaled["Amount"].std(ddof=0) - 1.0) < 1e-6


def test_scaler_uses_train_params_on_other_splits():
    train, val = make_df(shift=0.0), make_df(shift=5.0, seed=1)
    scaled_val = apply_scaler(fit_scaler(train), val)
    assert scaled_val["V1"].mean() > 3.0


def test_apply_scaler_does_not_mutate_input():
    train = make_df()
    before = train["Amount"].copy()
    apply_scaler(fit_scaler(train), train)
    pd.testing.assert_series_equal(train["Amount"], before)


def test_case_id_is_preserved_and_not_scaled():
    train = make_df()
    scaled = apply_scaler(fit_scaler(train), train)
    pd.testing.assert_series_equal(scaled[CASE_ID], train[CASE_ID])
    assert CASE_ID not in FEATURES
