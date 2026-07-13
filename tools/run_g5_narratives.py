"""Run paired strict/simple raw-text G5 generation and delivery-policy analysis."""

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
from src.narratives.llm_client import (
    LLMUnavailable,
    PROMPT_TEMPLATES,
    assert_local_ollama_host,
    generate_narrative_response,
    generation_options,
    get_ollama_runtime,
)
from src.provenance import (
    assert_clean_repository,
    assert_source_hashes,
    sha256_file,
    sha256_json,
    source_run_ref,
    validate_run_manifest,
    write_run_manifest,
)

CHECK_KEYS = ("format", "completeness", "grounding", "direction")
FINAL_ARMS = ("strict", "simple")
VALID_DIRECTIONS = {"increases_risk", "decreases_risk"}
VALID_RISK_BUCKETS = {"High", "Medium", "Low"}
DEFAULT_CALIBRATION = Path("experiments/calibration/validator_calibration_v1.json")
DEFAULT_CORPUS = Path("corpus/guardrail_corpus_v1.jsonl")
G5_SOURCE_FILES = (
    "corpus/guardrail_corpus_v1.jsonl",
    "experiments/calibration/validator_calibration_v1.json",
    "experiments/DECISIONS.md",
    "src/evaluation/stats.py",
    "src/narratives/evidence.py",
    "src/narratives/guardrails.py",
    "src/narratives/llm_client.py",
    "src/provenance.py",
    "tools/run_g5_narratives.py",
    "tools/build_guardrail_corpus.py",
    "tools/calibrate_validator.py",
)


def load_g4_context(g4: Path) -> tuple[dict, list[dict], int, list[str]]:
    """Load a manifest-valid G4 run and enforce its reason-code contract."""
    manifest = validate_run_manifest(g4, expected_group="g4")
    records = [
        json.loads(line)
        for line in (g4 / "reason_codes.jsonl").read_text().splitlines()
        if line.strip()
    ]
    if not records:
        raise ValueError("G4 reason codes are empty")
    case_ids = [record.get("case_id") for record in records]
    if any(case_id is None for case_id in case_ids) or len(case_ids) != len(
        set(case_ids)
    ):
        raise ValueError("G4 reason codes require non-null unique case_id values")
    known_features = list(manifest["feature_names"])
    known_set = set(known_features)
    for record in records:
        if record.get("risk_bucket") not in VALID_RISK_BUCKETS:
            raise ValueError(f"invalid G4 risk bucket: {record.get('risk_bucket')}")
        codes = record.get("codes")
        if not isinstance(codes, list) or not codes:
            raise ValueError("each G4 record requires non-empty reason codes")
        ordered = sorted(codes, key=lambda item: item.get("rank", -1))
        if [code.get("rank") for code in ordered] != list(
            range(1, len(ordered) + 1)
        ):
            raise ValueError("G4 reason-code ranks must be contiguous from one")
        features = [code.get("feature") for code in ordered]
        if any(not isinstance(feature, str) for feature in features):
            raise ValueError("G4 reason-code features must be strings")
        if len(features) != len(set(features)):
            raise ValueError("G4 reason codes require unique features per case")
        if not set(features).issubset(known_set):
            raise ValueError("G4 reason codes contain a feature absent from the manifest")
        directions = {code.get("direction") for code in ordered}
        if not directions.issubset(VALID_DIRECTIONS):
            raise ValueError(f"invalid G4 direction values: {sorted(directions)}")
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
        "rate": successes / n if n else None,
        "n": n,
        "ci95": [round(lower, 4), round(upper, 4)],
        "estimable": n > 0,
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
        "llm_transport_unavailable": _rate_block(total_n - judged_n, total_n),
        "denominators": {
            "off_policy": "raw LLM text returned by successful Ollama API calls",
            "on_policy": "all requested cases, including transport-failure fallbacks",
        },
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
    known_features: list[str] | None = None,
) -> dict:
    """Reject stale or failed calibration before a G5 run."""
    report = json.loads(calibration_path.read_text())
    if not report.get("overall", {}).get("gate_passed"):
        raise ValueError("validator calibration gate has not passed")
    if report.get("overall", {}).get("failed_corpus_ids"):
        raise ValueError("validator calibration contains failed corpus items")
    if report.get("instrument_sha256") != sha256_file(
        "src/narratives/guardrails.py"
    ):
        raise ValueError("validator changed after calibration")
    preprocessing = report.get("candidate_preprocessing", {})
    if (
        preprocessing.get("mode") != "identity_raw_text"
        or preprocessing.get("source") != "src/narratives/llm_client.py"
        or preprocessing.get("source_sha256")
        != sha256_file("src/narratives/llm_client.py")
    ):
        raise ValueError("raw candidate construction changed after calibration")
    if report.get("corpus_builder_sha256") != sha256_file(
        "tools/build_guardrail_corpus.py"
    ):
        raise ValueError("guardrail corpus builder changed after calibration")
    if report.get("corpus_sha256") != sha256_file(corpus_path):
        raise ValueError("guardrail corpus changed after calibration")
    runtime_features = known_features or report.get("known_features")
    if report.get("known_features") != runtime_features:
        raise ValueError("runtime feature vocabulary differs from calibration")
    items = [
        json.loads(line)
        for line in corpus_path.read_text().splitlines()
        if line.strip()
    ]
    if len(items) != report.get("n_items"):
        raise ValueError("calibration item count differs from corpus")
    failures = []
    for item in items:
        rejected = validate_narrative(
            item["text"], item["record"], runtime_features
        ).fallback
        if rejected != (item["expected"] == "reject"):
            failures.append(item["corpus_id"])
    if failures:
        raise ValueError(f"live calibration recomputation failed: {failures[:10]}")
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


