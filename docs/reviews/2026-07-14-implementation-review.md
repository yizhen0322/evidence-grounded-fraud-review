# Independent implementation review — 2026-07-14

Verdict: **COMMENT** — the committed detector→G4→G5→results pipeline and React/FastAPI dashboard are provenance-valid with no open BLOCKER or MAJOR finding. The dashboard exact-artifact integration is cleared; one confirmed MINOR validator false-rejection boundary remains.

- Pipeline review baseline: `6dd766aab32f364193975707f8ef5286ef30bf81`
- Dashboard review baseline: `b15aed586101a59813b73e924c2a8bd31f47e619`
- Reviewer role: independent adversarial Codex review; no experiment artifact was modified or regenerated.
- Architectural status: **WATCH** for the overall project because the validator deliberately implements a closed accepted-language grammar. Dashboard architectural status: **CLEAR** after exact-artifact, read-only, recorded/live-separation, and production-route verification.
- Recommendation: **COMMENT**. The implementation is suitable for report drafting and examiner rehearsal if the validator limitation and remaining human-only work are stated explicitly.

## Findings

### BLOCKER

None.

### MAJOR

None.

### MINOR

[MINOR] Closed direction grammar rejects faithful paraphrases outside the calibrated control set
- Location: `src/narratives/guardrails.py:32-68`, `src/narratives/guardrails.py:185-267`, `tools/build_guardrail_corpus.py:188-297`
- Status: CONFIRMED
- Contract: G5 must test faithful text that may be falsely rejected, report false rejection honestly, and describe validator calibration only within the versioned corpus.
- Failure scenario: For G4 case `83417`, both texts below preserve the High risk bucket, all three allowed features, their increasing-risk direction, bullet order, and the exact ACTION line, but `validate_narrative()` falls back because the narrative predicate is outside `DIRECTION_PHRASES`.

  Input 1:

  ```text
  NARRATIVE: This case is rated High risk. The presence of V14, V12, and V10 are all risk-increasing factors.

  EVIDENCE:
  - V14 - increases risk
  - V12 - increases risk
  - V10 - increases risk

  ACTION: Recommended for manual review.
  ```

  Observed result 1:

  ```json
  {"ok": false, "checks": {"format": true, "completeness": true, "grounding": false, "direction": false}, "fallback": true}
  ```

  Input 2:

  ```text
  NARRATIVE: This case is rated High risk. The presence of V14, V12, and V10 all contribute toward higher risk.

  EVIDENCE:
  - V14 - increases risk
  - V12 - increases risk
  - V10 - increases risk

  ACTION: Recommended for manual review.
  ```

  Observed result 2:

  ```json
  {"ok": false, "checks": {"format": true, "completeness": true, "grounding": false, "direction": false}, "fallback": true}
  ```

- Evidence: A direct `uv run python` call against the final G4 record reproduced both results. The same probe accepted the canonical recorded strict output and the safe phrase `all raise risk`. The calibration artifact correctly scopes its `0/318` false-rejection result to the synthetic versioned corpus, so this does not falsify that logged number; it demonstrates an out-of-corpus language boundary.
- Minimal repair direction: Keep fail-closed delivery. Either add these paraphrase families to a new versioned faithful-control corpus and extend the closed grammar before any future G5 rerun, or retain the current validator and state that it verifies a deliberately restricted narrative language rather than arbitrary semantically equivalent English. No current result needs regeneration if the implementation is unchanged.

## Resolved during dashboard review

These were confirmed during Review F and fixed before the dashboard baseline above; they are not open findings.

1. **Closed provenance drawer retained a hidden keyboard target.** `app/frontend/src/components/AppShell.tsx` now makes the closed drawer `inert`, and `app/frontend/e2e/dashboard.spec.ts` proves that the attribute is removed only while the drawer is open.
2. **Dashboard configuration accepted more loopback hosts than the evaluated Ollama client.** `app/backend/settings.py` now reuses `src.narratives.llm_client.assert_local_ollama_host()`, and `tests/dashboard_backend/test_settings.py` rejects the previously accepted `127.0.0.2` mismatch.

## Additional guardrail probes

No unfaithful bypass was found in the additional case-`83417` probes. All of the following produced `fallback=true`:

| Probe | Failed checks |
|---|---|
| Narrative direction flip for V14 | `direction` |
| Negated contribution (`do not contribute`) | `grounding`, `direction` |
| Ambiguous direction (`are related to risk`) | `grounding`, `direction` |
| Extra known feature V1 | `grounding`, `direction` |
| Invented `merchant_score` | `grounding`, `direction` |
| Unauthorized `91.7%` probability | `format`, `grounding` |
| Duplicated V14 evidence bullet | `completeness`, `direction` |
| Reordered evidence bullets | `completeness`, `direction` |
| Unicode bullet replacement | all four checks |

