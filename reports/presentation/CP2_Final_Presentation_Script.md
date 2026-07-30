# CP2 Presentation Content

Project: **Evidence-Grounded Local-LLM Explanations for Credit Card Fraud Alert Review**  
Student: **Ng Yi Zhen (23076003)**  
Use: 12-slide CP2 presentation outline aligned to the assessment areas for topic knowledge, technical approach, critical thinking, professionalism, and visual aids.

**Timing status:** This is the expanded reference script, not a script to read verbatim. For the confirmed 15-minute format including the live demonstration, use `CP2_15_Minute_Viva_Runbook.md` and the current slide wording in `CP2_Presentation_Content.md`.

## Slide 1. Title and Project Position

- Evidence-grounded local-LLM explanations for credit-card fraud alert review.
- The detector makes the fraud-risk prediction; the LLM does not classify.
- SHAP reason codes remain the evidence source.
- The main contribution is a fail-closed explanation-delivery boundary.
- The prototype is a local analyst decision-support system, not a deployed bank system.

**Existing visual recommendation:** Use a clean title slide with a cropped screenshot of `reports/figures/workbench_queue.png` on the right.

**Speaker script:**  
Good morning. My project is about credit-card fraud alert review, but the main contribution is not a new fraud-detection algorithm. The detector is treated as the model that produces the fraud score, and SHAP reason codes are treated as the evidence explaining that score. The local LLM is only allowed to translate that evidence into a short review brief. If the generated text changes, loses, or invents evidence, a deterministic validator rejects it and the system falls back to the original evidence. So the project studies a controlled explanation-delivery boundary: what can safely reach an analyst, what must be rejected, and how this can be measured.

## Slide 2. Problem and Motivation

- Fraud detection is highly imbalanced; accuracy is misleading.
- Explanations can mislead if generated text is treated as evidence.
- Prior work shows the need for faithful narrative explanation, not just readable prose.
- Local LLMs may reduce external exposure, but local generation can still drift from evidence.
- The project asks how to keep generated explanations inside the model-evidence contract.

**Existing visual recommendation:** Use a custom problem-flow graphic with citation callouts for AlMarri (2025), Zytek (2024), and Rebedea (2023).

**Speaker script:**  
The problem has two parts. First, credit-card fraud is a rare-event classification problem, so a useful detector must be evaluated with AP, precision, recall, F1, and confusion counts rather than headline accuracy. Second, explanation is a separate risk. The literature already shows that readable narrative explanations can be useful, but faithfulness remains difficult. AlMarri highlights mismatches between LLM explanation and SHAP evidence, Zytek shows the value of narrative explanation, and Rebedea motivates programmable guardrails. My project focuses on the gap between those ideas: can local generated text be constrained, measured, and rejected when it violates the model evidence?

## Slide 3. Research Questions and Evidence Roles

- **RQ1:** How effectively do deterministic guardrails detect local-LLM output violations and enforce fallback?
- **RQ2:** What does guarded local-LLM delivery add, preserve, or lose compared with SHAP reason codes and deterministic briefs?
- ULB is the real anonymised benchmark and anonymous-feature prompt stress test.
- S0 is the synthetic readable-feature study for semantic and operational evaluation.
- They are two evidence roles in one study, not two competing detector datasets.
- S0 follows Fraud Detection Handbook concepts to make feature semantics inspectable.

**Existing visual recommendation:** Use a custom two-role evidence map: ULB for real-data benchmark evidence and S0 for readable semantic evidence.

**Speaker script:**  
The project has two research questions. RQ1 is about the guardrail and fallback mechanism: when the LLM output violates the contract, can the system detect that and prevent delivery? RQ2 is about what the LLM actually adds or loses in an analyst-facing workflow. I use two evidence contexts. The European ULB dataset is the real anonymised benchmark and keeps the work connected to the approved CP1 fraud-detection task. However, its V1 to V28 features are anonymous, so it is limited for business-readable explanation. S0 is a synthetic stream informed by Fraud Detection Handbook concepts, used to test semantic explanation behaviour with readable fields. The two are not directly compared as detector results.

## Slide 4. End-to-End Methodology

- Deduplicate source data and create stable case IDs.
- Split before scaling, SMOTE, autoencoder fitting, threshold selection, and SHAP.
- Train six detector groups across five fixed seeds.
- Freeze the selected detector and generate signed SHAP reason codes.
- Generate local-LLM briefs, validate them, and fall back when needed.
- Consume the same artifacts in the React/FastAPI workbench.

**Existing visual recommendation:** Use a simplified end-to-end methodology chain rather than the full architecture diagram.

