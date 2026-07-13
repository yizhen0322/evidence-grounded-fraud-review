# Codex review prompt — CP2 bootstrap deliverables (2026-07-13)

Paste everything below the line into Codex, run from the repo root `fraud-detection-fyp/`.

---

You are an independent adversarial reviewer. Another AI agent (Claude) bootstrapped this FYP repository today. You did NOT write any of it. Your job is to find real problems, not to praise it. Assume it contains at least a few defects and hunt for them. Do not fix anything — report only.

## Context

This repo is Capstone Project 2 (implementation phase) of a Sunway University FYP: "Credit Card Fraud Detection using a Hybrid Autoencoder-XGBoost Model with Local LLM Explanations". No pipeline code has been implemented yet. What exists today, and what you are reviewing:

1. `AGENTS.md` — shared hard rules for all coding agents (research integrity, data leakage, test-set discipline, experiment matrix, LLM guardrails).
2. `CLAUDE.md`, `README.md` — pointers/orientation.
3. `data/raw/creditcard.csv` + `data/raw/DATA_MANIFEST.md` — the dataset and its provenance record.
4. `docs/plans/2026-07-13-cp2-implementation-plan.md` — a ~2000-line implementation plan containing COMPLETE embedded code (source modules, pytest tests, YAML configs, shell commands) for the whole CP2 pipeline. This plan will be executed task-by-task, so a bug in the plan's code becomes a bug in the project.
5. `.gitignore`, directory skeleton. Git repo is initialized with no commits yet.

## Ground truth (from the approved CP1 proposal — treat as the spec)

- Dataset: European Credit Card Fraud (ULB/Kaggle): exactly 284,807 rows, 492 frauds (~0.172%), 31 columns (Time, V1–V28, Amount, Class), no missing values.
- Split: 70/15/15 train/val/test, stratified by Class, random_state=42, performed BEFORE any scaling, resampling, AE fitting, or threshold selection.
- Scaler fit on train only. SMOTE on train only. AE trained on train-legitimate rows only. Val/test keep the original class distribution.
- Model selection: validation AUC-PR (primary). Test set evaluated ONCE per group after config freeze. Threshold selected on validation, frozen for test.
- Experiment groups: G0 XGBoost; G1 XGB+SMOTE; G2 AE-recon-error+XGB; G3 AE-recon-error+XGB+SMOTE; G4 best detector + SHAP reason codes (global + local top-k with direction); G5 = G4 + local LLM narrative; G6 XGB+scale_pos_weight; G7 AE-latent-features+XGB.
- Metrics: AUC-PR primary; Recall, Precision, F1 at frozen threshold; ROC-AUC secondary; confusion matrix; Precision@100/Recall@100; inference time; multi-seed (42–46) mean±std. Accuracy never a headline metric.
- LLM module (Ollama, llama3): strict translation layer over SHAP evidence. Never sees raw feature values or probabilities. Fixed template (NARRATIVE 2–3 sentences / EVIDENCE bullets / ACTION). Code-level guardrails: feature grounding, direction consistency, format compliance; any failure → fallback to reason codes. Faithfulness metrics: compliance rate, grounding rate, direction consistency rate, fallback rate.

## Review checklist

**A. Dataset & provenance**
- Re-verify `data/raw/creditcard.csv` yourself: SHA256, row count, fraud count, column list, missing values. Compare against `DATA_MANIFEST.md`. The manifest claims SHA256 `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`.
- Is the mirror source (TensorFlow tutorial hosting) credibly the same dataset as Kaggle mlg-ulb/creditcardfraud? Flag any doubt for the report's data-source section.

**B. Rules documents**
- `AGENTS.md`: internal contradictions, rules that conflict with the ground truth above, loopholes (e.g., is there any path to tune on test that the rules fail to forbid?), missing rules you'd expect for this methodology.
- Consistency across `AGENTS.md` ↔ `README.md` ↔ `CLAUDE.md` ↔ the plan (paths, group definitions, seeds, metric names).

**C. Plan — structure**
- Placeholder violations: any "TBD", "similar to task N", steps that describe without showing code.
- Interface consistency across tasks: function names, signatures, return types, config keys, file paths used in later tasks must match their definitions in earlier tasks exactly (e.g., does every caller of `run(...)`, `evaluate(...)`, `local_reason_codes(...)`, `validate_narrative(...)` match the defined signatures? Do config YAML keys match what `run_experiment.py` reads?).
- Task ordering: does anything get used before the task that creates it (allowing for documented lazy imports)?

