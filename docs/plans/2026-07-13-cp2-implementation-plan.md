# CP2 Implementation Plan — Hybrid AE-XGBoost Fraud Detection with Local LLM Explanations

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Read `AGENTS.md` before starting ANY task — its hard rules override convenience.

**Goal:** Implement, run, report, and demonstrate the complete CP2 experimental pipeline: XGBoost baselines (G0/G1/G6), AE-hybrid detectors (G2/G3/G7), SHAP reason codes (G4), a guardrailed local-LLM narrative layer with faithfulness evaluation (G5), and a provenance-verified local demo dashboard, producing the logged results, figures, report evidence, and live presentation workflow the CP2 needs.

**Architecture:** Config-driven experiment runner. Every experiment is a YAML file in `configs/` executed by `src/run_experiment.py`, which assembles pure functions from `src/data`, `src/models`, `src/evaluation`, `src/explainability`, `src/narratives` and writes an immutable, manifest-backed run directory under `experiments/runs/`. The LLM layer is a strict translation layer over SHAP evidence with code-level guardrails and fallback. A React + TypeScript + Vite dashboard is served by FastAPI as a read-only consumer of exact frozen detector/G4/G5/results artifacts and the existing `src.narratives` implementation.

**Tech Stack:** Python 3.12 (uv-managed), pandas, scikit-learn, imbalanced-learn (SMOTE), XGBoost, TensorFlow/Keras (autoencoder), SHAP, PyYAML, pyarrow, matplotlib, pytest, FastAPI, Uvicorn, Ollama (llama3 8B, local HTTP API), React, TypeScript, Vite, Vitest, React Testing Library, and Playwright.

## Global Constraints

(Verbatim from the approved proposal + AGENTS.md — every task inherits these.)

- Dataset: `data/raw/creditcard.csv` — 284,807 rows, 492 frauds (0.172%), columns Time, V1–V28, Amount, Class. SHA256 recorded in `data/raw/DATA_MANIFEST.md`.
- Split 70% train / 15% validation / 15% test, stratified by `Class`, `random_state=42`, performed BEFORE any scaling, SMOTE, AE fitting, or threshold selection.
- Scaler fit on train only. SMOTE on train only. AE fit on train legitimate rows only. Validation/test always keep the original class distribution.
- Model selection metric: **validation AUC-PR**. Test set evaluated ONCE per group after config freeze.
- Metrics reported: AUC-PR (primary), ROC-AUC (secondary), Precision/Recall/F1 at the validation-selected threshold, confusion matrix, Precision@100, Recall@100, inference time. Multi-seed (42–46) mean ± std for final groups. Accuracy is never a headline metric.
- LLM never sees raw transaction rows or exact feature values; guardrails (grounding / direction / format) are code; any failure → fallback to reason codes.
- Experiment groups: G0 (XGB), G1 (XGB+SMOTE), G2 (AE-recon-error+XGB), G3 (AE-recon-error+XGB+SMOTE), G4 (best detector + SHAP), G5 (G4 + LLM narrative), G6 (XGB+scale_pos_weight), G7 (AE-latent+XGB).
- All commands run from repo root `fraud-detection-fyp/` with `uv run …`. Tests: `uv run pytest` must pass before every commit touching `src/`.
- Unit tests never train on the full dataset — synthetic fixtures only. Full-data runs happen only through the runner.

---

## Phase 0 — Environment & project bootstrap

### Task 0.1: Python environment with uv

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`, `src/data/__init__.py`, `src/models/__init__.py`, `src/evaluation/__init__.py`, `src/explainability/__init__.py`, `src/narratives/__init__.py`, `tests/__init__.py`

**Interfaces:**
- Produces: a locked `.venv` where `uv run pytest` works; package imports of the form `from src.data.load import load_raw`.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "fraud-detection-fyp"
version = "0.1.0"
description = "CP2: Hybrid AE-XGBoost fraud detection with local LLM explanations"
requires-python = ">=3.12,<3.13"
dependencies = [
    "numpy>=1.26",
    "pandas>=2.2",
    "scikit-learn>=1.5",
    "imbalanced-learn>=0.12",
    "xgboost>=2.1",
    "tensorflow>=2.17,<2.20",
    "shap>=0.46",
    "pyyaml>=6.0",
    "pyarrow>=17",
    "matplotlib>=3.9",
    "requests>=2.32",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
]

[dependency-groups]
dev = ["pytest>=8.0", "httpx>=0.28"]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Pin Python and sync**

Run: `uv python pin 3.12 && uv sync`
Expected: `.venv` created; tensorflow, xgboost, shap resolve without conflict. (TensorFlow is the reason for pinning 3.12, not 3.13.)

- [ ] **Step 3: Create the package `__init__.py` files**

Run: `touch src/__init__.py src/data/__init__.py src/models/__init__.py src/evaluation/__init__.py src/explainability/__init__.py src/narratives/__init__.py tests/__init__.py`

- [ ] **Step 4: Smoke-test the environment**

Run: `uv run python -c "import tensorflow, xgboost, shap, imblearn, pandas; print('env OK')"`
Expected: `env OK` (TF may print CPU-optimization info lines first — fine).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock .gitignore .python-version src tests AGENTS.md CLAUDE.md data/raw/DATA_MANIFEST.md data/raw/.gitkeep docs
git commit -m "chore: bootstrap CP2 project (uv env, AGENTS.md, plan, data manifest)"
```

### Task 0.2: Dataset presence check script

**Files:**
- Create: `tools/check_data.py`

**Interfaces:**
- Produces: `uv run python tools/check_data.py` exits 0 iff the dataset is present and matches the manifest (rows/frauds/sha256).

- [ ] **Step 1: Write the script**

```python
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
```

- [ ] **Step 2: Run it**

Run: `uv run python tools/check_data.py`
Expected: five `PASS` lines, exit 0.

- [ ] **Step 3: Commit**

```bash
git add tools/check_data.py && git commit -m "feat: dataset integrity check script"
```

---

## Phase 1 — Data foundation (load, split, preprocess, resample)

### Task 1.1: Loader + dedup

**Files:**
- Create: `src/data/load.py`
- Test: `tests/test_load.py`

**Interfaces:**
- Produces: `load_raw(path, validate=True) -> pd.DataFrame`; `dedupe(df) -> tuple[pd.DataFrame, int]` (deduped df, n_dropped); constants `CASE_ID = "case_id"`, `FEATURES` (Time, V1–V28, Amount), and `TARGET = "Class"`.
- `case_id` is the original CSV row position, created immediately after load and before deduplication/splitting. It is preserved as metadata through all stages and is never included in model features.

- [ ] **Step 1: Write the failing test**

```python
import pandas as pd
import pytest

from src.data.load import CASE_ID, FEATURES, TARGET, dedupe, load_raw


def make_tiny_csv(tmp_path, rows=10):
    cols = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount", "Class"]
    df = pd.DataFrame([[float(i)] * 30 + [i % 2] for i in range(rows)], columns=cols)
    p = tmp_path / "tiny.csv"
    df.to_csv(p, index=False)
    return p


def test_load_raw_reads_csv(tmp_path):
    df = load_raw(make_tiny_csv(tmp_path), validate=False)
    assert list(df.columns) == [CASE_ID, *FEATURES, TARGET]
    assert len(df) == 10
    assert df[CASE_ID].tolist() == list(range(10))


def test_load_raw_validate_rejects_wrong_shape(tmp_path):
    with pytest.raises(ValueError):
        load_raw(make_tiny_csv(tmp_path), validate=True)  # 10 rows != 284807


def test_dedupe_drops_exact_duplicates():
    # case_id is identity metadata and must not prevent content deduplication.
    df = pd.DataFrame({CASE_ID: [10, 11, 12], "a": [1, 1, 2], "b": [3, 3, 4]})
    out, dropped = dedupe(df)
    assert len(out) == 2 and dropped == 1
    assert out[CASE_ID].tolist() == [10, 12]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_load.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.data.load'`

- [ ] **Step 3: Implement**

```python
"""Load and validate the ULB credit card fraud dataset."""
from pathlib import Path

import pandas as pd

FEATURES = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]
TARGET = "Class"
CASE_ID = "case_id"
EXPECTED_ROWS = 284_807
EXPECTED_FRAUDS = 492


def load_raw(path: str | Path, validate: bool = True) -> pd.DataFrame:
    df = pd.read_csv(path)
    if list(df.columns) != FEATURES + [TARGET]:
        raise ValueError(f"Unexpected columns: {list(df.columns)}")
    if validate:
        if len(df) != EXPECTED_ROWS:
            raise ValueError(f"Expected {EXPECTED_ROWS} rows, got {len(df)}")
        if int(df[TARGET].sum()) != EXPECTED_FRAUDS:
            raise ValueError(f"Expected {EXPECTED_FRAUDS} frauds, got {int(df[TARGET].sum())}")
    df.insert(0, CASE_ID, range(len(df)))
    return df


def dedupe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    content_columns = [c for c in df.columns if c != CASE_ID]
    out = df.drop_duplicates(subset=content_columns).reset_index(drop=True)
    return out, len(df) - len(out)
```

- [ ] **Step 4: Run tests, expect PASS.** Add regression assertions in Tasks 1.2–1.3 that `case_id` survives splitting/preprocessing unchanged and is absent from every feature matrix.
- [ ] **Step 5: Commit** — `git add src/data/load.py tests/test_load.py && git commit -m "feat: stable case identity + validated dataset loader"`

### Task 1.2: Stratified 70/15/15 split

**Files:**
- Create: `src/data/split.py`
- Test: `tests/test_split.py`

**Interfaces:**
- Consumes: a DataFrame with `Class` column.
- Produces: `stratified_split(df, seed=42) -> Splits` where `Splits` is a dataclass with `.train/.val/.test` DataFrames, and `split_summary(splits) -> dict` (sizes + fraud counts + fraud ratios per split) for the run log and leakage audit.
- Preserves stable `case_id` values and verifies that train, validation, and test ID sets are pairwise disjoint.

- [ ] **Step 1: Write the failing test**

```python
import pandas as pd

from src.data.load import CASE_ID
from src.data.split import split_summary, stratified_split


def make_df(n=2000, fraud_rate=0.05):
    n_fraud = int(n * fraud_rate)
    return pd.DataFrame(
        {CASE_ID: range(n), "Class": [1] * n_fraud + [0] * (n - n_fraud)}
    ).sample(frac=1, random_state=0).reset_index(drop=True)


def test_split_proportions_and_stratification():
    s = stratified_split(make_df(), seed=42)
    n = len(s.train) + len(s.val) + len(s.test)
    assert n == 2000
    assert abs(len(s.train) / n - 0.70) < 0.01
    assert abs(len(s.val) / n - 0.15) < 0.01
    for part in (s.train, s.val, s.test):
        assert abs(part["Class"].mean() - 0.05) < 0.01  # stratified


def test_split_is_reproducible_and_disjoint():
    a, b = stratified_split(make_df(), seed=42), stratified_split(make_df(), seed=42)
    assert a.train[CASE_ID].tolist() == b.train[CASE_ID].tolist()
    parts = [set(p[CASE_ID]) for p in (a.train, a.val, a.test)]
    assert parts[0].isdisjoint(parts[1])
    assert parts[0].isdisjoint(parts[2])
    assert parts[1].isdisjoint(parts[2])
    assert len(set.union(*parts)) == 2000  # no overlap, nothing lost


def test_split_summary_reports_counts():
    info = split_summary(stratified_split(make_df(), seed=42))
    assert set(info) == {"train", "val", "test"}
    assert info["test"]["n"] == 300 and "fraud_ratio" in info["test"]
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_split.py -v` → `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
"""Stratified train/validation/test split. Runs BEFORE any fitting (AGENTS.md)."""
from dataclasses import dataclass

import pandas as pd
from sklearn.model_selection import train_test_split

from src.data.load import TARGET


@dataclass
class Splits:
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame


def stratified_split(
    df: pd.DataFrame, seed: int = 42,
    train_frac: float = 0.70, val_frac: float = 0.15, test_frac: float = 0.15,
) -> Splits:
    assert abs(train_frac + val_frac + test_frac - 1.0) < 1e-9
    rest, test = train_test_split(
        df, test_size=test_frac, stratify=df[TARGET], random_state=seed
    )
    train, val = train_test_split(
        rest, test_size=val_frac / (1 - test_frac), stratify=rest[TARGET], random_state=seed
    )
    return Splits(
        train.reset_index(drop=True), val.reset_index(drop=True), test.reset_index(drop=True)
    )


def split_summary(s: Splits) -> dict:
    def info(part: pd.DataFrame) -> dict:
        return {
            "n": int(len(part)),
            "frauds": int(part[TARGET].sum()),
            "fraud_ratio": float(part[TARGET].mean()),
        }

    return {"train": info(s.train), "val": info(s.val), "test": info(s.test)}
```

- [ ] **Step 4: Run tests, expect PASS**, then **Step 5: Commit** — `git commit -m "feat: stratified 70/15/15 split with summary"`

### Task 1.3: Preprocessing (train-fit scaler)

**Files:**
- Create: `src/data/preprocess.py`
- Test: `tests/test_preprocess.py`

**Interfaces:**
- Produces: `fit_scaler(train_df) -> StandardScaler` (fit on `FEATURES` of TRAIN only); `apply_scaler(scaler, df) -> pd.DataFrame` (copy with FEATURES transformed). All model inputs downstream use scaled features (needed by the AE; harmless for XGBoost).
- Preserves `case_id` byte-for-byte as metadata. `case_id` is never passed to the scaler or included in a model feature matrix.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
import pandas as pd

from src.data.load import CASE_ID, FEATURES
from src.data.preprocess import apply_scaler, fit_scaler


def make_df(shift=0.0, n=500, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.normal(shift, 1.0, (n, 30)), columns=FEATURES)
    df.insert(0, CASE_ID, range(n))
    df["Class"] = 0
    return df


def test_scaler_standardizes_train():
    train = make_df()
    scaled = apply_scaler(fit_scaler(train), train)
    assert abs(scaled["Amount"].mean()) < 1e-9
    assert abs(scaled["Amount"].std(ddof=0) - 1.0) < 1e-6


def test_scaler_uses_train_params_on_other_splits():
    train, val = make_df(shift=0.0), make_df(shift=5.0, seed=1)
    scaled_val = apply_scaler(fit_scaler(train), val)
    # val was shifted by +5 vs train, so with TRAIN params its mean stays ~5, not 0
    assert scaled_val["V1"].mean() > 3.0


def test_apply_scaler_does_not_mutate_input():
    train = make_df()
    before = train["Amount"].copy()
    apply_scaler(fit_scaler(train), train)
    pd.testing.assert_series_equal(train["Amount"], before)


def test_case_id_is_preserved_and_not_scaled():
    train = make_df()
    scaled = apply_scaler(fit_scaler(train), train)
    pd.testing.assert_series_equal(scaled[CASE_ID], train[CASE_ID])
    assert CASE_ID not in FEATURES
```

- [ ] **Step 2: Run to verify failure**, then **Step 3: Implement**

```python
"""Preprocessing: scaler is fit on TRAIN ONLY (AGENTS.md hard rule)."""
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.data.load import FEATURES


def fit_scaler(train_df: pd.DataFrame) -> StandardScaler:
    return StandardScaler().fit(train_df[FEATURES])


