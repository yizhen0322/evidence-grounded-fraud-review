"""Calibrate the deterministic narrative validator on a labeled corpus."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.stats import wilson_ci
from src.narratives.guardrails import CALIBRATED_KNOWN_FEATURES, validate_narrative
from src.provenance import sha256_file

KNOWN = CALIBRATED_KNOWN_FEATURES


def _rate(successes: int, n: int) -> dict:
    lower, upper = wilson_ci(successes, n)
    return {
        "rate": successes / n if n else 0.0,
        "n": n,
        "ci95": [round(lower, 4), round(upper, 4)],
    }


def calibrate(path: str | Path) -> tuple[dict, list[int]]:
    items = [
        json.loads(line)
        for line in Path(path).read_text().splitlines()
        if line.strip()
    ]
    by_category: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    failures: list[int] = []
    for item in items:
        rejected = validate_narrative(item["text"], item["record"], KNOWN).fallback
        correct = rejected == (item["expected"] == "reject")
        key = (item["kind"], item["category"])
        by_category[key][0] += int(correct)
        by_category[key][1] += 1
        if not correct:
            failures.append(int(item["corpus_id"]))

    report = {
        "corpus": str(path),
        "corpus_sha256": sha256_file(path),
        "n_items": len(items),
        "instrument": "src/narratives/guardrails.py",
        "instrument_sha256": sha256_file("src/narratives/guardrails.py"),
        "candidate_preprocessing": {
            "mode": "identity_raw_text",
            "source": "src/narratives/llm_client.py",
            "source_sha256": sha256_file("src/narratives/llm_client.py"),
        },
        "corpus_builder": "tools/build_guardrail_corpus.py",
        "corpus_builder_sha256": sha256_file(
            "tools/build_guardrail_corpus.py"
        ),
        "known_features": KNOWN,
        "scope": (
            "Synthetic, template-constrained adversarial calibration. Rates describe "
            "this versioned corpus only; they do not estimate real LLM prevalence."
        ),
        "categories": {},
    }
    for (kind, category), (correct, n) in sorted(by_category.items()):
        metric = "interception_rate" if kind == "attack" else "acceptance_rate"
        report["categories"][f"{kind}/{category}"] = {metric: _rate(correct, n)}

    attack_correct = sum(
        correct
        for (kind, _), (correct, _n) in by_category.items()
        if kind == "attack"
    )
    attack_n = sum(
        n for (kind, _), (_correct, n) in by_category.items() if kind == "attack"
    )
    faithful_correct = sum(
        correct
        for (kind, _), (correct, _n) in by_category.items()
        if kind == "faithful"
    )
    faithful_n = sum(
        n for (kind, _), (_correct, n) in by_category.items() if kind == "faithful"
    )
    report["overall"] = {
        "attack_interception": _rate(attack_correct, attack_n),
        "false_rejection": _rate(faithful_n - faithful_correct, faithful_n),
        "failed_corpus_ids": failures,
        "gate_passed": not failures,
    }
    return report, failures


def main(
    path: str = "corpus/guardrail_corpus_v1.jsonl",
    output: str = "experiments/calibration/validator_calibration_v1.json",
) -> int:
    report, failures = calibrate(path)
    for key, result in report["categories"].items():
        metric = next(iter(result.values()))
        status = "PASS" if metric["rate"] == 1.0 else "FAIL"
        print(f"{status}: {key} {round(metric['rate'] * metric['n'])}/{metric['n']}")
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"calibration -> {destination}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