**Speaker script:**  
The methodology is designed around leakage control and provenance. The source data are checked and deduplicated before modelling, and stable case IDs are used for joins across later artifacts. Splitting happens before preprocessing or feature construction, so scaling, SMOTE, autoencoder fitting, and threshold selection do not use test data. The detector benchmark produces logged metrics and predictions. The selected detector is then frozen and explained with signed SHAP reason codes. The local LLM receives only a minimized reason-code package, and the validator decides whether to deliver it or fall back. Finally, the workbench consumes the exact recorded artifacts rather than recalculating model logic.

## Slide 5. Detector Benchmark: What Was Tested

- Groups: G0, G1, G2, G3, G6, and G7 over seeds 42 to 46.
- G0: original features with XGBoost.
- G1/G3: training-only SMOTE.
- G2/G3/G7: autoencoder reconstruction or latent features.
- G6: cost-sensitive XGBoost using `scale_pos_weight`.
- Detector comparison is supporting evidence, not the main novelty.

**Existing visual recommendation:** Use a custom detector-group matrix showing input feature design and imbalance handling.

**Speaker script:**  
For the detector benchmark, I evaluated six groups over five fixed seeds. G0 is the original-feature XGBoost reference. G1 adds SMOTE to the training set only. G2 adds autoencoder reconstruction error. G3 combines reconstruction error and SMOTE. G6 uses cost-sensitive XGBoost through `scale_pos_weight`, and G7 uses the autoencoder latent features. This part is important because the explanation layer must be based on a reproducible detector, but I do not claim algorithmic novelty here. The detector stage supplies the frozen model evidence for the later explanation experiment.

## Slide 6. Detector Results and Honest Interpretation

- G6 had the numerically highest mean test AP: 0.855214 +/- 0.027097.
- G2 had the highest mean F1: 0.870054 +/- 0.026465.
- G7 had the highest mean recall: 0.816901 +/- 0.041063.
- G6 had the highest mean precision and lowest mean false-positive count.
- No group led every metric, and no ranked-winner claim is made.

**Existing visual recommendation:** Use `reports/figures/detector_metric_bars.png`, especially the F1, precision/recall, and FP/FN panels.

**Speaker script:**  
The detector findings are mixed. G6 had the highest mean AP, but its advantage over G0 was very small. G2 had the best mean F1, and G7 had the best mean recall. G6 was strongest on precision and false positives, which made it a defensible downstream evidence source, but it was not clearly stronger across all metrics. This is an important critical point. The autoencoder variants did not show a clear added value over the original-feature baseline. Therefore, I present the detector comparison as a disciplined supporting benchmark, not as proof that the hybrid detector is better.

## Slide 7. Explanation Boundary: SHAP to Local LLM to Guardrail

- G4 generated signed SHAP reason codes for 51 flagged ULB test cases.
- The LLM payload excluded raw rows, exact values, labels, probabilities, and SHAP magnitudes.
- OFF-policy analysis measures raw LLM violations.
- ON-policy delivery validates the same raw output and falls back on failure.
- Fallback is generated from reason codes, not from rejected prose.

**Existing visual recommendation:** Use a custom evidence/guardrail flow that separates raw output measurement from ON-policy delivery.

**Speaker script:**  
The explanation boundary is the central design. G4 produces signed reason codes from SHAP. These reason codes state which features pushed the detector score toward fraud or legitimacy. The LLM does not receive the full transaction, exact feature values, historical labels, detector probabilities, or SHAP magnitudes. It only receives a minimized evidence package. The experiment then separates two policies. OFF policy measures the raw text returned by the model. ON policy sends that exact same text through the validator. If it fails, the delivered output is generated from the original reason codes, not repaired from the LLM text. This prevents a normalizer from hiding generation failures.

## Slide 8. Guardrail Results: Why Validation Matters

- ULB strict prompt: 2/51 detected-any violations, 3.92% [1.08%, 13.22%].
- ULB simple prompt: 51/51 detected-any violations, 100% [93.00%, 100%].
- Every detected failure activated deterministic fallback.
- Corpus calibration intercepted 330/330 ULB attacks and accepted 318/318 faithful controls.
- Blinded manual audit: 0/49 delivered strict narratives had a semantic violation [0%, 7.27%].
- The audit used one student reviewer; it is bounded evidence, not universal proof.

**Existing visual recommendation:** Use `reports/figures/narrative_delivery_bars.png` and one small callout for "by construction".

**Speaker script:**  
The guardrail results show why validation matters. Under the strict prompt, two of the 51 raw ULB outputs had a detected violation, so both fell back. Under the simple prompt, every output violated the accepted contract, so no simple-arm narrative was delivered. The 0/49 detected rate among delivered strict narratives is expected from the policy, but I also completed a separate blinded manual review of all 49 delivered narratives. I found no semantic violation against their supplied evidence, giving a 95% Wilson interval from zero to 7.27%. This is stronger than relying on the validator alone, although it remains a single-reviewer result and is not universal proof.

