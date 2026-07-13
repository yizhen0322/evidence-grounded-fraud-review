"""Convert XGBoost SHAP evidence into standardized reason codes.

TreeExplainer operates in raw margin space for the binary fraud model. Positive
SHAP values push the prediction toward fraud; negative values push away.
"""

import numpy as np
import pandas as pd
import shap


def shap_values_for(model, X) -> np.ndarray:
    """Return a two-dimensional row-by-feature SHAP matrix."""
    explanation = shap.TreeExplainer(model)(X)
    values = np.asarray(explanation.values)
    if values.ndim != 2:
        raise ValueError(f"expected 2D binary-class SHAP values, got {values.shape}")
    return values


def local_reason_codes(
    shap_row: np.ndarray,
    feature_names: list[str],
    top_k: int = 3,
) -> list[dict]:
    """Rank non-zero local contributions by absolute magnitude."""
    values = np.asarray(shap_row)
    if values.ndim != 1 or len(values) != len(feature_names):
        raise ValueError("SHAP row and feature_names must have matching lengths")
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    order = np.argsort(-np.abs(values), kind="stable")
    order = [int(index) for index in order if values[index] != 0][:top_k]
    return [
        {
            "feature": feature_names[index],
            "direction": (
                "increases_risk" if values[index] > 0 else "decreases_risk"
            ),
            "rank": rank,
            "shap_value": float(values[index]),
        }
        for rank, index in enumerate(order, start=1)
    ]


def global_importance(
    shap_matrix: np.ndarray,
    feature_names: list[str],
) -> pd.Series:
    """Return mean absolute SHAP contribution in descending order."""
    values = np.asarray(shap_matrix)
    if values.ndim != 2 or values.shape[1] != len(feature_names):
        raise ValueError("SHAP matrix width must match feature_names")
    return pd.Series(
        np.abs(values).mean(axis=0),
        index=feature_names,
        name="mean_abs_shap",
    ).sort_values(ascending=False, kind="stable")
