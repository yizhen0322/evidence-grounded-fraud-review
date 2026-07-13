import json

import pandas as pd
import pytest
import yaml

from src.data.load import CASE_ID
from src.evaluation.metrics import evaluate
from src.provenance import sha256_file, source_run_ref, write_run_manifest
from tools.make_results import collect_selected, validate_results_manifest


def make_detector_run(
    tmp_path,
    group="g0",
    seed=42,
    threshold=0.5,
    metric_threshold=None,
    omit_metric=None,
    corrupt_metric=None,
):
    run = tmp_path / f"{group}_seed{seed}"
    run.mkdir(parents=True)
    dataset = tmp_path / "dataset.csv"
    if not dataset.exists():
        dataset.write_text("x,y\n0,0\n1,0\n2,0\n3,1\n")
    assignments = pd.DataFrame(
        {CASE_ID: [0, 1, 2, 3], "split": ["train", "val", "test", "test"]}
    )
    assignments.to_parquet(run / "split_assignments.parquet", index=False)
    predictions = pd.DataFrame(
        {
            CASE_ID: [2, 3],
            "y_true": [0, 1],
            "score": [0.1, 0.9],
            "pred": [0, 1],
        }
    )
    predictions.to_parquet(run / "predictions.parquet", index=False)
    section = evaluate(predictions["y_true"], predictions["score"], threshold)
    metrics = {
        "val": dict(section),
        "test": dict(section),
        "runtime": {"train_seconds": 1.2, "test_inference_seconds": 0.1},
        "feature_names": ["V1"],
    }
    (run / "metrics.json").write_text(json.dumps(metrics))
    resolved_config = {"group": group, "seed": seed}
    (run / "config.yaml").write_text(yaml.safe_dump(resolved_config))
    split_summary = {
        "train": {"n": 1},
        "val": {"n": 1},
        "test": {"n": 2},
    }
    (run / "split_summary.json").write_text(json.dumps(split_summary))
    write_run_manifest(
        run_dir=run,
        group=group,
        seed=seed,
        dataset_path=dataset,
        resolved_config=resolved_config,
        split_summary=split_summary,
        threshold=threshold,
        feature_names=["V1"],
        source_files=[],
    )
    manifest_path = run / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if metric_threshold is not None:
        metrics["val"]["threshold"] = metric_threshold
        metrics["test"]["threshold"] = metric_threshold
    if omit_metric:
        metrics["test"].pop(omit_metric)
    if corrupt_metric:
        metrics["test"][corrupt_metric] += 0.1
    (run / "metrics.json").write_text(json.dumps(metrics))
    manifest["artifacts"]["metrics.json"]["sha256"] = sha256_file(
        run / "metrics.json"
    )
    manifest["git_dirty"] = False
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return run


def write_config(tmp_path, entries):
    path = tmp_path / "results.yaml"
    path.write_text(
        yaml.safe_dump(
            {"schema_version": 1, "runs": entries},
            sort_keys=False,
        )
    )
    return path


def test_valid_allowlist_uses_manifest_identity_and_recomputed_metrics(tmp_path):
    run = make_detector_run(tmp_path)
    config = write_config(
        tmp_path,
        [{"group": "g0", "seed": 42, "path": str(run)}],
    )
    rows, selected = collect_selected(
        config,
        expected_groups={"g0"},
        expected_seeds={42},
    )
    assert rows[0]["run_id"] == run.name
    assert rows[0]["threshold"] == 0.5
    assert len(selected) == 1


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        (
            [
                {"group": "g0", "seed": 42, "path": "same"},
                {"group": "g0", "seed": 42, "path": "same"},
            ],
            "duplicate",
        ),
        ([], "coverage"),
    ],
)
def test_duplicate_and_missing_pairs_are_rejected(tmp_path, entries, message):
    config = write_config(tmp_path, entries)
    with pytest.raises(ValueError, match=message):
        collect_selected(
            config,
            expected_groups={"g0"},
            expected_seeds={42},
        )


def test_tuning_paths_are_rejected(tmp_path):
    run = make_detector_run(tmp_path)
    tuning = tmp_path / "tuning_runs" / run.name
    tuning.parent.mkdir()
    run.rename(tuning)
    config = write_config(
        tmp_path,
        [{"group": "g0", "seed": 42, "path": str(tuning)}],
    )
    with pytest.raises(ValueError, match="tuning"):
        collect_selected(
            config,
            expected_groups={"g0"},
            expected_seeds={42},
        )


def test_wrong_threshold_missing_metric_and_metric_tampering_are_rejected(tmp_path):
    wrong = make_detector_run(tmp_path / "wrong", metric_threshold=0.6)
    config = write_config(
        tmp_path / "wrong",
        [{"group": "g0", "seed": 42, "path": str(wrong)}],
    )
    with pytest.raises(ValueError, match="threshold"):
        collect_selected(config, expected_groups={"g0"}, expected_seeds={42})

    missing = make_detector_run(tmp_path / "missing", omit_metric="recall_at_100")
    config = write_config(
        tmp_path / "missing",
        [{"group": "g0", "seed": 42, "path": str(missing)}],
    )
    with pytest.raises(ValueError, match="missing required metrics"):
        collect_selected(config, expected_groups={"g0"}, expected_seeds={42})

    corrupt = make_detector_run(tmp_path / "corrupt", corrupt_metric="auc_pr")
    config = write_config(
        tmp_path / "corrupt",
        [{"group": "g0", "seed": 42, "path": str(corrupt)}],
    )
    with pytest.raises(ValueError, match="metric mismatch"):
        collect_selected(config, expected_groups={"g0"}, expected_seeds={42})


def test_results_manifest_rejects_changed_output(tmp_path):
    run = make_detector_run(tmp_path / "source")
    config = write_config(
        tmp_path,
        [{"group": "g0", "seed": 42, "path": str(run)}],
    )
    output = tmp_path / "results_main.csv"
    output.write_text("group,seed\ng0,42\n")
    manifest_path = tmp_path / "results_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-07-14T00:00:00+00:00",
                "config_path": str(config),
                "config_sha256": sha256_file(config),
                "inputs": [source_run_ref(run)],
                "source_code_sha256": {},
                "outputs": {
                    str(output): {"sha256": sha256_file(output), "rows": 1}
                },
            }
        )
    )
    validate_results_manifest(
        manifest_path,
        expected_groups={"g0"},
        expected_seeds={42},
    )
    output.write_text("group,seed\ng0,43\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_results_manifest(
            manifest_path,
            expected_groups={"g0"},
            expected_seeds={42},
        )
