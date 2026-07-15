# FYP project status — 2026-07-14

## Current delivery state

The research pipeline and local product prototype are implemented and verified. The delivered system is now a **Fraud Review Workbench**, not only a model-results dashboard.

Current product claim:

> A locally deployable analyst decision-support prototype backed by immutable, provenance-verified research evidence.

It is intentionally not described as production-ready, bank-deployed, real-time fraud prevention, multi-user case management, or proven to improve analyst productivity.

## What the system is now

### Technology

- React + TypeScript + Vite frontend.
- FastAPI backend bound to `127.0.0.1`.
- Local SQLite analyst workflow store at `var/dashboard/workflow.sqlite3`.
- Optional local Ollama live replay; recorded evidence remains usable when Ollama is unavailable.

### Product areas

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

- Full Python suite: **179 passed**.
- Frontend component suite: **4 passed**.
- Playwright browser suite: **10 passed**.
- ESLint: zero warnings.
- TypeScript + Vite production build: passed.
- Exact dashboard validator: valid, 51 cases, verified G6 seed-42 → G4 → G5 → Task 7.1 source chain.
- Workflow no-write regression hashes and checks mtimes for **21 configured research artifacts**.
- Implementation commits:
  - `4ca8408` — local analyst workflow store;
  - `210bfb4` — analyst Fraud Review Workbench;
  - `d20b33a` — blind operational workflow and final ground-truth boundary repair.

## Research progress already complete

- Dataset validation, documented deduplication, and frozen 70/15/15 stratified splits.
- G0/G1/G2/G3/G6/G7 detector runs over seeds 42–46: 30 allowlisted runs.
- Leakage and provenance audits.
- Frozen detector decision and results aggregation.
- G4 SHAP reason codes and global importance.
- G5 strict/simple paired narrative experiment.
- Guardrail ON/OFF delivery analysis, Wilson intervals, calibration corpus, and deterministic fallback.
- Results tables, PR curve, SHAP figure, claim ledger, implementation review, dashboard specification, and product specification.

## Work still required

### Required human/research work

1. **Complete the human narrative audit.**
   - File: `experiments/audit/2026-07-14_g5_seed42_strict_audit_sample.csv`
   - 49 accepted strict narratives are waiting for human-only labels.
   - After attestation, run `tools/score_audit.py` and add the resulting rate to the report.
2. **Finish citation and novelty verification.**
   - Build/check the final literature comparison matrix.
   - Verify every cited claim and DOI/source.
   - Keep novelty wording qualified as “within the reviewed literature”; never use a bare “first”.
3. **Write the complete CP2/FYP report.**
   - A structured skeleton and evidence ledger exist, but the final report prose is not yet written.
   - Add Methods as implemented, Results, Discussion, Limitations, societal value, product architecture, screenshots, references, and appendices.
4. **Presentation preparation.**
   - Test at the actual projector resolution.
   - Capture final report/demo screenshots.
   - Complete at least three timed end-to-end rehearsals, including Ollama unavailable fallback.

### Known limitation to report, not silently hide

- The validator uses a deliberately closed accepted-language grammar. The independent review confirmed faithful out-of-corpus paraphrases that may be rejected. Current fail-closed behavior is safe, but the report must describe the grammar boundary honestly.
- Changing that validator now would require a new versioned calibration and a fresh final G5 run. It is not required for the current deliverable if documented as a limitation.

### Optional stretch work

- A second local LLM/model comparison.
- Additional responsive/mobile polish, richer SHAP interaction, export/PDF, or multi-case comparison.
- These are not required for the current FYP product and must not delay the report, human audit, or rehearsal.

## Where the paper and report materials are

### Existing original proposal/report documents

- Main editable document: `/Users/yizhen/Documents/sunway——yizhen/AAA_FYP/FYP NG YI ZHEN.docx`
- Proposal PDF: `/Users/yizhen/Documents/sunway——yizhen/AAA_FYP/Proposal_Capstone_Project.pdf`
- CP1 rubric: `/Users/yizhen/Documents/sunway——yizhen/AAA_FYP/CP1 Rubrics.pdf`

### CP2 writing materials in the repository

- Report skeleton: `reports/thesis/cp2_report_skeleton.md`
- Results-to-claims ledger: `reports/thesis/results_mapping.md`
- Results summary table: `reports/tables/results_summary.csv`
- Seed-level results table: `reports/tables/results_main.csv`
- PR curve: `reports/figures/pr_curves.png`
- Implementation review: `docs/reviews/2026-07-14-implementation-review.md`
- Main implementation plan: `docs/plans/2026-07-13-cp2-implementation-plan.md`
- Workbench product spec: `docs/specs/2026-07-14-fraud-review-workbench-spec.md`

There is currently **no complete final CP2 paper file**. The next writing task should use the existing Word document as the editable base and the CP2 skeleton/results mapping as the evidence-controlled chapter guide.
