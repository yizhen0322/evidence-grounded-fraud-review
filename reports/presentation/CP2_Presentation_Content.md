# CP2 presentation content

Project: **Evidence-Grounded Local-LLM Explanations for Credit Card Fraud Alert Review**  
Student: **Ng Yi Zhen (23076003)**  
Use: Final 12-slide CP2 viva deck. The presentation follows one argument: generated fraud-alert text remains untrusted until deterministic checks confirm that it matches the stored model evidence.

**Delivery constraint:** 15 minutes total, including the system demonstration. Use the timed runbook in `CP2_15_Minute_Viva_Runbook.md`: approximately 10 minutes 20 seconds for slides, 3 minutes 20 seconds for the live demonstration, and 1 minute 20 seconds for transitions and contingency. Stop expanding answers during the presentation; preserve detail for examiner questions.

## Slide 1. Fraud alert explanations that fail closed

- Evidence-grounded local-LLM delivery for credit-card alert review.
- The detector classifies; the LLM only restates approved evidence.
- A failed check returns the deterministic brief instead of generated prose.

**Existing visual recommendation:** Use a strong title panel and a cropped analyst-workbench screenshot. The slide should establish the product context without presenting the website as the research contribution.

**Speaker script:**  
Good morning. This project examines how a local language model can be used in fraud-alert review without allowing generated text to replace model evidence. The detector produces the fraud score. SHAP produces signed reason codes. The language model may turn those reason codes into a shorter brief, but it does not classify the transaction and it does not receive permission to add new fraud evidence. Before any generated brief reaches the analyst, a deterministic validator checks its format, evidence coverage, grounding, and direction. If any check fails, the system returns the deterministic evidence brief. The contribution is therefore a measured, fail-closed delivery boundary around optional local-LLM text.

## Slide 2. Readable does not mean faithful

- Fraud is a rare event, so detector accuracy alone is misleading.
- SHAP is evidence-grounded, but its output is technical and repetitive.
- LLM prose is readable, but it can omit, invent, or reverse evidence.
- The research problem is safe delivery, not unrestricted text generation.

**Existing visual recommendation:** Use a three-stage risk chain with one large statement: "Readable does not mean faithful."

**Speaker script:**  
The project starts with two separate risks. The first is detection. Fraud is rare, so a model can appear accurate while missing important fraudulent transactions. This is why I evaluate average precision, precision, recall, F1, and confusion counts rather than relying on accuracy. The second risk begins after detection. SHAP gives a traceable attribution, but raw feature names and contribution directions are not a complete analyst explanation. A language model can make the text easier to read, but readability does not guarantee faithfulness. It may drop a reason, introduce an unsupported feature, or reverse a direction. My research focuses on controlling that second risk.

## Slide 3. Research gap and questions

- Prior work covers SHAP alignment, narrative explanation, or programmable guardrails separately.
- Within the reviewed literature, the combined delivery contract remains under-evaluated.
- **RQ1:** How effectively do deterministic checks detect violations and enforce fallback?
- **RQ2:** What does guarded local-LLM delivery add, preserve, or lose?

**Existing visual recommendation:** Use a prior-work capability matrix above two large research-question cards. The matrix should compare deterministic validation, fail-closed fallback, local execution, and separate raw-versus-delivered measurement.

**Speaker script:**  
The reviewed literature contains the individual pieces of this problem. Some studies examine whether language-model explanations agree with SHAP. Others study narrative explanation, and programmable guardrail work shows how generated outputs can be checked. The gap I identified is the evaluated combination of four controls in a fraud-review setting: local execution, deterministic validation, fail-closed fallback, and separate measurement of raw output and delivered output. I therefore ask two questions. First, how effectively do the checks detect contract violations and activate fallback? Second, when the output passes those checks, what does the language model add, preserve, or lose compared with reason codes and deterministic briefs?

## Slide 4. Two evidence roles, one delivery boundary

- **ULB:** real anonymised benchmark for detector and SHAP evidence.
- **S0:** synthetic readable stream for semantic and operational evaluation.
- Their detector scores are not compared because the datasets serve different roles.
- Both test the same rule: generated text cannot become new evidence.

