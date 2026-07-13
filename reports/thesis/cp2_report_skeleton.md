# CP2 report skeleton — evidence-first draft

Working title: **Credit Card Fraud Detection using a Hybrid Autoencoder–XGBoost Model with Local LLM Explanations**

This skeleton is intentionally conservative. Claim IDs refer to `reports/thesis/results_mapping.md`. Literature citations must come only from papers already supplied or independently fetched and verified.

## Abstract

**Paragraph role — problem.** Introduce extreme class imbalance and the need for analyst-readable explanations without treating accuracy as the headline metric.

**Paragraph role — method.** Summarize the six detector groups, validation-only threshold selection, frozen detector, SHAP reason codes, local llama3:8b narrative generation, deterministic guardrails, paired OFF/ON delivery-policy evaluation, and fallback.

**Paragraph role — results.** Report only mapped facts: G6's descriptive mean test AUC-PR 0.855214 ± 0.027097 over five seeds (D9); G2's near-null difference from G0 (D10); strict detected-any violation/fallback 2/51 with CI (E5–E6); simple 51/51 fallback (E7); corpus calibration scope (E4). Do not include the pending human audit.

**Paragraph role — conclusion.** State that the main contribution is an evaluated, fail-closed narrative layer rather than a new detector algorithm. Use `within the reviewed literature that we identified` only after C5 is verified.

## Chapter 1 — Introduction

### 1.1 Background

- Explain credit-card fraud detection under a 0.172% pre-deduplication fraud prevalence.
- Explain why AUC-PR, recall, precision, and analyst ranking matter more than accuracy.
- Separate detector prediction from explanation delivery.

### 1.2 Problem statement

- Detection models can rank fraud risk but their evidence may be difficult to communicate consistently.
- A free-form LLM explanation may omit, invent, or reverse model evidence.
- Local execution and evidence minimization reduce exposure, but are not formal privacy guarantees.

### 1.3 Aim and objectives

1. Compare original, SMOTE, cost-sensitive, reconstruction-error, and latent-feature detector configurations under one leakage-controlled protocol.
2. Freeze one detector using validation evidence and generate case-level SHAP reason codes.
3. Evaluate a local LLM as a constrained translation layer under strict and simple prompts.
4. Measure detected violations before delivery and fallback behavior after deterministic validation.
5. Demonstrate the evaluated artifacts through a read-only local dashboard after Task 7.4 validation.

### 1.4 Research questions

- RQ1: How do G0/G1/G2/G3/G6/G7 compare descriptively across five fixed seeds using AUC-PR and supporting metrics?
- RQ2: Does AE-derived reconstruction error or latent representation provide a material descriptive advantage over the original-feature baseline in this implementation?
- RQ3: What detected violation and fallback rates arise under strict versus simple prompts for the same local model and reason-code evidence?
- RQ4: How effectively does the deterministic validator intercept the versioned attack corpus while accepting its faithful controls?

### 1.5 Contributions

- A reproducible six-group fraud detector benchmark with stable IDs and provenance-linked artifacts (D4–D7).
- A frozen detector→SHAP reason-code→local narrative chain (E1–E3, E9–E11).
- A paired OFF/ON measurement design that separates raw detected violations from delivered fallback outcomes (E5–E9).
- A versioned adversarial calibration corpus and fail-closed deterministic fallback (E4).
- A negative result: AE/hybrid variants did not show a clear AUC-PR advantage over the original-feature baseline (D10–D12).

### 1.6 Scope

- One public, historical, anonymized European credit-card dataset.
- Offline binary classification; no transaction stream, user study, bank deployment, or causal analysis.
- Local llama3:8b explanation generation for the 51 seed-42 flagged cases only.

## Chapter 2 — Literature review

Reuse the verified CP1 literature, then update it around four explicit axes:

1. Imbalanced fraud detection: XGBoost, SMOTE, and cost-sensitive learning.
2. Autoencoder-derived anomaly and representation features.
3. SHAP-based local evidence and the limits of attribution.
4. LLM explanation faithfulness, local deployment, deterministic validation, and fallback.

End with a literature matrix that records, for every verified paper: fraud domain, detector, attribution source, local/cloud LLM, deterministic guardrail, adversarial evaluation, fallback, and measured faithfulness. The gap claim must remain C5 `PENDING` until that matrix is citation-verified.

## Chapter 3 — Methodology as implemented

### 3.1 Dataset and integrity

- Pre-deduplication: 284,807 rows, 492 frauds (D1).
- Documented content deduplication: 1,081 rows removed; modeling data 283,726 rows, 473 frauds (D2).
- Stable `case_id` created before deduplication and excluded from model features.

### 3.2 Split and preprocessing

