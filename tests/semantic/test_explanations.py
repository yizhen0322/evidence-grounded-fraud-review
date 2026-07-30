import copy

from src.semantic.explanations import (
    SemanticLLMUnavailable,
    allowed_summaries,
    build_explanation_row,
    calibrate_validator,
    risk_bucket,
    validate_structured_brief,
)


def _payload():
    return {
        "risk_bucket": "High",
        "evidence": [
            {
                "rank": 1,
                "feature": "TransactionAmount",
                "display_label": "Transaction amount",
                "direction": "up",
                "value_bucket": "high",
            },
            {
                "rank": 2,
                "feature": "DuringNight",
                "display_label": "Night-time transaction",
                "direction": "up",
                "value_bucket": "yes",
            },
            {
                "rank": 3,
                "feature": "TerminalFraudRisk7Day",
                "display_label": "Delayed terminal fraud rate",
                "direction": "down",
                "value_bucket": "low",
            },
        ],
    }


def _candidate():
    payload = _payload()
    return {
        "risk_bucket": "High",
        "summary": allowed_summaries(payload)[0],
        "evidence": copy.deepcopy(payload["evidence"]),
        "action": "manual_review",
    }


def test_structured_validator_accepts_exact_payload():
    result = validate_structured_brief(_candidate(), _payload())

    assert result.ok is True
    assert result.fallback_reason is None


def test_risk_bucket_uses_relative_above_threshold_margin():
    assert risk_bucket(0.98, 0.97) == "Medium"
    assert risk_bucket(0.995, 0.97) == "High"
    assert risk_bucket(0.975, 0.97) == "Low"
    assert risk_bucket(0.96, 0.97) == "Low"


def test_structured_validator_rejects_attacks():
    attacks = []

    direction_flip = _candidate()
    direction_flip["evidence"][0]["direction"] = "down"
    attacks.append(direction_flip)

    missing = _candidate()
    missing["evidence"] = missing["evidence"][:2]
    attacks.append(missing)

    invented = _candidate()
    invented["evidence"][1]["feature"] = "CustomerAge"
    attacks.append(invented)

    invented_field = _candidate()
    invented_field["evidence"][0]["merchant_country"] = "foreign"
    attacks.append(invented_field)

    reordered = _candidate()
    reordered["evidence"] = list(reversed(reordered["evidence"]))
    attacks.append(reordered)

    numbered = _candidate()
    numbered["summary"] = "The case has score 0.91 and should be reviewed."
    attacks.append(numbered)

    malformed = "not-json"
    attacks.append(malformed)

    for candidate in attacks:
        assert validate_structured_brief(candidate, _payload()).ok is False


def test_transport_failure_delivers_deterministic_fallback(monkeypatch):
    def fail_request(*_args, **_kwargs):
        raise SemanticLLMUnavailable("connection refused")

    monkeypatch.setattr("src.semantic.explanations.request_structured_brief", fail_request)
    prediction = {
        "case_id": 10,
        "transaction_id": "TX10",
        "score": 0.9,
    }
    reason = {
        "case_id": 10,
        "transaction_id": "TX10",
        "codes": [
            {
                "rank": item["rank"],
                "key": item["feature"],
                "feature": item["feature"],
                "label": item["display_label"],
                "direction": "increases_risk" if item["direction"] == "up" else "decreases_risk",
                "coarse_bucket": item["value_bucket"],
                "shap_value": 1.0,
            }
            for item in _payload()["evidence"]
        ],
    }

    row, summary = build_explanation_row(
        prediction,
        reason,
        threshold=0.5,
        llm_config={"enabled": True},
        seed=42,
    )

    assert row["delivery"] == "deterministic_fallback"
    assert row["fallback_reason"] == "transport_unavailable"
    assert summary["transport_failures"] == 1
    assert "Transaction amount" in row["delivered_brief"]


def test_versioned_semantic_validator_corpus_calibrates():
    artifact = calibrate_validator("corpus/semantic_guardrail_corpus_v1.jsonl")

    assert artifact["passed"] is True
    assert artifact["corpus_version"] == "semantic_guardrail_corpus_v1"
    assert artifact["control_acceptance"]["n"] >= 40
    assert artifact["attack_interception"]["n"] >= 150
    assert artifact["control_acceptance"]["rate"] == 1.0
    assert artifact["attack_interception"]["rate"] == 1.0
