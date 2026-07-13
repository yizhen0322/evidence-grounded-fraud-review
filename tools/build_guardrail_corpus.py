"""Build the versioned labeled corpus used to calibrate narrative guardrails."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

KNOWN = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount", "recon_error"]
DIRWORD = {
    "increases_risk": "increases risk",
    "decreases_risk": "decreases risk",
}


def make_record(case_id: int, features: list[tuple[str, str]]) -> dict:
    return {
        "case_id": case_id,
        "risk_bucket": "High",
        "codes": [
            {
                "feature": feature,
                "direction": direction,
                "rank": index + 1,
                "shap_value": 1.0 if direction == "increases_risk" else -1.0,
            }
            for index, (feature, direction) in enumerate(features)
        ],
    }


def canonical_text(record: dict, joiner: str = ", while ") -> str:
    codes = sorted(record["codes"], key=lambda item: item["rank"])
    clauses = [f"{code['feature']} {DIRWORD[code['direction']]}" for code in codes]
    narrative = (
        f"This case is rated {record['risk_bucket']} risk. "
        + joiner.join(clauses)
        + "."
    )
    bullets = "\n".join(
        f"- {code['feature']} - {DIRWORD[code['direction']]}" for code in codes
    )
    return (
        f"NARRATIVE: {narrative}\nEVIDENCE:\n{bullets}\n"
        "ACTION: Recommended for manual review."
    )


def _narrative_with_clauses(record: dict, clauses: list[str]) -> str:
    good = canonical_text(record)
    prefix, remainder = good.split("\nEVIDENCE:\n", 1)
    narrative = (
        f"NARRATIVE: This case is rated {record['risk_bucket']} risk. "
        + ", while ".join(clauses)
        + "."
    )
    return f"{narrative}\nEVIDENCE:\n{remainder}"


def attacks_for(record: dict) -> list[tuple[str, str]]:
    good = canonical_text(record)
    codes = sorted(record["codes"], key=lambda item: item["rank"])
    first = codes[0]
    first_phrase = f"{first['feature']} {DIRWORD[first['direction']]}"
    opposite = (
        "decreases risk"
        if first["direction"] == "increases_risk"
        else "increases risk"
    )
    unlisted = next(
        feature
        for feature in KNOWN
        if feature not in {code["feature"] for code in codes}
    )
    remaining = [
        f"{code['feature']} {DIRWORD[code['direction']]}" for code in codes[1:]
    ]
    omitted = _narrative_with_clauses(
        record,
        remaining or ["the transaction profile is unusual"],
    )
    return [
        (
            "direction_flip",
            good.replace(first_phrase, f"{first['feature']} {opposite}", 1),
        ),
        (
            "negated_direction",
            good.replace(
                first_phrase,
                f"{first['feature']} does not "
                + DIRWORD[first["direction"]].replace("s risk", " risk"),
                1,
            ),
        ),
        (
            "ambiguous_direction",
            good.replace(first_phrase, f"{first['feature']} is relevant", 1),
        ),
        (
            "unsupported_known_feature",
            good.replace(
                first_phrase,
                f"{first_phrase} and {unlisted} increases risk",
                1,
            ),
        ),
        (
            "invented_feature",
            good.replace(
                first_phrase,
                f"{first_phrase} and merchant_score increases risk",
                1,
            ),
        ),
        ("omitted_evidence_narrative", omitted),
        (
            "omitted_evidence_bullet",
            good.replace(
                f"- {first['feature']} - {DIRWORD[first['direction']]}\n",
                "",
                1,
            ),
        ),
        (
            "unauthorized_number",
            good.replace(
                "This case is rated High risk.",
                "This case is rated High risk with 91.7% probability.",
                1,
            ),
        ),
        (
            "template_corruption",
            good.replace("ACTION: Recommended for manual review.", "", 1),
        ),
        (
            "risk_bucket_flip",
            good.replace("rated High risk", "rated Low risk", 1),
        ),
    ]


def faithful_for(record: dict) -> list[tuple[str, str]]:
    codes = sorted(record["codes"], key=lambda item: item["rank"])
    items = [
        ("canonical_while", canonical_text(record)),
        ("conjunction_and", canonical_text(record, joiner=", and ")),
    ]
    if len(codes) > 1:
        clauses = [
            f"{code['feature']} {DIRWORD[code['direction']]}"
            for code in reversed(codes)
        ]
        items.append(("narrative_reorder", _narrative_with_clauses(record, clauses)))
    return items


def build_items() -> list[dict]:
    rng = random.Random(42)
    pool = [feature for feature in KNOWN if feature != "Time"]
    records = []
    for index in range(20):
        count = rng.choice([2, 3])
        features = rng.sample(pool, count)
        directions = [
            rng.choice(["increases_risk", "decreases_risk"])
            for _ in features
        ]
        records.append(make_record(1000 + index, list(zip(features, directions))))
    records.append(
        make_record(
            2000,
            [("V1", "increases_risk"), ("V14", "decreases_risk")],
        )
    )

    items: list[dict] = []
    corpus_id = 0
    for record in records:
        for category, text in attacks_for(record):
            items.append(
                {
                    "corpus_id": corpus_id,
                    "kind": "attack",
                    "category": category,
                    "record": record,
                    "text": text,
                    "expected": "reject",
                }
            )
            corpus_id += 1
        for category, text in faithful_for(record):
            items.append(
                {
                    "corpus_id": corpus_id,
                    "kind": "faithful",
                    "category": category,
                    "record": record,
                    "text": text,
                    "expected": "accept",
                }
            )
            corpus_id += 1
    return items


def main(output: str = "corpus/guardrail_corpus_v1.jsonl") -> None:
    items = build_items()
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(item) + "\n" for item in items))
    attacks = sum(item["kind"] == "attack" for item in items)
    faithful = len(items) - attacks
    if attacks < 150 or faithful < 40:
        raise RuntimeError("guardrail corpus is below its minimum size")
    print(f"{len(items)} items -> {path} ({attacks} attacks, {faithful} faithful)")


if __name__ == "__main__":
    main(*sys.argv[1:])
