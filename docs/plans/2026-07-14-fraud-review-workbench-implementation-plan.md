# Fraud Review Workbench Implementation Plan

Date: 2026-07-14  
Source of truth: `docs/specs/2026-07-14-fraud-review-workbench-spec.md`

## Phase 1 — Workflow boundary

### Task 1.1 — Configuration and storage

- Add a strict `workflow.database_path` dashboard setting.
- Resolve the path inside the repository and outside experiment/report directories.
- Add `var/dashboard/` to `.gitignore`.
- Implement SQLite schema initialization with standard-library `sqlite3`.
- Store only workflow metadata and an evidence-chain fingerprint.

### Task 1.2 — Workflow API

- Add strict request/response types.
- Add list, detail, activity, summary, and revision-checked update routes.
- Validate every workflow `case_id` against the immutable snapshot.
- Return 409 for stale revisions and 422 for invalid transitions.

### Task 1.3 — Backend tests

- Persistence across store reconstruction.
- Invalid case rejection.
- Transition validation.
- Revision conflict.
- Note length and escaping boundary.
- Schema inspection proving forbidden evidence fields are absent.
- Artifact hash/mtime unchanged after writes.

## Phase 2 — Product shell and design system

### Task 2.1 — Application shell

- Replace the presentation-first top navigation with an Operations/Model Assurance side rail.
- Rename the product to Fraud Review Workbench.
- Keep local-prototype, artifact-integrity, and Ollama state visible but secondary.
- Move recorded/live selection into the Investigation narrative panel.

### Task 2.2 — Visual tokens

- Implement the industrial/utilitarian tokens in `DESIGN.md`.
- Remove Inter and decorative card treatment.
- Use compact desktop density, small radii, restrained motion, and semantic colour.

## Phase 3 — Analyst workflow

### Task 3.1 — Work Queue

- Join immutable case evidence with workflow state.
- Add operational counts and filters.
- Remove ground truth from the default queue.
- Add Start next review and resume actions.

### Task 3.2 — Investigation Workspace

- Add fixed decision rail with status, disposition, notes, and activity.
- Add Start, Save, Follow-up, Complete, Reopen, and Save & next actions.
- Keep evidence and narrative read-only.
- Exclude `y_true`, retrospective outcome text, and historical-label filtering from operational APIs and screens; retain only aggregate evaluation in Model Assurance.

## Phase 4 — Model Assurance

### Task 4.1 — Narrative Assurance

- Move the existing Guardrail Lab under `/assurance/narratives`.
- Reframe it as controlled policy assurance rather than a daily analyst screen.
- Keep `/guardrails` as a redirect.

### Task 4.2 — Model & Policy Monitor

- Move Results under `/assurance/performance`.
- Reframe metrics as recorded evaluation evidence.
- Keep `/results` as a redirect.

## Phase 5 — Verification and evidence

### Task 5.1 — Frontend tests

- Update API/component tests for absent operational ground truth and workflow actions.
- Add E2E analyst journey, refresh persistence, old-link redirects, and recorded/live separation.

### Task 5.2 — Full verification

- Backend unit/contract tests.
- Frontend unit tests.
- ESLint and production build.
- Playwright E2E.
- Exact dashboard validator.
- Full Python test suite.
- Artifact hash/mtime audit.

### Task 5.3 — Documentation

- Update implementation review and claim ledger.
- State that research artifacts are read-only while workflow metadata is stored separately.
- Record remaining human audit, literature verification, and rehearsal work.

## Stop condition

Stop implementation only when the user can complete this continuous path in the production build:

> Queue → start review → inspect immutable evidence → record disposition/note → complete → open next → inspect assurance → prove artifacts unchanged.
