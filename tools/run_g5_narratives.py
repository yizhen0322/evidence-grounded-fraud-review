"""Run paired strict/simple G5 narrative generation and delivery-policy analysis."""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.stats import wilson_ci
from src.narratives.evidence import serialize_evidence
from src.narratives.guardrails import fallback_text, validate_narrative
from src.narratives.llm_client import LLMUnavailable, PROMPT_TEMPLATES, generate_narrative
from src.provenance import (
    assert_clean_repository,
    sha256_file,
    validate_run_manifest,
    write_run_manifest,
)

CHECK_KEYS = ("format", "completeness", "grounding", "direction")
DEFAULT_CALIBRATION = Path("experiments/calibration/validator_calibration_v1.json")
DEFAULT_CORPUS = Path("corpus/guardrail_corpus_v1.jsonl")


def load_g4_context(g4: Path) -> tuple[dict, list[dict], int, list[str]]:
    """Load a manifest-valid G4 run and preserve its detector feature contract."""
    manifest = validate_run_manifest(g4, expected_group="g4")
    records = [
        json.loads(line)
        for line in (g4 / "reason_codes.jsonl").read_text().splitlines()
        if line.strip()
    ]
    case_ids = [record["case_id"] for record in records]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("G4 reason codes require unique case_id values")
    known_features = list(manifest["feature_names"])
    for record in records:
        codes = sorted(record["codes"], key=lambda item: item["rank"])
        if [code["rank"] for code in codes] != list(range(1, len(codes) + 1)):
            raise ValueError("G4 reason-code ranks must be contiguous from one")
        if not {code["feature"] for code in codes}.issubset(known_features):
            raise ValueError("G4 reason codes contain a feature absent from the manifest")
    return manifest, records, int(manifest["seed"]), known_features


def parse_arms(value: str) -> list[str]:
    arms = [arm.strip() for arm in value.split(",") if arm.strip()]
    if not arms or len(arms) != len(set(arms)):
        raise ValueError("arms must be a non-empty, duplicate-free list")
    unknown = set(arms) - set(PROMPT_TEMPLATES)
    if unknown:
        raise ValueError(f"unknown prompt arms: {sorted(unknown)}")
    return arms


def g5_output_dir(
    seed: int,
    limit: int | None,
    today: datetime.date | None = None,
) -> Path:
    stamp = (today or datetime.date.today()).isoformat()
    if limit is not None:
        return (
            Path("experiments/tuning_runs")
            / f"{stamp}_g5_quick_seed{seed}_limit{limit}"
        )
    return Path("experiments/runs") / f"{stamp}_g5_seed{seed}"


def _rate_block(successes: int, n: int) -> dict:
    lower, upper = wilson_ci(successes, n)
    return {
        "rate": successes / n if n else 0.0,
        "n": n,
        "ci95": [round(lower, 4), round(upper, 4)],
    }


def summarize_arm(rows: list[dict]) -> dict:
    """Summarize detected violations OFF policy and delivery outcomes ON policy."""
    judged = [row for row in rows if row["checks"] is not None]
    judged_n = len(judged)
    total_n = len(rows)
    prevalence = {
        f"detected_{key}_violation": _rate_block(
            sum(not row["checks"][key] for row in judged),
            judged_n,
        )
        for key in CHECK_KEYS
    }
    prevalence["detected_any_violation"] = _rate_block(
        sum(not all(row["checks"].values()) for row in judged),
        judged_n,
    )
    delivered_n = sum(not row["fallback"] for row in rows)
    return {
        "n_cases": total_n,
        "n_guardrail_judged": judged_n,
        "llm_unavailable": _rate_block(total_n - judged_n, total_n),
        "off_policy_prevalence": prevalence,
        "on_policy_delivery": {
            "fallback": _rate_block(sum(row["fallback"] for row in rows), total_n),
            "residual_detected_violation_on_delivered": {
                **_rate_block(0, delivered_n),
                "by_construction": True,
                "note": (
                    "ON policy delivers only check-passing narratives; undetected "
                    "violations require the blinded human audit."
                ),
            },
            "mean_latency_seconds": (
                sum(row["latency_seconds"] for row in rows) / total_n
                if total_n
                else 0.0
            ),
        },
    }


def assert_calibration_gate(
    calibration_path: Path = DEFAULT_CALIBRATION,
    corpus_path: Path = DEFAULT_CORPUS,
) -> dict:
    """Reject stale or failed calibration before a reported G5 run."""
    report = json.loads(calibration_path.read_text())
    if not report.get("overall", {}).get("gate_passed"):
        raise ValueError("validator calibration gate has not passed")
    if report.get("overall", {}).get("failed_corpus_ids"):
        raise ValueError("validator calibration contains failed corpus items")
    if report.get("instrument_sha256") != sha256_file(
        "src/narratives/guardrails.py"
    ):
        raise ValueError("validator changed after calibration")
    if report.get("corpus_sha256") != sha256_file(corpus_path):
        raise ValueError("guardrail corpus changed after calibration")
    return report


