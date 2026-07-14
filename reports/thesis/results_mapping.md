# CP2 results-to-claims mapping

This file is the claim ledger for the CP2 report. A claim may enter the report only when its evidence status is `SUPPORTED`. `PENDING` claims need the named experiment or human work. `DROP` claims must not appear.

## Detector and data claims

| ID | Planned report claim | Exact supporting evidence | Status and permitted wording |
|---|---|---|---|
| D1 | The source dataset contained 284,807 rows and 492 frauds before documented deduplication. | `data/raw/creditcard.csv`; dataset hash in every detector `run_manifest.json`; `tools/check_data.py` | SUPPORTED. State the pre-deduplication counts and dataset SHA-256 `76274b...51a89`. |
| D2 | Content deduplication removed 1,081 rows before splitting; the modeling dataset had 283,726 rows and 473 frauds. | `experiments/runs/2026-07-14_g0_seed42/split_summary.json`; `src/data/load.py` | SUPPORTED. Do not imply the original public dataset had only 473 frauds. |
| D3 | The seed-42 stratified split contained 198,608/42,559/42,559 train/validation/test rows and 331/71/71 frauds. | `experiments/runs/2026-07-14_g0_seed42/split_summary.json`, `split_assignments.parquet`, and `run_manifest.json` | SUPPORTED. Explain that later seeds use different frozen assignments. |
| D4 | Scaling, AE fitting, and SMOTE were restricted to training data; threshold selection used validation data. | `src/run_experiment.py`; `tools/leakage_audit.py`; all 30 manifests; `docs/reviews/2026-07-14-implementation-review.md` | SUPPORTED as an implementation/audit claim, not an empirical performance result. |
| D5 | Detector results cover G0/G1/G2/G3/G6/G7 over seeds 42–46. | `configs/results.yaml`; `reports/results_manifest.json`; `reports/tables/results_main.csv` | SUPPORTED. Exactly 30 unique detector runs. |
| D6 | Multi-seed detector performance is reported as mean ± sample standard deviation. | `reports/tables/results_summary.csv` | SUPPORTED. State `n=5 seeds` for every group. |
| D7 | Seed-42 precision–recall curves compare the six detector groups. | `reports/figures/pr_curves.png`; output hash in `reports/results_manifest.json` | SUPPORTED. The figure is seed 42 only, not a mean curve. |
| D8 | G6 was frozen after validation-only comparison and a 20-trial search applied to G6 and G2. | `experiments/DECISIONS.md`; `experiments/tuning/g6_tuning.json`; `experiments/tuning/g2_tuning.json`; `experiments/runs/2026-07-14_g6_seed42/config.yaml` | SUPPORTED. State the tuning asymmetry: other groups retained predeclared defaults. |
| D9 | G6 had the highest descriptive mean test AUC-PR: 0.855214 ± 0.027097. | `reports/tables/results_summary.csv`, row `g6` | SUPPORTED descriptively. Do not write `outperformed`, `superior`, or `significantly better`; G0 was 0.852891 ± 0.020896. |
| D10 | G2 mean test AUC-PR was 0.853707 ± 0.017449, only +0.000816 relative to G0. | `reports/tables/results_summary.csv`, rows `g2`, `g0` | SUPPORTED. Use as a null/small-effect result; do not claim the reconstruction-error hybrid improved detection. |
| D11 | G3 mean test AUC-PR was 0.816870 ± 0.078987, −0.036021 relative to G0. | `reports/tables/results_summary.csv`, rows `g3`, `g0` | SUPPORTED. Report honestly as lower and more variable under this implementation. |
| D12 | G7 mean test AUC-PR was 0.854767 ± 0.014410, with mean recall 0.816901 and mean F1 0.866858. | `reports/tables/results_summary.csv`, row `g7` | SUPPORTED. Descriptive comparison only. |
| D13 | All required seed-level metrics, thresholds, confusion counts, runtime, run IDs, and manifest hashes are available. | `reports/tables/results_main.csv`; each allowlisted run's `metrics.json` and `run_manifest.json` | SUPPORTED. Use the summary table for headline means and main table for seed-level details. |

## Explainability and narrative claims

