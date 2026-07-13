from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.backend.live import LiveNarrativeService
from app.backend.server import create_app
from src.narratives.llm_client import LLMUnavailable, NarrativeGeneration


def _artifact_state(paths: list[Path]) -> dict[str, tuple[int, str]]:
    import hashlib

    state = {}
    for root in paths:
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for path in files:
            state[str(path)] = (
                path.stat().st_mtime_ns,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
    return state


def test_live_replay_sends_only_minimal_recorded_evidence(
    dashboard_settings,
    dashboard_snapshot,
):
    captured = {}
    accepted = dashboard_snapshot.case(42009).narrative.final_text

    def generate(evidence_text: str, **kwargs):
        captured["evidence"] = evidence_text
        captured["kwargs"] = kwargs
        return NarrativeGeneration(raw_response=accepted, text=accepted)

    service = LiveNarrativeService(
        dashboard_settings,
        dashboard_snapshot,
        generate_fn=generate,
        runtime_fn=lambda **_: {"version": "test", "digest": "test"},
    )
    app = create_app(
        dashboard_settings,
        dashboard_snapshot,
        live_service=service,
        require_frontend=False,
    )
    with TestClient(app) as client:
        response = client.post("/api/v1/live/narrative", json={"case_id": 42009})

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload["mode"] == "live_demo"
    assert payload["reported"] is False
    assert payload["fallback"] is False
    evidence = captured["evidence"]
    assert "Case ID: 42009" in evidence
    assert "Risk level: High" in evidence
    assert "score" not in evidence.lower()
    assert "probability" not in evidence.lower()
    assert "y_true" not in evidence
    assert "Fraud" not in evidence
    for code in dashboard_snapshot.case(42009).reason_codes:
        assert str(code.shap_value) not in evidence
    assert captured["kwargs"]["prompt_style"] == "strict"


def test_live_transport_failure_is_successful_not_run_fallback(
    dashboard_settings,
    dashboard_snapshot,
):
    def unavailable(*_args, **_kwargs):
        raise LLMUnavailable("connection refused")

    service = LiveNarrativeService(
        dashboard_settings,
        dashboard_snapshot,
        generate_fn=unavailable,
        runtime_fn=unavailable,
    )
    app = create_app(
        dashboard_settings,
        dashboard_snapshot,
        live_service=service,
        require_frontend=False,
    )
    with TestClient(app) as client:
        response = client.post("/api/v1/live/narrative", json={"case_id": 42009})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload["fallback"] is True
    assert payload["fallback_reason"] == "llm_transport_unavailable"
    assert set(payload["checks"].values()) == {"NOT_RUN"}
    assert payload["raw_text"] is None


def test_all_api_actions_leave_source_artifacts_unchanged(
    dashboard_settings,
    dashboard_snapshot,
):
    roots = [
        dashboard_settings.detector_run,
        dashboard_settings.g4_run,
        dashboard_settings.g5_run,
        dashboard_settings.results_manifest,
        dashboard_settings.repo_root / "reports/tables",
        dashboard_settings.repo_root / "reports/figures",
    ]
    before = _artifact_state(roots)
    accepted = dashboard_snapshot.case(42009).narrative.final_text
    service = LiveNarrativeService(
        dashboard_settings,
        dashboard_snapshot,
        generate_fn=lambda *_args, **_kwargs: NarrativeGeneration(accepted, accepted),
        runtime_fn=lambda **_: {"version": "test", "digest": "test"},
    )
    app = create_app(
        dashboard_settings,
        dashboard_snapshot,
        live_service=service,
        require_frontend=False,
    )
    with TestClient(app) as client:
        client.get("/api/v1/cases")
        client.get("/api/v1/results")
        client.get("/api/v1/figures/pr_curves")
        client.post("/api/v1/live/narrative", json={"case_id": 42009})
        for preset in ("direction_flip", "unlisted_feature", "template_corruption"):
            client.post(
                "/api/v1/guardrails/demo",
                json={"case_id": 42009, "preset": preset},
            )
    assert _artifact_state(roots) == before
