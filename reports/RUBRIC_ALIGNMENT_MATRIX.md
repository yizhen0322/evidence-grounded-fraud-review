# CP2 Rubric Alignment Matrix

Prepared for: Ng Yi Zhen  
Rubric checked: `CP2 Rubrics(1).pdf`  
Verification date: 29 July 2026

This matrix maps each assessed component to evidence in the final package. It is a verification aid, not a predicted mark. Presentation professionalism still depends on the live delivery. The logbook starts at the official CP2 Semester 2 Week 1 and runs through Week 12; its early entries record the CP1-to-CP2 design transition, while its later implementation entries are supported by dated repository artifacts.

## Logbook: 10%

| Rubric criterion | Evidence in the package | Alignment and boundary |
|---|---|---|
| Progress reporting | `logbook/CP2_Logbook_Ng_Yi_Zhen.md` contains official CP2 Week 1 to Week 12 entries dated 11 May to 31 July 2026. Every entry records an objective, progress, evidence, a problem or decision, critical reflection, and the next action. | Structurally aligns with the rubric's ten-or-more-week band. Weeks 1-9 describe proposal review and design preparation; Weeks 10-12 contain the strongest dated implementation and evaluation evidence. |
| Critical reflection | Every entry records work completed, evidence, decisions, problems, corrections, and the next step. The final reflection explains leakage control, fail-closed validation, evidence-source separation, and limitations. | Strongly aligned to the rubric's understanding and decision-justification criteria without inventing meetings, hours, or supervisor comments. |

## Final report: 50%

| Rubric criterion | Report evidence | Alignment |
|---|---|---|
| Abstract, 2.5% | Abstract includes context, problem, objectives, methodology, detector and explanation results, blinded manual-audit evidence, interim usability evidence, contribution, and limitations. | All required abstract elements are present. |
| Chapter 1: Introduction, 5% | Sections 1.1 to 1.6 cover background, problem statement, aim and objectives, research questions, contributions, scope, limitations, sustainability, societal value, and intended beneficiaries. | Explicitly addresses the computing problem and its broader impact. |
| Chapter 2: Literature Review, 5% | Sections 2.1 to 2.7 compare imbalance handling, autoencoder features, SHAP, narrative explanations, local deployment, guardrails, fallback, and the identified research gap. Table 2.1 maps literature limitations to implemented responses. | Provides a critical gap argument and keeps novelty claims qualified to the reviewed literature. |
| Chapter 3: Methodology, 10% | Sections 3.1 to 3.13 document the data split, leakage controls, six detector groups, five seeds, autoencoder, XGBoost, SHAP, prompt arms, guardrails, calibration, the provenance-bound blinded manual audit, React and FastAPI application, S0 evaluation, and interim usability study. | Reproducible and aligned to objectives, with performance, privacy, security, ethics, usability, and failure handling considered. |
| Chapter 4: Results and Discussion, 15% | Sections 4.1 to 4.15 present and critically discuss detector, G4, G5, manual-audit, S0, application, and interim usability results. Sections 4.10 to 4.13 compare the findings with prior research and a deterministic renderer baseline. Section 4.15 states threats and limitations. | The required result-and-discussion content is combined in Chapter 4 and linked to the research questions. |
| Chapter 5: Conclusion and Future Work, 5% | Section 5.1 synthesizes the findings. Table 5.1 maps all six objectives to achieved or partially achieved outcomes and boundaries. Section 5.3 derives future work from current limitations. | Directly aligned to the rubric's conclusion and justified future-work requirement. |
| References, 2.5% | Twenty cited sources are listed consistently; DOI-bearing and authoritative non-DOI records are checked in `docs/reviews/2026-07-26-final-reference-audit.md`. | Relevant and consistently presented. The audit should be retained with the project evidence. |
| Quality, organization, and writing, 5% | The final A4 report has rubric-aligned chapter structure, numbered tables and figures, matched page maps, appendices, and a page-level visual review. | Strong document organization and readability. Final portal rules and any official declaration pages remain administrative checks. |

## Presentation: 40%

| Rubric criterion | Slide evidence | Alignment and live-delivery boundary |
|---|---|---|
| Topic knowledge, 10% | Slides 2 and 3 establish the fraud-review problem, literature gap, research questions, and the distinct ULB and S0 evidence roles. | The deck supports a detailed explanation, but the mark depends on answering examiner questions accurately. |
| Technical approach, 10% | Slides 4, 5, and 7 explain the end-to-end method, detector design, SHAP evidence, local Ollama candidate, deterministic validator, and fallback. | Methodology is tied to objectives, privacy, safety, usability, society, and environmental trade-offs. |
| Critical thinking, 10% | Slides 6, 8, 9, 10, and 11 present results, honest interpretation, guardrail effects, the 0/49 blinded manual-audit result with its 7.27% upper bound, S0 operational evidence, LLM trade-offs, and interim usability evidence. | Conclusions are bounded by the anonymous ULB data, synthetic S0 stream, validator grammar, single audit reviewer, and interim sample of 11 participants. |
| Professionalism, 5% | `presentation/CP2_Final_Presentation_Script.md` and the presenter guide provide a structured narrative, demonstration path, limitations, and examiner questions. | Preparation evidence is present. Attire, punctuality, confidence, engagement, and minimal reading can only be demonstrated in the live session. |
| Quality of visual aids, 5% | The 12-slide deck uses one evidence-governed story, distinct visual roles, readable charts, visible source citations, and a visually checked PDF reference. | Designed for a clear live explanation rather than a dense report-on-slides format. |

## Overall submission boundary

The final package is aligned to the rubric's report structure and contains evidence for every assessed content area. Two boundaries remain relevant:

1. The logbook follows the official CP2 Semester 2 Week 1-12 timeline, but the early design entries are retrospective summaries of the CP1-to-CP2 transition rather than Git-dated implementation records.
2. Presentation professionalism is awarded from the live session.

These boundaries should remain visible. The submission should not invent additional meetings, hours, or presentation performance.
