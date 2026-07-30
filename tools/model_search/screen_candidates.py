"""Screen detector candidates without touching the legacy test split.

The runner uses the existing seed-42 train/validation/test split only to define
development data: train + validation. The held-out legacy test split is excluded
from model selection. Candidate estimates come from stratified outer CV inside
development data, with per-fold train/early-stop/threshold-calibration splits.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from imblearn.ensemble import BalancedRandomForestClassifier, EasyEnsembleClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.data.load import CASE_ID, FEATURES, TARGET, dedupe, load_raw
from src.data.preprocess import apply_scaler, fit_scaler
from src.data.split import stratified_split

DEFAULT_SEED = 42
DEFAULT_CANDIDATES = (
    "xgb_unweighted",
    "xgb_cost_sensitive",
    "lightgbm_unweighted",
    "lightgbm_cost_sensitive",
    "catboost_unweighted",
    "catboost_cost_sensitive",
    "xgb_catboost_rank_ensemble",
    "balanced_random_forest",
    "easy_ensemble",
    "hist_gradient_boosting_balanced",
    "logistic_regression",
)


@dataclass(frozen=True)
class InnerSplit:
    train: pd.DataFrame
    early_stop: pd.DataFrame
    threshold_calibration: pd.DataFrame


@dataclass(frozen=True)
class ThresholdDecision:
    policy: str
    threshold: float
    calibration_precision: float
    calibration_recall: float
    calibration_f1: float
    calibration_f2: float


def _fbeta(precision: np.ndarray, recall: np.ndarray, beta: float) -> np.ndarray:
    beta_squared = beta * beta
    numerator = (1.0 + beta_squared) * precision * recall
    denominator = beta_squared * precision + recall
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=float),
        where=denominator > 0,
    )


def select_thresholds(
    y_true,
    scores,
    min_precision: float = 0.90,
) -> dict[str, ThresholdDecision]:
    """Select thresholds using only calibration labels and scores."""
    y_array = np.asarray(y_true)
    score_array = np.asarray(scores)
    if y_array.size == 0 or score_array.size == 0:
        raise ValueError("cannot select thresholds from empty calibration data")
    if y_array.size != score_array.size:
        raise ValueError("labels and scores must have the same length")
    if np.unique(y_array).size < 2:
        raise ValueError("calibration data must contain both classes")

    precision, recall, thresholds = precision_recall_curve(y_array, score_array)
    if thresholds.size == 0:
        raise ValueError("no threshold candidates were produced")

    precision_at_threshold = precision[:-1]
    recall_at_threshold = recall[:-1]
    f1 = _fbeta(precision_at_threshold, recall_at_threshold, beta=1.0)
    f2 = _fbeta(precision_at_threshold, recall_at_threshold, beta=2.0)

    def decision(policy: str, index: int) -> ThresholdDecision:
        return ThresholdDecision(
            policy=policy,
            threshold=float(thresholds[index]),
            calibration_precision=float(precision_at_threshold[index]),
            calibration_recall=float(recall_at_threshold[index]),
            calibration_f1=float(f1[index]),
            calibration_f2=float(f2[index]),
        )

    max_f1_index = int(np.lexsort((-recall_at_threshold, -f1))[0])
    max_f2_index = int(np.lexsort((-recall_at_threshold, -f2))[0])
    eligible = np.flatnonzero(precision_at_threshold >= min_precision)
    if eligible.size:
        eligible_order = np.lexsort(
            (
                -precision_at_threshold[eligible],
                -recall_at_threshold[eligible],
            )
        )
        recall_at_precision_index = int(eligible[eligible_order[0]])
    else:
        # Explicitly return the highest-precision point so callers can see the
        # precision target was not achievable on calibration data.
        recall_at_precision_index = int(
            np.lexsort((-recall_at_threshold, -precision_at_threshold))[0]
        )

    return {
        "max_f1": decision("max_f1", max_f1_index),
        "max_f2": decision("max_f2", max_f2_index),
        "max_recall_at_precision_0_90": decision(
            "max_recall_at_precision_0_90",
            recall_at_precision_index,
        ),
    }


def evaluate_at_threshold(y_true, scores, threshold: float) -> dict[str, float | int]:
    y_array = np.asarray(y_true)
    score_array = np.asarray(scores)
    pred = (score_array >= threshold).astype(int)
    tp = int(((pred == 1) & (y_array == 1)).sum())
    fp = int(((pred == 1) & (y_array == 0)).sum())
    fn = int(((pred == 0) & (y_array == 1)).sum())
    tn = int(((pred == 0) & (y_array == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    f2_denominator = 4 * precision + recall
    f2 = 5 * precision * recall / f2_denominator if f2_denominator else 0.0
    return {
        "threshold": float(threshold),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "f2": float(f2),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def evaluate_at_k(y_true, scores, k: int = 100) -> dict[str, float | int]:
    """Evaluate an analyst queue containing the highest-scoring k cases."""
    y_array = np.asarray(y_true)
    score_array = np.asarray(scores)
    if y_array.size != score_array.size:
        raise ValueError("labels and scores must have the same length")
    if k <= 0:
        raise ValueError("k must be positive")
    selected_n = min(k, y_array.size)
    selected = np.argsort(-score_array, kind="stable")[:selected_n]
    true_positives = int(y_array[selected].sum())
    total_positives = int(y_array.sum())
    return {
        "k": selected_n,
        "true_positives": true_positives,
        "precision_at_k": true_positives / selected_n if selected_n else 0.0,
        "recall_at_k": true_positives / total_positives if total_positives else 0.0,
    }


def load_development_and_legacy_test(
    data_path: str | Path,
    seed: int = DEFAULT_SEED,
    validate_data: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Return seed-42 development data and untouched legacy test split."""
    dataframe = load_raw(data_path, validate=validate_data)
    deduped, dropped = dedupe(dataframe)
    splits = stratified_split(deduped, seed=seed)
    development = pd.concat([splits.train, splits.val], ignore_index=True)
    legacy_test = splits.test.reset_index(drop=True)
    assert_disjoint_case_ids(
        {
            "development": development,
            "legacy_test": legacy_test,
        }
    )
    return development, legacy_test, {"dedup_dropped": int(dropped)}


