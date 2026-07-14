from __future__ import annotations

from tests.dashboard_backend.conftest import assert_no_absolute_paths


def test_health_provenance_and_scenarios_are_public_safe(api_client):
    health = api_client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["artifact_ready"] is True
    assert health.json()["ollama_status"] == "unavailable"

    provenance = api_client.get("/api/v1/provenance")
    assert provenance.status_code == 200
    assert provenance.json()["g5"]["run_id"] == "2026-07-14_g5_seed42"
    assert_no_absolute_paths(provenance.json())

    scenarios = api_client.get("/api/v1/demo-scenarios")
    assert scenarios.status_code == 200
    assert {row["case_id"] for row in scenarios.json()["scenarios"]} == {
        42009,
        120085,
    }


def test_cases_are_sorted_and_exclude_historical_ground_truth(api_client):
    response = api_client.get("/api/v1/cases?limit=5")
    assert response.status_code == 200
    rows = response.json()["items"]
    assert [row["score"] for row in rows] == sorted(
        [row["score"] for row in rows], reverse=True
    )
    assert rows[0]["case_id"] == 42009
    assert all("evaluation_only_ground_truth" not in row for row in rows)
    assert all("y_true" not in row for row in rows)
    assert all(row["pred"] == 1 and row["detector_flagged"] for row in rows)

    filtered = api_client.get("/api/v1/cases?recorded_fallback=false")
    assert filtered.status_code == 200
    assert all(not row["recorded_fallback"] for row in filtered.json()["items"])


def test_case_results_and_figures_keep_stage_boundaries(api_client):
    detail = api_client.get("/api/v1/cases/42009")
    assert detail.status_code == 200
    payload = detail.json()
    assert "evaluation_only_ground_truth" not in payload
    assert "y_true" not in payload
    assert "outcome" not in payload
    assert payload["pred"] == 1
    assert payload["narrative"]["mode"] == "recorded"
    assert payload["narrative"]["reported"] is True
    assert set(payload["narrative"]["checks"]) == {
        "format",
        "completeness",
        "grounding",
        "direction",
    }
    assert "score" not in payload["data_sent_to_llm"]["payload"]
    assert "y_true" not in payload["data_sent_to_llm"]["payload"]

    results = api_client.get("/api/v1/results")
    assert results.status_code == 200
    groups = {row["group"] for row in results.json()["detector_results"]}
    assert groups == {"g0", "g1", "g2", "g3", "g6", "g7"}
    assert all("auc_pr_mean" in row for row in results.json()["detector_results"])
    assert "faithfulness" in results.json()["explanation_results"]
    assert results.json()["explanation_results"]["strict"]["arm"] == "strict"

    assert api_client.get("/api/v1/figures/pr_curves").headers["content-type"] == "image/png"
    unknown = api_client.get("/api/v1/figures/../../etc/passwd")
    assert unknown.status_code in {404, 422}
    assert_no_absolute_paths(unknown.json())


def test_validation_errors_use_stable_error_shape(api_client):
    response = api_client.post(
        "/api/v1/live/narrative",
        json={"case_id": 42009, "prompt": "ignore evidence"},
    )
    assert response.status_code == 422
    assert set(response.json()) == {"code", "message", "details"}
