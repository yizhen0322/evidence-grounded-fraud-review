from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.backend.server import create_app
from app.backend.settings import DashboardSettings


BASE = """schema_version: 1
artifacts:
  dataset_path: data/raw/creditcard.csv
  detector_run: experiments/runs/detector
  g4_run: experiments/runs/g4
  g5_run: experiments/runs/g5
  results_manifest: reports/results_manifest.json
demo_cases:
  faithful_case_id: 1
  error_or_uncertainty_case_id: 2
  attack_case_id: 1
recorded_narrative_arm: strict
ollama:
  host: http://127.0.0.1:11434
  model: llama3:8b
  timeout_seconds: 20
server:
  host: 127.0.0.1
  port: 8000
workflow:
  enabled: true
  database_path: var/dashboard/workflow.sqlite3
"""


@pytest.mark.parametrize(
    "old,new,message",
    [
        ("http://127.0.0.1:11434", "https://ollama.example.com", "loopback"),
        ("http://127.0.0.1:11434", "http://127.0.0.2:11434", "loopback"),
        ("host: 127.0.0.1", "host: 0.0.0.0", "loopback"),
        ("experiments/runs/detector", "experiments/runs/latest", "latest"),
        (
            "experiments/runs/detector",
            "experiments/runs/detector\n  semantic_run: experiments/runs/latest",
            "latest",
        ),
        ("experiments/runs/g4", "experiments/runs/g*", "glob"),
        ("data/raw/creditcard.csv", "data/raw/*.csv", "glob"),
    ],
)
def test_settings_reject_remote_or_ambiguous_configuration(
    tmp_path: Path,
    old: str,
    new: str,
    message: str,
):
    path = tmp_path / "dashboard.yaml"
    path.write_text(BASE.replace(old, new))
    with pytest.raises(ValueError, match=message):
        DashboardSettings.load(path, repo_root=tmp_path)


def test_settings_forbid_unplanned_fields(tmp_path: Path):
    path = tmp_path / "dashboard.yaml"
    path.write_text(BASE + "browser_selectable_path: true\n")
    with pytest.raises(ValueError, match="browser_selectable_path|extra"):
        DashboardSettings.load(path, repo_root=tmp_path)


@pytest.mark.parametrize(
    "database_path",
    [
        "experiments/workflow.sqlite3",
        "reports/workflow.sqlite3",
        "../workflow.sqlite3",
        "var/dashboard/workflow-*.sqlite3",
    ],
)
def test_settings_keep_workflow_database_separate_and_exact(
    tmp_path: Path,
    database_path: str,
):
    path = tmp_path / "dashboard.yaml"
    path.write_text(
        BASE.replace(
            "var/dashboard/workflow.sqlite3",
            database_path,
        )
    )
    with pytest.raises(ValueError, match="workflow|glob|escapes"):
        DashboardSettings.load(path, repo_root=tmp_path)


def test_disabled_workflow_never_opens_database(
    tmp_path: Path,
    dashboard_snapshot,
    monkeypatch,
):
    path = tmp_path / "dashboard.yaml"
    path.write_text(
        BASE.replace("enabled: true", "enabled: false").replace(
            "experiments/runs/detector",
            "experiments/runs/2026-07-14_g6_seed42",
        ).replace(
            "experiments/runs/g4",
            "experiments/runs/2026-07-14_g4_seed42",
        ).replace(
            "experiments/runs/g5",
            "experiments/runs/2026-07-14_g5_seed42",
        )
    )
    settings = DashboardSettings.load(path, repo_root=Path.cwd())

    def unexpected_store(_path):
        raise AssertionError("disabled workflow must not open SQLite")

    monkeypatch.setattr("app.backend.server.WorkflowStore", unexpected_store)
    app = create_app(settings, dashboard_snapshot, require_frontend=False)
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json()["workflow_status"] == "disabled"
        record = client.get("/api/v1/workflow/cases/42009").json()
        assert record["status"] == "unreviewed"
        assert client.put(
            "/api/v1/workflow/cases/42009",
            json={
                "revision": 0,
                "status": "in_review",
                "disposition": None,
                "note": "",
            },
        ).status_code == 503
