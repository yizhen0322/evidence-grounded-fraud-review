import numpy as np
import pytest

from src.evaluation.metrics import evaluate, precision_at_k, recall_at_k


def test_precision_and_recall_at_k():
    y = np.array([1, 1, 0, 0, 1, 0])
    scores = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.1])

    assert precision_at_k(y, scores, k=2) == 1.0
    assert recall_at_k(y, scores, k=2) == 2 / 3


def test_top_k_handles_k_larger_than_dataset():
    y = np.array([1, 0, 0])
    scores = np.array([0.9, 0.2, 0.1])

    assert precision_at_k(y, scores, k=100) == 1 / 3
    assert recall_at_k(y, scores, k=100) == 1.0


def test_recall_at_k_is_zero_when_there_are_no_positives():
    assert recall_at_k([0, 0], [0.9, 0.1], k=1) == 0.0


def test_top_k_rejects_non_positive_k():
    with pytest.raises(ValueError, match="k must be positive"):
        precision_at_k([0, 1], [0.1, 0.9], k=0)


def test_evaluate_perfect_classifier():
    y = np.array([0, 0, 1, 1])
    scores = np.array([0.1, 0.2, 0.9, 0.95])

    metrics = evaluate(y, scores, threshold=0.5)

    assert metrics["auc_pr"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert (metrics["tp"], metrics["tn"], metrics["fp"], metrics["fn"]) == (
        2,
        2,
        0,
        0,
    )


def test_evaluate_applies_the_supplied_threshold():
    y = np.array([0, 1, 1])
    scores = np.array([0.4, 0.6, 0.45])

    metrics = evaluate(y, scores, threshold=0.5)

    assert metrics["threshold"] == 0.5
    assert metrics["tp"] == 1
    assert metrics["fn"] == 1
