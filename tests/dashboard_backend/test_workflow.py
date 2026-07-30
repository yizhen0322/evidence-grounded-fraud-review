from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from app.backend.workflow import (
    WorkflowStore,
    WorkflowTransitionError,
    evidence_fingerprint,
)
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
    assert {"namespace", "case_key", "case_id"}.issubset(columns["workflow_cases"])
    assert {"namespace", "case_key", "case_id"}.issubset(columns["workflow_events"])


def test_workflow_namespaces_keep_same_case_id_independent(workflow_store):
    fingerprint = "a" * 64
    research = workflow_store.update(
        case_id=42009,
        expected_revision=0,
        status="in_review",
        disposition=None,
        note="Research review",
        current_fingerprint=fingerprint,
        namespace="research",
    )
    operational = workflow_store.update(
        case_id=42009,
        expected_revision=0,
        status="in_review",
        disposition=None,
        note="Operational review",
        current_fingerprint=fingerprint,
        namespace="operational",
    )

    assert research["note"] == "Research review"
    assert operational["note"] == "Operational review"
    assert workflow_store.get(42009, fingerprint, namespace="research")["revision"] == 1
    assert workflow_store.get(42009, fingerprint, namespace="operational")["revision"] == 1
    assert workflow_store.activity(42009, fingerprint, namespace="research")[0][
        "event_type"
    ] == "review_started"
    assert workflow_store.activity(42009, fingerprint, namespace="operational")[0][
        "event_type"
    ] == "review_started"


def test_legacy_activity_is_migrated_fail_closed_by_evidence_fingerprint(tmp_path):
    path = tmp_path / "legacy-workflow.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE workflow_cases (
                case_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                disposition TEXT,
                note TEXT NOT NULL,
                revision INTEGER NOT NULL,
                evidence_fingerprint TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE workflow_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT NOT NULL,
                disposition TEXT,
                note_changed INTEGER NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            INSERT INTO workflow_events (
                case_id, event_type, from_status, to_status, disposition,
                note_changed, revision, created_at
            ) VALUES (42009, 'review_completed', 'in_review', 'review_complete',
                      'suspicious', 1, 2, '2026-07-14T00:00:00+00:00');
            """
        )

    store = WorkflowStore(path)
    assert "evidence_fingerprint" in store.table_columns()["workflow_events"]
    assert store.activity(42009, "a" * 64) == []


def test_workflow_writes_do_not_change_configured_artifacts(
    api_client,
    dashboard_settings,
):
    paths: list[Path] = []
    for run_dir in (
        dashboard_settings.detector_run,
        dashboard_settings.g4_run,
        dashboard_settings.g5_run,
    ):
        manifest_path = run_dir / "run_manifest.json"
        paths.append(manifest_path)
        manifest = json.loads(manifest_path.read_text())
        paths.extend(run_dir / relative_path for relative_path in manifest["artifacts"])

    paths.append(dashboard_settings.results_manifest)
    results_manifest = json.loads(dashboard_settings.results_manifest.read_text())
    repo_root = dashboard_settings.results_manifest.parents[1]
    paths.extend(repo_root / relative_path for relative_path in results_manifest["outputs"])
    assert len(set(paths)) >= 18
    paths = sorted(set(paths))
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


def test_evidence_change_masks_old_decision_and_supports_explicit_restart(
    workflow_store,
):
    old_fingerprint = "a" * 64
    new_fingerprint = "b" * 64
    workflow_store.update(
        case_id=42009,
        expected_revision=0,
        status="in_review",
        disposition=None,
        note="old review",
        current_fingerprint=old_fingerprint,
    )
    workflow_store.update(
        case_id=42009,
        expected_revision=1,
        status="review_complete",
        disposition="suspicious",
        note="old completed decision",
        current_fingerprint=old_fingerprint,
    )

    masked = workflow_store.get(42009, new_fingerprint)
    assert masked["status"] == "unreviewed"
    assert masked["disposition"] is None
    assert masked["note"] == ""
    assert masked["revision"] == 2
    assert masked["evidence_compatible"] is False

    restarted = workflow_store.update(
        case_id=42009,
        expected_revision=2,
        status="in_review",
        disposition=None,
        note="",
        current_fingerprint=new_fingerprint,
    )
    assert restarted["status"] == "in_review"
    assert restarted["revision"] == 3
    assert restarted["evidence_compatible"] is True
    current_activity = workflow_store.activity(42009, new_fingerprint)
    assert [event["event_type"] for event in current_activity] == [
        "evidence_review_restarted"
    ]
    assert workflow_store.activity(42009, old_fingerprint)[0]["event_type"] == "review_completed"


def test_completed_review_must_be_reopened_before_it_can_be_changed(workflow_store):
    fingerprint = "a" * 64
    workflow_store.update(
        case_id=42009,
        expected_revision=0,
        status="in_review",
        disposition=None,
        note="",
        current_fingerprint=fingerprint,
    )
    workflow_store.update(
        case_id=42009,
        expected_revision=1,
        status="review_complete",
        disposition="suspicious",
        note="closed",
        current_fingerprint=fingerprint,
    )

    with pytest.raises(WorkflowTransitionError, match="review_complete"):
        workflow_store.update(
            case_id=42009,
            expected_revision=2,
            status="review_complete",
            disposition="not_suspicious",
            note="silently rewritten",
            current_fingerprint=fingerprint,
        )
