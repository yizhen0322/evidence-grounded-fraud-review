# Wording boundaries

Status: mandatory for study materials and report writing

## 1. Allowed wording

Use:

- `synthetic fraud-alert cases`
- `synthetic operational case study`
- `adult participants`
- `proxy reviewers`
- `simulated alert-review task`
- `evidence comprehension`
- `perceived clarity`
- `self-reported confidence`
- `perceived effort`
- `provisional routing action`
- `guarded local-LLM brief`
- `deterministic renderer`
- `raw SHAP reason codes`
- `same ranked model evidence`
- `small undergraduate FYP study`

## 2. Conditional wording

Use only if the condition is true:

- `fraud analysts` - only if participants are professional fraud analysts.
- `faster` - only if task timing is measured and analyzed.
- `preferred` - only for observed participant preference data.
- `clearer` - only for measured clarity ratings or free-text evidence.
- `higher comprehension` - only for measured comprehension accuracy.

## 3. Prohibited wording

Do not write:

- `proved analyst productivity`
- `improved fraud detection`
- `better fraud decisions`
- `reduced fraud losses`
- `bank-ready`
- `production-ready`
- `deployed in banking`
- `privacy-preserving`
- `regulatory compliant`
- `hallucination-free`
- `guardrails eliminate errors`
- `LLM understands fraud`
- `participants validated the model`
- `real customer behavior`

## 4. SHAP wording

Correct:

- `SHAP reason codes describe model attribution.`
- `A positive contribution pushed the model score toward the fraud class.`
- `The evidence is not causal.`

Incorrect:

- `SHAP proves why fraud occurred.`
- `The feature caused fraud.`
- `The model discovered the true fraud reason.`

## 5. LLM wording

Correct:

- `The LLM is a constrained translation layer.`
- `The guarded LLM brief is validated against the supplied evidence.`
- `If validation fails, the system falls back to deterministic text.`

Incorrect:

- `The LLM decides whether the transaction is fraud.`
- `The LLM adds new evidence.`
- `The LLM output is always faithful.`

## 6. Human-study wording

Before data collection:

```text
This package proposes a human evaluation. No participants have been recruited
and no human-study results are available yet.
```

After data collection, if completed:

```text
A small synthetic-alert evaluation was conducted with [N] adult participants.
Participants reviewed explanation formats generated from the same S0 model
evidence. The study measured evidence comprehension and perceived clarity in a
simulated task.
```

Limitation sentence:

```text
The study used synthetic cases and proxy reviewers, so it does not establish
real-world fraud-investigation performance, analyst productivity, or banking
deployment readiness.
```

