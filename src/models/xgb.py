"""XGBoost classifier wrapper with validation-based early stopping."""

import numpy as np
from xgboost import XGBClassifier

DEFAULT_PARAMS = {
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "eval_metric": "aucpr",
    "tree_method": "hist",
    "n_jobs": -1,
}


def train_xgboost(
    X_train,
    y_train,
    X_val,
    y_val,
    params=None,
    seed: int = 42,
    early_stopping_rounds: int = 30,
) -> XGBClassifier:
    """Train using validation AUC-PR for early stopping."""
    config = {**DEFAULT_PARAMS, **(params or {}), "random_state": seed}
    model = XGBClassifier(
        **config,
        early_stopping_rounds=early_stopping_rounds,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    return model


def fraud_scores(model: XGBClassifier, X) -> np.ndarray:
    """Return probability estimates for the fraud class."""
    return model.predict_proba(X)[:, 1]
