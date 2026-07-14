# Fraud Review Workbench Specification

Date: 2026-07-14  
Status: Approved for implementation  
Supersedes: presentation-first framing in the demo dashboard specification; all existing research-integrity and artifact contracts remain binding.

## 1. Product decision

The dashboard becomes **Fraud Review Workbench**, a local analyst decision-support prototype for reviewing model-flagged transactions.

The product must feel like a system an analyst can use to complete work, not a page that only presents a model. Its operational loop is:

1. find the next case in the work queue;
2. inspect detector, G4, and G5 evidence;
3. record a provisional assessment and note;
4. move the case through a review state;
5. continue to the next case;
6. use Model Assurance when provenance, guardrails, or evaluation evidence must be inspected.

This remains an honest FYP prototype. It is not described as production-ready, real-time, bank-deployed, multi-user, or proven to improve analyst productivity.

## 2. Two-plane architecture

### 2.1 Immutable evidence plane

The existing detector, G4, G5, results, figures, and manifests remain immutable and provenance-verified.

- Dashboard code never writes to experiment or report artifacts.
- Recorded detector scores, thresholds, SHAP values, reason codes, narratives, and metrics are never recomputed in the browser.
- Provenance validation remains fail-closed.
- Live Ollama output remains `demo-only`, `reported=false`, loopback-only, minimized, non-persistent, and guarded by the real validator.

### 2.2 Local workflow plane

A separate SQLite database stores analyst-created workflow metadata:

- `case_id`;
- workflow status;
- provisional disposition;
- analyst note;
- revision number;
- evidence-chain fingerprint;
- local activity events and timestamps.

The workflow database must not store detector score, threshold, `y_true`, reason codes, SHAP values, narrative text, raw transaction rows, or reported metrics.

The database lives outside all experiment/report directories at `var/dashboard/workflow.sqlite3` and is ignored by Git.

## 3. Claim boundary

Permitted:

> A locally deployable analyst decision-support prototype backed by immutable, provenance-verified research evidence.

> Analysts can record local provisional review decisions without modifying experiment artifacts.

> LLM narratives are deterministically validated or replaced by a reason-code fallback.

Not permitted:

- production-ready or bank-grade;
- real-time fraud prevention;
- automated fraud decision system;
- fraud prevented or money saved;
- GDPR, PCI-DSS, or audit compliance;
- proven analyst-efficiency improvement;
- multi-user case management.

## 4. Users

### Primary user

A fraud analyst reviewing model-flagged transactions in a single-user local workspace.

### Secondary users

- a model-risk reviewer inspecting assurance evidence;
- a supervisor or examiner evaluating the FYP contribution and system boundaries.

## 5. Information architecture

### Operations

- `/queue` — **Work Queue**
- `/cases/:caseId` — **Investigation Workspace**

### Model Assurance

- `/assurance/narratives` — **Narrative Assurance**
- `/assurance/performance` — **Model & Policy Monitor**

Compatibility redirects:

- `/guardrails` → `/assurance/narratives`
- `/results` → `/assurance/performance`

## 6. Work Queue

Purpose: select and resume review work.

The default page contains:

- compact counts for unreviewed, in review, needs follow-up, review complete, and recorded narrative fallback;
- `Start next review` action;
- search by case ID or top recorded feature;
- filters for risk bucket, workflow state, and recorded narrative state;
- a dense table with risk, case ID, model score, explanation delivery, top reason, workflow state, and action.

The operational queue does not display `y_true`, historical outcome, G0–G7 labels, or research scenario cards. Curated demo paths may remain available in a secondary disclosure for rehearsals.

## 7. Investigation Workspace

Purpose: complete one provisional analyst review.

### Evidence area

- stable case ID;
- recorded risk bucket, model score, threshold, and detector decision;
- top SHAP contributions and reason-code table;
- validated recorded narrative or deterministic fallback;
- recorded/live selector inside the narrative area only;
- data-minimization disclosure;
- provenance access.

`y_true`, retrospective outcome text, and historical-label filtering are excluded from operational queue and case APIs. Retrospective outcomes appear only as aggregate research evidence in Model Assurance and in internal validation code, never as an analyst case input.

### Decision rail

The right-side rail contains:

- workflow status;
- provisional disposition: suspicious, not suspicious, or inconclusive;
- analyst note with a 2,000-character limit;
- `Start review`, `Save review`, `Needs follow-up`, `Complete review`, and `Save & open next` actions;
- local activity history.

It must state:

> Local workspace only. Review decisions are not fraud ground truth and are not included in reported experiment results.

## 8. Workflow state machine

Statuses:

- `unreviewed`;
- `in_review`;
- `needs_follow_up`;
- `review_complete`.

Permitted transitions:

- unreviewed → in review;
- in review → needs follow-up or review complete;
- needs follow-up → in review or review complete;
- review complete → in review (reopen).

Disposition is separate from status:

- `suspicious`;
- `not_suspicious`;
- `inconclusive`;
- null.

Every write uses optimistic revision checking. A stale update returns HTTP 409 instead of silently overwriting another browser tab.

## 9. Narrative Assurance

The existing guardrail challenge moves under Model Assurance.

The page must show:

- source-code compatibility and fail-closed delivery policy;
- a controlled attack selector;
- faithful and mutated text;
- format, completeness, grounding, and direction results;
- deterministic fallback;
- explicit wording that this is assurance testing, not the analyst review flow or a reported G5 run.

## 10. Model & Policy Monitor

The existing Results page becomes recorded evaluation evidence, not live production monitoring.

It keeps detector performance separate from G4/G5 narrative evidence and continues to show Wilson intervals, prompt-arm comparisons, figures, and provenance.

## 11. Visual system

- Industrial/utilitarian desktop workbench.
- Dark navy navigation rail, light neutral workspace, white content surfaces.
- One blue action accent; red, amber, and green are semantic only.
- Small radii, 1px borders, minimal shadows, compact spacing.
- No marketing hero, gradient, KPI-card mosaic, circular risk gauge, fake alert stream, or decorative enterprise chrome.
- Operational pages prioritize table, evidence, and action rail.
- Risk and state always include text, never colour alone.

## 12. Security and data boundaries

- FastAPI and Ollama remain loopback-only.
- Workflow writes accept allowlisted fields only.
- `case_id` must exist in the validated snapshot before workflow metadata can be created.
- Notes are length-limited and rendered as text, never HTML.
- The workflow database stores no experiment evidence or historical labels.
- Recorded artifacts are hash/mtime checked before and after workflow E2E tests.

## 13. Explicit non-goals

- login, RBAC, teams, or assignment;
- cloud deployment;
- real-time stream processing;
- customer, merchant, device, or location profiles not present in the dataset;
- transaction blocking, refund, chargeback, email, or SMS actions;
- configurable model thresholds;
- batch decisions;
- fake SLA, monetary impact, or compliance metrics.

## 14. Definition of done

1. Work Queue is the default operational route and hides historical ground truth.
2. A user can start, save, complete, and continue a review.
3. Workflow status, disposition, note, revision, and activity survive refresh and server restart.
4. All workflow data is stored only in the separate SQLite database.
5. Recorded artifacts remain byte-for-byte unchanged after the full analyst journey.
6. Stale revisions return HTTP 409.
7. Invalid case IDs cannot create workflow records.
8. Recorded/live and Operations/Assurance boundaries remain explicit.
9. Ollama failure still produces deterministic fallback and does not block review work.
10. Old `/guardrails` and `/results` links remain compatible.
11. Unit, backend, E2E, lint, and production build checks pass.
12. The UI at 1440×900 supports a complete queue → evidence → decision → next-case demonstration.
