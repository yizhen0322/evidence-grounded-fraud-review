# Pre-specified analysis plan

Status: frozen before recruitment; interim descriptive analysis completed at n = 11  
Important: the pre-specified minimum remains 18 and the target remains 30. No inferential test was run at the interim analysis.

## 1. Analysis objective

Estimate how the three explanation formats differ in:

- evidence-comprehension accuracy;
- perceived clarity;
- confidence;
- perceived effort;
- overall preference.

The analysis is descriptive and exploratory. It does not claim real-world fraud
decision quality.

## 2. Data freeze

Before recruitment starts, freeze:

- final Google Form versions;
- final case slots;
- final condition assignment table;
- source artifact paths;
- inclusion and exclusion rules;
- primary outcomes;
- analysis script or spreadsheet formula version.

After recruitment ends, export raw responses once and preserve the original
export unchanged.

## 3. Exclusion rules

Exclude a response from analysis if:

- consent is not `Yes`;
- participant indicates they are under 18;
- fewer than 70% of task blocks are completed;
- the response is a known duplicate and a pre-specified duplicate rule applies;
- the response is from a pilot run and the form changed afterward.

Do not exclude responses because their answers disagree with the expected
evidence answer.

## 4. Derived fields

For each task row:

- `top_evidence_correct = top_evidence_answer == top_evidence_expected`
- `top_direction_correct = top_direction_answer == top_direction_expected`
- `evidence_count_correct = evidence_count_answer == evidence_count_expected`

Do not derive a primary `fraud_decision_correct` field. Routing is exploratory.

## 5. Primary summaries

For each condition:

- number of participants exposed;
- number of task responses;
- top-evidence accuracy with numerator, denominator, rate, and 95% Wilson CI;
- direction accuracy with numerator, denominator, rate, and 95% Wilson CI;
- evidence-count accuracy with numerator, denominator, rate, and 95% Wilson CI;
- median and interquartile range for clarity;
- median and interquartile range for confidence;
- median and interquartile range for perceived effort;
- median and interquartile range for enough-evidence rating.

If statistical testing is not required by the supervisor, stop at descriptive
statistics and confidence intervals.

## 6. Optional inferential tests

Only run inferential tests if the final sample size is sufficient and the method
is stated before seeing results.

Possible tests:

- Friedman test for within-subject Likert ratings.
- Cochran's Q test for within-subject binary accuracy.
- Mixed-effects logistic regression for accuracy with participant and case as
  random effects, if tooling and sample size permit.

For a small undergraduate study, report these as exploratory. Do not overstate
p-values.

## 7. Free-text analysis

Code optional comments into small categories:

- unclear terminology;
- too terse;
- too verbose;
- missing context;
- easy to scan;
- trust concern;
- no issue;
- other.

Use human coding. If a second human coder is available, code a 20% subsample and
report agreement descriptively.

Do not use an AI tool to code participant free text unless the approved ethics
materials explicitly allow it and participants consented to that use.

## 8. Reporting template

Use this shape:

```text
We conducted a small synthetic-alert evaluation with [N] adult participants and
[task response count] completed case reviews. Participants were proxy reviewers,
not professional fraud analysts. The study compared raw reason codes,
deterministic briefs, and guarded LLM briefs generated from the same S0 model
evidence.
```

Then report each outcome with its denominator. For example:

```text
Top-evidence accuracy was [x/n] for raw reason codes, [x/n] for deterministic
briefs, and [x/n] for guarded LLM briefs.
```

Do not write results until the human study has actually been run.

## 9. Limitations to report

Always include:

- synthetic data;
- small sample;
- proxy reviewers rather than real fraud analysts unless otherwise true;
- short task duration;
- single project interface and evidence format;
- no real banking deployment;
- no measurement of fraud-loss reduction;
- no proof of production safety or compliance.
