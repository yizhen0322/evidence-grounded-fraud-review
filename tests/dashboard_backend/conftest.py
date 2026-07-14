from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.backend.artifacts import load_snapshot
from app.backend.server import create_app
from app.backend.settings import DashboardSettings
from app.backend.workflow import WorkflowStore


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def dashboard_settings(tmp_path_factory: pytest.TempPathFactory) -> DashboardSettings:
    config_path = tmp_path_factory.mktemp("dashboard-config") / "dashboard.yaml"
    config_path.write_text(
        """schema_version: 1
artifacts:
  detector_run: experiments/runs/2026-07-14_g6_seed42
  g4_run: experiments/runs/2026-07-14_g4_seed42
  g5_run: experiments/runs/2026-07-14_g5_seed42
  results_manifest: reports/results_manifest.json
demo_cases:
  faithful_case_id: 42009
  error_or_uncertainty_case_id: 120085
  attack_case_id: 42009
recorded_narrative_arm: strict
ollama:
  host: http://127.0.0.1:11434
  model: llama3:8b
  timeout_seconds: 20
server:
  host: 127.0.0.1
  port: 8000
"""
    )
    return DashboardSettings.load(config_path, repo_root=REPO_ROOT)


@pytest.fixture(scope="session")
def dashboard_snapshot(dashboard_settings: DashboardSettings):
    return load_snapshot(dashboard_settings)


class StubLiveService:
    def availability(self) -> str:
        return "unavailable"

    def generate(self, case_id: int) -> dict:
        raise AssertionError(f"unexpected live generation for {case_id}")


@pytest.fixture()
def workflow_store(tmp_path):
    return WorkflowStore(tmp_path / "workflow.sqlite3")


@pytest.fixture()
def api_client(dashboard_settings, dashboard_snapshot, workflow_store):
    app = create_app(
        dashboard_settings,
        dashboard_snapshot,
        live_service=StubLiveService(),
        workflow_store=workflow_store,
        require_frontend=False,
    )
    with TestClient(app) as client:
        yield client


def assert_no_absolute_paths(payload) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    assert str(REPO_ROOT) not in encoded
    assert "/Users/" not in encoded