def validate_reportable_g5_run(run: str | Path) -> tuple[dict, list[dict]]:
    """Validate final-run invariants before downstream reporting or audit sampling."""
    run_dir = Path(run)
    manifest = validate_run_manifest(run_dir, expected_group="g5")
    extra = manifest["extra"]
    if manifest["git_dirty"] or extra.get("reported") is not True:
        raise ValueError("G5 run is not a clean reportable final run")
    if set(manifest["source_code_sha256"]) != set(G5_SOURCE_FILES):
        raise ValueError("reportable G5 source-hash contract is incomplete")
    assert_source_hashes(manifest, G5_SOURCE_FILES)
    if extra.get("arms") != list(FINAL_ARMS):
        raise ValueError("reportable G5 requires strict and simple arms")
    if extra.get("llm_transport_unavailable_count") != 0:
        raise ValueError("reportable G5 requires zero transport failures")
    runtime = extra.get("ollama_runtime", {})
    if not runtime.get("version") or not runtime.get("digest"):
        raise ValueError("reportable G5 lacks exact Ollama runtime identity")
    assert_local_ollama_host(str(runtime.get("host", "")))
    source_path = Path((run_dir / "source_g4_run.txt").read_text().strip())
    source_manifest, records, _seed, known_features = load_g4_context(source_path)
    if source_run_ref(source_path) not in manifest["source_runs"]:
        raise ValueError("G5 manifest does not bind its declared G4 source")
    if int(source_manifest["seed"]) != int(manifest["seed"]):
        raise ValueError("G5 seed differs from G4")
    rows = [
        json.loads(line)
        for line in (run_dir / "narratives.jsonl").read_text().splitlines()
        if line.strip()
    ]
    validate_g5_rows(rows, records, list(FINAL_ARMS))
    records_by_id = {record["case_id"]: record for record in records}
    for row in rows:
        record = records_by_id[row["case_id"]]
        expected_evidence = serialize_evidence(record)
        if row.get("evidence") != expected_evidence:
            raise ValueError("G5 serialized evidence differs from bound G4 evidence")
        if row.get("checks") is None or row.get("raw_output") is None:
            raise ValueError("reportable G5 contains an unjudged transport failure")
        if row.get("candidate_text") != row.get("raw_output"):
            raise ValueError("OFF and ON policies do not share the exact raw output")
        recomputed = validate_narrative(
            row["raw_output"],
            record,
            known_features,
        )
        failed_checks = [
            key for key, passed in recomputed.checks.items() if not passed
        ]
        expected_reason = (
            f"guardrail_failed:{','.join(failed_checks)}"
            if recomputed.fallback
            else None
        )
        expected_fields = {
            "checks": recomputed.checks,
            "fallback": recomputed.fallback,
            "fallback_reason": expected_reason,
            "final_text": recomputed.final_text,
        }
        for field, expected_value in expected_fields.items():
            if row.get(field) != expected_value:
                raise ValueError(f"G5 stored {field} differs from recomputation")
        latency = row.get("latency_seconds")
        if not isinstance(latency, (int, float)) or latency < 0:
            raise ValueError("G5 latency must be a non-negative number")

    faithfulness = json.loads((run_dir / "faithfulness.json").read_text())
    if faithfulness.get("llm_transport_unavailable_count") != 0:
        raise ValueError("reportable G5 faithfulness summary contains transport failures")
    if set(faithfulness.get("arms", {})) != set(FINAL_ARMS):
        raise ValueError("reportable G5 faithfulness summary lacks both arms")
    for arm in FINAL_ARMS:
        if faithfulness["arms"][arm].get("n_cases") != len(records):
            raise ValueError("reportable G5 faithfulness case count differs from G4")
    recomputed_arms = {
        arm: summarize_arm([row for row in rows if row["arm"] == arm])
        for arm in FINAL_ARMS
    }
    if faithfulness["arms"] != recomputed_arms:
        raise ValueError("G5 faithfulness summaries differ from row recomputation")
    if faithfulness.get("model") != extra.get("model"):
        raise ValueError("G5 model metadata differs between artifacts")
    if faithfulness.get("ollama_runtime") != extra.get("ollama_runtime"):
        raise ValueError("G5 Ollama runtime metadata differs between artifacts")
    expected_generation = {
        "seed": extra.get("generation_seed"),
        "options": extra.get("generation_options"),
        "prompt_sha256": extra.get("prompt_sha256"),
    }
    if faithfulness.get("generation") != expected_generation:
        raise ValueError("G5 generation metadata differs between artifacts")
    calibration_report = assert_calibration_gate(known_features=known_features)
    expected_calibration = {
        "path": extra.get("calibration"),
        "gate_passed": calibration_report["overall"]["gate_passed"],
        "n_items": calibration_report["n_items"],
    }
    if faithfulness.get("calibration") != expected_calibration:
        raise ValueError("G5 calibration metadata differs from the bound gate")
    current_prompt_hashes = {
        arm: sha256_json({"prompt_template": PROMPT_TEMPLATES[arm]})
        for arm in FINAL_ARMS
    }
    if extra.get("prompt_sha256") != current_prompt_hashes:
        raise ValueError("G5 prompt hashes differ from current bound prompts")
    if extra.get("generation_options") != generation_options(manifest["seed"]):
        raise ValueError("G5 generation options differ from the frozen seed contract")
    return manifest, rows


