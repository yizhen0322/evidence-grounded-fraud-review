# Fraud alert review application

Student: Ng Yi Zhen (23076003)  
Programme: BCS (Hons), School of Computing and Artificial Intelligence, Sunway University  
Purpose: system description for Capstone Project 2 submission, demonstration, and supervisor discussion

## 1. System purpose

The application is a locally hosted fraud alert review system. It takes transactions flagged by a frozen detector and presents each one as a case that a human analyst can review. Every case contains the detector decision, ranked model evidence, a readable case brief, and a place to record the next routing action.

The project addresses more than binary classification. A detector can assign a high fraud score, but the score does not explain which model inputs moved the prediction. SHAP can provide signed feature attributions, although a raw SHAP table still requires technical interpretation. A local large language model can turn the ranked evidence into a shorter case brief, but generated text creates another risk: it may omit evidence, introduce a feature that was not supplied, or reverse the direction of a contribution.

The application keeps these responsibilities separate. XGBoost detects. SHAP records model attribution. Ollama drafts a case brief from a limited evidence package. Deterministic guardrails decide whether that draft may be shown. The analyst remains responsible for the next action.

The implementation uses one application with two evidence roles. The ULB dataset is the primary real-data detector benchmark. S0 is the primary semantic and operational local-LLM evaluation because its synthetic transaction fields have readable meanings. The two detector score scales are never compared.

This is a single-user local prototype. It is not deployed in a bank, does not process live payments, and is not presented as a production-ready or compliance-certified system.

## 2. Intended user and supported decision

The primary user is a fraud analyst reviewing a queue of model-flagged transactions on a local machine. A model-risk reviewer may also use the assurance and performance pages to inspect the evidence chain, guardrail behaviour, and recorded experimental results.

The application supports a routing decision rather than a final fraud verdict. In the Investigation Workspace, the analyst can:

- escalate the case for investigation;
- close it without escalation; or
- request additional information.

The application stores these choices internally as `suspicious`, `not_suspicious`, and `inconclusive`. They are provisional workflow outcomes. They do not change the detector result and are not treated as historical ground truth.

The operational case and queue APIs do not expose `y_true`. This matters because an analyst working on a real alert would not have the answer in advance. The reviewer must make a routing decision from the available evidence, not from an evaluation label.

## 3. How the system runs

The web application starts from frozen research artefacts. The browser does not retrain a model or recompute scores, SHAP values, experimental metrics, or recorded narratives.

At startup, `app/backend/settings.py` loads `configs/dashboard.yaml`. The configuration points to exact directories for the ULB detector, G4 reason codes, G5 narratives, aggregated results manifest, and the frozen S0 semantic run. Wildcards and a `latest` selector are rejected. The FastAPI server and Ollama host must use loopback addresses, and the workflow database must remain outside the experiment and report directories.

The backend then validates both evidence roles. The ULB loader joins the detector, G4, and G5 records with the stable `case_id` and verifies the linked manifests. The S0 loader independently verifies its chronological run, calibration result, minimized LLM payloads, saved validation decisions, and manifest hashes. The application exposes 51 ULB benchmark alerts and 25 S0 semantic cases. This is the immutable evidence plane.

The analyst uses the application as follows:

1. Open the Alert Queue, which defaults to S0 operational simulation cases.
2. Select an alert and inspect the readable signed SHAP evidence.
3. Compare the raw reason codes, deterministic brief, guarded local-LLM candidate, validator decision, and delivered output.
4. Record a provisional routing action and analyst note.
5. Complete the case, defer it for follow-up, or save it and open the next alert.
6. Switch the Source filter to Research benchmark when demonstrating the ULB detector evidence chain.

Analyst-created state is stored in `var/dashboard/workflow.sqlite3`. The SQLite database contains the source namespace, case identifier, workflow status, provisional disposition, note, revision, evidence fingerprint, and local activity events. The namespace prevents equal numeric identifiers from the S0 and ULB sources from sharing state. The database does not store or modify model scores, labels, SHAP values, narratives, raw transaction rows, or reported metrics.

