import numpy as np

from src.explainability.reason_codes import (
    global_importance,
    local_reason_codes,
    shap_values_for,
)
from src.models.xgb import train_xgboost


def test_local_reason_codes_rank_by_magnitude_and_sign():
    row = np.array([0.05, -2.0, 1.0, 0.0])
    names = ["Time", "V1", "V2", "Amount"]

    codes = local_reason_codes(row, names, top_k=2)

    assert [code["feature"] for code in codes] == ["V1", "V2"]
    assert codes[0]["direction"] == "decreases_risk"
    assert codes[1]["direction"] == "increases_risk"
    assert [code["rank"] for code in codes] == [1, 2]


def test_local_reason_codes_omit_zero_contributions():
    codes = local_reason_codes(
        np.array([0.0, 1.0, 0.0]),
        ["a", "b", "c"],
        top_k=3,
    )

    assert codes == [
        {
            "feature": "b",
            "direction": "increases_risk",
            "rank": 1,
            "shap_value": 1.0,
        }
    ]


def test_global_importance_is_mean_absolute_value():
    matrix = np.array([[1.0, -3.0], [-1.0, 3.0]])

    importance = global_importance(matrix, ["a", "b"])

    assert importance["b"] == 3.0
    assert importance["a"] == 1.0
    assert list(importance.index) == ["b", "a"]


def test_shap_values_match_binary_xgboost_feature_width():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(120, 3))
    y = (X[:, 0] > 0).astype(int)
    model = train_xgboost(
        X[:80],
        y[:80],
        X[80:],
        y[80:],
        params={"n_estimators": 20},
    )

    values = shap_values_for(model, X[80:85])

    assert values.shape == (5, 3)
