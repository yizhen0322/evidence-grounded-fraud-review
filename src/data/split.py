"""Stratified train/validation/test split performed before any model fitting."""

from dataclasses import dataclass

import pandas as pd
from sklearn.model_selection import train_test_split

from src.data.load import CASE_ID, TARGET


@dataclass
class Splits:
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame


def stratified_split(
    df: pd.DataFrame,
    seed: int = 42,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    test_frac: float = 0.15,
) -> Splits:
    if abs(train_frac + val_frac + test_frac - 1.0) >= 1e-9:
        raise ValueError("train/validation/test fractions must sum to 1")
    if CASE_ID not in df.columns or df[CASE_ID].isna().any() or not df[CASE_ID].is_unique:
        raise ValueError("case_id must be present, non-null, and unique before splitting")

    rest, test = train_test_split(
        df,
        test_size=test_frac,
        stratify=df[TARGET],
        random_state=seed,
    )
    train, val = train_test_split(
        rest,
        test_size=val_frac / (1 - test_frac),
        stratify=rest[TARGET],
        random_state=seed,
    )
    splits = Splits(
        train.reset_index(drop=True),
        val.reset_index(drop=True),
        test.reset_index(drop=True),
    )
    id_sets = [set(part[CASE_ID]) for part in (splits.train, splits.val, splits.test)]
    if not (
        id_sets[0].isdisjoint(id_sets[1])
        and id_sets[0].isdisjoint(id_sets[2])
        and id_sets[1].isdisjoint(id_sets[2])
        and len(set.union(*id_sets)) == len(df)
    ):
        raise RuntimeError("case_id split contract violated")
    return splits


def split_summary(splits: Splits) -> dict:
    def info(part: pd.DataFrame) -> dict:
        return {
            "n": int(len(part)),
            "frauds": int(part[TARGET].sum()),
            "fraud_ratio": float(part[TARGET].mean()),
        }

    return {
        "train": info(splits.train),
        "val": info(splits.val),
        "test": info(splits.test),
    }