Each workflow write includes the revision that the browser last read. If another browser tab has already updated the same case, the API returns HTTP 409 instead of silently overwriting the newer record. The evidence fingerprint also prevents an old workflow decision from appearing current after the underlying evidence has changed.

## 4. Responsibility of each component

### XGBoost detectors

XGBoost is the authoritative classifier in both evidence roles. The ULB benchmark uses the frozen G6 seed-42 cost-sensitive detector at the validation-selected threshold of 0.989038 and contains 51 flagged test cases. S0 uses a separate cost-sensitive XGBoost detector with 11 readable features, a chronological split, and a validation-selected threshold of 0.972929. Its frozen test period contains 25 above-threshold alerts. S0 is used for semantic and operational evaluation, not to revise the ULB detector ranking.

### Autoencoder experiments

The Autoencoder configurations are research alternatives rather than runtime components of the delivered workbench. G2 and G3 add reconstruction error, while G7 adds latent bottleneck features. Their results remain visible on the Detector & Policy Evidence page so that the project can compare the proposed hybrid approaches with the original-feature and imbalance-handling baselines.

The experiments did not show a clear detector advantage from the Autoencoder-derived features. The application therefore uses the selected cost-sensitive XGBoost detector recorded in the project artefacts rather than forcing an Autoencoder into the deployed review flow solely because it appears in the project title.

### SHAP attribution

SHAP explains how features contributed to a frozen model output. For each flagged case, the system keeps the largest signed contributions and labels each one as pushing the score towards fraud or towards legitimacy.

In S0, the feature labels describe readable synthetic concepts such as amount relative to customer history, terminal distance, night-time activity, and delayed terminal risk. In ULB, V1 to V28 remain anonymous transformed components. Neither set of SHAP values is a causal explanation.

### Local Ollama narrative

Ollama runs `llama3:8b` locally at `http://127.0.0.1:11434`. It receives a minimised evidence package and produces candidate text under a fixed output contract.

The model does not classify the transaction. It does not receive the raw transaction row, identifiers, exact feature values, detector probability, SHAP magnitudes, or historical label. In S0, the payload contains relative review priority plus ranked evidence keys, readable labels, directions, ranks, and coarse value buckets. The ULB research payload contains anonymous feature names and directions.

### Deterministic guardrails and fallback

The validator in `src/narratives/guardrails.py` treats every generated narrative as untrusted candidate text. Four checks decide whether it can be delivered:

| Check | What it verifies |
|---|---|
| Format | The required `NARRATIVE`, `EVIDENCE`, and `ACTION` structure is present and no unauthorised number appears. |
| Completeness | Every required ranked evidence item appears in the expected order. |
| Grounding | The narrative does not introduce a feature outside the evidence package. |
| Direction | Every feature direction matches its signed SHAP reason code. |

If any check fails, the candidate is rejected. The system then creates a deterministic fallback from the bound reason-code record. It does not try to repair or normalise the rejected narrative, so the original generation behaviour remains measurable.

### FastAPI, React, and SQLite

FastAPI loads the verified snapshot, exposes the read-only evidence endpoints, handles local workflow updates, runs the guardrail demonstrations, and provides optional live narrative regeneration. It also serves the production frontend build.

React, TypeScript, and Vite provide the analyst interface. SQLite stores only the local workflow state created by the analyst. This separation prevents routine review actions from changing the research evidence.

## 5. What each page is for

### Alert Queue

The Alert Queue is the starting page and the analyst's daily work list. It defaults to S0 operational simulation cases so the first screen contains readable transaction evidence. Cases that need follow-up appear first, followed by active reviews, unreviewed cases using fallback, and the remaining unreviewed alerts. Detector rank is used as a tie-breaker within each source.

The table shows the source, case or transaction identifier, transaction context, rank within that detector, explanation delivery status, leading signal, review state, and last update. Source options are S0 operational cases, All sources, and ULB research benchmark. Filters narrow the queue by review state or explanation delivery. Search can match a case identifier, feature name, or amount.

### Investigation Workspace

The Investigation Workspace combines immutable evidence with a separate decision rail.

