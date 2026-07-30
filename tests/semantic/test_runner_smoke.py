import json

from app.backend.semantic_artifacts import load_semantic_snapshot
from app.backend.settings import DashboardSettings
from src.provenance import validate_run_manifest
from tools.run_semantic_case_study import run


def _payload_keys(value):
    if isinstance(value, dict):
        keys = set(value)
        for child in value.values():
            keys.update(_payload_keys(child))
        return keys
    if isinstance(value, list):
        keys = set()
        for child in value:
            keys.update(_payload_keys(child))
        return keys
    return set()


def test_semantic_runner_smoke_writes_manifested_artifacts(tmp_path):
    config = {
        "seed": 42,
        "generator": {
            "seed": 42,
            "n_transactions": 900,
            "n_customers": 70,
            "n_terminals": 24,
            "days": 60,
            "terminal_compromise_rate": 0.12,
            "burst_fraud_rate": 0.02,
        },
        "feedback_delay_days": 7,
        "terminal_window_days": 7,
        "top_k": 3,
        "alert_limit": 5,
        "xgb_params": {"n_estimators": 12, "max_depth": 2, "n_jobs": 1},
        "llm": {
            "enabled": True,
            "host": "http://127.0.0.1:1",
            "model": "missing",
            "timeout_seconds": 1,
        },
    }

    run_dir = run(config, out_root=tmp_path)
    manifest = validate_run_manifest(run_dir, expected_group="s0")
    metrics = json.loads((run_dir / "metrics.json").read_text())
    summary = json.loads((run_dir / "explanation_summary.json").read_text())
    case = json.loads((run_dir / "semantic_cases.jsonl").read_text().splitlines()[0])
    explanation = json.loads(
        (run_dir / "explanation_comparison.jsonl").read_text().splitlines()[0]
    )

    required = {
        "config.yaml",
        "dataset_summary.json",
        "split_summary.json",
        "split_assignments.parquet",
        "metrics.json",
        "predictions.parquet",
        "reason_codes.jsonl",
        "semantic_cases.jsonl",
        "semantic_validator_calibration.json",
        "explanation_comparison.jsonl",
        "explanation_summary.json",
        "model/xgb.json",
        "environment.txt",
    }
    assert required.issubset(manifest["artifacts"])
    assert manifest["threshold"] == metrics["val"]["threshold"]
    assert metrics["selection"]["threshold_source"] == "validation_max_f1"
    assert manifest["feature_names"] == metrics["feature_names"]
    assert summary["rows"] == 5
    assert summary["fallbacks"] == 5
    assert summary["transport_failures"] == 5
    assert summary["transport_failure_rate"]["n"] == 5
    assert summary["deterministic_delivered_detected_violation_rate"]["label"] == "by_construction"
    assert summary["structural_descriptors"]["corpus_version"] == "semantic_guardrail_corpus_v1"
    assert manifest["extra"]["validator_corpus_sha256"]
    assert manifest["extra"]["prompt_sha256"]
    assert "y_true" not in case and "label" not in case
    assert {"detector_score", "alert_rank", "flagged_total", "transaction_context", "reason_codes"} <= set(case)
    assert {"transaction_time", "amount"} <= set(case["transaction_context"])
    assert case["reason_codes"][0]["direction"] in {"up", "down"}
    assert set(explanation["validation"]) == {"format", "completeness", "grounding", "direction"}
    assert explanation["fallback"] is True
    assert "minimized_llm_payload" in explanation
    forbidden_payload_keys = {
        "case_id",
        "amount",
        "score",
        "detector_score",
        "shap_value",
        "y_true",
    }
    assert forbidden_payload_keys.isdisjoint(
        _payload_keys(explanation["minimized_llm_payload"])
    )

    dashboard_config = tmp_path / "dashboard.yaml"
    dashboard_config.write_text(
        f"""schema_version: 1
artifacts:
  dataset_path: data/raw/creditcard.csv
  detector_run: experiments/runs/detector
  g4_run: experiments/runs/g4
  g5_run: experiments/runs/g5
  results_manifest: reports/results_manifest.json
  semantic_run: {run_dir.relative_to(tmp_path).as_posix()}
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
    )
    settings = DashboardSettings.load(dashboard_config, repo_root=tmp_path)
    snapshot = load_semantic_snapshot(settings)
    assert len(snapshot.cases) == 5
