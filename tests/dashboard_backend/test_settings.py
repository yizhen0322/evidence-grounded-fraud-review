from __future__ import annotations

from pathlib import Path

import pytest

from app.backend.settings import DashboardSettings


BASE = """schema_version: 1
artifacts:
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
"""


@pytest.mark.parametrize(
    "old,new,message",
    [
        ("http://127.0.0.1:11434", "https://ollama.example.com", "loopback"),
        ("host: 127.0.0.1", "host: 0.0.0.0", "loopback"),
        ("experiments/runs/detector", "experiments/runs/latest", "latest"),
        ("experiments/runs/g4", "experiments/runs/g*", "glob"),
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