For S0 cases, the evidence area shows synthetic amount and timestamp, detector rank and threshold, readable signed SHAP contributions, and coarse evidence buckets. A comparison area places raw SHAP reason codes, the deterministic brief, guarded local-LLM candidate, validation outcome, and delivered analyst brief together. A disclosure panel shows the minimized payload and excluded fields.

For ULB research cases, the same route shows Amount, elapsed dataset time, frozen detector evidence, anonymous V-features, the saved G5 brief, and optional temporary regeneration. Live output is not saved into the research artefacts.

The decision rail contains the workflow status, routing choice, a note of up to 2,000 characters, save and follow-up controls, completion controls, and the local activity history. This is where the human decision is recorded.

### Guardrail Tests

Guardrail Tests is for testing the explanation policy. Direct entry defaults to the S0 structured validator. An explicit research mode remains available for the ULB G5 narrative contract. It is not part of normal alert handling.

The user selects a case and a controlled mutation. The backend modifies the recorded narrative, runs the real validator, and displays the original text, mutated text, four check results, final policy verdict, and fallback output. The page does not accept arbitrary free-form attack text, and the mutation is never written back to the recorded artefacts.

### Detector & Policy Evidence

Detector & Policy Evidence presents recorded offline evaluation. It is not a live monitoring page.

The page presents S0 semantic and operational evidence first: detector metrics, local-LLM acceptance and fallback, latency, validator calibration, payload scope, and explicit synthetic-data boundaries. The ULB lane follows with the six experimental groups across five fixed seeds, mean F1 with standard-deviation error bars, grouped precision and recall bars, false-positive and false-negative counts, Average Precision, ROC-AUC, Precision@100, Recall@100, inference time, and precision-recall curves.

The narrative section reports detected format, completeness, grounding, direction, and any-violation rates with sample sizes and 95% Wilson confidence intervals. It also shows fallback delivery, successful pass rate, transport-unavailable counts, and mean generation latency. These are experiment results, not live service-level metrics.

## 6. Why the local LLM is included

The reason codes are the trusted evidence. S0 makes them readable enough to test whether a local language model adds anything beyond the deterministic renderer. Ollama receives only the minimized package and returns a candidate brief under a structured contract. The validator either accepts that candidate or delivers deterministic fallback.

Its role is deliberately narrow. The LLM cannot change the score, add evidence, or choose the routing outcome. Its output has no authority until deterministic validation passes. If validation fails or Ollama is unavailable, the analyst receives reason-code fallback and can continue reviewing the case.

The recorded S0 result did not show added analyst detail. All 23 accepted model responses selected the shorter permitted summary, while the two responses that selected the detailed option corrupted other structured fields and were rejected. The project has not measured whether analysts find the generated brief more useful than a deterministic renderer. The demonstrated contribution is the controlled, observable delivery boundary and the honest comparison, not a productivity claim.

## 7. Fixed demonstration scenarios

### Scenario A: accepted S0 case brief

1. Open transaction 2365335092145894 from the default S0 queue.
2. Show the readable ranked SHAP evidence and coarse buckets.
3. Compare the raw reason codes, deterministic brief, guarded local-LLM brief, and delivered output.
4. Confirm that format, completeness, grounding, and direction all pass.
5. Inspect the minimized Ollama payload and excluded fields.
6. Record a routing action and analyst note, then complete the case.

This scenario shows the normal path from readable alert evidence to a validated brief and recorded human action. In the frozen S0 run, 23 of 25 candidates passed the structured validator.

### Scenario B: Ollama unavailable

1. Stop or disconnect the local Ollama service.
2. Open an existing case. The saved recorded explanation and all detector evidence remain available.
3. Request a temporary local regeneration.
4. Show the `llm_transport_unavailable` fallback reason and the deterministic reason-code brief.

This scenario demonstrates that the LLM is optional for continuity. An unavailable generation service does not remove the recorded evidence or block the analyst workflow.

### Scenario C: rejected S0 candidate

1. Open transaction 3069170327433504, one of the two recorded S0 fallback cases.
2. Compare the malformed structured candidate with the deterministic delivered brief.
3. Open S0 Guardrail Tests and select the direction-flip condition.
4. Run the real structured validator and show the failed direction decision.
5. Show the rejection verdict and deterministic fallback.

