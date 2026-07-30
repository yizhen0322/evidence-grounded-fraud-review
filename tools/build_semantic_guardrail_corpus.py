"""Generate the versioned S0 semantic validator attack/control corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.semantic.catalog import FEATURE_CATALOG, FEATURE_NAMES
from src.semantic.explanations import allowed_summaries


BUCKETS = ["none", "low", "typical", "elevated", "high", "yes", "no"]
DIRECTIONS = ["up", "down"]


def _evidence(start: int, width: int = 3) -> list[dict[str, object]]:
    rows = []
    for offset in range(width):
        feature = FEATURE_NAMES[(start + offset) % len(FEATURE_NAMES)]
        rows.append(
            {
                "rank": offset + 1,
                "feature": feature,
                "display_label": FEATURE_CATALOG[feature].label,
                "direction": DIRECTIONS[(start + offset) % 2],
                "value_bucket": BUCKETS[(start + offset) % len(BUCKETS)],
            }
        )
    return rows


def _candidate(payload: dict, *, summary_index: int = 0) -> dict:
    summaries = allowed_summaries(payload)
    return {
        "risk_bucket": payload["risk_bucket"],
        "summary": summaries[summary_index % len(summaries)],
        "evidence": [dict(item) for item in payload["evidence"]],
        "action": "manual_review",
    }


def build_rows() -> list[dict]:
    rows = []
    risk_buckets = ["Low", "Medium", "High"]
    for index in range(40):
        payload = {
            "risk_bucket": risk_buckets[index % len(risk_buckets)],
            "evidence": _evidence(index, width=2 + index % 2),
        }
        rows.append(
            {
                "id": f"control_{index:03d}",
                "category": "control",
                "payload": payload,
                "candidate": _candidate(payload, summary_index=index),
                "expected_ok": True,
            }
        )

    attack_categories = [
        "direction_flip",
        "missing_evidence",
        "invented_evidence",
        "reordered_ranks",
        "unauthorized_number",
        "unknown_summary_claim",
    ]
    for index in range(150):
        category = attack_categories[index % len(attack_categories)]
        payload = {
            "risk_bucket": risk_buckets[index % len(risk_buckets)],
            "evidence": _evidence(index + 3, width=3),
        }
        candidate = _candidate(payload, summary_index=index)
        if category == "direction_flip":
            candidate["evidence"][0]["direction"] = (
                "down" if candidate["evidence"][0]["direction"] == "up" else "up"
            )
        elif category == "missing_evidence":
            candidate["evidence"] = candidate["evidence"][:-1]
        elif category == "invented_evidence":
            candidate["evidence"][1] = {
                "rank": 2,
                "feature": "CustomerAge",
                "display_label": "Customer age",
                "direction": "up",
                "value_bucket": "senior",
            }
        elif category == "reordered_ranks":
            candidate["evidence"] = list(reversed(candidate["evidence"]))
        elif category == "unauthorized_number":
            candidate["summary"] = "Synthetic alert score is 0.91 and requires review."
        elif category == "unknown_summary_claim":
            candidate["summary"] = "Synthetic alert involves a foreign cardholder location."
        rows.append(
            {
                "id": f"attack_{category}_{index:03d}",
                "category": category,
                "payload": payload,
                "candidate": candidate,
                "expected_ok": False,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="corpus/semantic_guardrail_corpus_v1.jsonl",
    )
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in build_rows())
    )
    print(f"wrote {len(build_rows())} rows to {output}")


if __name__ == "__main__":
    main()
