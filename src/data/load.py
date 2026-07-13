"""Load and validate the ULB credit card fraud dataset."""

from pathlib import Path

import pandas as pd

FEATURES = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]
TARGET = "Class"
CASE_ID = "case_id"
EXPECTED_ROWS = 284_807
EXPECTED_FRAUDS = 492


def load_raw(path: str | Path, validate: bool = True) -> pd.DataFrame:
    df = pd.read_csv(path)
    if list(df.columns) != FEATURES + [TARGET]:
        raise ValueError(f"Unexpected columns: {list(df.columns)}")
    if validate:
        if len(df) != EXPECTED_ROWS:
            raise ValueError(f"Expected {EXPECTED_ROWS} rows, got {len(df)}")
        frauds = int(df[TARGET].sum())
        if frauds != EXPECTED_FRAUDS:
            raise ValueError(f"Expected {EXPECTED_FRAUDS} frauds, got {frauds}")
    df.insert(0, CASE_ID, range(len(df)))
    return df


def dedupe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    content_columns = [column for column in df.columns if column != CASE_ID]
    out = df.drop_duplicates(subset=content_columns).reset_index(drop=True)
    return out, len(df) - len(out)
