"""Run the synthetic semantic fraud-triage case study."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.provenance import sha256_file, sha256_json, write_run_manifest
from src.semantic.catalog import FEATURE_NAMES, catalogue_records, coarse_bucket
from src.semantic.explanations import (
    STRUCTURED_PROMPT_TEMPLATE,
    build_explanation_row,
    calibrate_validator,
    ollama_identity,
    public_reason_codes,
    risk_bucket,
    wilson_ci,
)
from src.semantic.features import (
    chronological_split,
    engineer_past_only_features,
    split_assignments,
    split_summary,
)
from src.semantic.generator import (
    dataframe_sha256,
    dataset_summary,
    generate_transactions,
    generator_config_from_dict,
    write_dataset_json,
)
from src.semantic.modeling import fit_and_score, reason_codes_for_frame, shap_contributions


SOURCE_FILES = [
    "tools/run_semantic_case_study.py",
    "src/semantic/__init__.py",
    "src/semantic/catalog.py",
    "src/semantic/explanations.py",
    "src/semantic/features.py",
    "src/semantic/generator.py",
    "src/semantic/modeling.py",
    "corpus/semantic_guardrail_corpus_v1.jsonl",
    "tools/build_semantic_guardrail_corpus.py",
    "tools/calibrate_semantic_validator.py",
    "src/provenance.py",
]


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def _environment_text() -> str:
    packages = []
    for name in ("numpy", "pandas", "scikit-learn", "xgboost", "pyarrow", "requests"):
        try:
            packages.append(f"{name}=={importlib.metadata.version(name)}")
        except importlib.metadata.PackageNotFoundError:
            packages.append(f"{name}=not-installed")
    return "\n".join(
        [
            f"python={platform.python_version()}",
            f"platform={platform.platform()}",
            *packages,
            "",
        ]
    )


def _run_dir(out_root: str | Path, seed: int) -> Path:
    return Path(out_root) / f"{dt.date.today().isoformat()}_s0_seed{seed}"


def run(config: dict[str, Any], *, out_root: str | Path | None = None) -> Path:
    started = time.time()
    seed = int(config.get("seed", 42))
    resolved_config = dict(config)
    generator_config = generator_config_from_dict(resolved_config.get("generator"))
    if generator_config.seed != seed:
        generator_config = generator_config.__class__(**{**generator_config.__dict__, "seed": seed})
        resolved_config["generator"] = {**resolved_config.get("generator", {}), "seed": seed}
    root = out_root or resolved_config.get("out_root", "experiments/runs")
    run_dir = _run_dir(root, seed)
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "model").mkdir()

    raw = generate_transactions(generator_config)
    engineered = engineer_past_only_features(
        raw,
        feedback_delay_days=int(resolved_config.get("feedback_delay_days", 7)),
        terminal_window_days=int(resolved_config.get("terminal_window_days", 7)),
    )
    splits_obj = chronological_split(engineered)
    splits = {name: getattr(splits_obj, name) for name in ("train", "val", "test")}
    summary = split_summary(splits_obj)
    assignments = split_assignments(splits_obj)

    model, metrics, scores, threshold = fit_and_score(
        splits,
        seed=seed,
        xgb_params=resolved_config.get("xgb_params"),
    )
    metrics["runtime"]["total_seconds"] = time.time() - started
    metrics["selection"] = {
        "threshold_source": "validation_max_f1",
        "test_evaluated_once_after_threshold_freeze": True,
    }
    test = splits["test"].reset_index(drop=True).copy()
    test["score"] = scores["test"]
    test["pred"] = (test["score"] >= threshold).astype(int)
    predictions = test[
        [
            "case_id",
            "transaction_id",
            "timestamp",
            "customer_id",
            "terminal_id",
            "amount",
            "Class",
            "score",
            "pred",
            *FEATURE_NAMES,
        ]
    ].rename(columns={"Class": "y_true"})

    shap_matrix = shap_contributions(model, test[FEATURE_NAMES])
    reason_records = reason_codes_for_frame(test, shap_matrix, top_k=int(resolved_config.get("top_k", 3)))
    by_case = {record["case_id"]: record for record in reason_records}
    alert_limit = int(resolved_config.get("alert_limit", 25))
    case_predictions = predictions.sort_values(["score", "case_id"], ascending=[False, True]).head(alert_limit)
    flagged_total = int(predictions["pred"].sum())
    semantic_cases = [
        {
            "case_id": str(row.case_id),
            "threshold": float(threshold),
            "detector_score": float(row.score),
            "alert_rank": rank,
            "flagged_total": flagged_total,
            "risk_bucket": risk_bucket(float(row.score), float(threshold)),
            "review_status": "unreviewed",
            "transaction_context": {
                "transaction_id": row.transaction_id,
                "transaction_time": str(row.timestamp),
                "amount": float(row.amount),
                "customer_activity_24h": float(row.CustomerTxCount1Day),
                "customer_activity_7d": float(row.CustomerTxCount7Day),
                "terminal_activity_7d": float(row.TerminalTxCount7Day),
                "terminal_fraud_risk_bucket": coarse_bucket(
                    "TerminalFraudRisk7Day",
                    float(row.TerminalFraudRisk7Day),
                ),
            },
            "reason_codes": public_reason_codes(by_case[int(row.case_id)]),
        }
        for rank, row in enumerate(case_predictions.itertuples(index=False), start=1)
    ]

    corpus_path = Path(
        resolved_config.get("validator_corpus", "corpus/semantic_guardrail_corpus_v1.jsonl")
    )
    calibration = calibrate_validator(corpus_path)
    _write_json(run_dir / "semantic_validator_calibration.json", calibration)

    llm_config = dict(resolved_config.get("llm", {}))
    identity, identity_status = ollama_identity(
        model=llm_config.get("model", "llama3:8b"),
        host=llm_config.get("host", "http://localhost:11434"),
        timeout=int(llm_config.get("timeout_seconds", 2)),
    )
    explanation_rows = []
    explanation_counts = {
        "rows": 0,
        "fallbacks": 0,
        "transport_failures": 0,
        "validator_failures": 0,
        "llm_latency_ms_total": 0.0,
        "llm_latency_ms_n": 0,
    }
    prediction_records = predictions.set_index("case_id").to_dict("index")
    for case in semantic_cases:
        numeric_case_id = int(case["case_id"])
        prediction = {"case_id": numeric_case_id, **prediction_records[numeric_case_id]}
        row, counts = build_explanation_row(
            prediction,
            by_case[numeric_case_id],
            threshold=threshold,
            llm_config=llm_config,
            seed=seed,
        )
        explanation_rows.append(row)
        for key, value in counts.items():
            explanation_counts[key] += value

    explanation_summary = {
        **explanation_counts,
        "fallback_rate": (
            explanation_counts["fallbacks"] / explanation_counts["rows"]
            if explanation_counts["rows"]
            else 0.0
        ),
        "fallback_rate_wilson": wilson_ci(
            explanation_counts["fallbacks"],
            explanation_counts["rows"],
        ),
        "transport_failure_rate": wilson_ci(
            explanation_counts["transport_failures"],
            explanation_counts["rows"],
        ),
        "validator_failure_rate": wilson_ci(
            explanation_counts["validator_failures"],
            explanation_counts["rows"],
        ),
        "deterministic_delivered_detected_violation_rate": {
            **wilson_ci(0, explanation_counts["rows"]),
            "label": "by_construction",
        },
        "llm_latency_ms_mean": (
            explanation_counts["llm_latency_ms_total"]
            / explanation_counts["llm_latency_ms_n"]
            if explanation_counts["llm_latency_ms_n"]
            else None
        ),
        "ollama_identity_status": identity_status,
        "ollama_identity": identity,
        "structural_descriptors": {
            "top_k": int(resolved_config.get("top_k", 3)),
            "payload_fields": ["risk_bucket", "evidence"],
            "evidence_fields": [
                "rank",
                "feature",
                "display_label",
                "direction",
                "value_bucket",
            ],
            "validator_checks": ["format", "completeness", "grounding", "direction"],
            "corpus_version": calibration["corpus_version"],
        },
    }

    write_dataset_json(run_dir / "semantic_transactions.json", raw)
    engineered.to_parquet(run_dir / "semantic_transactions.parquet")
    _write_json(run_dir / "dataset_summary.json", {**dataset_summary(raw, generator_config), "dataset_sha256_records": dataframe_sha256(raw)})
    _write_json(run_dir / "split_summary.json", summary)
    assignments.to_parquet(run_dir / "split_assignments.parquet")
    predictions.to_parquet(run_dir / "predictions.parquet")
    _write_json(run_dir / "metrics.json", metrics)
    _write_jsonl(run_dir / "reason_codes.jsonl", reason_records)
    _write_jsonl(run_dir / "semantic_cases.jsonl", semantic_cases)
    _write_jsonl(run_dir / "explanation_comparison.jsonl", explanation_rows)
    _write_json(run_dir / "explanation_summary.json", explanation_summary)
    (run_dir / "config.yaml").write_text(yaml.safe_dump(resolved_config, sort_keys=False))
    (run_dir / "environment.txt").write_text(_environment_text())
    model.save_model(run_dir / "model" / "xgb.json")

    write_run_manifest(
        run_dir=run_dir,
        group="s0",
        seed=seed,
        dataset_path=run_dir / "semantic_transactions.json",
        resolved_config=resolved_config,
        split_summary=summary,
        threshold=threshold,
        feature_names=FEATURE_NAMES,
        source_files=SOURCE_FILES,
        extra={
            "generator_config": generator_config.__dict__,
            "generator_config_sha256": sha256_json(generator_config.__dict__),
            "feature_catalogue": catalogue_records(),
            "split_boundaries": {
                name: {"start": summary[name]["start"], "end": summary[name]["end"]}
                for name in ("train", "val", "test")
            },
            "prompt_sha256": sha256_json(STRUCTURED_PROMPT_TEMPLATE),
            "validator_sha256": sha256_file("src/semantic/explanations.py"),
            "validator_corpus_sha256": sha256_file(corpus_path),
            "validator_calibration_sha256": sha256_file(
                run_dir / "semantic_validator_calibration.json"
            ),
            "ollama_identity_status": identity_status,
            "ollama_identity": identity,
            "ollama_identity_sha256": sha256_json(
                {"status": identity_status, "identity": identity}
            ),
            "artifact_contract": [
                "config.yaml",
                "dataset_summary.json",
                "split_summary.json",
                "split_assignments.parquet",
                "semantic_validator_calibration.json",
                "metrics.json",
                "predictions.parquet",
                "reason_codes.jsonl",
                "semantic_cases.jsonl",
                "explanation_comparison.jsonl",
                "explanation_summary.json",
                "model/xgb.json",
                "environment.txt",
                "run_manifest.json",
            ],
        },
    )
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/semantic_case_study.yaml")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out-root", default=None)
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text())
    if args.seed is not None:
        config["seed"] = args.seed
    run_dir = run(config, out_root=args.out_root)
    print(f"semantic run written to {run_dir}")
    print((run_dir / "metrics.json").read_text())


if __name__ == "__main__":
    sys.exit(main())