**Existing visual recommendation:** Use two asymmetric evidence panels connected to one shared delivery boundary. Label every result as ULB or S0.

**Speaker script:**  
I use two evidence contexts, but they are not two competing projects. The European ULB dataset is the real anonymised benchmark. It supports the detector comparison, leakage checks, and SHAP evidence chain. Its V1 to V28 features are anonymous, which makes them unsuitable for a realistic business explanation. S0 is a synthetic transaction stream with readable fields such as amount relative to recent behaviour, terminal distance, and night-time status. It supports semantic evaluation, the analyst workflow, and the human pilot. I do not compare ULB and S0 detector scores because their data-generating processes and feature spaces differ. Both are used to test the same delivery boundary.

## Slide 5. Method: freeze evidence before generation

- Split before scaling, SMOTE, autoencoder fitting, threshold selection, or SHAP.
- Train six detector groups across five fixed seeds.
- Freeze the selected detector and persist case-linked SHAP reason codes.
- Send only a minimised evidence package to the local LLM.
- Validate the raw candidate or deliver deterministic fallback.

**Existing visual recommendation:** Use a locked pipeline. Separate immutable research artifacts from analyst workflow state.

**Speaker script:**  
The methodology protects the evidence chain before the language model is introduced. I deduplicate the source data, create stable case identifiers, and split the data before fitting scalers, SMOTE, autoencoders, thresholds, or SHAP. Six detector groups are evaluated over five fixed seeds. After selection, the downstream detector is frozen. Predictions, metrics, reason codes, and manifests are stored as linked artifacts. The local model receives a minimised package rather than the raw transaction row. Its candidate is retained so the experiment can measure what the model actually produced. The validator then either accepts that unchanged candidate or returns a deterministic fallback generated from the stored reason codes.

## Slide 6. Supporting benchmark: no detector dominates

- G6 had the highest mean test AP and precision.
- G2 had the highest mean F1; G7 had the highest recall.
- Autoencoder features did not show a clear general advantage.
- G6 was selected as a stable evidence source, not as an algorithmic breakthrough.

**Existing visual recommendation:** Make the metric bars the hero visual. Add small callouts for AP, F1, recall, and the operational precision-recall trade-off.

**Speaker script:**  
The detector benchmark produced a mixed result. G6, the cost-sensitive XGBoost group, had the highest mean test average precision at 0.8552 and the highest precision. G2 had the highest mean F1 at 0.8701, while G7 had the highest recall at 0.8169. No group led every metric, and the autoencoder groups did not show a clear general advantage over the original-feature baseline. G6 was selected for the downstream explanation chain because it provided a reproducible evidence source with strong precision and fewer false positives. This is an operational trade-off that can reduce analyst workload, not evidence of a new detector algorithm.

## Slide 7. Core innovation: measure raw output, gate delivery

- **OFF policy:** retain and measure the raw LLM candidate.
- **ON policy:** validate the same candidate before delivery.
- A failed candidate is rejected; it is not repaired or normalised.
- Fallback is rebuilt from the original reason codes.

**Existing visual recommendation:** Use a split flow comparing raw-output measurement with delivered-output policy. Include a small rejected-candidate example and the line "A normaliser can hide a failure; fallback preserves the evidence."

**Speaker script:**  
This is the central design decision. Under the OFF policy, I retain the raw language-model output and measure its violations. Under the ON policy, the exact same candidate goes through deterministic checks before delivery. The system does not use a normaliser to rewrite a bad answer into a valid-looking one. That would hide the original failure and make the model appear more reliable than it was. Instead, the candidate is either accepted unchanged or rejected. When rejection occurs, the delivered brief is rebuilt from the original reason codes. This keeps generation quality and delivery safety as two separate measurements.

## Slide 8. Guardrails changed what reached the analyst

- Strict prompt: **2/51** raw ULB outputs had a detected violation.
- Simple prompt: **51/51** raw ULB outputs had a detected violation.
- Calibration: **330/330** attacks intercepted and **318/318** faithful controls accepted.
- Manual audit: **0/49** delivered strict narratives were judged semantically inconsistent, 95% CI **0% to 7.27%**.