| ID | Planned report claim | Exact supporting evidence | Status and permitted wording |
|---|---|---|---|
| E1 | G4 explains the frozen G6 seed-42 detector and produced reason codes for all 51 flagged test cases. | `experiments/runs/2026-07-14_g4_seed42/reason_codes.jsonl`; G4 `run_manifest.json`; source detector `experiments/runs/2026-07-14_g6_seed42/predictions.parquet` | SUPPORTED. The 51 cases comprise 50 true positives and 1 false positive at the frozen threshold. |
| E2 | G4 reason codes preserve detector case ID, score, and label and rank signed SHAP contributions. | G4 `reason_codes.jsonl`; `src/explainability/reason_codes.py`; `tests/test_g4_contract.py`; implementation review | SUPPORTED as an implementation/audit claim. Avoid causal wording. |
| E3 | Global SHAP evidence is available for the frozen detector. | `experiments/runs/2026-07-14_g4_seed42/global_importance.csv`; `shap_global_bar.png`; G4 manifest hashes | SUPPORTED. Call it global mean absolute SHAP importance, not causal importance. |
| E4 | The deterministic validator passed a 648-item versioned calibration corpus. | `experiments/calibration/validator_calibration_v1.json`; `corpus/guardrail_corpus_v1.jsonl` | SUPPORTED only within corpus scope: 330/330 attacks intercepted, 0/318 faithful controls falsely rejected; attack CI [98.85%, 100%], false-rejection CI [0%, 1.19%]. |
| E5 | Strict-prompt raw narratives had detected-any violation prevalence 2/51 = 3.92%, 95% Wilson CI [1.08%, 13.22%]. | `experiments/runs/2026-07-14_g5_seed42/faithfulness.json`, `arms.strict.off_policy_prevalence.detected_any_violation` | SUPPORTED. Always include `detected`, `n=51`, and the CI. |
| E6 | Strict ON-policy fallback was 2/51 = 3.92%, leaving 49 delivered narratives. | G5 `faithfulness.json`, `arms.strict.on_policy_delivery` | SUPPORTED. The delivered residual detected violation rate is 0/49 **by construction**, not evidence of zero undetected violations. |
| E7 | Simple-prompt raw narratives had detected-any violation prevalence 51/51 = 100%, 95% Wilson CI [93.00%, 100%], and all 51 fell back. | G5 `faithfulness.json`, `arms.simple` | SUPPORTED as a negative experimental finding. Do not describe the simple arm as a useful delivery configuration. |
| E8 | Simple-arm residual delivered-narrative violation is not estimable because zero narratives were delivered. | G5 `faithfulness.json`, `arms.simple.on_policy_delivery.residual_detected_violation_on_delivered` | SUPPORTED. Report `n=0`, `rate=null`; never turn this into `0%`. |
| E9 | The final G5 run had zero transport failures and used the same unmodified raw string for OFF- and ON-policy analysis. | G5 `narratives.jsonl`, `faithfulness.json`, `run_manifest.json`; `docs/reviews/2026-07-14-implementation-review.md` | SUPPORTED. 102 rows = 51 cases × 2 arms. |
| E10 | The final explanation run used local Ollama 0.31.1 with the exact llama3:8b digest `365c0bd...d8ad1`. | G5 `run_manifest.json`, `extra.ollama_runtime`; G5 `faithfulness.json` | SUPPORTED. This identifies the evaluated local runtime; it does not prove privacy preservation. |
| E11 | Only serialized reason-code evidence was sent to the LLM, excluding raw rows, exact feature values, labels, probabilities, and SHAP magnitudes. | `src/narratives/evidence.py`; `src/narratives/llm_client.py`; `tests/test_evidence.py`; `tests/test_llm_client.py` | SUPPORTED as a code/test-backed data-minimization claim. Preferred wording: `privacy-conscious local deployment with data minimization`. |
| E12 | Human audit-estimated undetected violation rate. | Blank sample: `experiments/audit/2026-07-14_g5_seed42_strict_audit_sample.csv`; manifest beside it | PENDING HUMAN WORK. The sample has 49 rows and blank human-only columns. Do not report a rate until a human completes and attests the audit and `tools/score_audit.py` produces a result. |
| E13 | The validator accepts every semantically faithful English paraphrase. | Additional review probes in `docs/reviews/2026-07-14-implementation-review.md` | DROP. Two out-of-corpus faithful paraphrases were confirmed to fall back. Describe the validator as a closed, corpus-calibrated narrative language. |

## Dashboard, novelty, and societal claims