## Slide 9. S0 Operational Study and Application

- S0 contains 50,000 synthetic transactions with readable operational fields.
- S0 test AP was 0.544017; precision 0.720000, recall 0.400000, F1 0.514286.
- The selected explanation set contained 25 above-threshold alerts.
- Guarded local-LLM briefs passed validation for 23/25 and fell back for 2/25.
- The application presents one source-labelled queue and separates Work from Model Evidence.

**Existing visual recommendation:** Use `reports/figures/workbench_queue.png` or `reports/figures/workbench_investigation.png`, plus a small inset from `reports/figures/semantic_detector_metrics.png`.

**Speaker script:**  
S0 addresses the limitation of anonymous ULB features. It is synthetic, so I do not treat it as real-bank validation, but it gives readable evidence such as amount compared with the customer's recent behaviour, terminal distance, night-time status, and terminal fraud risk. On the frozen S0 test period, the detector had AP 0.544 and F1 0.514. The explanation comparison used the 25 selected alerts, which in this run were exactly the above-threshold cases. The workbench opens on one queue with source labels, so S0 and ULB are visible in the same application without mixing their score scales. The application supports review, evidence inspection, validation display, fallback, and local workflow notes.

## Slide 10. What the LLM Added and Lost

- The deterministic S0 brief preserved all three evidence items.
- All 23 accepted guarded-LLM summaries selected the shorter permitted option.
- Accepted guarded summaries averaged 12 words and one named evidence item.
- Deterministic briefs averaged 39.09 words and three named evidence items.
- Participants more often selected the LLM brief as clearest, but it did not add evidence detail.

**Existing visual recommendation:** Use `reports/figures/semantic_explanation_assurance.png` or a two-column deterministic vs guarded-LLM text example from the report.

**Speaker script:**  
The most important S0 finding is that the LLM did not add analytical detail. In this design, it was not allowed to invent new evidence. It was given two permitted summary options: a detailed option naming all three evidence items and a shorter option naming the leading signal. All accepted LLM outputs selected the shorter option. That made them more compact, but less complete than the deterministic brief. The two outputs that attempted the detailed route corrupted structured fields and were rejected. In the human pilot, participants more often selected the LLM brief as clearest and preferred for first pass, but the deterministic brief was selected most often as trustworthy. The deterministic brief remains the trusted baseline, while the LLM is only an optional articulation layer.

## Slide 11. Human Evaluation: What People Preferred

- Eleven proxy reviewers completed 99 case reviews.
- Accuracy did not favour the guarded LLM brief on any comprehension check.
- Median clarity was 4/5 for all three formats.
- Guarded LLM brief was selected as clearest and preferred first-pass format by 7/11.
- Deterministic brief was selected as most trustworthy by 6/11.
- Interpretation: readability preference did not equal stronger evidence understanding.

**Existing visual recommendation:** Use `reports/figures/human_eval_outcomes.png` and `reports/figures/human_eval_preferences.png`.

**Speaker script:**  
The human evaluation gives a useful but bounded result. Eleven proxy reviewers completed 99 synthetic case reviews, so I treat the findings descriptively rather than as a formal analyst-productivity claim. The objective comprehension checks did not favour the guarded LLM brief. In fact, its point estimates were lower for leading evidence, direction, and evidence count. However, participants still tended to choose the guarded LLM brief as the clearest and preferred first-pass format. The deterministic brief was most often chosen as the most trustworthy. This separates readability from trust and evidence retention. It supports the design decision that readable LLM text should not replace the deterministic evidence layer.

## Slide 12. Conclusion, Limitations, and Next Work

- Main contribution: a provenance-linked fail-closed delivery boundary for local-LLM fraud-alert briefs.
- Detector result: autoencoder features did not show a clear advantage over baseline.
- Explanation result: guardrails can measure and block detected violations under tested contracts.
- Human result: perceived clarity and trust do not fully align.
- Societal/environmental relevance: local, minimized, fallback-first design may reduce unsupported explanation exposure and unnecessary model calls.
- Next work: independent audit replication, professional analyst study, additional local models, and real interpretable data.

**Existing visual recommendation:** Use a simple closing diagram: "Evidence -> Optional LLM -> Validator -> Delivered brief or fallback". Reuse elements from `reports/figures/cp2_system_architecture.png`.

