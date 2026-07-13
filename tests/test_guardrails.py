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
        (
            GOOD.replace(
                "V10 increases risk for this transaction, while V14 decreases risk",
                "V10 increases risk, while V14 decreases risk, because cardholder behavior is suspicious",
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


def test_ambiguous_allowed_feature_is_grounded_but_has_no_direction():
    text = GOOD.replace("V10 increases risk", "V10 is relevant")
    result = validate_narrative(text, RECORD, KNOWN)
    assert result.checks["grounding"] is True
    assert result.checks["direction"] is False
    assert result.fallback


def test_missing_action_is_only_a_format_failure_when_content_is_faithful():
    text = GOOD.replace("\nACTION: Recommended for manual review.", "")
    result = validate_narrative(text, RECORD, KNOWN)
    assert result.checks == {
        "format": False,
        "completeness": True,
        "grounding": True,
        "direction": True,
    }


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
        GOOD.replace("V10 increases risk", "V10 increases the risk"),
        GOOD.replace(
            "V10 increases risk for this transaction, while V14 decreases risk",
            "V10 increases risk, while V14 decreases risk",
        ),
        GOOD.replace("V10 increases risk", "V10 raises risk").replace(
            "V14 decreases risk",
            "V14 lowers risk",
            1,
        ),
        GOOD.replace(
            "V10 increases risk for this transaction, while V14 decreases risk",
            "Together, V10 increases risk; V14 decreases risk",
        ),
        GOOD.replace(
            "V10 increases risk for this transaction, while V14 decreases risk",
            "Overall, V10 increases risk, whereas V14 decreases risk",
        ),
        GOOD.replace(
            "V10 increases risk for this transaction, while V14 decreases risk",
            "V10 increases risk, but V14 decreases risk",
        ),
        GOOD.replace("\nEVIDENCE:\n", "\n\nEVIDENCE:\n").replace(
            "\nACTION:", "\n\nACTION:"
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
        GOOD.replace("V10 increases risk", "V10 hardly increases risk"),
        GOOD.replace("V10 increases risk", "V10 fails to increase risk"),
    ],
)
def test_adversarial_pass_seeking_narratives_are_rejected(bad):
    assert validate_narrative(bad, RECORD, KNOWN).fallback


def test_same_direction_features_may_share_an_explicit_plural_direction():
    record = {
        **RECORD,
        "codes": [
            {**RECORD["codes"][0], "direction": "increases_risk"},
            RECORD["codes"][1],
        ],
    }
    text = """NARRATIVE: This case is rated High risk. V14 and V10 increase risk.
EVIDENCE:
- V14 - increases risk
- V10 - increases risk
ACTION: Recommended for manual review."""
    assert validate_narrative(text, record, KNOWN).ok


def test_presence_contribution_paraphrase_is_accepted():
    record = {
        **RECORD,
        "codes": [
            {**RECORD["codes"][0], "direction": "increases_risk"},
            RECORD["codes"][1],
        ],
    }
    text = """NARRATIVE: This case is rated High risk. The presence of V14 and V10 all contribute to an increased risk.

EVIDENCE:
- V14 - increases risk
- V10 - increases risk

ACTION: Recommended for manual review."""
    assert validate_narrative(text, record, KNOWN).ok


@pytest.mark.parametrize(
    "second_sentence",
    [
        "V14, V10, and V12 increase risk.",
        "This case is rated High risk due to V14 increasing risk, V10 increasing risk, and V12 increasing risk.",
        "V14 and V10 increase risk, while V12 also increases risk.",
    ],
)
def test_safe_grouped_llm_phrasings_are_accepted(second_sentence):
    record = {
        **RECORD,
        "codes": [
            {**RECORD["codes"][0], "direction": "increases_risk"},
            RECORD["codes"][1],
            {"feature": "V12", "direction": "increases_risk", "rank": 3},
        ],
    }
    text = f"""NARRATIVE: This case is rated High risk. {second_sentence}
EVIDENCE:
- V14 - increases risk
- V10 - increases risk
- V12 - increases risk
ACTION: Recommended for manual review."""
    assert validate_narrative(text, record, KNOWN).ok
