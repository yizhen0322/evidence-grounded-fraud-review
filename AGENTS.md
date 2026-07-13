# AGENTS.md — Fraud Detection FYP (CP2)

Shared instructions for ALL coding agents working in this repository (Codex, Claude Code, and any subagents).
These rules are non-negotiable. If a user request conflicts with a rule here, stop and ask the user to confirm explicitly.

## Project summary

Sunway University BCS (Hons) Capstone Project 2 by Ng Yi Zhen (23076003).
Title: **"Credit Card Fraud Detection using a Hybrid Autoencoder-XGBoost Model with Local LLM Explanations"**.
Pipeline: AE + XGBoost detection → imbalance handling (SMOTE / cost-sensitive) → SHAP reason codes → local LLM (Ollama) narrative → faithfulness verification.
Dataset: European Credit Card Fraud dataset (ULB/Kaggle): 284,807 transactions, 492 frauds (0.172%), features V1–V28 (PCA), Time, Amount, Class.

The approved methodology is in `../Proposal_Capstone_Project.pdf` (Chapter 3). Do not silently change the methodology; propose changes to the user first.

## Research integrity (hard rules)

- **Never fabricate experimental results.** Every number in a report, table, or claim must come from a logged run under `experiments/runs/`. If a result does not exist yet, say so.
- **Never fabricate references, DOIs, authors, or quotes.** Only cite papers the user has provided (see `../paper/` and `../review.csv`) or that you have actually fetched and read.
- **Never write "improves", "outperforms", or "superior" about our models unless a logged test-set result supports it.** Report differences with the actual numbers alongside.
- Do not claim the system is "privacy-preserving" as a proven property. Use "privacy-conscious local deployment" / "locally deployed explanation architecture with data minimization" unless the report explicitly scopes the claim.
- Report negative or null results honestly. A hybrid model that does NOT beat the baseline is still a valid CP2 finding.

## Data leakage rules (hard rules)

- **Split before everything.** Train/validation/test split (70/15/15, stratified by Class, `random_state=42`) happens BEFORE any scaling, SMOTE, autoencoder fitting, feature engineering, or threshold selection.
- **Fit preprocessing on train only.** Scalers (e.g., StandardScaler for Amount/Time) are fit on the training set only, then applied to validation/test.
- **SMOTE on the training set only.** Validation and test sets always keep the original class distribution. Never resample validation or test.
- **The autoencoder must never see validation or test data during fitting.** AE is trained on training-set legitimate (Class=0) transactions only. AE-derived features (reconstruction error, latent codes) for val/test are produced by *applying* the trained AE, never by fitting on them.
- **Thresholds are selected on the validation set**, then frozen before touching test.
- Duplicate handling: deduplication decisions are made once, before splitting, and documented in the run config.

## Test-set discipline (hard rules)

- **Model selection uses validation AUC-PR** (primary), with Recall/F1 as supporting metrics.
- **The test set is evaluated ONCE per experiment group, after the configuration is frozen.** Never iterate hyperparameters, thresholds, features, or seeds in response to test-set results. If a test evaluation reveals a bug, fix the bug, note the re-run in the run log, and state it in the report.
- Never use test data for early stopping, calibration, SMOTE, AE training, or prompt tuning.

## Experiments

- Experiment groups use the **G-numbering** (single source of truth, unifying proposal Tables 3.1/3.2):
  - **G0** — XGBoost, original features, no imbalance handling (= M1)
  - **G1** — XGBoost + SMOTE (training only) (= M2)
  - **G2** — AE reconstruction error + XGBoost, no resampling
  - **G3** — AE reconstruction error + XGBoost + SMOTE (= M3)
  - **G4** — best detector from G0–G3/G6/G7 + SHAP reason codes
  - **G5** — G4 + local LLM narratives under a paired delivery-policy design: the SAME raw outputs are analysed OFF-policy (delivered raw → detected-violation prevalence) and ON-policy (validated → fallback); two prompt arms (strict / simple); the validator must pass corpus calibration (Task 6.7 gate) BEFORE the final G5 run
  - **G6** — XGBoost + `scale_pos_weight` (cost-sensitive) (= M4)
  - **G7** — AE latent (bottleneck) features + XGBoost
