import json

import numpy as np
import pandas as pd
import pytest

from src.data.load import CASE_ID, FEATURES, TARGET
from src.provenance import validate_run_manifest
from src.run_experiment import run


def make_synthetic_csv(tmp_path, n=3000, fraud_rate=0.05, seed=0):
    rng = np.random.default_rng(seed)
    labels = (rng.random(n) < fraud_rate).astype(int)
    features = rng.normal(size=(n, 30))
    features[:, 5] += labels * 3.0
    dataframe = pd.DataFrame(features, columns=FEATURES)
    dataframe[TARGET] = labels
    path = tmp_path / "synth.csv"
    dataframe.to_csv(path, index=False)
    return path


def test_runner_end_to_end_baseline(tmp_path):
    config = {
        "group": "g0",
        "features": "original",
        "imbalance": "none",
        "dedup": True,
        "seed": 42,
        "xgb_params": {"n_estimators": 30},
    }

    run_dir = run(
        config,
        data_path=make_synthetic_csv(tmp_path),
        out_root=tmp_path / "runs",
        validate_data=False,
        require_clean=False,
    )

    metrics = json.loads((run_dir / "metrics.json").read_text())
    assert set(metrics) >= {"val", "test", "runtime"}
    assert 0.0 <= metrics["test"]["auc_pr"] <= 1.0
    predictions = pd.read_parquet(run_dir / "predictions.parquet")
    assert list(predictions.columns) == [CASE_ID, "y_true", "score", "pred"]
    assert predictions[CASE_ID].is_unique
    manifest = validate_run_manifest(run_dir, expected_group="g0")
    assert manifest["schema_version"] == 1
    assert manifest["artifacts"]["predictions.parquet"]["rows"] == len(
        predictions
    )
    assert manifest["threshold"] == metrics["val"]["threshold"]
    assignments = pd.read_parquet(run_dir / "split_assignments.parquet")
    assert assignments[CASE_ID].is_unique
    assert set(assignments["split"]) == {"train", "val", "test"}
    assert (run_dir / "split_summary.json").exists()
    assert (run_dir / "model" / "xgb.json").exists()


def test_runner_smote_changes_only_train(tmp_path):
    config = {
        "group": "g1",
        "features": "original",
        "imbalance": "smote",
        "dedup": True,
        "seed": 42,
        "xgb_params": {"n_estimators": 30},
    }

    run_dir = run(
        config,
        data_path=make_synthetic_csv(tmp_path),
        out_root=tmp_path / "runs",
        validate_data=False,
        require_clean=False,
    )

    summary = json.loads((run_dir / "split_summary.json").read_text())
    assert summary["val"]["fraud_ratio"] < 0.10
    assert summary["test"]["fraud_ratio"] < 0.10
    assert summary["train_after_resample"]["fraud_ratio"] == 0.5


def test_runner_rejects_unknown_pipeline_modes(tmp_path):
    config = {
        "group": "bad",
        "features": "original",
        "imbalance": "test_smote",
    }

    with pytest.raises(ValueError, match="unsupported imbalance mode"):
        run(
            config,
            data_path=make_synthetic_csv(tmp_path),
            out_root=tmp_path / "runs",
            validate_data=False,
            require_clean=False,
        )


def test_clean_run_requirement_is_independent_of_data_validation(
    tmp_path,
    monkeypatch,
):
    config = {
        "group": "g0",
        "features": "original",
        "imbalance": "none",
    }

    def reject_dirty_repo():
        raise ValueError("committed clean Git worktree")

    monkeypatch.setattr(
        "src.run_experiment.assert_clean_repository",
        reject_dirty_repo,
    )
    with pytest.raises(ValueError, match="committed clean Git worktree"):
        run(
            config,
            data_path=make_synthetic_csv(tmp_path),
            out_root=tmp_path / "runs",
            validate_data=False,
            require_clean=True,
        )


def test_runner_hybrid_reconstruction_error(tmp_path):
    config = {
        "group": "g2",
        "features": "recon_error",
        "imbalance": "none",
        "dedup": True,
        "seed": 42,
        "xgb_params": {"n_estimators": 20},
        "ae_params": {
            "build": {"hidden": [8], "bottleneck": 3},
            "fit": {"epochs": 3, "batch_size": 64},
        },
    }

    run_dir = run(
        config,
        data_path=make_synthetic_csv(tmp_path),
        out_root=tmp_path / "runs",
        validate_data=False,
        require_clean=False,
    )

    metrics = json.loads((run_dir / "metrics.json").read_text())
    manifest = validate_run_manifest(run_dir, expected_group="g2")
    assert metrics["feature_names"][-1] == "recon_error"
    assert manifest["feature_names"] == metrics["feature_names"]
    assert (run_dir / "model" / "ae.keras").exists()


def test_validation_only_run_does_not_score_or_write_test_predictions(tmp_path):
    config = {
        "group": "g0_tune00",
        "features": "original",
        "imbalance": "none",
        "dedup": True,
        "seed": 42,
        "xgb_params": {"n_estimators": 20},
    }

    run_dir = run(
        config,
        data_path=make_synthetic_csv(tmp_path),
        out_root=tmp_path / "tuning_runs",
        validate_data=False,
        require_clean=False,
        evaluate_test=False,
    )

    metrics = json.loads((run_dir / "metrics.json").read_text())
    manifest = validate_run_manifest(run_dir)
    assert "val" in metrics
    assert "test" not in metrics
    assert metrics["runtime"]["test_inference_seconds"] is None
    assert not (run_dir / "predictions.parquet").exists()
    assert "predictions.parquet" not in manifest["artifacts"]
