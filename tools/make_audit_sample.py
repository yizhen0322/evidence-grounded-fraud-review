"""Create a blinded, human-only audit sheet from delivered G5 narratives."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

AUDIT_COLUMNS = [
    "case_id",
    "arm",
    "evidence",
    "delivered_text",
    "violation_found",
    "violation_category",
    "notes",
]


def make_audit_sample(
    g5_run: str | Path,
    *,
    arm: str = "strict",
    n: int = 50,
    seed: int = 42,
    output: str | Path | None = None,
) -> Path:
    if n <= 0:
        raise ValueError("audit sample size must be positive")
    run = Path(g5_run)
    rows = [
        json.loads(line)
        for line in (run / "narratives.jsonl").read_text().splitlines()
        if line.strip()
    ]
    accepted = [
        {
            "case_id": row["case_id"],
            "arm": row["arm"],
            "evidence": row["evidence"],
            "delivered_text": row["final_text"],
        }
        for row in rows
        if row["arm"] == arm and not row["fallback"]
    ]
    if not accepted:
        raise ValueError(f"no accepted narratives available for arm {arm}")
    frame = pd.DataFrame(accepted)
    frame = frame.sample(n=min(n, len(frame)), random_state=seed).reset_index(drop=True)
    for column in ["violation_found", "violation_category", "notes"]:
        frame[column] = ""
    frame = frame[AUDIT_COLUMNS]

    destination = (
        Path(output)
        if output is not None
        else Path("experiments/audit") / f"{run.name}_{arm}_audit_sample.csv"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)
    print(f"{len(frame)} blank human-audit rows -> {destination}")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--g5-run", required=True)
    parser.add_argument("--arm", default="strict")
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output")
    arguments = parser.parse_args()
    make_audit_sample(
        arguments.g5_run,
        arm=arguments.arm,
        n=arguments.n,
        seed=arguments.seed,
        output=arguments.output,
    )


if __name__ == "__main__":
    main()
