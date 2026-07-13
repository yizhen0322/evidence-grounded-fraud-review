from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "preset,target_check",
    [
        ("direction_flip", "direction"),
        ("unlisted_feature", "grounding"),
        ("template_corruption", "format"),
    ],
)
def test_guardrail_lab_uses_real_validator_and_activates_fallback(
    api_client,
    preset: str,
    target_check: str,
):
    response = api_client.post(
        "/api/v1/guardrails/demo",
        json={"case_id": 42009, "preset": preset},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["validator"] == "src.narratives.guardrails.validate_narrative"
    assert payload["checks"][target_check] == "FAIL"
    assert payload["fallback"] is True
    assert payload["final_text"].startswith("Risk level: High")
    assert payload["original_text"] != payload["tampered_text"]


def test_guardrail_lab_rejects_arbitrary_text_and_unknown_presets(api_client):
    arbitrary = api_client.post(
        "/api/v1/guardrails/demo",
        json={
            "case_id": 42009,
            "preset": "direction_flip",
            "text": "arbitrary",
        },
    )
    assert arbitrary.status_code == 422
    unknown = api_client.post(
        "/api/v1/guardrails/demo",
        json={"case_id": 42009, "preset": "../../etc/passwd"},
    )
    assert unknown.status_code == 422
