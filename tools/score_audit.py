"""Score a provenance-bound completed human audit without changing annotations."""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

import pandas as pd

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.stats import wilson_ci
from src.provenance import sha256_file
from tools.make_audit_sample import (
    AUDIT_COLUMNS,
    HUMAN_AUDIT_COLUMNS,
    IMMUTABLE_AUDIT_COLUMNS,
    build_blind_sample,
    immutable_rows_sha256,
)
from tools.run_g5_narratives import validate_reportable_g5_run


def score_audit(
    filled_csv: str | Path,
    sample_manifest: str | Path,
    *,
    human_attestation: str,
    output: str | Path = "experiments/audit/audit_result.json",
) -> Path:
    if len(human_attestation.strip()) < 12:
        raise ValueError("an explicit human attestation is required")
    source = Path(filled_csv)
    manifest_path = Path(sample_manifest)
    audit_manifest = json.loads(manifest_path.read_text())
    required_manifest = {
        "schema_version",
        "source_g5_run",
        "source_g5_manifest_sha256",
        "arm",
        "requested_n",
        "actual_n",
        "sampling_seed",
        "columns",
        "immutable_columns",
        "immutable_rows_sha256",
        "blank_human_columns",
        "sample_csv",
        "sample_csv_sha256_at_creation",
        "source_code_sha256",
    }
    if (
        audit_manifest.get("schema_version") != 1
        or required_manifest - set(audit_manifest)
    ):
        raise ValueError("invalid audit sample manifest")
    if audit_manifest["columns"] != AUDIT_COLUMNS:
        raise ValueError("audit manifest column contract differs from the scorer")
    if audit_manifest["immutable_columns"] != IMMUTABLE_AUDIT_COLUMNS:
        raise ValueError("audit manifest immutable column contract is invalid")
    if audit_manifest["blank_human_columns"] != HUMAN_AUDIT_COLUMNS:
        raise ValueError("audit manifest human column contract is invalid")
    expected_sources = {
        "tools/make_audit_sample.py",
        "tools/run_g5_narratives.py",
    }
    if set(audit_manifest["source_code_sha256"]) != expected_sources:
        raise ValueError("audit manifest source-code contract is incomplete")
    for path, expected_hash in audit_manifest["source_code_sha256"].items():
        if not Path(path).exists() or sha256_file(path) != expected_hash:
            raise ValueError(f"audit source hash mismatch: {path}")

    source_g5_run = Path(audit_manifest["source_g5_run"])
    _g5_manifest, g5_rows = validate_reportable_g5_run(source_g5_run)
    source_g5_manifest_path = source_g5_run / "run_manifest.json"
    if (
        sha256_file(source_g5_manifest_path)
        != audit_manifest["source_g5_manifest_sha256"]
    ):
        raise ValueError("audit manifest is not bound to the verified G5 manifest")
    reconstructed = build_blind_sample(
        g5_rows,
        arm=str(audit_manifest["arm"]),
        n=int(audit_manifest["requested_n"]),
        seed=int(audit_manifest["sampling_seed"]),
    )
    if len(reconstructed) != int(audit_manifest["actual_n"]):
        raise ValueError("audit sample size differs from deterministic reconstruction")
    if immutable_rows_sha256(reconstructed) != audit_manifest["immutable_rows_sha256"]:
        raise ValueError("audit sample manifest differs from deterministic reconstruction")

    frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    if list(frame.columns) != AUDIT_COLUMNS:
        raise ValueError("filled audit sheet must have the exact blinded schema")
    if len(frame) == 0:
        raise ValueError("filled audit sheet cannot be empty")
    if len(frame) != int(audit_manifest["actual_n"]):
        raise ValueError("filled audit row count differs from the sample manifest")
    if frame[["case_id", "arm"]].duplicated().any():
        raise ValueError("filled audit requires unique case_id/arm rows")
    if immutable_rows_sha256(frame) != audit_manifest["immutable_rows_sha256"]:
        raise ValueError("immutable blinded audit fields were changed")

    normalized = frame["violation_found"].str.strip().str.lower()
    invalid = sorted(set(normalized) - {"yes", "no"})
    if invalid:
        raise ValueError(f"violation_found must contain only yes/no: {invalid}")
    missing_categories = (
        (normalized == "yes")
        & (frame["violation_category"].str.strip() == "")
    )
    if missing_categories.any():
        raise ValueError("yes violations require a violation_category")
    violations = int((normalized == "yes").sum())
    n = int(len(frame))
    lower, upper = wilson_ci(violations, n)
    result = {
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "source_audit_sheet": str(source),
        "source_audit_sheet_sha256": sha256_file(source),
        "audit_sample_manifest": str(manifest_path),
        "audit_sample_manifest_sha256": sha256_file(manifest_path),
        "source_g5_manifest_sha256": audit_manifest[
            "source_g5_manifest_sha256"
        ],
        "undetected_violation_rate": {
            "rate": violations / n,
            "n": n,
            "ci95": [round(lower, 4), round(upper, 4)],
        },
        "n_violations": violations,
        "annotation_source": "human_attested",
        "human_attestation": human_attestation.strip(),
        "human_columns": HUMAN_AUDIT_COLUMNS,
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"audit score -> {destination}")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("filled_csv")
    parser.add_argument("--sample-manifest", required=True)
    parser.add_argument("--human-attestation", required=True)
    parser.add_argument("--output", default="experiments/audit/audit_result.json")
    arguments = parser.parse_args()
    score_audit(
        arguments.filled_csv,
        arguments.sample_manifest,
        human_attestation=arguments.human_attestation,
        output=arguments.output,
    )


if __name__ == "__main__":
    main()
