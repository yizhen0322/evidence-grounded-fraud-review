import json

import pandas as pd
import pytest

from src.data.load import CASE_ID
from src.provenance import (
    source_run_ref,
    validate_run_manifest,
    write_run_manifest,
)
from tools.run_g4_shap import (
    risk_bucket,
    select_flagged,
    validate_reason_records,
)


def fixture_frames():
    predictions = pd.DataFrame(
        {
            CASE_ID: [10, 20, 30],
            "y_true": [0, 1, 0],
            "score": [0.2, 0.9, 0.8],
            "pred": [0, 1, 1],
        }
    )
    features = pd.DataFrame(
        {"V1": [300.0, 100.0, 200.0]},
        index=[30, 10, 20],
    )
    features.index.name = CASE_ID
    return predictions, features


def test_flagged_features_are_joined_by_case_id_not_position():
    predictions, features = fixture_frames()

    flagged, flagged_features = select_flagged(predictions, features)

    assert list(flagged.index) == [20, 30]
    assert list(flagged_features.index) == [20, 30]
    assert list(flagged_features["V1"]) == [200.0, 300.0]


@pytest.mark.parametrize("mutation", ["duplicate", "missing"])
def test_duplicate_or_missing_ids_are_rejected(mutation):
    predictions, features = fixture_frames()
    if mutation == "duplicate":
        predictions.loc[2, CASE_ID] = 20
    else:
        features = features.drop(index=30)

    with pytest.raises(ValueError, match="case_id"):
        select_flagged(predictions, features)


def test_g4_records_must_preserve_detector_score_and_label():
    predictions, _ = fixture_frames()
    records = [
        {CASE_ID: 20, "score": 0.9, "y_true": 1, "codes": []},
        {CASE_ID: 30, "score": 0.8, "y_true": 0, "codes": []},
    ]
    validate_reason_records(records, predictions)

    records[0]["score"] = 0.91
    with pytest.raises(ValueError, match="score"):
        validate_reason_records(records, predictions)
    records[0]["score"], records[0]["y_true"] = 0.9, 0
    with pytest.raises(ValueError, match="label"):
        validate_reason_records(records, predictions)


def test_risk_bucket_boundaries():
    assert risk_bucket(0.9) == "High"
    assert risk_bucket(0.5) == "Medium"
    assert risk_bucket(0.499) == "Low"


def test_g4_manifest_has_exact_detector_reference(tmp_path):
    dataset = tmp_path / "data.csv"
    dataset.write_text("x,y\n1,0\n2,1\n")
    detector = tmp_path / "detector"
    detector.mkdir()
    pd.DataFrame(
        {
            CASE_ID: [1, 2],
            "y_true": [0, 1],
            "score": [0.1, 0.9],
            "pred": [0, 1],
        }
    ).to_parquet(detector / "predictions.parquet")
    pd.DataFrame(
        {CASE_ID: [1, 2], "split": ["test", "test"]}
    ).to_parquet(detector / "split_assignments.parquet")
    metrics = {
        "val": {"threshold": 0.5},
        "test": {"threshold": 0.5},
        "feature_names": ["V1", "recon_error"],
    }
    summary = {"test": {"n": 2}}
    (detector / "metrics.json").write_text(json.dumps(metrics))
    (detector / "config.yaml").write_text("group: g3\n")
    (detector / "split_summary.json").write_text(json.dumps(summary))
    write_run_manifest(
        run_dir=detector,
        group="g3",
        seed=44,
        dataset_path=dataset,
        resolved_config={"group": "g3"},
        split_summary=summary,
        threshold=0.5,
        feature_names=["V1", "recon_error"],
        source_files=[],
    )

    g4 = tmp_path / "g4"
    g4.mkdir()
    (g4 / "reason_codes.jsonl").write_text(
        json.dumps(
            {
                CASE_ID: 2,
                "score": 0.9,
                "y_true": 1,
                "codes": [],
            }
        )
        + "\n"
    )
    write_run_manifest(
        run_dir=g4,
        group="g4",
        seed=44,
        source_run_dirs=[detector],
        source_files=[],
    )

    manifest = validate_run_manifest(g4, expected_group="g4")
    assert manifest["source_runs"] == [source_run_ref(detector)]
    assert manifest["seed"] == 44
    assert manifest["feature_names"] == ["V1", "recon_error"]
