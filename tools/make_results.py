"""Build detector tables and PR curves from an explicit exact-run allowlist."""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import precision_recall_curve

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.metrics import evaluate
from src.provenance import sha256_file, source_run_ref, validate_run_manifest

EXPECTED_GROUPS = {"g0", "g1", "g2", "g3", "g6", "g7"}
EXPECTED_SEEDS = {42, 43, 44, 45, 46}
TEST_METRICS = {
    "auc_pr",
    "roc_auc",
    "precision",
    "recall",
    "f1",
    "tp",
    "tn",
    "fp",
    "fn",
    "precision_at_100",
    "recall_at_100",
    "threshold",
}


def _metric_equal(recorded: float | int, recomputed: float | int) -> bool:
    if isinstance(recomputed, (int, np.integer)):
        return int(recorded) == int(recomputed)
    return bool(np.isclose(float(recorded), float(recomputed), rtol=1e-12, atol=1e-12))


def _validate_test_metrics(
    run_dir: Path,
    metrics: dict,
    threshold: float,
) -> None:
    predictions = pd.read_parquet(run_dir / "predictions.parquet")
    expected_pred = (predictions["score"].to_numpy() >= threshold).astype(int)
    if not np.array_equal(predictions["pred"].to_numpy(), expected_pred):
        raise ValueError(f"saved predictions disagree with threshold: {run_dir}")
    recomputed = evaluate(predictions["y_true"], predictions["score"], threshold)
    for key in TEST_METRICS:
        if not _metric_equal(metrics["test"][key], recomputed[key]):
            raise ValueError(f"test metric mismatch for {key}: {run_dir}")


def collect_selected(
    config_path: str | Path,
    expected_groups: set[str] = EXPECTED_GROUPS,
    expected_seeds: set[int] = EXPECTED_SEEDS,
) -> tuple[list[dict], list[tuple[Path, dict]]]:
    config = yaml.safe_load(Path(config_path).read_text()) or {}
    if config.get("schema_version") != 1:
        raise ValueError("results config requires schema_version 1")
    entries = config.get("runs")
    if not isinstance(entries, list):
        raise ValueError("results config requires a runs list")
    expected = {
        (group, seed) for group in expected_groups for seed in expected_seeds
    }
    seen: set[tuple[str, int]] = set()
    declared_entries: list[tuple[dict, tuple[str, int]]] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"group", "seed", "path"}:
            raise ValueError("each results entry requires only group, seed, and path")
        declared = (str(entry["group"]), int(entry["seed"]))
        if declared in seen:
            raise ValueError(f"duplicate group/seed entry: {declared}")
        seen.add(declared)
        declared_entries.append((entry, declared))
    if seen != expected:
        raise ValueError(
            f"allowlist coverage mismatch; missing={sorted(expected - seen)}, "
            f"unexpected={sorted(seen - expected)}"
        )

    rows: list[dict] = []
    selected: list[tuple[Path, dict]] = []
    for entry, declared in declared_entries:
        run_dir = Path(entry["path"])
        lowered = run_dir.as_posix().lower()
        if any(token in lowered for token in ("tuning_runs", "superseded", "quick")):
            raise ValueError(f"tuning/quick/superseded path is not reportable: {run_dir}")
        manifest = validate_run_manifest(run_dir, expected_group=declared[0])
        actual = (manifest["group"], int(manifest["seed"]))
        if actual != declared:
            raise ValueError(f"declared group/seed {declared} != manifest {actual}")
        if manifest["git_dirty"]:
            raise ValueError(f"dirty run is not reportable: {run_dir}")
        metrics = json.loads((run_dir / "metrics.json").read_text())
        missing_test = TEST_METRICS - set(metrics.get("test", {}))
        missing_val = {"auc_pr", "threshold"} - set(metrics.get("val", {}))
        if missing_test or missing_val:
            raise ValueError(
                f"missing required metrics: val={sorted(missing_val)}, "
                f"test={sorted(missing_test)}"
            )
        threshold = float(manifest["threshold"])
        if not (
            float(metrics["val"]["threshold"])
            == float(metrics["test"]["threshold"])
            == threshold
        ):
            raise ValueError("threshold provenance mismatch between val/test/manifest")
        if metrics.get("feature_names") != manifest["feature_names"]:
            raise ValueError("metrics feature_names differ from manifest")
        runtime = metrics.get("runtime", {})
        if {"train_seconds", "test_inference_seconds"} - set(runtime):
            raise ValueError("missing required runtime metric")
        _validate_test_metrics(run_dir, metrics, threshold)
        test = metrics["test"]
        rows.append(
            {
                "group": actual[0],
                "seed": actual[1],
                "val_auc_pr": metrics["val"]["auc_pr"],
                **{
                    f"test_{key}": test[key]
                    for key in sorted(TEST_METRICS - {"threshold"})
                },
                "threshold": threshold,
                "train_seconds": runtime["train_seconds"],
                "test_inference_seconds": runtime["test_inference_seconds"],
                "run_id": manifest["run_id"],
                "manifest_sha256": sha256_file(run_dir / "run_manifest.json"),
            }
        )
        selected.append((run_dir, manifest))
    return rows, selected


