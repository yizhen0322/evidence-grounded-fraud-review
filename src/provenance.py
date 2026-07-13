"""Fail-closed provenance manifests shared by every pipeline stage."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml

SCHEMA_VERSION = 1
CASE_ID = "case_id"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _row_count(path: Path) -> int | None:
    if path.suffix == ".parquet":
        return int(len(pd.read_parquet(path)))
    if path.suffix == ".jsonl":
        return sum(bool(line.strip()) for line in path.read_text().splitlines())
    if path.suffix == ".csv":
        with path.open(newline="") as handle:
            return max(0, sum(1 for _ in csv.reader(handle)) - 1)
    return None


def _validate_predictions(run_dir: Path) -> None:
    path = run_dir / "predictions.parquet"
    if not path.exists():
        return
    predictions = pd.read_parquet(path)
    required = {CASE_ID, "y_true", "score", "pred"}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(
            f"predictions missing case_id contract columns: {sorted(missing)}"
        )
    if predictions[CASE_ID].isna().any() or not predictions[CASE_ID].is_unique:
        raise ValueError("predictions case_id must be non-null and unique")


def _split_assignment_hash(path: Path) -> str:
    assignments = pd.read_parquet(path)
    if list(assignments.columns) != [CASE_ID, "split"]:
        raise ValueError("split assignments must contain exactly case_id and split")
    if assignments[CASE_ID].isna().any() or not assignments[CASE_ID].is_unique:
        raise ValueError("split assignment case_id must be non-null and unique")
    allowed = {"train", "val", "test"}
    if not set(assignments["split"]).issubset(allowed):
        raise ValueError("split assignments contain an unknown split label")
    identity = {
        name: sorted(
            int(case_id)
            for case_id in assignments.loc[
                assignments["split"] == name,
                CASE_ID,
            ]
        )
        for name in ("train", "val", "test")
    }
    return sha256_json(identity)


def _artifact_catalog(run_dir: Path) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for path in sorted(candidate for candidate in run_dir.rglob("*") if candidate.is_file()):
        relative = path.relative_to(run_dir).as_posix()
        if relative == "run_manifest.json" or relative.endswith(".tmp"):
            continue
        item: dict[str, Any] = {"sha256": sha256_file(path)}
        rows = _row_count(path)
        if rows is not None:
            item["rows"] = rows
        artifacts[relative] = item
    return artifacts


def _git_state(repo_root: Path) -> tuple[str, bool]:
    commit_result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    commit = (
        commit_result.stdout.strip()
        if commit_result.returncode == 0
        else "UNBORN"
    )
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return commit, bool(status)


def assert_clean_repository(repo_root: str | Path = ".") -> None:
    """Reject final-run creation from an uncommitted tracked worktree."""
    commit, dirty = _git_state(Path(repo_root))
    if dirty or commit == "UNBORN":
        raise ValueError("reported final runs require a committed clean Git worktree")


def _validate_content_contract(run_dir: Path, manifest: dict[str, Any]) -> None:
    config_path = run_dir / "config.yaml"
    split_path = run_dir / "split_summary.json"
    assignments_path = run_dir / "split_assignments.parquet"
    metrics_path = run_dir / "metrics.json"
    if not manifest["source_runs"] and config_path.exists():
        resolved_config = yaml.safe_load(config_path.read_text())
        if sha256_json(resolved_config) != manifest["config_sha256"]:
            raise ValueError("config hash mismatch")
    if not manifest["source_runs"] and split_path.exists():
        split_summary = json.loads(split_path.read_text())
        if assignments_path.exists():
            assignments = pd.read_parquet(assignments_path)
            for name in ("train", "val", "test"):
                if name in split_summary:
                    actual = int((assignments["split"] == name).sum())
                    if actual != split_summary[name]["n"]:
                        raise ValueError(f"split assignment count mismatch: {name}")
        if not assignments_path.exists():
            raise ValueError("root run missing split_assignments.parquet")
        if _split_assignment_hash(assignments_path) != manifest["split_sha256"]:
            raise ValueError("split assignment hash mismatch")
        predictions_path = run_dir / "predictions.parquet"
        if predictions_path.exists():
            predictions = pd.read_parquet(predictions_path)
            assignments = pd.read_parquet(assignments_path)
            expected_test_ids = set(
                assignments.loc[assignments["split"] == "test", CASE_ID]
            )
            if set(predictions[CASE_ID]) != expected_test_ids:
                raise ValueError("prediction case_ids differ from frozen test split")
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text())
        if "val" in metrics and metrics["val"].get("threshold") != manifest["threshold"]:
            raise ValueError("validation threshold differs from manifest")
        if "test" in metrics and metrics["test"].get("threshold") != manifest["threshold"]:
            raise ValueError("test threshold differs from manifest")
        if "feature_names" in metrics and metrics["feature_names"] != manifest["feature_names"]:
            raise ValueError("feature_names differ from manifest")


def validate_run_manifest(
    run_dir: str | Path,
    expected_group: str | None = None,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    required = {
        "schema_version",
        "run_id",
        "group",
        "seed",
        "dataset_sha256",
        "config_sha256",
        "split_sha256",
        "threshold",
        "feature_names",
        "git_commit",
        "git_dirty",
        "source_runs",
        "source_code_sha256",
        "artifacts",
        "extra",
    }
    missing = required - set(manifest)
    if missing:
        raise ValueError(f"manifest missing fields: {sorted(missing)}")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported manifest schema")
    if manifest["run_id"] != run_dir.name:
        raise ValueError("run_id does not match directory")
    if expected_group is not None and manifest["group"] != expected_group:
        raise ValueError(
            f"expected group {expected_group}, got {manifest['group']}"
        )
    if not isinstance(manifest["feature_names"], list) or not manifest["feature_names"]:
        raise ValueError("feature_names must be a non-empty list")
    for reference in manifest["source_runs"]:
        if set(reference) != {"run_id", "manifest_sha256"}:
            raise ValueError(
                "source_runs entries must contain only run_id and manifest_sha256"
            )

    _validate_predictions(run_dir)
    actual_artifacts = _artifact_catalog(run_dir)
    if set(actual_artifacts) != set(manifest["artifacts"]):
        raise ValueError(
            "recorded artifact set differs from files present in run directory"
        )
    for relative, recorded in manifest["artifacts"].items():
        path = run_dir / relative
        if not path.exists():
            raise ValueError(f"missing artifact: {relative}")
        if sha256_file(path) != recorded["sha256"]:
            raise ValueError(f"artifact hash mismatch: {relative}")
        if "rows" in recorded and _row_count(path) != recorded["rows"]:
            raise ValueError(f"artifact row-count mismatch: {relative}")

    _validate_content_contract(run_dir, manifest)
    return manifest


def source_run_ref(run_dir: str | Path) -> dict[str, str]:
    run_dir = Path(run_dir)
    manifest = validate_run_manifest(run_dir)
    return {
        "run_id": manifest["run_id"],
        "manifest_sha256": sha256_file(run_dir / "run_manifest.json"),
    }


def assert_source_run(manifest: dict[str, Any], source_dir: str | Path) -> None:
    expected = source_run_ref(source_dir)
    if expected not in manifest["source_runs"]:
        raise ValueError(f"missing exact source reference: {expected['run_id']}")


def assert_source_hashes(
    manifest: dict[str, Any],
    paths: Iterable[str],
    repo_root: str | Path = ".",
) -> None:
    root = Path(repo_root)
    for relative in paths:
        expected = manifest["source_code_sha256"].get(relative)
        if expected is None or sha256_file(root / relative) != expected:
            raise ValueError(f"source hash mismatch: {relative}")


def write_run_manifest(
    run_dir: str | Path,
    *,
    group: str,
    seed: int,
    dataset_path: str | Path | None = None,
    resolved_config: dict[str, Any] | None = None,
    split_summary: dict[str, Any] | None = None,
    threshold: float | None = None,
    feature_names: list[str] | None = None,
    source_run_dirs: Iterable[str | Path] = (),
    source_files: Iterable[str] = (),
    extra: dict[str, Any] | None = None,
    repo_root: str | Path = ".",
    require_clean: bool = False,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    root = Path(repo_root)
    source_dirs = [Path(path) for path in source_run_dirs]
    source_manifests = [validate_run_manifest(path) for path in source_dirs]

    if source_manifests:
        parent = source_manifests[0]
        if int(seed) != int(parent["seed"]):
            raise ValueError("derived run seed must match its upstream manifest")
        dataset_hash = parent["dataset_sha256"]
        config_hash = parent["config_sha256"]
        split_hash = parent["split_sha256"]
        threshold = parent["threshold"] if threshold is None else threshold
        feature_names = (
            parent["feature_names"] if feature_names is None else feature_names
        )
    else:
        if dataset_path is None or resolved_config is None or split_summary is None:
            raise ValueError(
                "root runs require dataset_path, resolved_config, split_summary"
            )
        dataset_hash = sha256_file(dataset_path)
        config_hash = sha256_json(resolved_config)
        assignments_path = run_dir / "split_assignments.parquet"
        if not assignments_path.exists():
            raise ValueError("root runs require split_assignments.parquet")
        split_hash = _split_assignment_hash(assignments_path)

    if threshold is None or not feature_names:
        raise ValueError("threshold and feature_names are required or must be inherited")

    _validate_predictions(run_dir)
    commit, dirty = _git_state(root)
    if require_clean:
        assert_clean_repository(root)

    source_hashes = {
        relative: sha256_file(root / relative)
        for relative in sorted(source_files)
    }
    if require_clean:
        for relative in source_hashes:
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", relative],
                cwd=root,
                capture_output=True,
                text=True,
            )
            if tracked.returncode != 0:
                raise ValueError(f"final-run source file is not tracked: {relative}")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_dir.name,
        "group": group,
        "seed": int(seed),
        "dataset_sha256": dataset_hash,
        "config_sha256": config_hash,
        "split_sha256": split_hash,
        "threshold": float(threshold),
        "feature_names": list(feature_names),
        "git_commit": commit,
        "git_dirty": dirty,
        "source_runs": [source_run_ref(path) for path in source_dirs],
        "source_code_sha256": source_hashes,
        "artifacts": _artifact_catalog(run_dir),
        "extra": extra or {},
    }
    temporary = run_dir / "run_manifest.json.tmp"
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    temporary.replace(run_dir / "run_manifest.json")
    validate_run_manifest(run_dir, expected_group=group)
    return manifest