**Existing visual recommendation:** Lead with three large metrics and keep the delivery-policy chart as supporting evidence. Mark the manual audit as single reviewer.

**Speaker script:**  
The guardrail results show the difference between prompt quality and delivery policy. With the strict prompt, 2 of 51 raw ULB outputs had a detected violation. With the simple prompt, all 51 raw outputs violated the accepted contract. Every detected failure activated deterministic fallback. The validator was also calibrated on a versioned corpus, intercepting all 330 constructed attacks while accepting all 318 faithful controls. I then manually reviewed all 49 strict-arm narratives that passed the validator. I judged none to contain a semantic contradiction with the supplied evidence. The 95% Wilson interval is 0% to 7.27%, so this is bounded single-reviewer evidence, not proof that every possible error is eliminated.

## Slide 9. Operational proof: the app preserves the evidence boundary

- One source-labelled queue contains S0 operational cases and ULB supporting evidence.
- The case view separates evidence, validation status, and analyst action.
- Workflow notes cannot modify recorded research artifacts.
- Rejected LLM output never becomes the official analyst brief.

**Existing visual recommendation:** Use three enlarged crops from the workbench: model evidence, validation and fallback, and analyst workflow. Avoid a full unreadable screenshot.

**Speaker script:**  
The application demonstrates that the same boundary can operate in an analyst-facing workflow. The queue is source-labelled, so S0 operational cases and ULB supporting evidence appear in one system without mixing their score scales. The case view separates the stored model evidence, the generated candidate, the validator decision, the delivered brief, and the analyst's own action. The application is a read-only consumer of the experiment artifacts. Notes and workflow states are stored separately and cannot rewrite predictions, SHAP reason codes, or narrative results. If the language model fails or is unavailable, the analyst still receives the deterministic evidence brief.

## Slide 10. The LLM improved articulation, not evidence completeness

- Deterministic brief: **39.09 words** and **3 named evidence items** on average.
- Accepted guarded LLM brief: **12 words** and **1 named evidence item**.
- All 23 accepted S0 candidates selected the shorter permitted summary.
- Two detailed attempts corrupted structured fields and were rejected.

**Existing visual recommendation:** Show one deterministic brief and one guarded LLM brief side by side. Place the word and evidence counts directly below each example.

**Speaker script:**  
The S0 result answers the concern that the language model may only be rewriting SHAP. In this experiment, the model was not allowed to create new analytical evidence. The deterministic brief named all three evidence items and averaged 39.09 words. Every accepted guarded candidate selected the shorter permitted option, averaging 12 words and naming only the leading evidence item. The two candidates that attempted the detailed form corrupted structured fields and were rejected. The language model therefore improved compact articulation, but it reduced evidence completeness. This negative result is important. The deterministic brief remains the trusted baseline, while the language-model brief is an optional first-pass summary.

## Slide 11. Human pilot: preference did not guarantee comprehension

- Eleven proxy reviewers completed 99 case reviews; results are descriptive.
- Median clarity was 4/5 for all three formats.
- The guarded LLM brief was selected as clearest and preferred first-pass format by 7/11 participants.
- The deterministic brief was selected as most trustworthy by 6/11.
- Objective comprehension did not improve with the guarded LLM brief.

**Existing visual recommendation:** Use the preference chart as the main panel and a compact comprehension summary. Do not present the pilot as the primary result.

**Speaker script:**  
The human pilot separates perceived readability from objective understanding. Eleven proxy reviewers completed 99 synthetic case reviews, so I report the findings as descriptive rather than as a population estimate. Median clarity was 4 out of 5 for all three formats. Seven participants selected the guarded language-model brief as the clearest and as their preferred first-pass format. Six selected the deterministic brief as the most trustworthy. However, the objective checks for leading evidence, direction, and evidence count did not improve with the guarded brief. A shorter explanation may feel easier to read without preserving as much evidence. This supports the decision to keep the deterministic brief visible.

## Slide 12. Conclusion: generated text remains untrusted until checked

