"""Uniform evaluation for every detector experiment.

AUC-PR is the primary model-selection metric for the imbalanced fraud task.
"""

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def _top_k_indices(scores, k: int) -> np.ndarray:
    if k <= 0:
        raise ValueError("k must be positive")
    # Preserve input order when scores tie so repeated runs select the same rows.
    return np.argsort(-np.asarray(scores), kind="stable")[:k]


def precision_at_k(y_true, scores, k: int = 100) -> float:
    """Return precision among the available top ``min(k, n)`` cases."""
    y = np.asarray(y_true)
    indices = _top_k_indices(scores, k)
    if indices.size == 0:
        return 0.0
    return float(y[indices].mean())


def recall_at_k(y_true, scores, k: int = 100) -> float:
    """Return the fraction of all fraud cases captured in the top k scores."""
    y = np.asarray(y_true)
    total_positives = y.sum()
    if total_positives == 0:
        return 0.0
    indices = _top_k_indices(scores, k)
    return float(y[indices].sum() / total_positives)


def evaluate(y_true, scores, threshold: float) -> dict:
    """Evaluate continuous fraud scores at one already-selected threshold."""
    y = np.asarray(y_true)
    score_array = np.asarray(scores)
    predictions = (score_array >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel()

    return {
        "auc_pr": float(average_precision_score(y, score_array)),
        "roc_auc": float(roc_auc_score(y, score_array)),
        "threshold": float(threshold),
        "precision": float(precision_score(y, predictions, zero_division=0)),
        "recall": float(recall_score(y, predictions, zero_division=0)),
        "f1": float(f1_score(y, predictions, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "precision_at_100": precision_at_k(y, score_array, 100),
        "recall_at_100": recall_at_k(y, score_array, 100),
    }
