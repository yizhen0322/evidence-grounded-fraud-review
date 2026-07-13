"""Serialize the minimal evidence package supplied to the local LLM."""

from __future__ import annotations


def allowed_features(record: dict) -> list[str]:
    """Return ranked SHAP feature identifiers without exposing values."""
    return [code["feature"] for code in sorted(record["codes"], key=lambda item: item["rank"])]


def serialize_evidence(record: dict, anomaly_level: str | None = None) -> str:
    """Render feature names, ranks, directions, and coarse buckets only."""
    lines = [
        f"Case ID: {record['case_id']}",
        f"Risk level: {record['risk_bucket']}",
        "Top contributing features (ranked):",
    ]
    for code in sorted(record["codes"], key=lambda item: item["rank"]):
        direction = (
            "increases risk"
            if code["direction"] == "increases_risk"
            else "decreases risk"
        )
        lines.append(f"{code['rank']}. {code['feature']} - {direction}")
    if anomaly_level is not None:
        lines.append(f"AE anomaly level: {anomaly_level}")
    return "\n".join(lines)
