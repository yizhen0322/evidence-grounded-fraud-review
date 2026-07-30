# CP2 Project Logbook (Semester 2)

**Student:** NG YI ZHEN  
**Student ID:** 23076003  
**Programme:** Bachelor of Computer Science (Hons)  
**Supervisor:** Dr Tang Tiong Yew  
**Project title:** Evidence-Grounded Local-LLM Explanations for Credit Card Fraud Alert Review  
**Semester period:** Official CP2 Week 1 to Week 12, 11 May to 31 July 2026

This logbook is organised according to the official Capstone Project 2 teaching
weeks. The early entries record the transition from the approved CP1 proposal
into an implementable CP2 design. Later entries reference the dated code,
experiments, reports, and evaluation artifacts produced during implementation.
The evidence column identifies the project material associated with each work
stream. No supervisor meeting, working hour, or feedback is claimed unless it
formed part of the actual project process.
The first entry therefore starts at the beginning of the CP2 semester timeline,
not only at the July implementation period.

Weeks 1-9 are retrospective CP1-to-CP2 planning and design summaries
reconstructed against the official teaching-week timeline. Dated repository
implementation and experiment evidence begins in Week 10; later-created files
listed in the early entries show where each design was subsequently formalised.

## Week 1. Project Restart and CP1-to-CP2 Scope Review

**Date:** 11-17 May 2026  
**Weekly objective:** Restart the project from the approved CP1 proposal and
identify what had to be delivered during CP2.

**Progress and output:** I reviewed the CP1 proposal, including the original
Autoencoder-XGBoost detector, SHAP explanations, local LLM, privacy rationale,
and guardrail plan. I separated the work into two questions: whether the hybrid
detector improved fraud detection, and whether generated explanations could be
kept faithful to model evidence. This prevented the LLM from being treated as a
second fraud detector.

**Evidence/files:**
`CP1/01_FINAL_SUBMISSION/Proposal_Capstone_Project.pdf`; final report Sections
1.2-1.5 and 3.1.

**Problem or decision:** The proposal combined model development, explainable
AI, an LLM, and an application. Without a clear hierarchy, CP2 could have looked
like several unrelated projects.

**Critical reflection:** I decided that the detector would remain the source of
the prediction, SHAP would provide attribution evidence, and the LLM would only
articulate that evidence. This role separation later became the central project
design.

**Next-week action:** Confirm project continuity and map the semester
deliverables.

## Week 2. Supervisor Continuity and Semester Planning

**Date:** 18-24 May 2026  
**Weekly objective:** Confirm the CP2 administrative starting point and plan the
work against the Week 12 submission deadline.

**Progress and output:** I confirmed that Dr Claymond Lim Wei Xiang remained the
supervisor from CP1. I mapped the project work to the CP2 teaching timeline:
design and preparation first, implementation and evaluation next, followed by
the final report, logbook, presentation, and system demonstration. I also kept
the project title open to revision if the detector results did not support the
original Autoencoder emphasis.

**Evidence/files:** `docs/references/CP2_Timeline_2026.png`; CP1 proposal cover;
final report cover and Section 1.3.

**Problem or decision:** A schedule based only on model training would leave
insufficient time for explanation validation, application work, writing, and
demonstration preparation.

**Critical reflection:** Treating the report, reproducibility evidence, and
system demonstration as project outputs from the beginning reduced the risk of
building a model that could not later be explained or defended.

**Next-week action:** Revisit the literature and identify the most defensible
research gap.

## Week 3. Literature Review and Contribution Reframing

**Date:** 25-31 May 2026  
**Weekly objective:** Reassess which part of the proposed project could make a
credible FYP contribution.

**Progress and output:** I reviewed literature on imbalanced fraud detection,
SMOTE, cost-sensitive learning, autoencoder features, XGBoost, SHAP, narrative
explanations, local language models, hallucination, and programmable
guardrails. Existing work already covered hybrid fraud detectors and LLM-based
explanation. The more specific gap was the measurement and fail-closed control
of LLM text against fixed SHAP evidence.

**Evidence/files:** The starting literature foundation is recorded in the CP1
literature review. The resulting CP2 synthesis was later formalised in final
report Chapter 2 and Table 2.1 and verified in
`docs/reviews/2026-07-26-final-reference-audit.md`.

**Problem or decision:** Claiming that Autoencoder plus XGBoost or “using an LLM
for explanations” was new would be difficult to defend against prior research.

**Critical reflection:** I reframed the intended contribution as an evaluated
explanation-delivery boundary: local generation, minimized evidence, code-level
validation, measured failure rates, and deterministic fallback. The detector
benchmark would test the original CP1 assumption rather than guarantee it.

