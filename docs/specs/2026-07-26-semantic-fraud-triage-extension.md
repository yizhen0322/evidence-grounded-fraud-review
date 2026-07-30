# Semantic fraud triage evaluation track

**Status:** implementation specification  
**Date:** 26 July 2026  
**Baseline preserved at:** `releases/submission-safe-v1-2026-07-24/`

## 1. Decision

The completed project uses one architecture in two evidence roles. The European
Credit Card Fraud dataset remains the primary real-data detector benchmark
because it is the approved CP1 dataset and has a complete five-seed result
chain. S0 is the primary semantic and operational evaluation context for the
local-LLM explanation layer. Its synthetic transaction stream addresses the
main weakness of the anonymous V1 to V28 features: they cannot support
business-readable alert explanations.

S0 does not replace the detector benchmark or rewrite its results. The two
tracks answer different questions. ULB evaluates detector configurations on
historical public data. S0 evaluates how readable evidence passes through raw
SHAP reason codes, a deterministic renderer, guarded local-LLM generation, and
fail-closed fallback.

## 2. Research question

The semantic and operational track answers one additional question:

> How does a guarded local-LLM case brief differ from raw SHAP reason codes and
> a deterministic renderer when the fraud evidence contains business-readable,
> readable current-transaction fields and leakage-controlled historical features?

The comparison is descriptive. It reports validator-detected violation rate,
fallback rate, transport-failure rate, local model-request latency,
evidence-key coverage, brief length, and vocabulary outside the catalogue. Every
rate includes n and a 95% Wilson interval. It does not claim analyst productivity,
clarity, usefulness, or user preference because no human-subject study has been
approved.

## 3. Data source and attribution

The synthetic stream is independently implemented from the documented design of
the Fraud Detection Handbook simulator. The implementation does not copy the
handbook notebook source. The report cites the retrieved official simulator and
baseline feature-transformation chapters and identifies the local generator as
an adaptation. Source authorship, date, URL, and licence are copied from the
retrieved source.

The generated rows contain:

- transaction ID and timestamp;
- customer and terminal identifiers;
- transaction amount;
- fraud label and fraud-scenario identifier;
- synthetic customer and terminal profile relationships.

The generator is deterministic for a fixed configuration and seed. Generated
CSV files remain outside version control, while the configuration, source hashes,
dataset hash, counts, and run artifacts are recorded.

## 4. Leakage controls

The semantic stream is split chronologically into 70% training, 15% validation,
and 15% test periods. The test period is not used for model choice, feature
design, threshold selection, prompt revision, or guardrail calibration.

All behavioural features use information available strictly before the current
transaction. Customer rolling windows exclude the current transaction. For a
transaction at time t, `TerminalFraudRisk7Day` uses terminal transactions in the
seven-day risk window ending at t minus the configured seven-day feedback delay.
Both widths are stored in the config and manifest. No customer or terminal
aggregate can read future rows.

Validation and test rows may use earlier history, including training-period
transactions, because that history would already exist at scoring time. No purge
gap is applied at split boundaries; this simplification is disclosed as a
limitation.

The validation set selects the decision threshold by maximum F1. The threshold
is frozen before the test set is evaluated.

## 5. Semantic feature catalogue

The detector uses a compact interpretable set rather than anonymous PCA
components:

| Evidence key | Display label | Meaning |
| --- | --- | --- |
| `TransactionAmount` | Transaction amount | Current synthetic transaction amount |
| `AmountVsCustomer30Day` | Amount vs customer 30-day average | Ratio to the customer's past-only 30-day mean |
| `CustomerTxCount1Day` | Customer activity in 24 hours | Past-only transaction count in the previous day |
| `CustomerTxCount7Day` | Customer activity in 7 days | Past-only transaction count in the previous week |
| `MinutesSinceCustomerTx` | Time since customer's prior transaction | Short gaps indicate a burst |
| `NewTerminalForCustomer30Day` | New terminal for customer | Terminal absent from the customer's prior 30-day history |
| `TerminalTxCount7Day` | Terminal activity in 7 days | Past-only terminal transaction count |
| `TerminalFraudRisk7Day` | Delayed terminal fraud rate | Seven-day risk window using labels delayed by seven days |
| `TerminalDistanceFromCustomerHome` | Terminal distance from customer home | Synthetic profile distance available at transaction time |
| `DuringNight` | Night-time transaction | Transaction occurred from midnight through 06:00 |
| `DuringWeekend` | Weekend transaction | Transaction occurred on Saturday or Sunday |

Exact values are available to the detector and analyst evidence panel. The local
LLM receives only the evidence key, display label, direction, rank, and a coarse
value bucket. It does not receive customer ID, terminal ID, exact amount,
probability, historical label, or SHAP magnitude.

## 6. Explanation comparison

Every selected semantic alert produces three outputs from the same signed SHAP
evidence:

1. **Raw reason codes:** ranked feature keys and directions.
2. **Deterministic brief:** fixed text generated from the feature catalogue and
   coarse buckets.