def make_outer_folds(
    development: pd.DataFrame,
    folds: int = 5,
    seed: int = DEFAULT_SEED,
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    result = []
    for train_index, holdout_index in splitter.split(development, development[TARGET]):
        outer_train = development.iloc[train_index].reset_index(drop=True)
        outer_holdout = development.iloc[holdout_index].reset_index(drop=True)
        assert_disjoint_case_ids(
            {"outer_train": outer_train, "outer_holdout": outer_holdout}
        )
        result.append((outer_train, outer_holdout))
    return result


def make_inner_split(
    outer_train: pd.DataFrame,
    seed: int = DEFAULT_SEED,
    early_stop_frac: float = 0.15,
    calibration_frac: float = 0.15,
) -> InnerSplit:
    if early_stop_frac <= 0 or calibration_frac <= 0:
        raise ValueError("inner holdout fractions must be positive")
    if early_stop_frac + calibration_frac >= 1:
        raise ValueError("inner holdout fractions must leave training data")

    train_plus_early, calibration = train_test_split(
        outer_train,
        test_size=calibration_frac,
        stratify=outer_train[TARGET],
        random_state=seed,
    )
    early_stop_relative = early_stop_frac / (1.0 - calibration_frac)
    train, early_stop = train_test_split(
        train_plus_early,
        test_size=early_stop_relative,
        stratify=train_plus_early[TARGET],
        random_state=seed,
    )
    inner = InnerSplit(
        train=train.reset_index(drop=True),
        early_stop=early_stop.reset_index(drop=True),
        threshold_calibration=calibration.reset_index(drop=True),
    )
    assert_disjoint_case_ids(
        {
            "inner_train": inner.train,
            "early_stop": inner.early_stop,
            "threshold_calibration": inner.threshold_calibration,
        }
    )
    return inner


def assert_disjoint_case_ids(parts: dict[str, pd.DataFrame]) -> None:
    seen: dict[int, str] = {}
    for name, frame in parts.items():
        ids = frame[CASE_ID]
        if ids.isna().any() or not ids.is_unique:
            raise RuntimeError(f"{name} has missing or duplicate case_id values")
        for case_id in ids:
            previous = seen.setdefault(int(case_id), name)
            if previous != name:
                raise RuntimeError(
                    f"case_id {case_id} appears in both {previous} and {name}"
                )


def _scaled_matrices(inner: InnerSplit, outer_holdout: pd.DataFrame):
    scaler = fit_scaler(inner.train)
    scaled_train = apply_scaler(scaler, inner.train)
    scaled_early_stop = apply_scaler(scaler, inner.early_stop)
    scaled_calibration = apply_scaler(scaler, inner.threshold_calibration)
    scaled_holdout = apply_scaler(scaler, outer_holdout)
    return (
        scaled_train[FEATURES],
        scaled_train[TARGET],
        scaled_early_stop[FEATURES],
        scaled_early_stop[TARGET],
        scaled_calibration[FEATURES],
        scaled_calibration[TARGET],
        scaled_holdout[FEATURES],
        scaled_holdout[TARGET],
    )


def _predict_scores(model, X) -> np.ndarray:
    if isinstance(model, tuple):
        member_scores = [_predict_scores(member, X) for member in model]
        ranked = []
        for scores in member_scores:
            order = np.argsort(scores, kind="stable")
            ranks = np.empty_like(order, dtype=float)
            ranks[order] = np.arange(order.size, dtype=float)
            if order.size > 1:
                ranks /= order.size - 1
            ranked.append(ranks)
        return np.mean(ranked, axis=0)
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(X)[:, 1])
    if hasattr(model, "decision_function"):
        raw = np.asarray(model.decision_function(X))
        return 1.0 / (1.0 + np.exp(-raw))
    raise TypeError(f"{type(model).__name__} cannot produce fraud scores")


