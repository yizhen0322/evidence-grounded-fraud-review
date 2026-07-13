"""Train-only fitted feature scaling."""

import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.data.load import FEATURES


def fit_scaler(train_df: pd.DataFrame) -> StandardScaler:
    return StandardScaler().fit(train_df[FEATURES])


def apply_scaler(scaler: StandardScaler, df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out[FEATURES] = scaler.transform(df[FEATURES])
    return out
