from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.backend.artifacts import ArtifactValidationError
from app.backend.semantic_artifacts import load_semantic_snapshot
from app.backend.server import create_app
from app.backend.settings import DashboardSettings
from src.provenance import sha256_file, sha256_json
from src.semantic.explanations import STRUCTURED_PROMPT_TEMPLATE, allowed_summaries


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n")


def _base_config(tmp_path: Path, semantic_run: str | None) -> DashboardSettings:
    semantic_line = "" if semantic_run is None else f"  semantic_run: {semantic_run}\n"
    config = tmp_path / "dashboard.yaml"
    config.write_text(
        f"""schema_version: 1
artifacts:
  dataset_path: data/raw/creditcard.csv
  detector_run: experiments/runs/detector
  g4_run: experiments/runs/g4
  g5_run: experiments/runs/g5
  results_manifest: reports/results_manifest.json
{semantic_line}demo_cases:
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
    return DashboardSettings.load(config, repo_root=tmp_path)


def _semantic_run(tmp_path: Path) -> Path:
    run = tmp_path / "experiments/runs/2026-07-26_s0_seed42"
    run.mkdir(parents=True)
    _write_jsonl(
        run / "semantic_cases.jsonl",
        [
            {
                "case_id": "9000001",
                "alert_rank": 1,
                "flagged_total": 1,
                "detector_score": 0.91,
                "threshold": 0.73,
                "risk_bucket": "High",
                "review_status": "unreviewed",
                "transaction_context": {
                    "transaction_id": "T-0001",
                    "transaction_time": "2026-07-26T09:15:00",
                    "amount": 184.52,
                    "customer_activity_24h": 5,
                    "terminal_context": "new for customer in 30 days",
                },
                "reason_codes": [
                    {
                        "evidence_key": "AmountVsCustomer30Day",
                        "display_label": "Amount vs customer 30-day average",
                        "direction": "up",
                        "rank": 1,
                        "value_bucket": "much higher than usual",
                        "shap_value": 0.42,
                    },
                    {
                        "evidence_key": "NewTerminalForCustomer30Day",
                        "display_label": "New terminal for customer",
                        "direction": "up",
                        "rank": 2,
                        "value_bucket": "new terminal",
                        "shap_value": 0.31,
                    },
                ],
            },
            {
                "case_id": "9000002",
                "alert_rank": 2,
                "flagged_total": 2,
                "detector_score": 0.88,
                "threshold": 0.73,
                "risk_bucket": "Medium",
                "review_status": "unreviewed",
                "transaction_context": {
                    "transaction_id": "T-0002",
                    "transaction_time": "2026-07-26T09:16:00",
                    "amount": 92.10,
                    "customer_activity_24h": 8,
                    "terminal_context": "higher than usual terminal velocity",
                },
                "reason_codes": [
                    {
                        "evidence_key": "TerminalVelocity1Hour",
                        "display_label": "Terminal one-hour velocity",
                        "direction": "up",
                        "rank": 1,
                        "value_bucket": "higher than usual",
                        "shap_value": 0.28,
                    }
                ],
            },
        ],
    )
    first_payload = {
        "risk_bucket": "High",
        "evidence": [
            {
                "feature": "AmountVsCustomer30Day",
                "display_label": "Amount vs customer 30-day average",
                "direction": "up",
                "rank": 1,
                "value_bucket": "much higher than usual",
            },
            {
                "feature": "NewTerminalForCustomer30Day",
                "display_label": "New terminal for customer",
                "direction": "up",
                "rank": 2,
                "value_bucket": "new terminal",
            },
        ],
    }
    first_candidate = {
        "risk_bucket": "High",
        "summary": allowed_summaries(first_payload)[0],
        "evidence": first_payload["evidence"],
        "action": "manual_review",
    }
    second_payload = {
        "risk_bucket": "Medium",
        "evidence": [
            {
                "feature": "TerminalVelocity1Hour",
                "display_label": "Terminal one-hour velocity",
                "direction": "up",
                "rank": 1,
                "value_bucket": "higher than usual",
            }
        ],
    }
    second_candidate = {
        "risk_bucket": "Medium",
        "summary": "This unsupported summary is not an allowed evidence-bound option.",
        "evidence": second_payload["evidence"],
        "action": "manual_review",
    }
    _write_jsonl(
        run / "explanation_comparison.jsonl",
        [
            {
                "case_id": "9000001",
                "deterministic_brief": "High-risk synthetic alert with unusually large spend and a new terminal.",
                "guarded_llm_brief": first_candidate["summary"],
                "delivered_brief": first_candidate["summary"],
                "validation": {
                    "format": True,
                    "completeness": True,
                    "grounding": True,
                    "direction": True,
                },
                "fallback": False,
                "fallback_reason": None,
                "minimized_llm_payload": first_payload,
                "llm_candidate": first_candidate,
                "llm_transport_status": "ok",
            },
            {
                "case_id": "9000002",
                "deterministic_brief": "Medium-risk synthetic alert with elevated terminal velocity.",
                "guarded_llm_brief": "Medium-risk synthetic alert with elevated terminal velocity.",
                "delivered_brief": "Medium-risk synthetic alert with elevated terminal velocity.",
                "validation": {
                    "format": False,
                    "completeness": True,
                    "grounding": False,
                    "direction": True,
                },
                "fallback": True,
                "fallback_reason": "format",
                "minimized_llm_payload": second_payload,
                "llm_candidate": second_candidate,
                "llm_transport_status": "ok",
            },
        ],
    )
    _write_json(
        run / "metrics.json",
        {"val": {"threshold": 0.73}, "test": {"auc_pr": 0.62, "threshold": 0.73}},
    )
    _write_json(
        run / "explanation_summary.json",
        {"cases": 2, "fallback_rate": {"rate": 0.5, "n": 2}},
    )
    corpus_path = tmp_path / "corpus/semantic_guardrail_corpus_v1.jsonl"
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_path.write_text('{"id":"fixture"}\n')
    validator_path = tmp_path / "src/semantic/explanations.py"
    validator_path.parent.mkdir(parents=True, exist_ok=True)
    validator_path.write_text("# fixture validator identity\n")
    _write_json(
        run / "semantic_validator_calibration.json",
        {
            "schema_version": 1,
            "corpus_version": "semantic_guardrail_corpus_v1",
            "corpus_path": "corpus/semantic_guardrail_corpus_v1.jsonl",
            "corpus_sha256": sha256_file(corpus_path),
            "validator_source": "src/semantic/explanations.py",
            "validator_sha256": sha256_file(validator_path),
            "prompt_sha256": sha256_json(STRUCTURED_PROMPT_TEMPLATE),
            "n": 24,
            "matched": 24,
            "passed": True,
            "control_acceptance": {"rate": 1.0, "n": 12, "lower": 0.75, "upper": 1.0},
            "attack_interception": {"rate": 1.0, "n": 12, "lower": 0.75, "upper": 1.0},
        },
    )
    manifest = {
        "schema_version": 1,
        "run_id": run.name,
        "group": "s0",
        "seed": 42,
        "dataset_sha256": "dataset-hash",
        "config_sha256": "config-hash",
        "threshold": 0.73,
        "feature_names": [
            "AmountVsCustomer30Day",
            "NewTerminalForCustomer30Day",
        ],
        "extra": {
            "validator_corpus_sha256": sha256_file(corpus_path),
            "validator_sha256": sha256_file(validator_path),
            "prompt_sha256": sha256_json(STRUCTURED_PROMPT_TEMPLATE),
            "validator_calibration_sha256": sha256_file(
                run / "semantic_validator_calibration.json"
            ),
        },
        "artifacts": {
            relative: {"sha256": sha256_file(run / relative)}
            for relative in (
                "semantic_cases.jsonl",
                "explanation_comparison.jsonl",
                "metrics.json",
                "explanation_summary.json",
                "semantic_validator_calibration.json",
            )
        },
    }
    _write_json(run / "run_manifest.json", manifest)
    return run


def test_operational_endpoints_return_503_without_semantic_run(
    tmp_path: Path,
    dashboard_snapshot,
):
    settings = _base_config(tmp_path, None)
    app = create_app(settings, dashboard_snapshot, require_frontend=False)
    with TestClient(app) as client:
        for route in (
            "/api/v1/operational/cases",
            "/api/v1/operational/cases/9000001",
            "/api/v1/operational/results",
        ):
            response = client.get(route)
            assert response.status_code == 503
            assert response.json()["code"] == "semantic_run_unavailable"


def test_semantic_snapshot_fails_closed_when_relative_risk_bucket_is_missing(
    tmp_path: Path,
):
    run = _semantic_run(tmp_path)
    cases_path = run / "semantic_cases.jsonl"
    rows = [json.loads(line) for line in cases_path.read_text().splitlines()]
    rows[0].pop("risk_bucket")
    _write_jsonl(cases_path, rows)
    manifest_path = run / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"]["semantic_cases.jsonl"]["sha256"] = sha256_file(cases_path)
    _write_json(manifest_path, manifest)
    settings = _base_config(tmp_path, run.relative_to(tmp_path).as_posix())

    with pytest.raises(ArtifactValidationError, match="missing relative risk_bucket"):
        load_semantic_snapshot(settings)


def test_operational_endpoints_expose_semantic_contract_without_ground_truth(
    tmp_path: Path,
    dashboard_snapshot,
):
    run = _semantic_run(tmp_path)
    settings = _base_config(tmp_path, run.relative_to(tmp_path).as_posix())
    app = create_app(settings, dashboard_snapshot, require_frontend=False)
    with TestClient(app) as client:
        queue = client.get("/api/v1/operational/cases")
        assert queue.status_code == 200
        queue_payload = queue.json()
        assert queue_payload["synthetic"] is True
        assert queue_payload["total"] == 2
        assert queue_payload["items"][0]["synthetic"] is True
        assert queue_payload["items"][0]["top_reason"] == {
            "feature": "AmountVsCustomer30Day",
            "display_label": "Amount vs customer 30-day average",
            "direction": "increases_risk",
            "direction_label": "Increases risk",
            "rank": 1,
            "value_bucket": "much higher than usual",
        }
        assert queue_payload["items"][0]["explanation_delivery"] == "guarded_llm"
        assert queue_payload["items"][0]["timestamp"] == "2026-07-26T09:15:00"

        detail = client.get("/api/v1/operational/cases/9000001")
        assert detail.status_code == 200
        payload = detail.json()
        assert payload["synthetic"] is True
        assert payload["detector"]["threshold"] == 0.73
        assert payload["reason_codes"][0]["shap_value"] == 0.42
        assert payload["reason_codes"][0]["direction"] == "increases_risk"
        assert payload["explanation_comparison"]["deterministic_brief"]
        assert payload["validation"]["passed"] is True
        assert payload["explanations"]["guarded_llm"]["checks"] == {
            "format": "PASS",
            "completeness": "PASS",
            "grounding": "PASS",
            "direction": "PASS",
        }
        assert payload["data_sent_to_llm"]["payload"]["risk_bucket"] == "High"
        encoded = json.dumps(payload, sort_keys=True)
        assert "y_true" not in encoded
        assert "historical_label" not in encoded
        assert "ground_truth" not in encoded
        assert "fraud_label" not in encoded

        results = client.get("/api/v1/operational/results")
        assert results.status_code == 200
        assert results.json()["metrics"]["test"]["auc_pr"] == 0.62
        assert results.json()["validator_calibration"]["corpus_version"] == (
            "semantic_guardrail_corpus_v1"
        )
        assert results.json()["provenance"]["synthetic"] is True
        assert (
            "semantic_validator_calibration.json"
            in results.json()["provenance"]["artifacts"]
        )

        fallback_queue = client.get("/api/v1/operational/cases?recorded_fallback=true")
        assert fallback_queue.status_code == 200
        assert fallback_queue.json()["total"] == 1
        assert fallback_queue.json()["items"][0]["case_id"] == 9000002

        passed_queue = client.get("/api/v1/operational/cases?recorded_fallback=false")
        assert passed_queue.status_code == 200
        assert passed_queue.json()["total"] == 1
        assert passed_queue.json()["items"][0]["case_id"] == 9000001


def test_operational_workflow_uses_semantic_evidence_namespace(
    tmp_path: Path,
    dashboard_snapshot,
):
    run = _semantic_run(tmp_path)
    settings = _base_config(tmp_path, run.relative_to(tmp_path).as_posix())
    app = create_app(settings, dashboard_snapshot, require_frontend=False)
    with TestClient(app) as client:
        summary = client.get("/api/v1/operational/workflow/summary")
        assert summary.status_code == 200
        assert summary.json()["counts"]["unreviewed"] == 2

        started = client.put(
            "/api/v1/operational/workflow/cases/9000001",
            json={
                "revision": 0,
                "status": "in_review",
                "disposition": None,
                "note": "",
            },
        )
        assert started.status_code == 200
        assert started.json()["status"] == "in_review"

        research = client.get("/api/v1/workflow/cases/9000001")
        assert research.status_code == 404


@pytest.mark.parametrize(
    "preset,target_check",
    [
        ("direction_flip", "direction"),
        ("unlisted_feature", "grounding"),
        ("template_corruption", "format"),
    ],
)
def test_operational_guardrail_demo_uses_semantic_validator(
    tmp_path: Path,
    dashboard_snapshot,
    preset: str,
    target_check: str,
):
    run = _semantic_run(tmp_path)
    settings = _base_config(tmp_path, run.relative_to(tmp_path).as_posix())
    app = create_app(settings, dashboard_snapshot, require_frontend=False)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/operational/guardrails/demo",
            json={"case_id": 9000001, "preset": preset},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["validator"] == "src.semantic.explanations.validate_structured_brief"
    assert payload["mode"] == "operational_guardrail_demo"
    assert payload["checks"][target_check] == "FAIL"
    assert payload["fallback"] is True
    assert payload["final_text"] == "High-risk synthetic alert with unusually large spend and a new terminal."
    assert payload["original_text"] != payload["tampered_text"]


def test_semantic_loader_rejects_manifest_hash_mismatch(tmp_path: Path):
    run = _semantic_run(tmp_path)
    (run / "semantic_cases.jsonl").write_text("{}\n")
    settings = _base_config(tmp_path, run.relative_to(tmp_path).as_posix())
    with pytest.raises(ArtifactValidationError, match="hash mismatch"):
        load_semantic_snapshot(settings)


def test_semantic_loader_rejects_manifested_calibration_hash_mismatch(tmp_path: Path):
    run = _semantic_run(tmp_path)
    _write_json(run / "semantic_validator_calibration.json", {"version": "tampered"})
    settings = _base_config(tmp_path, run.relative_to(tmp_path).as_posix())
    with pytest.raises(ArtifactValidationError, match="hash mismatch"):
        load_semantic_snapshot(settings)


def test_semantic_loader_rejects_unmanifested_calibration_absence(tmp_path: Path):
    run = _semantic_run(tmp_path)
    (run / "semantic_validator_calibration.json").unlink()
    manifest = json.loads((run / "run_manifest.json").read_text())
    manifest["artifacts"].pop("semantic_validator_calibration.json")
    _write_json(run / "run_manifest.json", manifest)

    settings = _base_config(tmp_path, run.relative_to(tmp_path).as_posix())
    with pytest.raises(ArtifactValidationError, match="missing required artifacts"):
        load_semantic_snapshot(settings)


def test_semantic_loader_rejects_failed_calibration(tmp_path: Path):
    run = _semantic_run(tmp_path)
    calibration_path = run / "semantic_validator_calibration.json"
    calibration = json.loads(calibration_path.read_text())
    calibration["passed"] = False
    _write_json(calibration_path, calibration)
    manifest = json.loads((run / "run_manifest.json").read_text())
    manifest["artifacts"]["semantic_validator_calibration.json"]["sha256"] = sha256_file(
        calibration_path
    )
    _write_json(run / "run_manifest.json", manifest)
    settings = _base_config(tmp_path, run.relative_to(tmp_path).as_posix())

    with pytest.raises(ArtifactValidationError, match="calibration did not pass"):
        load_semantic_snapshot(settings)


def test_semantic_loader_rejects_payload_that_differs_from_reason_codes(tmp_path: Path):
    run = _semantic_run(tmp_path)
    explanations_path = run / "explanation_comparison.jsonl"
    rows = [json.loads(line) for line in explanations_path.read_text().splitlines()]
    rows[0]["minimized_llm_payload"]["evidence"][0]["feature"] = "TransactionAmount"
    _write_jsonl(explanations_path, rows)
    manifest = json.loads((run / "run_manifest.json").read_text())
    manifest["artifacts"]["explanation_comparison.jsonl"]["sha256"] = sha256_file(
        explanations_path
    )
    _write_json(run / "run_manifest.json", manifest)
    settings = _base_config(tmp_path, run.relative_to(tmp_path).as_posix())

    with pytest.raises(ArtifactValidationError, match="payload evidence differs"):
        load_semantic_snapshot(settings)


def test_semantic_loader_recomputes_and_rejects_false_pass_claim(tmp_path: Path):
    run = _semantic_run(tmp_path)
    explanations_path = run / "explanation_comparison.jsonl"
    rows = [json.loads(line) for line in explanations_path.read_text().splitlines()]
    rows[1]["validation"] = {
        "format": True,
        "completeness": True,
        "grounding": True,
        "direction": True,
    }
    rows[1]["fallback"] = False
    rows[1]["fallback_reason"] = None
    rows[1]["delivered_brief"] = rows[1]["guarded_llm_brief"]
    _write_jsonl(explanations_path, rows)
    manifest = json.loads((run / "run_manifest.json").read_text())
    manifest["artifacts"]["explanation_comparison.jsonl"]["sha256"] = sha256_file(
        explanations_path
    )
    _write_json(run / "run_manifest.json", manifest)
    settings = _base_config(tmp_path, run.relative_to(tmp_path).as_posix())

    with pytest.raises(ArtifactValidationError, match="stored validation differs"):
        load_semantic_snapshot(settings)


def test_semantic_loader_rejects_unbound_explanation_rows(tmp_path: Path):
    run = _semantic_run(tmp_path)
    _write_jsonl(
        run / "explanation_comparison.jsonl",
        [
            {
                "case_id": "txn-other",
                "deterministic_brief": "Fallback.",
                "delivered_brief": "Fallback.",
                "validation": {
                    "format": True,
                    "completeness": True,
                    "grounding": True,
                    "direction": True,
                },
                "fallback": True,
                "fallback_reason": "transport_unavailable",
                "minimized_llm_payload": {"risk_bucket": "High", "evidence": []},
            }
        ],
    )
    manifest = json.loads((run / "run_manifest.json").read_text())
    manifest["artifacts"]["explanation_comparison.jsonl"]["sha256"] = sha256_file(
        run / "explanation_comparison.jsonl"
    )
    _write_json(run / "run_manifest.json", manifest)
    settings = _base_config(tmp_path, run.relative_to(tmp_path).as_posix())
    with pytest.raises(ArtifactValidationError, match="no explanation comparison"):
        load_semantic_snapshot(settings)