**Next-week action:** Define the detector comparison, metrics, and research
questions before implementation.

## Week 4. Experimental Groups and Evaluation Design

**Date:** 1-7 June 2026  
**Weekly objective:** Design a fair detector experiment that could test the CP1
hybrid-model assumption.

**Progress and output:** I specified six detector groups: baseline XGBoost,
SMOTE-XGBoost, reconstruction-error hybrid, reconstruction-error plus SMOTE,
cost-sensitive XGBoost, and latent-feature hybrid. Five fixed seeds were planned
for every group. Average Precision was selected as the primary ranking metric,
with precision, recall, F1, ROC-AUC, ranked-alert metrics, confusion counts, and
runtime retained for interpretation.

**Evidence/files:** This design was later formalised in final report Sections
3.4-3.5 and Tables 3.1-3.2 and implemented in `configs/g0_xgb.yaml` to
`configs/g7_ae_latent_xgb.yaml`.

**Problem or decision:** Fraud accuracy is misleading because non-fraud cases
dominate the dataset. A single metric could also hide operational trade-offs
between missed frauds and unnecessary reviews.

**Critical reflection:** The multi-group, multi-seed design allowed the original
hybrid idea to fail without invalidating the project. It also created a stronger
basis for choosing one frozen detector for later SHAP and narrative work.

**Next-week action:** Define the data split, preprocessing, identity, and leakage
controls.

## Week 5. Dataset and Leakage-Control Design

**Date:** 8-14 June 2026  
**Weekly objective:** Establish a reproducible data protocol before model
training.

**Progress and output:** I retained the European Credit Card Fraud dataset from
the CP1 proposal and defined content deduplication, stable case identifiers, a
stratified 70/15/15 train-validation-test split, train-only scaler fitting, and
train-only SMOTE. Validation data would be used for tuning, detector selection,
and threshold selection; test data would remain untouched until freezing.

**Evidence/files:** This protocol was later formalised in
`data/raw/DATA_MANIFEST.md` and final report Sections 3.2-3.3, then implemented
in `src/data/load.py`, `src/data/split.py`, `src/data/preprocess.py`, and
`src/data/resample.py`.

**Problem or decision:** Leakage could occur through duplicate transactions,
scaling, resampling, autoencoder fitting, threshold selection, or unsafe joins
between predictions and explanations.

**Critical reflection:** Stable `case_id` values became necessary because SHAP,
LLM, and application records should never be joined by row position. I also
recognised that leakage prevention had to be demonstrated by tests and
manifests, not only described in the report.

**Next-week action:** Finalise the Autoencoder and XGBoost component design.

## Week 6. Detector Architecture and Hybrid-Feature Plan

**Date:** 15-21 June 2026  
**Weekly objective:** Translate the model proposal into components that could be
compared under one interface.

**Progress and output:** I planned a common XGBoost wrapper, validation-only
early stopping, validation-selected thresholding, an Autoencoder trained on
legitimate training observations, reconstruction-error features, and latent
features. SMOTE and class weighting were kept as separate imbalance strategies
so their effects would not be mixed.

**Evidence/files:** The component design was later formalised in final report
Sections 3.4-3.6 and implemented in `src/models/xgb.py`,
`src/models/autoencoder.py`, `src/evaluation/metrics.py`, and
`src/evaluation/threshold.py`.

**Problem or decision:** The original title could encourage selecting the hybrid
model regardless of the result. I instead planned all groups to use the same
split, metrics, artifact contract, and seeds.

**Critical reflection:** A negative Autoencoder result would still answer a
valid research question. This was more academically useful than changing the
metric or comparison after seeing the outcome.

**Next-week action:** Define the SHAP-to-LLM evidence boundary and narrative
failure checks.

## Week 7. Explainability, Local LLM, and Guardrail Design

**Date:** 22-28 June 2026  
**Weekly objective:** Specify how generated text would remain subordinate to
detector evidence.

**Progress and output:** I designed signed SHAP reason codes containing feature
identity, rank, and contribution direction. The local Ollama model would receive
only a minimized reason-code package, not a raw transaction row, exact values,
labels, probabilities, or SHAP magnitudes. Candidate narratives would be checked
for format, completeness, grounding, and direction. A failed check or unavailable
LLM would return a deterministic brief.

**Evidence/files:** This boundary was later formalised in final report Sections
3.6-3.8 and implemented in `src/explainability/`, `src/narratives/`, and
`corpus/guardrail_corpus_v1.jsonl`.