def _xgb_candidate(seed: int, smoke: bool, cost_sensitive: bool) -> Callable:
    def train(X_train, y_train, X_early_stop, y_early_stop):
        negatives = int((y_train == 0).sum())
        positives = int((y_train == 1).sum())
        n_estimators = 20 if smoke else 300
        early_stopping_rounds = 5 if smoke else 30
        kwargs = {}
        if cost_sensitive:
            kwargs["scale_pos_weight"] = float(negatives / max(1, positives))
        model = XGBClassifier(
            n_estimators=n_estimators,
            max_depth=3 if smoke else 6,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="aucpr",
            tree_method="hist",
            n_jobs=1 if smoke else -1,
            random_state=seed,
            early_stopping_rounds=early_stopping_rounds,
            **kwargs,
        )
        model.fit(X_train, y_train, eval_set=[(X_early_stop, y_early_stop)], verbose=False)
        return model

    return train


def _candidate_trainers(seed: int, smoke: bool) -> dict[str, Callable]:
    n_estimators = 10 if smoke else 300
    hgb_iterations = 20 if smoke else 300

    def balanced_random_forest(X_train, y_train, X_early_stop, y_early_stop):
        del X_early_stop, y_early_stop
        model = BalancedRandomForestClassifier(
            n_estimators=n_estimators,
            random_state=seed,
            n_jobs=1 if smoke else -1,
            replacement=True,
            bootstrap=False,
        )
        return model.fit(X_train, y_train)

    def easy_ensemble(X_train, y_train, X_early_stop, y_early_stop):
        del X_early_stop, y_early_stop
        model = EasyEnsembleClassifier(
            n_estimators=3 if smoke else 10,
            random_state=seed,
            n_jobs=1 if smoke else -1,
        )
        return model.fit(X_train, y_train)

    def hist_gradient_boosting(X_train, y_train, X_early_stop, y_early_stop):
        train_weights = compute_sample_weight("balanced", y_train)
        early_stop_weights = compute_sample_weight("balanced", y_early_stop)
        model = HistGradientBoostingClassifier(
            max_iter=hgb_iterations,
            learning_rate=0.08,
            l2_regularization=0.01,
            early_stopping=True,
            random_state=seed,
        )
        return model.fit(
            X_train,
            y_train,
            sample_weight=train_weights,
            X_val=X_early_stop,
            y_val=y_early_stop,
            sample_weight_val=early_stop_weights,
        )

    def logistic_regression(X_train, y_train, X_early_stop, y_early_stop):
        del X_early_stop, y_early_stop
        model = LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            solver="liblinear",
            random_state=seed,
        )
        return model.fit(X_train, y_train)

    def train_lightgbm(
        X_train,
        y_train,
        X_early_stop,
        y_early_stop,
        *,
        cost_sensitive: bool,
    ):
        try:
            import lightgbm as lgb
        except ImportError as exc:
            raise RuntimeError(
                "lightgbm is optional; run with `uv run --with lightgbm ...`"
            ) from exc

        negatives = int((y_train == 0).sum())
        positives = int((y_train == 1).sum())
        kwargs = {}
        if cost_sensitive:
            kwargs.update(
                scale_pos_weight=float(negatives / max(1, positives)),
                boost_from_average=False,
            )
        model = lgb.LGBMClassifier(
            objective="binary",
            n_estimators=30 if smoke else 500,
            learning_rate=0.08 if smoke else 0.03,
            num_leaves=15,
            max_depth=-1,
            min_child_samples=50,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=2.0,
            random_state=seed,
            n_jobs=1 if smoke else -1,
            verbosity=-1,
            deterministic=True,
            force_col_wise=True,
            **kwargs,
        )
        callbacks = [lgb.early_stopping(5 if smoke else 30, verbose=False)]
        return model.fit(
            X_train,
            y_train,
            eval_X=X_early_stop,
            eval_y=y_early_stop,
            eval_metric="average_precision",
            callbacks=callbacks,
        )

    def lightgbm_unweighted(X_train, y_train, X_early_stop, y_early_stop):
        return train_lightgbm(
            X_train,
            y_train,
            X_early_stop,
            y_early_stop,
            cost_sensitive=False,
        )

    def lightgbm_cost_sensitive(X_train, y_train, X_early_stop, y_early_stop):
        return train_lightgbm(
            X_train,
            y_train,
            X_early_stop,
            y_early_stop,
            cost_sensitive=True,
        )

    def train_catboost(
        X_train,
        y_train,
        X_early_stop,
        y_early_stop,
        *,
        cost_sensitive: bool,
    ):
        try:
            from catboost import CatBoostClassifier
        except ImportError as exc:
            raise RuntimeError(
                "catboost is optional; run with `uv run --with catboost ...`"
            ) from exc

        negatives = int((y_train == 0).sum())
        positives = int((y_train == 1).sum())
        kwargs = {}
        if cost_sensitive:
            kwargs["scale_pos_weight"] = float(negatives / max(1, positives))
        model = CatBoostClassifier(
            iterations=30 if smoke else 500,
            depth=6,
            learning_rate=0.08 if smoke else 0.05,
            loss_function="Logloss",
            eval_metric="PRAUC:type=Classic",
            random_seed=seed,
            thread_count=1 if smoke else -1,
            verbose=False,
            allow_writing_files=False,
            od_type="Iter",
            od_wait=5 if smoke else 30,
            **kwargs,
        )
        return model.fit(
            X_train,
            y_train,
            eval_set=(X_early_stop, y_early_stop),
            verbose=False,
        )

    def catboost_unweighted(X_train, y_train, X_early_stop, y_early_stop):
        return train_catboost(
            X_train,
            y_train,
            X_early_stop,
            y_early_stop,
            cost_sensitive=False,
        )

    def catboost_cost_sensitive(X_train, y_train, X_early_stop, y_early_stop):
        return train_catboost(
            X_train,
            y_train,
            X_early_stop,
            y_early_stop,
            cost_sensitive=True,
        )

    def xgb_catboost_rank_ensemble(X_train, y_train, X_early_stop, y_early_stop):
        xgb = _xgb_candidate(
            seed=seed,
            smoke=smoke,
            cost_sensitive=True,
        )(X_train, y_train, X_early_stop, y_early_stop)
        catboost = catboost_unweighted(
            X_train,
            y_train,
            X_early_stop,
            y_early_stop,
        )
        return (xgb, catboost)

    return {
        "xgb_unweighted": _xgb_candidate(
            seed=seed,
            smoke=smoke,
            cost_sensitive=False,
        ),
        "xgb_cost_sensitive": _xgb_candidate(
            seed=seed,
            smoke=smoke,
            cost_sensitive=True,
        ),
        "lightgbm_unweighted": lightgbm_unweighted,
        "lightgbm_cost_sensitive": lightgbm_cost_sensitive,
        "catboost_unweighted": catboost_unweighted,
        "catboost_cost_sensitive": catboost_cost_sensitive,
        "xgb_catboost_rank_ensemble": xgb_catboost_rank_ensemble,
        "balanced_random_forest": balanced_random_forest,
        "easy_ensemble": easy_ensemble,
        "hist_gradient_boosting_balanced": hist_gradient_boosting,
        "logistic_regression": logistic_regression,
    }


