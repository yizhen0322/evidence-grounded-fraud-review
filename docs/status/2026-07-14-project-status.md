# FYP project status - updated 29 July 2026

## Current delivery state

The evidence pipeline, fail-closed local-LLM explanation layer, analyst application, report, logbook, and presentation package are implemented. The project is one explanation-assurance study supported by detector and application evidence.

Current product claim:

> Model evidence is converted into a local-LLM candidate explanation, checked deterministically, and either delivered or replaced by a safe evidence-only brief for analyst review.

It is intentionally not described as production-ready, bank-deployed, real-time fraud prevention, multi-user case management, or proven to improve analyst productivity.

The ULB benchmark supports the real-data detector evidence chain. The S0 synthetic stream is the primary readable semantic and operational evaluation for the explanation layer. They are not an ensemble and their detector metrics are not compared.

## Implemented system

### Technology

- React + TypeScript + Vite frontend.
- FastAPI backend bound to `127.0.0.1`.
- Local SQLite analyst workflow store at `var/dashboard/workflow.sqlite3`.
- Optional local Ollama live replay; recorded evidence remains usable when Ollama is unavailable.

### Analyst application areas

1. **Operations / Work Queue**
   - prioritized flagged cases;
   - risk, explanation-delivery, and workflow filters;
   - workflow counts;
   - start/restart/open review actions.
2. **Investigation Workspace**
   - recorded detector score and threshold;
   - SHAP contribution display and standardized reason codes;
   - recorded guardrail-validated narrative or deterministic fallback;
   - provisional assessment, analyst note, status, activity history, complete/reopen, and save/open-next workflow.
3. **Model Assurance / Narrative Assurance**
   - controlled direction-flip, invented-feature, and template-corruption tests against the real validator;
   - deterministic fallback display;
   - live replay is explicitly demo-only and never reported as G5 evidence.
4. **Model & Policy Monitor**
   - detector results separated from G4/G5 explanation evidence;
   - frozen figures, tables, and provenance.

### Integrity boundaries

- Detector, G4, G5, results tables, figures, and manifests are immutable evidence.
- SQLite stores only local workflow metadata: `case_id`, status, provisional disposition, note, revision, evidence fingerprint, and activity events.
- Workflow writes do not store or modify score, threshold, `y_true`, SHAP values, reason codes, narratives, raw rows, or reported metrics.
- Operational queue/case APIs exclude historical ground truth, retrospective outcome text, historical-label filtering, and the curated false-positive scenario.
- Old workflow records are masked when the configured evidence fingerprint changes and must restart with blank local fields.
- Completed decisions must be explicitly reopened before modification.

## Verification evidence

The current command-level results and document checks are recorded in `reports/thesis/submission/VERIFICATION_RECORD.md`. The rubric mapping is in `reports/RUBRIC_ALIGNMENT_MATRIX.md`.

## Research progress already complete

- Dataset validation, documented deduplication, and frozen 70/15/15 stratified splits.
- G0/G1/G2/G3/G6/G7 detector runs over seeds 42–46: 30 allowlisted runs.
- Leakage and provenance audits.
- Frozen detector decision and results aggregation.
- G4 SHAP reason codes and global importance.
- G5 strict/simple paired narrative experiment.
- Guardrail ON/OFF delivery analysis, Wilson intervals, calibration corpus, and deterministic fallback.
- Results tables, PR curve, SHAP figure, claim ledger, implementation review, dashboard specification, and product specification.

## Work still required before submission or presentation

1. Confirm the portal filename, required upload format, official submission date, and any Sunway declaration or originality forms.
2. Rehearse the presentation and application demonstration on the actual display setup, including the Ollama-unavailable fallback path.
3. Treat the current human evaluation as interim evidence. It contains 11 adult proxy reviewers, below the planned minimum of 18 and target of 30.
4. Do not describe the milestone logbook as ten calendar weeks. Repository evidence covers 13 to 29 July 2026.

### Known limitation to report, not silently hide

- The validator uses a deliberately closed accepted-language grammar. The independent review confirmed faithful out-of-corpus paraphrases that may be rejected. Current fail-closed behavior is safe, but the report must describe the grammar boundary honestly.
- Changing that validator now would require a new versioned calibration and a fresh final G5 run. It is not required for the current deliverable if documented as a limitation.

### Optional later work

- A second local LLM/model comparison.
- Additional responsive/mobile polish, richer SHAP interaction, export/PDF, or multi-case comparison.
- These are not required for the current CP2 submission and must not delay administrative checks or rehearsal.

## Where the paper and report materials are

### Existing original proposal/report documents

- Main editable document: `/Users/yizhen/Documents/sunway——yizhen/AAA_FYP/CP1/02_EDITABLE_SOURCE/FYP NG YI ZHEN.docx`
- Proposal PDF: `/Users/yizhen/Documents/sunway——yizhen/AAA_FYP/CP1/01_FINAL_SUBMISSION/Proposal_Capstone_Project.pdf`
- CP1 rubric: `/Users/yizhen/Documents/sunway——yizhen/AAA_FYP/CP1/02_EDITABLE_SOURCE/CP1 Rubrics.pdf`

### CP2 submission materials in the repository

- Final report: `reports/thesis/submission/CP2_Final_Report_Ng_Yi_Zhen.docx`
- Final report PDF: `reports/thesis/submission/CP2_Final_Report_Ng_Yi_Zhen.pdf`
- Logbook: `reports/logbook/CP2_Logbook_Ng_Yi_Zhen.docx`
- Presentation: `reports/presentation/CP2_Presentation_Ng_Yi_Zhen.pptx`
- Rubric matrix: `reports/RUBRIC_ALIGNMENT_MATRIX.md`
- Submission index: `reports/FINAL_SUBMISSION_INDEX.md`
- Report source: `reports/thesis/cp2_final_report.md`
- Results-to-claims ledger: `reports/thesis/results_mapping.md`
- Results summary table: `reports/tables/results_summary.csv`
- Seed-level results table: `reports/tables/results_main.csv`
- PR curve: `reports/figures/pr_curves.png`
- Implementation review: `docs/reviews/2026-07-14-implementation-review.md`
- Main implementation plan: `docs/plans/2026-07-13-cp2-implementation-plan.md`
- Workbench product spec: `docs/specs/2026-07-14-fraud-review-workbench-spec.md`

The complete CP2 report, editable support files, presentation deck, and verification records are present in `reports/`. The PDF copies are the stable visual references; the DOCX and PPTX copies remain editable.
