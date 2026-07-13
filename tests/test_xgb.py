import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from src.models.xgb import fraud_scores, train_xgboost


def make_separable(n=400, seed=0):
    rng = np.random.default_rng(seed)
    y = pd.Series((rng.random(n) < 0.3).astype(int))
    X = pd.DataFrame(
        {
            "f1": y * 2.0 + rng.normal(0, 0.3, n),
            "f2": rng.normal(size=n),
        }
    )
    return X, y


def test_xgboost_learns_separable_data():
    X, y = make_separable()
    X_val, y_val = make_separable(seed=1)

    model = train_xgboost(
        X,
        y,
        X_val,
        y_val,
        params={"n_estimators": 50},
        seed=42,
    )
    scores = fraud_scores(model, X_val)

    assert scores.shape == (400,)
    assert scores[y_val == 1].mean() > scores[y_val == 0].mean()
    assert average_precision_score(y_val, scores) > 0.95
    assert model.get_params()["eval_metric"] == "aucpr"


def test_scale_pos_weight_passes_through():
    X, y = make_separable()

    model = train_xgboost(
        X,
        y,
        X,
        y,
        params={"scale_pos_weight": 7.0, "n_estimators": 10},
    )

    assert model.get_params()["scale_pos_weight"] == 7.0
