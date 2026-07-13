"""Score a completed human audit sheet without changing its annotations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.stats import wilson_ci


def score_audit(
    filled_csv: str | Path,
    output: str | Path = "experiments/audit/audit_result.json",
) -> Path:
    source = Path(filled_csv)
    frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    if "violation_found" not in frame:
        raise ValueError("audit sheet is missing violation_found")
    normalized = frame["violation_found"].str.strip().str.lower()
    invalid = sorted(set(normalized) - {"yes", "no"})
    if invalid:
        raise ValueError(f"violation_found must contain only yes/no: {invalid}")
    violations = int((normalized == "yes").sum())
    n = int(len(frame))
    lower, upper = wilson_ci(violations, n)
    result = {
        "source_audit_sheet": str(source),
        "undetected_violation_rate": {
            "rate": violations / n if n else 0.0,
            "n": n,
            "ci95": [round(lower, 4), round(upper, 4)],
        },
        "n_violations": violations,
        "annotation_source": "human",
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"audit score -> {destination}")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("filled_csv")
    parser.add_argument("--output", default="experiments/audit/audit_result.json")
    arguments = parser.parse_args()
    score_audit(arguments.filled_csv, arguments.output)


if __name__ == "__main__":
    main()
