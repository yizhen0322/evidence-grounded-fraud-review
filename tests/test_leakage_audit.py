import json

import pandas as pd
import pytest

from src.data.load import CASE_ID
from src.provenance import sha256_file, write_run_manifest
from tools.leakage_audit import audit_run, main


def make_valid_run(tmp_path):
    run_dir = tmp_path / "g0_seed42"
    run_dir.mkdir()
    dataset = tmp_path / "data.csv"
    dataset.write_text("x,y\n1,0\n2,1\n")
    ratio = 492 / 284_807
    summary = {
        "train": {"n": 10, "fraud_ratio": ratio},
        "val": {"n": 2, "fraud_ratio": ratio},
        "test": {"n": 2, "fraud_ratio": ratio},
    }
    metrics = {
        "val": {"threshold": 0.5},
        "test": {"threshold": 0.5},
        "feature_names": ["V1", "Amount"],
    }
    pd.DataFrame(
        {
            CASE_ID: [12, 13],
            "y_true": [0, 1],
            "score": [0.1, 0.9],
            "pred": [0, 1],
        }
    ).to_parquet(run_dir / "predictions.parquet")
    pd.DataFrame(
        {
            CASE_ID: list(range(14)),
            "split": ["train"] * 10 + ["val"] * 2 + ["test"] * 2,
        }
    ).to_parquet(run_dir / "split_assignments.parquet")
    (run_dir / "split_summary.json").write_text(json.dumps(summary))
    (run_dir / "metrics.json").write_text(json.dumps(metrics))
    (run_dir / "config.yaml").write_text("group: g0\n")
    (run_dir / "environment.txt").write_text("python=test\n")
    write_run_manifest(
        run_dir=run_dir,
        group="g0",
        seed=42,
        dataset_path=dataset,
        resolved_config={"group": "g0"},
        split_summary=summary,
        threshold=0.5,
        feature_names=metrics["feature_names"],
        source_files=["tools/leakage_audit.py"],
    )
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["git_dirty"] = False
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return run_dir


def test_audit_checks_case_id_features_threshold_and_manifest(tmp_path):
    run_dir = make_valid_run(tmp_path)

    results = audit_run(run_dir)

    assert results
    assert all(results.values())


def test_duplicate_case_id_is_rejected_even_if_hash_is_resealed(tmp_path):
    run_dir = make_valid_run(tmp_path)
    predictions = pd.read_parquet(run_dir / "predictions.parquet")
    predictions[CASE_ID] = [12, 12]
    predictions.to_parquet(run_dir / "predictions.parquet")
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"]["predictions.parquet"]["sha256"] = sha256_file(
        run_dir / "predictions.parquet"
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )

    with pytest.raises(ValueError, match="case_id"):
        audit_run(run_dir)


def test_tampered_artifact_makes_cli_fail(tmp_path):
    run_dir = make_valid_run(tmp_path)
    (run_dir / "metrics.json").write_text("tampered")

    assert main(str(run_dir)) == 1