- Every run is driven by a YAML config in `configs/`, executed via `src/`, and writes to `experiments/runs/<date>_<group>_seed<seed>/`: `config.yaml`, `metrics.json`, `predictions.parquet`, `environment.txt`, model artifacts. Results not logged this way do not exist.
- Fixed seeds everywhere (`random_state=42` default; multi-seed runs use 42, 43, 44, 45, 46). Log library versions.
- `notebooks/` is for exploration only. No reported result may come from a notebook.

## Metrics

- Primary: **AUC-PR** (average precision). Supporting: Recall, Precision, F1 (at the validation-selected threshold), ROC-AUC (secondary only), confusion matrix, Precision@100, Recall@100, inference time.
- Multi-seed experiments report mean ± std over seeds.
- Never report plain accuracy as a headline metric (0.17% fraud rate makes it meaningless).
- Faithfulness metrics (G5): per-check detected-violation prevalence (format / completeness / grounding / direction / any), fallback rate, validator calibration (per-category interception + false-rejection on the versioned corpus), audit-estimated undetected violation rate. **Every reported rate carries its n and a 95% Wilson CI.**

## LLM explanation module rules

- The local LLM (Ollama) is a **constrained translation layer only**. It converts SHAP reason codes into a fixed-template narrative. It must never: classify transactions, invent reasons/features, see raw transaction rows, or receive exact feature values (only feature name, direction, rank, coarse buckets).
- Guardrails are code, not prompts: feature-grounding check, direction-consistency check, template-format check. Any failure → fall back to raw reason codes. Log compliance/grounding/direction/fallback rates.
- Direction semantics: a feature whose SHAP value pushes toward fraud is "↑ risk"; toward legitimate is "↓ risk". A narrative that flips a direction is a guardrail failure, not a style issue.
- Measurement wording (hard rules): every violation metric is a **detected** violation; never write "guardrails eliminate violations" — "residual detected violation rate on delivered narratives" is 0 by construction and must be labelled `by_construction`; the validator is a **corpus-calibrated instrument**, calibrated before it measures; the novelty claim always reads "within the reviewed literature … that we identified", never a bare "first".
- Manual audit integrity: the `violation_found` / `violation_category` / `notes` columns of any audit sheet are filled ONLY by humans. No AI agent may fill, edit, or "correct" them. Audit scoring requires the provenance-bound sample manifest and an explicit human attestation; never infer human authorship from a CSV.

## Engineering conventions

- Python ≥3.11 managed with `uv` (venv in `.venv/`). Core deps: numpy, pandas, scikit-learn, imbalanced-learn, xgboost, tensorflow (AE), shap, pyyaml, matplotlib, pytest, requests (Ollama HTTP).
- Source layout: `src/data/` (load/split/preprocess), `src/models/` (AE, XGBoost, hybrid), `src/evaluation/` (metrics, thresholds), `src/explainability/` (SHAP, reason codes), `src/narratives/` (LLM client, guardrails). Tests in `tests/` mirror `src/`.
- TDD: new behavior gets a failing test first (pytest). Fast tests only — unit tests must not train on the full dataset; use small synthetic fixtures.
- Do not commit `data/`, `artifacts/`, or `experiments/runs/` contents (see `.gitignore`). Never delete or overwrite `experiments/runs/` history.
- Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `exp:` for experiment runs).

## Division of labour

- **Claude Code**: research planning, experiment design, results interpretation, report/thesis drafting, consistency checks between report and logged runs.
- **Codex**: implementation, tests, refactoring, running pipelines, and **independent adversarial review** (leakage, metric bugs, threshold handling, test-set reuse, unsupported claims, SHAP direction errors, LLM hallucination).
- The agent that implements a stage must not be the only reviewer of that stage.