**Problem or decision:** Automatically normalizing or repairing rejected LLM
text would make the output look correct while hiding what the model originally
generated.

**Critical reflection:** I separated OFF-policy measurement of raw output from
ON-policy delivery. This allowed the project to report the LLM's observed
failure rate while ensuring that detected failures were not shown as accepted
evidence.

**Next-week action:** Design an application that demonstrates the same evaluated
evidence chain.

## Week 8. Analyst Workbench Architecture

**Date:** 29 June-5 July 2026  
**Weekly objective:** Plan a deliverable application that resembles an analyst
workflow rather than a model demonstration page.

**Progress and output:** I selected React and TypeScript for the frontend and
FastAPI for the local backend. The planned workflow used one alert queue, a case
review workspace, explanation assurance, evaluation results, and separate
analyst actions. Research artifacts would be immutable consumers, while status,
notes, and activity would be stored in a separate local SQLite workflow plane.

**Evidence/files:** This architecture was later formalised in
`docs/specs/2026-07-13-react-fastapi-demo-dashboard-spec.md` and final report
Sections 3.10-3.11, then implemented in `app/frontend/` and `app/backend/`.

**Problem or decision:** A dashboard organised around tabs for models and charts
could appear fragmented and would not explain who uses the system or what action
follows an alert.

**Critical reflection:** The application was reframed around the sequence
“select alert, inspect evidence, review validation, record an action.” It would
support decision-making but would not declare whether a transaction was truly
fraudulent.

**Next-week action:** Prepare the implementation contracts, provenance schema,
and review criteria.

## Week 9. Implementation Readiness and Evidence Contracts

**Date:** 6-12 July 2026  
**Weekly objective:** Convert the design into an executable build sequence with
clear artifact boundaries.

**Progress and output:** I prepared the implementation work breakdown for data,
models, experiments, SHAP, narrative generation, provenance, results, and the
application. I defined run manifests, stable source-run links, frozen artifacts,
and adversarial review expectations. Tests were planned where they protected
leakage, provenance, validation, and workflow contracts, rather than forcing
every documentation or presentation task into TDD.

**Evidence/files:** This readiness work was formalised at the start of Week 10
in `docs/plans/2026-07-13-cp2-implementation-plan.md`,
`docs/specs/2026-07-13-react-fastapi-demo-dashboard-spec.md`, and
`docs/specs/2026-07-14-fraud-review-workbench-spec.md`.

**Problem or decision:** The system had many interfaces. If detector predictions,
SHAP records, narratives, and dashboard cases used inconsistent identities or
unverified “latest” directories, the final demonstration could silently show a
different system from the reported experiment.

**Critical reflection:** Treating the plan and manifests as contracts made later
results easier to audit. The most important tests were placed at research-risk
boundaries instead of using TDD mechanically for every task.

**Next-week action:** Implement and execute the full detector-to-explanation
pipeline.

## Week 10. Core Implementation, Detector Benchmark, and First Review Package

**Date:** 13-19 July 2026  
**Weekly objective:** Build the reproducible research pipeline and obtain the
first complete experimental evidence.

**Progress and output:** I implemented dataset integrity checks, stable case IDs,
preprocessing, SMOTE, the XGBoost and Autoencoder components, thresholding,
manifests, and leakage audits. I ran six groups over five seeds, producing 30
detector runs. G6 had the numerically highest mean test AP at 0.855214, although
the leading differences were small and the Autoencoder variants showed no clear
advantage. G6 seed 42 was frozen for SHAP. I generated reason codes for 51
flagged cases, ran the strict and simple Ollama prompt arms, calibrated the
validator, implemented the first React-FastAPI workbench, and prepared a
supervisor review package.

**Evidence/files:** Git commits from `dc19eb8` onward; `experiments/runs/`;
`reports/tables/results_summary.csv`; `experiments/runs/2026-07-14_g4_seed42/`;
`experiments/runs/2026-07-14_g5_seed42/`; `app/`; `supervisor_meeting/`.

**Problem or decision:** The original Autoencoder claim was not supported. The
ULB feature names were also anonymous, so LLM narratives remained close to the
SHAP reason-code wording.

**Critical reflection:** I kept the negative detector result and repositioned
the project around verifiable explanation delivery. The first workbench made
the evidence visible but still needed a clearer operational story and better
result visualisation.

**Next-week action:** Present the progress, respond to feedback, and strengthen
the readable explanation evaluation.

## Week 11. Supervisor Feedback, Result Visualisation, and S0 Evaluation

