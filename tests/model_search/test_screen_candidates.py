import numpy as np
import pandas as pd
import pytest

from src.data.load import CASE_ID, FEATURES, TARGET
from tools.model_search.screen_candidates import (
    assert_disjoint_case_ids,
    evaluate_at_k,
    load_development_and_legacy_test,
    make_inner_split,
    make_outer_folds,
    _predict_scores,
    select_thresholds,
)


def _frame(n=300, positives=30):
    values = {
        CASE_ID: range(n),
        TARGET: [1] * positives + [0] * (n - positives),
    }
    for index, feature in enumerate(FEATURES):
        values[feature] = np.linspace(0, 1, n) + index
    return pd.DataFrame(values).sample(frac=1, random_state=7).reset_index(drop=True)


def test_select_thresholds_uses_calibration_scores_for_all_policies():
    y = np.array([1] * 5 + [0] * 10)
    scores = np.array(
        [
            0.99,
            0.98,
            0.97,
            0.30,
            0.29,
            0.96,
            0.95,
            0.94,
            0.93,
            0.92,
            0.91,
            0.90,
            0.89,
            0.28,
            0.27,
        ]
    )

    decisions = select_thresholds(y, scores, min_precision=0.90)

    assert set(decisions) == {
        "max_f1",
        "max_f2",
        "max_recall_at_precision_0_90",
    }
    assert decisions["max_f1"].threshold == pytest.approx(0.97)
    assert decisions["max_f2"].threshold == pytest.approx(0.29)
    assert decisions["max_recall_at_precision_0_90"].threshold == pytest.approx(0.97)
    assert decisions["max_recall_at_precision_0_90"].calibration_precision >= 0.90


def test_select_threshold_precision_policy_reports_unachievable_target():
    y = np.array([1, 1, 0, 0])
    scores = np.array([0.8, 0.7, 0.95, 0.9])

    decision = select_thresholds(y, scores, min_precision=0.90)[
        "max_recall_at_precision_0_90"
    ]

    assert decision.calibration_precision < 0.90
    assert decision.threshold in scores


def test_evaluate_at_k_matches_analyst_queue_metrics():
    y = np.array([1, 0, 1, 0, 1])
    scores = np.array([0.9, 0.8, 0.7, 0.6, 0.5])

    metrics = evaluate_at_k(y, scores, k=2)

    assert metrics == {
        "k": 2,
        "true_positives": 1,
        "precision_at_k": 0.5,
        "recall_at_k": pytest.approx(1 / 3),
    }


def test_rank_ensemble_combines_member_orderings():
    class DummyModel:
        def __init__(self, scores):
            self.scores = np.asarray(scores)

        def predict_proba(self, X):
            del X
            return np.column_stack([1 - self.scores, self.scores])

    first = DummyModel([0.9, 0.2, 0.1])
    second = DummyModel([0.3, 0.8, 0.1])

    scores = _predict_scores((first, second), np.zeros((3, 1)))

    assert scores.tolist() == pytest.approx([0.75, 0.75, 0.0])


def test_development_data_excludes_seed42_legacy_test_split(tmp_path):
    original = _frame(n=300, positives=30).drop(columns=[CASE_ID])
    original = original[FEATURES + [TARGET]]
    data_path = tmp_path / "creditcard.csv"
    original.to_csv(data_path, index=False)

    development, legacy_test, metadata = load_development_and_legacy_test(
        data_path,
        seed=42,
        validate_data=False,
    )

    development_ids = set(development[CASE_ID])
    legacy_test_ids = set(legacy_test[CASE_ID])
    assert development_ids.isdisjoint(legacy_test_ids)
    assert len(development) == 255
    assert len(legacy_test) == 45
    assert len(development_ids | legacy_test_ids) == 300
    assert metadata == {"dedup_dropped": 0}


def test_outer_and_inner_splits_are_case_id_disjoint():
    development = _frame(n=300, positives=30)
    outer_train, outer_holdout = make_outer_folds(
        development,
        folds=3,
        seed=42,
    )[0]
    inner = make_inner_split(outer_train, seed=43)

    assert_disjoint_case_ids(
        {
            "inner_train": inner.train,
            "early_stop": inner.early_stop,
            "threshold_calibration": inner.threshold_calibration,
            "outer_holdout": outer_holdout,
        }
    )
    combined_ids = (
        set(inner.train[CASE_ID])
        | set(inner.early_stop[CASE_ID])
        | set(inner.threshold_calibration[CASE_ID])
        | set(outer_holdout[CASE_ID])
    )
    assert combined_ids == set(development[CASE_ID])


def test_split_isolation_detects_overlap():
    first = pd.DataFrame({CASE_ID: [1, 2], TARGET: [0, 1]})
    second = pd.DataFrame({CASE_ID: [2, 3], TARGET: [1, 0]})

    with pytest.raises(RuntimeError, match="appears in both"):
        assert_disjoint_case_ids({"first": first, "second": second})
