"""Public API input schemas and stable validation-state helpers."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CheckState(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LiveNarrativeRequest(StrictRequest):
    case_id: int = Field(ge=0)


class GuardrailDemoRequest(StrictRequest):
    case_id: int = Field(ge=0)
    preset: Literal[
        "direction_flip",
        "unlisted_feature",
        "template_corruption",
    ]


class WorkflowUpdateRequest(StrictRequest):
    revision: int = Field(ge=0)
    status: Literal[
        "unreviewed",
        "in_review",
        "needs_follow_up",
        "review_complete",
    ]
    disposition: Literal[
        "suspicious",
        "not_suspicious",
        "inconclusive",
    ] | None = None
    note: str = Field(default="", max_length=2000)


def check_states(checks: dict[str, bool] | None) -> dict[str, str]:
    keys = ("format", "completeness", "grounding", "direction")
    if checks is None:
        return {key: CheckState.NOT_RUN.value for key in keys}
    return {
        key: (CheckState.PASS.value if bool(checks[key]) else CheckState.FAIL.value)
        for key in keys
    }
