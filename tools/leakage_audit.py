"""Leakage and artifact-contract audit for a completed detector run."""

import json
import sys
from pathlib import Path

import pandas as pd

from src.data.load import CASE_ID
from src.provenance import validate_run_manifest


def audit_run(run_dir: str | Path) -> dict[str, bool]:
    directory = Path(run_dir)
    manifest = validate_run_manifest(directory)
    summary = json.loads((directory / "split_summary.json").read_text())
    metrics = json.loads((directory / "metrics.json").read_text())
    predictions = pd.read_parquet(directory / "predictions.parquet")
    assignments = pd.read_parquet(directory / "split_assignments.parquet")
    feature_names = metrics.get("feature_names", [])
    results: dict[str, bool] = {}

    original_ratio = 492 / 284_807
    for partition in ("val", "test"):
        ratio = summary[partition]["fraud_ratio"]
        results[f"{partition} keeps original distribution"] = (
            abs(ratio - original_ratio) < 5e-4
        )
    results["threshold frozen from val to test and manifest"] = (
        metrics["val"]["threshold"]
        == metrics["test"]["threshold"]
        == manifest["threshold"]
    )
    results["predictions cover exactly the test set"] = (
        len(predictions) == summary["test"]["n"]
        and set(predictions[CASE_ID])
        == set(assignments.loc[assignments["split"] == "test", CASE_ID])
    )
    results["case_id present"] = CASE_ID in predictions.columns
    results["case_id non-null and unique"] = (
        CASE_ID in predictions.columns
        and not predictions[CASE_ID].isna().any()
        and predictions[CASE_ID].is_unique
    )
    results["case_id excluded from model features"] = CASE_ID not in feature_names
    results["feature_names match manifest"] = (
        feature_names == manifest["feature_names"]
    )
    results["manifest hashes, split IDs, and row counts validate"] = True
    results["reported run came from clean Git state"] = not manifest["git_dirty"]
    results["config + environment recorded"] = (
        (directory / "config.yaml").exists()
        and (directory / "environment.txt").exists()
    )
    if "train_after_resample" in summary:
        results["SMOTE balanced train only"] = (
            summary["train_after_resample"]["fraud_ratio"] == 0.5
            and abs(summary["val"]["fraud_ratio"] - original_ratio) < 5e-4
            and abs(summary["test"]["fraud_ratio"] - original_ratio) < 5e-4
        )
    return results


def main(run_dir: str) -> int:
    try:
        results = audit_run(run_dir)
    except Exception as error:
        print(f"FAIL: manifest/artifact contract: {error}")
        return 1
    for name, passed in results.items():
        print(f"{'PASS' if passed else 'FAIL'}: {name}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tools/leakage_audit.py RUN_DIR")
    sys.exit(main(sys.argv[1]))
