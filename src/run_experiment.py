"""Config-driven, provenance-backed detector experiment runner.

Pipeline order: load -> deduplicate -> split -> train-fitted scaling -> optional
AE augmentation -> train-only imbalance handling -> XGBoost -> validation
threshold selection -> one test evaluation -> immutable run artifacts.
"""

import argparse
import datetime
import json
import platform
import subprocess
import time
from pathlib import Path

import pandas as pd
import yaml

from src.data.load import CASE_ID, FEATURES, TARGET, dedupe, load_raw
from src.data.preprocess import apply_scaler, fit_scaler
from src.data.resample import smote_train
from src.data.split import split_summary, stratified_split
from src.evaluation.metrics import evaluate
from src.evaluation.threshold import select_threshold_max_f1
from src.models.xgb import fraud_scores, train_xgboost
from src.provenance import write_run_manifest


def _validate_config(config: dict) -> None:
    required = {"group", "features", "imbalance"}
    missing = required - set(config)
    if missing:
        raise ValueError(f"config missing keys: {sorted(missing)}")
    if config["features"] not in {"original", "recon_error", "latent"}:
        raise ValueError(f"unsupported feature mode: {config['features']}")
    if config["imbalance"] not in {"none", "smote", "scale_pos_weight"}:
        raise ValueError(f"unsupported imbalance mode: {config['imbalance']}")


def _augment(config, scaled, seed, run_dir):
    """Return train/validation/test model matrices and ordered feature names."""
    matrices = {
        name: scaled[name][FEATURES].copy()
        for name in ("train", "val", "test")
    }
    feature_names = list(FEATURES)
    if config["features"] in {"recon_error", "latent"}:
        from src.models.autoencoder import (
            build_autoencoder,
            latent_features,
            reconstruction_error,
            train_autoencoder,
        )

        ae_config = config.get("ae_params", {})
        train_legitimate = matrices["train"][
            scaled["train"][TARGET].to_numpy() == 0
        ].to_numpy()
        autoencoder = build_autoencoder(
            input_dim=len(FEATURES),
            seed=seed,
            **ae_config.get("build", {}),
        )
        autoencoder = train_autoencoder(
            autoencoder,
            train_legitimate,
            seed=seed,
            **ae_config.get("fit", {}),
        )
        autoencoder.save(run_dir / "model" / "ae.keras")

        if config["features"] == "recon_error":
            for name, matrix in matrices.items():
                matrix["recon_error"] = reconstruction_error(
                    autoencoder,
                    matrix.to_numpy(),
                )
            feature_names.append("recon_error")
        else:
            latent_width = None
            for name, matrix in matrices.items():
                latent = latent_features(
                    autoencoder,
                    matrix[FEATURES].to_numpy(),
                )
                latent_width = latent.shape[1]
                for index in range(latent_width):
                    matrix[f"latent_{index}"] = latent[:, index]
            feature_names.extend(
                f"latent_{index}" for index in range(latent_width or 0)
            )

    return (
        matrices["train"],
        matrices["val"],
        matrices["test"],
        feature_names,
    )


def _json_safe_parameters(parameters: dict) -> dict:
    result = {}
    for key, value in parameters.items():
        if hasattr(value, "item"):
            value = value.item()
        result[key] = value
    return result


