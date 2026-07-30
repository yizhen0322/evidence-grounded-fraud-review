# Single-form presentation and ordering plan

Status: draft for supervisor or ethics review

## 1. Design choice

Use one Google Form and one participant link for the full sample of approximately
30 adults. Every participant reviews the same nine synthetic alert cases.

Each participant sees:

- 3 raw reason-code cases;
- 3 deterministic brief cases;
- 3 guarded LLM brief cases.

Each source case appears once per participant. The form uses a fixed interleaved
order so the three explanation formats alternate instead of appearing in three
long condition blocks.

## 2. Fixed condition assignment

| Display order | Source slot | Explanation condition |
| --- | --- | --- |
| Case 01 | S01 | Raw reason codes |
| Case 02 | S04 | Deterministic brief |
| Case 03 | S07 | Guarded LLM brief |
| Case 04 | S02 | Raw reason codes |
| Case 05 | S05 | Deterministic brief |
| Case 06 | S08 | Guarded LLM brief |
| Case 07 | S03 | Raw reason codes |
| Case 08 | S06 | Deterministic brief |
| Case 09 | S09 | Guarded LLM brief |

This is a deliberately simple within-subjects FYP design. It does not claim to
eliminate case-specific or order effects. Those limitations must be disclosed in
the report rather than hidden.

## 3. Participant-facing data

Use neutral labels `Case 01` through `Case 09`. Do not expose internal case IDs,
transaction IDs, detector scores, SHAP magnitudes, fraud labels, or artifact
paths.

The admin manifest records the hashed source-case reference, assigned condition,
expected rank-one evidence, expected direction, and expected evidence count for
analysis and reproducibility.
