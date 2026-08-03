from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.backend.artifacts import (
    ArtifactValidationError,
    _assert_file_points_to,
    _load_transaction_context,
    load_snapshot,
)
from app.backend.settings import DashboardSettings
from tests.dashboard_backend.conftest import REPO_ROOT, assert_no_absolute_paths


def test_exact_recorded_chain_loads_fail_closed(dashboard_snapshot):
    assert len(dashboard_snapshot.cases) == 51
    assert dashboard_snapshot.case(42009).narrative.arm == "strict"
    assert dashboard_snapshot.case(120085).y_true == 0
    assert dashboard_snapshot.case(120085).pred == 1
    case = dashboard_snapshot.case(42009)
    assert case.transaction_context.amount == 112.33
    assert case.transaction_context.elapsed_seconds == 40919.0
    assert case.score_rank == 1
    assert case.flagged_total == 51
    assert set(dashboard_snapshot.figures) == {"pr_curves", "shap_global_bar"}
    assert_no_absolute_paths(dashboard_snapshot.public_provenance())


def test_transaction_context_rejects_dataset_hash_mismatch(tmp_path: Path):
    dataset = tmp_path / "creditcard.csv"
    pd.DataFrame({"Time": [0.0], "Amount": [12.34]}).to_csv(dataset, index=False)

    with pytest.raises(ArtifactValidationError, match="dataset hash"):
        _load_transaction_context(dataset, "0" * 64, {0})


def test_source_pointer_allows_relocated_release_with_same_run_id(tmp_path: Path):
    expected = tmp_path / "release" / "experiments" / "runs" / "g6_seed42"
    expected.mkdir(parents=True)
    pointer = tmp_path / "source_detector_run.txt"
    pointer.write_text("/original/workspace/experiments/runs/g6_seed42\n")

    _assert_file_points_to(pointer, expected, "G4 detector")


def test_source_pointer_rejects_different_run_id(tmp_path: Path):
    expected = tmp_path / "release" / "experiments" / "runs" / "g6_seed42"
    expected.mkdir(parents=True)
    pointer = tmp_path / "source_detector_run.txt"
    pointer.write_text("/original/workspace/experiments/runs/g0_seed42\n")

    with pytest.raises(ArtifactValidationError, match="does not match configured run"):
        _assert_file_points_to(pointer, expected, "G4 detector")


def test_snapshot_rejects_recorded_source_code_hash_mismatch(
    dashboard_settings,
    monkeypatch,
):
    def reject_detector(manifest, paths, repo_root="."):
        if manifest["group"] == "g6":
            raise ValueError("source hash mismatch: src/run_experiment.py")

    monkeypatch.setattr("app.backend.artifacts.assert_source_hashes", reject_detector)
    with pytest.raises(ArtifactValidationError, match="source hash mismatch"):
        load_snapshot(dashboard_settings)


def test_wrong_configured_detector_is_rejected(tmp_path: Path):
    config = tmp_path / "dashboard.yaml"
    config.write_text(
        """schema_version: 1
artifacts:
  detector_run: experiments/runs/2026-07-14_g0_seed42
  g4_run: experiments/runs/2026-07-14_g4_seed42
  g5_run: experiments/runs/2026-07-14_g5_seed42
  results_manifest: reports/results_manifest.json
demo_cases:
  faithful_case_id: 42009
  error_or_uncertainty_case_id: 120085
  attack_case_id: 42009
recorded_narrative_arm: strict
ollama: {host: http://127.0.0.1:11434, model: 'llama3:8b', timeout_seconds: 20}
server: {host: 127.0.0.1, port: 8000}
"""
    )
    settings = DashboardSettings.load(config, repo_root=REPO_ROOT)
    with pytest.raises(ArtifactValidationError, match="G4.*detector|source chain"):
        load_snapshot(settings)


def test_invalid_curated_scenario_is_rejected(tmp_path: Path):
    config = tmp_path / "dashboard.yaml"
    config.write_text(
        """schema_version: 1
artifacts:
  detector_run: experiments/runs/2026-07-14_g6_seed42
  g4_run: experiments/runs/2026-07-14_g4_seed42
  g5_run: experiments/runs/2026-07-14_g5_seed42
  results_manifest: reports/results_manifest.json
demo_cases:
  faithful_case_id: 120085
  error_or_uncertainty_case_id: 42009
  attack_case_id: 42009
recorded_narrative_arm: strict
ollama: {host: http://127.0.0.1:11434, model: 'llama3:8b', timeout_seconds: 20}
server: {host: 127.0.0.1, port: 8000}
"""
    )
    settings = DashboardSettings.load(config, repo_root=REPO_ROOT)
    with pytest.raises(ArtifactValidationError, match="error.*false positive"):
        load_snapshot(settings)