- Stratified 70/15/15 split per fixed seed; give seed-42 counts (D3).
- StandardScaler fit on training only and applied to validation/test.
- Validation selects threshold; test evaluates the frozen seed-specific configuration once.

### 3.3 Detector groups

- G0: original XGBoost.
- G1: G0 + train-only SMOTE.
- G2: reconstruction error + XGBoost.
- G3: reconstruction error + train-only SMOTE + XGBoost.
- G6: cost-sensitive XGBoost.
- G7: AE latent features + XGBoost.

Explain that the AE trains only on legitimate training rows and uses an internal training-derived early-stopping partition.

### 3.4 Validation-only tuning and detector freeze

- Describe the two-stage selection in `experiments/DECISIONS.md`.
- State that only G2 and G6 received the 20-trial search (D8).
- Record the frozen G6 parameters and validation evidence.
- Treat tuning asymmetry as a design limitation when comparing group mechanisms.

### 3.5 Evaluation

- Primary metric: average precision/AUC-PR.
- Supporting: ROC-AUC, precision, recall, F1, confusion matrix, Precision@100, Recall@100, training time, test inference time.
- Five seeds; mean ± sample SD.
- Wilson intervals for all G5 rates.

### 3.6 G4 SHAP reason codes

- Explain signed SHAP direction in the pinned XGBoost/SHAP stack.
- Preserve exact case ID, detector score, and evaluation-only label.
- Rank the top three local contributions and generate a global mean-absolute-SHAP summary.

### 3.7 G5 local narrative experiment

- Evidence package: case ID, coarse risk bucket, ranked feature names, direction; no raw row, score, label, exact value, or SHAP magnitude (E11).
- Same local llama3:8b runtime and generation seed for strict and simple arms.
- Exact raw output analyzed OFF policy; same unmodified string validated ON policy.
- Four checks: format, completeness, grounding, direction.
- Any failure delivers deterministic reason codes.
- Calibration gate: 648-item versioned corpus (E4).
- Manual audit design: 49 accepted strict outputs sampled, but human annotations pending (E12).

### 3.8 Reproducibility and provenance

- YAML configs, fixed seeds, environment capture, manifest-last writes, artifact hashes, source hashes, stable IDs, and exact upstream references.
- Explain that `configs/results.yaml` is an allowlist, not a `latest`/glob selection.

### 3.9 Demo architecture

Keep this subsection provisional until C1–C2 pass. Describe React + FastAPI as a read-only local demonstration consumer; do not yet claim exact-artifact integration as completed.

## Chapter 4 — Results

### 4.1 Data and run integrity

Report D1–D7 and cite the results manifest. State that the independent implementation review found no BLOCKER/MAJOR pipeline defect and one MINOR closed-language false-rejection limitation.

### 4.2 Detector comparison

Insert Table 4.1 from `results_summary.csv` and Figure 4.1 from `pr_curves.png`.

Reviewer-facing interpretation:

- G6: 0.855214 ± 0.027097 mean test AUC-PR, numerically highest (D9).
- G7: 0.854767 ± 0.014410, with the highest descriptive mean recall among the listed rows (D12). G2 had the highest descriptive mean F1 at 0.870054.
- G2: 0.853707 ± 0.017449, only +0.000816 versus G0 (D10).
- G3: 0.816870 ± 0.078987, lower and more variable than G0 (D11).
- These are descriptive results. No logged significance test supports superiority language.

### 4.3 Frozen detector and explanations

- Report the frozen G6 seed-42 test metrics separately from the multi-seed mean.
- State that its frozen threshold flagged 51 cases: 50 true positives and one false positive (E1).
- Show the global SHAP figure and one or two anonymized reason-code examples without exposing raw transaction features.

### 4.4 Validator calibration

Report E4 with the corpus scope sentence next to the numbers. Include an attack-category table if space permits. Do not generalize 100% interception beyond this corpus.

### 4.5 Paired narrative experiment

Insert a table with exact numerators, denominators, and Wilson CIs:

- Strict detected-any violation: 2/51, 3.92%, CI [1.08%, 13.22%].
- Strict fallback: 2/51, 3.92%, same CI.
- Strict delivered residual detected violation: 0/49, CI [0%, 7.27%], `by_construction`.
- Simple detected-any violation: 51/51, 100%, CI [93.00%, 100%].
- Simple fallback: 51/51, 100%, same CI.
- Simple delivered residual: not estimable, n=0.
- Transport unavailable: 0/51 per arm, CI [0%, 7.00%].

### 4.6 Human audit

Omit the audit-result table until E12 is completed by a human and scored. The current artifact is a blank 49-row audit package, not a result.

## Chapter 5 — Discussion and limitations

### 5.1 Detector findings

