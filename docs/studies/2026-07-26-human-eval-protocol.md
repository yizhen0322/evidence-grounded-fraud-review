# Human evaluation protocol

Status: project owner reports supervisor approval for the minimal-risk pilot  
Recruitment status: interim, 11 included responses analysed  
Approval boundary: supervisor approval reported by the project owner; no formal institutional ethics record is present in the repository

## 1. Study title

Human evaluation of explanation formats for synthetic fraud-alert review.

## 2. Research question

In a synthetic fraud-alert review task, how do raw SHAP reason codes,
deterministic briefs, and guarded local-LLM briefs affect evidence comprehension,
perceived clarity, confidence, and perceived effort?

## 3. Conservative scope

This is a small undergraduate FYP study. It uses synthetic transaction alerts
from the S0 operational case study. Participants review explanation displays and
answer comprehension and perception questions.

The study does not evaluate real fraud analysts, real bank customers, live
payments, production deployment, regulatory compliance, or actual fraud loss
reduction.

## 4. Design

Use a within-subjects design. Each participant sees all three explanation
conditions, but each source case appears only once for that participant.

Conditions:

| Condition | Participant sees | Source field |
| --- | --- | --- |
| Raw reason codes | Ranked evidence labels, direction, and value bucket | `semantic_cases.jsonl.reason_codes` or `explanation_comparison.jsonl.minimized_llm_payload.evidence` |
| Deterministic brief | Fixed template generated from the same ranked evidence | `explanation_comparison.jsonl.deterministic_brief` |
| Guarded LLM brief | Validator-accepted guarded LLM summary | `explanation_comparison.jsonl.guarded_llm_brief` where `fallback=false` |

Main comparison cases should use rows where `fallback=false` so the guarded LLM
condition is not silently identical to the deterministic fallback. The two
fallback rows may be used only in a separate optional demonstration or excluded
from the main participant task set.

## 5. Participants

Target sample:

- Target: 30 completed adult participants.
- All participants complete the same single Google Form.
- Acceptable undergraduate minimum if recruitment is interrupted: 18 completed
  participants, with the imbalance disclosed.
- Pilot: 2 adults, excluded from final analysis unless the form is unchanged.

Participant type:

- Sunway students, staff, or invited adult volunteers.
- Non-expert proxy reviewers are acceptable.
- Do not describe participants as professional fraud analysts unless they have
  relevant professional experience.

## 6. Inclusion criteria

Participants may join if they:

- are at least 18 years old;
- can read English;
- can complete a browser-based form;
- voluntarily consent;
- have not already completed the study.

## 7. Exclusion criteria

Exclude participants who:

- are under 18;
- do not consent;
- previously completed the same study;
- report serious discomfort with fraud or crime-related scenarios;
- are directly involved in building this project or preparing the study stimuli;
- submit less than 70% of task responses.

The supervisor, examiner, or anyone in a grading relationship should not be
recruited unless the supervisor explicitly confirms there is no coercion or
conflict concern.

## 8. Task procedure

1. Participant reads the information sheet and consent statement.
2. Participant confirms age 18 or older and voluntary consent.
3. Participant answers non-identifying background questions.
4. Participant completes one practice case.
5. Participant reviews 9 synthetic alert cases:
   - 3 raw reason-code cases;
   - 3 deterministic brief cases;
   - 3 guarded LLM brief cases.
6. For each case, participant answers evidence-comprehension, routing, and
   perception questions.
7. Participant completes an overall format-preference section.
8. Participant reads a short debrief.

Expected completion time: 10-15 minutes.

## 9. Stimulus rules

Participant-facing stimuli may include:

- neutral case label such as `Case 01`;
- relative review priority bucket;
- rounded or bucketed transaction context if approved by supervisor;
- evidence display label;
- evidence direction as `raises risk` or `reduces risk`;
- evidence rank;
- coarse value bucket;
- explanation text for the assigned condition.

Participant-facing stimuli must not include:

- internal `case_id`;
- transaction ID;
- customer ID;
- terminal ID;
- raw row values beyond approved context;
- detector score or threshold;
- SHAP magnitude;
- fraud label or retrospective outcome;
- artifact path;
- LLM candidate text that failed validation.

## 10. Outcomes

Primary objective outcomes:

- top-evidence accuracy;
- direction accuracy;
- evidence-count accuracy.

Primary subjective outcomes:

- clarity rating;
- confidence rating;
- perceived effort rating;
- enough-evidence rating.

Secondary exploratory outcomes:

- routing action distribution by condition;
- optional timing if available from a form platform or separate timing method;
- overall format preference;
- free-text comments about unclear points.

Do not treat routing action as real fraud-decision quality. If synthetic labels
are used for an exploratory alignment check, report that limitation explicitly.

## 11. Data handling

Do not collect names, student IDs, email addresses, phone numbers, IP addresses,
or class marks. Google Form settings should disable email collection.

Store exports under an approved, access-controlled location. Raw exports should
remain unchanged. Cleaned analysis files should be separate from raw exports.

## 12. Ethical risk level

Expected risk is minimal because:

- the cases are synthetic;
- the task is a short browser form;
- the study does not evaluate personal ability or academic performance;
- no identifying data are requested;
- participation is voluntary.

The study still involves human participants and must pass the supervisor or
ethics gate before recruitment.

## 13. Evidence base used for this protocol

Repository evidence:

- `docs/specs/2026-07-26-semantic-fraud-triage-extension.md`
- `docs/guides/2026-07-24-fraud-alert-review-application-guide.md`
- `reports/thesis/results_mapping.md`
- `src/semantic/explanations.py`
- `experiments/runs/2026-07-26_s0_seed42/explanation_summary.json`
- `reports/tables/semantic_explanation_assurance.csv`

Sunway ethics references:

- https://sunwayuniversity.edu.my/research/institutional-review-board
- https://sunwayuniversity.edu.my/research/human-ethics-and-clinical-research