**Speaker script:**  
My conclusion is that the project contributes a verifiable explanation-delivery boundary, not a new fraud detector and not an open-ended generative explanation system. The detector benchmark is reproducible but does not show a clear autoencoder advantage. The explanation experiments show that raw local-LLM behaviour must be measured separately from what is delivered to the analyst. The fallback design preserves evidence when validation fails. A blinded manual review found no semantic violation in the 49 delivered strict-arm narratives, although the 7.27% upper confidence bound and single-reviewer design remain important limits. The human pilot adds a separate caution: people may prefer the more readable LLM-style brief, but that does not mean it is more complete or more trustworthy. The societal value is prospective: the design may reduce unsupported explanation exposure by making fallback visible. Environmentally, the deterministic baseline means the LLM can be disabled or avoided when not needed, but I did not measure energy or carbon impact. The next steps are to replicate the audit with independent reviewers, test professional analyst use, compare additional local models, and apply the boundary to real interpretable fraud data.

# Examiner Q&A Preparation

## Q1. What is the innovation if XGBoost, SHAP, and LLMs already exist?

The innovation is the evaluated delivery boundary. The project does not claim a new detector or a new LLM method. It separates detector evidence, generated articulation, validation, fallback, and analyst workflow, then measures raw-output violations separately from delivered output. That makes the LLM a controlled translation layer instead of a source of new fraud evidence.

## Q2. Why not just use a deterministic renderer?

A deterministic renderer is the trusted baseline and fallback, and the results actually show it remains safer and more complete in the current S0 setup. The LLM is retained as an optional articulation layer because participants preferred its readability in the interim pilot and because its failures can be measured and blocked. The project does not argue that the LLM must replace deterministic briefs.

## Q3. Why use both ULB and S0? Does that make the project unfocused?

They serve different evidence roles in the same research question. ULB is the real anonymised benchmark and supports the detector and SHAP chain. S0 is synthetic but readable, so it allows the semantic behaviour of explanations to be checked. The report does not directly compare their detector scores because their data sources, feature spaces, prevalence, and split designs are different.

## Q4. Did the autoencoder add clear detector value?

No clear added value was observed. G2 was only slightly above G0 in mean AP, G3 was lower and more variable, and G7 was competitive but not clearly better. This is reported as a null or small-effect finding rather than hidden. The explanation-delivery boundary is the main contribution.

## Q5. Does the local LLM give a formal privacy guarantee?

No formal privacy proof is claimed. The correct wording is privacy-conscious local deployment with data minimization. The LLM payload excludes raw rows, exact values, labels, detector probabilities, and SHAP magnitudes, but the project does not claim compliance certification or full privacy preservation.

## Q6. Do the guardrails catch every hallucination?

No. The validator detects violations under a defined contract and prevents detected failures from being delivered. Residual detected violation is zero by construction because only passing text is delivered. I therefore performed a separate blinded manual audit: 0 of 49 delivered strict narratives contained a judged semantic violation, with a 95% Wilson interval of 0% to 7.27%. That supports the reviewed set, but one reviewer and a non-zero upper bound mean I still do not claim that every possible hallucination is caught.

## Q7. Is the human evaluation enough?

It is useful but bounded. Eleven proxy reviewers completed 99 case reviews, with fixed case order and proxy reviewers rather than professional analysts. It supports cautious discussion about comprehension and preference, not a claim of analyst productivity or format ranking.

## Q8. What would you improve next?

The highest-priority next steps are completing recruitment to 30 participants, counterbalancing case order and format assignment, independently replicating the completed semantic audit with multiple reviewers, and testing the same boundary with another local model or a real interpretable fraud dataset. These would strengthen external validity, add inter-rater evidence, and better estimate whether the readable layer helps real review work.

## Q9. Why did you not train only one final model?

The project needed a reproducible evidence source before testing explanations. The multi-group detector benchmark was used to choose and justify that source under leakage controls. After selection, G6 seed 42 was frozen for SHAP and narrative experiments. The explanation layer is then evaluated on top of fixed evidence rather than repeatedly changing the detector.

## Q10. What is the safest practical conclusion?

The safest conclusion is that generated fraud-alert text should be treated as untrusted until it passes deterministic evidence checks. In this project, SHAP reason codes and deterministic briefs remain the evidence layer, while local-LLM text can be offered only when it stays within the contract. If it fails or the model is unavailable, the analyst still receives the fallback evidence.

# Slide-Build Notes

- Keep the slide deck focused on one story: **evidence-bound local-LLM delivery for alert review**.
- Do not title sections as separate projects such as "Detector Project", "S0 Project", and "Human Study Project".
- Prefer the wording "supporting detector benchmark", "synthetic semantic study", and "interim human pilot".
- Avoid unsupported claims about model ranking, significance, production deployment, formal privacy guarantees, analyst usefulness, or total hallucination removal.
- Use source-labelled captions when showing ULB and S0 results together.
- Put limitations on the main slides, not only in Q&A. This supports the critical-thinking component of the rubric.