**Date:** 20-26 July 2026  
**Weekly objective:** Improve how the project communicates detector trade-offs
and demonstrate the value and limitations of the local LLM more clearly.

**Progress and output:** During the supervisor discussion, the main practical
feedback was to show more bar charts, especially F1, and to make the purpose of
the website and the value of Ollama clearer. I added mean F1 with standard-
deviation error bars, grouped precision and recall, false-positive and
false-negative counts, and narrative violation, fallback, and acceptance
charts. I also ran an exploratory model search but retained the frozen G6 chain
because the alternatives did not justify breaking provenance. To address the
anonymous ULB limitation, I added the S0 synthetic stream with readable
transaction concepts. Its frozen test result was AP 0.544017 and F1 0.514286.
Among 25 selected alerts, 23 guarded LLM briefs passed and 2 used fallback.

**Evidence/files:** `docs/reviews/2026-07-20-detector-model-search.md`;
`reports/figures/detector_metric_bars.png`;
`reports/figures/narrative_delivery_bars.png`;
`docs/specs/2026-07-26-semantic-fraud-triage-extension.md`;
`experiments/runs/2026-07-26_s0_seed42/`; `reports/semantic_results_manifest.json`.

**Problem or decision:** S0 could make the project appear to contain two
unrelated detectors. The local LLM also did not consistently produce a more
complete brief than the deterministic renderer.

**Critical reflection:** I defined ULB as the supporting real-data detector
benchmark and S0 as the primary readable semantic and operational context. The
LLM's value is controlled articulation and measurable failure handling, not new
risk knowledge. The accepted S0 outputs choosing shorter summaries was retained
as a negative result.

**Next-week action:** Complete the human pilot, final report, presentation, and
submission verification.

## Week 12. Human Pilot, Final Report, Presentation, and Submission Preparation

**Date:** 27-31 July 2026  
**Weekly objective:** Integrate the completed evidence into the assessed CP2
deliverables before the 31 July deadline.

**Progress and output:** I prepared the consent material, questionnaire,
recruitment message, analysis plan, and explanation stimuli. Eleven adult proxy
reviewers completed 99 case reviews. Because this was below the planned minimum
of 18 and target of 30, I reported it as descriptive interim evidence and did
not run a superiority test. I also manually audited all 49 strict-arm narratives
delivered without fallback against their bound evidence and found no semantic
violation; the 95% Wilson interval was 0%-7.27%, so I retained the single-reviewer
and uncertainty limits. I completed the rubric-aligned final report,
12-week logbook, 12-slide presentation, presenter guide, submission index,
rubric matrix, page-map verification, and software test record. As of 29 July,
the final report was 79 A4 pages and the tested application remained a local
prototype rather than a production-bank deployment.

**Evidence/files:** `docs/studies/`; `reports/human_eval_results.json`;
`reports/tables/human_eval_*.csv`; `reports/thesis/submission/`;
`reports/presentation/`; `reports/RUBRIC_ALIGNMENT_MATRIX.md`;
`reports/thesis/submission/VERIFICATION_RECORD.md`;
`experiments/audit/audit_result.json`.

**Problem or decision:** The human sample was smaller than planned, and the
submission still required consistency checks across the report, logbook,
slides, figures, page numbers, and stated limitations.

**Critical reflection:** The final package is strongest when it reports both
positive and negative evidence. The project demonstrates a reproducible
detector-to-explanation chain and a fail-closed local-LLM delivery boundary, but
the 0/49 manual-audit observation still does not prove universal semantic
correctness. It also does not prove a new best detector, improved analyst
productivity, or production readiness.

**Next action:** Submit the final report and logbook by the course deadline,
rehearse the system demonstration and viva, and continue recruitment only if
additional responses can be incorporated without changing the frozen evidence
claims improperly.

## Overall Critical Reflection

Across the 12 teaching weeks, the project moved from the CP1 hybrid-model
proposal to an evidence-grounded explanation-delivery study. The Autoencoder
variants were implemented and evaluated but did not show a clear advantage.
That result changed the emphasis without being removed from the report. The
local LLM was then constrained to a narrow role: translating minimized SHAP
evidence into a standardised brief. Its raw output was measured separately from
the fail-closed delivery policy, and detected failures returned deterministic
evidence.

The application, S0 study, and interim human pilot improved the practical and
semantic evaluation, but they also introduced boundaries that must remain
visible. S0 is synthetic, the ULB and S0 detector scores are not directly
comparable, the validator only covers its tested contract, and the human pilot
contains 11 proxy reviewers rather than the planned 30. Preserving these limits
made the final project more credible and easier to defend during the viva.
