"""Verify data/raw/creditcard.csv matches the recorded manifest."""

import hashlib
import sys
from pathlib import Path

import pandas as pd

PATH = Path("data/raw/creditcard.csv")
EXPECTED_SHA256 = "76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89"
EXPECTED_ROWS, EXPECTED_FRAUDS, EXPECTED_COLS = 284_807, 492, 31


def main() -> int:
    if not PATH.exists():
        print(f"MISSING: {PATH}. Re-download per data/raw/DATA_MANIFEST.md")
        return 1
    sha = hashlib.sha256(PATH.read_bytes()).hexdigest()
    df = pd.read_csv(PATH)
    checks = {
        "sha256": sha == EXPECTED_SHA256,
        "rows": len(df) == EXPECTED_ROWS,
        "frauds": int(df["Class"].sum()) == EXPECTED_FRAUDS,
        "cols": df.shape[1] == EXPECTED_COLS,
        "no_missing": not df.isna().any().any(),
    }
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'}: {name}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