def validate_results_manifest(
    path: str | Path = "reports/results_manifest.json",
    expected_groups: set[str] = EXPECTED_GROUPS,
    expected_seeds: set[int] = EXPECTED_SEEDS,
) -> dict:
    manifest_path = Path(path)
    manifest = json.loads(manifest_path.read_text())
    required = {
        "schema_version",
        "generated_at",
        "config_path",
        "config_sha256",
        "inputs",
        "source_code_sha256",
        "outputs",
    }
    if manifest.get("schema_version") != 1 or required - set(manifest):
        raise ValueError("invalid results manifest schema")
    config_path = Path(manifest["config_path"])
    if sha256_file(config_path) != manifest["config_sha256"]:
        raise ValueError("results config hash mismatch")
    _rows, selected = collect_selected(
        config_path,
        expected_groups=expected_groups,
        expected_seeds=expected_seeds,
    )
    expected_inputs = [source_run_ref(run_dir) for run_dir, _ in selected]
    if manifest["inputs"] != expected_inputs:
        raise ValueError("results input references differ from the allowlist")
    for source, recorded_hash in manifest["source_code_sha256"].items():
        if not Path(source).exists() or sha256_file(source) != recorded_hash:
            raise ValueError(f"results source hash mismatch: {source}")
    for raw_path, recorded in manifest["outputs"].items():
        output = Path(raw_path)
        if not output.exists():
            raise ValueError(f"missing results output: {output}")
        if sha256_file(output) != recorded["sha256"]:
            raise ValueError(f"results output hash mismatch: {output}")
        if "rows" in recorded and len(pd.read_csv(output)) != recorded["rows"]:
            raise ValueError(f"results output row mismatch: {output}")
    return manifest


def make_results(config_path: str | Path) -> Path:
    config_path = Path(config_path)
    rows, selected = collect_selected(config_path)
    tables = Path("reports/tables")
    figures = Path("reports/figures")
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    main_path = tables / "results_main.csv"
    summary_path = tables / "results_summary.csv"
    figure_path = figures / "pr_curves.png"

    main = pd.DataFrame(rows).sort_values(["group", "seed"])
    main.to_csv(main_path, index=False)
    numeric = [
        column
        for column in main.select_dtypes("number").columns
        if column != "seed"
    ]
    summary = main.groupby("group")[numeric].agg(["mean", "std"])
    summary.columns = [f"{metric}_{stat}" for metric, stat in summary.columns]
    summary.reset_index().to_csv(summary_path, index=False)

    plt.figure(figsize=(8, 6))
    for run_dir, run_manifest in selected:
        if int(run_manifest["seed"]) != 42:
            continue
        predictions = pd.read_parquet(run_dir / "predictions.parquet")
        precision, recall, _ = precision_recall_curve(
            predictions["y_true"],
            predictions["score"],
        )
        plt.plot(recall, precision, label=run_manifest["group"].upper())
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Recorded test precision-recall curves (seed 42)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figure_path, dpi=200)
    plt.close()

    outputs = {
        main_path.as_posix(): {
            "sha256": sha256_file(main_path),
            "rows": len(main),
        },
        summary_path.as_posix(): {
            "sha256": sha256_file(summary_path),
            "rows": len(summary),
        },
        figure_path.as_posix(): {"sha256": sha256_file(figure_path)},
    }
    results_manifest = {
        "schema_version": 1,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "config_path": config_path.as_posix(),
        "config_sha256": sha256_file(config_path),
        "inputs": [source_run_ref(run_dir) for run_dir, _ in selected],
        "source_code_sha256": {
            "src/evaluation/metrics.py": sha256_file("src/evaluation/metrics.py"),
            "src/provenance.py": sha256_file("src/provenance.py"),
            "tools/make_results.py": sha256_file("tools/make_results.py"),
        },
        "outputs": outputs,
    }
    result_path = Path("reports/results_manifest.json")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(results_manifest, indent=2, sort_keys=True) + "\n"
    )
    validate_results_manifest(result_path)
    return result_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    arguments = parser.parse_args()
    print(make_results(arguments.config))


if __name__ == "__main__":
    main()
