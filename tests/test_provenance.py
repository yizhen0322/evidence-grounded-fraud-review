import json

import pandas as pd
import pytest

from src.data.load import CASE_ID
from src.provenance import (
    assert_source_hashes,
    assert_source_run,
    sha256_file,
    sha256_json,
    source_run_ref,
    validate_run_manifest,
    write_run_manifest,
)


def make_run(tmp_path, name="detector", source_run_dirs=()):
    run_dir = tmp_path / name
    run_dir.mkdir()
    dataset = tmp_path / "dataset.csv"
    if not dataset.exists():
        dataset.write_text("x,y\n1,0\n2,1\n")
    pd.DataFrame(
        {
            CASE_ID: [101, 102],
            "y_true": [0, 1],
            "score": [0.1, 0.9],
            "pred": [0, 1],
        }
    ).to_parquet(run_dir / "predictions.parquet")
    (run_dir / "metrics.json").write_text(json.dumps({"ok": True}))
    (run_dir / "config.yaml").write_text("group: g0\n")
    (run_dir / "split_summary.json").write_text(
        json.dumps({"test": {"n": 2}})
    )
    pd.DataFrame(
        {CASE_ID: [101, 102], "split": ["test", "test"]}
    ).to_parquet(run_dir / "split_assignments.parquet")
    write_run_manifest(
        run_dir=run_dir,
        group="g0" if not source_run_dirs else "g4",
        seed=42,
        dataset_path=dataset if not source_run_dirs else None,
        resolved_config={"group": "g0"} if not source_run_dirs else None,
        split_summary={"test": {"n": 2}} if not source_run_dirs else None,
        threshold=0.5 if not source_run_dirs else None,
        feature_names=["V1", "Amount"] if not source_run_dirs else None,
        source_run_dirs=source_run_dirs,
        source_files=["src/provenance.py"],
        repo_root=".",
    )
    return run_dir


def test_manifest_round_trip_and_exact_source_reference(tmp_path):
    detector = make_run(tmp_path)
    child = make_run(tmp_path, "g4", [detector])

    manifest = validate_run_manifest(child, expected_group="g4")

    assert manifest["threshold"] == 0.5
    assert manifest["feature_names"] == ["V1", "Amount"]
    assert manifest["source_runs"] == [source_run_ref(detector)]
    assert set(manifest["source_runs"][0]) == {
        "run_id",
        "manifest_sha256",
    }
    assert_source_run(manifest, detector)
    assert_source_hashes(manifest, ["src/provenance.py"])


def test_canonical_json_hash_ignores_mapping_order():
    assert sha256_json({"b": 2, "a": 1}) == sha256_json({"a": 1, "b": 2})


def test_changed_artifact_is_rejected(tmp_path):
    run_dir = make_run(tmp_path)
    (run_dir / "metrics.json").write_text("tampered")

    with pytest.raises(ValueError, match="hash mismatch"):
        validate_run_manifest(run_dir)


def test_duplicate_or_missing_case_id_is_rejected(tmp_path):
    run_dir = make_run(tmp_path)
    predictions = pd.read_parquet(run_dir / "predictions.parquet")
    predictions[CASE_ID] = [101, 101]
    predictions.to_parquet(run_dir / "predictions.parquet")

    with pytest.raises(ValueError, match="case_id"):
        validate_run_manifest(run_dir)

    predictions = predictions.drop(columns=[CASE_ID])
    predictions.to_parquet(run_dir / "predictions.parquet")
    with pytest.raises(ValueError, match="case_id"):
        validate_run_manifest(run_dir)


def test_manifest_rejects_config_contract_drift(tmp_path):
    run_dir = make_run(tmp_path)
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["config_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(ValueError, match="config hash mismatch"):
        validate_run_manifest(run_dir)


def test_split_hash_binds_case_assignments_not_summary_fields(tmp_path):
    first = make_run(tmp_path, "first")
    second = make_run(tmp_path, "second")
    first_manifest = validate_run_manifest(first)
    second_manifest = validate_run_manifest(second)

    assert first_manifest["split_sha256"] == second_manifest["split_sha256"]

    second_assignments = pd.read_parquet(second / "split_assignments.parquet")
    second_assignments.loc[0, "split"] = "train"
    second_assignments.to_parquet(second / "split_assignments.parquet")
    with pytest.raises(ValueError, match="hash mismatch|count mismatch"):
        validate_run_manifest(second)


def test_derived_run_binds_its_own_metrics_contract(tmp_path):
    detector = make_run(tmp_path)
    child = make_run(tmp_path, "g4", [detector])
    metrics_path = child / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "val": {"threshold": 0.9},
                "test": {"threshold": 0.9},
                "feature_names": ["V1", "Amount"],
            }
        )
    )
    manifest_path = child / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"]["metrics.json"]["sha256"] = sha256_file(metrics_path)
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(ValueError, match="threshold differs"):
        validate_run_manifest(child)
