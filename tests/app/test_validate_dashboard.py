import subprocess

from tools.validate_dashboard import validate_dashboard


def test_exact_dashboard_config_validates_real_artifact_snapshot():
    result = validate_dashboard("configs/dashboard.yaml")

    assert result["valid"] is True
    assert result["case_count"] == 51
    assert result["scenario_count"] == 3
    assert result["source_chain_verified"] is True
    assert result["recorded_narrative_arm"] == "strict"


def test_dashboard_validator_script_entry_point_runs_from_repo_root():
    completed = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "tools/validate_dashboard.py",
            "--config",
            "configs/dashboard.yaml",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert '"valid": true' in completed.stdout