def screen_candidates(
    development: pd.DataFrame,
    candidate_names: tuple[str, ...] = DEFAULT_CANDIDATES,
    folds: int = 5,
    seed: int = DEFAULT_SEED,
    smoke: bool = False,
) -> list[dict]:
    trainers = _candidate_trainers(seed=seed, smoke=smoke)
    unknown = sorted(set(candidate_names) - set(trainers))
    if unknown:
        raise ValueError(f"unknown candidates: {unknown}")

    rows = []
    for fold_index, (outer_train, outer_holdout) in enumerate(
        make_outer_folds(development, folds=folds, seed=seed),
        start=1,
    ):
        inner = make_inner_split(outer_train, seed=seed + fold_index)
        (
            X_train,
            y_train,
            X_early_stop,
            y_early_stop,
            X_calibration,
            y_calibration,
            X_holdout,
            y_holdout,
        ) = _scaled_matrices(inner, outer_holdout)

        for candidate in candidate_names:
            model = trainers[candidate](X_train, y_train, X_early_stop, y_early_stop)
            calibration_scores = _predict_scores(model, X_calibration)
            holdout_scores = _predict_scores(model, X_holdout)
            decisions = select_thresholds(y_calibration, calibration_scores)
            ap = float(average_precision_score(y_holdout, holdout_scores))
            top_100 = evaluate_at_k(y_holdout, holdout_scores, k=100)
            for policy, threshold_decision in decisions.items():
                metrics = evaluate_at_threshold(
                    y_holdout,
                    holdout_scores,
                    threshold_decision.threshold,
                )
                rows.append(
                    {
                        "candidate": candidate,
                        "fold": fold_index,
                        "policy": policy,
                        "outer_average_precision": ap,
                        "outer_precision": metrics["precision"],
                        "outer_recall": metrics["recall"],
                        "outer_f1": metrics["f1"],
                        "outer_f2": metrics["f2"],
                        "outer_tp": metrics["tp"],
                        "outer_fp": metrics["fp"],
                        "outer_fn": metrics["fn"],
                        "outer_tn": metrics["tn"],
                        "outer_top_100_tp": top_100["true_positives"],
                        "outer_precision_at_100": top_100["precision_at_k"],
                        "outer_recall_at_100": top_100["recall_at_k"],
                        "threshold": threshold_decision.threshold,
                        "calibration_precision": threshold_decision.calibration_precision,
                        "calibration_recall": threshold_decision.calibration_recall,
                        "calibration_f1": threshold_decision.calibration_f1,
                        "calibration_f2": threshold_decision.calibration_f2,
                        "inner_train_n": int(len(inner.train)),
                        "early_stop_n": int(len(inner.early_stop)),
                        "threshold_calibration_n": int(
                            len(inner.threshold_calibration)
                        ),
                        "outer_holdout_n": int(len(outer_holdout)),
                    }
                )
    return rows


