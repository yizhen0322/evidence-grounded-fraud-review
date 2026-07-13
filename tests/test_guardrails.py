import pytest

from src.narratives.guardrails import fallback_text, validate_narrative


RECORD = {
    "case_id": 7,
    "risk_bucket": "High",
    "codes": [
        {
            "feature": "V14",
            "direction": "decreases_risk",
            "rank": 1,
            "shap_value": -1.2,
        },
        {
            "feature": "V10",
            "direction": "increases_risk",
            "rank": 2,
            "shap_value": 0.8,
        },
    ],
}
KNOWN = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount", "recon_error"]

GOOD = """NARRATIVE: This case is rated High risk. V10 increases risk for this transaction, while V14 decreases risk.
EVIDENCE:
- V14 - decreases risk
- V10 - increases risk
ACTION: Recommended for manual review."""


def test_good_narrative_passes_all_checks():
    result = validate_narrative(GOOD, RECORD, KNOWN)
    assert result.ok and not result.fallback and result.final_text == GOOD
    assert result.checks == {
        "format": True,
        "completeness": True,
        "grounding": True,
        "direction": True,
    }


@pytest.mark.parametrize(
    ("bad", "failed_check"),
    [
        (GOOD.replace("while V14 decreases risk", "and V27 increases risk"), "grounding"),
        (GOOD.replace("V14 decreases risk", "V14 increases risk"), "direction"),
        ("just some text", "format"),
        (GOOD.replace("- V14 - decreases risk\n", ""), "completeness"),
        (GOOD.replace("V10 increases risk", "V10 is relevant"), "direction"),
        (
            GOOD.replace(
                "This case is rated High risk.",
                "This case has 91.7% fraud probability.",
            ),
            "format",
        ),
        (
            GOOD.replace(
                "V10 increases risk for this transaction",
                "V10 increases risk and merchant_score increases risk",
            ),
            "grounding",
        ),
        (GOOD.replace("High risk", "Low risk", 1), "grounding"),
    ],
)
def test_unfaithful_or_malformed_narratives_fail_closed(bad, failed_check):
    result = validate_narrative(bad, RECORD, KNOWN)
    assert result.checks[failed_check] is False
    assert result.fallback
    assert result.final_text == fallback_text(RECORD)


def test_fallback_text_lists_codes_in_rank_order():
    text = fallback_text(RECORD)
    assert text.index("V14") < text.index("V10") and "High" in text


@pytest.mark.parametrize(
    "text",
    [
        GOOD.replace("while V14 decreases risk", "and V14 decreases risk"),
        GOOD.replace(
            "V10 increases risk for this transaction, while V14 decreases risk",
            "Both V14 decreases risk and V10 increases risk for this transaction",
        ),
    ],
)
def test_faithful_conjunctions_are_not_false_rejected(text):
    assert validate_narrative(text, RECORD, KNOWN).ok


@pytest.mark.parametrize(
    "bad",
    [
        GOOD.replace("V10 increases risk", "V10 does not increase risk"),
        GOOD.replace("V14 decreases risk", "V14 decreases risk and increases risk"),
        GOOD.replace("- V10 - increases risk", "- V10 - related to risk"),
        GOOD.replace("V10 increases risk", "V10 never increases risk"),
    ],
)
def test_adversarial_pass_seeking_narratives_are_rejected(bad):
    assert validate_narrative(bad, RECORD, KNOWN).fallback
