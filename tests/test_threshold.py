import numpy as np
import pytest
from sklearn.metrics import precision_recall_curve

from src.evaluation.metrics import evaluate
from src.evaluation.threshold import select_threshold_max_f1


def test_selected_threshold_maximizes_f1_on_validation():
    y = np.array([0] * 90 + [1] * 10)
    scores = np.concatenate(
        [np.linspace(0.0, 0.55, 90), np.linspace(0.5, 1.0, 10)]
    )

    threshold = select_threshold_max_f1(y, scores)
    best_f1 = evaluate(y, scores, threshold)["f1"]

    for other in np.linspace(0.01, 0.99, 99):
        assert best_f1 >= evaluate(y, scores, other)["f1"] - 1e-9


def test_selected_threshold_is_from_the_precision_recall_candidates():
    y = np.array([0, 1, 0, 1, 0, 1])
    scores = np.array([0.05, 0.8, 0.2, 0.7, 0.6, 0.9])
    _, _, candidate_thresholds = precision_recall_curve(y, scores)

    threshold = select_threshold_max_f1(y, scores)

    assert threshold in candidate_thresholds
    assert threshold == pytest.approx(0.7)


def test_threshold_selection_rejects_empty_validation_scores():
    with pytest.raises(ValueError, match="empty validation scores"):
        select_threshold_max_f1([], [])