def summarize(rows: list[dict]) -> list[dict]:
    frame = pd.DataFrame(rows)
    grouped = frame.groupby(["candidate", "policy"], sort=True)
    summary = grouped.agg(
        outer_average_precision_mean=("outer_average_precision", "mean"),
        outer_average_precision_std=("outer_average_precision", "std"),
        outer_precision_mean=("outer_precision", "mean"),
        outer_recall_mean=("outer_recall", "mean"),
        outer_f1_mean=("outer_f1", "mean"),
        outer_f2_mean=("outer_f2", "mean"),
        outer_top_100_tp_mean=("outer_top_100_tp", "mean"),
        outer_precision_at_100_mean=("outer_precision_at_100", "mean"),
        outer_recall_at_100_mean=("outer_recall_at_100", "mean"),
        folds=("fold", "nunique"),
    ).reset_index()
    summary = summary.fillna({"outer_average_precision_std": 0.0})
    return summary.to_dict(orient="records")


def write_outputs(
    rows: list[dict],
    metadata: dict,
    out_root: str | Path = "experiments/model_search",
) -> Path:
    out_root = Path(out_root)
    run_dir = out_root / dt.datetime.now().strftime("%Y-%m-%d_%H%M%S_seed42")
    run_dir.mkdir(parents=True, exist_ok=False)
    summary = summarize(rows)
    payload = {
        "metadata": metadata,
        "fold_results": rows,
        "summary": summary,
    }
    (run_dir / "results.json").write_text(json.dumps(payload, indent=2))

    fieldnames = list(rows[0].keys()) if rows else []
    with (run_dir / "fold_results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary_fields = list(summary[0].keys()) if summary else []
    with (run_dir / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary)
    return run_dir


def _smoke_sample(development: pd.DataFrame, rows: int, seed: int) -> pd.DataFrame:
    if rows >= len(development):
        return development
    positives = development[development[TARGET] == 1]
    negatives = development[development[TARGET] == 0]
    positive_n = min(len(positives), max(8, rows // 20))
    negative_n = rows - positive_n
    sampled = pd.concat(
        [
            positives.sample(n=positive_n, random_state=seed),
            negatives.sample(n=negative_n, random_state=seed),
        ],
        ignore_index=True,
    )
    return sampled.sample(frac=1, random_state=seed).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/raw/creditcard.csv")
    parser.add_argument("--out-root", default="experiments/model_search")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--no-validate-data", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--smoke-rows", type=int, default=1200)
    parser.add_argument(
        "--candidates",
        nargs="+",
        default=list(DEFAULT_CANDIDATES),
        choices=list(DEFAULT_CANDIDATES),
    )
    args = parser.parse_args()

    folds = 2 if args.smoke else args.folds
    development, legacy_test, load_metadata = load_development_and_legacy_test(
        args.data,
        seed=args.seed,
        validate_data=not args.no_validate_data,
    )
    if args.smoke:
        development = _smoke_sample(development, rows=args.smoke_rows, seed=args.seed)

    rows = screen_candidates(
        development,
        candidate_names=tuple(args.candidates),
        folds=folds,
        seed=args.seed,
        smoke=args.smoke,
    )
    metadata = {
        "seed": args.seed,
        "folds": folds,
        "smoke": args.smoke,
        "candidates": args.candidates,
        "development_n": int(len(development)),
        "legacy_test_n": int(len(legacy_test)),
        "legacy_test_used_for_selection": False,
        **load_metadata,
    }
    run_dir = write_outputs(rows, metadata=metadata, out_root=args.out_root)
    print(f"model search written to {run_dir}")
    print(json.dumps(summarize(rows), indent=2))


if __name__ == "__main__":
    main()