3. **Guarded local-LLM brief:** Ollama returns a structured JSON candidate. A
   deterministic validator verifies the exact evidence-key set, rank, direction,
   allowed vocabulary, risk bucket, schema, and absence of unauthorized numbers.
   Invalid or unavailable output falls back to the deterministic brief.

The raw reason-code and deterministic arms are generated directly from the bound
evidence record, so their zero detected-violation rate is `by_construction`. Only
the local-LLM arm has an empirical deliverability and fallback rate.

The semantic structured-output validator has a separate versioned attack-and-
control corpus. It is calibrated before any test-period narrative is generated.
The previous anonymous-feature calibration results do not transfer to this
contract. The semantic prompt hash, validator source hash, corpus hash, generator
config hash, and Ollama digest are frozen and recorded before test generation.

The LLM does not diagnose fraud, create new evidence, or choose the case outcome.
Its intended role is to articulate already selected model evidence. The study
must report whether the recorded model output actually adds detail relative to
the deterministic renderer rather than assuming that it does.

## 7. Application design

The workbench defaults to an **Operational simulation** queue backed by the
semantic case-study artifacts. The existing anonymous benchmark remains
available under **Research benchmark**.

The operational queue shows readable primary signals, review status, transaction
time, amount, customer activity, terminal context, and explanation delivery
state. Case Review presents:

- alert rank and frozen detector threshold;
- a plain-language evidence summary;
- signed SHAP contributions with readable labels;
- raw reason codes, deterministic brief, and guarded local-LLM brief side by side;
- the exact minimized payload sent to Ollama;
- validator checks and fallback reason;
- workflow action and notes.

The UI must state that all entities and transactions in this route are synthetic.
It must not imply a bank deployment or real customer validation.

Changing the landing route requires the report's application description and
screenshots to be recaptured. The existing 30-run ULB result allowlist and
detector-to-G4-to-G5 evidence chain remain unchanged.

## 8. Run contract

The semantic run is written under
`experiments/runs/<date>_s0_seed<seed>/` and contains at least:

- `config.yaml`;
- `dataset_summary.json`;
- `split_summary.json`;
- `split_assignments.parquet`;
- `metrics.json`;
- `predictions.parquet`;
- `reason_codes.jsonl`;
- `semantic_cases.jsonl`;
- `explanation_comparison.jsonl`;
- `explanation_summary.json`;
- `model/xgb.json`;
- `environment.txt`;
- `run_manifest.json`.

The registered default S0 configuration generates 50,000 transactions across
1,500 synthetic customers and 400 synthetic terminals over 150 days. Generator
and detector seeds remain separate manifest fields even when both use 42 in the
registered run.

The run manifest records source hashes, dataset hash, feature names, threshold,
generator configuration, split boundaries, Ollama identity when used, and every
generated artifact.

## 9. Acceptance criteria

- Re-running the generator with the same seed produces the same dataset hash.
- Unit tests prove that every rolling feature is past-only.
- A future-row mutation cannot alter an earlier row's engineered features.
- The semantic detector has a logged validation-selected threshold and test
  metrics. No minimum score is imposed.
- Every explanation row binds to one prediction and one SHAP evidence record by
  transaction ID.
- Validator attacks cover direction flips, missing evidence, invented evidence,
  reordered ranks, unauthorized numbers, malformed JSON, and transport failure.
- The semantic validator calibration corpus passes before test-period generation;
  its per-category results and false-rejection counts are logged separately from
  the ULB guardrail corpus.
- Prompt, validator, corpus, generator configuration, and Ollama identity are
  frozen by hash before test-period generation.
- The application works with Ollama stopped by displaying deterministic fallback.
- Existing ULB experiment and dashboard tests continue to pass.
- The report states the two evidence roles explicitly: ULB is the primary
  real-data detector benchmark, while S0 is the primary semantic and operational
  local-LLM evaluation context. Neither is generalized to a real bank environment.
- Semantic metrics are never compared with, ranked against, or used to revise a
  ULB result because the studies differ in data-generating process, feature set,
  prevalence, and split design.
- `DuringNight` means local simulator time from 00:00 through 06:00 inclusive.
  A customer with no prior 30-day terminal history has
  `NewTerminalForCustomer30Day = 1`.

## 10. Report changes

The final report keeps the original detector results intact and presents S0 as
the main semantic and operational explanation study. It includes:

- the operational interpretability motivation in Chapters 1 and 2;
- the simulator, chronological split, current transaction fields, leakage-controlled historical features, and structured
  explanation contract in Chapter 3;
- semantic detector and explanation-comparison results in Chapter 4;
- a discussion of what the LLM adds beyond SHAP and what it still cannot add in
  Chapter 5;
- simulator limitations and synthetic-to-real transfer limits in Section 5.6,
  future external validation in Section 5.7, and a bounded conclusion in Chapter
  6;
- official Fraud Detection Handbook references.

The update also covers the Abstract, objectives, research questions, scope,
research-question summary, evidence map, software and verification appendix,
lists of tables and figures, and recaptured application figures. Test and
artifact counts are read from fresh verification output.

All new quantitative statements must be read from the semantic run artifacts.
The text must not contain placeholder numbers.