def apply_scaler(scaler: StandardScaler, df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out[FEATURES] = scaler.transform(df[FEATURES])
    return out
```

- [ ] **Step 4: PASS**, **Step 5: Commit** — `git commit -m "feat: train-only-fit standard scaler"`

### Task 1.4: SMOTE (train only)

**Files:**
- Create: `src/data/resample.py`
- Test: `tests/test_resample.py`

**Interfaces:**
- Consumes: `X_train: pd.DataFrame`, `y_train: pd.Series`.
- Produces: `smote_train(X_train, y_train, seed=42) -> tuple[pd.DataFrame, pd.Series]` — balanced 1:1 by default. There is deliberately NO function that accepts val/test.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
import pandas as pd

from src.data.resample import smote_train


def test_smote_balances_training_classes():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(200, 5)), columns=list("abcde"))
    y = pd.Series([1] * 20 + [0] * 180)
    Xr, yr = smote_train(X, y, seed=42)
    assert (yr == 1).sum() == (yr == 0).sum() == 180
    assert list(Xr.columns) == list("abcde")


def test_smote_is_reproducible():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(100, 3)), columns=list("abc"))
    y = pd.Series([1] * 10 + [0] * 90)
    (X1, _), (X2, _) = smote_train(X, y, seed=42), smote_train(X, y, seed=42)
    pd.testing.assert_frame_equal(X1, X2)
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement**

```python
"""SMOTE applied to the TRAINING split only (AGENTS.md hard rule)."""
import pandas as pd
from imblearn.over_sampling import SMOTE


def smote_train(
    X_train: pd.DataFrame, y_train: pd.Series, seed: int = 42
) -> tuple[pd.DataFrame, pd.Series]:
    X_res, y_res = SMOTE(random_state=seed).fit_resample(X_train, y_train)
    return X_res, y_res
```

- [ ] **Step 4: PASS**, **Step 5: Commit** — `git commit -m "feat: SMOTE train-only resampling"`

---

## Phase 2 — Evaluation core (metrics + threshold, built BEFORE any model)

### Task 2.1: Metrics module

**Files:**
- Create: `src/evaluation/metrics.py`
- Test: `tests/test_metrics.py`

**Interfaces:**
- Produces: `evaluate(y_true, scores, threshold) -> dict` with keys `auc_pr, roc_auc, threshold, precision, recall, f1, tn, fp, fn, tp, precision_at_100, recall_at_100`; helpers `precision_at_k`, `recall_at_k`. Every experiment group reports exactly this dict for val and test.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np

from src.evaluation.metrics import evaluate, precision_at_k, recall_at_k


def test_precision_and_recall_at_k():
    y = np.array([1, 1, 0, 0, 1, 0])
    scores = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.1])
    assert precision_at_k(y, scores, k=2) == 1.0        # top-2 both fraud
    assert recall_at_k(y, scores, k=2) == 2 / 3          # 2 of 3 frauds captured


def test_evaluate_perfect_classifier():
    y = np.array([0, 0, 1, 1])
    scores = np.array([0.1, 0.2, 0.9, 0.95])
    m = evaluate(y, scores, threshold=0.5)
    assert m["auc_pr"] == 1.0 and m["recall"] == 1.0 and m["f1"] == 1.0
    assert (m["tp"], m["tn"], m["fp"], m["fn"]) == (2, 2, 0, 0)


def test_evaluate_threshold_applied():
    y = np.array([0, 1, 1])
    scores = np.array([0.4, 0.6, 0.45])
    m = evaluate(y, scores, threshold=0.5)
    assert m["tp"] == 1 and m["fn"] == 1  # 0.45 fraud missed at t=0.5
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement**

```python
"""Uniform evaluation for all experiment groups. AUC-PR is primary (AGENTS.md)."""
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def precision_at_k(y_true, scores, k: int = 100) -> float:
    y = np.asarray(y_true)
    idx = np.argsort(np.asarray(scores))[::-1][:k]
    return float(y[idx].mean())


def recall_at_k(y_true, scores, k: int = 100) -> float:
    y = np.asarray(y_true)
    total = y.sum()
    if total == 0:
        return 0.0
    idx = np.argsort(np.asarray(scores))[::-1][:k]
    return float(y[idx].sum() / total)


def evaluate(y_true, scores, threshold: float) -> dict:
    y = np.asarray(y_true)
    s = np.asarray(scores)
    pred = (s >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "auc_pr": float(average_precision_score(y, s)),
        "roc_auc": float(roc_auc_score(y, s)),
        "threshold": float(threshold),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "precision_at_100": precision_at_k(y, s, 100),
        "recall_at_100": recall_at_k(y, s, 100),
    }
```

- [ ] **Step 4: PASS**, **Step 5: Commit** — `git commit -m "feat: uniform metrics module (AUC-PR primary)"`

### Task 2.2: Threshold selection on validation

**Files:**
- Create: `src/evaluation/threshold.py`
- Test: `tests/test_threshold.py`

**Interfaces:**
- Produces: `select_threshold_max_f1(y_val, val_scores) -> float`. The returned threshold is FROZEN and reused on test — no test-set threshold search exists anywhere in the codebase.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np

from src.evaluation.metrics import evaluate
from src.evaluation.threshold import select_threshold_max_f1


def test_selected_threshold_maximizes_f1_on_validation():
    y = np.array([0] * 90 + [1] * 10)
    scores = np.concatenate([np.linspace(0.0, 0.55, 90), np.linspace(0.5, 1.0, 10)])
    t = select_threshold_max_f1(y, scores)
    best_f1 = evaluate(y, scores, t)["f1"]
    for other in np.linspace(0.01, 0.99, 99):
        assert best_f1 >= evaluate(y, scores, other)["f1"] - 1e-9
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement**

```python
"""Threshold selection happens on VALIDATION scores only, then is frozen (AGENTS.md)."""
import numpy as np
from sklearn.metrics import precision_recall_curve


def select_threshold_max_f1(y_val, val_scores) -> float:
    precision, recall, thresholds = precision_recall_curve(y_val, val_scores)
    p, r = precision[:-1], recall[:-1]
    f1 = 2 * p * r / np.clip(p + r, 1e-12, None)
    return float(thresholds[int(np.argmax(f1))])
```

- [ ] **Step 4: PASS**, **Step 5: Commit** — `git commit -m "feat: validation-only max-F1 threshold selection"`

---

## Phase 3 — Experiment runner + baselines (G0, G1, G6)

### Task 3.1: XGBoost wrapper

**Files:**
- Create: `src/models/xgb.py`
- Test: `tests/test_xgb.py`

**Interfaces:**
- Produces: `train_xgboost(X_train, y_train, X_val, y_val, params=None, seed=42) -> XGBClassifier` (early stopping on validation AUC-PR); `fraud_scores(model, X) -> np.ndarray` (probability of class 1).

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
import pandas as pd

from src.models.xgb import fraud_scores, train_xgboost


def make_separable(n=400, seed=0):
    rng = np.random.default_rng(seed)
    y = pd.Series((rng.random(n) < 0.3).astype(int))
    X = pd.DataFrame({"f1": y * 2.0 + rng.normal(0, 0.3, n), "f2": rng.normal(size=n)})
    return X, y


def test_xgboost_learns_separable_data():
    X, y = make_separable()
    Xv, yv = make_separable(seed=1)
    model = train_xgboost(X, y, Xv, yv, params={"n_estimators": 50}, seed=42)
    scores = fraud_scores(model, Xv)
    assert scores.shape == (400,)
    assert scores[yv == 1].mean() > scores[yv == 0].mean() + 0.3


def test_scale_pos_weight_passes_through():
    X, y = make_separable()
    model = train_xgboost(X, y, X, y, params={"scale_pos_weight": 7.0, "n_estimators": 10})
    assert model.get_params()["scale_pos_weight"] == 7.0
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement**

```python
"""XGBoost classifier wrapper. Early stopping uses the validation split (model selection)."""
import numpy as np
from xgboost import XGBClassifier

DEFAULT_PARAMS = {
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "eval_metric": "aucpr",
    "tree_method": "hist",
    "n_jobs": -1,
}


def train_xgboost(X_train, y_train, X_val, y_val, params=None, seed: int = 42,
                  early_stopping_rounds: int = 30) -> XGBClassifier:
    cfg = {**DEFAULT_PARAMS, **(params or {}), "random_state": seed}
    model = XGBClassifier(**cfg, early_stopping_rounds=early_stopping_rounds)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    return model


def fraud_scores(model: XGBClassifier, X) -> np.ndarray:
    return model.predict_proba(X)[:, 1]
```

- [ ] **Step 4: PASS**, **Step 5: Commit** — `git commit -m "feat: XGBoost wrapper with val early stopping"`

### Task 3.2: Config-driven experiment runner

**Files:**
- Create: `src/run_experiment.py`, `src/provenance.py`, `configs/g0_xgb.yaml`, `configs/g1_xgb_smote.yaml`, `configs/g6_xgb_spw.yaml`
- Test: `tests/test_runner.py`, `tests/test_provenance.py` (config parsing + tiny end-to-end on synthetic data + canonical manifest/hash validation)

**Interfaces:**
- Consumes: everything from Phases 1–3.
- Produces: `run(config: dict, data_path: str, out_root: str) -> Path` (returns the run dir) and CLI `uv run python -m src.run_experiment --config configs/g0_xgb.yaml [--seed 42]`. Run dir layout: `config.yaml`, `split_summary.json`, `metrics.json` (`{"val": {...}, "test": {...}, "runtime": {...}}`), `predictions.parquet` (test `case_id`, `y_true`, `score`, `pred`), `environment.txt`, `run_manifest.json`, `model/xgb.json` (+ `model/ae.keras` for hybrids). Config schema keys: `group`, `features` (`original` | `recon_error` | `latent`), `imbalance` (`none` | `smote` | `scale_pos_weight`), `seed`, `dedup` (bool), `xgb_params` (dict), `ae_params` (dict, hybrids only).
- `src/provenance.py` provides canonical SHA256 helpers plus a versioned manifest writer/validator reused by detector, G4, G5, results, and dashboard tooling.
- Detector manifest fields include schema version, run ID/group/seed, dataset/config/split hashes, the frozen validation threshold, the exact detector `feature_names`, Git commit + dirty state, relevant source hashes, exact upstream run references, and hashes/row counts for every required artifact. Final reported runs must record `git_dirty: false`.

- [ ] **Step 1: Write the three baseline configs**

`configs/g0_xgb.yaml`:
```yaml
group: g0
description: XGBoost baseline, original features, no imbalance handling
features: original
imbalance: none
dedup: true
seed: 42
xgb_params: {}
```

`configs/g1_xgb_smote.yaml`:
```yaml
group: g1
description: XGBoost + SMOTE (training set only)
features: original
imbalance: smote
dedup: true
seed: 42
xgb_params: {}
```

`configs/g6_xgb_spw.yaml`:
```yaml
group: g6
description: XGBoost cost-sensitive via scale_pos_weight (= n_legit/n_fraud on train)
features: original
imbalance: scale_pos_weight
dedup: true
seed: 42
xgb_params: {}
```

- [ ] **Step 2: Write the failing test**

```python
import json

import numpy as np
import pandas as pd

from src.data.load import CASE_ID, FEATURES, TARGET
from src.run_experiment import run


def make_synthetic_csv(tmp_path, n=3000, fraud_rate=0.05, seed=0):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < fraud_rate).astype(int)
    X = rng.normal(size=(n, 30))
    X[:, 5] += y * 3.0  # separable signal on V5
    df = pd.DataFrame(X, columns=FEATURES)
    df[TARGET] = y
    p = tmp_path / "synth.csv"
    df.to_csv(p, index=False)
    return p


def test_runner_end_to_end_baseline(tmp_path):
    cfg = {"group": "g0", "features": "original", "imbalance": "none",
           "dedup": True, "seed": 42, "xgb_params": {"n_estimators": 30}}
    run_dir = run(cfg, data_path=make_synthetic_csv(tmp_path), out_root=tmp_path / "runs",
                  validate_data=False)
    metrics = json.loads((run_dir / "metrics.json").read_text())
    assert set(metrics) >= {"val", "test", "runtime"}
    assert 0.0 <= metrics["test"]["auc_pr"] <= 1.0
    assert (run_dir / "predictions.parquet").exists()
    preds = pd.read_parquet(run_dir / "predictions.parquet")
    assert list(preds.columns) == [CASE_ID, "y_true", "score", "pred"]
    assert preds[CASE_ID].is_unique
    manifest = json.loads((run_dir / "run_manifest.json").read_text())
    assert manifest["schema_version"] == 1
    assert manifest["artifacts"]["predictions.parquet"]["rows"] == len(preds)
    assert (run_dir / "split_summary.json").exists()
    assert (run_dir / "model" / "xgb.json").exists()


def test_runner_smote_changes_only_train(tmp_path):
    cfg = {"group": "g1", "features": "original", "imbalance": "smote",
           "dedup": True, "seed": 42, "xgb_params": {"n_estimators": 30}}
    run_dir = run(cfg, data_path=make_synthetic_csv(tmp_path), out_root=tmp_path / "runs",
                  validate_data=False)
    summary = json.loads((run_dir / "split_summary.json").read_text())
    # original-distribution val/test recorded; post-SMOTE train recorded separately
    assert summary["val"]["fraud_ratio"] < 0.10
    assert summary["train_after_resample"]["fraud_ratio"] == 0.5
```

- [ ] **Step 3: Verify failure**, then **Step 4: Implement the runner**

```python
"""Config-driven experiment runner. The ONLY sanctioned way to produce results.

Pipeline order (AGENTS.md): load -> dedup -> split -> scale(fit on train) ->
AE fit on train legit (hybrids) -> feature augment -> SMOTE/spw (train only) ->
XGBoost -> threshold on val -> ONE test evaluation -> write immutable run dir.
"""
import argparse
import datetime
import json
import platform
import subprocess
import time
from pathlib import Path

import pandas as pd
import yaml

from src.data.load import CASE_ID, FEATURES, TARGET, dedupe, load_raw
from src.data.preprocess import apply_scaler, fit_scaler
from src.data.resample import smote_train
from src.data.split import split_summary, stratified_split
from src.evaluation.metrics import evaluate
from src.evaluation.threshold import select_threshold_max_f1
from src.models.xgb import fraud_scores, train_xgboost
from src.provenance import write_run_manifest


def _augment(cfg, splits, scaled, seed, run_dir):
    """Return (X_train, X_val, X_test, feature_names) per cfg['features']."""
    Xs = {k: scaled[k][FEATURES].copy() for k in ("train", "val", "test")}
    names = list(FEATURES)
    if cfg["features"] in ("recon_error", "latent"):
        from src.models.autoencoder import (
            build_autoencoder, latent_features, reconstruction_error, train_autoencoder,
        )
        ae_cfg = cfg.get("ae_params", {})
        train_legit = Xs["train"][scaled["train"][TARGET] == 0].to_numpy()
        ae = build_autoencoder(input_dim=len(FEATURES), seed=seed, **ae_cfg.get("build", {}))
        ae = train_autoencoder(ae, train_legit, seed=seed, **ae_cfg.get("fit", {}))
        (run_dir / "model").mkdir(parents=True, exist_ok=True)
        ae.save(run_dir / "model" / "ae.keras")
        if cfg["features"] == "recon_error":
            for k in Xs:
                Xs[k]["recon_error"] = reconstruction_error(ae, Xs[k].to_numpy())
            names.append("recon_error")
        else:
            for k in Xs:
                Z = latent_features(ae, Xs[k][FEATURES].to_numpy())
                for j in range(Z.shape[1]):
                    Xs[k][f"latent_{j}"] = Z[:, j]
            names += [f"latent_{j}" for j in range(Z.shape[1])]
    return Xs["train"], Xs["val"], Xs["test"], names