- The detector comparison does not support a strong algorithmic novelty claim.
- AE reconstruction and latent features did not yield a clear AUC-PR advantage over G0.
- Cost-sensitive G6 was a defensible validation-selected detector but its multi-seed mean was only slightly above G0/G2/G7.
- SMOTE effects were mixed and G3 variance was high.

### 5.2 Narrative-layer findings

- Strict instructions greatly increased deliverability relative to the simple prompt for this model and case set.
- Deterministic validation converted detected violations into reason-code fallbacks.
- Zero delivered detected violations is a policy invariant, not proof that the validator detects every semantic defect.
- The confirmed faithful-paraphrase false rejections show the tradeoff of a closed verifier language.

### 5.3 Practical and societal relevance

- Potential value: a consistent explanation format, visible evidence chain, and safe fallback could support analyst review and training.
- Do not claim measured analyst productivity, reduced financial loss, fairness, or public trust; none was evaluated.
- Future social value depends on prospective testing, analyst usability work, governance, and monitoring for dataset/model drift.

### 5.4 Privacy and deployment boundary

- Use **privacy-conscious local deployment with data minimization**.
- Local execution reduces external transmission but does not prove anonymity, confidentiality, differential privacy, or regulatory compliance.
- This is an offline local prototype, not a real-time banking control or production service.

### 5.5 Threats to validity

- Single old, anonymized dataset; limited external validity and no merchant semantics.
- Deduplication changes the fraud count and must be reported transparently.
- Only G2/G6 were tuned; cross-group mechanism attribution is limited.
- One local 8B model, one prompt pair, 51 flagged cases.
- Synthetic guardrail calibration is generated from the same closed language design.
- Human audit is pending.
- No analyst usability, latency under load, fairness, calibration, drift, or deployment study.

### 5.6 Future work

- Complete the human blind audit and report its Wilson interval.
- Add independent human-authored faithful/attack text to a new calibration version.
- Replicate the paired design with another local model and a second dataset only if time permits.
- Conduct analyst usability evaluation and prospective drift testing.
- Finish and independently review the read-only dashboard exact-artifact integration.

## Conclusion

Conclude with three bounded messages:

1. Detector engineering was reproducible, but hybrid features did not produce a clear performance advantage.
2. The evaluated contribution is the measurable, fail-closed narrative layer: raw detected violations, deterministic validation, and fallback are separated explicitly.
3. Results are local to the dataset/model/prompt/corpus studied and should motivate, not substitute for, human and deployment evaluation.

## Appendices

- A: Exact configs and environment versions.
- B: Seed-level detector table with run IDs/manifests.
- C: Leakage and provenance audit summary.
- D: Guardrail corpus taxonomy and category intervals.
- E: G5 prompt templates and data-minimization disclosure.
- F: Human audit instructions and, only after completion, attested result.
- G: Dashboard API/UX contract and exact-artifact smoke evidence.

## Claim–evidence map for the draft

| Major claim | Evidence | Status |
|---|---|---|
| The detector benchmark is leakage-controlled and reproducible. | D3–D7; implementation review | supported |
| G6 is numerically highest by mean AUC-PR but not proven superior. | D9 | supported |
| AE-derived features do not show a clear advantage here. | D10–D12 | supported |
| Strict prompts reduce detected violations/fallback relative to simple prompts for this experiment. | E5–E8 | supported |
| Guardrails eliminate all semantic violations. | No evidence; residual is `by_construction`, audit pending | remove |
| The calibration corpus was fully classified by the validator. | E4 | supported within corpus scope |
| The system is privacy-preserving. | No formal evidence | remove |
| The architecture is novel within reviewed literature. | C5 | needs citation verification |
| The dashboard is the same evaluated system. | C1–C2 | needs implementation evidence |

## Five-dimension self-review

### Contribution

- PASS if the report frames novelty around measured narrative faithfulness and fail-closed delivery, not AE+XGBoost.
- NEEDS REVISION until C5 is verified against the final literature matrix.

### Writing clarity

- PASS when `detected violation`, `fallback`, `delivered`, `by_construction`, and `not estimable` are defined once and used consistently.
- NEEDS REVISION if seed-42 frozen-detector results are mixed with five-seed means.

### Experimental strength

- PASS for honest multi-seed detector results and paired G5 reporting.
- NEEDS NEW EXPERIMENT only for claims about other models, datasets, humans, or deployment.

### Evaluation completeness

- NEEDS HUMAN WORK for the blinded audit.
- NEEDS REVISION if Wilson intervals or denominators are omitted.

### Method design soundness

- PASS for leakage controls, stable IDs, manifests, raw paired-policy measurement, and fallback.
- NEEDS DISCUSSION for tuning asymmetry, the closed validator language, single-model scope, and pending dashboard verification.