**D. Plan — embedded code correctness (the highest-value section, read every code block)**
- Leakage: trace the runner's pipeline order (load → dedup → split → scale → AE → augment → SMOTE → train → threshold → test). Any way val/test statistics reach any fitted object? Is the AE's early stopping really isolated from the global validation set? Is dedup-before-split defensible or does it need documenting?
- API misuse for the pinned stack (xgboost ≥2.1, shap ≥0.46, TF ≥2.17/Keras 3, imbalanced-learn ≥0.12, sklearn ≥1.5, pandas ≥2.2): e.g., `XGBClassifier(early_stopping_rounds=...)` in constructor vs fit; `shap.TreeExplainer(model)(X).values` shape for binary XGBoost; `keras.saving.load_model`; `Model.save(...".keras")`; `SMOTE.fit_resample` return types (does the code assume DataFrame out and does imblearn preserve that?); parquet round-trip of indices in `run_g4_shap.py`.
- SHAP sign convention: the plan asserts positive SHAP = pushes toward fraud for XGBoost TreeExplainer margin output. Verify this holds for `XGBClassifier` binary logistic, and that reason-code direction mapping is therefore correct.
- Guardrails logic (`guardrails.py`): try to construct narratives that are unfaithful but PASS the checks (regex gaps, clause splitting on `[.!?;,]|while|whereas|but`, feature-name word boundaries like V1 vs V14, direction phrasing not covered by UP_WORDS/DOWN_WORDS), and faithful narratives that FAIL. Report concrete adversarial strings.
- Metrics: `precision_at_k`/`recall_at_k` tie handling; `evaluate` on all-negative or all-positive edge cases; threshold selection off-by-one (`precision_recall_curve` returns len(thresholds) = len(precision) - 1 — is the indexing right?).
- Runner details: `scale_pos_weight` computed from post-dedup train only; SMOTE applied AFTER AE feature augmentation (is that ordering stated and consistent?); run-dir collision behavior; anything nondeterministic left unseeded (TF ops, SMOTE, numpy, random search in `tune.py`).
- G4/G5 scripts: `rebuild_test_matrix` must reproduce the exact training-time feature matrix (same dedup flag, same seed, same scaler fit) — any drift possible between it and the runner? Faithfulness rate denominators (rates over judged cases vs all cases vs LLM-unavailable cases) — are they defined sensibly and consistently with the proposal's four metrics?

**E. Plan — test quality**
- For each TDD pair, would the given test actually pass against the given implementation? Flag any that would fail (that's a plan bug, since executors follow it literally). Mechanical check encouraged: extract code blocks into a scratch dir, `uv init` a throwaway env, and run the cheap tests (skip TF-dependent ones if install time is unreasonable). Do NOT train on the real dataset.
- Do the tests pin the safety-critical behaviors (train-only scaler fit, SMOTE not touching val/test, frozen threshold) or only happy paths? List the most important missing test.

**F. Coverage vs spec**
- Walk the ground-truth list above and name anything the plan never implements or logs (each G-group, every metric, every faithfulness rate, multi-seed, tuning-on-validation-only, DECISIONS.md freeze record).

**G. Repo hygiene**
- `.gitignore` vs the plan's outputs: will any large/generated file (dataset, runs, tuning runs, models, figures?) get committed by the plan's own `git add`/`git commit -am` commands? Will anything needed for reproducibility be wrongly ignored?

## What you may and may not do

- MAY: read everything; hash/inspect the CSV; extract plan code to a scratch dir and run cheap tests; install a throwaway venv.
- MAY NOT: modify repo files, commit, train on the full dataset, download anything new, or "fix" findings.

## Output format

A single markdown report:
1. **Verdict per section A–G**: PASS / PASS-WITH-ISSUES / FAIL, one line of justification each.
2. **Findings table**, ordered by severity (BLOCKER = would invalidate results or violate a hard rule; MAJOR = wrong results/crash in some path; MINOR = quality/robustness). For each: severity, `file:line` (or plan task number), one-sentence defect, concrete failure scenario or adversarial input, CONFIRMED (you demonstrated it) vs SUSPECTED (reasoned but not executed).
3. **Top 5 risks to research validity** in priority order, one sentence each.
No fixes, no rewritten code — findings only.
