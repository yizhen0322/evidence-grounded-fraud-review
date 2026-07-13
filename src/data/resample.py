"""SMOTE applied to the training split only."""

import pandas as pd
from imblearn.over_sampling import SMOTE

__all__ = ["smote_train"]


def smote_train(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.Series]:
    """Balance the training data while preserving pandas labels and columns."""
    X_resampled, y_resampled = SMOTE(random_state=seed).fit_resample(
        X_train,
        y_train,
    )
    return X_resampled, y_resampled
