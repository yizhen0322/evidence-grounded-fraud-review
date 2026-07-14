from __future__ import annotations

from pathlib import Path

from app.backend.workflow import WorkflowStore, evidence_fingerprint
from src.provenance import sha256_file


def test_workflow_journey_persists_and_records_activity(api_client, workflow_store):
    initial = api_client.get("/api/v1/workflow/cases/42009")
    assert initial.status_code == 200
    assert initial.json()["status"] == "unreviewed"
    assert initial.json()["revision"] == 0

    started = api_client.put(
        "/api/v1/workflow/cases/42009",
        json={
            "revision": 0,
            "status": "in_review",
            "disposition": None,
            "note": "Checking the recorded evidence.",
        },
    )
    assert started.status_code == 200
    assert started.json()["revision"] == 1

    completed = api_client.put(
        "/api/v1/workflow/cases/42009",
        json={
            "revision": 1,
            "status": "review_complete",
            "disposition": "suspicious",
            "note": "Recorded evidence supports follow-up.",
        },
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "review_complete"
    assert completed.json()["revision"] == 2

    fingerprint = api_client.get("/api/v1/workflow/summary").json()[
        "evidence_fingerprint"
    ]
    reloaded = WorkflowStore(workflow_store.path)
    persisted = reloaded.get(42009, fingerprint)
    assert persisted["disposition"] == "suspicious"
    assert persisted["note"] == "Recorded evidence supports follow-up."

    activity = api_client.get("/api/v1/workflow/cases/42009/activity").json()[
        "items"
    ]
    assert [event["event_type"] for event in activity] == [
        "review_completed",
        "review_started",
    ]


def test_workflow_rejects_stale_revision_invalid_case_and_incomplete_close(api_client):
    started = api_client.put(
        "/api/v1/workflow/cases/42009",
        json={
            "revision": 0,
            "status": "in_review",
            "disposition": None,
            "note": "",
        },
    )
    assert started.status_code == 200

    stale = api_client.put(
        "/api/v1/workflow/cases/42009",
        json={
            "revision": 0,
            "status": "needs_follow_up",
            "disposition": "inconclusive",
            "note": "",
        },
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "workflow_revision_conflict"

    incomplete = api_client.put(
        "/api/v1/workflow/cases/42009",
        json={
            "revision": 1,
            "status": "review_complete",
            "disposition": None,
            "note": "",
        },
    )
    assert incomplete.status_code == 422
    assert incomplete.json()["code"] == "invalid_workflow_transition"

    unknown = api_client.put(
        "/api/v1/workflow/cases/999999999",
        json={
            "revision": 0,
            "status": "in_review",
            "disposition": None,
            "note": "",
        },
    )
    assert unknown.status_code == 404


def test_workflow_store_schema_excludes_research_evidence(workflow_store):
    columns = workflow_store.table_columns()
    forbidden = {
        "score",
        "threshold",
        "y_true",
        "shap_value",
        "reason_codes",
        "narrative",
        "raw_transaction",
    }
    assert forbidden.isdisjoint(columns["workflow_cases"])
    assert forbidden.isdisjoint(columns["workflow_events"])


def test_workflow_writes_do_not_change_configured_artifacts(
    api_client,
    dashboard_settings,
):
    paths = [
        dashboard_settings.detector_run / "run_manifest.json",
        dashboard_settings.g4_run / "run_manifest.json",
        dashboard_settings.g5_run / "run_manifest.json",
        dashboard_settings.results_manifest,
    ]
    before = {path: (sha256_file(path), path.stat().st_mtime_ns) for path in paths}

    response = api_client.put(
        "/api/v1/workflow/cases/42009",
        json={
            "revision": 0,
            "status": "in_review",
            "disposition": None,
            "note": "Local note only.",
        },
    )
    assert response.status_code == 200

    after = {path: (sha256_file(path), path.stat().st_mtime_ns) for path in paths}
    assert after == before


def test_evidence_fingerprint_changes_when_manifest_identity_changes():
    provenance = {
        name: {"run_id": name, "manifest_sha256": character * 64}
        for name, character in (("detector", "a"), ("g4", "b"), ("g5", "c"))
    }
    first = evidence_fingerprint(provenance)
    provenance["g5"]["manifest_sha256"] = "d" * 64
    assert evidence_fingerprint(provenance) != first
