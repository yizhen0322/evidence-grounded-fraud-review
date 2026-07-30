"""Build the versioned S0 semantic validator calibration artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.semantic.explanations import calibrate_validator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus",
        default="corpus/semantic_guardrail_corpus_v1.jsonl",
    )
    parser.add_argument(
        "--output",
        default="experiments/calibration/semantic_validator_calibration_v1.json",
    )
    args = parser.parse_args()
    artifact = calibrate_validator(args.corpus)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    print(f"semantic validator calibration written to {output}")


if __name__ == "__main__":
    main()
