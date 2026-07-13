from src.narratives.evidence import allowed_features, serialize_evidence


RECORD = {
    "case_id": 7,
    "score": 0.97,
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
        {
            "feature": "Amount",
            "direction": "increases_risk",
            "rank": 3,
            "shap_value": 0.3,
        },
    ],
}


def test_serialization_contains_directions_but_no_values():
    text = serialize_evidence(RECORD, anomaly_level="Medium")
    assert "High" in text and "V14" in text
    assert "decreases risk" in text and "increases risk" in text
    assert "AE anomaly level: Medium" in text
    assert "0.97" not in text and "-1.2" not in text


def test_features_and_output_follow_rank_not_input_order():
    shuffled = dict(RECORD, codes=list(reversed(RECORD["codes"])))
    assert allowed_features(shuffled) == ["V14", "V10", "Amount"]
    text = serialize_evidence(shuffled)
    assert text.index("1. V14") < text.index("2. V10") < text.index("3. Amount")