| ID | Planned report claim | Exact supporting evidence | Status and permitted wording |
|---|---|---|---|
| C1 | The React/FastAPI Fraud Review Workbench consumes the exact evaluated detector/G4/G5/results artifacts. | `configs/dashboard.yaml`; `tools/validate_dashboard.py`; `tests/dashboard_backend/`; `app/frontend/e2e/dashboard.spec.ts`; `docs/reviews/2026-07-14-implementation-review.md` | SUPPORTED as an exact configured local-prototype claim. The validator loaded 51 cases and 3 curated scenarios from the verified G6 seed-42 → G4 → G5 → Task 7.1 chain, and production route/deep-link smoke passed. Do not call this a deployed production system. |
| C2 | Live replay sends the same minimized evidence to local Ollama and does not persist output to the configured experiment/report artifacts. | `app/backend/live.py`; `src/narratives/evidence.py`; `tests/dashboard_backend/test_live.py`; production API payload and before/after hash/mtime audit in the implementation review | SUPPORTED as a code/test/production-smoke claim. The live response is `demo-only`, uses `Cache-Control: no-store`, and a real all-endpoint audit left all 21 configured artifact files unchanged. This is not a formal privacy proof. |
| C3 | The system is privacy-preserving. | No artifact proves a formal privacy property. | DROP. Replace with `privacy-conscious local deployment` or `locally deployed explanation architecture with data minimization`. |
| C4 | The detector or workbench is production-ready, real-time, bank-deployed, or proven to improve analyst productivity. | No deployment study, load test, prospective data, security assessment, or analyst trial exists. | DROP. Present it as a locally deployable analyst decision-support prototype. |
| C5 | Within the reviewed literature that we identified, this is an evaluated fraud-specific narrative layer combining local generation, deterministic evidence guardrails, paired OFF/ON measurement, adversarial calibration, and deterministic fallback. | CP1/updated literature matrix plus G5 artifacts and implementation review | PENDING LITERATURE VERIFICATION. Use the full qualified wording only after every cited paper is checked. Never write a bare `first`. |
| C6 | The work can support future fraud analysts by turning model evidence into a consistent review format and by failing back to reason codes when generated text violates the contract. | Architecture and G5 delivery evidence | SUPPORTED as a potential-use argument, not a measured productivity or social-impact outcome. Use `could support`; do not claim time savings or reduced fraud losses. |
| C7 | The project shows that stronger prompt constraints can materially change deliverability under the same local model and evidence format. | G5 strict versus simple arms in `faithfulness.json` | SUPPORTED for this model, dataset, prompt pair, and 51 flagged cases. Do not generalize to all LLMs. |
| C8 | Analysts can persist provisional review status, disposition, notes, and activity without modifying experiment artifacts. | `app/backend/workflow.py`; workflow API routes in `app/backend/server.py`; `tests/dashboard_backend/test_workflow.py`; `app/frontend/e2e/dashboard.spec.ts`; implementation review | SUPPORTED as a local single-user prototype claim. The SQLite workflow plane stores only workflow metadata and an evidence fingerprint; it is not fraud ground truth and is excluded from G0–G7, G4, G5, and report metrics. Records from an older evidence fingerprint are masked and must be explicitly restarted with blank local fields. |
| C9 | Operational review is blind to retrospective ground truth. | `app/backend/artifacts.py`; `/api/v1/cases` routes; `tests/dashboard_backend/test_api.py`; frontend queue/investigation tests | SUPPORTED as an interface-boundary claim. Operational queue and case responses exclude `y_true`, retrospective outcome text, and historical-label filtering. Aggregate evaluation results remain in Model Assurance. |

## Figure and table placement ledger

| Report item | Source | Caption boundary |
|---|---|---|
| Table 4.1: Detector performance by group | `reports/tables/results_summary.csv` | Mean ± SD over seeds 42–46; AUC-PR primary. |
| Appendix Table A.1: Seed-level detector results | `reports/tables/results_main.csv` | Include run IDs and manifest hashes or provide them electronically. |
| Figure 4.1: Recorded test PR curves | `reports/figures/pr_curves.png` | Seed 42 only; not an averaged curve. |
| Table 4.2: Frozen G6 seed-42 metrics | `experiments/runs/2026-07-14_g6_seed42/metrics.json` | Configuration selected using validation evidence; test AUC-PR was 0.820176 for this seed. |
| Figure 4.2: Global SHAP importance | `experiments/runs/2026-07-14_g4_seed42/shap_global_bar.png` | Mean absolute SHAP over the recorded sample; non-causal. |
| Table 4.3: Guardrail calibration | `experiments/calibration/validator_calibration_v1.json` | Synthetic, template-constrained versioned corpus only. |
| Table 4.4: G5 paired-policy outcomes | `experiments/runs/2026-07-14_g5_seed42/faithfulness.json` | Every rate includes numerator/denominator and Wilson CI; preserve `detected` and `by_construction` labels. |
| Table 4.5: Human audit | Future `experiments/audit/audit_result.json` | PENDING; omit until human-attested output exists. |

## Claim discipline checklist

- Every detector number is copied from `results_summary.csv` or `results_main.csv`, not manually recomputed in prose.
- `Improves`, `outperforms`, `superior`, and `significant` are prohibited unless a logged comparison supports the exact word.
- All G5 rates use `detected violation`, include `n` and a 95% Wilson CI, and preserve `by_construction` or `not estimable` where applicable.
- SHAP is described as model attribution, not causation.
- The audit rate remains absent until human-attested scoring exists.
- Novelty language remains qualified by the reviewed literature.
- Workbench claims are limited to exact-artifact consumption, data minimization, immutable research evidence, and separate local workflow persistence verified by tests and production-path review; no deployment, productivity, compliance, or formal privacy claim is permitted.