def validate_g5_rows(rows: list[dict], records: list[dict], arms: list[str]) -> None:
    expected_ids = {record["case_id"] for record in records}
    pairs = [(row["case_id"], row["arm"]) for row in rows]
    if len(pairs) != len(set(pairs)):
        raise ValueError("G5 requires unique case_id/arm pairs")
    if set(row["arm"] for row in rows) != set(arms):
        raise ValueError("G5 rows do not cover every requested arm")
    for arm in arms:
        actual_ids = {row["case_id"] for row in rows if row["arm"] == arm}
        if actual_ids != expected_ids:
            raise ValueError(f"G5 {arm} case_id set differs from G4")


def run_g5(
    g4_run: str | Path,
    *,
    model: str = "llama3:8b",
    arms: list[str] | None = None,
    limit: int | None = None,
    timeout: int = 60,
    output: str | Path | None = None,
    require_clean: bool | None = None,
) -> Path:
    g4 = Path(g4_run)
    selected_arms = arms or ["strict", "simple"]
    if set(selected_arms) - set(PROMPT_TEMPLATES):
        raise ValueError("unknown prompt arm")
    _manifest, records, seed, known_features = load_g4_context(g4)
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        records = records[:limit]
    final_run = limit is None
    clean_required = final_run if require_clean is None else require_clean
    calibration = assert_calibration_gate()
    if clean_required:
        assert_clean_repository()
    destination = Path(output) if output is not None else g5_output_dir(seed, limit)
    destination.mkdir(parents=True, exist_ok=False)

    rows: list[dict] = []
    unavailable = 0
    for record in records:
        evidence = serialize_evidence(record)
        for arm in selected_arms:
            started = time.perf_counter()
            try:
                raw = generate_narrative(
                    evidence,
                    model=model,
                    timeout=timeout,
                    prompt_style=arm,
                )
                result = validate_narrative(raw, record, known_features)
            except LLMUnavailable:
                unavailable += 1
                raw = None
                result = None
            latency = time.perf_counter() - started
            failed_checks = (
                [key for key, passed in result.checks.items() if not passed]
                if result is not None
                else []
            )
            row = {
                "case_id": record["case_id"],
                "arm": arm,
                "evidence": evidence,
                "raw_output": raw,
                "checks": result.checks if result is not None else None,
                "fallback": result.fallback if result is not None else True,
                "fallback_reason": (
                    f"guardrail_failed:{','.join(failed_checks)}"
                    if result is not None and result.fallback
                    else "llm_unavailable"
                    if result is None
                    else None
                ),
                "final_text": (
                    result.final_text if result is not None else fallback_text(record)
                ),
                "latency_seconds": latency,
            }
            rows.append(row)
            status = "FALLBACK" if row["fallback"] else "ok"
            print(f"case {record['case_id']} [{arm}]: {status} ({latency:.2f}s)")

    validate_g5_rows(rows, records, selected_arms)
    faithfulness = {
        "model": model,
        "llm_unavailable_count": unavailable,
        "paired_design": (
            "Each raw output is evaluated OFF policy and the same output is then "
            "subjected to ON-policy validate-or-fallback delivery."
        ),
        "calibration": {
            "path": str(DEFAULT_CALIBRATION),
            "gate_passed": calibration["overall"]["gate_passed"],
            "n_items": calibration["n_items"],
        },
        "arms": {
            arm: summarize_arm([row for row in rows if row["arm"] == arm])
            for arm in selected_arms
        },
    }
    with (destination / "narratives.jsonl").open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    (destination / "faithfulness.json").write_text(
        json.dumps(faithfulness, indent=2, sort_keys=True) + "\n"
    )
    (destination / "source_g4_run.txt").write_text(str(g4.resolve()) + "\n")
    write_run_manifest(
        run_dir=destination,
        group="g5",
        seed=seed,
        source_run_dirs=[g4],
        source_files=[
            "corpus/guardrail_corpus_v1.jsonl",
            "experiments/calibration/validator_calibration_v1.json",
            "src/evaluation/stats.py",
            "src/narratives/evidence.py",
            "src/narratives/guardrails.py",
            "src/narratives/llm_client.py",
            "src/provenance.py",
            "tools/run_g5_narratives.py",
        ],
        extra={
            "model": model,
            "arms": selected_arms,
            "corpus_version": "v1",
            "calibration": str(DEFAULT_CALIBRATION),
            "reported": final_run,
        },
        require_clean=clean_required,
    )
    print(json.dumps(faithfulness, indent=2))
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--g4-run", required=True)
    parser.add_argument("--model", default="llama3:8b")
    parser.add_argument("--arms", default="strict,simple")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=int, default=60)
    arguments = parser.parse_args()
    run_g5(
        arguments.g4_run,
        model=arguments.model,
        arms=parse_arms(arguments.arms),
        limit=arguments.limit,
        timeout=arguments.timeout,
    )


if __name__ == "__main__":
    main()