def run(
    config: dict,
    data_path,
    out_root="experiments/runs",
    validate_data=True,
) -> Path:
    """Execute one experiment and return its immutable run directory."""
    _validate_config(config)
    seed = int(config.get("seed", 42))
    stamp = datetime.date.today().isoformat()
    run_dir = Path(out_root) / f"{stamp}_{config['group']}_seed{seed}"
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "model").mkdir()

    started = time.time()
    dataframe = load_raw(data_path, validate=validate_data)
    dropped = 0
    if config.get("dedup", True):
        dataframe, dropped = dedupe(dataframe)

    splits = stratified_split(dataframe, seed=seed)
    summary = split_summary(splits)
    summary["dedup_dropped"] = dropped

    scaler = fit_scaler(splits.train)
    scaled = {
        "train": apply_scaler(scaler, splits.train),
        "val": apply_scaler(scaler, splits.val),
        "test": apply_scaler(scaler, splits.test),
    }
    labels = {name: frame[TARGET] for name, frame in scaled.items()}

    X_train, X_val, X_test, feature_names = _augment(
        config,
        scaled,
        seed,
        run_dir,
    )

    xgb_parameters = dict(config.get("xgb_params") or {})
    if config["imbalance"] == "smote":
        X_train, y_train = smote_train(
            X_train,
            labels["train"],
            seed=seed,
        )
        summary["train_after_resample"] = {
            "n": int(len(y_train)),
            "frauds": int(y_train.sum()),
            "fraud_ratio": float(y_train.mean()),
        }
    else:
        y_train = labels["train"]
        if config["imbalance"] == "scale_pos_weight":
            negatives = int((y_train == 0).sum())
            positives = int((y_train == 1).sum())
            xgb_parameters.setdefault(
                "scale_pos_weight",
                float(negatives / max(1, positives)),
            )

    training_started = time.time()
    model = train_xgboost(
        X_train,
        y_train,
        X_val,
        labels["val"],
        params=xgb_parameters,
        seed=seed,
    )
    training_seconds = time.time() - training_started

    validation_scores = fraud_scores(model, X_val)
    threshold = select_threshold_max_f1(labels["val"], validation_scores)
    inference_started = time.time()
    test_scores = fraud_scores(model, X_test)
    inference_seconds = time.time() - inference_started

    metrics = {
        "val": evaluate(labels["val"], validation_scores, threshold),
        "test": evaluate(labels["test"], test_scores, threshold),
        "runtime": {
            "train_seconds": training_seconds,
            "test_inference_seconds": inference_seconds,
            "total_seconds": time.time() - started,
        },
        "feature_names": feature_names,
        "resolved_xgb_params": _json_safe_parameters(xgb_parameters),
    }

    predictions = pd.DataFrame(
        {
            CASE_ID: scaled["test"][CASE_ID].to_numpy(),
            "y_true": labels["test"].to_numpy(),
            "score": test_scores,
            "pred": (test_scores >= threshold).astype(int),
        }
    )
    if predictions[CASE_ID].isna().any() or not predictions[CASE_ID].is_unique:
        raise RuntimeError("test prediction case_id contract violated")
    predictions.to_parquet(run_dir / "predictions.parquet")
    model.save_model(run_dir / "model" / "xgb.json")
    (run_dir / "config.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False)
    )
    (run_dir / "split_summary.json").write_text(
        json.dumps(summary, indent=2)
    )
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    freeze = subprocess.run(
        ["uv", "pip", "list", "--format", "freeze"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    (run_dir / "environment.txt").write_text(
        f"python={platform.python_version()}\n"
        f"platform={platform.platform()}\n"
        f"{freeze}"
    )

    source_files = [
        "src/run_experiment.py",
        "src/data/load.py",
        "src/data/split.py",
        "src/data/preprocess.py",
        "src/data/resample.py",
        "src/evaluation/metrics.py",
        "src/evaluation/threshold.py",
        "src/models/xgb.py",
        "src/provenance.py",
    ]
    if config["features"] != "original":
        source_files.append("src/models/autoencoder.py")
    write_run_manifest(
        run_dir=run_dir,
        group=config["group"],
        seed=seed,
        dataset_path=Path(data_path),
        resolved_config=config,
        split_summary=summary,
        threshold=threshold,
        feature_names=feature_names,
        source_run_dirs=[],
        source_files=source_files,
        require_clean=validate_data,
    )
    return run_dir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--data", default="data/raw/creditcard.csv")
    arguments = parser.parse_args()
    config = yaml.safe_load(Path(arguments.config).read_text())
    if arguments.seed is not None:
        config["seed"] = arguments.seed
    run_dir = run(config, data_path=arguments.data)
    print(f"run written to {run_dir}")
    test_metrics = json.loads((run_dir / "metrics.json").read_text())["test"]
    print(json.dumps(test_metrics, indent=2))


if __name__ == "__main__":
    main()