The fallback text was deterministic and was rebuilt from the bound G4 record's ranked reason codes.

## Review evidence by charter area

### A — Data, splits, and leakage

- `load_raw()` creates `case_id` before optional deduplication; deduplication excludes `case_id` from its content comparison and preserves the surviving original ID.
- The model matrices are built only from the explicit `FEATURES` list. `Class` and `case_id` do not enter the scaler, AE, SMOTE, or XGBoost feature matrix.
- Split order is load → documented deduplication → stratified split → train-fitted scaling → optional train-legitimate AE → optional train-only SMOTE → XGBoost.
- The final seed-42 split contains 198,608/42,559/42,559 train/validation/test rows and 331/71/71 frauds after 1,081 duplicate rows were removed.
- All 30 exact detector runs in `configs/results.yaml` passed `tools.leakage_audit.audit_run()`.
- Threshold selection correctly drops the extra terminal precision/recall point before indexing the shorter threshold array and uses `score >= threshold` consistently.

### B — Metrics and reproducibility

- Metrics were independently recomputed from `predictions.parquet` for `2026-07-14_g0_seed42` and `2026-07-14_g6_seed46`. AUC-PR, ROC-AUC, precision, recall, F1, and the confusion matrix matched `metrics.json`.
- The raw decimal strings in `results_main.csv` match the corresponding JSON values. A `pandas.read_csv()` float round-trip differed by approximately `1.11e-16` for two G6 seed-46 fields; this is parser representation, not a changed result.
- The positive score column is `predict_proba(... )[:, 1]`; confusion-matrix labels are fixed `[0, 1]`; top-100 ties use a stable sort.
- The final artifacts record the exact validation-selected threshold, feature list, seed, library environment, training time, and test inference time.

### C — Provenance and run selection

- Dataset SHA-256 independently matched `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`.
- `configs/results.yaml` contains exactly 30 unique pairs: G0/G1/G2/G3/G6/G7 × seeds 42–46. The results manifest contains 30 exact input references, the main table has 30 rows, and the summary table has 6 rows.
- Current source hashes and `git show <manifest.git_commit>:<path>` hashes matched the recorded source hashes for sampled G0, G6, G4, and G5 manifests.
- The exact source chain validated as G6 seed 42 → G4 seed 42 → G5 seed 42 using only `{run_id, manifest_sha256}` references.
- Results output hashes and row counts reproduced through `validate_results_manifest()`.

### D — G4 and SHAP

- The committed shuffled-row test proves `select_flagged()` joins by `case_id`, not position, and duplicate/missing IDs are rejected.
- The final detector has 51 positive predictions; G4 contains exactly 51 unique reason-code records with identical case IDs, scores, and labels.
- G4 uses the saved detector predictions as authoritative and computes SHAP only for explanation; it does not replace scores or predictions.
- The frozen G6 source has the original 30-feature vocabulary, and G4's manifest inherits the exact same ordered list.

### E — Guardrails and G5

- The versioned calibration contains 648 items: 330 attacks and 318 faithful controls. It reports 330/330 detected attacks and 0/318 false rejections, with Wilson intervals and an explicit synthetic-corpus scope statement.
- The final G5 run has 51 cases per arm, 102 unique case/arm rows, exact `raw_output == candidate_text`, and zero Ollama transport failures.
- Strict arm: detected-any violation and fallback were both 2/51 = 3.92%, 95% Wilson CI [1.08%, 13.22%]. Forty-nine narratives were delivered.
- Simple arm: detected-any violation and fallback were both 51/51 = 100%, 95% Wilson CI [93.00%, 100%]. No simple-arm narrative was delivered, so its residual delivered-narrative rate is not estimable.
- Strict delivered residual detected violation was 0/49 with `by_construction=true`; this is not evidence that undetected violations are zero.
- Ollama identity is pinned to version `0.31.1` and digest `365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1`. The client rejects non-loopback endpoints and disables proxy-environment inheritance.
- The blank human audit contains 49 accepted strict narratives. Its human columns remain blank; therefore no audit-estimated undetected-violation rate exists yet.

### F — Dashboard and claim boundaries

