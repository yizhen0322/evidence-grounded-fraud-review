"""Deterministic attacks for the S0 semantic guardrail demonstration."""

from __future__ import annotations

import copy
import json
from typing import Any

from app.backend.schemas import check_states
from app.backend.semantic_artifacts import SemanticSnapshot
from src.semantic.catalog import FEATURE_CATALOG
from src.semantic.explanations import allowed_summaries, validate_structured_brief


FAILURE_MESSAGES = {
    "format": "The required structured JSON schema was not preserved.",
    "completeness": "The ranked evidence list is missing, duplicated, or out of order.",
    "grounding": "The candidate contains evidence that is not in this S0 case payload.",
    "direction": "At least one evidence direction contradicts the recorded S0 contribution.",
}


def _display(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def _candidate(payload: dict[str, Any], summary: str) -> dict[str, Any]:
    candidate = {
        "risk_bucket": payload["risk_bucket"],
        "summary": summary,
        "evidence": copy.deepcopy(payload["evidence"]),
        "action": "manual_review",
    }
    result = validate_structured_brief(candidate, payload)
    if result.ok:
        return candidate
    for fallback_summary in allowed_summaries(payload):
        candidate["summary"] = fallback_summary
        result = validate_structured_brief(candidate, payload)
        if result.ok:
            return candidate
    raise RuntimeError("semantic guardrail demo requires a faithful base candidate")


def _direction_flip(candidate: dict[str, Any]) -> dict[str, Any]:
    tampered = copy.deepcopy(candidate)
    first = tampered["evidence"][0]
    first["direction"] = "down" if first["direction"] == "up" else "up"
    return tampered


def _unlisted_feature(candidate: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    tampered = copy.deepcopy(candidate)
    listed = {item["feature"] for item in payload["evidence"]}
    injected = next((key for key in FEATURE_CATALOG if key not in listed), None)
    if injected is None:
        raise RuntimeError("no known unlisted semantic feature is available for this case")
    tampered["evidence"][0]["feature"] = injected
    tampered["evidence"][0]["display_label"] = FEATURE_CATALOG[injected].label
    return tampered


def _template_corruption(candidate: dict[str, Any]) -> dict[str, Any]:
    tampered = copy.deepcopy(candidate)
    tampered.pop("action", None)
    return tampered


def run_semantic_attack(
    snapshot: SemanticSnapshot,
    case_id: str,
    preset: str,
) -> dict[str, Any]:
    case = snapshot.case(str(case_id))
    payload = dict(case.briefs.minimized_llm_payload)
    base = _candidate(payload, case.briefs.guarded_llm)

    if preset == "direction_flip":
        tampered = _direction_flip(base)
        target = "direction"
    elif preset == "unlisted_feature":
        tampered = _unlisted_feature(base, payload)
        target = "grounding"
    elif preset == "template_corruption":
        tampered = _template_corruption(base)
        target = "format"
    else:
        raise ValueError(f"unknown semantic guardrail preset: {preset}")

    result = validate_structured_brief(tampered, payload)
    if result.checks[target] or result.ok:
        raise RuntimeError(f"deterministic semantic {preset} did not trigger {target}")
    failed = [key for key, passed in result.checks.items() if not passed]
    return {
        "mode": "operational_guardrail_demo",
        "reported": False,
        "case_id": int(case.case_id) if case.case_id.isdigit() else case.case_id,
        "preset": preset,
        "original_text": _display(base),
        "tampered_text": _display(tampered),
        "checks": check_states(result.checks),
        "check_reasons": {key: FAILURE_MESSAGES[key] for key in failed},
        "failure_reasons": {key: FAILURE_MESSAGES[key] for key in failed},
        "fallback": True,
        "fallback_reason": result.fallback_reason,
        "final_text": case.briefs.deterministic,
        "validator": "src.semantic.explanations.validate_structured_brief",
    }
