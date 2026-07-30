"""Operational evidence serialization for the local dashboard.

The recorded G5 artifact keeps its historical evidence text unchanged. Live replay
uses this stricter serializer so transaction identifiers and model values never
leave the application boundary for Ollama.
"""

from __future__ import annotations


def serialize_operational_evidence(record: dict) -> str:
    """Render only the allowlisted coarse bucket and ranked SHAP directions."""

    lines = [
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
    return "\n".join(lines)
