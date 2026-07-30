"""Semantic detector training, metrics, and local reason codes."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from xgboost import XGBClassifier

from src.evaluation.threshold import select_threshold_max_f1
from src.semantic.catalog import FEATURE_CATALOG, FEATURE_NAMES, coarse_bucket


def train_cost_sensitive_xgb(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    *,
    seed: int,
    params: dict | None = None,
) -> XGBClassifier:
    positives = int((y_train == 1).sum())
    negatives = int((y_train == 0).sum())
    config = {
        "n_estimators": 80,
        "max_depth": 3,
        "learning_rate": 0.08,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "eval_metric": "aucpr",
        "tree_method": "hist",
        "n_jobs": 1,
        "random_state": seed,
        "scale_pos_weight": float(negatives / max(1, positives)),
    }
    config.update(params or {})
    model = XGBClassifier(**config)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    return model


def fraud_scores(model: XGBClassifier, X: pd.DataFrame) -> np.ndarray:
    return model.predict_proba(X)[:, 1]


def evaluate_scores(y_true: pd.Series, scores: np.ndarray, threshold: float) -> dict[str, object]:
    y = np.asarray(y_true)
    pred = (np.asarray(scores) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    roc_auc = None if len(np.unique(y)) < 2 else float(roc_auc_score(y, scores))
    auc_pr = float(average_precision_score(y, scores))
    return {
        "auc_pr": auc_pr,
        "roc_auc": roc_auc,
        "threshold": float(threshold),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def fit_and_score(
    splits: dict[str, pd.DataFrame],
    *,
    seed: int,
    xgb_params: dict | None = None,
) -> tuple[XGBClassifier, dict[str, object], dict[str, np.ndarray], float]:
    X_train = splits["train"][FEATURE_NAMES].astype(float)
    X_val = splits["val"][FEATURE_NAMES].astype(float)
    X_test = splits["test"][FEATURE_NAMES].astype(float)
    y_train = splits["train"]["Class"].astype(int)
    y_val = splits["val"]["Class"].astype(int)
    y_test = splits["test"]["Class"].astype(int)
    started = time.time()
    model = train_cost_sensitive_xgb(
        X_train,
        y_train,
        X_val,
        y_val,
        seed=seed,
        params=xgb_params,
    )
    train_seconds = time.time() - started
    scores = {
        "val": fraud_scores(model, X_val),
        "test": fraud_scores(model, X_test),
    }
    threshold = select_threshold_max_f1(y_val, scores["val"])
    metrics = {
        "feature_names": FEATURE_NAMES,
        "val": evaluate_scores(y_val, scores["val"], threshold),
        "test": evaluate_scores(y_test, scores["test"], threshold),
        "runtime": {"train_seconds": train_seconds},
        "resolved_xgb_params": {
            key: value.item() if hasattr(value, "item") else value
            for key, value in model.get_xgb_params().items()
        },
    }
    return model, metrics, scores, threshold


def shap_contributions(model: XGBClassifier, X: pd.DataFrame) -> np.ndarray:
    matrix = xgb.DMatrix(X[FEATURE_NAMES].astype(float), feature_names=FEATURE_NAMES)
    values = model.get_booster().predict(matrix, pred_contribs=True)
    return np.asarray(values)[:, : len(FEATURE_NAMES)]


def reason_codes_for_frame(
    frame: pd.DataFrame,
    shap_matrix: np.ndarray,
    *,
    top_k: int = 3,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for row_index, (_, row) in enumerate(frame.reset_index(drop=True).iterrows()):
        values = shap_matrix[row_index]
        order = np.argsort(-np.abs(values), kind="stable")[:top_k]
        codes = []
        for rank, feature_index in enumerate(order, start=1):
            key = FEATURE_NAMES[int(feature_index)]
            value = float(row[key])
            codes.append(
                {
                    "rank": rank,
                    "key": key,
                    "feature": key,
                    "label": FEATURE_CATALOG[key].label,
                    "direction": "increases_risk" if values[feature_index] > 0 else "decreases_risk",
                    "shap_value": float(values[feature_index]),
                    "coarse_bucket": coarse_bucket(key, value),
                }
            )
        records.append(
            {
                "case_id": int(row["case_id"]),
                "transaction_id": row["transaction_id"],
                "codes": codes,
            }
        )
    return records
