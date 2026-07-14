"""Local analyst workflow storage kept separate from immutable research artifacts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


WORKFLOW_STATUSES = (
    "unreviewed",
    "in_review",
    "needs_follow_up",
    "review_complete",
)
DISPOSITIONS = (
    "suspicious",
    "not_suspicious",
    "inconclusive",
)
ALLOWED_TRANSITIONS = {
    "unreviewed": {"in_review"},
    "in_review": {"in_review", "needs_follow_up", "review_complete"},
    "needs_follow_up": {"needs_follow_up", "in_review", "review_complete"},
    "review_complete": {"in_review"},
}


class WorkflowConflictError(RuntimeError):
    """Raised when a stale browser revision would overwrite newer work."""


class WorkflowTransitionError(ValueError):
    """Raised when a requested workflow transition violates the state machine."""


class WorkflowEvidenceMismatchError(RuntimeError):
    """Raised when saved workflow metadata belongs to another evidence chain."""


def evidence_fingerprint(public_provenance: dict) -> str:
    """Return a stable identifier for the configured detector/G4/G5 evidence chain."""

    fields = {
        name: {
            "run_id": public_provenance[name]["run_id"],
            "manifest_sha256": public_provenance[name]["manifest_sha256"],
        }
        for name in ("detector", "g4", "g5")
    }
    payload = json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _default_record(case_id: int) -> dict:
    return {
        "case_id": case_id,
        "status": "unreviewed",
        "disposition": None,
        "note": "",
        "revision": 0,
        "created_at": None,
        "updated_at": None,
        "evidence_compatible": True,
        "activity_count": 0,
    }


class WorkflowStore:
    """Small single-user SQLite store for local review metadata only."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS workflow_cases (
                    case_id INTEGER PRIMARY KEY,
                    status TEXT NOT NULL CHECK (
                        status IN ('unreviewed', 'in_review', 'needs_follow_up', 'review_complete')
                    ),
                    disposition TEXT CHECK (
                        disposition IS NULL OR disposition IN ('suspicious', 'not_suspicious', 'inconclusive')
                    ),
                    note TEXT NOT NULL DEFAULT '',
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    evidence_fingerprint TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workflow_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    from_status TEXT,
                    to_status TEXT NOT NULL,
                    disposition TEXT,
                    note_changed INTEGER NOT NULL CHECK (note_changed IN (0, 1)),
                    revision INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (case_id) REFERENCES workflow_cases(case_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS workflow_events_case_id_id
                ON workflow_events(case_id, id);
                """
            )

    @staticmethod
    def _record_payload(row: sqlite3.Row, *, activity_count: int = 0) -> dict:
        return {
            "case_id": row["case_id"],
            "status": row["status"],
            "disposition": row["disposition"],
            "note": row["note"],
            "revision": row["revision"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "evidence_compatible": True,
            "activity_count": activity_count,
        }

    def get(self, case_id: int, current_fingerprint: str) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM workflow_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
            if row is None:
                return _default_record(case_id)
            count = connection.execute(
                "SELECT COUNT(*) FROM workflow_events WHERE case_id = ?",
                (case_id,),
            ).fetchone()[0]
            payload = self._record_payload(row, activity_count=count)
            compatible = row["evidence_fingerprint"] == current_fingerprint
            payload["evidence_compatible"] = compatible
            if not compatible:
                payload.update(status="unreviewed", disposition=None, note="")
            return payload

    def list(self, case_ids: Iterable[int], current_fingerprint: str) -> list[dict]:
        ordered_ids = list(case_ids)
        if not ordered_ids:
            return []
        placeholders = ",".join("?" for _ in ordered_ids)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT workflow_cases.*, COUNT(workflow_events.id) AS activity_count
                FROM workflow_cases
                LEFT JOIN workflow_events ON workflow_events.case_id = workflow_cases.case_id
                WHERE workflow_cases.case_id IN ({placeholders})
                GROUP BY workflow_cases.case_id
                """,
                ordered_ids,
            ).fetchall()
        recorded = {row["case_id"]: row for row in rows}
        items: list[dict] = []
        for case_id in ordered_ids:
            row = recorded.get(case_id)
            if row is None:
                items.append(_default_record(case_id))
                continue
            payload = self._record_payload(row, activity_count=row["activity_count"])
            compatible = row["evidence_fingerprint"] == current_fingerprint
            payload["evidence_compatible"] = compatible
            if not compatible:
                payload.update(status="unreviewed", disposition=None, note="")
            items.append(payload)
        return items

    def activity(self, case_id: int) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, event_type, from_status, to_status, disposition,
                       note_changed, revision, created_at
                FROM workflow_events
                WHERE case_id = ?
                ORDER BY id DESC
                """,
                (case_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "from_status": row["from_status"],
                "to_status": row["to_status"],
                "disposition": row["disposition"],
                "note_changed": bool(row["note_changed"]),
                "revision": row["revision"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def update(
        self,
        *,
        case_id: int,
        expected_revision: int,
        status: str,
        disposition: str | None,
        note: str,
        current_fingerprint: str,
    ) -> dict:
        if status not in WORKFLOW_STATUSES:
            raise WorkflowTransitionError(f"unknown workflow status: {status}")
        if disposition is not None and disposition not in DISPOSITIONS:
            raise WorkflowTransitionError(f"unknown disposition: {disposition}")
        if status == "review_complete" and disposition is None:
            raise WorkflowTransitionError(
                "review_complete requires a provisional disposition"
            )

        now = _utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM workflow_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
            current_status = "unreviewed" if row is None else row["status"]
            current_revision = 0 if row is None else row["revision"]
            current_note = "" if row is None else row["note"]
            current_disposition = None if row is None else row["disposition"]
            evidence_mismatch = (
                row is not None
                and row["evidence_fingerprint"] != current_fingerprint
            )

            if expected_revision != current_revision:
                raise WorkflowConflictError(
                    f"stale workflow revision {expected_revision}; current revision is {current_revision}"
                )
            if evidence_mismatch and not (
                status == "in_review" and disposition is None and note == ""
            ):
                raise WorkflowEvidenceMismatchError(
                    "saved workflow metadata belongs to another evidence chain; restart the review with blank local fields"
                )

            transition_status = "unreviewed" if evidence_mismatch else current_status
            if status not in ALLOWED_TRANSITIONS[transition_status]:
                raise WorkflowTransitionError(
                    f"cannot transition workflow from {transition_status} to {status}"
                )

            revision = current_revision + 1
            created_at = now if row is None else row["created_at"]
            connection.execute(
                """
                INSERT INTO workflow_cases (
                    case_id, status, disposition, note, revision,
                    evidence_fingerprint, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    status = excluded.status,
                    disposition = excluded.disposition,
                    note = excluded.note,
                    revision = excluded.revision,
                    evidence_fingerprint = excluded.evidence_fingerprint,
                    updated_at = excluded.updated_at
                """,
                (
                    case_id,
                    status,
                    disposition,
                    note,
                    revision,
                    current_fingerprint,
                    created_at,
                    now,
                ),
            )

            event_type = "review_updated"
            if evidence_mismatch:
                event_type = "evidence_review_restarted"
            elif current_status == "unreviewed" and status == "in_review":
                event_type = "review_started"
            elif current_status == "review_complete" and status == "in_review":
                event_type = "review_reopened"
            elif status == "needs_follow_up" and current_status != status:
                event_type = "follow_up_requested"
            elif status == "review_complete" and current_status != status:
                event_type = "review_completed"

            connection.execute(
                """
                INSERT INTO workflow_events (
                    case_id, event_type, from_status, to_status, disposition,
                    note_changed, revision, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    event_type,
                    current_status,
                    status,
                    disposition,
                    int(note != current_note),
                    revision,
                    now,
                ),
            )

        payload = self.get(case_id, current_fingerprint)
        payload["disposition_changed"] = disposition != current_disposition
        return payload

    def table_columns(self) -> dict[str, list[str]]:
        """Expose schema names for regression tests, never through the public API."""

        with self._connect() as connection:
            return {
                table: [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
                for table in ("workflow_cases", "workflow_events")
            }