The unlisted-feature condition can be used to demonstrate grounding failure, while template corruption demonstrates format failure. None of these assurance tests changes the stored research artefacts.

## 8. Data scope and limitations

The detector benchmark uses the public European credit card fraud dataset. It contains 284,807 transactions and 492 fraud cases before deduplication. Content-based deduplication leaves 283,726 rows and 473 fraud cases.

Features V1 to V28 are anonymised principal components. The ULB dataset does not contain interpretable merchant, customer, device, location, or transaction-description context. S0 addresses the semantic evaluation problem with readable synthetic fields, but its customers, terminals, transactions, and labels are simulated rather than observed in a bank.

The privacy controls are architectural rather than certified. Ollama runs over loopback, the generation payload is minimised, and temporary live output is not counted as recorded experimental evidence. These measures reduce unnecessary disclosure, but they do not prove regulatory compliance or complete system security.

The empirical findings are also limited. The detector study covers one historical dataset and six configurations over five seeds. The ULB narrative stress test covers one local 8B model, two prompts, and 51 flagged cases. The S0 semantic evaluation covers one synthetic stream, one seed, 25 alerts, one structured prompt, and a separate 190-item validator corpus. Neither evaluation estimates analyst usefulness.

For this reason, zero detected violations among delivered narratives is described as a result of the validate-or-fallback policy. It does not prove that the validator understands all valid language or catches every possible semantic error. The project did not conduct a human semantic audit, analyst usability study, fairness evaluation, drift study, compliance assessment, or load test.

## 9. Local startup and verification

Run the following commands from the repository root:

```bash
uv python pin 3.12 && uv sync
uv run python tools/check_data.py
cd app/frontend && npm ci && npm run build && cd ../..
uv run python tools/validate_dashboard.py --config configs/dashboard.yaml
uv run python -m app.backend.server --config configs/dashboard.yaml
```

The server binds to `127.0.0.1:8000`. If the production frontend build is missing, startup stops and prints the rebuild command. The dashboard validator checks the configured artefact chain without starting the server and reports the case count, selected narrative arm, source verification status, and run identifiers.

Optional live narrative generation requires Ollama in a separate terminal:

```bash
ollama serve
ollama pull llama3:8b
```

Run the verification suite with:

```bash
uv run pytest
cd app/frontend
npm run test
npm run lint
npm run e2e
```

The health endpoint at `GET /api/v1/health` reports evidence readiness, frontend build version, Ollama availability and model, and workflow-store status.

## 10. Terminology

| Term | Meaning in this application |
|---|---|
| Alert | A transaction scored above the frozen detector threshold and admitted to the review queue. |
| Evidence | Immutable detector, threshold, SHAP reason-code, and provenance records used to review an alert. |
| Case brief | The explanation delivered to the analyst, either a validated local LLM narrative or deterministic reason-code fallback. |
| Guardrail validation | The four deterministic checks that decide whether candidate text is delivered or replaced. |
| Routing action | The provisional next step recorded by the analyst: escalate, close without escalation, or request more information. |
| Human analyst | The user who reviews the evidence and remains responsible for the routing action. |

## 11. Main point for an examiner

The detector, explanation evidence, generated language, and human decision are separate parts of the system.

XGBoost identifies the alerts. SHAP records which anonymous features moved each model score. Ollama turns a minimised reason-code package into a standard case brief. Code-based guardrails decide whether the brief can be delivered. The analyst reviews the evidence and records the next action in a separate workflow database.

The failure behaviour is visible and repeatable. If Ollama is unavailable, the system uses deterministic reason codes. If generated text contradicts the evidence, the validator rejects it and uses the same fallback. If the evidence chain changes, an earlier workflow decision is marked incompatible instead of being silently reused.

The limitations remain part of the explanation. Anonymous features prevent business-level interpretation. SHAP attribution is not causation. Calibration results apply to a defined closed corpus rather than to all natural language. The application supports human review, but it does not replace the analyst or claim to make a final fraud decision.