- The committed `configs/dashboard.yaml` pins exact detector/G4/G5/results paths and loopback hosts. The selected faithful case (`42009`) is a recorded accepted strict narrative; the uncertainty case (`120085`) is the detector's single seed-42 false positive; the attack case is intended for deterministic mutation.
- `tools/validate_dashboard.py --config configs/dashboard.yaml` loaded 51 cases and 3 predicate-validated scenarios and verified the exact G6 seed-42 → G4 → G5 → Task 7.1 source chain.
- The production FastAPI build started on `127.0.0.1:8000`. Real-browser smoke covered Queue, Investigation, Guardrail Lab, Results, and a direct `/cases/42009` refresh. Detector and G4/G5 result stages remained visibly separate.
- A real live API call returned `mode=live_demo`, `reported=false`, four `PASS` checks, and `Cache-Control: no-store`. A later real-browser call exercised the transport-unavailable path and displayed deterministic fallback with four `NOT_RUN` checks rather than treating the outage as a validation failure.
- All three real server-side attack presets triggered the intended check (`direction`, `grounding`, `format`) and deterministic fallback through `src.narratives.guardrails.validate_narrative`.
- A before/after SHA-256 and nanosecond-mtime audit covered 21 configured detector/G4/G5/results/table/figure files across every GET, live POST, and attack POST; no file changed. Ten public JSON responses were also scanned without exposing an absolute repository path.
- The displayed live evidence payload contained only case ID, coarse risk, feature names, direction, and rank; it excluded the detector score/probability, historical label, exact values, and SHAP magnitudes.
- Approved wording is **exact-artifact local demonstration prototype** and **privacy-conscious local deployment with data minimization**. `privacy-preserving`, `production-ready`, and `real-time deployed` remain unsupported.

### G — Tests and completeness

- `uv run pytest -q` passed: 168 tests, 12 dependency deprecation warnings.
- Dashboard-specific verification passed: 20 FastAPI/backend tests, 2 Vitest component tests, 8 Playwright E2E tests, ESLint with zero warnings, TypeScript/Vite production build, and the exact dashboard validator.
- Playwright covers all three attacks, live success, transport fallback with four `NOT_RUN` states, deep-link refresh, detector/explanation stage separation, keyboard route navigation, closed-drawer focus exclusion, and rejection of non-loopback browser traffic.
- No committed `xfail` or `skip` was observed in the reviewed test set.
- Critical negative contracts exist for split IDs, threshold indexing, G4 joins, G5 final-run invariants, forged G5 semantics, source hashes, local Ollama endpoints, audit reconstruction, results allowlisting, and output hash changes.
- Task 7.4 implementation and production-path review are complete. Projector-room readability and three human timed rehearsals remain presentation preparation rather than missing code.

## Accepted false positives and contract-based rebuttals

1. **CSV float inequality after parsing:** Two G6 seed-46 floats compared unequal after `pandas.read_csv()` by about `1.11e-16`. The CSV source strings exactly equal the JSON decimal strings, so this is not a reporting mismatch.
2. **Simple arm has 100% fallback:** This is a logged negative experimental result for the deliberately weaker prompt, not a failed final run. The same raw text is judged and the delivery policy works as designed.
3. **Audit requested 50 but contains 49:** Only 49 strict narratives passed the guardrails. `make_audit_sample.py` correctly samples `min(requested_n, accepted_n)` and records `requested_n=50`, `actual_n=49`.
4. **G6 mean AUC-PR is numerically highest:** The difference from G0 is only +0.002324 and no paired significance test is logged. The report may state the descriptive means, but not that G6 is superior or significantly better.

## Tested commands

```bash
uv run pytest -q
uv run python tools/validate_dashboard.py --config configs/dashboard.yaml
npm --prefix app/frontend test
npm --prefix app/frontend run lint
npm --prefix app/frontend run build
npm --prefix app/frontend run e2e
```

Read-only Python verification also executed:

- `collect_selected('configs/results.yaml')` and `validate_results_manifest('reports/results_manifest.json')`;
- `validate_run_manifest()` and `audit_run()` for all 30 allowlisted detector runs;
- independent metric recomputation for G0 seed 42 and G6 seed 46;
- `validate_reportable_g5_run('experiments/runs/2026-07-14_g5_seed42')`;
- `assert_calibration_gate()` against the final G4 feature vocabulary;
- current-source and recorded-commit source hash comparisons for sampled G0/G6/G4/G5 manifests;
- direct `validate_narrative()` probes listed above;
- production HTTP/browser route smoke, data-minimization inspection, all three attack presets, live success/fallback, public-path scan, and 21-file hash/mtime no-write audit.

## Untested areas and why

- Full-data retraining was prohibited by the review charter; saved artifacts, manifests, unit tests, and recomputation were used instead.
- Human audit scoring was not run because the audit columns are intentionally blank and may only be filled by humans.
- Projector-room readability and three complete timed examiner rehearsals require the student's presentation setup and remain pending.
- Claude review was authorized but could not run because the local Claude CLI had no authenticated session or `ANTHROPIC_API_KEY`; native adversarial review and executable verification were used instead.
- No external citation or literature novelty review was performed in this code-review task.

## Count

- BLOCKER: 0 confirmed, 0 suspected
- MAJOR: 0 confirmed, 0 suspected
- MINOR: 1 open confirmed, 0 suspected; 2 dashboard findings confirmed and resolved before the dashboard review baseline.