def run(config: dict, data_path, out_root="experiments/runs", validate_data=True) -> Path:
    seed = int(config.get("seed", 42))
    stamp = datetime.date.today().isoformat()
    run_dir = Path(out_root) / f"{stamp}_{config['group']}_seed{seed}"
    run_dir.mkdir(parents=True, exist_ok=False)  # never overwrite a run
    (run_dir / "model").mkdir(exist_ok=True)

    t0 = time.time()
    df = load_raw(data_path, validate=validate_data)
    n_dropped = 0
    if config.get("dedup", True):
        df, n_dropped = dedupe(df)
    splits = stratified_split(df, seed=seed)
    summary = split_summary(splits)
    summary["dedup_dropped"] = n_dropped

    scaler = fit_scaler(splits.train)
    scaled = {"train": apply_scaler(scaler, splits.train),
              "val": apply_scaler(scaler, splits.val),
              "test": apply_scaler(scaler, splits.test)}
    y = {k: scaled[k][TARGET] for k in scaled}

    X_train, X_val, X_test, feature_names = _augment(config, splits, scaled, seed, run_dir)

    xgb_params = dict(config.get("xgb_params") or {})
    if config["imbalance"] == "smote":
        X_train, y_train = smote_train(X_train, y["train"], seed=seed)
        summary["train_after_resample"] = {
            "n": int(len(y_train)), "frauds": int(y_train.sum()),
            "fraud_ratio": float(y_train.mean()),
        }
    else:
        y_train = y["train"]
        if config["imbalance"] == "scale_pos_weight":
            spw = float((y_train == 0).sum() / max(1, (y_train == 1).sum()))
            xgb_params.setdefault("scale_pos_weight", spw)

    t_train0 = time.time()
    model = train_xgboost(X_train, y_train, X_val, y["val"], params=xgb_params, seed=seed)
    train_secs = time.time() - t_train0

    val_scores = fraud_scores(model, X_val)
    threshold = select_threshold_max_f1(y["val"], val_scores)
    t_inf0 = time.time()
    test_scores = fraud_scores(model, X_test)          # test evaluated ONCE
    infer_secs = time.time() - t_inf0

    metrics = {
        "val": evaluate(y["val"], val_scores, threshold),
        "test": evaluate(y["test"], test_scores, threshold),
        "runtime": {"train_seconds": train_secs, "test_inference_seconds": infer_secs,
                    "total_seconds": time.time() - t0},
        "feature_names": feature_names,
        "resolved_xgb_params": {k: (float(v) if isinstance(v, (int, float)) else v)
                                 for k, v in xgb_params.items()},
    }

    pd.DataFrame({
        CASE_ID: scaled["test"][CASE_ID].to_numpy(),
        "y_true": y["test"].to_numpy(),
        "score": test_scores,
        "pred": (test_scores >= threshold).astype(int),
    }).to_parquet(run_dir / "predictions.parquet")
    model.save_model(run_dir / "model" / "xgb.json")
    (run_dir / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    (run_dir / "split_summary.json").write_text(json.dumps(summary, indent=2))
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    freeze = subprocess.run(["uv", "pip", "list", "--format", "freeze"],
                            capture_output=True, text=True).stdout
    (run_dir / "environment.txt").write_text(
        f"python={platform.python_version()}\nplatform={platform.platform()}\n{freeze}"
    )
    # Write run_manifest.json LAST, after all artifacts exist. Use the shared
    # provenance helper to hash the dataset, resolved config, split summary,
    # relevant source files, models, metrics, predictions, and environment.
    # The helper also records git commit + dirty state; reported final runs must
    # come from a clean revision.
    write_run_manifest(
        run_dir=run_dir,
        group=config["group"],
        seed=seed,
        dataset_path=Path(data_path),
        resolved_config=config,
        split_summary=summary,
        threshold=threshold,
        feature_names=feature_names,
        source_run_dirs=[],
        source_files=[
            "src/run_experiment.py",
            "src/data/load.py",
            "src/data/split.py",
            "src/data/preprocess.py",
            "src/evaluation/metrics.py",
            "src/evaluation/threshold.py",
            "src/models/xgb.py",
            "src/provenance.py",
        ] + (["src/models/autoencoder.py"] if config["features"] != "original" else []),
        require_clean=validate_data,
    )
    return run_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--data", default="data/raw/creditcard.csv")
    args = ap.parse_args()
    config = yaml.safe_load(Path(args.config).read_text())
    if args.seed is not None:
        config["seed"] = args.seed
    run_dir = run(config, data_path=args.data)
    print(f"run written to {run_dir}")
    print(json.dumps(json.loads((run_dir / 'metrics.json').read_text())["test"], indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5a: Write `tests/test_provenance.py` before the implementation.** This is executable contract coverage, not a prose checklist:

```python
import json

import pandas as pd
import pytest

from src.data.load import CASE_ID
from src.provenance import (
    sha256_json,
    source_run_ref,
    validate_run_manifest,
    write_run_manifest,
)


def make_run(tmp_path, name="detector", source_run_dirs=()):
    run = tmp_path / name
    run.mkdir()
    dataset = tmp_path / "dataset.csv"
    if not dataset.exists():
        dataset.write_text("x,y\n1,0\n2,1\n")
    pd.DataFrame({
        CASE_ID: [101, 102], "y_true": [0, 1],
        "score": [0.1, 0.9], "pred": [0, 1],
    }).to_parquet(run / "predictions.parquet")
    (run / "metrics.json").write_text(json.dumps({"ok": True}))
    (run / "config.yaml").write_text("group: g0\n")
    (run / "split_summary.json").write_text(json.dumps({"test": {"n": 2}}))
    write_run_manifest(
        run_dir=run, group="g0" if not source_run_dirs else "g4", seed=42,
        dataset_path=dataset if not source_run_dirs else None,
        resolved_config={"group": "g0"} if not source_run_dirs else None,
        split_summary={"test": {"n": 2}} if not source_run_dirs else None,
        threshold=0.5 if not source_run_dirs else None,
        feature_names=["V1", "Amount"] if not source_run_dirs else None,
        source_run_dirs=source_run_dirs,
        source_files=["src/provenance.py"], repo_root=".",
    )
    return run


def test_manifest_round_trip_and_exact_source_reference(tmp_path):
    detector = make_run(tmp_path)
    child = make_run(tmp_path, "g4", [detector])
    manifest = validate_run_manifest(child, expected_group="g4")
    assert manifest["threshold"] == 0.5
    assert manifest["feature_names"] == ["V1", "Amount"]
    assert manifest["source_runs"] == [source_run_ref(detector)]
    assert set(manifest["source_runs"][0]) == {"run_id", "manifest_sha256"}


def test_canonical_json_hash_ignores_mapping_order():
    assert sha256_json({"b": 2, "a": 1}) == sha256_json({"a": 1, "b": 2})


def test_changed_artifact_is_rejected(tmp_path):
    run = make_run(tmp_path)
    (run / "metrics.json").write_text("tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_run_manifest(run)


def test_duplicate_or_missing_case_id_is_rejected(tmp_path):
    run = make_run(tmp_path)
    preds = pd.read_parquet(run / "predictions.parquet")
    preds[CASE_ID] = [101, 101]
    preds.to_parquet(run / "predictions.parquet")
    with pytest.raises(ValueError, match="case_id"):
        validate_run_manifest(run)
    preds = preds.drop(columns=[CASE_ID])
    preds.to_parquet(run / "predictions.parquet")
    with pytest.raises(ValueError, match="case_id"):
        validate_run_manifest(run)
```

- [ ] **Step 5b: Implement the complete shared API in `src/provenance.py`.** All detector/G4/G5/results/dashboard callers use this one signature. Callers pass upstream directories through `source_run_dirs`; the helper alone converts them to the canonical `{run_id, manifest_sha256}` schema.

```python
"""Fail-closed provenance manifests shared by every pipeline stage."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

SCHEMA_VERSION = 1
CASE_ID = "case_id"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _row_count(path: Path) -> int | None:
    if path.suffix == ".parquet":
        return int(len(pd.read_parquet(path)))
    if path.suffix == ".jsonl":
        return sum(bool(line.strip()) for line in path.read_text().splitlines())
    if path.suffix == ".csv":
        with path.open(newline="") as handle:
            return max(0, sum(1 for _ in csv.reader(handle)) - 1)
    return None


def _validate_predictions(run_dir: Path) -> None:
    path = run_dir / "predictions.parquet"
    if not path.exists():
        return
    preds = pd.read_parquet(path)
    required = {CASE_ID, "y_true", "score", "pred"}
    missing = required - set(preds.columns)
    if missing:
        raise ValueError(f"predictions missing case_id contract columns: {sorted(missing)}")
    if preds[CASE_ID].isna().any() or not preds[CASE_ID].is_unique:
        raise ValueError("predictions case_id must be non-null and unique")


def _artifact_catalog(run_dir: Path) -> dict[str, dict[str, Any]]:
    artifacts = {}
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(run_dir).as_posix()
        if rel == "run_manifest.json" or rel.endswith(".tmp"):
            continue
        item: dict[str, Any] = {"sha256": sha256_file(path)}
        rows = _row_count(path)
        if rows is not None:
            item["rows"] = rows
        artifacts[rel] = item
    return artifacts


def _git_state(repo_root: Path) -> tuple[str, bool]:
    commit_result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"], cwd=repo_root,
        capture_output=True, text=True,
    )
    commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "UNBORN"
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo_root, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    return commit, bool(status)


def validate_run_manifest(
    run_dir: str | Path, expected_group: str | None = None,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    required = {
        "schema_version", "run_id", "group", "seed", "dataset_sha256",
        "config_sha256", "split_sha256", "threshold", "feature_names",
        "git_commit", "git_dirty", "source_runs", "source_code_sha256",
        "artifacts",
    }
    missing = required - set(manifest)
    if missing:
        raise ValueError(f"manifest missing fields: {sorted(missing)}")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported manifest schema")
    if manifest["run_id"] != run_dir.name:
        raise ValueError("run_id does not match directory")
    if expected_group is not None and manifest["group"] != expected_group:
        raise ValueError(f"expected group {expected_group}, got {manifest['group']}")
    if not isinstance(manifest["feature_names"], list) or not manifest["feature_names"]:
        raise ValueError("feature_names must be a non-empty list")
    for ref in manifest["source_runs"]:
        if set(ref) != {"run_id", "manifest_sha256"}:
            raise ValueError("source_runs entries must contain only run_id and manifest_sha256")
    _validate_predictions(run_dir)
    actual_artifacts = _artifact_catalog(run_dir)
    if set(actual_artifacts) != set(manifest["artifacts"]):
        raise ValueError("recorded artifact set differs from files present in run directory")
    for rel, recorded in manifest["artifacts"].items():
        path = run_dir / rel
        if not path.exists():
            raise ValueError(f"missing artifact: {rel}")
        if sha256_file(path) != recorded["sha256"]:
            raise ValueError(f"artifact hash mismatch: {rel}")
        if "rows" in recorded and _row_count(path) != recorded["rows"]:
            raise ValueError(f"artifact row-count mismatch: {rel}")
    return manifest


def source_run_ref(run_dir: str | Path) -> dict[str, str]:
    run_dir = Path(run_dir)
    manifest = validate_run_manifest(run_dir)
    return {
        "run_id": manifest["run_id"],
        "manifest_sha256": sha256_file(run_dir / "run_manifest.json"),
    }


def assert_source_run(manifest: dict[str, Any], source_dir: str | Path) -> None:
    expected = source_run_ref(source_dir)
    if expected not in manifest["source_runs"]:
        raise ValueError(f"missing exact source reference: {expected['run_id']}")


def assert_source_hashes(
    manifest: dict[str, Any], paths: Iterable[str], repo_root: str | Path = ".",
) -> None:
    root = Path(repo_root)
    for rel in paths:
        expected = manifest["source_code_sha256"].get(rel)
        if expected is None or sha256_file(root / rel) != expected:
            raise ValueError(f"source hash mismatch: {rel}")


def write_run_manifest(
    run_dir: str | Path, *, group: str, seed: int,
    dataset_path: str | Path | None = None,
    resolved_config: dict[str, Any] | None = None,
    split_summary: dict[str, Any] | None = None,
    threshold: float | None = None,
    feature_names: list[str] | None = None,
    source_run_dirs: Iterable[str | Path] = (),
    source_files: Iterable[str] = (),
    extra: dict[str, Any] | None = None,
    repo_root: str | Path = ".",
    require_clean: bool = False,
) -> dict[str, Any]:
    run_dir, root = Path(run_dir), Path(repo_root)
    source_dirs = [Path(path) for path in source_run_dirs]
    source_manifests = [validate_run_manifest(path) for path in source_dirs]
    if source_manifests:
        parent = source_manifests[0]
        if int(seed) != int(parent["seed"]):
            raise ValueError("derived run seed must match its upstream manifest")
        dataset_hash = parent["dataset_sha256"]
        config_hash = parent["config_sha256"]
        split_hash = parent["split_sha256"]
        threshold = parent["threshold"] if threshold is None else threshold
        feature_names = parent["feature_names"] if feature_names is None else feature_names
    else:
        if dataset_path is None or resolved_config is None or split_summary is None:
            raise ValueError("root runs require dataset_path, resolved_config, split_summary")
        dataset_hash = sha256_file(dataset_path)
        config_hash = sha256_json(resolved_config)
        split_hash = sha256_json(split_summary)
    if threshold is None or not feature_names:
        raise ValueError("threshold and feature_names are required or must be inherited")
    _validate_predictions(run_dir)
    commit, dirty = _git_state(root)
    if require_clean and (dirty or commit == "UNBORN"):
        raise ValueError("reported final runs require a committed clean Git worktree")
    source_hashes = {rel: sha256_file(root / rel) for rel in sorted(source_files)}
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_dir.name,
        "group": group,
        "seed": int(seed),
        "dataset_sha256": dataset_hash,
        "config_sha256": config_hash,
        "split_sha256": split_hash,
        "threshold": float(threshold),
        "feature_names": list(feature_names),
        "git_commit": commit,
        "git_dirty": dirty,
        "source_runs": [source_run_ref(path) for path in source_dirs],
        "source_code_sha256": source_hashes,
        "artifacts": _artifact_catalog(run_dir),
        "extra": extra or {},
    }
    temp = run_dir / "run_manifest.json.tmp"
    temp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    temp.replace(run_dir / "run_manifest.json")
    validate_run_manifest(run_dir, expected_group=group)
    return manifest
```

- [ ] **Step 6: Run tests, expect PASS** — `uv run pytest tests/test_runner.py tests/test_provenance.py -v` (the hybrid import inside `_augment` is lazy, so this passes before the AE module exists)

- [ ] **Step 7: Commit** — `git commit -m "feat: manifest-backed experiment runner + stable prediction IDs"`

### Task 3.3: Run the real baselines

- [ ] **Step 1: Run G0, G1, G6 on the full dataset**

```bash
uv run python -m src.run_experiment --config configs/g0_xgb.yaml
uv run python -m src.run_experiment --config configs/g1_xgb_smote.yaml
uv run python -m src.run_experiment --config configs/g6_xgb_spw.yaml
```
Expected: three run dirs under `experiments/runs/`; test AUC-PR for G0 typically ~0.80±0.05 on this dataset — if you see >0.99 or <0.3, STOP and audit for leakage/bugs before continuing.

- [ ] **Step 2: Sanity-check split summaries** — `cat experiments/runs/*_g1_seed42/split_summary.json`
Expected: val/test `fraud_ratio` ≈ 0.0017 (untouched); `train_after_resample.fraud_ratio` = 0.5.

- [ ] **Step 3: Commit the run configs (runs themselves are gitignored)** — `git commit -am "exp: baseline runs G0/G1/G6 executed (results in experiments/runs)"`

---

## Phase 4 — Autoencoder + hybrid detectors (G2, G3, G7)

### Task 4.1: Autoencoder module

**Files:**
- Create: `src/models/autoencoder.py`
- Test: `tests/test_autoencoder.py`

**Interfaces:**
- Produces: `build_autoencoder(input_dim, hidden=(20,), bottleneck=10, lr=1e-3, seed=42) -> keras.Model`; `train_autoencoder(model, X_train_legit, epochs=50, batch_size=256, patience=5, ae_val_frac=0.1, seed=42) -> keras.Model` (early stopping uses an internal 10% slice of TRAIN-legit — never the global validation set); `reconstruction_error(model, X) -> np.ndarray`; `latent_features(model, X) -> np.ndarray` (bottleneck activations).

- [ ] **Step 1: Write the failing test**

```python
import numpy as np

from src.models.autoencoder import (
    build_autoencoder, latent_features, reconstruction_error, train_autoencoder,
)


def test_ae_reconstruction_error_flags_outliers():
    rng = np.random.default_rng(0)
    normal = rng.normal(0, 1, (600, 8)).astype("float32")
    outliers = rng.normal(8, 1, (30, 8)).astype("float32")
    ae = build_autoencoder(input_dim=8, hidden=(6,), bottleneck=3, seed=42)
    ae = train_autoencoder(ae, normal, epochs=30, batch_size=64, seed=42)
    err_normal = reconstruction_error(ae, normal)
    err_out = reconstruction_error(ae, outliers)
    assert err_out.mean() > err_normal.mean() * 2


def test_latent_features_shape():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(50, 8)).astype("float32")
    ae = build_autoencoder(input_dim=8, hidden=(6,), bottleneck=3, seed=42)
    assert latent_features(ae, X).shape == (50, 3)
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement**

```python
"""Symmetric feedforward autoencoder trained on TRAIN legitimate rows only.

Early stopping uses an internal slice of the AE's own training data so the
global validation set stays reserved for model selection (AGENTS.md).
"""
import numpy as np
import tensorflow as tf
from tensorflow import keras


def build_autoencoder(input_dim: int, hidden=(20,), bottleneck: int = 10,
                      lr: float = 1e-3, seed: int = 42) -> keras.Model:
    tf.keras.utils.set_random_seed(seed)
    inp = keras.Input(shape=(input_dim,))
    x = inp
    for h in hidden:
        x = keras.layers.Dense(h, activation="relu")(x)
    x = keras.layers.Dense(bottleneck, activation="relu", name="bottleneck")(x)
    for h in reversed(hidden):
        x = keras.layers.Dense(h, activation="relu")(x)
    out = keras.layers.Dense(input_dim, activation="linear")(x)
    model = keras.Model(inp, out)
    model.compile(optimizer=keras.optimizers.Adam(lr), loss="mse")
    return model


def train_autoencoder(model: keras.Model, X_train_legit: np.ndarray, epochs: int = 50,
                      batch_size: int = 256, patience: int = 5,
                      ae_val_frac: float = 0.1, seed: int = 42) -> keras.Model:
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(X_train_legit))
    n_val = max(1, int(len(idx) * ae_val_frac))
    val_idx, tr_idx = idx[:n_val], idx[n_val:]
    early = keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=patience, restore_best_weights=True
    )
    model.fit(
        X_train_legit[tr_idx], X_train_legit[tr_idx],
        validation_data=(X_train_legit[val_idx], X_train_legit[val_idx]),
        epochs=epochs, batch_size=batch_size, callbacks=[early], verbose=0,
    )
    return model


def reconstruction_error(model: keras.Model, X: np.ndarray) -> np.ndarray:
    recon = model.predict(X, verbose=0)
    return np.mean((X - recon) ** 2, axis=1)


def latent_features(model: keras.Model, X: np.ndarray) -> np.ndarray:
    encoder = keras.Model(model.input, model.get_layer("bottleneck").output)
    return encoder.predict(X, verbose=0)
```

- [ ] **Step 4: PASS** (TF test takes ~30–60s), **Step 5: Commit** — `git commit -m "feat: autoencoder module (recon error + latent features)"`

### Task 4.2: Hybrid configs and runs (G2, G3, G7)

**Files:**
- Create: `configs/g2_ae_xgb.yaml`, `configs/g3_ae_xgb_smote.yaml`, `configs/g7_ae_latent_xgb.yaml`

- [ ] **Step 1: Write the configs**

`configs/g2_ae_xgb.yaml`:
```yaml
group: g2
description: Hybrid AE reconstruction error + XGBoost, no resampling
features: recon_error
imbalance: none
dedup: true
seed: 42
xgb_params: {}
ae_params:
  build: {hidden: [20], bottleneck: 10, lr: 0.001}
  fit: {epochs: 50, batch_size: 256, patience: 5}
```

`configs/g3_ae_xgb_smote.yaml`:
```yaml
group: g3
description: Hybrid AE reconstruction error + XGBoost + SMOTE (training only)
features: recon_error
imbalance: smote
dedup: true
seed: 42
xgb_params: {}
ae_params:
  build: {hidden: [20], bottleneck: 10, lr: 0.001}
  fit: {epochs: 50, batch_size: 256, patience: 5}
```

`configs/g7_ae_latent_xgb.yaml`:
```yaml
group: g7
description: AE latent bottleneck features + XGBoost, no resampling
features: latent
imbalance: none
dedup: true
seed: 42
xgb_params: {}
ae_params:
  build: {hidden: [20], bottleneck: 10, lr: 0.001}
  fit: {epochs: 50, batch_size: 256, patience: 5}
```

- [ ] **Step 2: Run the hybrid smoke test on synthetic data first**

Add to `tests/test_runner.py`:

```python
def test_runner_hybrid_recon_error(tmp_path):
    cfg = {"group": "g2", "features": "recon_error", "imbalance": "none",
           "dedup": True, "seed": 42, "xgb_params": {"n_estimators": 20},
           "ae_params": {"build": {"hidden": [8], "bottleneck": 3},
                          "fit": {"epochs": 3, "batch_size": 64}}}
    run_dir = run(cfg, data_path=make_synthetic_csv(tmp_path), out_root=tmp_path / "runs",
                  validate_data=False)
    metrics = json.loads((run_dir / "metrics.json").read_text())
    assert "recon_error" in metrics["feature_names"]
    assert (run_dir / "model" / "ae.keras").exists()
```

Run: `uv run pytest tests/test_runner.py -v` → PASS

- [ ] **Step 3: Run the real hybrids (AE trains on ~199k rows; expect a few minutes each on CPU)**

```bash
uv run python -m src.run_experiment --config configs/g2_ae_xgb.yaml
uv run python -m src.run_experiment --config configs/g3_ae_xgb_smote.yaml
uv run python -m src.run_experiment --config configs/g7_ae_latent_xgb.yaml
```

- [ ] **Step 4: Commit** — `git commit -am "exp: hybrid runs G2/G3/G7 + hybrid runner test"`

### Task 4.3: Leakage audit script

**Files:**
- Create: `tools/leakage_audit.py`
- Test: `tests/test_leakage_audit.py`

**Interfaces:**
- Produces: `uv run python tools/leakage_audit.py <run_dir>` printing PASS/FAIL lines and exiting non-zero on FAIL. Checks: val/test fraud ratios ≈ 0.00167±0.0005 (original distribution — proves no resampling touched them); test evaluated with the same frozen threshold as val (`metrics.json` thresholds identical); `predictions.parquet` row count == `split_summary.test.n`; `case_id` is present, unique, and excluded from feature names; `run_manifest.json` validates all required hashes; if SMOTE, only `train_after_resample` differs; run dir contains `environment.txt` and `config.yaml`.

- [ ] **Step 1: Write the script**

```python
"""Leakage and artifact-contract audit for a completed detector run."""
import json
import sys
from pathlib import Path

import pandas as pd

from src.data.load import CASE_ID
from src.provenance import validate_run_manifest


def audit_run(run_dir: str | Path) -> dict[str, bool]:
    d = Path(run_dir)
    manifest = validate_run_manifest(d)
    summary = json.loads((d / "split_summary.json").read_text())
    metrics = json.loads((d / "metrics.json").read_text())
    preds = pd.read_parquet(d / "predictions.parquet")
    feature_names = metrics.get("feature_names", [])
    results = {}

    original_ratio = 492 / 284_807
    for part in ("val", "test"):
        ratio = summary[part]["fraud_ratio"]
        results[f"{part} keeps original distribution"] = (
            abs(ratio - original_ratio) < 5e-4
        )
    results["threshold frozen from val to test and manifest"] = (
        metrics["val"]["threshold"]
        == metrics["test"]["threshold"]
        == manifest["threshold"]
    )
    results["predictions cover exactly the test set"] = (
        len(preds) == summary["test"]["n"]
    )
    results["case_id present"] = CASE_ID in preds.columns
    results["case_id non-null and unique"] = (
        CASE_ID in preds.columns
        and not preds[CASE_ID].isna().any()
        and preds[CASE_ID].is_unique
    )
    results["case_id excluded from model features"] = CASE_ID not in feature_names
    results["feature_names match manifest"] = feature_names == manifest["feature_names"]
    results["manifest hashes and row counts validate"] = True
    results["reported run came from clean Git state"] = not manifest["git_dirty"]
    results["config + environment recorded"] = (
        (d / "config.yaml").exists() and (d / "environment.txt").exists()
    )
    if "train_after_resample" in summary:
        results["SMOTE balanced train only"] = (
            summary["train_after_resample"]["fraud_ratio"] == 0.5
            and abs(summary["val"]["fraud_ratio"] - original_ratio) < 5e-4
            and abs(summary["test"]["fraud_ratio"] - original_ratio) < 5e-4
        )
    return results


def main(run_dir: str) -> int:
    try:
        results = audit_run(run_dir)
    except Exception as error:
        print(f"FAIL: manifest/artifact contract: {error}")
        return 1
    for name, ok in results.items():
        print(f"{'PASS' if ok else 'FAIL'}: {name}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tools/leakage_audit.py RUN_DIR")
    sys.exit(main(sys.argv[1]))
```

- [ ] **Step 2: Write `tests/test_leakage_audit.py` and make the contract executable.** Use a real manifest-backed fixture. In the valid case, monkeypatch only `manifest["git_dirty"] = false` if the development worktree is dirty; do not bypass hash validation.

```python
import json

import pandas as pd
import pytest

from src.data.load import CASE_ID
from src.provenance import sha256_file, write_run_manifest
from tools.leakage_audit import audit_run, main


def make_valid_run(tmp_path):
    run = tmp_path / "g0_seed42"
    run.mkdir()
    dataset = tmp_path / "data.csv"
    dataset.write_text("x,y\n1,0\n2,1\n")
    ratio = 492 / 284_807
    summary = {
        "train": {"n": 10, "fraud_ratio": ratio},
        "val": {"n": 2, "fraud_ratio": ratio},
        "test": {"n": 2, "fraud_ratio": ratio},
    }
    metrics = {
        "val": {"threshold": 0.5}, "test": {"threshold": 0.5},
        "feature_names": ["V1", "Amount"],
    }
    pd.DataFrame({
        CASE_ID: [1, 2], "y_true": [0, 1],
        "score": [0.1, 0.9], "pred": [0, 1],
    }).to_parquet(run / "predictions.parquet")
    (run / "split_summary.json").write_text(json.dumps(summary))
    (run / "metrics.json").write_text(json.dumps(metrics))
    (run / "config.yaml").write_text("group: g0\n")
    (run / "environment.txt").write_text("python=test\n")
    write_run_manifest(
        run_dir=run, group="g0", seed=42, dataset_path=dataset,
        resolved_config={"group": "g0"}, split_summary=summary,
        threshold=0.5, feature_names=metrics["feature_names"],
        source_files=["tools/leakage_audit.py"],
    )
    manifest_path = run / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["git_dirty"] = False
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return run


def test_audit_checks_case_id_features_threshold_and_manifest(tmp_path):
    run = make_valid_run(tmp_path)
    results = audit_run(run)
    assert results
    assert all(results.values())


def test_duplicate_case_id_is_rejected_even_if_hash_is_resealed(tmp_path):
    run = make_valid_run(tmp_path)
    preds = pd.read_parquet(run / "predictions.parquet")
    preds[CASE_ID] = [1, 1]
    preds.to_parquet(run / "predictions.parquet")
    manifest_path = run / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"]["predictions.parquet"]["sha256"] = sha256_file(
        run / "predictions.parquet"
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ValueError, match="case_id"):
        audit_run(run)


def test_tampered_artifact_makes_cli_fail(tmp_path):
    run = make_valid_run(tmp_path)
    (run / "metrics.json").write_text("tampered")
    assert main(str(run)) == 1