def run_g5(
    g4_run: str | Path,
    *,
    model: str = "llama3:8b",
    host: str = "http://localhost:11434",
    arms: list[str] | None = None,
    limit: int | None = None,
    timeout: int = 60,
    output: str | Path | None = None,
) -> Path:
    g4 = Path(g4_run)
    selected_arms = arms or list(FINAL_ARMS)
    if set(selected_arms) - set(PROMPT_TEMPLATES):
        raise ValueError("unknown prompt arm")
    _manifest, records, seed, known_features = load_g4_context(g4)
    final_run = limit is None
    if final_run:
        if selected_arms != list(FINAL_ARMS):
            raise ValueError("reported G5 requires arms in strict,simple order")
        if output is not None:
            raise ValueError("reported G5 output path is fixed by the run contract")
        assert_clean_repository()
    else:
        if limit <= 0:
            raise ValueError("limit must be positive")
        records = records[:limit]

    calibration = assert_calibration_gate(known_features=known_features)
    runtime_identity = get_ollama_runtime(model, host=host, timeout=min(timeout, 10))
    options = generation_options(seed)
    prompt_sha256 = {
        arm: sha256_json({"prompt_template": PROMPT_TEMPLATES[arm]})
        for arm in selected_arms
    }
    destination = (
        Path(output) if output is not None else g5_output_dir(seed, limit)
    )
    if destination.exists():
        raise FileExistsError(destination)

    rows: list[dict] = []
    unavailable = 0
    for record in records:
        evidence = serialize_evidence(record)
        for arm in selected_arms:
            started = time.perf_counter()
            try:
                generation = generate_narrative_response(
                    evidence,
                    model=model,
                    host=host,
                    timeout=timeout,
                    prompt_style=arm,
                    generation_seed=seed,
                )
                raw = generation.raw_response
                candidate = raw
                result = validate_narrative(candidate, record, known_features)
            except LLMUnavailable:
                unavailable += 1
                raw = None
                candidate = None
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
                "candidate_text": candidate,
                "checks": result.checks if result is not None else None,
                "fallback": result.fallback if result is not None else True,
                "fallback_reason": (
                    f"guardrail_failed:{','.join(failed_checks)}"
                    if result is not None and result.fallback
                    else "llm_transport_unavailable"
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
            print(
                f"case {record['case_id']} [{arm}]: {status} ({latency:.2f}s)",
                flush=True,
            )

    validate_g5_rows(rows, records, selected_arms)
    runtime_after = get_ollama_runtime(model, host=host, timeout=min(timeout, 10))
    if (
        runtime_after.get("version") != runtime_identity.get("version")
        or runtime_after.get("digest") != runtime_identity.get("digest")
    ):
        raise RuntimeError("Ollama runtime or model digest changed during G5")
    if final_run and unavailable:
        raise RuntimeError(
            "reported G5 requires every requested Ollama API call to succeed; "
            f"transport_unavailable={unavailable}/{len(rows)}"
        )
    faithfulness = {
        "model": model,
        "ollama_runtime": runtime_identity,
        "generation": {
            "seed": seed,
            "options": options,
            "prompt_sha256": prompt_sha256,
        },
        "llm_transport_unavailable_count": unavailable,
        "paired_design": (
            "Each arm's exact raw model text is analysed OFF policy and the same "
            "unmodified text is then subjected to ON-policy validate-or-fallback "
            "delivery. No parser or renderer sits between generation and validation."
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
    destination.mkdir(parents=True, exist_ok=False)
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
        source_files=G5_SOURCE_FILES,
        extra={
            "model": model,
            "ollama_runtime": runtime_identity,
            "generation_seed": seed,
            "generation_options": options,
            "prompt_sha256": prompt_sha256,
            "arms": selected_arms,
            "corpus_version": "v1",
            "calibration": str(DEFAULT_CALIBRATION),
            "llm_transport_unavailable_count": unavailable,
            "reported": final_run,
        },
        require_clean=final_run,
    )
    if final_run:
        validate_reportable_g5_run(destination)
    print(json.dumps(faithfulness, indent=2))
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--g4-run", required=True)
    parser.add_argument("--model", default="llama3:8b")
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--arms", default="strict,simple")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=int, default=60)
    arguments = parser.parse_args()
    run_g5(
        arguments.g4_run,
        model=arguments.model,
        host=arguments.host,
        arms=parse_arms(arguments.arms),
        limit=arguments.limit,
        timeout=arguments.timeout,
    )


if __name__ == "__main__":
    main()
