# Google Form blueprint

Status: draft for supervisor or ethics review  
Do not publish or accept responses before approval

## Form settings

- Do not collect email addresses.
- Do not require sign-in unless the supervisor confirms it is acceptable.
- Disable response editing after submission unless the approved ethics plan says
  otherwise.
- Do not ask for name, student ID, email, phone number, class section, or any
  direct identifier.
- Use one form and one participant link for the full sample.
- Every participant sees the same nine cases in the fixed interleaved order
  documented in `2026-07-26-human-eval-randomization-plan.md`.

## Section 1: Information and consent

Add the consent text from `2026-07-26-human-eval-consent.md`.

Required question:

1. I confirm that I am at least 18 years old, have read the information above,
   and voluntarily agree to participate.
   - Yes, I agree.
   - No, I do not agree.

Branch `No` to the end of the form.

## Section 2: Background

2. Which area best describes your current study or work background?
   - Computing / IT
   - Business / finance / accounting
   - Other science, technology, engineering, or mathematics
   - Other non-STEM
   - Prefer not to say

3. How familiar are you with machine learning?
   - None
   - Basic
   - Intermediate
   - Advanced

4. How familiar are you with fraud detection?
   - None
   - Basic
   - Intermediate
   - Advanced

5. Have you used SHAP or feature-attribution explanations before?
   - Yes
   - No
   - Not sure

## Section 3: Instructions

Display this text:

You will review synthetic fraud-alert cases. For each case, answer based only on
the information shown. There is no expected professional fraud decision. Choose
the option that best matches your understanding of the case explanation.

Do not show internal IDs, detector scores, SHAP values, artifact paths, or fraud
labels in this section.

## Section 4: Practice case

Use a practice case that is not included in the final analysis.

Practice display:

- Case label: `Practice Case`
- Relative review priority: `Medium`
- Explanation: one short example using generic evidence labels.

Practice questions:

1. Which evidence item was ranked first?
   - Option A
   - Option B
   - Option C
   - Not clear

2. Did the first-ranked evidence raise or reduce risk?
   - Raised risk
   - Reduced risk
   - Not clear

3. How clear was the explanation?
   - 1 Very unclear
   - 2
   - 3
   - 4
   - 5 Very clear

## Section 5: Alert tasks

Repeat the following task block 9 times. Label blocks `Case 01` through
`Case 09`. Do not display internal `case_id` or transaction ID.

### Case display template

Participant-facing context:

- Case label: `Case NN`
- Relative review priority: `Low`, `Medium`, or `High`
- Synthetic transaction context: approved non-identifying summary only
- Explanation format: one of raw reason codes, deterministic brief, or guarded
  LLM brief

Raw reason-code display:

```text
Ranked evidence:
1. [Evidence label] - raises/reduces risk - value bucket: [bucket]
2. [Evidence label] - raises/reduces risk - value bucket: [bucket]
3. [Evidence label] - raises/reduces risk - value bucket: [bucket]
```

Deterministic brief display:

```text
[Use deterministic_brief from explanation_comparison.jsonl after removing any
internal identifiers.]
```

Guarded LLM brief display:

```text
[Use guarded_llm_brief from explanation_comparison.jsonl for fallback=false
rows only in the main comparison.]
```

### Case questions

For each case:

1. Which evidence item was ranked first?
   - [Evidence label A]
   - [Evidence label B]
   - [Evidence label C]
   - Not clear

2. Did the first-ranked evidence raise or reduce risk?
   - Raised risk
   - Reduced risk
   - Not clear

3. How many distinct evidence items were explicitly named in the explanation?
   - 1
   - 2
   - 3
   - Not clear

4. What provisional routing action would you choose?
   - Escalate for investigation
   - Close without escalation
   - Request more information

5. How confident are you in that routing action?
   - 1 Very low
   - 2
   - 3
   - 4
   - 5 Very high

6. The explanation was easy to understand.
   - 1 Strongly disagree
   - 2
   - 3
   - 4
   - 5 Strongly agree

7. The explanation gave enough evidence for a provisional routing action.
   - 1 Strongly disagree
   - 2
   - 3
   - 4
   - 5 Strongly agree

8. The explanation felt mentally effortful to use.
   - 1 Strongly disagree
   - 2
   - 3
   - 4
   - 5 Strongly agree

9. Optional: What, if anything, was unclear?
   - Short answer

## Section 6: Overall comparison

1. Which explanation format was clearest overall?
   - Raw reason codes
   - Deterministic brief
   - Guarded LLM brief
   - No preference

2. Which explanation format would you prefer for a first-pass synthetic alert
   review?
   - Raw reason codes
   - Deterministic brief
   - Guarded LLM brief
   - No preference

3. Which explanation format felt most trustworthy?
   - Raw reason codes
   - Deterministic brief
   - Guarded LLM brief
   - No preference

4. Briefly explain your preference.
   - Paragraph

## Section 7: Debrief

Display the debrief text from `2026-07-26-human-eval-consent.md`.
