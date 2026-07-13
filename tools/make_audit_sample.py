"""Create a provenance-bound blinded human audit sheet from final G5 output."""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

import pandas as pd

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.provenance import sha256_file, sha256_json
from tools.run_g5_narratives import validate_reportable_g5_run

IMMUTABLE_AUDIT_COLUMNS = ["case_id", "arm", "evidence", "delivered_text"]
HUMAN_AUDIT_COLUMNS = ["violation_found", "violation_category", "notes"]
AUDIT_COLUMNS = IMMUTABLE_AUDIT_COLUMNS + HUMAN_AUDIT_COLUMNS


def immutable_rows_sha256(frame: pd.DataFrame) -> str:
    """Hash only fields that annotators are not allowed to change."""
    canonical = frame[IMMUTABLE_AUDIT_COLUMNS].copy()
    for column in IMMUTABLE_AUDIT_COLUMNS:
        canonical[column] = canonical[column].astype(str)
    return sha256_json(canonical.to_dict(orient="records"))


def build_blind_sample(
    rows: list[dict],
    *,
    arm: str,
    n: int,
    seed: int,
) -> pd.DataFrame:
    """Reconstruct the exact blinded sample from verified G5 rows."""
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
    for column in HUMAN_AUDIT_COLUMNS:
        frame[column] = ""
    return frame[AUDIT_COLUMNS]


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
    manifest, rows = validate_reportable_g5_run(run)
    if arm not in manifest["extra"]["arms"]:
        raise ValueError(f"arm is absent from the reportable G5 run: {arm}")
    frame = build_blind_sample(rows, arm=arm, n=n, seed=seed)

    destination = (
        Path(output)
        if output is not None
        else Path("experiments/audit") / f"{run.name}_{arm}_audit_sample.csv"
    )
    manifest_path = destination.with_suffix(".manifest.json")
    if destination.exists() or manifest_path.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)
    audit_manifest = {
        "schema_version": 1,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "source_g5_run": str(run.resolve()),
        "source_g5_manifest_sha256": sha256_file(run / "run_manifest.json"),
        "arm": arm,
        "requested_n": n,
        "actual_n": len(frame),
        "sampling_seed": seed,
        "columns": AUDIT_COLUMNS,
        "immutable_columns": IMMUTABLE_AUDIT_COLUMNS,
        "immutable_rows_sha256": immutable_rows_sha256(frame),
        "blank_human_columns": HUMAN_AUDIT_COLUMNS,
        "sample_csv": str(destination.resolve()),
        "sample_csv_sha256_at_creation": sha256_file(destination),
        "source_code_sha256": {
            "tools/make_audit_sample.py": sha256_file(
                "tools/make_audit_sample.py"
            ),
            "tools/run_g5_narratives.py": sha256_file(
                "tools/run_g5_narratives.py"
            ),
        },
    }
    manifest_path.write_text(
        json.dumps(audit_manifest, indent=2, sort_keys=True) + "\n"
    )
    print(f"{len(frame)} blank human-audit rows -> {destination}")
    print(f"audit manifest -> {manifest_path}")
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
