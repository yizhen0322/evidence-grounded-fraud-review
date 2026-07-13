"""Deterministic server-side attacks for the guardrail demonstration."""

from __future__ import annotations

from typing import Any

from app.backend.artifacts import DashboardSnapshot
from app.backend.schemas import check_states
from src.narratives.guardrails import validate_narrative


FAILURE_MESSAGES = {
    "format": "The required NARRATIVE / EVIDENCE / ACTION template was not preserved.",
    "completeness": "The ranked evidence list is missing, duplicated, or out of order.",
    "grounding": "The text contains a feature that is not in this case's recorded evidence.",
    "direction": "At least one feature direction contradicts the recorded SHAP contribution.",
}


def _direction_flip(text: str, record: dict[str, Any]) -> str:
    first = min(record["codes"], key=lambda code: code["rank"])
    old_direction = (
        "increases risk" if first["direction"] == "increases_risk" else "decreases risk"
    )
    new_direction = "decreases risk" if old_direction == "increases risk" else "increases risk"
    old = f"- {first['feature']} - {old_direction}"
    new = f"- {first['feature']} - {new_direction}"
    if old not in text:
        raise RuntimeError("faithful base narrative lacks the expected first evidence bullet")
    return text.replace(old, new, 1)


def _unlisted_feature(
    text: str,
    record: dict[str, Any],
    known_features: tuple[str, ...],
) -> str:
    listed = {code["feature"] for code in record["codes"]}
    injected = next(
        (
            feature
            for feature in known_features
            if feature not in listed and (feature.startswith("V") or "_" in feature)
        ),
        None,
    )
    if injected is None:
        injected = next((feature for feature in known_features if feature not in listed), None)
    if injected is None:
        raise RuntimeError("no known unlisted feature is available for this case")
    marker = "\n\nACTION: Recommended for manual review."
    if marker not in text:
        raise RuntimeError("faithful base narrative lacks the ACTION section")
    return text.replace(
        marker,
        f"\n- {injected} - increases risk{marker}",
        1,
    )


def _template_corruption(text: str) -> str:
    marker = "\nACTION: Recommended for manual review."
    if marker not in text:
        raise RuntimeError("faithful base narrative lacks the ACTION section")
    return text.replace(marker, "", 1)


def run_attack(
    snapshot: DashboardSnapshot,
    case_id: int,
    preset: str,
) -> dict[str, Any]:
    case = snapshot.case(case_id)
    record = case.guardrail_record()
    original = case.narrative.final_text
    original_result = validate_narrative(original, record, list(snapshot.known_features))
    if not original_result.ok:
        raise RuntimeError("guardrail demo requires a currently faithful recorded base narrative")

    if preset == "direction_flip":
        tampered = _direction_flip(original, record)
        target = "direction"
    elif preset == "unlisted_feature":
        tampered = _unlisted_feature(original, record, snapshot.known_features)
        target = "grounding"
    elif preset == "template_corruption":
        tampered = _template_corruption(original)
        target = "format"
    else:
        raise ValueError(f"unknown guardrail preset: {preset}")

    result = validate_narrative(tampered, record, list(snapshot.known_features))
    if result.checks[target] or not result.fallback:
        raise RuntimeError(f"deterministic {preset} did not trigger the required guardrail")
    failed = [key for key, passed in result.checks.items() if not passed]
    return {
        "case_id": case.case_id,
        "preset": preset,
        "original_text": original,
        "tampered_text": tampered,
        "checks": check_states(result.checks),
        "failure_reasons": {key: FAILURE_MESSAGES[key] for key in failed},
        "fallback": result.fallback,
        "final_text": result.final_text,
        "validator": "src.narratives.guardrails.validate_narrative",
    }
