# Human evaluation study package

Status: project owner reports supervisor approval; interim recruitment and analysis in progress  
Project: Evidence-Grounded Credit Card Fraud Detection and Review with Local LLM Explanations and Deterministic Guardrails  
Student: Ng Yi Zhen (23076003), Sunway University

## Approval and current status

The participant-facing form was released after supervisor approval was reported
by the project owner. The repository does not contain a formal Sunway ethics
approval record and does not claim one. If the supervisor or school requires an
additional institutional route, further recruitment must pause until that
requirement is satisfied.

The package supports a small, low-risk, synthetic-alert human evaluation. The
current interim analysis includes 11 adult proxy reviewers and 99 completed case
reviews. Aggregate results are stored under `reports/`; the anonymous raw-response
snapshot is stored under ignored `data/private/` and is not part of the public
repository evidence package.

## Study purpose

The study compares three ways of presenting the same model evidence from the S0
synthetic operational case study:

1. Raw SHAP reason codes.
2. Deterministic renderer.
3. Guarded local-LLM brief.

The study measures evidence comprehension and perceived usability in a simulated
alert-review task. It does not measure real fraud-investigation performance,
bank deployment readiness, regulatory compliance, or analyst productivity.

## Source artifacts

Use the sealed S0 artifact structure:

- `experiments/runs/2026-07-26_s0_seed42/semantic_cases.jsonl`
- `experiments/runs/2026-07-26_s0_seed42/explanation_comparison.jsonl`
- `experiments/runs/2026-07-26_s0_seed42/explanation_summary.json`
- `corpus/semantic_guardrail_corpus_v1.jsonl`
- `reports/tables/semantic_explanation_assurance.csv`
- `reports/tables/semantic_brief_comparison.csv`

Verified before drafting:

- `semantic_cases.jsonl`: 25 rows.
- `explanation_comparison.jsonl`: 25 rows.
- `semantic_guardrail_corpus_v1.jsonl`: 190 rows.
- `semantic_explanation_assurance.csv`: 23 accepted guarded LLM briefs, 2
  deterministic fallbacks, 0 transport failures, 150/150 calibration attacks
  intercepted, 40/40 faithful controls accepted.

## Participant-facing ID rule

Participant-facing materials must not expose internal `case_id`, transaction ID,
customer ID, terminal ID, detector score, SHAP value, raw row, fraud label, or
artifact path. Use neutral labels such as `Case 01`.

Admin-only files may keep a hashed source-case reference for reproducibility.
If a raw internal case ID is ever needed for reconstruction, keep it outside the
Google Form and outside screenshots shown to participants.

## Files in this package

- `2026-07-26-human-eval-protocol.md` - full study protocol.
- `2026-07-26-human-eval-consent.md` - participant information and consent text.
- `2026-07-26-human-eval-google-form-blueprint.md` - Google Form sections and
  questions.
- `2026-07-26-human-eval-randomization-plan.md` - fixed case assignment and
  presentation order.
- `2026-07-26-human-eval-analysis-plan.md` - pre-specified analysis plan.
- `2026-07-26-human-eval-data-dictionary.csv` - response and derived-field
  dictionary.
- `2026-07-26-human-eval-supervisor-ethics-gate.md` - supervisor and ethics
  checklist.
- `2026-07-26-human-eval-wording-boundaries.md` - allowed and prohibited wording.

## Closed draft generator

The repository includes a deterministic form generator. Running the generator
does not itself recruit participants or enable response collection.

```bash
uv run python tools/build_human_eval_stimuli.py
```

The command creates one participant-facing form payload, an admin-only stimulus
manifest, and
`docs/studies/google_forms/create_human_eval_forms.gs`. Paste that file into a
Google Apps Script project and run `createHumanEvaluationDraft()`. It creates
one Google Form and one linked response spreadsheet. All participants receive
the same direct Google Form link and review the same nine cases. Email collection
is disabled. The released form was opened after the project owner supplied the
explicit `openStudyAfterApproval('SUPERVISOR_APPROVED')` confirmation token.