- Detector: a reproducible source of signed model evidence.
- Guardrail: raw failures are measured and rejected before delivery.
- LLM: optional articulation, not a source of fraud knowledge.
- Workbench: operational review without mutating research evidence.
- Limits: anonymised real data, synthetic readable data, one audit reviewer, and a small proxy pilot.

**Existing visual recommendation:** Use four claim blocks and one final policy statement. Keep future work brief: independent audit replication, another local model, and real readable transaction data.

**Speaker script:**  
The project shows that generated fraud-alert text should be treated as untrusted until it passes deterministic evidence checks. The detector and SHAP provide the evidence. The local language model offers an optional, shorter articulation layer. Raw failures remain measurable, and failed candidates are replaced by evidence-derived fallback rather than repaired prose. The workbench demonstrates how that policy can be exposed in an operational review interface without changing the research artifacts. The main limitations are the anonymous real-data features, the synthetic semantic stream, the single-reviewer manual audit, and the small proxy pilot. The next steps are independent audit replication, evaluation with another local model, and testing on real data with interpretable operational fields.

# Examiner Q&A preparation

## Q1. What is the innovation if XGBoost, SHAP, and LLMs already exist?

The contribution is the evaluated delivery contract around those components. The project combines local execution, deterministic evidence checks, fail-closed fallback, provenance-linked artifacts, and separate measurement of raw and delivered output. It does not claim a new detector or language model.

## Q2. Why not use a normaliser to correct the LLM output?

A normaliser can hide a generation failure. The corrected text may look compliant even though the raw model response was not. This project retains the original candidate for measurement, rejects it when necessary, and creates fallback from the source reason codes. The failure remains visible and the delivered evidence remains traceable.

## Q3. Why not use only the deterministic brief?

The deterministic brief is the trusted baseline and fallback. The local LLM is retained as an optional articulation layer because participants often preferred its compact first-pass presentation. The results do not support replacing the deterministic brief, so both remain visible in the system.

## Q4. Why use both ULB and S0?

ULB provides real anonymised detector evidence and a realistic rare-event benchmark. S0 provides readable fields for semantic evaluation and workflow demonstration. They answer different parts of the same delivery-boundary question and are not compared as equivalent detector datasets.

## Q5. Did the autoencoder improve fraud detection?

No clear general improvement was observed. G2 had the highest mean F1, but the autoencoder groups did not consistently lead across metrics. G6 was selected for the downstream evidence chain because of its precision and false-positive profile, not because the project established algorithmic superiority.

## Q6. Do the guardrails catch every hallucination?

No universal guarantee is claimed. They detect violations under a defined contract. The corpus calibration and the 49-item manual review support the tested boundary, but the audit had one reviewer and the 95% confidence interval has a 7.27% upper bound.

## Q7. Is local execution a formal privacy guarantee?

No. The correct claim is privacy-conscious local processing with data minimisation. The payload excludes raw rows, exact values, labels, probabilities, and SHAP magnitudes. The project does not claim legal compliance certification or formal privacy preservation.

## Q8. Is the human evaluation sufficient?

It is a descriptive pilot involving 11 proxy reviewers and 99 case reviews. It supports discussion of clarity, trust, and comprehension, but it does not establish professional analyst productivity or a general format ranking.

## Q9. What does the website contribute to the research?

It operationalises and tests the evidence boundary. It shows that the same stored artifacts can support queue review, evidence inspection, visible fallback, and analyst workflow without allowing user actions to alter the model evidence.

## Q10. What is the safest practical conclusion?

Generated fraud-alert text should not become analyst-facing evidence merely because it is readable. It should be delivered only when deterministic checks confirm that it matches the approved evidence package. Otherwise, the system should return an evidence-derived fallback.

# Slide-build notes

- Keep one story throughout: detector evidence, optional local generation, deterministic validation, analyst delivery.
- Use conclusion-led titles rather than report-section titles.
- Label ULB and S0 clearly whenever results appear.
- Use large metrics and readable examples instead of dense bullet lists.
- Keep all claims bounded. Do not claim production deployment, formal privacy, detector superiority, complete hallucination removal, or professional analyst benefit.
- Keep each slide understandable within five seconds, with the detail carried by speaker notes.
