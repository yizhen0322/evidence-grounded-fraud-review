import pandas as pd
import pytest

from src.data.load import CASE_ID
from src.data.split import split_summary, stratified_split


def make_df(n=2000, fraud_rate=0.05):
    n_fraud = int(n * fraud_rate)
    return pd.DataFrame(
        {CASE_ID: range(n), "Class": [1] * n_fraud + [0] * (n - n_fraud)}
    ).sample(frac=1, random_state=0).reset_index(drop=True)


def test_split_proportions_and_stratification():
    splits = stratified_split(make_df(), seed=42)
    n = len(splits.train) + len(splits.val) + len(splits.test)
    assert n == 2000
    assert abs(len(splits.train) / n - 0.70) < 0.01
    assert abs(len(splits.val) / n - 0.15) < 0.01
    for part in (splits.train, splits.val, splits.test):
        assert abs(part["Class"].mean() - 0.05) < 0.01


def test_split_is_reproducible_and_disjoint():
    first = stratified_split(make_df(), seed=42)
    second = stratified_split(make_df(), seed=42)
    assert first.train[CASE_ID].tolist() == second.train[CASE_ID].tolist()
    parts = [set(part[CASE_ID]) for part in (first.train, first.val, first.test)]
    assert parts[0].isdisjoint(parts[1])
    assert parts[0].isdisjoint(parts[2])
    assert parts[1].isdisjoint(parts[2])
    assert len(set.union(*parts)) == 2000


def test_split_summary_reports_counts():
    info = split_summary(stratified_split(make_df(), seed=42))
    assert set(info) == {"train", "val", "test"}
    assert info["test"]["n"] == 300 and "fraud_ratio" in info["test"]


def test_split_rejects_duplicate_case_ids():
    df = make_df()
    df.loc[1, CASE_ID] = df.loc[0, CASE_ID]
    with pytest.raises(ValueError, match="case_id"):
        stratified_split(df, seed=42)