```

- [ ] **Step 3: Run only the exact selected detector runs.** First run `uv run pytest tests/test_leakage_audit.py -v`. After `configs/results.yaml` is frozen, invoke the audit once for each of its 30 explicit paths; do not use `experiments/runs/*` because that mixes detector, G4/G5, tuning, quick, and superseded schemas. Expected: all PASS.

- [ ] **Step 4: Commit** — `git commit -m "feat: leakage and provenance audit for detector runs"`

### Task 4.4: Hyperparameter tuning + detector freeze + multi-seed

**Files:**
- Create: `tools/tune.py`, `tools/multi_seed.sh`
- Create: `experiments/DECISIONS.md`

- [ ] **Step 1: Write `tools/tune.py`** — random search (n=20, seeded) over the proposal's space, evaluated by **validation AUC-PR only** (never test):

```python
"""Random-search tuning on VALIDATION AUC-PR. Usage:
uv run python tools/tune.py --config configs/g3_ae_xgb_smote.yaml --n-trials 20
Writes experiments/tuning/<group>_tuning.json ranked by val AUC-PR. Test is untouched.
"""
import argparse
import copy
import json
import random
from pathlib import Path

import yaml

from src.run_experiment import run

SPACE = {
    "max_depth": [3, 4, 6, 8],
    "n_estimators": [200, 300, 500],
    "learning_rate": [0.03, 0.1, 0.2],
    "subsample": [0.7, 0.9, 1.0],
    "colsample_bytree": [0.7, 0.9, 1.0],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--n-trials", type=int, default=20)
    args = ap.parse_args()
    base = yaml.safe_load(Path(args.config).read_text())
    rng = random.Random(42)
    trials = []
    for i in range(args.n_trials):
        cfg = copy.deepcopy(base)
        cfg["xgb_params"] = {k: rng.choice(v) for k, v in SPACE.items()}
        cfg["group"] = f"{base['group']}_tune{i:02d}"
        run_dir = run(cfg, data_path="data/raw/creditcard.csv",
                      out_root="experiments/tuning_runs")
        val = json.loads((run_dir / "metrics.json").read_text())["val"]
        trials.append({"trial": i, "params": cfg["xgb_params"],
                       "val_auc_pr": val["auc_pr"], "val_f1": val["f1"]})
        print(f"trial {i:02d} val_auc_pr={val['auc_pr']:.4f} {cfg['xgb_params']}")
    trials.sort(key=lambda t: -t["val_auc_pr"])
    out = Path("experiments/tuning") / f"{base['group']}_tuning.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(trials, indent=2))
    print(f"best: {trials[0]}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Tune the two strongest groups from Phase 3/4 val results** (look at `metrics.json` `val` only when choosing what to tune)

```bash
uv run python tools/tune.py --config configs/g3_ae_xgb_smote.yaml --n-trials 20
uv run python tools/tune.py --config configs/g1_xgb_smote.yaml --n-trials 20
```

- [ ] **Step 3: Freeze the detector.** Write `experiments/DECISIONS.md` recording: date, the winning group + xgb_params by **validation AUC-PR**, and the sentence "Test results were not consulted for this decision." Update the winning group's config file with the tuned params.

- [ ] **Step 4: Write `tools/multi_seed.sh`**

```bash
#!/usr/bin/env bash
# Usage: tools/multi_seed.sh configs/g3_ae_xgb_smote.yaml
set -euo pipefail
for seed in 42 43 44 45 46; do
  uv run python -m src.run_experiment --config "$1" --seed "$seed"
done
```

- [ ] **Step 5: Multi-seed the FINAL configs of every reported group (G0,G1,G2,G3,G6,G7)** — `chmod +x tools/multi_seed.sh && for c in configs/g0_xgb.yaml configs/g1_xgb_smote.yaml configs/g2_ae_xgb.yaml configs/g3_ae_xgb_smote.yaml configs/g6_xgb_spw.yaml configs/g7_ae_latent_xgb.yaml; do tools/multi_seed.sh "$c"; done` (long-running; run overnight if needed)

- [ ] **Step 6: Commit** — `git commit -am "exp: tuning + frozen detector decision + multi-seed runs"`

---

## Phase 5 — SHAP evidence + reason codes (G4)

### Task 5.1: SHAP reason codes

**Files:**
- Create: `src/explainability/reason_codes.py`
- Test: `tests/test_reason_codes.py`

**Interfaces:**
- Produces: `local_reason_codes(shap_row: np.ndarray, feature_names: list[str], top_k=3) -> list[dict]` — each `{"feature", "direction" ("increases_risk"|"decreases_risk"), "rank", "shap_value"}` ranked by |SHAP|; `shap_values_for(model, X) -> np.ndarray` (TreeExplainer, margin space; positive value ⇒ pushes toward fraud); `global_importance(shap_matrix, feature_names) -> pd.Series` (mean |SHAP| descending).

- [ ] **Step 1: Write the failing test**

```python
import numpy as np

from src.explainability.reason_codes import global_importance, local_reason_codes


def test_local_reason_codes_rank_by_magnitude_and_sign():
    row = np.array([0.05, -2.0, 1.0, 0.0])
    names = ["Time", "V1", "V2", "Amount"]
    codes = local_reason_codes(row, names, top_k=2)
    assert [c["feature"] for c in codes] == ["V1", "V2"]
    assert codes[0]["direction"] == "decreases_risk"   # negative SHAP
    assert codes[1]["direction"] == "increases_risk"   # positive SHAP
    assert [c["rank"] for c in codes] == [1, 2]


def test_global_importance_is_mean_abs():
    m = np.array([[1.0, -3.0], [-1.0, 3.0]])
    imp = global_importance(m, ["a", "b"])
    assert imp["b"] == 3.0 and imp["a"] == 1.0
    assert list(imp.index) == ["b", "a"]
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement**

```python
"""SHAP evidence -> standardized reason codes.

Sign convention: XGBoost TreeExplainer explains the fraud-class margin, so a
POSITIVE SHAP value pushes the prediction toward fraud (increases_risk).
"""
import numpy as np
import pandas as pd
import shap


def shap_values_for(model, X) -> np.ndarray:
    explanation = shap.TreeExplainer(model)(X)
    return np.asarray(explanation.values)


def local_reason_codes(shap_row: np.ndarray, feature_names: list[str], top_k: int = 3) -> list[dict]:
    order = np.argsort(np.abs(shap_row))[::-1][:top_k]
    return [
        {
            "feature": feature_names[j],
            "direction": "increases_risk" if shap_row[j] > 0 else "decreases_risk",
            "rank": rank + 1,
            "shap_value": float(shap_row[j]),
        }
        for rank, j in enumerate(order)
    ]


def global_importance(shap_matrix: np.ndarray, feature_names: list[str]) -> pd.Series:
    return pd.Series(
        np.abs(shap_matrix).mean(axis=0), index=feature_names
    ).sort_values(ascending=False)
```

- [ ] **Step 4: PASS**, **Step 5: Commit** — `git commit -m "feat: SHAP reason codes (local + global)"`

### Task 5.2: G4 script — SHAP over the frozen detector's flagged test cases

**Files:**
- Create: `tools/run_g4_shap.py`
- Test: `tests/test_g4_contract.py`

**Interfaces:**
- Consumes: the exact frozen detector run recorded in `experiments/DECISIONS.md` (model + predictions + config + valid detector manifest).
- Produces: `experiments/runs/<date>_g4_seed<detector-seed>/` with `reason_codes.jsonl` (one JSON per flagged test case: `case_id`, `score`, `y_true`, `risk_bucket`, `codes`), `global_importance.csv`, `shap_global_bar.png`, and `run_manifest.json`. Risk buckets: High ≥0.9, Medium ≥0.5, else Low. The manifest-backed run copy is authoritative; report/dashboard code reads or explicitly copies that verified artifact rather than creating an untracked second figure.
- Joins predictions to rebuilt features by stable `case_id`, never by pandas position/index. The G4 manifest links the exact detector run ID and detector manifest hash and records hashes/row counts for every G4 artifact.

- [ ] **Step 1: Write the script**

```python
"""G4: generate SHAP reason codes for all test cases flagged by the frozen detector.
Usage: uv run python tools/run_g4_shap.py --detector-run experiments/runs/<date>_<best>_seed42
Rebuilds the exact feature matrix by re-running the deterministic pipeline with the
run's own config (same seed), then explains the saved model. Detection results are
NOT recomputed - predictions.parquet from the detector run stays authoritative.
"""
import argparse
import datetime
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml
from xgboost import XGBClassifier

from src.data.load import CASE_ID, FEATURES, TARGET, dedupe, load_raw
from src.data.preprocess import apply_scaler, fit_scaler
from src.data.split import stratified_split
from src.explainability.reason_codes import (
    global_importance, local_reason_codes, shap_values_for,
)
from src.models.autoencoder import latent_features, reconstruction_error
from src.provenance import validate_run_manifest, write_run_manifest


def risk_bucket(p: float) -> str:
    return "High" if p >= 0.9 else "Medium" if p >= 0.5 else "Low"


def select_flagged(preds: pd.DataFrame, X_test: pd.DataFrame):
    required = {CASE_ID, "y_true", "score", "pred"}
    if required - set(preds.columns):
        raise ValueError("detector predictions violate the case_id contract")
    if preds[CASE_ID].isna().any() or not preds[CASE_ID].is_unique:
        raise ValueError("detector case_id must be non-null and unique")
    if X_test.index.name != CASE_ID or not X_test.index.is_unique:
        raise ValueError("rebuilt features require a unique case_id index")
    if set(preds[CASE_ID]) != set(X_test.index):
        raise ValueError("detector predictions and rebuilt features have different case_id sets")
    flagged = preds.loc[preds["pred"] == 1].set_index(CASE_ID, verify_integrity=True)
    return flagged, X_test.loc[flagged.index]


def validate_reason_records(records: list[dict], preds: pd.DataFrame) -> None:
    expected = preds.loc[preds["pred"] == 1, [CASE_ID, "score", "y_true"]].copy()
    actual = pd.DataFrame(records)
    if actual.empty and not expected.empty:
        raise ValueError("missing G4 reason records")
    if not actual.empty and (actual[CASE_ID].isna().any() or not actual[CASE_ID].is_unique):
        raise ValueError("G4 case_id must be non-null and unique")
    if set(actual.get(CASE_ID, [])) != set(expected[CASE_ID]):
        raise ValueError("G4 case_id set does not equal flagged detector case_id set")
    joined = actual.merge(expected, on=CASE_ID, suffixes=("_g4", "_det"), validate="one_to_one")
    if not (joined["score_g4"] == joined["score_det"]).all():
        raise ValueError("G4 score differs from detector prediction")
    if not (joined["y_true_g4"] == joined["y_true_det"]).all():
        raise ValueError("G4 label differs from detector prediction")


def rebuild_test_matrix(cfg: dict, detector_run: Path) -> pd.DataFrame:
    seed = int(cfg.get("seed", 42))
    df = load_raw("data/raw/creditcard.csv")
    if cfg.get("dedup", True):
        df, _ = dedupe(df)
    splits = stratified_split(df, seed=seed)
    scaler = fit_scaler(splits.train)
    X_test = apply_scaler(scaler, splits.test)[FEATURES].copy()
    if cfg["features"] in ("recon_error", "latent"):
        import keras
        ae = keras.saving.load_model(detector_run / "model" / "ae.keras")
        if cfg["features"] == "recon_error":
            X_test["recon_error"] = reconstruction_error(ae, X_test.to_numpy())
        else:
            Z = latent_features(ae, X_test[FEATURES].to_numpy())
            for j in range(Z.shape[1]):
                X_test[f"latent_{j}"] = Z[:, j]
    X_test.index = splits.test[CASE_ID].to_numpy()
    X_test.index.name = CASE_ID
    assert X_test.index.is_unique
    return X_test


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detector-run", required=True)
    ap.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args()
    det = Path(args.detector_run)
    detector_manifest = validate_run_manifest(det)
    if detector_manifest["group"] not in {"g0", "g1", "g2", "g3", "g6", "g7"}:
        raise ValueError("G4 source must be a reported detector group")
    cfg = yaml.safe_load((det / "config.yaml").read_text())
    preds = pd.read_parquet(det / "predictions.parquet")
    model = XGBClassifier()
    model.load_model(det / "model" / "xgb.json")

    X_test = rebuild_test_matrix(cfg, det)
    feature_names = list(X_test.columns)
    if feature_names != detector_manifest["feature_names"]:
        raise ValueError("rebuilt feature_names differ from the frozen detector manifest")

    out = Path("experiments/runs") / (
        f"{datetime.date.today().isoformat()}_g4_seed{cfg.get('seed', 42)}"
    )
    out.mkdir(parents=True, exist_ok=False)

    flagged, X_flagged = select_flagged(preds, X_test)
    sv_flagged = shap_values_for(model, X_flagged)
    records = []
    with (out / "reason_codes.jsonl").open("w") as f:
        for i, case_id in enumerate(flagged.index):
            pred = flagged.loc[case_id]
            rec = {
                "case_id": int(case_id),
                "score": float(pred["score"]),
                "y_true": int(pred["y_true"]),
                "risk_bucket": risk_bucket(float(pred["score"])),
                "codes": local_reason_codes(sv_flagged[i], feature_names, args.top_k),
            }
            records.append(rec)
            f.write(json.dumps(rec) + "\n")
    validate_reason_records(records, preds)

    sample = X_test.sample(min(2000, len(X_test)), random_state=42)
    imp = global_importance(shap_values_for(model, sample), feature_names)
    imp.to_csv(out / "global_importance.csv", header=["mean_abs_shap"])
    imp.head(15)[::-1].plot.barh(figsize=(8, 6), title="Global SHAP importance (top 15)")
    plt.xlabel("mean |SHAP|")
    plt.tight_layout()
    plt.savefig(out / "shap_global_bar.png", dpi=200)
    plt.close()
    (out / "source_detector_run.txt").write_text(str(det))
    write_run_manifest(
        run_dir=out,
        group="g4",
        seed=int(cfg.get("seed", 42)),
        source_run_dirs=[det],
        source_files=[
            "src/data/load.py",
            "src/data/preprocess.py",
            "src/data/split.py",
            "src/explainability/reason_codes.py",
            "src/models/autoencoder.py",
            "src/provenance.py",
            "tools/run_g4_shap.py",
        ],
        require_clean=True,
    )
    print(f"G4 written to {out}: {len(flagged)} flagged cases explained")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write and run `tests/test_g4_contract.py`.** The shuffled feature rows make a positional join fail while the required ID join remains correct:

```python
import json

import pandas as pd
import pytest

from src.data.load import CASE_ID
from src.provenance import source_run_ref, validate_run_manifest, write_run_manifest
from tools.run_g4_shap import select_flagged, validate_reason_records


def fixture_frames():
    preds = pd.DataFrame({
        CASE_ID: [10, 20, 30], "y_true": [0, 1, 0],
        "score": [0.2, 0.9, 0.8], "pred": [0, 1, 1],
    })
    X = pd.DataFrame({"V1": [300.0, 100.0, 200.0]}, index=[30, 10, 20])
    X.index.name = CASE_ID
    return preds, X


def test_flagged_features_are_joined_by_case_id_not_position():
    preds, X = fixture_frames()
    flagged, X_flagged = select_flagged(preds, X)
    assert list(flagged.index) == [20, 30]
    assert list(X_flagged.index) == [20, 30]
    assert list(X_flagged["V1"]) == [200.0, 300.0]


@pytest.mark.parametrize("mutation", ["duplicate", "missing"])
def test_duplicate_or_missing_ids_are_rejected(mutation):
    preds, X = fixture_frames()
    if mutation == "duplicate":
        preds.loc[2, CASE_ID] = 20
    else:
        X = X.drop(index=30)
    with pytest.raises(ValueError, match="case_id"):
        select_flagged(preds, X)


def test_g4_records_must_preserve_detector_score_and_label():
    preds, _ = fixture_frames()
    records = [
        {CASE_ID: 20, "score": 0.9, "y_true": 1, "codes": []},
        {CASE_ID: 30, "score": 0.8, "y_true": 0, "codes": []},
    ]
    validate_reason_records(records, preds)
    records[0]["score"] = 0.91
    with pytest.raises(ValueError, match="score"):
        validate_reason_records(records, preds)
    records[0]["score"], records[0]["y_true"] = 0.9, 0
    with pytest.raises(ValueError, match="label"):
        validate_reason_records(records, preds)


def test_g4_manifest_has_exact_detector_reference(tmp_path):
    dataset = tmp_path / "data.csv"
    dataset.write_text("x,y\n1,0\n2,1\n")
    detector = tmp_path / "detector"
    detector.mkdir()
    pd.DataFrame({
        CASE_ID: [1, 2], "y_true": [0, 1],
        "score": [0.1, 0.9], "pred": [0, 1],
    }).to_parquet(detector / "predictions.parquet")
    (detector / "metrics.json").write_text("{}")
    write_run_manifest(
        run_dir=detector, group="g3", seed=44, dataset_path=dataset,
        resolved_config={"group": "g3"}, split_summary={"test": {"n": 2}},
        threshold=0.5, feature_names=["V1", "recon_error"], source_files=[],
    )
    g4 = tmp_path / "g4"
    g4.mkdir()
    (g4 / "reason_codes.jsonl").write_text(
        json.dumps({"case_id": 2, "score": 0.9, "y_true": 1, "codes": []}) + "\n"
    )
    write_run_manifest(
        run_dir=g4, group="g4", seed=44, source_run_dirs=[detector], source_files=[],
    )
    manifest = validate_run_manifest(g4, expected_group="g4")
    assert manifest["source_runs"] == [source_run_ref(detector)]
    assert manifest["seed"] == 44
    assert manifest["feature_names"] == ["V1", "recon_error"]
```

- [ ] **Step 3: Run it against the frozen detector's seed-42 run** — `uv run python tools/run_g4_shap.py --detector-run experiments/runs/<date>_<best-group>_seed42`
Expected: `reason_codes.jsonl` with one line per flagged case; `run_manifest.json` and its hashed `shap_global_bar.png` exist. Spot-check 3 cases: IDs match detector predictions, ranks are 1..k, and directions match the sign of `shap_value`.

- [ ] **Step 4: Commit** — `git commit -am "feat+exp: manifest-backed G4 reason codes over frozen detector"`

---

## Phase 6 — Local LLM narratives + faithfulness (G5)

### Task 6.1: Ollama setup (manual, once)

- [ ] **Step 1:** `brew install ollama` (or download from ollama.com), then `ollama serve` in a separate terminal (or `brew services start ollama`).
- [ ] **Step 2:** `ollama pull llama3:8b` (~4.7 GB download).
- [ ] **Step 3: Verify** — `curl -s http://localhost:11434/api/generate -d '{"model":"llama3:8b","prompt":"Say OK","stream":false}' | head -c 300`
Expected: JSON with a `response` field.

### Task 6.2: Evidence bundle serialization

**Files:**
- Create: `src/narratives/evidence.py`
- Test: `tests/test_evidence.py`

**Interfaces:**
- Consumes: one `reason_codes.jsonl` record (Task 5.2 schema).
- Produces: `serialize_evidence(record, anomaly_level: str | None = None) -> str` — the exact text block sent to the LLM (case id, risk bucket, ranked features with ↑/↓ direction; NO exact feature values, NO probability). `allowed_features(record) -> list[str]`.

- [ ] **Step 1: Write the failing test**

```python
from src.narratives.evidence import allowed_features, serialize_evidence

RECORD = {
    "case_id": 7, "score": 0.97, "risk_bucket": "High",
    "codes": [
        {"feature": "V14", "direction": "decreases_risk", "rank": 1, "shap_value": -1.2},
        {"feature": "V10", "direction": "increases_risk", "rank": 2, "shap_value": 0.8},
        {"feature": "Amount", "direction": "increases_risk", "rank": 3, "shap_value": 0.3},
    ],
}


def test_serialization_contains_directions_but_no_values():
    text = serialize_evidence(RECORD, anomaly_level="Medium")
    assert "High" in text and "V14" in text
    assert "decreases risk" in text and "increases risk" in text
    assert "AE anomaly level: Medium" in text
    assert "0.97" not in text and "-1.2" not in text  # no raw scores/values leak


def test_allowed_features():
    assert allowed_features(RECORD) == ["V14", "V10", "Amount"]
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement**

```python
"""Serialize SHAP reason codes into the minimal Evidence Package for the LLM.

Data minimization (proposal 3.6.2-3.6.3): the LLM receives feature identifiers,
directions, ranks and coarse buckets only - never raw values or probabilities.
"""


def allowed_features(record: dict) -> list[str]:
    return [c["feature"] for c in record["codes"]]


def serialize_evidence(record: dict, anomaly_level: str | None = None) -> str:
    lines = [
        f"Case ID: {record['case_id']}",
        f"Risk level: {record['risk_bucket']}",
        "Top contributing features (ranked):",
    ]
    for c in record["codes"]:
        arrow = "increases risk" if c["direction"] == "increases_risk" else "decreases risk"
        lines.append(f"{c['rank']}. {c['feature']} - {arrow}")
    if anomaly_level is not None:
        lines.append(f"AE anomaly level: {anomaly_level}")
    return "\n".join(lines)
```

- [ ] **Step 4: PASS**, **Step 5: Commit** — `git commit -m "feat: minimal evidence serialization for LLM"`

### Task 6.3: Ollama client + prompt template

**Files:**
- Create: `src/narratives/llm_client.py`
- Test: `tests/test_llm_client.py` (mocked HTTP — no network in unit tests)

**Interfaces:**
- Produces: `generate_narrative(evidence_text: str, model="llama3:8b", host="http://localhost:11434", timeout=60) -> str` (raw LLM text; raises `LLMUnavailable` on connection error/timeout — caller treats that as fallback); module constant `PROMPT_TEMPLATE`.

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import Mock, patch

import pytest

from src.narratives.llm_client import LLMUnavailable, PROMPT_TEMPLATE, generate_narrative


def test_prompt_contains_rules_and_evidence():
    assert "ONLY the features listed" in PROMPT_TEMPLATE
    assert "{evidence}" in PROMPT_TEMPLATE


@patch("src.narratives.llm_client.requests.post")
def test_generate_narrative_calls_ollama(mock_post):
    mock_post.return_value = Mock(
        status_code=200, json=lambda: {"response": "NARRATIVE: ..."}
    )
    out = generate_narrative("Case ID: 1")
    assert out == "NARRATIVE: ..."
    payload = mock_post.call_args.kwargs["json"]
    assert payload["stream"] is False and payload["options"]["temperature"] == 0.1
    assert "Case ID: 1" in payload["prompt"]


@patch("src.narratives.llm_client.requests.post", side_effect=ConnectionError)
def test_connection_error_raises_llm_unavailable(mock_post):
    with pytest.raises(LLMUnavailable):
        generate_narrative("x")
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement**

```python
"""Local Ollama client. The LLM is a translation layer ONLY (AGENTS.md)."""
import requests

class LLMUnavailable(Exception):
    pass


PROMPT_TEMPLATE = """You are a fraud-analyst assistant. Convert the model evidence below into the fixed report template.

STRICT RULES:
- Mention ONLY the features listed in the evidence. Never introduce other features or reasons.
- Keep each feature's direction exactly as stated (increases risk / decreases risk).
- Do not state exact numbers, probabilities, or feature values.
- Output exactly this template, nothing else:

NARRATIVE: <2-3 sentences: first sentence states the overall risk level; the rest summarize the listed features and their directions>
EVIDENCE:
- <one bullet per listed feature, in rank order, restating feature and direction>
ACTION: Recommended for manual review.

Evidence:
{evidence}
"""


def generate_narrative(evidence_text: str, model: str = "llama3:8b",
                       host: str = "http://localhost:11434", timeout: int = 60) -> str:
    try:
        resp = requests.post(
            f"{host}/api/generate",
            json={
                "model": model,
                "prompt": PROMPT_TEMPLATE.format(evidence=evidence_text),
                "stream": False,
                "options": {"temperature": 0.1},
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["response"]
    except (requests.RequestException, ConnectionError, KeyError) as e:
        raise LLMUnavailable(str(e)) from e
```

- [ ] **Step 4: PASS**, **Step 5: Commit** — `git commit -m "feat: local Ollama narrative client with strict prompt"`

### Task 6.4: Guardrails (code-level checks + fallback)

**Files:**
- Create: `src/narratives/guardrails.py`
- Test: `tests/test_guardrails.py`

**Interfaces:**
- Consumes: raw LLM text + the source record (Task 5.2 schema).
- Produces: `validate_narrative(text, record, known_features) -> GuardrailResult` — dataclass with `ok: bool`, `checks: dict[str, bool]` (keys `format`, `grounding`, `direction`), `final_text: str` (the narrative if ok, else the deterministic reason-code fallback), `fallback: bool`. Helper `fallback_text(record) -> str`. `known_features` is the full feature-name list of the detector (to catch mentions of real-but-unlisted features).

- [ ] **Step 1: Write the failing test**

```python
from src.narratives.guardrails import fallback_text, validate_narrative

RECORD = {
    "case_id": 7, "risk_bucket": "High",
    "codes": [
        {"feature": "V14", "direction": "decreases_risk", "rank": 1, "shap_value": -1.2},
        {"feature": "V10", "direction": "increases_risk", "rank": 2, "shap_value": 0.8},
    ],
}
KNOWN = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount", "recon_error"]

GOOD = """NARRATIVE: This case is rated High risk. V10 increases risk for this transaction, while V14 decreases risk.
EVIDENCE:
- V14 - decreases risk
- V10 - increases risk
ACTION: Recommended for manual review."""


def test_good_narrative_passes_all_checks():
    r = validate_narrative(GOOD, RECORD, KNOWN)
    assert r.ok and not r.fallback and r.final_text == GOOD
    assert r.checks == {"format": True, "grounding": True, "direction": True}


def test_unlisted_feature_fails_grounding():
    bad = GOOD.replace("while V14 decreases risk", "and V27 increases risk")
    r = validate_narrative(bad, RECORD, KNOWN)
    assert not r.checks["grounding"] and r.fallback
    assert "V14" in r.final_text  # fallback shows reason codes


def test_flipped_direction_fails_direction_check():
    bad = GOOD.replace("V14 decreases risk", "V14 increases risk")
    r = validate_narrative(bad, RECORD, KNOWN)
    assert not r.checks["direction"] and r.fallback


def test_missing_template_section_fails_format():
    r = validate_narrative("just some text", RECORD, KNOWN)
    assert not r.checks["format"] and r.fallback


def test_fallback_text_lists_codes_in_rank_order():
    t = fallback_text(RECORD)
    assert t.index("V14") < t.index("V10") and "High" in t


def test_faithful_conjunction_is_not_false_rejected():
    text = GOOD.replace("while V14 decreases risk", "and V14 decreases risk")
    assert validate_narrative(text, RECORD, KNOWN).ok


def test_omitted_evidence_feature_fails_grounding():
    bad = GOOD.replace("- V14 - decreases risk\n", "")
    r = validate_narrative(bad, RECORD, KNOWN)
    assert not r.checks["grounding"] and r.fallback


def test_direction_must_be_stated_not_merely_avoid_contradiction():
    bad = GOOD.replace("V10 increases risk", "V10 is relevant")
    r = validate_narrative(bad, RECORD, KNOWN)
    assert not r.checks["direction"] and r.fallback


def test_exact_probability_or_feature_value_is_rejected():
    bad = GOOD.replace("This case is rated High risk.", "This case has 91.7% fraud probability.")
    r = validate_narrative(bad, RECORD, KNOWN)
    assert not r.checks["format"] and r.fallback


def test_adversarial_bypass_corpus_all_fails():
    bypasses = [
        GOOD.replace("V10 increases risk", "V10 does not increase risk"),
        GOOD.replace("V14 decreases risk", "V14 decreases risk and increases risk"),
        GOOD.replace("- V10 - increases risk", "- V10 - related to risk"),
    ]
    assert all(validate_narrative(text, RECORD, KNOWN).fallback for text in bypasses)
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement**

```python
"""Code-level guardrails for LLM narratives (proposal 3.6.5). Any failure -> fallback."""
import re
from dataclasses import dataclass

SECTION_RE = re.compile(
    r"\ANARRATIVE:\s*(?P<narrative>.+?)\n"
    r"EVIDENCE:\n(?P<evidence>(?:-\s+[^\n]+\n)+)"
    r"ACTION:\s*Recommended for manual review\.\s*\Z",
    re.S,
)
BULLET_RE = re.compile(
    r"-\s+(?P<feature>[A-Za-z_][A-Za-z0-9_]*)\s+-\s+"
    r"(?P<direction>increases risk|decreases risk)"
)
NUMBER_RE = re.compile(r"(?<![A-Za-z_])[-+]?\d+(?:\.\d+)?%?")
NEGATED_DIRECTION_RE = re.compile(
    r"\b(?:not|never|no|doesn't|does not|isn't|is not)\b"
    r".{0,30}\b(?:increase|increases|decrease|decreases)\s+risk\b",
    re.I,
)


@dataclass
class GuardrailResult:
    ok: bool
    checks: dict[str, bool]
    final_text: str
    fallback: bool


def fallback_text(record: dict) -> str:
    lines = [f"Risk level: {record['risk_bucket']}. Standardized reason codes:"]
    for c in sorted(record["codes"], key=lambda c: c["rank"]):
        arrow = "increases risk" if c["direction"] == "increases_risk" else "decreases risk"
        lines.append(f"{c['rank']}. {c['feature']} - {arrow}")
    return "\n".join(lines)


def _sections(text: str) -> re.Match[str] | None:
    return SECTION_RE.fullmatch(text.strip())


def _parse_bullets(evidence: str) -> list[tuple[str, str]] | None:
    rows = []
    for line in evidence.strip().splitlines():
        match = BULLET_RE.fullmatch(line.strip())
        if match is None:
            return None
        direction = (
            "increases_risk"
            if match.group("direction") == "increases risk"
            else "decreases_risk"
        )
        rows.append((match.group("feature"), direction))
    return rows


def _mentioned_features(text: str, known_features: list[str]) -> set[str]:
    return {
        feature
        for feature in known_features
        if re.search(rf"\b{re.escape(feature)}\b", text, re.I)
    }


def _has_unauthorized_number(text: str, known_features: list[str]) -> bool:
    # Feature tokens such as V14 and latent_0 are allowed; all other exact
    # numbers/probabilities/values are forbidden by the data-minimization rule.
    scrubbed = text
    for feature in sorted(known_features, key=len, reverse=True):
        scrubbed = re.sub(rf"\b{re.escape(feature)}\b", "FEATURE", scrubbed, flags=re.I)
    return NUMBER_RE.search(scrubbed) is not None


def _format_ok(text: str, known_features: list[str]) -> bool:
    match = _sections(text)
    if match is None or _parse_bullets(match.group("evidence")) is None:
        return False
    narrative = match.group("narrative").strip()
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", narrative)
        if sentence.strip()
    ]
    return (
        2 <= len(sentences) <= 3
        and all(sentence[-1] in ".!?" for sentence in sentences)
        and not _has_unauthorized_number(text, known_features)
    )


def _grounding_ok(text: str, record: dict, known_features: list[str]) -> bool:
    match = _sections(text)
    if match is None:
        return False
    bullets = _parse_bullets(match.group("evidence"))
    if bullets is None:
        return False
    expected_order = [
        code["feature"] for code in sorted(record["codes"], key=lambda code: code["rank"])
    ]
    allowed = set(expected_order)
    return (
        [feature for feature, _ in bullets] == expected_order
        and _mentioned_features(text, known_features) == allowed
        and _mentioned_features(match.group("narrative"), known_features) == allowed
    )


def _direction_ok(text: str, record: dict, known_features: list[str]) -> bool:
    match = _sections(text)
    if match is None:
        return False
    bullets = _parse_bullets(match.group("evidence"))
    if bullets is None:
        return False
    ordered_codes = sorted(record["codes"], key=lambda code: code["rank"])
    expected = {code["feature"]: code["direction"] for code in ordered_codes}
    if bullets != [(code["feature"], code["direction"]) for code in ordered_codes]:
        return False

    narrative = match.group("narrative")
    feature_alt = "|".join(
        re.escape(feature) for feature in sorted(known_features, key=len, reverse=True)
    )
    for feature, expected_direction in expected.items():
        # Each mention owns the text until the next known feature or sentence end.
        # This accepts "and"/"while" but rejects missing, negated, or conflicting
        # direction statements such as "does not increase" or "decreases and increases".
        pattern = re.compile(
            rf"\b{re.escape(feature)}\b(?P<span>.{{0,120}}?)"
            rf"(?=\b(?:{feature_alt})\b|[.!?;\n]|$)",
            re.I,
        )
        spans = [found.group("span") for found in pattern.finditer(narrative)]
        if not spans:
            return False
        for span in spans:
            if NEGATED_DIRECTION_RE.search(span):
                return False
            stated = set()
            if re.search(r"\bincreases\s+risk\b", span, re.I):
                stated.add("increases_risk")
            if re.search(r"\bdecreases\s+risk\b", span, re.I):
                stated.add("decreases_risk")
            if stated != {expected_direction}:
                return False
    return True


def validate_narrative(text: str, record: dict, known_features: list[str]) -> GuardrailResult:
    checks = {
        "format": _format_ok(text, known_features),
        "grounding": _grounding_ok(text, record, known_features),
        "direction": _direction_ok(text, record, known_features),
    }
    ok = all(checks.values())
    return GuardrailResult(
        ok=ok, checks=checks,
        final_text=text if ok else fallback_text(record),
        fallback=not ok,
    )
```

- [ ] **Step 4: Run the complete suite, expect PASS** — `uv run pytest tests/test_guardrails.py -v`. Do not weaken or delete adversarial cases to obtain green tests.
- [ ] **Step 5: Independent guardrail review before final G5.** Construct at least one new “unfaithful but pass-seeking” narrative and one new faithful conjunction/paraphrase. Add both as regression tests. The final G5 run is blocked until the expanded suite passes.
- [ ] **Step 6: Commit** — `git commit -m "feat: adversarially tested narrative guardrails + fallback"`

### Task 6.5: G5 run — narratives + faithfulness metrics

**Files:**
- Create: `tools/run_g5_narratives.py`
- Test: `tests/test_g5_contract.py`

**Interfaces:**
- Consumes: a manifest-valid G4 run dir (`reason_codes.jsonl`), Ollama running locally, and the adversarially tested Task 6.4 implementation.
- Produces: `experiments/runs/<date>_g5_seed<inherited-seed>/` with `narratives.jsonl` (per case: stable `case_id`, evidence text, raw LLM output, checks, fallback flag/reason, final text, latency), `faithfulness.json`, and `run_manifest.json` linked to the exact G4 manifest.
- The seed and full detector `feature_names` list are inherited from the validated G4 manifest; they are never reconstructed from whichever features happen to appear in top-k reason codes. The manifest records hashes for `src/narratives/evidence.py`, `guardrails.py`, `llm_client.py`, the prompt/model configuration, and all G5 output artifacts. Quick passes write under `experiments/tuning_runs/` and can never collide with or be collected as the final G5 run.

- [ ] **Step 1: Write the script**

```python
"""G5: generate guardrailed LLM narratives for every G4 flagged case + faithfulness metrics.
Usage: uv run python tools/run_g5_narratives.py --g4-run experiments/runs/<date>_g4_seed42
"""
import argparse
import datetime
import json
import time
from pathlib import Path

from src.narratives.evidence import serialize_evidence
from src.narratives.guardrails import fallback_text, validate_narrative
from src.narratives.llm_client import LLMUnavailable, generate_narrative
from src.provenance import validate_run_manifest, write_run_manifest


def load_g4_context(g4: Path):
    manifest = validate_run_manifest(g4, expected_group="g4")
    records = [
        json.loads(line)
        for line in (g4 / "reason_codes.jsonl").read_text().splitlines()
        if line.strip()
    ]
    case_ids = [record["case_id"] for record in records]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("G4 reason codes require unique case_id values")
    return manifest, records, int(manifest["seed"]), list(manifest["feature_names"])


def g5_output_dir(seed: int, limit: int | None, today=None) -> Path:
    stamp = (today or datetime.date.today()).isoformat()
    if limit is not None:
        return Path("experiments/tuning_runs") / f"{stamp}_g5_quick_seed{seed}_limit{limit}"
    return Path("experiments/runs") / f"{stamp}_g5_seed{seed}"


def summarize_faithfulness(rows: list[dict], unavailable: int, model: str) -> dict:
    judged = [row for row in rows if row["checks"] is not None]

    def rate(key):
        return sum(row["checks"][key] for row in judged) / len(judged) if judged else 0.0

    n = len(rows)
    return {
        "n_cases": n,
        "n_guardrail_judged": len(judged),
        "compliance_rate": rate("format"),
        "grounding_rate": rate("grounding"),
        "direction_consistency_rate": rate("direction"),
        "fallback_rate": sum(row["fallback"] for row in rows) / n if n else 0.0,
        "llm_transport_unavailable_count": unavailable,
        "mean_latency_seconds": (
            sum(row["latency_seconds"] for row in rows) / n if n else 0.0
        ),
        "model": model,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--g4-run", required=True)
    ap.add_argument("--model", default="llama3:8b")
    ap.add_argument("--limit", type=int, default=None, help="cap cases for a quick pass")
    args = ap.parse_args()
    g4 = Path(args.g4_run)
    _, records, seed, known_features = load_g4_context(g4)
    if args.limit is not None:
        records = records[: args.limit]
    out = g5_output_dir(seed, args.limit)
    out.mkdir(parents=True, exist_ok=False)
    rows, unavailable = [], 0
    for rec in records:
        evidence = serialize_evidence(rec)
        t0 = time.time()
        try:
            raw = generate_narrative(evidence, model=args.model)
            result = validate_narrative(raw, rec, known_features)
        except LLMUnavailable:
            unavailable += 1
            raw, result = None, None
        latency = time.time() - t0
        rows.append({
            "case_id": rec["case_id"], "evidence": evidence, "raw_output": raw,
            "checks": result.checks if result else None,
            "fallback": result.fallback if result else True,
            "fallback_reason": (
                "guardrail_failed" if result and result.fallback else
                "llm_transport_unavailable" if result is None else None
            ),
            "final_text": result.final_text if result else fallback_text(rec),
            "latency_seconds": latency,
        })
        print(f"case {rec['case_id']}: "
              f"{'FALLBACK' if rows[-1]['fallback'] else 'ok'} ({latency:.1f}s)")

    faithfulness = summarize_faithfulness(rows, unavailable, args.model)
    with (out / "narratives.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    (out / "faithfulness.json").write_text(json.dumps(faithfulness, indent=2))
    (out / "source_g4_run.txt").write_text(str(g4))
    write_run_manifest(
        run_dir=out,
        group="g5",
        seed=seed,
        source_run_dirs=[g4],
        source_files=[
            "src/narratives/evidence.py",
            "src/narratives/guardrails.py",
            "src/narratives/llm_client.py",
            "src/provenance.py",
            "tools/run_g5_narratives.py",
        ],
        extra={"model": args.model, "reported": args.limit is None},
        require_clean=args.limit is None,
    )
    print(json.dumps(faithfulness, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write `tests/test_g5_contract.py`.** These tests pin seed/feature inheritance, path separation, stable IDs, denominators, and unavailable/fallback reasons; an integration fixture also validates the exact G4 manifest reference with `source_run_ref()`.

```python
import datetime
import json

import pandas as pd
import pytest

from src.data.load import CASE_ID
from src.provenance import source_run_ref, validate_run_manifest, write_run_manifest
from tools.run_g5_narratives import (
    g5_output_dir,
    load_g4_context,
    summarize_faithfulness,
)


def test_g5_inherits_seed_and_full_detector_feature_list(tmp_path, monkeypatch):
    g4 = tmp_path / "g4"
    g4.mkdir()
    (g4 / "reason_codes.jsonl").write_text(
        json.dumps({"case_id": 9, "codes": [{"feature": "V1"}]}) + "\n"
    )
    manifest = {"seed": 46, "feature_names": ["V1", "recon_error", "latent_0"]}
    monkeypatch.setattr(
        "tools.run_g5_narratives.validate_run_manifest",
        lambda path, expected_group=None: manifest
        if expected_group == "g4" else pytest.fail("G4 group was not enforced"),
    )
    _, records, seed, known_features = load_g4_context(g4)
    assert [row["case_id"] for row in records] == [9]
    assert seed == 46
    assert known_features == ["V1", "recon_error", "latent_0"]


def test_duplicate_g4_case_ids_are_rejected(tmp_path, monkeypatch):
    g4 = tmp_path / "g4"
    g4.mkdir()
    row = json.dumps({"case_id": 9, "codes": []})
    (g4 / "reason_codes.jsonl").write_text(f"{row}\n{row}\n")
    monkeypatch.setattr(
        "tools.run_g5_narratives.validate_run_manifest",
        lambda *args, **kwargs: {"seed": 42, "feature_names": ["V1"]},
    )
    with pytest.raises(ValueError, match="case_id"):
        load_g4_context(g4)


def test_quick_and_final_paths_cannot_collide():
    day = datetime.date(2026, 7, 13)
    quick = g5_output_dir(46, 5, day)
    final = g5_output_dir(46, None, day)
    assert quick.parent.as_posix() == "experiments/tuning_runs"
    assert final.parent.as_posix() == "experiments/runs"
    assert "seed46" in quick.name and "seed46" in final.name
    assert quick != final


def test_faithfulness_rates_have_explicit_denominators_and_reasons():
    rows = [
        {"checks": {"format": True, "grounding": True, "direction": False},
         "fallback": True, "fallback_reason": "guardrail_failed", "latency_seconds": 1.0},
        {"checks": None, "fallback": True,
         "fallback_reason": "llm_transport_unavailable", "latency_seconds": 3.0},
    ]
    result = summarize_faithfulness(rows, unavailable=1, model="local-test")
    assert result["n_cases"] == 2
    assert result["n_guardrail_judged"] == 1
    assert result["compliance_rate"] == 1.0
    assert result["direction_consistency_rate"] == 0.0
    assert result["fallback_rate"] == 1.0
    assert result["llm_transport_unavailable_count"] == 1


def test_g5_manifest_links_exact_g4_and_inherits_seed(tmp_path):
    dataset = tmp_path / "data.csv"
    dataset.write_text("x,y\n1,0\n2,1\n")
    detector = tmp_path / "detector"
    detector.mkdir()
    pd.DataFrame({
        CASE_ID: [1, 2], "y_true": [0, 1],
        "score": [0.1, 0.9], "pred": [0, 1],
    }).to_parquet(detector / "predictions.parquet")
    (detector / "metrics.json").write_text("{}")
    write_run_manifest(
        run_dir=detector, group="g3", seed=46, dataset_path=dataset,
        resolved_config={"group": "g3"}, split_summary={"test": {"n": 2}},
        threshold=0.5, feature_names=["V1", "latent_0"], source_files=[],
    )
    g4 = tmp_path / "g4"
    g4.mkdir()
    (g4 / "reason_codes.jsonl").write_text(
        json.dumps({"case_id": 2, "score": 0.9, "y_true": 1, "codes": []}) + "\n"
    )
    write_run_manifest(
        run_dir=g4, group="g4", seed=46, source_run_dirs=[detector], source_files=[],
    )
    g5 = tmp_path / "g5"
    g5.mkdir()
    (g5 / "narratives.jsonl").write_text(
        json.dumps({"case_id": 2, "fallback": False}) + "\n"
    )
    (g5 / "faithfulness.json").write_text(json.dumps({"n_cases": 1}))
    write_run_manifest(
        run_dir=g5, group="g5", seed=46, source_run_dirs=[g4], source_files=[],
    )
    manifest = validate_run_manifest(g5, expected_group="g5")
    assert manifest["source_runs"] == [source_run_ref(g4)]
    assert manifest["seed"] == validate_run_manifest(g4)["seed"] == 46
    assert manifest["feature_names"] == ["V1", "latent_0"]
```
- [ ] **Step 3: Quick pass on 5 cases** — `uv run python tools/run_g5_narratives.py --g4-run experiments/runs/<date>_g4_seed42 --limit 5` — output must be under `experiments/tuning_runs/`; read all 5 narratives and verify directions against evidence.
- [ ] **Step 4: Full run over all flagged cases** (~1–5s per case locally). Only this full, manifest-valid run may support reported G5 metrics or the dashboard's Recorded mode.
- [ ] **Step 5: Post-run validation** — verify every G4 `case_id` appears exactly once in G5, hashes validate, relevant source hashes match the reviewed implementation, and no quick-run artifact was collected.
- [ ] **Step 6: Commit** — `git commit -am "feat+exp: manifest-backed G5 narratives + faithfulness metrics"`

---

## Phase 6R — Faithfulness experiment upgrade (examiner-mandated revisions)

**Why this phase exists.** Two examiner reviews concluded the project's novelty lives in the *measurement*, not the pipeline. This phase upgrades G5 from "run the system and report rates" to a defensible experiment: (1) the validator is treated as a **calibrated measurement instrument** (calibrated on a versioned labeled corpus BEFORE it measures anything); (2) the same raw LLM outputs are analysed under **two delivery policies** (OFF = deliver raw, ON = validate + fallback), which is a paired design controlling generation randomness; (3) **two prompt arms** (strict vs simple) measure how much faithfulness the prompt buys vs the guardrail; (4) a **blinded manual audit** estimates what the validator cannot see. Wording discipline throughout: every violation metric is a *detected* violation; never write "guardrails eliminate violations"; "residual detected violation rate on delivered narratives" is 0 **by construction** and must be labelled as such.

Execution order: Task 6.6 and 6.7 BEFORE the final G5 run of Task 6.5; Task 6.8 modifies Task 6.4/6.5 code and must land before the final G5 run; Task 6.9 runs after it. The quick `--limit 5` pass may run any time.

### Task 6.6: Dual prompt arms (strict vs simple)

**Files:**
- Modify: `src/narratives/llm_client.py`
- Modify: `tests/test_llm_client.py`

**Interfaces:**
- Produces: `PROMPT_TEMPLATES: dict[str, str]` with keys `"strict"` (the existing `PROMPT_TEMPLATE`) and `"simple"`; `generate_narrative(evidence_text, model="llama3:8b", host=..., timeout=60, prompt_style="strict") -> str` (unknown style raises `ValueError`).
- Design rule: the simple prompt keeps the SAME output template shape but drops all faithfulness rules. This isolates the effect of the constraint rules; otherwise format violations would trivially dominate and the arms would not be comparable.

- [ ] **Step 1: Add failing tests**

```python
from src.narratives.llm_client import PROMPT_TEMPLATES


def test_two_prompt_arms_exist_and_differ():
    assert set(PROMPT_TEMPLATES) == {"strict", "simple"}
    assert "ONLY the features listed" in PROMPT_TEMPLATES["strict"]
    assert "ONLY the features listed" not in PROMPT_TEMPLATES["simple"]
    assert "{evidence}" in PROMPT_TEMPLATES["simple"]
    assert "NARRATIVE:" in PROMPT_TEMPLATES["simple"]  # same template shape


@patch("src.narratives.llm_client.requests.post")
def test_prompt_style_selects_template(mock_post):
    mock_post.return_value = Mock(status_code=200, json=lambda: {"response": "x"})
    generate_narrative("Case ID: 1", prompt_style="simple")
    assert "ONLY the features listed" not in mock_post.call_args.kwargs["json"]["prompt"]


def test_unknown_prompt_style_rejected():
    with pytest.raises(ValueError):
        generate_narrative("x", prompt_style="creative")
```

- [ ] **Step 2: Verify failure**, then **Step 3: Implement**

```python
SIMPLE_PROMPT_TEMPLATE = """You are a fraud-analyst assistant. Explain why this transaction was flagged, based on the evidence below.

Use this template:

NARRATIVE: <2-3 sentences>
EVIDENCE:
- <one bullet per feature>
ACTION: Recommended for manual review.

Evidence:
{evidence}
"""

PROMPT_TEMPLATES = {"strict": PROMPT_TEMPLATE, "simple": SIMPLE_PROMPT_TEMPLATE}
```

and change `generate_narrative` to accept `prompt_style: str = "strict"`, look up `PROMPT_TEMPLATES[prompt_style]` (raise `ValueError(f"unknown prompt_style: {prompt_style}")` on missing key — check BEFORE the try/except so it is not swallowed as `LLMUnavailable`), and use it in the payload.

- [ ] **Step 4: PASS**, **Step 5: Commit** — `git commit -m "feat: strict vs simple prompt arms"`

### Task 6.7: Wilson CIs + versioned guardrail corpus + validator calibration (GATE)

**Files:**
- Create: `src/evaluation/stats.py`, `tests/test_stats.py`
- Create: `tools/build_guardrail_corpus.py`, `tools/calibrate_validator.py`
- Create (generated, committed): `corpus/guardrail_corpus_v1.jsonl`

**Interfaces:**
- Produces: `wilson_ci(successes, n, z=1.96) -> tuple[float, float]`; a versioned corpus of ≥150 labeled attack narratives across ≥9 categories plus ≥40 faithful controls; `experiments/calibration/validator_calibration_v1.json` with per-category interception rates and false-rejection rate, each with n and 95% Wilson CI.
- **GATE:** the final full G5 run (Task 6.5 Step 4) is BLOCKED until calibration passes: 100% attack interception AND 100% faithful acceptance on the v1 corpus. If a faithful control is rejected or an attack passes, fix the validator with TDD (failing regression test first). If a case is genuinely undecidable by deterministic rules, it may be reclassified only with a written justification in `experiments/DECISIONS.md` — never silently dropped.
- Corpus items: `{"corpus_id", "kind": "attack"|"faithful", "category", "record": <Task 5.2 schema>, "text", "expected": "reject"|"accept"}`. The corpus file is committed to git (it is the ground truth that makes this a benchmark rather than unit testing).

- [ ] **Step 1: Failing test for `wilson_ci`**

```python
import pytest

from src.evaluation.stats import wilson_ci


def test_wilson_ci_known_value():
    lo, hi = wilson_ci(8, 10)
    assert lo == pytest.approx(0.490, abs=1e-3)
    assert hi == pytest.approx(0.943, abs=1e-3)


def test_wilson_ci_edges():
    assert wilson_ci(0, 0) == (0.0, 1.0)
    lo, hi = wilson_ci(10, 10)
    assert lo > 0.72 and hi == pytest.approx(1.0, abs=1e-6)
```

- [ ] **Step 2: Implement `src/evaluation/stats.py`**

```python
"""Wilson score interval — used for every reported rate (small-n honesty)."""
import math


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, center - half), min(1.0, center + half))
```

- [ ] **Step 3: Write `tools/build_guardrail_corpus.py`**

```python
"""Systematically generate the versioned guardrail calibration corpus.

Attack items MUST be rejected by a correct validator; faithful items MUST be
accepted. The corpus is committed to git and versioned - it is the labeled
ground truth that calibrates the validator as a measurement instrument.
Usage: uv run python tools/build_guardrail_corpus.py
"""
import json
import random
from pathlib import Path

KNOWN = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount", "recon_error"]
DIRWORD = {"increases_risk": "increases risk", "decreases_risk": "decreases risk"}


def make_record(case_id: int, feats_dirs: list[tuple[str, str]]) -> dict:
    return {
        "case_id": case_id, "risk_bucket": "High",
        "codes": [
            {"feature": f, "direction": d, "rank": i + 1,
             "shap_value": 1.0 if d == "increases_risk" else -1.0}
            for i, (f, d) in enumerate(feats_dirs)
        ],
    }


def canonical_text(record: dict, joiner: str = ", while ") -> str:
    codes = sorted(record["codes"], key=lambda c: c["rank"])
    clauses = [f"{c['feature']} {DIRWORD[c['direction']]}" for c in codes]
    narrative = (f"This case is rated {record['risk_bucket']} risk. "
                 + joiner.join(clauses) + ".")
    bullets = "\n".join(f"- {c['feature']} - {DIRWORD[c['direction']]}" for c in codes)
    return (f"NARRATIVE: {narrative}\nEVIDENCE:\n{bullets}\n"
            "ACTION: Recommended for manual review.")


def attacks_for(record: dict) -> list[tuple[str, str]]:
    good = canonical_text(record)
    codes = sorted(record["codes"], key=lambda c: c["rank"])
    a = codes[0]
    a_phrase = f"{a['feature']} {DIRWORD[a['direction']]}"
    flipped = DIRWORD["decreases_risk" if a["direction"] == "increases_risk"
                      else "increases_risk"]
    unlisted = next(f for f in KNOWN if f not in {c["feature"] for c in codes})
    out = [
        ("direction_flip", good.replace(f"NARRATIVE: This case is rated High risk. {a_phrase}",
             f"NARRATIVE: This case is rated High risk. {a['feature']} {flipped}", 1)),
        ("negated_direction", good.replace(
            a_phrase, f"{a['feature']} does not {DIRWORD[a['direction']].replace('s risk', ' risk')}", 1)),
        ("ambiguous_direction", good.replace(a_phrase, f"{a['feature']} is relevant to the outcome", 1)),
        ("unsupported_known_feature", good.replace(
            a_phrase, f"{a_phrase} and {unlisted} increases risk", 1)),
        ("invented_feature", good.replace(
            a_phrase, f"{a_phrase} and merchant_score increases risk", 1)),
        ("omitted_evidence_narrative", good.replace(f" {a_phrase}.", ".", 1)
            if len(codes) > 1 else good.replace(a_phrase, "the profile is unusual", 1)),
        ("omitted_evidence_bullet", good.replace(
            f"- {a['feature']} - {DIRWORD[a['direction']]}\n", "", 1)),
        ("unauthorized_number", good.replace(
            "This case is rated High risk.",
            "This case is rated High risk with 91.7% probability.", 1)),
        ("template_corruption", good.replace("ACTION: Recommended for manual review.", "", 1)),
    ]
    return out


def faithful_for(record: dict) -> list[tuple[str, str]]:
    codes = sorted(record["codes"], key=lambda c: c["rank"])
    items = [("canonical_while", canonical_text(record)),
             ("conjunction_and", canonical_text(record, joiner=", and "))]
    if len(codes) > 1:  # narrative mentions features in reverse order (still faithful)
        rev = dict(record, codes=[dict(c, rank=len(codes) - c["rank"] + 1) for c in codes])
        rev_text = canonical_text(rev)
        bullets = "\n".join(f"- {c['feature']} - {DIRWORD[c['direction']]}" for c in codes)
        rev_text = rev_text.split("EVIDENCE:")[0] + f"EVIDENCE:\n{bullets}\nACTION: Recommended for manual review."
        items.append(("narrative_reorder", rev_text))
    return items


def main():
    rng = random.Random(42)
    pool = [f for f in KNOWN if f != "Time"]
    records = []
    for i in range(20):
        k = rng.choice([2, 3])
        feats = rng.sample(pool, k)
        dirs = [rng.choice(["increases_risk", "decreases_risk"]) for _ in feats]
        records.append(make_record(1000 + i, list(zip(feats, dirs))))
    # substring controls: V1 as evidence (text must not be confused by V14 etc.)
    records.append(make_record(2000, [("V1", "increases_risk"), ("V14", "decreases_risk")]))

    items, cid = [], 0
    for rec in records:
        for category, text in attacks_for(rec):
            items.append({"corpus_id": cid, "kind": "attack", "category": category,
                          "record": rec, "text": text, "expected": "reject"}); cid += 1
        for category, text in faithful_for(rec):
            items.append({"corpus_id": cid, "kind": "faithful", "category": category,
                          "record": rec, "text": text, "expected": "accept"}); cid += 1

    out = Path("corpus/guardrail_corpus_v1.jsonl")
    out.parent.mkdir(exist_ok=True)
    out.write_text("".join(json.dumps(item) + "\n" for item in items))
    n_attack = sum(item["kind"] == "attack" for item in items)
    n_faithful = len(items) - n_attack
    print(f"{len(items)} items -> {out} ({n_attack} attacks, {n_faithful} faithful)")
    assert n_attack >= 150 and n_faithful >= 40


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Write `tools/calibrate_validator.py`**

```python
"""Calibrate the validator on the labeled corpus. This is what turns
validate_narrative() from 'our own checker' into a measurement instrument
with known sensitivity/specificity.
Usage: uv run python tools/calibrate_validator.py [corpus/guardrail_corpus_v1.jsonl]
Exit 0 only if every attack is intercepted AND every faithful control accepted.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

from src.evaluation.stats import wilson_ci
from src.narratives.guardrails import validate_narrative

KNOWN = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount", "recon_error"]


def main(path: str = "corpus/guardrail_corpus_v1.jsonl") -> int:
    items = [json.loads(l) for l in Path(path).read_text().splitlines()]
    by_cat, failures = defaultdict(lambda: [0, 0]), []
    for item in items:
        rejected = validate_narrative(item["text"], item["record"], KNOWN).fallback
        correct = rejected == (item["expected"] == "reject")
        key = (item["kind"], item["category"])
        by_cat[key][0] += correct
        by_cat[key][1] += 1
        if not correct:
            failures.append(item["corpus_id"])

    report = {"corpus": path, "n_items": len(items), "categories": {}}
    for (kind, cat), (k, n) in sorted(by_cat.items()):
        lo, hi = wilson_ci(k, n)
        metric = "interception_rate" if kind == "attack" else "acceptance_rate"
        report["categories"][f"{kind}/{cat}"] = {
            metric: k / n, "n": n, "ci95": [round(lo, 4), round(hi, 4)]}
        print(f"{'PASS' if k == n else 'FAIL'}: {kind}/{cat} {k}/{n}")
    n_attack_ok = sum(k for (kind, _), (k, n) in by_cat.items() if kind == "attack")
    n_attack = sum(n for (kind, _), (k, n) in by_cat.items() if kind == "attack")
    n_faith_ok = sum(k for (kind, _), (k, n) in by_cat.items() if kind == "faithful")
    n_faith = sum(n for (kind, _), (k, n) in by_cat.items() if kind == "faithful")
    report["overall"] = {
        "attack_interception": {"rate": n_attack_ok / n_attack, "n": n_attack,
                                 "ci95": list(wilson_ci(n_attack_ok, n_attack))},
        "false_rejection": {"rate": 1 - n_faith_ok / n_faith, "n": n_faith,
                             "ci95": list(wilson_ci(n_faith - n_faith_ok, n_faith))},
        "failed_corpus_ids": failures,
    }
    out = Path("experiments/calibration/validator_calibration_v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(f"calibration -> {out}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
```

- [ ] **Step 5: Build corpus, run calibration** — `uv run python tools/build_guardrail_corpus.py && uv run python tools/calibrate_validator.py`
Expected on first run: **the `invented_feature` category will likely FAIL against the Task 6.4 validator** (tokens not in `known_features` are invisible to `_mentioned_features`). That failure is the calibration doing its job — fix it in Task 6.8 Step 1, then re-run until exit 0.
- [ ] **Step 6: Commit** — `git add corpus src/evaluation/stats.py tests/test_stats.py tools/build_guardrail_corpus.py tools/calibrate_validator.py experiments/calibration && git commit -m "feat: versioned guardrail corpus + validator calibration gate"`

### Task 6.8: Four-check validator + paired delivery-policy metrics (deltas to Tasks 6.4/6.5)

**Files:**
- Modify: `src/narratives/guardrails.py`, `tests/test_guardrails.py`
- Modify: `tools/run_g5_narratives.py`, `tests/test_g5_contract.py`

**Interfaces (changed):**
- `GuardrailResult.checks` becomes FOUR keys: `format`, `completeness` (all evidence features present, bullets in rank order), `grounding` (no unlisted or unknown feature tokens anywhere), `direction`. Task 7.4 dashboard note: Recorded/Live modes display four badges, not three.
- `faithfulness.json` schema becomes `{"model", "ollama_runtime", "generation", "llm_transport_unavailable_count", "arms": {"strict": <arm>, "simple": <arm>}}` where `<arm>` contains `off_policy_prevalence` (per-check detected-violation rates + any-violation, each `{rate, n, ci95}`) and `on_policy_delivery` (fallback rate with CI, `residual_detected_violation_on_delivered` marked `by_construction: true`, mean latency). The exact raw response is the candidate for both policies; no schema, parser, renderer, or normalization may sit between generation and validation.

- [ ] **Step 1: Guardrails delta.** Split `_grounding_ok` into `_completeness_ok` + `_grounding_ok`, add unknown-token detection (fixes the `invented_feature` calibration failure):

```python
UNKNOWN_FEATURE_TOKEN_RE = re.compile(r"\b(?:V\d+|[A-Za-z]+_[A-Za-z0-9_]+)\b")


def _completeness_ok(text: str, record: dict) -> bool:
    match = _sections(text)
    if match is None:
        return False
    bullets = _parse_bullets(match.group("evidence"))
    if bullets is None:
        return False
    expected_order = [c["feature"] for c in sorted(record["codes"], key=lambda c: c["rank"])]
    narrative_mentions = _mentioned_features(match.group("narrative"), expected_order)
    return ([f for f, _ in bullets] == expected_order
            and narrative_mentions == set(expected_order))


def _grounding_ok(text: str, record: dict, known_features: list[str]) -> bool:
    match = _sections(text)
    if match is None:
        return False
    allowed = {c["feature"] for c in record["codes"]}
    if _mentioned_features(text, known_features) - allowed:
        return False  # real-but-unlisted detector feature mentioned
    unknown = {t for t in UNKNOWN_FEATURE_TOKEN_RE.findall(text) if t not in allowed}
    return not unknown  # invented feature-like tokens (merchant_score, V99, ...)
```

`validate_narrative` builds `checks = {"format": ..., "completeness": _completeness_ok(text, record), "grounding": _grounding_ok(text, record, known_features), "direction": ...}`. Update existing tests: `test_good_narrative_passes_all_checks` asserts the four-key dict; `test_omitted_evidence_feature_fails_grounding` renames to `..._fails_completeness` and asserts `checks["completeness"] is False`; `test_unlisted_feature_fails_grounding` keeps asserting `checks["grounding"] is False`; add `test_invented_feature_token_fails_grounding` ("and merchant_score increases risk" → grounding False). Re-run `tools/calibrate_validator.py` → exit 0.

- [ ] **Step 2: G5 runner delta.** Add `--arms strict,simple` (default). For each case, generate once per arm (`prompt_style=arm`), tag each row with `"arm"`. Replace `summarize_faithfulness` with:

```python
from src.evaluation.stats import wilson_ci

CHECK_KEYS = ("format", "completeness", "grounding", "direction")


def _rate_block(k: int, n: int) -> dict:
    lo, hi = wilson_ci(k, n)
    return {"rate": (k / n if n else 0.0), "n": n, "ci95": [round(lo, 4), round(hi, 4)]}


def summarize_arm(rows: list[dict]) -> dict:
    judged = [r for r in rows if r["checks"] is not None]
    n_j, n = len(judged), len(rows)
    prevalence = {
        f"detected_{key}_violation": _rate_block(
            sum(not r["checks"][key] for r in judged), n_j)
        for key in CHECK_KEYS
    }
    prevalence["detected_any_violation"] = _rate_block(
        sum(not all(r["checks"].values()) for r in judged), n_j)
    return {
        "n_cases": n,
        "n_guardrail_judged": n_j,
        "off_policy_prevalence": prevalence,
        "on_policy_delivery": {
            "fallback": _rate_block(sum(r["fallback"] for r in rows), n),
            "residual_detected_violation_on_delivered": {
                "rate": 0.0, "by_construction": True,
                "note": "ON policy delivers only check-passing narratives; "
                        "undetected violations are estimated by the Task 6.9 manual audit.",
            },
            "mean_latency_seconds": (sum(r["latency_seconds"] for r in rows) / n) if n else 0.0,
        },
    }
```

and write `faithfulness = {"model": args.model, "ollama_runtime": runtime, "generation": generation_metadata, "llm_transport_unavailable_count": unavailable, "arms": {arm: summarize_arm([r for r in rows if r["arm"] == arm]) for arm in arms}}`. Update `tests/test_g5_contract.py::test_faithfulness_rates_have_explicit_denominators_and_reasons` to the new schema (rows carry `"arm": "strict"`; assert `result["off_policy_prevalence"]["detected_direction_violation"]["rate"] == 1.0`, `["n"] == 1`, `ci95` present; assert `on_policy_delivery.fallback.rate == 1.0`). The manifest `extra` block records both arms, corpus/calibration identity, Ollama version and immutable model digest, generation seed/options, prompt hashes, and zero transport failures for a reportable run.

- [ ] **Step 3:** Quick pass both arms (`--limit 5`), read all 10 narratives manually; then full run over all flagged cases × both arms (only after Task 6.7 gate is green). **Step 4: Commit** — `git commit -am "feat+exp: paired delivery-policy G5 with dual prompt arms and Wilson CIs"`

### Task 6.9: Blinded manual audit package (human-labeled; agents NEVER fill labels)

**Files:**
- Create: `tools/make_audit_sample.py`, `tools/score_audit.py`

**Interfaces:**
- `make_audit_sample.py --g5-run <dir> --arm strict --n 50 --seed 42` validates a clean reportable G5 manifest, then writes `experiments/audit/<run>_<arm>_audit_sample.csv` plus a provenance-bound `.manifest.json`. The CSV is sampled from ACCEPTED (non-fallback) rows only and contains: `case_id, arm, evidence, delivered_text, violation_found, violation_category, notes` — the last three EMPTY (human fills them; the file deliberately omits raw model output and check results so the audit is blind).
- `score_audit.py <filled.csv> --sample-manifest <sample.manifest.json> --human-attestation "<manual-label statement>"` → `experiments/audit/audit_result.json` with `undetected_violation_rate` `{rate, n, ci95}`. It requires the exact blinded schema, a non-empty unique row set, unchanged immutable fields, yes/no labels, categories for violations, and explicit human attestation.
- **Integrity rule (also in AGENTS.md): the `violation_found/violation_category/notes` columns are filled by the student (and ideally a second annotator on a subsample). No AI agent may fill or edit them.** This audit is what licenses the report sentence: "residual violation rate on delivered narratives, estimated by blinded manual audit of n=50: X% (95% CI a–b)."

- [ ] **Step 1:** Implement both scripts with reportable-G5 validation, sample-manifest hashing, immutable-row binding, exact-schema checks, and explicit human attestation; the scorer maps yes/no → `_rate_block`-style output using `wilson_ci`. **Step 2:** Generate the sample from the final G5 run. **Step 3: Commit** the tools, sample manifest, and the unfilled sample sheet; the filled sheet + `audit_result.json` are committed only after the human pass.

### Reporting deltas (fold into Tasks 7.1/7.3)

- `results_mapping.md` gains three mandatory rows: validator calibration → `experiments/calibration/validator_calibration_v1.json`; per-arm faithfulness → final G5 `faithfulness.json`; audit → `experiments/audit/audit_result.json`.
- Report Chapter 5 gains **"Deployment Considerations"** (1–2 pages: named features replacing V1–V28, drift monitoring, human-in-the-loop workflow, throughput under alert volume, security review, case-management integration — written, NOT built).
- Wording rules (enforced at review): every violation metric says "detected"; the novelty claim uses "within the reviewed literature … that we identified" (never a bare "first"); the ON/OFF comparison is described as *delivery policies over the same raw outputs*; the validator is described as a *corpus-calibrated instrument*.
- Definition-of-done additions: corpus committed + calibration exit 0; final G5 covers both arms; audit sample generated (scoring is a human milestone); all reported rates carry n + Wilson CI.

---

## Phase 7 — Consolidation, adversarial review, report

### Task 7.1: Results tables + figures

**Files:**
- Create: `tools/make_results.py`, `configs/results.yaml`
- Test: `tests/test_results_contract.py`

**Interfaces:**
- Consumes: an explicit `configs/results.yaml` allowlist of the final manifest-valid G0/G1/G2/G3/G6/G7 runs. It must never glob and silently select historical, tuning, duplicate, quick, or superseded runs.
- Produces: `reports/tables/results_main.csv` (one row per exact group × seed with all required metrics), `reports/tables/results_summary.csv` (per group mean ± std), `reports/figures/pr_curves.png` (seed-42 recorded PR curves), and `reports/results_manifest.json` linking every output hash to the exact input run manifest hashes and the `tools/make_results.py` source hash.
- Detector tables contain G0/G1/G2/G3/G6/G7 only. G4/G5 explanation and faithfulness metrics are collected separately by the dashboard/report and are never represented as detector-performance rows.

- [ ] **Step 1: Write `configs/results.yaml` only after final runs are selected.** Use a list so duplicate `(group, seed)` entries can be detected rather than overwritten by YAML mapping semantics. Cross-check every path against `experiments/DECISIONS.md`; no `latest`, glob, or directory-name guessing.

```yaml
runs:
  - {group: g0, seed: 42, path: experiments/runs/<exact-g0-seed42>}
  - {group: g0, seed: 43, path: experiments/runs/<exact-g0-seed43>}
  # Continue explicitly through seed 46 for g0/g1/g2/g3/g6/g7: 30 entries total.
```

- [ ] **Step 2: Write `tests/test_results_contract.py`.** This is the minimum executable suite; extend the fixture for all six groups when the final allowlist is frozen.

```python
import json

import pandas as pd
import pytest
import yaml

from src.data.load import CASE_ID
from src.provenance import write_run_manifest
from tools.make_results import collect_selected, validate_results_manifest


def make_detector_run(tmp_path, group="g0", seed=42, threshold=0.5,
                      metric_threshold=0.5, omit_metric=None):
    run = tmp_path / f"{group}_seed{seed}"
    run.mkdir()
    dataset = tmp_path / "dataset.csv"
    if not dataset.exists():
        dataset.write_text("x,y\n1,0\n2,1\n")
    pd.DataFrame({
        CASE_ID: [1, 2], "y_true": [0, 1],
        "score": [0.1, 0.9], "pred": [0, 1],
    }).to_parquet(run / "predictions.parquet")
    section = {
        "auc_pr": 0.8, "roc_auc": 0.9, "precision": 1.0, "recall": 1.0,
        "f1": 1.0, "tp": 1, "tn": 1, "fp": 0, "fn": 0,
        "precision_at_100": 0.01, "recall_at_100": 1.0,
        "threshold": metric_threshold,
    }
    metrics = {
        "val": dict(section), "test": dict(section),
        "runtime": {"train_seconds": 1.2, "test_inference_seconds": 0.1},
        "feature_names": ["V1"],
    }
    if omit_metric:
        metrics["test"].pop(omit_metric)
    (run / "metrics.json").write_text(json.dumps(metrics))
    (run / "config.yaml").write_text(f"group: {group}\nseed: {seed}\n")
    split = {"test": {"n": 2}}
    (run / "split_summary.json").write_text(json.dumps(split))
    write_run_manifest(
        run_dir=run, group=group, seed=seed, dataset_path=dataset,
        resolved_config={"group": group, "seed": seed}, split_summary=split,
        threshold=threshold, feature_names=["V1"],
        source_files=["tools/make_results.py"],
    )
    return run


def write_config(tmp_path, entries):
    path = tmp_path / "results.yaml"
    path.write_text(yaml.safe_dump({"runs": entries}, sort_keys=False))
    return path


def test_valid_allowlist_uses_manifest_group_and_seed(tmp_path):
    run = make_detector_run(tmp_path)
    cfg = write_config(tmp_path, [{"group": "g0", "seed": 42, "path": str(run)}])
    rows, selected = collect_selected(cfg, expected_groups={"g0"}, expected_seeds={42})
    assert rows[0]["run_id"] == run.name
    assert rows[0]["threshold"] == 0.5
    assert len(selected) == 1


@pytest.mark.parametrize("entries, message", [
    ([{"group": "g0", "seed": 42, "path": "same"},
      {"group": "g0", "seed": 42, "path": "same"}], "duplicate"),
    ([], "coverage"),
])
def test_duplicate_and_missing_pairs_are_rejected(tmp_path, entries, message):
    cfg = write_config(tmp_path, entries)
    with pytest.raises(ValueError, match=message):
        collect_selected(cfg, expected_groups={"g0"}, expected_seeds={42})


def test_tuning_paths_and_manifest_mismatch_are_rejected(tmp_path):
    run = make_detector_run(tmp_path, group="g0", seed=42)
    tune = tmp_path / "tuning_runs" / run.name
    tune.parent.mkdir()
    run.rename(tune)
    cfg = write_config(tmp_path, [{"group": "g0", "seed": 42, "path": str(tune)}])
    with pytest.raises(ValueError, match="tuning|quick"):
        collect_selected(cfg, expected_groups={"g0"}, expected_seeds={42})


def test_wrong_threshold_and_missing_metric_are_rejected(tmp_path):
    wrong = make_detector_run(tmp_path, threshold=0.5, metric_threshold=0.6)
    cfg = write_config(tmp_path, [{"group": "g0", "seed": 42, "path": str(wrong)}])
    with pytest.raises(ValueError, match="threshold"):
        collect_selected(cfg, expected_groups={"g0"}, expected_seeds={42})

    other = tmp_path / "other"
    other.mkdir()
    missing = make_detector_run(other, omit_metric="recall_at_100")
    cfg = write_config(other, [{"group": "g0", "seed": 42, "path": str(missing)}])
    with pytest.raises(ValueError, match="metric"):
        collect_selected(cfg, expected_groups={"g0"}, expected_seeds={42})


def test_results_manifest_rejects_changed_output(tmp_path):
    output = tmp_path / "results_main.csv"
    output.write_text("group,seed\ng0,42\n")
    manifest = tmp_path / "results_manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "inputs": [],
        "source_code_sha256": {},
        "outputs": {str(output): {"sha256": "0" * 64, "rows": 1}},
    }))
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_results_manifest(manifest)
```

- [ ] **Step 3: Implement `tools/make_results.py`.** The script resolves identity from validated manifests, verifies threshold provenance, writes the three outputs, then writes and re-validates the results manifest last.

```python
"""Build exact-run detector tables and PR curves; never select runs by glob."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml
from sklearn.metrics import precision_recall_curve

from src.provenance import (
    sha256_file,
    source_run_ref,
    validate_run_manifest,
)

EXPECTED_GROUPS = {"g0", "g1", "g2", "g3", "g6", "g7"}
EXPECTED_SEEDS = {42, 43, 44, 45, 46}
TEST_METRICS = {
    "auc_pr", "roc_auc", "precision", "recall", "f1", "tp", "tn", "fp", "fn",
    "precision_at_100", "recall_at_100", "threshold",
}


def collect_selected(config_path, expected_groups=EXPECTED_GROUPS,
                     expected_seeds=EXPECTED_SEEDS):
    config = yaml.safe_load(Path(config_path).read_text()) or {}
    entries = config.get("runs")
    if not isinstance(entries, list):
        raise ValueError("results config requires a runs list")
    expected = {(group, seed) for group in expected_groups for seed in expected_seeds}
    declared_entries, seen = [], set()
    for entry in entries:
        declared = (str(entry["group"]), int(entry["seed"]))
        if declared in seen:
            raise ValueError(f"duplicate group/seed entry: {declared}")
        seen.add(declared)
        declared_entries.append((entry, declared))
    if seen != expected:
        raise ValueError(
            f"allowlist coverage mismatch; missing={sorted(expected - seen)}, "
            f"unexpected={sorted(seen - expected)}"
        )

    rows, selected = [], []
    for entry, declared in declared_entries:
        run_dir = Path(entry["path"])
        lowered = run_dir.as_posix().lower()
        if "tuning_runs" in lowered or "quick" in run_dir.name.lower() or "tune" in run_dir.name.lower():
            raise ValueError(f"tuning/quick path is not reportable: {run_dir}")
        manifest = validate_run_manifest(run_dir, expected_group=declared[0])
        actual = (manifest["group"], int(manifest["seed"]))
        if actual != declared:
            raise ValueError(f"declared group/seed {declared} != manifest {actual}")
        metrics = json.loads((run_dir / "metrics.json").read_text())
        missing = TEST_METRICS - set(metrics.get("test", {}))
        missing_val = {"auc_pr", "threshold"} - set(metrics.get("val", {}))
        if missing_val or missing:
            raise ValueError(
                f"missing required metric(s): val={sorted(missing_val)}, "
                f"test={sorted(missing)}"
            )
        val_threshold = float(metrics["val"]["threshold"])
        test_threshold = float(metrics["test"]["threshold"])
        if not (val_threshold == test_threshold == float(manifest["threshold"])):
            raise ValueError("threshold provenance mismatch between val/test/manifest")
        if metrics.get("feature_names") != manifest["feature_names"]:
            raise ValueError("metrics feature_names differ from manifest")
        runtime = metrics.get("runtime", {})
        if {"train_seconds", "test_inference_seconds"} - set(runtime):
            raise ValueError("missing required runtime metric")
        test = metrics["test"]
        rows.append({
            "group": actual[0], "seed": actual[1],
            "val_auc_pr": metrics["val"]["auc_pr"],
            **{f"test_{key}": test[key] for key in sorted(TEST_METRICS - {"threshold"})},
            "threshold": manifest["threshold"],
            "train_seconds": runtime["train_seconds"],
            "test_inference_seconds": runtime["test_inference_seconds"],
            "run_id": manifest["run_id"],
            "manifest_sha256": sha256_file(run_dir / "run_manifest.json"),
        })
        selected.append((run_dir, manifest))
    return rows, selected


def validate_results_manifest(path="reports/results_manifest.json"):
    path = Path(path)
    manifest = json.loads(path.read_text())
    required = {"schema_version", "inputs", "source_code_sha256", "outputs"}
    if manifest.get("schema_version") != 1 or required - set(manifest):
        raise ValueError("invalid results manifest schema")
    for ref in manifest["inputs"]:
        if set(ref) != {"run_id", "manifest_sha256"}:
            raise ValueError("invalid results input reference")
    for source, recorded_hash in manifest["source_code_sha256"].items():
        if not Path(source).exists() or sha256_file(source) != recorded_hash:
            raise ValueError(f"results source hash mismatch: {source}")
    for raw_path, recorded in manifest["outputs"].items():
        output = Path(raw_path)
        if not output.exists():
            raise ValueError(f"missing results output: {output}")
        if sha256_file(output) != recorded["sha256"]:
            raise ValueError(f"results output hash mismatch: {output}")
        if "rows" in recorded and len(pd.read_csv(output)) != recorded["rows"]:
            raise ValueError(f"results output row mismatch: {output}")
    return manifest


def make_results(config_path):
    rows, selected = collect_selected(config_path)
    tables, figures = Path("reports/tables"), Path("reports/figures")
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    main_path = tables / "results_main.csv"
    summary_path = tables / "results_summary.csv"
    figure_path = figures / "pr_curves.png"

    main = pd.DataFrame(rows).sort_values(["group", "seed"])
    main.to_csv(main_path, index=False)
    numeric = [
        column for column in main.select_dtypes("number").columns if column != "seed"
    ]
    summary = main.groupby("group")[numeric].agg(["mean", "std"])
    summary.columns = [f"{metric}_{stat}" for metric, stat in summary.columns]
    summary.reset_index().to_csv(summary_path, index=False)

    for run_dir, manifest in selected:
        if int(manifest["seed"]) != 42:
            continue
        preds = pd.read_parquet(run_dir / "predictions.parquet")
        precision, recall, _ = precision_recall_curve(preds["y_true"], preds["score"])
        plt.plot(recall, precision, label=manifest["group"].upper())
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Recorded test precision-recall curves (seed 42)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figure_path, dpi=200)
    plt.close()

    outputs = {
        main_path.as_posix(): {"sha256": sha256_file(main_path), "rows": len(main)},
        summary_path.as_posix(): {"sha256": sha256_file(summary_path), "rows": len(summary)},
        figure_path.as_posix(): {"sha256": sha256_file(figure_path)},
    }
    manifest = {
        "schema_version": 1,
        "inputs": [source_run_ref(run_dir) for run_dir, _ in selected],
        "source_code_sha256": {"tools/make_results.py": sha256_file("tools/make_results.py")},
        "outputs": outputs,
    }
    result_path = Path("reports/results_manifest.json")
    result_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    validate_results_manifest(result_path)
    return result_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    print(make_results(args.config))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run and validate** — `uv run pytest tests/test_results_contract.py -v`, then `uv run python tools/make_results.py --config configs/results.yaml`, then re-run the contract test. Manually compare at least two output rows with their source `metrics.json` files and confirm the result manifest lists exactly 30 inputs and 30 main rows.
- [ ] **Step 5: Commit** — `git commit -am "feat: provenance-linked results tables and figures"`

### Task 7.2: Independent adversarial review (Codex)

- [ ] **Step 1: Run an implementation review, not the bootstrap-plan review.** Open a fresh Codex task in the repository root using an agent that did not implement the pipeline. Paste the following charter verbatim. The bootstrap prompt in `docs/reviews/2026-07-13-codex-bootstrap-review-prompt.md` remains a pre-implementation document review only and must not be reused here.

```text
You are the independent adversarial reviewer of an IMPLEMENTED fraud-detection FYP repository.
You did not write this code. Assume material defects exist and hunt for them. REPORT ONLY:
do not edit repository files, weaken tests, regenerate final artifacts, or train models.

GROUND TRUTH AND NON-NEGOTIABLE CONTRACTS
1. Dataset: European credit-card dataset, 284,807 rows and 492 frauds before any documented
   deduplication. Stable case_id is created before splitting and never enters the feature matrix.
2. Split: stratified 70/15/15 with a fixed seed. Scaler/AE/SMOTE fit on training data only.
   Validation selects hyperparameters and one frozen max-F1 threshold; test is evaluated once.
3. Detector groups reported as performance rows: G0/G1/G2/G3/G6/G7, five exact seeds 42–46.
   G4 is SHAP reason-code generation and G5 is guarded narrative generation, not detector rows.
4. Required detector reporting: val/test AUC-PR; test ROC-AUC, precision, recall, F1,
   TP/TN/FP/FN, Precision@100, Recall@100; frozen threshold; training and inference time.
5. G4 explains saved predictions from the frozen detector and joins rebuilt features by case_id.
   SHAP direction follows the signed contribution convention actually returned by the pinned stack.
6. G5 sends only ranked reason-code evidence to local Ollama: no raw transaction row, exact feature
   value, score/probability, y_true, or SHAP magnitude. validate_narrative() must enforce exact format,
   complete grounding, explicit non-contradictory directions, and deterministic fallback.
7. Every reported detector/G4/G5 run has a valid run_manifest.json. Upstream links are exactly
   {run_id, manifest_sha256}; artifact/source hashes and row counts validate. Final reported runs are
   clean. Results are built only from configs/results.yaml, never by glob/latest/name guessing.
8. The React/FastAPI dashboard is a read-only consumer. Recorded and live_demo are visibly distinct;
   live data is never persisted; public APIs expose no absolute paths; startup fails closed on invalid
   recorded provenance; Ollama failure degrades to deterministic reason codes instead of HTTP 500.

ALLOWED ACTIONS
- Read any repository file and git metadata.
- Recompute hashes/counts on local CSV/JSON/JSONL/Parquet artifacts.
- Run existing unit/contract tests and cheap targeted tests.
- Copy small code units to a scratch directory outside the repo and construct synthetic/adversarial
  inputs. You may mock Ollama. Do not download packages/models/data or run full-data training.
- Do not modify repository files, manifests, final run artifacts, configs, or reports.

REVIEW A — DATA, SPLITS, AND LEAKAGE
- Trace case_id from load through split, scaling, AE, SMOTE, model.fit, predictions, G4, and G5.
- Prove case_id/TARGET cannot enter FEATURES, scaler, AE, SMOTE, or XGBoost.
- Check deduplication timing; stratification; train-only fitted state; AE early stopping source;
  SMOTE inputs; scale_pos_weight inputs; tuning objective; and every path that could read test metrics.
- Verify validation threshold indexing and boundary behavior, including precision_recall_curve's
  threshold array being one element shorter than precision/recall.

REVIEW B — METRICS AND REPRODUCIBILITY
- Recompute selected metrics from at least two saved predictions.parquet files and compare exactly
  with metrics.json and results_main.csv. Check positive-class score column, >= threshold semantics,
  confusion-matrix ordering, Precision@100/Recall@100 ties, zero divisions, runtime definitions,
  seed propagation, and group coverage.
- Inspect pinned-version API usage: XGBoost constructor/fit early stopping, Keras 3 save/load,
  SHAP return shape and sign convention, pandas index/Parquet behavior.

REVIEW C — PROVENANCE AND RUN SELECTION
- Independently hash dataset, config, split, sources, manifests, and required artifacts.
- Verify manifest fields/signatures are consistent across runner, G4, G5, results, and dashboard.
- Verify source_runs contains only exact run_id + manifest_sha256 references and the chain reaches
  the exact detector. Check changed/missing files, duplicate IDs, row counts, dirty state, and atomic
  manifest-last behavior fail closed.
- Confirm results.yaml has exactly 30 unique group/seed pairs and rejects tuning/quick/superseded runs.
  Confirm results_manifest output hashes and input references reproduce.

REVIEW D — G4/SHAP CONTRACT
- Shuffle rebuilt X_test rows and prove the join remains correct by case_id.
- Try duplicate, missing, and orphan IDs; detector/G4 score or y_true disagreement; feature-name/order
  mismatch; recon_error/latent dimensions; empty flagged set; top_k bounds; SHAP multi-output shapes.
- Confirm G4 never recomputes or replaces authoritative detector scores/predictions.

REVIEW E — GUARDRAILS AND G5
- Run the full guardrail suite. Then create additional adversarial strings in both classes:
  (a) unfaithful text trying to pass: omitted evidence, extra known/unlisted feature, direction flip,
      negation, ambiguous 'related to risk', unauthorized number/probability/value, duplicated bullet,
      reordered rank, punctuation/sentence-count bypass, Unicode/case/substring tricks;
  (b) faithful text that may be falsely rejected: conjunctions, safe paraphrases, decreases-risk
      wording, feature names such as V1 vs V10, and normal punctuation.
- For every bypass/false rejection, run validate_narrative() and save the exact input/result in the
  report. Verify fallback text is deterministic and derived only from the evidence record.
- Verify G5 inherits seed and the full detector manifest feature_names (including recon_error/latent
  features absent from a particular top-k), preserves every G4 case_id exactly once, records explicit
  judged/unavailable denominators, and cannot report quick-run outputs as final.
- Mock Ollama and inspect the exact outgoing payload for prohibited fields.

REVIEW F — DASHBOARD AND CLAIM BOUNDARIES
- Run backend/frontend contract tests and production Recorded-mode smoke if cheap. Verify the artifact
  adapter uses the same provenance/guardrail modules, is read-only, and exposes only allowlisted files.
- Attack API inputs with arbitrary paths/prompts/evidence/scores; verify rejection. Check deep links,
  missing build, invalid manifests, Ollama timeout, Cache-Control no-store, non-loopback requests,
  recorded/live labels, NOT_RUN semantics, and artifact hashes/mtimes before vs after API actions.
- Cross-check results_mapping/report/dashboard claims against exact supporting artifacts. Flag any
  unsupported 'privacy-preserving', causal, real-time, production-ready, or same-system claim.

REVIEW G — TEST ADEQUACY AND PLAN COMPLETENESS
- Identify tests that merely assert fixtures/mocks rather than the production path, weakened assertions,
  xfail/skip, order dependence, broad exception catches, stale interfaces, and missing negative cases.
- Compare implemented outputs against every G0–G7, metric, provenance, guardrail, report, and dashboard
  requirement above. Report omissions even when no existing test expects them.

OUTPUT FORMAT
Start with a one-line verdict. Then list findings ordered BLOCKER, MAJOR, MINOR.
For every finding use exactly:
[SEVERITY] Short title
- Location: file:line (use the tightest relevant range)
- Status: CONFIRMED or SUSPECTED
- Contract: the violated ground-truth item
- Failure scenario: exact input/state and observed or predicted outcome
- Evidence: command/test/hash/result used; for SUSPECTED, state what was not executable
- Minimal repair direction: describe the required behavior, but do not write or apply the fix

CONFIRMED means you actually demonstrated the failure with code/test/artifact evidence.
SUSPECTED means reasoned from source but could not execute it. Do not inflate severity without a
concrete consequence. End with: tested commands, untested areas and why, and a count by severity/status.
If there are no findings, say so explicitly and still list the evidence collected.
```

Save the report under `docs/reviews/` with a date and `implementation-review` in the filename.

- [ ] **Step 2:** Triage findings; fix real bugs with TDD (failing test reproducing the bug first). If any fix changes results, re-run the affected groups and note the re-run in `experiments/DECISIONS.md`.
- [ ] **Step 3:** Before Task 7.4 real-artifact integration, resolve every relevant BLOCKER/MAJOR affecting stable case IDs, run/result manifests, G4/G5 joins, guardrail bypass/false rejection, data minimization, run selection, or provenance. Any guardrail behaviour change requires a fresh final G5 run and updated manifest.
- [ ] **Step 4:** Validate the exact allowlisted final detector runs from `configs/results.yaml` plus final G4/G5; do not audit with a broad glob that accidentally includes incompatible run types. All applicable audits and manifest validations must PASS. Record accepted false positives with a concrete contract-based rebuttal in the same review file rather than silently deleting them.
- [ ] **Step 5: Commit** — `git commit -am "fix: address adversarial review findings"`

### Task 7.3: CP2 report skeleton mapped to logged results

**Files:**
- Create: `reports/thesis/results_mapping.md`

- [ ] **Step 1:** Write `results_mapping.md`: a table mapping every planned report claim → the exact run dir / table / figure that supports it (e.g., "G3 vs G0 AUC-PR comparison → `reports/tables/results_summary.csv` rows g0,g3"; "faithfulness rates → the exact final `experiments/runs/<date>_g5_seed<inherited-seed>/faithfulness.json`"). Any claim without a source is either dropped or marked "needs experiment".
- [ ] **Step 2:** Draft CP2 report chapters (reuse CP1 Chapters 1–2 with updates; Chapter 3 → "as implemented"; Chapter 4 Results from the tables; Chapter 5 Discussion & Limitations — including the honest wording "privacy-conscious local deployment", not "privacy-preserving" as a proven property).
- [ ] **Step 3: Commit** — `git commit -am "docs: results-to-claims mapping + report skeleton"`

### Task 7.4: React + FastAPI local demo dashboard

**Canonical specification:** `docs/specs/2026-07-13-react-fastapi-demo-dashboard-spec.md`  
**Consensus execution plan:** `.omx/plans/2026-07-13-react-fastapi-demo-dashboard.md`

**Hard gate before real-artifact integration:**

- Tasks 5.2, 6.4, 6.5, 7.1, and the relevant Task 7.2 BLOCKER/MAJOR remediations are complete.
- Exact final detector/G4/G5/results manifests validate.
- The guardrail adversarial suite passes before the final G5 run.
- Stable `case_id` joins, source-code hashes, and curated scenario predicates validate automatically.
- Fixture-based frontend work may start earlier, but the app must not connect to unreviewed final artifacts or claim “same evaluated system” before this gate passes.

**End-of-W12 route-level scope gate:**

- Mandatory live-demo routes are **Case Queue**, **Investigation**, and **Guardrail Lab**, including provenance fail-closed behavior, Recorded/Live separation, data-minimization tests, and Ollama fallback.
- If the verified backend plus these three routes are not complete by the end of W12, freeze scope immediately: keep Results as a provenance-labelled static view of the already generated Task 7.1 table/figure (or report screenshot) and drop interactive Results API/chart polish.
- Do not remove or weaken artifact validation, guardrail reuse, accessibility, fallback, or read-only tests to save time. Drop optional animation, extra filters, chart interactivity, responsive/mobile polish, and additional live controls first.
- W13 is feature freeze, exact-artifact smoke, screenshots, report integration, and rehearsals—not recovery time for new routes.

**Files:**

- Create: `app/__init__.py`, `app/backend/__init__.py`
- Create: `app/backend/server.py`, `settings.py`, `schemas.py`, `artifacts.py`, `live.py`, `attack_presets.py`
- Create: `app/frontend/` React + TypeScript + Vite application with routes `/queue`, `/cases/:caseId`, `/guardrails`, `/results`
- Create: `configs/dashboard.yaml`, `tools/validate_dashboard.py`
- Test: `tests/app/test_artifacts.py`, `test_api.py`, `test_live.py`, `test_attack_presets.py`, fixture artifacts
- Test: frontend Vitest/Testing Library tests and `app/frontend/e2e/dashboard.spec.ts`
- Modify: `.gitignore` for `app/frontend/node_modules/`, `app/frontend/dist/`, and frontend test artifacts

**Interfaces:**

- Production command after dependency installation and frontend build:

  ```bash
  uv run python -m app.backend.server --config configs/dashboard.yaml
  ```

- FastAPI binds to `127.0.0.1` by default, serves `/api/v1/*`, then serves the built React SPA from `app/frontend/dist/`.
- The backend loads exact configured artifacts once at startup, verifies the entire chain, and exposes an immutable read-only snapshot.
- The dashboard never trains, scores, selects thresholds, recomputes reported metrics, rebuilds SHAP values, or writes experiment artifacts.
- Recorded and live replay results are distinct API/UI states. Every live response includes `mode: live_demo` and `reported: false` and is not persisted.
- Live narrative generation reuses the real `serialize_evidence()`, `generate_narrative()`, `validate_narrative()`, and `fallback_text()` functions from `src.narratives`.

- [ ] **Step 1: Freeze the dashboard configuration and artifact contract**

  Write `configs/dashboard.yaml` with exact detector, G4, G5, and `reports/results_manifest.json` paths plus verified curated scenario IDs. Do not use globs, “latest,” or a browser-selectable path.

  Define Pydantic schemas and fixture manifests for:

  - detector predictions and manifest;
  - G4 reason codes and source link;
  - G5 narrative records and source-code hashes;
  - results tables/figures manifest;
  - `PASS | FAIL | NOT_RUN` check states;
  - recorded/live response labelling.

- [ ] **Step 2: Write failing artifact-validator tests**

  Cover:

  - missing required file or manifest;
  - dataset/config/source-chain/artifact hash mismatch;
  - duplicate/missing `case_id`;
  - detector ↔ G4 score/label mismatch;
  - G4 ↔ G5 orphan/missing cases;
  - relevant `evidence.py` / `guardrails.py` / `llm_client.py` source-hash mismatch;
  - invalid results-manifest input/output hash;
  - invalid faithful/error/attack scenario predicate;
  - absolute path leakage in a public API schema.

- [ ] **Step 3: Implement the read-only artifact adapter and CLI validator**

  `tools/validate_dashboard.py --config configs/dashboard.yaml` validates the same contract used by FastAPI startup. `app/backend/artifacts.py` creates an immutable joined snapshot keyed by stable `case_id`. It exposes provenance IDs/hashes but not absolute filesystem paths. Production startup fails closed on an invalid recorded chain; Ollama unavailability is not a startup failure.

- [ ] **Step 4: Write failing FastAPI contract tests, then implement `/api/v1`**

  Required endpoints:

  - `GET /api/v1/health`
  - `GET /api/v1/provenance`
  - `GET /api/v1/demo-scenarios`
  - `GET /api/v1/cases`
  - `GET /api/v1/cases/{case_id}`
  - `GET /api/v1/results`
  - `GET /api/v1/figures/{figure_id}` using an allowlist
  - `POST /api/v1/live/narrative`
  - `POST /api/v1/guardrails/demo`

  API constraints:

  - live request accepts only `case_id`;
  - guardrail demo accepts only `case_id` + `direction_flip | unlisted_feature | template_corruption`;
  - no arbitrary prompt, evidence, raw transaction, score, SHAP value, or filesystem path input;
  - Ollama timeout/connection failure returns a successful degraded response with deterministic fallback, `NOT_RUN` checks, and a reason—not an unhandled 500;
  - live responses set `Cache-Control: no-store` and never write files;
  - figure requests use fixed IDs rather than path mapping.

- [ ] **Step 5: Prove LLM data minimization and read-only behaviour**

  Mock Ollama and inspect the exact outgoing payload. Assert that it contains no raw row, exact feature value, detector score/probability, historical label, or SHAP magnitude. Hash and record mtimes for the configured experiment/report artifacts before and after all API actions; assert they are unchanged.

- [ ] **Step 6: Bootstrap the React + TypeScript + Vite frontend**

  Use npm and commit `package-lock.json`. Runtime dependencies are React, React DOM, and React Router. Development/test dependencies are TypeScript, Vite, Vitest, React Testing Library, Playwright, and ESLint. Do not add a UI kit or chart library in v1; use CSS tokens and accessible SVG/CSS contribution bars. Bundle fonts/assets locally or use system fallbacks.

- [ ] **Step 7: Implement the app shell and visual system with component tests**

  Create the projector-safe light investigation console defined in the spec. Global UI includes navigation, Recorded/Live Replay state, artifact readiness, Ollama status, current case, provenance drawer, and Reset demo. Implement visible focus, semantic tables/buttons, non-colour-only statuses, reduced-motion handling, loading/empty/error states, and deep-link recovery.

- [ ] **Step 8: Implement Case Queue and Investigation**

  Queue shows stable case ID, risk bucket, recorded score, detector result, **Evaluation-only ground truth**, top reason, and recorded narrative status. Investigation uses a 60/40 desktop layout with detector/evidence on the left and narrative/guardrails/fallback on the right. Label the chart **Top recorded SHAP contributions**; do not call it a waterfall. The “Data sent to LLM” disclosure lists included and excluded fields explicitly.

- [ ] **Step 9: Implement Guardrail Lab**

  Server-side deterministic presets transform a verified faithful base narrative, then pass it to the real `validate_narrative()`. Show original vs tampered text, structured check results, failure reasons, and deterministic fallback. Each preset must fail the intended check and activate fallback without allowing arbitrary narrative submission.

- [ ] **Step 10: Implement Results**

  Display G0/G1/G2/G3/G6/G7 detector performance separately from G4/G5 explanation/faithfulness metrics. Read recorded tables/figures and their manifest; do not calculate reported metrics in React. Show source run IDs/hashes and an accessible caption/table alternative for figures.

  If the end-of-W12 scope gate fires, this step is satisfied by a static, provenance-labelled rendering of the Task 7.1 CSV/PNG (or an exported report screenshot plus accessible table/link). Interactive chart controls and dedicated Results polish are then explicitly deferred; provenance validation and the route smoke test remain mandatory.

- [ ] **Step 11: Package production serving**

  Vite builds to `app/frontend/dist/`. FastAPI serves API routes first and an SPA fallback second. If the build is missing, startup exits with the exact `npm ci && npm run build` instruction. Development may use Vite proxy + FastAPI reload; the live demo uses the single FastAPI process only.

- [ ] **Step 12: Run the full automated verification**

  ```bash
  uv run pytest tests/app
  uv run pytest
  cd app/frontend
  npm ci
  npm run test
  npm run build
  npm run e2e
  cd ../..
  uv run python tools/validate_dashboard.py --config configs/dashboard.yaml
  ```

  Playwright must cover Queue → faithful Investigation → Guardrail Lab → Results, all three attacks, live success with mocked Ollama, timeout fallback, deep-link refresh, keyboard navigation, and a production recorded flow with Ollama stopped. Add a test that fails any request to a non-loopback origin.

- [ ] **Step 13: Exact-artifact smoke and feature freeze**

  Start the production app with the final config, verify all provenance badges against the source manifests, and confirm source artifact hashes/mtimes are unchanged afterward. Freeze dashboard features at the start of W13; waterfall charts, animation, mobile layout, extra tabs, and additional live controls remain optional and cannot delay rehearsal/report work.

- [ ] **Step 14: Rehearse on the presentation laptop**

  Complete at least three timed end-to-end rehearsals after feature freeze, including:

  - network disabled + Ollama disabled cold start;
  - faithful live replay with Ollama enabled;
  - three deterministic attacks;
  - real error/uncertainty case;
  - Ollama timeout fallback;
  - browser refresh/deep link recovery;
  - recovery instructions for missing Ollama or frontend build.

- [ ] **Step 15: Commit** — `git commit -am "feat: provenance-verified React FastAPI demo dashboard"`

---

## Suggested CP2 timeline (14 weeks)

| Weeks | Phase | Exit criteria |
|---|---|---|
| W1 | Phase 0–1 | env + data modules green (`uv run pytest`) |
| W2 | Phase 2–3 | G0/G1/G6 logged; leakage audit PASS |
| W3–4 | Phase 4 | G2/G3/G7 logged; tuning done; detector frozen in DECISIONS.md |
| W5 | Phase 4 | multi-seed runs complete |
| W6–7 | Phase 5 | G4 reason codes + SHAP figures |
| W8–9 | Phase 6 | G5 narratives + faithfulness metrics |
| W10 | Phase 7.1–7.2 | provenance-linked tables/figures; adversarial review, fixes, manifest validation, dashboard source chain frozen |
| W11 | Phase 7.3–7.4 | report drafting continues; verified backend snapshot plus Queue and Investigation implemented against fixtures/exact contracts |
| W12 | Phase 7.4 | Guardrail Lab, live/fallback, and automated tests complete; end-W12 scope gate freezes Results as static Task 7.1 evidence if interactive Results is not ready |
| W13 | Phase 7.3–7.4 | feature freeze from day one; exact-artifact smoke, report screenshots/integration, and at least three complete rehearsals |
| W14 | — | buffer, supervisor feedback, recovery drill, final report/presentation polish |

## Definition of done (CP2)

1. `uv run pytest` green; every `src/` module has tests, including stable-ID, provenance, and adversarial guardrail regression coverage.
2. Stable `case_id` is preserved from load through detector/G4/G5, excluded from all model features, and used for every cross-stage join.
3. Groups G0–G3, G6, G7 each have 5 seed runs with valid `run_manifest.json`, `metrics.json`, unique-ID `predictions.parquet`, and passing leakage/provenance audit.
4. `experiments/DECISIONS.md` records the frozen detector chosen on validation AUC-PR without test-driven model selection.
5. G4 `reason_codes.jsonl`, manifest, and global SHAP figure exist for the exact frozen detector; detector ↔ G4 IDs/scores/labels validate.
6. The adversarial guardrail suite passes before the final G5 run. G5 `faithfulness.json`, narratives, and manifest cover all G4 cases and report compliance / grounding / direction-consistency / fallback rates with consistent denominators.
7. `reports/tables/results_summary.csv`, `results_main.csv`, and PR-curve figure regenerate from exact allowlisted runs and validate against `reports/results_manifest.json`.
8. Adversarial review (Task 7.2) real BLOCKER/MAJOR findings are resolved; affected results were rerun and recorded where required.
9. Every report claim maps to a logged artifact in `results_mapping.md`.
10. Task 7.4 production build starts with one FastAPI command after install/build preparation; Recorded mode works with network and Ollama disabled.
11. Dashboard artifact/source-chain validation, LLM data-minimization tests, Python/frontend/Playwright tests, and exact-final-artifact smoke are green; live output remains demo-only and non-persistent.
12. The faithful case, real error/uncertainty case, three guardrail attacks, Ollama fallback, provenance explanation, and Results flow have completed at least three timed post-freeze rehearsals on the presentation laptop.

## Optional Phase 8 — project skills (only if time permits)

Six `.claude/skills/` entries can wrap the tools built above (they add convenience, not capability): `fraud-data-auditor` → `tools/leakage_audit.py` + `tools/check_data.py`; `experiment-designer` → the G0–G7 matrix in AGENTS.md; `experiment-runner` → `src/run_experiment.py` usage; `fraud-evaluator` → `tools/make_results.py`; `shap-faithfulness-auditor` → `tools/run_g5_narratives.py`; `research-claim-checker` → `reports/thesis/results_mapping.md` discipline. Create them with the official `skill-creator` skill; keep each SKILL.md under a page.
