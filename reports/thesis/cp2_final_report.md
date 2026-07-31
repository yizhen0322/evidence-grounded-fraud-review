# Evidence-Grounded Local-LLM Explanations for Credit Card Fraud Alert Review

## Capstone Project 2 Final Report

**Study focus:** Fail-closed local-LLM explanation delivery, supported by a reproducible detector benchmark and a readable synthetic evaluation stream  

**CAPSTONE PROJECT 2**

**Final Report**

**Student:** NG YI ZHEN  
**Student ID:** 23076003  
**Programme:** Bachelor of Computer Science (Hons)  
**Supervisor:** Dr Tang Tiong Yew  
**School:** School of Computing and Artificial Intelligence  
**Faculty:** Faculty of Engineering and Technology  
**Semester:** April 2026  
**Academic year:** 2025/2026  
**Submission date:** 29 July 2026

<!-- pagebreak -->

# Abstract

Credit-card fraud alerts require more than a risk score: an analyst also needs a concise and accurate account of the evidence behind that score. SHAP can provide signed feature attribution for a frozen detector, but attribution values remain technical, while a large language model may omit a listed contribution, introduce unsupported information, or reverse its direction. This project therefore evaluates a fail-closed local-LLM explanation layer that treats generated text as an untrusted candidate, validates it against a minimised SHAP evidence package, and replaces detected failures with a deterministic brief.

Six detector configurations were first compared on the European Credit Card Fraud dataset using content deduplication, stratified 70/15/15 splits, training-only preprocessing, validation-only threshold selection, and five fixed seeds. G6 produced the numerically highest mean test Average Precision at 0.855214 ± 0.027097, but the differences between the leading configurations were small and the autoencoder variants showed no clear advantage. The frozen G6 seed-42 cost-sensitive XGBoost detector was therefore retained as a reproducible evidence source rather than as an algorithmic contribution. In an anonymous-feature prompt stress test, a strict prompt produced a detected violation in 2/51 raw outputs (3.92%, 95% Wilson interval 1.08% to 13.22%), while a simple prompt produced one in 51/51 (100%, 93.00% to 100%). Every detected failure activated deterministic fallback. Within its versioned template-constrained corpus, the validator intercepted 330/330 attacks and falsely rejected 0/318 faithful controls.

The primary semantic evaluation used S0, a synthetic stream of 50,000 transactions with 11 business-readable features and a chronological 70/15/15 split. On the frozen test period, the detector achieved AP 0.544017, precision 0.720000, recall 0.400000, and F1 0.514286 at the validation-selected threshold 0.972929. Among 25 selected alerts, the guarded local-LLM brief passed validation for 23 and activated deterministic fallback for 2. All 23 accepted responses selected the shorter permitted summary and named only the leading signal, so the language layer did not add detail beyond the deterministic brief. The S0 results are synthetic operational simulation evidence and are not compared with the ULB benchmark.

An interim human evaluation then compared raw reason codes, deterministic briefs, and guarded LLM briefs with 11 adult proxy reviewers, producing 99 completed case reviews. The sample was below the pre-specified minimum of 18 and target of 30, so no inferential test was performed. Top-evidence accuracy was 28/33 (84.85%) for raw reason codes, 29/33 (87.88%) for deterministic briefs, and 27/33 (81.82%) for guarded LLM briefs. Median clarity was 4/5 for every format. Seven of 11 participants selected the guarded LLM brief as the clearest, and seven selected it as their preferred first-pass format, while 6 of 11 selected the deterministic brief as the most trustworthy. Because case assignment and presentation order were fixed, these descriptive findings do not establish a causal format effect or superiority.

The main contribution is an evaluated explanation-delivery process that keeps model evidence separate from LLM-generated wording. Each raw response is measured before validation, and any rejected response is replaced with a deterministic brief built from the original evidence. A React and FastAPI review application reads the same provenance-verified artifacts. A student-conducted blinded manual audit found no semantic violation in the 49 strict-arm narratives that passed the validator (0/49, 0%, 95% Wilson interval 0% to 7.27%). Conclusions remain limited to one historical dataset, one synthetic stream, one local 8B model, 51 ULB cases, 25 S0 alerts, predefined validator grammars, one manual auditor, and 11 proxy reviewers.

**Keywords:** credit-card fraud alert review; local large language model; SHAP; evidence grounding; deterministic guardrails; fail-closed fallback; analyst decision support

# List of Abbreviations

| Abbreviation | Meaning |
|---|---|
| AE | Autoencoder |
| API | Application Programming Interface |
| AP | Average Precision |
| AUC-ROC | Area Under the Receiver Operating Characteristic Curve |
| FYP | Final Year Project |
| LLM | Large Language Model |
| ML | Machine Learning |
| SHAP | SHapley Additive exPlanations |
| SMOTE | Synthetic Minority Over-sampling Technique |
| XAI | Explainable Artificial Intelligence |
| XGBoost | Extreme Gradient Boosting |

# List of Tables

Table 2.1. Literature streams, limitations, and implemented responses  
Table 2.2. Prior-work comparison for guarded narrative delivery  
Table 3.1. Detector configurations and experimental purpose  
Table 3.2. Detector tuning budget and comparison constraint  
Table 3.3. S0 semantic feature catalogue and operational meaning  
Table 4.1. Dataset integrity and seed-42 split counts  
Table 4.2. Five-seed detector performance  
Table 4.3. Frozen G6 seed-42 performance  
Table 4.4. Validator calibration outcomes  
Table 4.5. Strict and simple prompt outcomes  
Table 4.6. S0 synthetic stream and chronological split counts  
Table 4.7. S0 detector performance at the validation-selected threshold  
Table 4.8. S0 explanation assurance outcomes  
Table 4.9. S0 deterministic and guarded-LLM brief comparison  
Table 4.10. Interim human evaluation participant profile  
Table 4.11. Interim human evaluation comprehension accuracy  
Table 4.12. Interim human evaluation rating summaries  
Table 4.13. Interim human evaluation format preferences  
Table 4.14. Research question summary  
Table 5.1. Achievement of project objectives  
Table A.1. Experiment and evidence map  
Table B.1. Software and reproducibility summary  
Table E.1. Supporting detector ranking metrics  
Table E.2. Supporting detector confusion counts and runtime

# List of Figures

Figure 3.1. CP2 system architecture and evidence boundary  
Figure 3.2. Unified Alert Queue for operational and research review work  
Figure 3.3. Case Review evidence brief and bounded local-LLM note  
Figure 4.1. Detector metric comparison across five seeds  
Figure 4.2. Seed-42 precision-recall curves  
Figure 4.3. Global mean absolute SHAP importance  
Figure 4.4. Narrative violation, fallback, and acceptance rates  
Figure 4.5. S0 Explanation Assurance with an unlisted-feature mutation  
Figure 4.6. S0 direction-flip assurance test  
Figure 4.7. S0 detector metrics on the synthetic operational test period  
Figure 4.8. S0 explanation assurance outcomes
Figure 4.9. Interim human evaluation comprehension and rating outcomes  
Figure 4.10. Interim human evaluation format preferences

<!-- mainmatter -->

# 1. Introduction

## 1.1 Background

Credit-card fraud detection must identify a rare minority class within a large volume of legitimate transactions. The public European Credit Card Fraud dataset used in this study contains 284,807 transactions and 492 fraud cases before deduplication, corresponding to approximately 0.172% fraud prevalence. In this setting, accuracy is not an informative headline measure, because a classifier can appear accurate by favouring the majority class. Average Precision (AP), recall, precision, F1, and ranked-alert measures are more appropriate because they focus on the trade-off between capturing fraud and controlling false alerts.

The operational problem is also broader than classification. A risk score may help rank alerts, but it does not by itself communicate which model features pushed a case towards fraud or legitimacy. SHAP can provide signed feature attribution for a frozen model, yet raw attribution values and plots remain technical. Narrative explanations may make this evidence easier to scan, but a free-form large language model can introduce a second failure surface by omitting a reason, adding an unsupported feature, or reversing the direction of a contribution.

This project addresses the combined detection and explanation-delivery problem. The detector is treated as the authoritative classifier, SHAP is treated as model-attribution evidence rather than causal truth, and the local LLM is restricted to translating a small reason-code package. A deterministic validator then decides whether the generated text can be delivered or must be replaced by the original reason codes. The analyst uses the resulting evidence to choose a routing action; the application does not declare whether a transaction is fraudulent.

## 1.2 Problem Statement

Extreme class imbalance complicates detector evaluation. Fraud cases are rare enough that resampling, cost-sensitive learning, and anomaly-derived features may shift the balance between recall and precision. These techniques must be compared under a common split and leakage protocol, because applying scaling, SMOTE, autoencoder fitting, or threshold selection outside the training and validation boundaries would inflate reported performance.

The communication of evidence raises a separate problem. A model attribution that is technically correct is not automatically a safe natural-language explanation. If an LLM is permitted to reason independently of the supplied evidence, its narrative can differ from the detector's actual feature contributions. The system must therefore distinguish between the classifier's decision, the evidence extracted from that decision, and the later articulation of that evidence.

Measurement matters equally, because a claim that a guardrail "eliminates hallucinations" is not testable unless the guardrail is treated as an instrument with known scope. Raw model behaviour, validator detection, fallback delivery, corpus interception, false rejection, and human review must each be measured separately. In particular, a zero detected-violation rate among delivered narratives is expected by policy, because only validator-passing narratives are delivered; it is not evidence that the validator catches every possible semantic error.

## 1.3 Aim and Objectives

The aim of this project is to implement and evaluate a fail-closed local-LLM explanation layer that translates model-attribution evidence into an analyst-facing fraud alert brief, without allowing detected evidence violations to reach the analyst as accepted prose.

The objectives are:

1. Establish reproducible detector evidence through a leakage-controlled comparison, validation-based model freezing, and signed SHAP reason codes.
2. Evaluate a locally hosted LLM as a constrained articulation layer using fixed evidence packages and two prompt conditions.
3. Measure raw-output violations, validator decisions, and fallback outcomes without normalising or rewriting the original model output.
4. Calibrate the deterministic validator on versioned attack and faithful-control corpora before using it as a measurement instrument.
5. Compare raw reason codes, a deterministic brief, and guarded local-LLM delivery in the S0 readable-feature context.
6. Deliver the same provenance-verified evidence through a local analyst workbench while keeping research artifacts immutable and analyst workflow state separate.

## 1.4 Research Questions

**RQ1.** Under the tested evidence contracts, how effectively can deterministic guardrails detect local-LLM output violations and enforce fail-closed delivery for fraud alert briefs?

**RQ2.** In an analyst-facing fraud alert workflow, what information does guarded local-LLM delivery add, preserve, or lose compared with raw SHAP reason codes and a deterministic brief?

Both research questions are evaluated through a single evidence-governed architecture. ULB provides a supporting real-data detector benchmark, the frozen SHAP chain, and an anonymous-feature prompt stress test. S0 provides the primary semantic and operational explanation context, because its readable transaction concepts allow deterministic and local-LLM briefs to be checked against recognisable evidence. S0 does not enter the ULB detector ranking, and the two score scales are not compared.

The work therefore evaluates a single main proposition: that generated explanation text can be treated as an untrusted delivery artifact rather than as a second model decision. The detector benchmark, provenance chain, validator calibration, S0 comparison, and local workbench support that proposition. The study does not demonstrate a new fraud-detection algorithm, universal semantic correctness, improved analyst performance, or production-bank effectiveness.

## 1.5 Contributions

The primary contribution is a provenance-linked, fail-closed explanation-delivery design. It traces a frozen detector through signed SHAP evidence, standardised reason codes, local-LLM generation, deterministic validation, and fallback. The LLM does not classify transactions, and it never receives raw rows, exact feature values, historical labels, detector probabilities, or SHAP magnitudes.

The design is evaluated by preserving the exact raw model output and by separating candidate behaviour from delivery policy. That same output is measured before validation and is then passed unchanged to the validate-or-fallback policy, so that a normaliser, parser, or renderer cannot conceal the original model behaviour. The validator is adversarially calibrated, and its interception and false-rejection rates are scoped to versioned synthetic corpora.

Two supporting contributions make that evaluation auditable. The first is a 30-run detector benchmark with stable case identifiers, manifests, source hashes, validation-selected thresholds, and immutable predictions, which provides the model-evidence source. The second is the React and FastAPI Fraud Alert Review application, which consumes the evaluated artifacts while separating immutable research evidence from writable workflow metadata. S0 supplies the main readable context for comparing raw SHAP evidence, deterministic rendering, guarded local-LLM articulation, and fallback. Neither the detector benchmark nor the application is presented as a separate research topic.

## 1.6 Scope and Limitations

The empirical scope is offline binary classification on one historical, anonymised European credit-card dataset, together with one synthetic transaction stream generated for this study. The detector comparison spans six configurations across five fixed seeds. The explanation study covers the 51 flagged cases of the frozen seed-42 detector under two prompts, and the 25 above-threshold alerts of the frozen S0 test period under one structured prompt. One local runtime, llama3:8b through Ollama, was evaluated throughout.

S0 provides the primary semantic and operational explanation context because its fields, such as transaction amount, amount relative to the customer's prior 30-day mean, terminal distance, night flags, and weekend flags, can be read and checked against the synthetic record. That readability is a property of the feature design rather than of the language model, and the stream remains synthetic and single-seed. S0 therefore supports an operational simulation claim only, and its detector scores are never placed alongside the ULB scores.

Five limitations follow from this scope and affect how the results should be interpreted. First, the ULB features are anonymised components, so a narrative naming V14 can be checked for fidelity but not for business meaning. Second, only G2 and G6 received a 20-trial search, and cross-group differences are therefore descriptive rather than causal. Third, the deterministic validator accepts only a predefined grammar. Faithful paraphrases outside that grammar are rejected, and the calibration results apply only to the versioned corpora used to test it. Fourth, the blinded semantic audit was completed by one student reviewer without a second annotator or agreement statistic; its 0/49 result has a 95% Wilson upper bound of 7.27% and does not establish universal correctness. Fifth, the human usability evidence comes from 11 proxy reviewers under fixed case-to-format assignment and is interim and descriptive. Section 4.15 discusses these limitations alongside the reported results.

The system does not process live transactions, block payments, model real customer or merchant histories, or claim causal explanations. Fairness, drift, adversarial robustness, multi-user operation, load behaviour, and regulatory compliance were not evaluated.

## 1.7 Significance

The significance of the work lies in where it draws the boundary rather than in any component it uses. A risk score tells an analyst which case to open; it does not record what the model weighted. SHAP recovers that record, but as signed values rather than readable evidence. Introducing a language model to close that gap opens a second failure surface, because generated prose can omit a listed contribution, add one that was never supplied, or reverse a direction while remaining fluent. The design treats every generated brief as an untrusted candidate and delivers it only if it satisfies an explicit evidence contract; otherwise the deterministic brief built from the same reason codes is delivered, and the substitution is visible.

Three groups could benefit if this boundary were adopted. An analyst would receive a first-pass brief whose provenance is unambiguous, with the ranked evidence still available underneath. A customer would benefit indirectly from a review process in which fluent text cannot substitute for recorded model evidence. A model-risk or governance reviewer would gain an audit trail in which the rejected candidate, the validator outcome, the fallback, and the source manifest are all retained. These are prospective uses. None of analyst productivity, decision quality, fraud loss, fairness, customer outcome, or compliance was measured in this study, and no claim is made about any of them.

The specific harm addressed is the presentation of unsupported generated text as if it were detector evidence, which can misdirect an investigation and is difficult to audit after the fact. The design reduces that risk for the failure modes the validator detects. It does not correct errors in the detector, in the SHAP computation, in the evidence catalogue, or in the analyst's own judgement.

Sustainability is treated as a design consideration and not as a measured result. Generation runs locally on an 8B model with a minimised payload, the deterministic renderer produces a complete brief with no model call, and a rejected candidate is replaced rather than regenerated. The optional layer can therefore be disabled without removing analyst-facing evidence. Against this, local inference still consumes electricity and hardware. No energy, carbon, or utilisation measurement was performed, and no environmental benefit is claimed.

# 2. Literature Review

## 2.1 Credit Card Fraud Detection as an Imbalanced Classification Problem

Credit card fraud detection is commonly formulated as binary classification, but the operational objective differs from a conventional balanced classification task. Fraud cases are rare, false negatives may carry direct financial cost, and false positives create investigation workload and customer friction. The European dataset used in this study contains only 492 fraud cases among 284,807 transactions. At this prevalence, overall accuracy is unsuitable as a primary measure, because a majority-class prediction strategy can appear highly accurate while failing to identify fraud (Marazqah Btoush et al., 2023).

The literature therefore places greater emphasis on minority-sensitive measures. AP summarises ranked precision across recall increments and is more informative than accuracy when the positive class is rare (Hancock et al., 2022). Threshold-dependent precision, recall, and F1 describe the behaviour of a selected operating point, while ranked-alert measures such as Precision@100 and Recall@100 reflect the practical situation in which an analyst can inspect only a limited number of highly ranked cases. A detector can have a strong ranking metric and still produce an unsuitable alert volume at a poorly selected threshold.

The dataset also carries methodological limitations that affect interpretation. The V1-V28 features are anonymised transformations and do not expose merchant, device, location, customer, or transaction-category semantics. Dal Pozzolo et al. (2015) discuss evaluation under severe imbalance using this data source, while the dataset provider documents the original counts and feature structure (Machine Learning Group - ULB, n.d.). The dataset is useful for controlled comparison, but it cannot reproduce the information richness or temporal drift of an operational banking environment.

Synthetic transaction streams provide a controlled way to study temporal features and operational evidence without claiming access to real bank data. The Fraud Detection Handbook documents a reproducible simulator and baseline feature-transformation workflow for customers, terminals, fraud scenarios, and chronological evaluation (Le Borgne et al., 2022). Synthetic data cannot establish real-world accuracy, but it can make feature timing, leakage boundaries, and explanation semantics explicit. For this reason, S0 is used as the primary semantic and operational explanation context, while the approved ULB dataset remains the real-data detector benchmark.

## 2.2 Imbalance-Handling Strategies

Imbalance handling can be implemented at either the data level or the algorithm level. Data-level methods alter the training distribution. SMOTE creates synthetic minority examples between neighbouring minority observations (Chawla et al., 2002), increasing minority representation without duplicating records exactly. In fraud data, however, synthetic interpolation can also expand ambiguous regions, preserve noise, or create examples that do not correspond to plausible transactions. Hajjami and Diallo (2025) address this problem by combining oversampling with noise reduction, which illustrates why sampling design must be evaluated rather than assumed to be beneficial.

Algorithm-level methods leave the observed training records unchanged but modify the learning objective. Cost-sensitive fraud detection assigns different consequences to false-negative and false-positive errors. Bahnsen et al. (2013) formulate this using Bayes minimum risk and transaction-specific costs. XGBoost is a regularised gradient-boosting framework for scalable tree learning (Chen & Guestrin, 2016). Its `scale_pos_weight` parameter increases the contribution of minority examples during training. This approach does not synthesise new rows, but it can shift the decision boundary and alter the balance between precision and recall.

SMOTE and class weighting are therefore treated as controlled experimental factors in this project. G1 applies SMOTE to original features, G3 applies it after the reconstruction-error feature is created, and G6 uses cost-sensitive XGBoost. All three approaches are confined to the training split. Their performance is compared under the same validation-based threshold selection and untouched test distribution.

## 2.3 Autoencoder-Derived Fraud Features

An autoencoder learns to reconstruct its input through a lower-dimensional bottleneck. Bottleneck networks have long been used to learn compact representations of high-dimensional data (Hinton & Salakhutdinov, 2006). When an autoencoder is trained primarily on legitimate transactions, reconstruction loss can act as an anomaly signal, because observations that differ from the learned legitimate pattern may produce larger errors. The bottleneck activations can also be used as learned latent features for a downstream classifier.

Ding et al. (2024) provide a close precedent by combining an autoencoder with LightGBM for credit card fraud detection. Their work confirms that autoencoder-plus-boosting is an established hybrid pattern rather than a new algorithm introduced by this project. The empirical question is whether the additional representation produces a useful signal for the present dataset and protocol.

Three experimental groups address that question. G2 appends a single reconstruction-error feature to the original variables. G3 combines the same feature with training-only SMOTE. G7 appends the ten bottleneck activations. These designs separate a lightweight anomaly feature from a richer learned representation. The hybrid configurations are retained even if they do not improve performance, because a controlled negative result still informs whether the added training complexity is justified.

## 2.4 Explainable Artificial Intelligence and SHAP Evidence

Tree-based ensembles are effective for tabular classification, but their decision paths are difficult to communicate directly (Weber et al., 2024; Černevičienė & Kabašinskas, 2024). SHAP provides additive feature attributions derived from Shapley-value principles (Lundberg & Lee, 2017). For a specific prediction, each attribution describes how a feature contribution moves the model output relative to its baseline. Global mean absolute SHAP values summarise which features had larger attribution magnitudes across an explanation sample.

FraudX AI demonstrates the use of SHAP in an interpretable fraud-detection workflow (Baisholan et al., 2025). Such applications show the value of model attribution, but they also reveal a communication problem. A waterfall plot or a vector of signed values is useful to a technical reviewer, yet an analyst still has to identify the dominant features and interpret their directions consistently (Rong et al., 2024).

This project implements a standardised reason-code boundary between SHAP and narrative generation. Each flagged case is represented by its three largest signed contributions, ordered by absolute magnitude. Each reason code records the feature identifier, rank, and contribution direction. The reason codes remain the authoritative analyst-facing fallback and can be used without any generated text. Throughout the report, SHAP is described as attribution of the frozen model's output rather than as a causal explanation of fraudulent behaviour.

## 2.5 Narrative Explanations and LLM Faithfulness

Recent XAI research has examined whether technical attribution artifacts can be translated into natural language. Bello et al. (2025) describe a framework in which LLMs mediate between algorithmic explanations and stakeholder-facing language. In a study of narrative-driven explanations, Martens et al. (2025) report that narrative presentation can be persuasive to users. Zytek et al. (2024) propose Explingo, which combines an LLM narrator with an LLM grader to generate and evaluate free-text explanations.

The flexibility of natural language creates a separate reliability problem (Ji et al., 2023; Manakul et al., 2023; Huang et al., 2025). An LLM can add a feature that was never supplied, omit an important contribution, change the direction of a feature, or generate a plausible explanation drawn from general knowledge rather than from the specific model evidence. AlMarri et al. (2025) report divergence between LLM self-explanations and SHAP attribution in financial tabular classification. Their result is directly relevant here, because it shows that readable language cannot be treated as evidence fidelity.

This project responds by separating reasoning from articulation. The detector supplies the prediction, SHAP provides the model-attribution evidence, and the LLM may only translate a minimised reason-code package. Programmable guardrail frameworks motivate rule-based control of LLM output (Rebedea et al., 2023); this project implements a fully deterministic validator. This differs from an LLM-as-judge design because the acceptance decision does not rely on another stochastic model that may share similar generative failure modes (Zheng et al., 2023).

## 2.6 Local Deployment, Data Minimisation, and Fallback

Financial information is sensitive, so external transmission should be minimised. Local execution through Ollama keeps generation on the project machine, while evidence serialisation prevents the LLM from receiving the raw transaction row. The recorded G5 experiment input was limited to a stable case identifier, a coarse risk category, ranked anonymous feature names, contribution directions, and rank. The operational live-replay projection removes even that identifier, sending only the coarse risk and the ranked feature-direction evidence. Exact feature values, labels, probabilities, and SHAP magnitudes are excluded in both paths.

Local execution alone does not prove privacy or regulatory compliance. A formal claim would require threat modelling, access controls, secure deployment, a retention policy, and organisational assessment (National Institute of Standards and Technology, 2024). The report therefore uses the narrower description of privacy-conscious local deployment with data minimisation.

Fallback is necessary because both generation and validation can fail. If Ollama is unavailable, or if a generated narrative violates the evidence contract, the system returns deterministic reason codes. The review process can then continue without presenting unvalidated prose as model evidence.

## 2.7 Research Gap and Project Positioning

None of the individual components is new on its own. XGBoost, SMOTE, cost weighting, autoencoders, SHAP, local LLM execution, templates, and fallback are all established techniques. This project evaluates how they work together in a fraud-review setting. Its main contribution is the evaluation boundary: each raw narrative is measured before and after deterministic validation, while reason-code fallback and artifact provenance remain traceable.

The detector benchmark tests whether the proposed hybrid features improve performance. The explanation experiment measures failures in the raw narratives and the effect of fail-closed delivery. The workbench shows how an analyst can use the evaluated artifacts without changing the underlying research evidence (Amershi et al., 2019; Rong et al., 2024). These parts address one question: can a local LLM translate model evidence without becoming a new source of evidence?

S0 provides the readable feature labels that are missing from the ULB dataset. It applies the same fail-closed design to an independently implemented synthetic stream inspired by the Fraud Detection Handbook, using current-transaction fields and leakage-controlled historical features. S0 is not presented as more realistic than the ULB dataset. It tests whether the explanation controls remain traceable and measurable when the evidence uses operationally meaningful labels instead of anonymous components.

<!-- pagebreak -->

Table 2.1. Literature streams, limitations, and implemented responses

| Literature stream | Primary focus | Limitation addressed in this project | Implemented response |
|---|---|---|---|
| Imbalance handling | Resampling or class weighting | Explanation delivery is outside the detector objective | Compare SMOTE and class weighting under one leakage-controlled protocol |
| AE plus boosting | Learned anomaly features | Hybrid benefit varies by dataset and protocol | Test reconstruction and latent features, then report the observed result |
| SHAP-based XAI | Attribution values and plots | Evidence remains technical | Convert signed top-k attribution into standardised reason codes |
| LLM narrative XAI | Natural-language explanation | Generated text may diverge from supplied evidence | Restrict the LLM to minimised evidence translation |
| LLM-based grading | Automated explanation assessment | A stochastic grader may share generative weaknesses | Use deterministic checks and a versioned calibration corpus |
| Analyst dashboards | Scores and explanations | Demo state can be mixed with research evidence | Separate immutable evidence from workflow metadata |
| Synthetic fraud streams | Reproducible temporal fraud data | Synthetic realism is not real-bank validity | Use a primary semantic and operational evaluation track with explicit simulation boundaries |

As shown in Table 2.1, the reviewed streams address separate parts of the problem. This project combines them within one evaluation boundary covering detector evidence, constrained narrative generation, deterministic validation, fallback, and separated workflow state.

Table 2.2 sets out the four properties most closely related to the explanation-delivery contribution. The coding refers to the evaluated design reported by each study, rather than to every possible extension of that work.

Table 2.2. Prior-work comparison for guarded narrative delivery

| Study | Deterministic code-level validator | Fail-closed deterministic fallback | Local narrative-model execution | Raw and delivered output measured separately |
|---|---|---|---|---|
| AlMarri et al. (2025) | Not reported | Not reported | Yes | Not reported |
| Zytek et al. (2024) | No | Partial | Partial | Not reported |
| Bello et al. (2025) | Not reported | Not reported | Partial | Not reported |
| Martens et al. (2025) | Not reported | Not reported | No | Not reported |
| This project | Yes | Yes | Yes | Yes |

Table 2.2 uses `Partial` in a specific sense. Explingo describes an LLM-grader threshold that can reject a narrative and revert to a graph-based explanation, but the acceptance gate is itself stochastic; its main experiments use GPT-4o through an API, while a smaller local model is examined separately (Zytek et al., 2024). Bello et al. (2025) recommend on-premise execution for sensitive applications, although their reported case studies use GPT-4.5 illustratively and the framework remains conceptual. `Not reported` means that the property was not described as part of the evaluated design; it is not a universal proof of absence.

Within the reviewed literature, none of the compared studies evaluated all four properties together. This finding positions the contribution as a jointly evaluated delivery boundary rather than as an exhaustive priority claim over all possible prior work.

# 3. Methodology and System Design

## 3.1 Overview

The implemented methodology comprises four connected stages. First, data preparation and detector experiments produce leakage-controlled, provenance-linked results. Second, a validation-selected detector is frozen and explained using signed SHAP contributions. Third, a local LLM converts minimised reason-code evidence into a fixed narrative format that is deterministically accepted or replaced by fallback. Fourth, a React and FastAPI workbench consumes the exact recorded artifacts while storing only analyst-created workflow metadata in a separate SQLite plane.

![Figure 3.1. CP2 system architecture and evidence boundary. The detector, G4, G5, results, figures, and manifests remain immutable. Only the separate analyst workflow plane is writable.](reports/figures/cp2_system_architecture.png)

As shown in Figure 3.1, the evidence flow is one-way: immutable detector and explanation artifacts feed the workbench, while analyst changes remain in a separate workflow plane.

### 3.1.1 Objective-to-Method Mapping

Each objective in Section 1.3 is addressed by a specific method stage and reported through a specific measure, so that no objective depends on an unmeasured claim.

| Objective | Method stage | Reported measure |
|---|---|---|
| 1. Reproducible detector evidence | Sections 3.2 to 3.6 | Five-seed AP, precision, recall, F1; leakage and provenance audits; signed reason codes for 51 flagged cases |
| 2. Local LLM as a constrained articulation layer | Section 3.7 | Raw output retained per case under two prompts, with fixed evidence packages |
| 3. Separate raw violations from delivery outcomes | Sections 3.7.3 and 3.8 | Paired OFF/ON rates with n and 95% Wilson intervals; fallback counts |
| 4. Calibrate the validator before use | Sections 3.9 and 3.12 | Attack interception and false-rejection counts within versioned corpora |
| 5. Compare three explanation formats | Sections 3.12 and 3.13 | Structural comparison of delivered text; interim comprehension, rating, and preference results |
| 6. Deliver evidence through a local workbench | Section 3.11 | Artifact-chain validation, two-plane separation, no-write audit |

### 3.1.2 Design Constraints

Five constraints guided the design. Each one is linked to a concrete implementation control.

**Performance** is treated as evidence quality and delivery behaviour rather than throughput. Average Precision is the model-selection metric because prevalence is approximately 0.172%, and the operating threshold is chosen on validation data and then applied unchanged. Generation latency is recorded, with a mean of 21.932 seconds per S0 request before validation, but it is not optimised. No load or concurrency testing was performed.

**Security and privacy** are addressed by data minimisation and locality rather than by a security assessment. Generation runs on a loopback endpoint, and the serialised payload carries only the coarse risk bucket and the ranked feature names, directions, and ranks. Raw rows, exact feature values, detector probabilities, SHAP magnitudes, and historical labels are excluded by construction and covered by tests. This is described as privacy-conscious local deployment with data minimisation; a privacy claim would require threat modelling, access control, retention policy, and organisational review, none of which was performed.

**Ethics** applies mainly to the human study, which used synthetic alerts, collected no direct identifiers, and obtained recorded consent and age confirmation before any task item was shown. This report does not claim formal institutional ethics approval. A larger study, recruitment of practising analysts, collection of identifying or employment information, or any deployment-linked study would require the institutional review route before recruitment.

**Usability** is treated as an evidence-presentation requirement. The analyst works from a single alert queue; the source namespace is preserved so that two incomparable detector scales are never merged; retrospective ground truth is withheld from operational routes; and the delivered brief, the rejected candidate, and the validator outcome are shown separately. Section 3.13 describes the interim study that examined whether readers could extract the intended evidence from each format.

**Reproducibility** is enforced rather than described. Every run is driven by a versioned configuration and writes a manifest that binds the dataset hash, configuration hash, split summary, threshold, ordered feature names, upstream run identifiers, source hashes, and artifact hashes. Result selection uses an explicit 30-run allowlist; wildcards and a "latest" selector are rejected by both the results pipeline and the application loader.

## 3.2 Dataset and Data Integrity

### 3.2.1 Data Source and Prediction Target

The source dataset (Dal Pozzolo et al., 2015; Machine Learning Group - ULB, n.d.) contains 284,807 rows, 30 numeric input features, and a binary Class target. Features V1-V28 are anonymised principal components, while Time and Amount retain their original labels. Before deduplication, the source contains 492 fraud cases.

The target equals one for a fraudulent transaction and zero for a legitimate transaction. Fraud prevalence is approximately 0.172% before deduplication, so the task is treated as rare-event classification. The raw source file is frozen by SHA-256 hash before experiments are executed. Schema checks confirm the expected feature set, target values, row count, and the absence of unexpected columns.

### 3.2.2 Deduplication and Stable Case Identity

Content-based deduplication removed 1,081 rows before splitting, leaving 283,726 modelling rows and 473 fraud cases. A stable case_id was created before deduplication and excluded from content comparison and all model feature matrices. This identifier supports artifact joins across predictions, G4 reason codes, G5 narratives, audit packages, and the workbench without exposing row position as an implicit key.

## 3.3 Split and Leakage Controls

Each seed uses a stratified 70/15/15 train, validation, and test split. For seed 42, the split comprises 198,608 training rows with 331 frauds, 42,559 validation rows with 71 frauds, and 42,559 test rows with 71 frauds.

All preprocessing is fitted on training data only. Scaling parameters are learned from the training split and then applied to the validation and test splits. SMOTE is applied only to the training split. The autoencoder is fitted only on legitimate training rows and produces reconstruction or latent features for validation and test by forward application. Threshold selection uses validation predictions, and the frozen threshold is applied unchanged to test predictions.

The five seeds, 42 to 46, create independent stratified assignments under the same split ratios. Within each seed, the case ID sets are checked for pairwise disjointness and for complete coverage of the modelling dataset. Split assignments are persisted so that later stages do not recreate or infer membership.

### 3.3.1 Feature Scaling

A standard scaler is fitted to the training features only. The fitted means and scales are then applied to the validation and test partitions. The case ID and target columns never enter the scaler or the detector feature matrix. This control is important for Amount and Time, whose scales differ from those of the anonymised variables, and for the autoencoder, whose mean-squared reconstruction loss is sensitive to feature scale.

### 3.3.2 Training-Only Imbalance Handling

For G1 and G3, SMOTE (Chawla et al., 2002) is fitted and applied after the split and after feature construction, using only the training matrix and the training labels. Validation and test retain their observed prevalence. For G6, `scale_pos_weight` is computed from the legitimate-to-fraud ratio in the training labels. The weight is passed to XGBoost without changing the validation or test observations.

## 3.4 Detector Configurations

Table 3.1. Detector configurations and experimental purpose

| Group | Detector input and imbalance design | Purpose |
|---|---|---|
| G0 | Original features, XGBoost, no explicit imbalance handling | Original-feature reference baseline |
| G1 | Original features, training-only SMOTE, XGBoost | Test data-level resampling |
| G2 | Original features plus AE reconstruction error, XGBoost | Test lightweight anomaly feature |
| G3 | Original features plus reconstruction error, training-only SMOTE, XGBoost | Test reconstruction feature with resampling |
| G6 | Original features, cost-sensitive XGBoost using scale_pos_weight | Test algorithm-level imbalance handling |
| G7 | Original features plus AE latent bottleneck features, XGBoost | Test learned representation features |

As shown in Table 3.1, all groups were executed over seeds 42-46. Only G2 and G6 received a seeded 20-trial random search, having been the strongest untuned groups by validation AP. The other groups retained their predeclared defaults. This tuning asymmetry is reported as a limitation, because cross-group differences cannot be attributed solely to architecture or imbalance mechanism.

### 3.4.1 XGBoost Classifier

Using the gradient-boosted tree framework described by Chen and Guestrin (2016), XGBoost produces a continuous fraud score for every validation and test observation. The original-feature groups use the 30 scaled input variables. G2 and G3 add reconstruction error, while G7 adds ten bottleneck activations. The saved model, resolved parameters, ordered feature names, validation threshold, and environment are stored with each run.

### 3.4.2 Autoencoder Architecture

The autoencoder follows the bottleneck representation principle described by Hinton and Salakhutdinov (2006). It is a symmetric feed-forward network with a 30-dimensional input, a 20-unit hidden layer, a 10-unit ReLU bottleneck, a mirrored 20-unit decoder layer, and a 30-dimensional linear output. It is optimised with Adam at a learning rate of 0.001 using mean squared error. The maximum training length is 50 epochs, with a batch size of 256 and early stopping patience of five epochs.

Only legitimate training rows are used to fit the autoencoder. Ten per cent of those rows are reserved internally for reconstruction-loss early stopping; the global validation split is not used for AE weight fitting. Reconstruction error is the row-wise mean squared difference between the input and its reconstruction. Latent features are the ten bottleneck activations produced by the frozen encoder.

### 3.4.3 Hyperparameter Selection

The project uses validation AP as the principal detector-selection criterion. The G2 and G6 search records each contain 20 seeded trials. G6 was selected as the explanation source after validation comparison, not after inspection of test results. The final G6 configuration uses maximum tree depth 6, 500 estimators, learning rate 0.2, subsample 1.0, column sampling 0.7, and the training-derived class weight.

The same seed-42 validation split supported XGBoost early stopping, the two 20-trial searches, cross-group detector selection, and F1-based threshold selection. The test split remained untouched until each configuration was frozen, but repeated use of one validation split can make its AP and threshold estimates optimistic. This reuse is treated as a model-development limitation rather than independent repeated validation.

Table 3.2. Detector tuning budget and comparison constraint

| Group | Dedicated search budget | Basis used in the final comparison |
|---|---:|---|
| G0 | None | Predeclared XGBoost defaults |
| G1 | None | Predeclared defaults with training-only SMOTE |
| G2 | 20 seeded random-search trials | Tuned after ranking among the strongest untuned groups by validation AP |
| G3 | None | Predeclared defaults with AE reconstruction error and training-only SMOTE |
| G6 | 20 seeded random-search trials | Tuned after ranking among the strongest untuned groups by validation AP |
| G7 | None | Predeclared defaults with ten frozen AE latent features |

Table 3.2 makes clear that this is not an equal-budget architecture comparison. The resulting cross-group test differences are therefore interpreted descriptively rather than as isolated causal effects of autoencoding, resampling, or class weighting.

## 3.5 Detector Selection and Evaluation

Average Precision (AP) is the primary model-selection and reporting metric. The implementation computes it with scikit-learn's `average_precision_score`. Persisted experiment artifacts retain the legacy internal field name `auc_pr`, but the numeric value is AP rather than trapezoidal area under a precision-recall curve. Supporting metrics are ROC-AUC, precision, recall, F1, confusion counts, Precision@100, Recall@100, training time, and test inference time. Five-seed summaries use the mean and sample standard deviation.

G6 was frozen after validation-only comparison. The frozen parameters were max_depth 6, 500 estimators, learning_rate 0.2, subsample 1.0, colsample_bytree 0.7, and a training-derived scale_pos_weight. Its validation AP was 0.877447, and test results were not consulted in the freeze decision.

### 3.5.1 Validation-Based Threshold Selection

The decision threshold is chosen by maximising measured F1 on the validation precision-recall curve. The implementation accounts for the extra terminal precision and recall point returned by `precision_recall_curve`, which has no corresponding threshold. Once selected, the threshold is written into the metrics and manifest, and is applied unchanged to the test scores.

### 3.5.2 Evaluation Measures

AP and AUC-ROC are computed from continuous scores, whereas precision, recall, F1, and the confusion matrix are evaluated at the frozen validation-selected threshold. Precision@100 is the fraud proportion among the 100 highest scores, and Recall@100 is the proportion of all test frauds contained in those 100 alerts. Score ties are broken by stable sorting, so that repeated runs select the same ranked cases.

## 3.6 G4 Signed SHAP Reason Codes

G4 explains the frozen G6 seed-42 detector. The saved detector score and decision remain authoritative, with SHAP computed only for explanation. For every flagged case, the three largest signed contributions are ranked. Positive signed contributions are labelled as pushing toward fraud, and negative contributions are labelled as pushing toward legitimacy.

The reason-code record preserves the stable case ID, detector score, evaluation-only label, ranked feature identifiers, signed direction, and SHAP value. The operational analyst APIs later remove the historical label, although it remains available inside the research artifacts for retrospective evaluation.

G4 applies `TreeExplainer` to the exact saved XGBoost model and ordered feature list recorded in the G6 manifest. Local reason codes are generated for all 51 flagged test cases. Separately, global mean absolute SHAP importance is computed on a deterministic random sample of 2,000 complete seed-42 test rows using `random_state=42`. For each flagged case, the three non-zero contributions with the largest absolute magnitude are retained. Feature ranking is deterministic, and every reason-code record is validated against the corresponding flagged prediction by case ID rather than by row position.

## 3.7 G5 Local Narrative Experiment

The local LLM runs through Ollama on a loopback endpoint, and the final experiment used Ollama 0.31.1 with an immutable llama3:8b model digest. The evidence package contains only case ID, coarse risk bucket, ranked anonymised feature names, direction, and rank. The package excludes the raw transaction row, exact feature values, detector score or probability, historical label, and SHAP magnitude. The historical inclusion of case ID is retained as a disclosed protocol deviation from the later operational allowlist: the identifier was not required for language generation, and the current live serialiser removes it. The reported G5 results continue to describe the original frozen research payload rather than retroactively attributing the stricter live payload to that experiment.

Two prompt arms were evaluated. The strict prompt defined the accepted narrative rules, whereas the simple prompt retained the same general output objective without the detailed evidence constraints. For each arm and case, the exact raw model response was retained. That unmodified string was first analysed under the OFF policy and then submitted to the ON validate-or-fallback policy. No schema parser, normaliser, or renderer altered the text before validation.

Before the final experiment, preliminary pipeline-verification runs exercised eight of the 51 flagged cases. These runs are retained under experiments/tuning_runs, are marked as not reported, and contribute nothing directly to the rates in Section 4. The most recent preliminary run records the same strict and simple prompt hashes as the final experiment. Earlier runs predate prompt-hash logging, and the recorded artifacts therefore cannot establish prompt stability across the full development period. The overall G5 result is accordingly development-set-inclusive rather than a fully independent generalisation estimate. Section 4.5 reports a sensitivity split between the eight exposed cases and the 43 cases not used in preliminary runs.

### 3.7.1 Evidence Serialisation

The evidence serialiser converts the reason-code record into a compact textual contract. It includes the risk bucket and an ordered list such as `1. V14 - increases risk`. Exact values and attribution magnitudes are excluded because they are unnecessary for the narrative task and would enlarge the information exposed to the model.

### 3.7.2 Strict and Simple Prompt Arms

Both arms request the same high-level narrative structure. The strict arm specifies that every listed feature must appear exactly once, every direction must be explicit and unchanged, no unsupported features or numbers may be introduced, and the action statement must remain non-causal. The simple arm removes these detailed constraints while preserving the task and evidence. Temperature and runtime settings are held constant.

The full recorded prompt templates are reproduced in Appendix D. Their SHA-256 values are `34f7e5baa4e8562039e3b12db51a4d3fd5dc33af990c39e41f3f9c4410997381` for the strict arm and `761d56f6e29f5ee08d41a0985a1ada0b5d119f1818142e1fe90255b80d756d42` for the simple arm. These hashes are stored with the final G5 result, so that the wording used to produce the reported comparison can be checked independently of the current source file.

### 3.7.3 Paired OFF and ON Policies

The OFF-policy denominator is the set of raw LLM texts returned by successful Ollama API calls, whereas the ON-policy denominator is all requested cases, including any transport-failure fallbacks. Both denominators were 51 per arm in the final run because Ollama returned successfully for every request. The OFF policy measures the unmodified raw response without determining whether it would be released, while the ON policy passes that same string through the validator. A passing response is delivered; a failing response is replaced by deterministic reason codes. This paired design prevents stochastic regeneration from being confused with a guardrail effect.

## 3.8 Deterministic Guardrails and Fallback

The validator implements four separately reported checks. They are not statistically independent failure modes: completeness, grounding, and direction also fail when the required content sections cannot be parsed. The format check verifies the required NARRATIVE, EVIDENCE, and ACTION structure and rejects unauthorised numbers or malformed sections. The completeness check verifies that all required ranked evidence items appear in the expected order. The grounding check rejects unsupported or invented features and restricts the accepted language. The direction check verifies that every feature is described with the same signed direction as the SHAP reason code. A case is counted as a detected-any violation when at least one of the four checks fails.

Any failed check activates deterministic fallback. The fallback is generated from the bound reason-code record rather than from the rejected narrative. An Ollama transport failure also produces reason-code fallback, which allows the review workflow to continue without presenting an unavailable model call as a validator failure.

Appendix D specifies the accepted document structure, clause grammar, check dependencies, and fallback rule. The source implementation remains authoritative, while the appendix makes the measurement instrument inspectable from the submitted report.

## 3.9 Validator Calibration Protocol

Before the final G5 run, the validator was calibrated on a versioned 648-item corpus. The corpus contains 330 attacks across 15 categories, including direction flips, invented features, omitted evidence, template corruption, unauthorised numbers, and negation. It also contains 318 faithful controls across 17 template-compatible language categories. Wilson score intervals are reported for observed proportions because they remain well behaved at zero and one counts (Wilson, 1927).

The calibration corpus establishes measured behaviour only within that synthetic, template-constrained scope. It does not estimate the prevalence of real LLM errors, nor does it prove that all semantically faithful English will be accepted. The completed empirical evaluation therefore reports detected violations under the implemented validator and does not interpret those rates as the total semantic error rate.

### 3.9.1 Blinded Manual Semantic Audit

After the final G5 run, all 49 strict-arm narratives that passed the validator were placed in a provenance-bound audit sheet. Each row contained only the case identifier, prompt arm, serialised evidence, and delivered text. Raw rejected candidates, validator check results, fallback flags, and automated labels were withheld so that the reviewer judged the delivered narrative directly against its evidence rather than copying the system decision. The immutable row content was bound to the source G5 manifest by SHA-256 hashes.

The student manually reviewed every row for omission, unsupported evidence, reversed direction, and material format error. Human-only fields recorded a yes/no judgement, violation category where applicable, and optional notes. The scoring tool rejected incomplete labels, changed immutable fields, missing provenance, or absent human attestation, and reported the observed rate with a 95% Wilson interval. This is a blinded manual audit of the complete delivered strict-arm set, but it is not an independent multi-reviewer assessment and does not provide an agreement statistic.

## 3.10 Provenance and Reproducibility

Every detector run is driven by a versioned YAML configuration and writes a config snapshot, metrics, predictions, split summary, environment, model artifacts, and a manifest. G4 and G5 manifests bind their exact upstream run IDs and manifest hashes. The results pipeline uses an explicit allowlist rather than selecting a "latest" directory or glob match.

A scripted implementation audit traced the source chain from G6 seed 42 to G4, G5, aggregated results, figures, and the workbench. The audit re-derived selected metrics from stored predictions and compared the dataset and artifact hashes with their recorded manifests. These checks establish internal reproducibility and artifact consistency; they are not independent human or external validation.

Each manifest records the run identifier, group, seed, dataset hash, configuration hash, split summary, threshold, ordered feature names, upstream manifest references, relevant source hashes, Git revision, artifact hashes, and row counts. Final results are selected from an explicit allowlist of 30 detector runs, which prevents an accidental latest-directory selection from changing the reported evidence.

## 3.11 Fraud Alert Review Application

The delivered system is a local analyst decision-support prototype built with React, TypeScript, Vite, FastAPI, and SQLite. Its purpose is to support a repeatable alert-review task: the analyst inspects a model-flagged transaction, understands the recorded model evidence, verifies the delivered case brief, and records the next routing action. The application does not make the final fraud decision.

The application opens on one Alert Queue rather than a presentation dashboard. Navigation separates analyst Work from Model Evidence. The default queue view shows S0 Operational Simulation alerts because these cases contain readable evidence for the local-LLM evaluation. An All sources option and a Research benchmark filter keep the ULB evidence chain available in the same inbox. A visible Source column preserves the evidence namespace, and opening a row dispatches to the matching source-specific case route. Detector rank is shown only within its originating model because the two score scales are not comparable. Model Evidence presents S0 semantic and operational validation first, followed by the ULB detector comparison and anonymous-feature narrative-policy evidence. The interface states explicitly that every entity in the operational source is synthetic.

### 3.11.1 Recorded Evidence and Local Workflow State

The workbench uses a two-plane architecture. The immutable evidence plane contains detector predictions, thresholds, SHAP values, reason codes, recorded narratives, metrics, figures, and manifests. At startup, FastAPI loads exact artifact paths from `configs/dashboard.yaml`. It verifies and joins the ULB detector, G4, and G5 records by stable `case_id`, and independently validates the manifested S0 semantic run used by the operational routes. Wildcards and a `latest` selector are rejected. The application therefore cannot change reported evidence by silently selecting a newer run directory.

The separate workflow plane holds only the source namespace, `case_id`, status, provisional disposition, analyst note, revision, evidence fingerprint, and local activity events. The compound namespace-and-case key prevents an S0 operational case from sharing workflow state with a ULB research case that happens to have the same numeric identifier. The database does not store or modify model scores, labels, SHAP values, narratives, raw rows, or reported metrics. Every workflow write carries the revision last read by the browser, and a stale revision returns HTTP 409 instead of overwriting newer work. The evidence fingerprint also prevents a decision recorded against one snapshot from appearing current after the evidence changes.

The operational queue and case APIs do not expose retrospective ground truth. An analyst therefore reviews the detector decision and the explanation evidence without seeing the evaluation answer. Completed cases must be explicitly reopened before further changes can be made.

### 3.11.2 Analyst Pages and Routing Flow

The unified Alert Queue contains the 25 highest-scoring S0 test transactions, which are exactly the 25 above-threshold alerts in the frozen run, together with the 51 ULB seed-42 alerts. S0 rows show a synthetic transaction timestamp and amount, a readable leading model signal, relative review priority, delivery state, and analyst workflow status. Research rows retain their anonymous V1-V28 evidence. The High, Medium, and Low labels divide the already-flagged score range within a source and are not calibrated probabilities. Source, workflow-state, explanation-state, search, and sort controls allow the analyst to work from a single inbox without implying that S0 and ULB detector scores are interchangeable. A fallback filter isolates the two S0 cases with rejected LLM candidates.

![Figure 3.2. Unified Alert Queue presenting operational simulation and ULB research alerts in one analyst inbox. Source badges preserve the evidence namespace, while rank remains defined within each detector source.](reports/figures/workbench_queue.png)

As shown in Figure 3.2, source badges and within-source rank allow S0 and ULB alerts to appear in one queue without implying that their detector scores share a common scale.

Operational Case Review places the analyst action controls before the detailed evidence on narrower screens. It reports the frozen threshold, alert rank, readable signed SHAP contributions, coarse value buckets, synthetic amount and timestamp, and narrative delivery status. The page then presents four records side by side: raw SHAP reason codes, the complete deterministic renderer, the Ollama candidate, and the brief actually delivered to the analyst. When validation fails, the rejected candidate remains visible for audit, but the delivered panel shows deterministic fallback.

The local LLM note appears as a separate, subordinate record. The interface labels it as a bounded candidate that cannot add risk facts, change the ranking, choose the workflow action, or access identifiers and exact values removed from its payload. A distinct action panel records one of three provisional outcomes: escalate for investigation, close without escalation, or request additional information. These are workflow outcomes, not reconstructed ground-truth labels.

![Figure 3.3. Operational Case Review comparing readable SHAP reason codes, the deterministic renderer, the Ollama candidate, the delivered analyst brief, validation outcomes, and the minimised payload for one synthetic alert.](reports/figures/workbench_investigation.png)

Figure 3.3 shows the evidence hierarchy within a case: the SHAP-derived reasons and deterministic brief remain visible alongside the LLM candidate, validator outcome, and analyst-visible delivered output.

### 3.11.3 Narrative Service Boundary and Failure Handling

Recorded narratives remain available when Ollama is stopped because they belong to the frozen G5 artifact. Optional local regeneration is labelled temporary, excluded from reported G5 evidence, and not persisted to the case record. The live serialiser sends only the coarse risk bucket and the ranked feature directions, and it excludes the raw transaction row, exact feature values, detector probability, SHAP magnitudes, and historical label.

If Ollama is unavailable, the application returns deterministic reason-code fallback and continues the review workflow. When generated text fails format, completeness, grounding, or direction validation, the candidate is rejected and the same fallback is delivered. Explanation Assurance exposes these decisions with controlled mutations while leaving the recorded artifacts unchanged.

## 3.12 S0 Semantic and Operational Evaluation Track

S0 is the primary semantic and operational evaluation context because the ULB dataset's anonymised V1-V28 features cannot support business-readable alert explanations. The ULB detector benchmark and its reported results remain unchanged. S0 examines the explanation layer using readable current-transaction fields and historical features restricted to records available before scoring.

The synthetic stream is an independent local implementation informed by the documented design of the Fraud Detection Handbook simulator and the baseline feature-transformation chapters (Le Borgne et al., 2022). No handbook notebook code is copied into this repository. The registered configuration uses seed 42 to generate 50,000 transactions over 150 days from 1 January 2024, with 1,500 configured customers, 400 terminals, a 0.10 terminal-compromise rate, and a 0.015 burst-fraud rate. The frozen artifact contains 397 fraud transactions, equivalent to 0.794% prevalence, and records 1,492 observed customers and 400 terminals.

S0 uses chronological splitting rather than stratified random splitting. The training period contains 35,000 transactions and 303 frauds, the validation period contains 7,500 transactions and 49 frauds, and the test period contains 7,500 transactions and 45 frauds. The validation period selects the decision threshold by maximum F1, and the test period is evaluated only after that threshold is frozen.

Table 3.3. S0 semantic feature catalogue and operational meaning

| Feature | Analyst-facing meaning | Timing control |
|---|---|---|
| TransactionAmount | Current synthetic transaction amount | Current transaction field |
| AmountVsCustomer30Day | Amount relative to the customer's prior 30-day mean | Past-only customer history |
| CustomerTxCount1Day | Customer transaction activity in the previous day | Excludes current transaction |
| CustomerTxCount7Day | Customer transaction activity in the previous week | Excludes current transaction |
| MinutesSinceCustomerTx | Time since the customer's previous transaction | Uses only preceding event time |
| NewTerminalForCustomer30Day | Whether the terminal was absent from the customer's prior 30-day history | Past-only customer-terminal history |
| TerminalDistanceFromCustomerHome | Distance between synthetic customer and terminal profile locations | Static synthetic profiles |
| TerminalTxCount7Day | Terminal activity in the previous seven days | Excludes current transaction |
| TerminalFraudRisk7Day | Delayed seven-day terminal fraud rate | Seven-day label feedback delay |
| DuringNight | Transaction occurred from midnight through 06:00 | Current timestamp only |
| DuringWeekend | Transaction occurred on Saturday or Sunday | Current timestamp only |

Table 3.3 shows how each readable S0 feature is tied to a current field, past-only history, a static synthetic profile, or delayed label feedback. The S0 detector is a cost-sensitive XGBoost classifier that uses 160 trees, a maximum depth of 4, a learning rate of 0.05, subsample 0.9, column sampling 0.9, and the training-derived class weight. It produces a score for every transaction. The registered configuration selects the 25 highest-scoring test transactions for the explanation comparison. In this frozen run, the detector also flagged exactly 25 transactions at the validation-selected threshold, comprising 18 true positives and 7 false positives. The configured top-25 set is therefore identical to the complete above-threshold set for this run, with no flagged alert truncated and no below-threshold transaction admitted. This equality is a property of the frozen result, not of the general selection rule.

For each selected alert, S0 derives the top three signed SHAP contributions and compares three evidence presentations. The first is the raw reason-code list. The second is a deterministic brief generated directly from the feature catalogue, contribution directions, rank, and coarse value buckets. The third is a guarded local-LLM brief generated through Ollama with llama3:8b. The minimised LLM payload contains the relative review-priority bucket, three ranked evidence items (each containing rank, feature key, display label, direction, and coarse value bucket), and two complete summary options generated deterministically from the same evidence. One option names all three evidence items and the other names only the leading signal. The prompt requires the model to select one option exactly and to copy the structured evidence without alteration. It does not receive customer ID, terminal ID, transaction ID, exact amount, detector score or probability, historical label, or SHAP magnitude.

The Low, Medium, and High labels in S0 are relative review-priority buckets among transactions that have already exceeded the frozen threshold. They are not calibrated fraud-probability bands. The range between the frozen threshold and 1.0 is divided into three equal score-margin regions, so that the operational queue contains visible prioritisation without changing which cases are flagged.

The semantic validator is separate from the ULB narrative validator. It checks the structured format, the complete evidence set, grounding to the supplied fields, direction, order, risk-bucket consistency, the approved summary, and the absence of unauthorised numbers. A failed or unavailable LLM candidate falls back to the deterministic brief. The deterministic renderer therefore provides the trusted delivery baseline, while the guarded LLM remains an optional articulation layer.

## 3.13 Interim Human Evaluation

The artifact-level results measure validator decisions and structural properties of the delivered text, but they do not show whether a human reader can extract the intended evidence from each format. A small within-participant study therefore compared raw reason codes, the deterministic brief, and the guarded local-LLM brief using frozen S0 evidence. The registered target was 30 completed participants, with a pre-specified minimum of 18 if recruitment was interrupted. Eleven participants were included, so the study is reported as an interim pilot and analysed descriptively.

### 3.13.1 Ethics, Consent, and Participants

The study used synthetic alerts, requested no direct identifiers, and involved a short browser-based review task. Distribution began after the project owner reported supervisor approval. This report does not claim formal institutional ethics approval. A larger study, recruitment of professional analysts, collection of identifying or employment information, or any deployment-linked study would require the appropriate formal institutional review route before recruitment. Each participant read an information and consent statement, confirmed that they were at least 18 years old, and voluntarily agreed before the task items were shown. Participation could be stopped at any time.

Eleven adult proxy reviewers completed the form, and all met the implemented inclusion rules: valid consent and age confirmation, no duplicate response, and at least 70% of task blocks completed. No response was excluded, and disagreement with an expected answer was not an exclusion criterion. Eight participants reported a computing or information technology background, and three reported a business, finance, or accounting background. Machine-learning familiarity was none for two participants, basic for six, and intermediate for three. Fraud-domain familiarity was none for two and basic for nine. Prior exposure to SHAP was reported as yes by three participants, no by three, and not sure by five. The sample was not drawn from professional fraud analysts.

### 3.13.2 Design and Procedure

Every participant reviewed all three explanation formats. After one practice case, each reviewed nine synthetic S0 alerts: three as raw ranked reason codes, three as deterministic briefs, and three as guarded local-LLM briefs. The guarded condition used validator-accepted briefs so that rejected candidates and their fallback copies were not silently presented as LLM output.

Case-to-format assignment and presentation order were fixed for every participant. Each participant therefore saw three different cases per condition, but each format was always paired with the same cases and the same sequence position. This design keeps the stimulus set constant, yet it confounds explanation format with case difficulty and with order effects such as learning or fatigue. The study cannot attribute an observed difference to format alone.

Participant-facing stimuli were limited to a neutral case label, the relative review-priority bucket, evidence display labels, evidence directions, ranks, coarse value buckets, and the assigned explanation text. Internal identifiers, detector scores, thresholds, SHAP magnitudes, labels, outcomes, artifact paths, and validator-rejected candidate text were excluded.

### 3.13.3 Measures and Analysis

Three objective comprehension measures were recorded for every case: identification of the highest-ranked evidence item, of that item's contribution direction, and of the number of evidence items presented. Four subjective measures were recorded on five-point scales: clarity, confidence, evidence sufficiency, and mental effort, where a higher mental-effort score indicates greater effort. Participants also selected a provisional routing action and answered three overall preference questions covering the clearest format, the preferred first-pass format, and the most trustworthy format. Routing was not scored as fraud-decision correctness because retrospective ground truth was not shown.

Email collection was disabled, and no names, student identifiers, telephone numbers, or class marks were requested. The raw export was stored in an ignored private project location, while derived aggregate tables and figures were generated separately by a reproducible analysis script. Accuracy is reported as numerator, denominator, observed rate, and 95% Wilson interval for 33 task responses per format. Likert outcomes are reported as median and interquartile range, and preferences as counts out of 11 participants. No inferential test was run because recruitment remained below the pre-specified minimum, task responses were clustered within participants, and format was confounded with case and order. No optional free-text response was submitted, and therefore no qualitative coding was performed.

This pilot addresses evidence comprehension and format preference. It is distinct from the blinded manual semantic audit in Section 3.9.1, which checks whether validator-passing narratives preserve their supplied evidence but does not measure reader comprehension or format preference.

# 4. Results and Discussion

## 4.1 Data and Run Integrity

The source data contained 284,807 rows with 492 frauds. After documented deduplication, the modelling dataset contained 283,726 rows with 473 frauds. The final results set holds exactly 30 unique detector runs, six groups across five seeds. All required run manifests, metrics, thresholds, predictions, environments, and split assignments were available, and each passed the implemented leakage and provenance audits.

Table 4.1. Dataset integrity and seed-42 split counts

| Data stage | Transactions | Fraud cases | Fraud prevalence |
|---|---:|---:|---:|
| Source dataset | 284,807 | 492 | 0.1728% |
| After content deduplication | 283,726 | 473 | 0.1667% |
| Seed-42 training split | 198,608 | 331 | 0.1667% |
| Seed-42 validation split | 42,559 | 71 | 0.1668% |
| Seed-42 test split | 42,559 | 71 | 0.1668% |

As shown in Table 4.1, the seed-42 split preserved approximately the same fraud prevalence after deduplication across the training, validation, and test partitions. The dataset SHA-256 was `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`. Split audits confirmed disjoint stable case IDs and complete coverage of the data after deduplication. The detector leakage audit confirmed that scaling, AE fitting, and SMOTE drew on no validation or test observations.

## 4.2 Supporting Detector Benchmark

Table 4.2 reports the five-seed test results. G6 had the numerically highest mean AP at 0.855214, with G7, G2, and G0 close behind. G2 had the highest mean F1, and G7 the highest mean recall. These differences are descriptive; no logged significance test supports superiority language.

Table 4.2. Five-seed detector performance, reported as mean ± sample standard deviation

| Group | Test AP | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| G0 | 0.852891 ± 0.020896 | 0.930238 ± 0.059501 | 0.788732 ± 0.060580 | 0.850707 ± 0.026482 |
| G1 | 0.840457 ± 0.040837 | 0.946300 ± 0.031602 | 0.794366 ± 0.045202 | 0.863342 ± 0.036487 |
| G2 | 0.853707 ± 0.017449 | 0.937490 ± 0.039176 | 0.814085 ± 0.050193 | 0.870054 ± 0.026465 |
| G3 | 0.816870 ± 0.078987 | 0.904594 ± 0.062856 | 0.763380 ± 0.087619 | 0.824657 ± 0.054749 |
| G6 | 0.855214 ± 0.027097 | 0.955540 ± 0.040615 | 0.769014 ± 0.074262 | 0.849037 ± 0.031311 |
| G7 | 0.854767 ± 0.014410 | 0.925863 ± 0.043737 | 0.816901 ± 0.041063 | 0.866858 ± 0.024778 |

As shown in Table 4.2, G2 exceeded G0 by only 0.000816 in mean AP, which gives little evidence that reconstruction error materially improved discrimination. G3 fell 0.036021 below G0 and had the largest standard deviation, indicating lower and less stable performance under the reconstruction-error plus SMOTE configuration. G7 came close to the leading AP groups but did not establish a clear hybrid advantage.

Figure 4.1 presents the same five-seed comparison across several metrics. Panel a shows mean F1 with sample standard-deviation error bars, panel b the precision and recall trade-off, and panel c the resulting false-positive and false-negative burden. G2 had the highest mean F1, G6 the highest mean precision and the lowest mean false-positive count, and G7 the highest mean recall and the lowest mean false-negative count. No group led every measure.

For operations, G6 and G7 represent different review policies rather than a simple better-or-worse ordering. Across the five seeds, G6 combined precision 0.955540 ± 0.040615 and recall 0.769014 ± 0.074262 with 2.8 ± 2.775 false positives and 16.4 ± 5.273 false negatives per test run. G7 combined precision 0.925863 ± 0.043737 and recall 0.816901 ± 0.041063 with 4.8 ± 3.114 false positives and 13.0 ± 2.915 false negatives. At the reported validation-selected operating points, G6 would therefore place fewer false alerts in an analyst queue, while G7 would miss fewer fraud cases at the cost of additional review work. Because each seed used its own validation-selected threshold, these counts do not compare the models at one common cut-off. The appropriate choice depends on the relative cost of analyst capacity and missed fraud, and the recorded results do not establish either group as universally superior.

![Figure 4.1. Detector metric comparison across five fixed seeds. a, Mean test F1 with sample standard-deviation error bars. G6 is coloured separately because it is the frozen detector used downstream, not because it has the highest F1. b, Mean test precision and recall. c, Mean false-positive and false-negative counts with sample standard-deviation error bars. Each bar summarises n = 5 seeds. Source data: reports/tables/results_summary.csv.](reports/figures/detector_metric_bars.png)

Figure 4.1 shows that no detector dominated every operational measure: G6 reduced false-positive review burden, whereas G7 reduced missed fraud at the reported thresholds. Ranked-alert and runtime measures were also recorded for every run. Across the six groups, mean Precision@100 ranged from 0.598 to 0.606 and mean Recall@100 from 0.842 to 0.854. Appendix E reports the per-group mean and sample standard deviation for ROC-AUC, Precision@100, Recall@100, confusion counts, training time, and test inference time. Seed-level results and manifest identifiers remain available in full in the electronic project repository.

![Figure 4.2. Seed-42 precision-recall curves for the six detector groups. The curves are seed-specific and are not mean curves across five seeds.](reports/figures/pr_curves.png)

Figure 4.2 shows how precision and recall change as the score threshold moves; the curve itself was not used to select the final operating point from test evidence. For the frozen G6 seed-42 detector, the threshold of 0.989038 was chosen by maximum F1 on the validation precision-recall curve and then applied unchanged to the test split. In this highly imbalanced setting, such a high threshold admitted only the extreme upper tail of detector scores. On the untouched test split it produced 50 true positives and a single false positive, but it also left 21 of the 71 fraud cases below threshold. The resulting precision of 0.980392 and recall of 0.704225 therefore express an operational choice: a compact, low-noise alert queue obtained at the cost of missed fraud cases.

## 4.3 Frozen Detector and G4 Explanations

At the validation-selected threshold of 0.989038, the frozen G6 seed-42 detector reached test AP 0.820176, precision 0.980392, recall 0.704225, and F1 0.819672. It produced 50 true positives, one false positive, 21 false negatives, and 42,487 true negatives, so the threshold flagged 51 test cases.

Table 4.3. Frozen G6 seed-42 performance at the validation-selected threshold

| Measure | Frozen G6 seed-42 value |
|---|---:|
| Validation AP | 0.877447 |
| Test AP | 0.820176 |
| Test AUC-ROC | 0.977399 |
| Validation-selected threshold | 0.989038 |
| Precision | 0.980392 |
| Recall | 0.704225 |
| F1 | 0.819672 |
| True positives / false positives | 50 / 1 |
| False negatives / true negatives | 21 / 42,487 |

Table 4.3 records the frozen operating point and its resulting confusion counts. G4 generated one local reason-code record for each of the 51 flagged cases. In the separate 2,000-row global explanation sample, mean absolute SHAP importance ranked V14, V4, V12, V3, and V11 as the five highest features. V14 also ranked first in each of the 51 flagged-case evidence packages and appeared as an increasing-risk contribution in 50 of them. V10 appeared in 49 packages and V12 in 44, and 42 of the 51 packages contained the same V14, V10, and V12 trio in one of two rank orders. The repeated anonymous reason-code patterns are therefore a property of the frozen detector's concentrated attribution pattern on this dataset rather than an artefact introduced by the workbench interface. SHAP remains a non-causal model-attribution method, and the anonymised feature identifiers limit direct business interpretation.

![Figure 4.3. Global mean absolute SHAP importance for a random sample of 2,000 complete seed-42 test rows, selected with random_state=42. Importance describes the frozen model's attribution pattern, not causal fraud drivers.](reports/figures/shap_global_bar.png)

As shown in Figure 4.3, V14 has the largest global mean absolute SHAP importance, which helps explain why many flagged cases contain similar V14-led reason-code patterns.

## 4.4 Validator Calibration

The validator intercepted all 330 attacks in the versioned corpus, corresponding to 100% with a 95% Wilson interval of 98.85%-100%. It falsely rejected 0/318 faithful controls, corresponding to 0% with an interval of 0%-1.19%. Every individual attack category in the corpus had an observed interception rate of 100%.

Table 4.4. Validator calibration outcomes within the versioned synthetic corpus

| Calibration outcome | Count | Observed rate | 95% Wilson interval |
|---|---:|---:|---:|
| Attacks intercepted | 330/330 | 100% | 98.85%-100% |
| Attacks not intercepted | 0/330 | 0% | 0%-1.15% |
| Faithful controls accepted | 318/318 | 100% | 98.81%-100% |
| Faithful controls falsely rejected | 0/318 | 0% | 0%-1.19% |

As shown in Table 4.4, the validator intercepted all versioned attacks and accepted all faithful controls within the calibration corpus. These results are deliberately restricted to that synthetic corpus. A separate adversarial test constructed faithful English paraphrases that fell outside the accepted phrase grammar, and the validator rejected them. The calibration result therefore demonstrates consistency within a defined language contract, not universal natural-language understanding.

## 4.5 Paired Strict and Simple Prompt Results

The strict prompt produced 2/51 raw outputs with a detected-any violation (3.92%, 95% Wilson interval 1.08%-13.22%). Both failed outputs activated deterministic fallback, which left 49 delivered narratives. The simple prompt produced 51/51 outputs with a detected-any violation (100%, 95% Wilson interval 93.00%-100%), so all 51 activated fallback and no simple-arm narratives were delivered.

Because each case was generated once under each prompt, the detected-any outcome was also analysed as a paired binary comparison. Forty-nine cases passed under the strict prompt and failed under the simple prompt, no case showed the reverse pattern, and two cases failed under both. A two-sided exact McNemar test gave p = 3.55 x 10^-15. This supports a prompt-arm difference within this fixed model, evidence format, and case set; it does not establish a universal advantage for strict prompting.

Table 4.5. Strict and simple prompt outcomes under paired OFF and ON policies

| Outcome | Strict prompt | Simple prompt |
|---|---:|---:|
| Detected-any raw-output violation | 2/51, 3.92% [1.08%, 13.22%] | 51/51, 100% [93.00%, 100%] |
| Detected format violation | 2/51, 3.92% [1.08%, 13.22%] | 51/51, 100% [93.00%, 100%] |
| Detected completeness violation | 0/51, 0% [0%, 7.00%] | 2/51, 3.92% [1.08%, 13.22%] |
| Detected grounding violation | 2/51, 3.92% [1.08%, 13.22%] | 51/51, 100% [93.00%, 100%] |
| Detected direction violation | 2/51, 3.92% [1.08%, 13.22%] | 51/51, 100% [93.00%, 100%] |
| ON-policy fallback | 2/51, 3.92% [1.08%, 13.22%] | 51/51, 100% [93.00%, 100%] |
| Narratives delivered | 49/51 | 0/51 |
| Residual detected violation among delivered | 0/49 [0%, 7.27%], by construction | Not estimable, n=0 |
| Manual audit-estimated semantic violation among delivered | 0/49, 0% [0%, 7.27%] | Not estimable, n=0 |
| Transport unavailable | 0/51 [0%, 7.00%] | 0/51 [0%, 7.00%] |
| Mean generation-and-validation latency | 4.843 seconds | 4.556 seconds |

As shown in Table 4.5, the per-check rows are not additive and should not be read as separate error prevalences. In the strict arm, the same two outputs failed format, grounding, and direction while retaining complete evidence bullets. In the simple arm, all 51 candidates failed the required full structure and so could not be accepted by the grounding or direction parsers, although 49 still preserved the complete ordered evidence list. The 100% direction-check failure therefore does not mean that every simple narrative semantically reversed a SHAP direction; it means that none satisfied the validator's complete accepted direction contract.

Figure 4.4 separates three quantities that would otherwise be easy to conflate. The detected-any violation rate describes the raw text returned by Ollama. Fallback delivery describes how often the ON policy replaced that text. Accepted LLM narrative describes how often the generated candidate passed all implemented checks and was delivered without fallback. For the strict prompt, these rates were 3.92%, 3.92%, and 96.08%; for the simple prompt, they were 100%, 100%, and 0%.

![Figure 4.4. Narrative violation, fallback, and acceptance rates for the strict and simple prompt arms. Bars show the observed rate over n = 51 cases per arm. Error bars show 95% Wilson confidence intervals. Accepted LLM narrative is the complement of ON-policy fallback; it does not measure human-rated usefulness or undetected semantic error. Source data: the frozen G5 faithfulness artifact.](reports/figures/narrative_delivery_bars.png)

As shown in Figure 4.4, stronger prompt constraints changed deliverability for this model, prompt pair, evidence format, and 51-case set. This does not establish that strict prompting is generally superior across LLMs or tasks. The simple arm is a negative experimental result, not a usable delivery configuration.

The residual detected-violation value is 0/49 by construction, because the ON policy releases only narratives that pass all implemented checks. The separate blinded manual audit is not fixed by that policy: the student compared all 49 delivered strict-arm narratives with their serialised evidence and identified 0 semantic violations (0%, 95% Wilson interval 0%-7.27%). This provides direct evidence for the reviewed set, but the upper confidence bound and the single-reviewer design prevent a claim of zero general error. For sensitivity analysis, the strict arm had 0/8 outputs with a detected-any violation among development-exposed cases (0%, 95% Wilson interval 0%-32.44%) and 2/43 among previously unseen cases (4.65%, 95% Wilson interval 1.28%-15.46%). The split shows that the two final strict-arm failures occurred outside the preliminary case subset, but it does not remove the development exposure from the overall experiment.

The Wilson intervals in Table 4.5 summarise binomial uncertainty for the studied case set. The 51 cases are the complete flagged set of one fixed detector split, not an independent random sample of deployment alerts. The intervals do not account for prompt-development exposure, repeated evidence patterns, or distribution shift.

### 4.5.1 Worked Narrative Examples

Case 83417 illustrates an accepted strict-arm output. The supplied reason codes were V14, V12, and V10, all ranked as increasing risk. The exact generated text was:

```text
NARRATIVE: This case is rated High risk. The presence of V14, V12, and V10 all contribute to an increased risk.

EVIDENCE:
- V14 - increases risk
- V12 - increases risk
- V10 - increases risk

ACTION: Recommended for manual review.
```

All four checks passed, so the ON policy delivered the candidate unchanged. The example also shows the limit of the LLM layer. With anonymous features and a rule that forbids new facts, the generated sentence stays close to the reason-code input, and the system does not present that similarity as added analytical evidence. In the case-review interface, a deterministic evidence synthesis uses the detector order, signed SHAP magnitudes, and the balance of supporting and counter-signals to make the alert easier to triage. The LLM output is retained as a standardised review note whose delivery can be measured and controlled.

The two strict-arm rejections were cases 215132 and 154234. Both outputs retained all three ranked evidence bullets but omitted the required ACTION section and used narrative clause forms that fell outside the validator's accepted grammar. Case 215132 included the phrase `which increase the risk, outweighs the decrease in risk caused by V24`; case 154234 used repeated relative clauses such as `which also increases risk`. Their recorded check pattern was format = fail, completeness = pass, grounding = fail, and direction = fail. These are detected contract violations, not evidence that the semantic direction was necessarily reversed.

For each rejected case, the delivered text was generated from the original reason-code record rather than from the rejected prose. The fallback for case 215132, for example, began with `Risk level: High. Standardized reason codes:` and then listed V14 increases risk, V24 decreases risk, and V10 increases risk in rank order. That preserves the evidence while keeping the rejection visible.

## 4.6 Workbench and Guardrail Demonstration

The workbench keeps the research evidence read-only. Analyst actions cannot rewrite detector predictions, reason codes, generated candidates, validation results, manifests, or report artifacts. Status, disposition, notes, and activity live in a separate workflow database keyed by source namespace, case identifier, and evidence fingerprint, so an analyst can update the case record without changing the evidence used in the reported experiments.

Generated text is also subject to a fail-closed publication rule. A candidate becomes the official analyst brief only after the validator accepts it. If a check fails or local generation is unavailable, the candidate remains available for audit and the system builds the delivered brief deterministically from the source evidence. When the application loads recorded S0 evidence, it recomputes the validator outcome and rejects any artifact whose fallback flag, delivery label, or delivered brief conflicts with that policy. Neither an analyst action nor an inconsistent stored record can promote rejected LLM text into the formal brief.

The interface also keeps ULB and S0 separate, with different provenance labels, case namespaces, ranking contexts, and result sections. Queue position is calculated within the selected source, and the assurance pages do not merge the two sets of detector metrics into one ranking. Automated contract, route, provenance, workflow, and end-to-end tests support these claims for the local prototype. They do not establish production-grade access control, organisational deployment, or analyst productivity.

Three fixed scenarios demonstrate the operational boundary. The first uses S0 case 2365335092145894, transaction TX00045653, to show the normal accepted path: the analyst compares the raw signed SHAP reasons, deterministic brief, guarded local-LLM brief, delivered text, and validation results before recording a routing action. The second uses a recorded S0 fallback case or stops Ollama; recorded evidence remains available, while rejected or unavailable generation leads to deterministic reason-code fallback. The third applies a controlled mutation to an S0 structured candidate and runs the real validator.

Explanation Assurance presents the recorded candidate, the controlled mutation, each validation result, the policy verdict, and the fallback output. The layout separates the generated text from the code-based decision that controls delivery.

The Evaluation Results page presents S0 explanation-policy evidence first, including guarded local-LLM acceptance, fallback, latency, and validator calibration. The frozen ULB G6 seed-42 operating point, six-group detector comparison, precision-recall curves, confusion burden, and G5 anonymous-feature narrative-policy results follow as supporting benchmark evidence. The page states that the two detector studies are not directly comparable. Explanation Assurance defaults to the S0 structured validator, while the ULB research attack lab remains available through an explicit research mode.

![Figure 4.5. S0 Explanation Assurance with an unlisted-feature mutation. The grounding check fails while format, completeness, and direction remain passing, so the policy rejects the candidate and activates deterministic fallback.](reports/figures/workbench_narrative_assurance.png)

Figure 4.5 shows that an unlisted-feature mutation fails grounding and activates fallback without changing the recorded case. The controlled mutations also include a direction flip and template corruption. In the direction-flip scenario, the altered direction for Terminal distance from customer home fails only the direction check. The system rejects the candidate and displays the fallback that would reach the analyst. The test leaves the recorded S0 evidence and delivered brief unchanged.

![Figure 4.6. S0 direction-flip assurance test. The tampered contribution direction fails the direction check, while format, completeness, and grounding remain passing. The system rejects the candidate and activates deterministic fallback.](reports/figures/workbench_guardrail_failure.png)

As shown in Figure 4.6, the direction-flip mutation isolates the direction check while the other three checks remain passing. Verification outcomes are recorded in Appendix B.

<!-- pagebreak -->

## 4.7 S0 Semantic and Operational Evaluation Results

S0 generated 50,000 synthetic transactions from 1 January 2024 00:00:11 to 29 May 2024 23:56:13. The generated stream contained 397 fraud transactions, a fraud prevalence of 0.794%. Scenario 0 denotes non-fraud and accounted for 49,603 transactions. Scenario 1, burst fraud, accounted for 272 transactions, and scenario 2, terminal-compromise fraud, for 125. The dataset record hash was `824f50f80f75116d48e44db04777cf95e3c27b02597c7d91cc14381bf894834f`.

Table 4.6. S0 synthetic stream and chronological split counts

| Data stage | Transactions | Fraud cases | Fraud prevalence | Period |
|---|---:|---:|---:|---|
| Full S0 stream | 50,000 | 397 | 0.7940% | 2024-01-01 00:00:11 to 2024-05-29 23:56:13 |
| Training period | 35,000 | 303 | 0.8657% | 2024-01-01 00:00:11 to 2024-04-14 22:46:38 |
| Validation period | 7,500 | 49 | 0.6533% | 2024-04-14 22:48:43 to 2024-05-07 06:41:39 |
| Test period | 7,500 | 45 | 0.6000% | 2024-05-07 06:49:03 to 2024-05-29 23:56:13 |

As shown in Table 4.6, the chronological test period contained 7,500 transactions and 45 fraud cases, with a lower observed fraud prevalence than the training period. The S0 detector applied the validation-selected threshold 0.972929. Over the frozen test period it produced 18 true positives, 7 false positives, 27 false negatives, and 7,448 true negatives. Test AP was 0.544017, ROC-AUC was 0.960945, precision was 0.720000, recall was 0.400000, and F1 was 0.514286. These values describe the synthetic stream only. They are not directly comparable with the ULB benchmark because the data-generating process, feature space, prevalence, and split design all differ.

Table 4.7. S0 detector performance at the validation-selected threshold

| Measure | S0 seed-42 value |
|---|---:|
| Validation AP | 0.548381 |
| Test AP | 0.544017 |
| Test ROC-AUC | 0.960945 |
| Validation-selected threshold | 0.972929 |
| Precision | 0.720000 |
| Recall | 0.400000 |
| F1 | 0.514286 |
| True positives / false positives | 18 / 7 |
| False negatives / true negatives | 27 / 7,448 |

![Figure 4.7. S0 detector metrics on the synthetic operational test period. Source data: reports/tables/semantic_detector_metrics.csv.](reports/figures/semantic_detector_metrics.png)

Table 4.7 and Figure 4.7 show that the S0 operating point favoured precision over recall, producing 18 true positives and 7 false positives while leaving 27 fraud cases below threshold. The explanation comparison covered the 25 highest-scoring S0 test transactions, which in this frozen run are exactly the 25 above-threshold alerts. Their relative review-priority distribution was 7 High, 7 Medium, and 11 Low. These labels subdivide only the already-flagged score range and do not represent calibrated fraud probabilities. Each alert carried three ranked evidence items. Amount relative to the customer's 30-day average and terminal distance from the customer home profile appeared in all 25 evidence packages, night-time status in 14, transaction amount in 10, and delayed terminal fraud risk in one.

The semantic calibration corpus contained 150 attack cases and 40 faithful controls. The validator intercepted 150/150 attacks, corresponding to 100% with a 95% Wilson interval of 97.50%-100%, and accepted 40/40 faithful controls, corresponding to 100% with a 95% Wilson interval of 91.24%-100%. The attack categories were direction flip, invented evidence, missing evidence, reordered ranks, unauthorised number, and unknown summary claim. These rates apply only to the versioned semantic corpus and do not demonstrate universal semantic correctness.

Table 4.8. S0 explanation assurance outcomes

| Measure | Count | Observed rate | 95% Wilson interval |
|---|---:|---:|---:|
| Guarded LLM accepted | 23/25 | 92.00% | 75.03%-97.78% |
| Deterministic fallback | 2/25 | 8.00% | 2.22%-24.97% |
| Transport failure | 0/25 | 0.00% | 0.00%-13.32% |
| Calibration attacks intercepted | 150/150 | 100.00% | 97.50%-100.00% |
| Faithful controls accepted | 40/40 | 100.00% | 91.24%-100.00% |

![Figure 4.8. S0 explanation assurance outcomes. The deterministic fallback rate equals the validator failure rate for the selected 25 alerts because there were no transport failures. Source data: reports/tables/semantic_explanation_assurance.csv.](reports/figures/semantic_explanation_assurance.png)

As shown in Table 4.8 and Figure 4.8, the guarded LLM passed validation for 23/25 briefs and activated deterministic fallback for 2/25. Both rejected candidates returned only one structured evidence item, even though the minimised payload contained three ranked items, and both copied the rank-one evidence value bucket, `regional`, into the separate review-priority field. These two coupled defects caused all four reported checks to fail: the invalid review-priority value failed format, while the shortened evidence list caused the completeness, grounding, and direction comparisons to fail. The malformed candidates were retained for audit, and the deterministic brief was delivered as the analyst-facing output. The mean local Ollama request latency across the 25 calls was 21.932 seconds, measured before deterministic validation, and no transport failures occurred. The 25 delivered outputs contained zero validator-detected violations by construction, because the two rejected candidates were replaced by deterministic briefs.

Setting the three formats side by side shows how the model behaved within this unusually tight contract. For every case, the prompt offered two complete deterministic summary options: a detailed one naming all three evidence items, and a shorter one naming only the leading signal. All 23 accepted responses selected the shorter option. They therefore collapsed to two unique strings following the pattern `All supplied signals raise risk, led by X`, with Terminal distance from customer home selected in 16 cases and Amount vs customer 30-day average in 7. The accepted summaries averaged 12 words and named one evidence item, against 39.09 words and all three evidence items for the deterministic brief. The two responses that selected the detailed three-item option also corrupted the structured evidence and review-priority fields, so they were rejected and replaced by fallback. Because the prompt did not allow new evidence, this cannot be read as a failure to discover new evidence. It shows instead that, when the model was constrained to two evidence-bound renderings and otherwise satisfied the contract, it consistently delivered the less complete one. The positive result here is the delivery boundary: malformed candidates were detected and were not delivered as accepted analyst briefs.

Table 4.9. S0 deterministic and guarded-LLM brief comparison

| Structural measure | Deterministic brief | Accepted guarded-LLM summary |
|---|---:|---:|
| Evaluated accepted cases | 23 | 23 |
| Unique analyst-visible strings | 23 | 2 |
| Mean words | 39.09 | 12.00 |
| Mean characters | 297.91 | 76.09 |
| Mean named evidence items | 3.00 | 1.00 |

As shown in Table 4.9, the accepted guarded-LLM summaries were shorter and less varied than the deterministic briefs and named one rather than three evidence items on average. These artifact-level measurements describe the delivered text; human comprehension and preference are examined separately in Section 4.8.

## 4.8 Interim Human Evaluation Results

The interim human evaluation compared the three S0 explanation formats used in the application: raw SHAP reason codes, the deterministic brief, and the guarded local-LLM brief. Eleven adult participants completed the single-form protocol, all satisfied the implemented consent and completion rules, and none were excluded. The sample produced 99 completed case reviews, nine cases per participant and 33 task responses per format. It remained below the pre-specified minimum of 18 and target of 30, so the analysis is descriptive. No inferential test or significance claim is reported, and no participant submitted an optional free-text comment.

Participants were proxy reviewers rather than practising fraud analysts. Their self-reported backgrounds are summarised in Table 4.10.

Table 4.10. Interim human evaluation participant profile

| Characteristic | Category | Participants (n = 11) |
|---|---|---:|
| Background area | Computing or IT | 8 |
| Background area | Business, finance, or accounting | 3 |
| Machine-learning familiarity | None | 2 |
| Machine-learning familiarity | Basic | 6 |
| Machine-learning familiarity | Intermediate | 3 |
| Fraud-domain familiarity | None | 2 |
| Fraud-domain familiarity | Basic | 9 |
| Prior exposure to SHAP | Yes | 3 |
| Prior exposure to SHAP | No | 3 |
| Prior exposure to SHAP | Not sure | 5 |

As shown in Table 4.10, the sample was dominated by participants with computing or IT backgrounds and basic fraud-domain familiarity, so it should not be treated as a practising-analyst sample.

Each case contained three objective comprehension checks: identifying the leading evidence item, its contribution direction, and the number of evidence items presented. Table 4.11 reports the observed accuracy with 95% Wilson intervals.

Table 4.11. Interim human evaluation comprehension accuracy, n = 33 task responses per format

| Comprehension check | Raw reason codes | Deterministic brief | Guarded LLM brief |
|---|---|---|---|
| Leading evidence item | 28/33, 84.85% [69.08%, 93.35%] | 29/33, 87.88% [72.67%, 95.18%] | 27/33, 81.82% [65.61%, 91.39%] |
| Contribution direction | 28/33, 84.85% [69.08%, 93.35%] | 28/33, 84.85% [69.08%, 93.35%] | 26/33, 78.79% [62.25%, 89.32%] |
| Number of evidence items | 30/33, 90.91% [76.43%, 96.86%] | 26/33, 78.79% [62.25%, 89.32%] | 24/33, 72.73% [55.78%, 84.93%] |

Table 4.11 shows overlapping observed accuracy ranges across the three formats, with no comprehension check led by the guarded LLM brief.

Table 4.12 reports the five-point rating items as medians with interquartile ranges. Higher values are more favourable for clarity, confidence, and evidence sufficiency; for mental effort a higher value indicates more effort and is therefore less favourable.

Table 4.12. Interim human evaluation rating summaries, median [Q1, Q3] over 33 ratings per format

| Rating item | Raw reason codes | Deterministic brief | Guarded LLM brief |
|---|---|---|---|
| Clarity of presentation | 4 [3, 4] | 4 [3, 4] | 4 [4, 4] |
| Confidence in the review decision | 3 [3, 3] | 3 [3, 4] | 3 [3, 3] |
| Enough evidence to proceed | 3 [3, 4] | 4 [3, 4] | 3 [3, 4] |
| Mental effort required, higher is worse | 3 [3, 4] | 3 [3, 4] | 3 [3, 4] |

As shown in Table 4.12, median clarity was 4 for every format, while confidence and mental-effort medians were 3 across all three formats.

At the end of the session, participants answered three format-preference questions across all reviewed cases. Table 4.13 reports the counts. A no-preference option was available only for the clarity question.

Table 4.13. Interim human evaluation format preferences, n = 11 participants

| Preference question | Raw reason codes | Deterministic brief | Guarded LLM brief | No preference |
|---|---:|---:|---:|---:|
| Clearest overall presentation | 0 | 1 | 7 | 3 |
| Preferred format for a first pass | 1 | 3 | 7 | Not offered |
| Most trustworthy format | 1 | 6 | 4 | Not offered |

Table 4.13 shows that perceived clarity and first-pass preference favoured the guarded LLM brief, whereas trust favoured the deterministic brief. Participants also recorded a provisional routing action for each case. Because the workflow was blind to retrospective ground truth, these actions are workflow observations rather than correctness measures and are not scored here.

![Figure 4.9. Interim human evaluation outcomes for the three explanation formats. Values summarise 33 task responses per format from 11 proxy reviewers. Accuracy error bars are 95% Wilson intervals. The intervals treat task responses as independent and do not account for clustering within participants. Source data: reports/tables/human_eval_accuracy.csv and reports/tables/human_eval_likert.csv.](reports/figures/human_eval_outcomes.png)

![Figure 4.10. Interim human evaluation format preferences. Counts show how many of the 11 participants selected each format as clearest, preferred for first-pass review, and most trustworthy. Source data: reports/tables/human_eval_preferences.csv.](reports/figures/human_eval_preferences.png)

Figures 4.9 and 4.10 summarise a trade-off rather than a single winning format. All nine accuracy estimates fell between 72.73% and 90.91%, and the intervals overlapped across formats. The deterministic brief had the highest observed accuracy for identifying the leading evidence item, raw reason codes the highest for evidence count, and the guarded LLM brief the lowest point estimate on all three checks. Median clarity was 4 for every format, but only the guarded LLM brief had an interquartile range of [4, 4]. The deterministic brief was the only format with a median of 4 for evidence sufficiency, while confidence and mental-effort medians were 3 for all three formats. Seven participants selected the guarded LLM brief as clearest and seven selected it for first-pass review, whereas six selected the deterministic brief as most trustworthy.

These findings do not rank the formats. Every participant saw the same cases in the same sequence, and each format was paired with the same three cases, so format is confounded with case content and presentation order, and repeated responses are clustered within participants. Together with the small proxy-reviewer sample and the synthetic alert set, these limitations restrict the result to preliminary descriptive evidence.

## 4.9 Research Question Summary

Table 4.14. Research question summary

| RQ | Result supported by the completed study |
|---|---|
| RQ1 | In the ULB stress test, detected-any violations occurred in 2/51 strict outputs (3.92%, 95% Wilson interval 1.08%-13.22%) and 51/51 simple outputs (100%, 93.00%-100%); every detected failure activated fallback. The ULB validator intercepted 330/330 attacks and accepted 318/318 faithful controls within its versioned corpus. A blinded manual audit identified 0 semantic violations among the 49 delivered strict-arm narratives (0%, 95% Wilson interval 0%-7.27%). In S0, 2/25 candidates failed validation and were replaced. These results support fail-closed delivery under the tested contracts and reviewed case set, not universal semantic correctness. |
| RQ2 | Raw SHAP reason codes preserved ranked signed evidence, and the deterministic S0 brief preserved all three evidence items with no model latency. All 23 accepted guarded-LLM summaries selected the shorter permitted option, while the two detailed responses corrupted structured fields and were rejected. The interim human evaluation added evidence from 11 proxy reviewers and 99 case reviews. Observed comprehension accuracy did not favour the guarded LLM brief on any of the three checks, and the preference and trust responses pointed in different directions. The guarded local-LLM path therefore preserved the evidence boundary through validation and fallback, but it did not demonstrate added analyst detail or higher measured comprehension. |

As shown in Table 4.14, RQ1 is supported only within the tested validation and fallback contracts, while RQ2 records a bounded negative result for added detail and measured comprehension. The human evidence supporting RQ2 is interim and descriptive. Recruitment did not reach the pre-specified minimum of 18, no inferential test was run, and explanation format is confounded with case content and presentation order. The RQ2 result records what was observed under these conditions rather than a comparative ranking.

## 4.10 Supporting Detector Findings

The detector results do not support the original expectation that AE-derived features would clearly improve fraud detection. Reconstruction error produced a near-null AP difference relative to G0, and the reconstruction-error plus SMOTE configuration was lower and more variable. Latent features were competitive but stayed within the same narrow descriptive range as G0, G2, and G6.

G6 was a defensible frozen detector because it was selected using validation evidence under the documented protocol, but it should not be described as superior. Using the unrounded group means, its mean AP advantage over G0 was only 0.002324, and its mean recall of 0.769014 was below that of every other group except G3. The detector comparison should therefore be interpreted across multiple metrics rather than reduced to mean AP alone.

On this anonymised benchmark, the added autoencoder complexity did not produce a clear advantage. The imbalance-handling mechanisms also changed precision and recall in different ways, so no single score captures the full comparison. The strongest empirical contribution comes from the explanation-delivery experiment and its system boundaries.

## 4.11 Narrative-Layer Findings

In the final experiment, the strict prompt had substantially higher observed deliverability than the simple prompt. Only two strict outputs contained detected violations, whereas every simple output failed at least one check. The paired exact comparison indicates that prompt wording affected whether this model satisfied the fixed evidence contract for the studied 51 cases. The conclusion is limited to the recorded model, prompts, evidence format, and validator.

The guardrail's practical role is not to improve the rejected narrative. It prevents a detected failure from being delivered and replaces it with a deterministic representation of the original reason codes, which makes the fallback behaviour predictable and separates generation quality from delivery safety.

The calibration and implementation review reveal a trade-off. A predefined grammar is easier to test and supports fail-closed delivery, but it can reject semantically faithful paraphrases outside its phrase set. For this prototype, false rejection is an acceptable failure mode because fallback preserves the underlying evidence. The conclusions apply only to the restricted narrative contract, and the paraphrase probes in Section 4.4 show why the results should not be extended to unconstrained English.

The manual audit measures something different from validator calibration. None of the 49 delivered strict-arm narratives was judged to omit, invent, or reverse the supplied evidence, giving an observed rate of 0% with a 95% Wilson interval from 0% to 7.27%. Because one student reviewed the same fixed set of 49 cases, the audit reduces but does not remove the possibility of undetected semantic error.

The comparison with prior work is specific rather than universal. AlMarri et al. (2025) show that LLM self-explanations can diverge from SHAP attribution in financial tabular classification. This study takes a different route: the language model is not allowed to supply evidence, and its output is checked against a fixed SHAP-derived contract. Zytek et al. (2024) use an LLM narrator and an LLM grader in Explingo, whereas this project uses deterministic checks and deterministic fallback, so acceptance does not depend on a second generative model. Martens et al. (2025) report that narrative presentation can be persuasive. The interim human results in this study suggest that narrative form may feel clearer, but they also show that perceived clarity is not evidence of fidelity or improved comprehension.

## 4.12 Comparison with a Deterministic Renderer Baseline

A deterministic renderer is a strong baseline and may be the safer default for the current anonymised, fixed-template evidence. It is cheaper, faster, and guaranteed to stay within the reason-code contract. For that reason, the project does not treat the LLM as the only output path: deterministic reason codes are the trusted baseline and fallback.

The research question posed here is narrower. It asks whether an optional natural-language translation layer can be bounded and measured, not whether an LLM should replace deterministic formatting. The simple-arm result shows why the question needs measurement rather than assumption: when the evidence constraints were relaxed, all 51 raw outputs contained a detected violation. A workflow that used those narratives without validation would have delivered unchecked text. The contribution evaluated here is the measured delivery boundary, which remains useful whether or not the optional narrative layer is enabled.

The interim human comparison provides no evidence that accepted LLM narratives offer more analyst value than a deterministic renderer. Observed comprehension accuracy for the guarded LLM brief was at or below that of the deterministic brief on all three checks, while preference and trust responses diverged. These results distinguish perceived readability from trust and evidence retention. Accordingly, the deterministic renderer remains the trusted default, and the optional LLM layer is retained because its delivery can be bounded and measured, not because it was shown to improve comprehension.

## 4.13 Findings from the S0 Semantic and Operational Evaluation

S0 addresses a different limitation from the ULB benchmark. The ULB study provides continuity with the approved CP1 dataset and a controlled five-seed detector comparison, but its anonymous feature names restrict business interpretation. S0 instead uses one synthetic stream and one frozen seed with readable current-transaction fields and leakage-controlled historical features, among them amount relative to customer history, terminal distance, activity windows, and delayed terminal fraud risk.

S0 evidence can be checked directly against the synthetic transaction record. For example, `TerminalDistanceFromCustomerHome` with a `far_from_home` bucket either matches that record or it does not. An unsupported business interpretation of V14 cannot be checked in the same way against the ULB feature space. The difference comes from the readable feature design, not from the language model.

On the language layer, S0 is a negative result for added analyst detail. The deterministic renderer was faster and more complete in the measured artifact: it preserved all three evidence items and required no model request. The structured prompt offered the model two permitted summaries derived from the same evidence package, and all 23 accepted responses selected the shorter leading-signal option. Both responses that selected the detailed three-item option failed the surrounding structured-field contract and were replaced by fallback. The experiment measures constrained rendering preference and delivery compliance, not open-ended explanation generation. Under that contract, the model did not improve on the deterministic brief.

The 2/25 fallback result still shows why the delivery boundary matters. Both malformed outputs lost evidence items and confused an evidence value bucket with the separate review-priority field. The system delivered the deterministic brief rather than repairing or normalising either candidate, which preserves the distinction between untrusted generated text and the evidence accepted for analyst review.

The interim human evaluation supplies partial and mixed evidence on whether the optional LLM layer is worth retaining. The guarded LLM brief attracted the strongest clarity and first-pass preference counts, the deterministic brief attracted the strongest trust count, and observed comprehension accuracy did not favour the LLM brief on any check. Because the pilot used 11 proxy reviewers with fixed cases and ordering, it narrows the question rather than settling it.

Because S0 and ULB differ in data source, prevalence, split design, features, detector configuration, and case-selection process, the S0 results do not alter the ULB detector conclusion. They support only the narrower claim that the fail-closed explanation architecture can operate on a readable synthetic transaction stream while retaining a measurable boundary between candidate LLM text and delivered evidence.

This use of synthetic data follows the role described by Le Borgne et al. (2022): a reproducible transaction stream makes temporal feature construction and leakage boundaries inspectable. The present S0 implementation extends that role to explanation evaluation by attaching readable evidence labels and a chronological test period. It remains simulation evidence rather than a substitute for validation on a real operational stream.

## 4.14 Practical and Societal Implications

The practical result concerns delivery control rather than writing quality. Under the relaxed prompt, all 51 raw outputs contained a detected contract violation; under the constrained prompt, 2/51 did. Without validation, the first configuration would have released all of its unchecked text, and the system could not have distinguished it from compliant output. The implemented design instead applies a clear delivery rule. The same rule operated in S0, where 2/25 candidates were rejected and replaced by deterministic briefs.

The interim human results add an important qualification. Martens et al. (2025) report that narrative presentation can be persuasive. In this study, participants' readability preferences differed from their trust responses, and observed comprehension accuracy did not favour the LLM brief on any of the three checks. The deterministic renderer therefore remains the delivery baseline and the language layer remains optional. A format that reads easily is not necessarily the format an analyst should trust most. Because the cases and their order were fixed, this remains a descriptive observation.

The implemented system is a local single-user decision-support prototype backed by immutable, provenance-verified evidence. It is not a production banking control, a real-time prevention service, a multi-user case-management platform, or a compliance-certified system. The evaluation covered none of organisational security, drift, load, or prospective deployment.

## 4.15 Threats to Validity and Limitations

External validity is constrained by the data. The study uses one historical, anonymised dataset with PCA-like feature identifiers and no merchant, device, location, customer, or transaction-description semantics. A narrative stating that V14 increased risk is useful for testing attribution fidelity, but it is not equivalent to an explanation built on real operational fields. The detector comparison also carries an experimental asymmetry: only G2 and G6 received the 20-trial search, so the group comparison remains descriptive and cannot isolate the causal effect of each feature or imbalance mechanism. The seed-42 validation split was reused for XGBoost early stopping, hyperparameter selection, detector selection, and F1-threshold selection. Although the test split remained untouched until the configurations were frozen, the validation estimates may be optimistic because they are not independent of these repeated development decisions.

The narrative evidence is similarly narrow. G5 uses one local 8B model, one generation setting, two prompts, and the 51 flagged cases of one frozen seed-42 detector. Eight of those 51 cases appeared in preliminary pipeline runs, so the overall rate is development-set-inclusive. The sensitivity split found 0/8 detected violations among exposed cases and 2/43 among previously unseen cases, but the small counts do not support a generalisation claim. The results cannot be extended to other LLMs, prompts, datasets, or production alert distributions. Validator construct validity is also limited, because the calibration corpus was generated for the same closed language contract that the validator implements. Although the attacks cover 15 categories, the corpus remains synthetic and template-constrained. The confirmed false rejection of faithful out-of-corpus paraphrases shows that corpus performance is not universal language performance.

An interim analyst-facing usability pilot was completed, but its scope is narrow. It included 11 proxy reviewers rather than professional fraud analysts, remained below the pre-specified minimum of 18 and target of 30, and used only three cases per format for each participant. Case assignment and presentation order were fixed, so format is confounded with case content and sequence position. Task responses are also clustered within participants, so the reported Wilson intervals do not represent participant-level uncertainty. No inferential test was run, no free-text comment was submitted, and review time, decision quality, confidence calibration, and productivity were not measured. The pilot provides descriptive evidence about comprehension and preference, and it does not rank the three formats.

A blinded manual semantic audit of all 49 delivered strict-arm narratives found no violations against the supplied evidence, corresponding to 0% with a 95% Wilson interval of 0%-7.27%. This estimate is not by construction, but it was produced by one student reviewer without independent duplication, disagreement adjudication, or an agreement statistic. It therefore cannot establish that every accepted narrative is semantically correct in other cases, prompts, models, or reviewer populations. The usability pilot remains a separate study of clarity, comprehension, and preference. The project also does not evaluate fairness, drift, security, regulatory compliance, or system performance under load.

The S0 semantic evaluation adds readable evidence, but it also brings synthetic-data limits. Its customers, terminals, fraud scenarios, activity patterns, and labels were generated by an independent local implementation informed by the Fraud Detection Handbook design rather than observed in a bank. The chronological split is more suitable for a transaction stream than a random split, but it includes no purge gap. Validation and test features may use earlier historical transactions because those records would be available at scoring time; this remains a simplified representation of production history and delayed labels.

The S0 explanation comparison covers 25 selected alerts, one seed, one detector, one llama3:8b runtime, one structured prompt, and one semantic validator corpus. The 23/25 acceptance rate and 2/25 fallback rate measure the validator's contract decisions. They do not establish that an accepted LLM brief is clearer, faster to review, or more useful than the deterministic renderer. The interim pilot does not settle that question either, because it used synthetic alerts, proxy reviewers, and a confounded case-to-format assignment. The relative High, Medium, and Low labels also apply only within the already-flagged score range and must not be interpreted as calibrated fraud risk.

# 5. Conclusion and Future Work

## 5.1 Overall Conclusion

This project asked two questions. On RQ1, deterministic validation enforced a measurable fail-closed boundary under the tested contracts: detected violations occurred in 2/51 strict-prompt raw outputs (3.92%, 95% Wilson interval 1.08% to 13.22%) and in 51/51 simple-prompt outputs (100%, 93.00% to 100%); every detected failure activated deterministic fallback; and the ULB validator intercepted 330/330 corpus attacks while falsely rejecting 0/318 faithful controls. The zero residual detected rate among the 49 delivered narratives is a property of the delivery policy. Separately, a blinded manual review of those 49 narratives found 0 semantic violations (0%, 95% Wilson interval 0% to 7.27%), which is bounded evidence for the reviewed set rather than proof that no semantic error can survive.

On RQ2, the guarded local-LLM path preserved the evidence boundary but did not add analyst-facing detail. All 23 accepted S0 briefs selected the shorter permitted summary, naming one evidence item in a mean of 12 words against three items in 39.09 words for the deterministic brief. Both responses that selected the detailed option corrupted surrounding structured fields and were replaced by fallback. Across 11 proxy reviewers and 33 task responses per format, observed comprehension accuracy did not favour the guarded brief on any check, yet 7 of 11 selected it as the clearest and 6 of 11 selected the deterministic brief as the most trustworthy.

The findings can be considered in relation to the reviewed literature. AlMarri et al. (2025) show that LLM self-explanations can diverge from SHAP attribution. This study prevents that failure mode by treating SHAP-derived reason codes as the evidence and requiring the LLM output to satisfy a fixed contract. Zytek et al. (2024) assess free-text explanations with an LLM grader; the deterministic validator used here avoids relying on a second generative model, but the paraphrase probes in Section 4.4 show the cost of that choice, since faithful wording outside the predefined grammar can be rejected. The detector benchmark supports the explanation study but is not its main result. The autoencoder variants showed no clear advantage, and G6 was retained as a reproducible evidence source at mean test AP 0.855214 ± 0.027097, compared with 0.852891 ± 0.020896 for the baseline.

The usability evidence is interim. The pilot did not reach its pre-specified minimum of 18 participants, used proxy reviewers and synthetic alerts, and fixed the case assignment and presentation order. No inferential test was run.

The project contributes a verifiable explanation-delivery process, not a new fraud detector or an open-ended generative explanation method. ULB provides the real-data detector benchmark and anonymous-feature prompt stress test. S0 provides a readable semantic and operational evaluation, and the interim human study adds descriptive evidence on comprehension and preference. Across these parts, SHAP reason codes remain the evidence source, deterministic briefs remain the trusted baseline, and local-LLM briefs are delivered only after they satisfy an explicit evidence contract. The results demonstrate guarded explanation delivery in an operational simulation. They do not prove analyst usefulness, production readiness, or fraud-detection performance in a real bank.

## 5.2 Achievement of Objectives

Table 5.1 maps each stated objective to the completed evidence. The status terms are deliberately conservative: "met" means that the planned artifact and evaluation were completed, while "partially met" means that the implementation exists but the available human or external-validity evidence is not sufficient for the broader intended claim.

Table 5.1. Achievement of project objectives

| Objective | Status | Evidence and boundary |
|---|---|---|
| 1. Establish reproducible detector evidence | Met | Thirty leakage-controlled detector runs, validation-based freezing, stable case identifiers, manifests, predictions, and signed G4 SHAP reason codes were completed. The benchmark does not establish a new detector algorithm. |
| 2. Evaluate a local LLM under two prompt conditions | Met | The same 51 ULB cases were generated under strict and simple prompts with one local llama3:8b runtime. The result is scoped to this fixed model, evidence format, and case set. |
| 3. Separate raw violations, validator decisions, and fallback | Met | Exact raw outputs were preserved and measured before the validate-or-fallback policy. Detected failures were replaced without normalisation or repair. |
| 4. Calibrate deterministic validators before final evaluation | Met | The ULB and S0 validators were tested on versioned attack and faithful-control corpora. The results apply only to their predefined accepted grammars. |
| 5. Compare three explanation formats in a readable context | Partially met | Artifact comparison and an interim 11-participant pilot were completed. The pilot was below its minimum sample and used fixed cases and ordering, so it does not establish a causal format effect or analyst benefit. |
| 6. Deliver provenance-verified evidence through a local workbench | Met | The React and FastAPI application consumes immutable experiment artifacts, separates workflow state, exposes guardrail outcomes, and retains deterministic fallback. It remains a local prototype rather than a production banking system. |

As shown in Table 5.1, five objectives were met within their stated evidence boundaries, while the explanation-format comparison remained partially met because the human evaluation was interim and confounded.

## 5.3 Future Work

The priorities below follow directly from the limitations discussed in Sections 1.6 and 4.15.

The first priority is independent replication of the completed semantic audit. The present 49-row blinded review provides a student-annotated estimate, but future work should assign at least two independent reviewers, define an adjudication protocol, and report agreement alongside omission, grounding, and direction errors. This would test the stability of the 0/49 observation without treating either the validator or one reviewer as complete ground truth. The usability pilot remains complementary, because comprehension and preference ratings answer a different question from evidence-faithfulness review.

The validator should next be challenged with an independently authored corpus. The current calibration corpus is valuable for regression testing but was designed around the same closed contract as the implementation. A second corpus should be written without access to the validator's phrase lists, and should include faithful paraphrases, ambiguous coordination, negation, reordered clauses, and adversarial feature tokens. Results should separate attack interception from false rejection and should retain failure examples for qualitative analysis.

External validity should be extended through a second dataset with interpretable transaction fields and, if access permits, a prospective alert stream. That evaluation should include drift monitoring, fairness analysis, security and privacy threat modelling, concurrent workflow behaviour, load testing, and measured analyst outcomes. For the semantic evaluation, a separately authored synthetic or real transaction stream would reduce dependence on one generated stream, while an independently written validator corpus could test faithful paraphrases, missing-context ambiguity, reordered evidence, and realistic operational terminology. These studies are necessary before the prototype could support a production, regulatory, or organisational effectiveness claim.

# References

AlMarri, S., Ravaut, M., Juhasz, K., Marti, G., Al Ahbabi, H., & Elfadel, I. (2025). Measuring what LLMs think they do: SHAP faithfulness and deployability on financial tabular classification. *arXiv*. https://doi.org/10.48550/arXiv.2512.00163

Amershi, S., Weld, D., Vorvoreanu, M., Fourney, A., Nushi, B., Collisson, P., Suh, J., Iqbal, S., Bennett, P. N., Inkpen, K., Teevan, J., Kikin-Gil, R., & Horvitz, E. (2019). Guidelines for human-AI interaction. In *Proceedings of the 2019 CHI Conference on Human Factors in Computing Systems* (pp. 1-13). https://doi.org/10.1145/3290605.3300233

Bahnsen, A. C., Stojanovic, A., Aouada, D., & Ottersten, B. (2013). Cost sensitive credit card fraud detection using Bayes minimum risk. In *2013 12th International Conference on Machine Learning and Applications* (pp. 333-338). https://doi.org/10.1109/ICMLA.2013.68

Baisholan, N., Dietz, J. E., Gnatyuk, S., Turdalyuly, M., Matson, E. T., & Baisholanova, K. (2025). FraudX AI: An interpretable machine learning framework for credit card fraud detection on imbalanced datasets. *Computers*, 14(4), 120. https://doi.org/10.3390/computers14040120

Bello, M., Bello, R., García, M.-M., Nowé, A., Sevillano-García, I., & Herrera, F. (2025). A three-level framework for LLM-enhanced explainable AI: From technical explanations to natural language. *Information Systems Frontiers*. Advance online publication. https://doi.org/10.1007/s10796-025-10668-1

Černevičienė, J., & Kabašinskas, A. (2024). Explainable artificial intelligence (XAI) in finance: A systematic literature review. *Artificial Intelligence Review*, 57(8), Article 216. https://doi.org/10.1007/s10462-024-10854-8

Chawla, N. V., Bowyer, K. W., Hall, L. O., & Kegelmeyer, W. P. (2002). SMOTE: Synthetic minority over-sampling technique. *Journal of Artificial Intelligence Research*, 16, 321-357. https://doi.org/10.1613/jair.953

Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. In *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining* (pp. 785-794). https://doi.org/10.1145/2939672.2939785

Dal Pozzolo, A., Caelen, O., Johnson, R. A., & Bontempi, G. (2015). Calibrating probability with undersampling for unbalanced classification. In *2015 IEEE Symposium Series on Computational Intelligence* (pp. 159-166). https://doi.org/10.1109/SSCI.2015.33

Ding, L., Liu, L., Wang, Y., Shi, P., & Yu, J. (2024). An AutoEncoder enhanced light gradient boosting machine method for credit card fraud detection. *PeerJ Computer Science*, 10, e2323. https://doi.org/10.7717/peerj-cs.2323

Hajjami, S. E., & Diallo, G. (2025). SMOTE-OSBNR: An effective approach for imbalanced credit card fraud detection. *IEEE Access*, 13, 183503-183518. https://doi.org/10.1109/ACCESS.2025.3624961

Hancock, J., Khoshgoftaar, T. M., & Johnson, J. M. (2022). Informative evaluation metrics for highly imbalanced big data classification. In *2022 21st IEEE International Conference on Machine Learning and Applications (ICMLA)* (pp. 1419-1426). https://doi.org/10.1109/ICMLA55696.2022.00224

Hinton, G. E., & Salakhutdinov, R. R. (2006). Reducing the dimensionality of data with neural networks. *Science*, 313(5786), 504-507. https://doi.org/10.1126/science.1127647

Huang, L., Yu, W., Ma, W., Zhong, W., Feng, Z., Wang, H., Chen, Q., Peng, W., Feng, X., Qin, B., & Liu, T. (2025). A survey on hallucination in large language models: Principles, taxonomy, challenges, and open questions. *ACM Transactions on Information Systems*, 43(2), 1-55. https://doi.org/10.1145/3703155

Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., Bang, Y. J., Madotto, A., & Fung, P. (2023). Survey of hallucination in natural language generation. *ACM Computing Surveys*, 55(12), 1-38. https://doi.org/10.1145/3571730

Le Borgne, Y.-A., Siblini, W., Lebichot, B., & Bontempi, G. (2022). *Reproducible machine learning for credit card fraud detection - Practical handbook*. Université Libre de Bruxelles. https://github.com/Fraud-Detection-Handbook/fraud-detection-handbook

Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. In *Advances in Neural Information Processing Systems 30*.

Machine Learning Group - ULB. (n.d.). *Credit card fraud detection* [Data set]. Kaggle. https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud

Manakul, P., Liusie, A., & Gales, M. (2023). SelfCheckGPT: Zero-resource black-box hallucination detection for generative large language models. In *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing* (pp. 9004-9017). https://doi.org/10.18653/v1/2023.emnlp-main.557

Marazqah Btoush, E. A. L., Zhou, X., Gururajan, R., Chan, K. C., Genrich, R., & Sankaran, P. (2023). A systematic review of literature on credit card cyber fraud detection using machine and deep learning. *PeerJ Computer Science*, 9, e1278. https://doi.org/10.7717/peerj-cs.1278

Martens, D., Hinns, J., Dams, C., Vergouwen, M., & Evgeniou, T. (2025). Tell me a story! Narrative-driven XAI with large language models. *Decision Support Systems*, 191, 114402. https://doi.org/10.1016/j.dss.2025.114402

National Institute of Standards and Technology. (2024). *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile* (NIST AI 600-1). https://doi.org/10.6028/NIST.AI.600-1

Rebedea, T., Dinu, R., Sreedhar, M. N., Parisien, C., & Cohen, J. (2023). NeMo Guardrails: A toolkit for controllable and safe LLM applications with programmable rails. In *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing: System Demonstrations* (pp. 431-445). https://doi.org/10.18653/v1/2023.emnlp-demo.40

Rong, Y., Leemann, T., Nguyen, T.-T., Fiedler, L., Qian, P., Unhelkar, V., Seidel, T., Kasneci, G., & Kasneci, E. (2024). Towards human-centered explainable AI: A survey of user studies for model explanations. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 46(4), 2104-2122. https://doi.org/10.1109/TPAMI.2023.3331846

Weber, P., Carl, K. V., & Hinz, O. (2024). Applications of explainable artificial intelligence in finance: A systematic review of finance, information systems, and computer science literature. *Management Review Quarterly*, 74(2), 867-907. https://doi.org/10.1007/s11301-023-00320-0

Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association*, 22(158), 209-212. https://doi.org/10.1080/01621459.1927.10502953

Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. In *Advances in Neural Information Processing Systems 36* (pp. 46595-46623).

Zytek, A., Pido, S., Alnegheimish, S., Berti-Équille, L., & Veeramachaneni, K. (2024). Explingo: Explaining AI predictions using large language models. In *2024 IEEE International Conference on Big Data* (pp. 1197-1208). https://doi.org/10.1109/BIGDATA62323.2024.10825114

<!-- pagebreak -->

# Appendix A. Experiment and Evidence Map

Table A.1. Experiment and evidence map

| Reported claim | Primary evidence | Interpretation boundary |
|---|---|---|
| The detector benchmark is leakage-controlled and reproducible | Split summaries, manifests, leakage audit, implementation review | Implementation and audit claim |
| G6 has the numerically highest mean test AP | Five-seed results summary | Descriptive comparison only |
| AE-derived features show no clear advantage in this implementation | G0, G2, G3, and G7 five-seed results | Dataset- and protocol-specific finding |
| Strict prompting changes deliverability relative to the simple prompt | Final G5 faithfulness results | Limited to llama3:8b, the prompt pair, and 51 cases |
| The validator intercepted all attacks in the versioned corpus | Validator calibration artifact | Synthetic, template-constrained corpus only |
| Detected failures are not delivered as accepted narratives | G5 ON-policy artifacts | Delivery-policy property, not proof of universal semantic correctness |
| The workbench consumes the evaluated evidence chain | Dashboard validator, source manifests, no-write audit | Local single-user prototype claim |
| Local deployment minimises evidence sent to the LLM | Evidence serialiser and LLM client tests | Data-minimisation claim, not a formal privacy proof |
| S0 is the primary semantic and operational explanation context and remains separate from the ULB detector benchmark | Semantic evaluation specification and S0 run manifest | Synthetic operational evidence only; no ULB result is revised or directly compared |
| S0 uses readable transaction fields with leakage-controlled historical components | S0 configuration, feature catalogue, split summary, and source hashes | Operational simulation evidence, not real-bank validation |
| S0 detector performance | S0 metrics and semantic detector source table | Single-seed synthetic stream; not comparable with the ULB five-seed benchmark |
| S0 guarded LLM delivery outcomes | S0 explanation summary, comparison rows, and semantic assurance source table | Validator-detected delivery compliance only; human comprehension and preference are reported separately |
| S0 source attribution | Fraud Detection Handbook source record | Independent local implementation informed by documented concepts; no copied notebook code |
| Interim human evaluation sample and completed case reviews | `reports/human_eval_results.json` and participant-profile table | Eleven proxy reviewers and 99 case reviews; below the pre-specified minimum of 18 and target of 30 |
| Interim comprehension accuracy across three explanation formats | Human-evaluation accuracy table and Figure 4.9 | Descriptive only; 33 task responses per format, clustered within participants, with no inferential test |
| Interim ratings and preference distribution | Human-evaluation rating and preference tables, Figures 4.9 and 4.10 | Preference is not professional analyst acceptance, decision quality, or productivity evidence |
| Fixed case assignment and order limit the human comparison | Frozen participant form and study protocol | Format is confounded with case content and presentation order; no causal comparison |
| No qualitative human result was reported | Human-evaluation aggregate result, `free_text` field | No optional free-text response, quotation, or thematic coding |
| Blinded manual semantic audit found 0 violations among 49 delivered strict-arm narratives | Completed audit worksheet, bound manifest, human attestation, and `experiments/audit/audit_result.json` | Student-conducted single-reviewer estimate, 95% Wilson interval 0%-7.27%; no inter-rater agreement or universal correctness claim |

Table A.1 shows that each reported claim is paired with primary evidence and an explicit interpretation boundary.

# Appendix B. Software and Reproducibility Summary

Table B.1. Software and reproducibility summary

| Component | Implemented technology or artifact |
|---|---|
| Detector pipeline | Python, pandas, scikit-learn, imbalanced-learn, XGBoost |
| Autoencoder | TensorFlow and Keras |
| Attribution | SHAP TreeExplainer |
| Local narrative runtime | Ollama 0.31.1 with llama3:8b |
| Backend | FastAPI with Pydantic validation |
| Frontend | React, TypeScript, Vite |
| Workflow persistence | Namespaced local SQLite database containing workflow metadata only |
| Detector evidence | 30 allowlisted runs with manifests, metrics, predictions, split assignments, models, and environments |
| Explanation evidence | G4 signed reason codes and global SHAP artifacts for 51 flagged cases |
| Narrative evidence | G5 strict/simple raw outputs, validator decisions, fallback outcomes, and Wilson intervals |
| Report bar charts | Reproducible Python script with detector summary CSV and frozen G5 faithfulness JSON as source data |
| S0 synthetic stream | Independent Fraud Detection Handbook-inspired generator, seed 42, 50,000 transactions |
| S0 semantic detector | Cost-sensitive XGBoost over 11 readable current-transaction fields and leakage-controlled historical components |
| S0 explanation comparison | Raw SHAP reason codes, deterministic brief, guarded local-LLM brief, and deterministic fallback |
| S0 semantic validator | Versioned 190-item corpus with 150 attacks and 40 faithful controls |
| S0 provenance | Manifest binding dataset, configuration, prompt, validator, corpus, Ollama identity, split boundaries, source files, and output artifacts |
| Interim human evaluation | Frozen participant form, private raw snapshot, reproducible aggregate analysis, Wilson intervals, rating summaries, and preference counts |
| Verification | 222 Python tests, twelve frontend component tests, eleven Playwright tests, ESLint, production build, ULB and S0 artifact validation, and 21-artifact no-write audit |

Table B.1 summarises the implemented software and the artifact types retained for reproducibility. The source dataset hash is `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`. The final narrative experiment records the exact local model digest `365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1`. Downstream manifests identify their source runs by run ID and manifest hash, allowing the frozen G6 detector, G4 explanations, G5 narratives, aggregated results, figures, and workbench configuration to be traced as one evidence chain.

The frozen S0 run is `2026-07-26_s0_seed42`, with run-manifest SHA-256 `bbc18d3720b5a751568b44b45553b100da1ed229ac08443bceb8e4a3f12645c5`. `reports/semantic_results_manifest.json` binds the semantic source tables and exported figures to that run and to the exact metrics, explanation summary, and calibration hashes. The directory named `2026-07-26_s0_seed42_superseded-risk-bucket` is retained only as an audit record and is not used by the application or report.

# Appendix C. Application Startup and Demonstration

The following commands reproduce the local application from the repository root:

```bash
uv python pin 3.12 && uv sync
uv run python tools/check_data.py
cd app/frontend && npm ci && npm run build && cd ../..
uv run python tools/validate_dashboard.py --config configs/dashboard.yaml
uv run python -m app.backend.server --config configs/dashboard.yaml
```

The server binds to `127.0.0.1:8000`. `tools/validate_dashboard.py` checks the configured source chain without starting the web server and reports the case count, narrative arm, source-chain status, and bound run identifiers.

The application opens on `/queue`, which combines S0 operational simulation and ULB research alerts in one source-labelled inbox. The legacy `/operational/queue` and `/research/queue` links redirect to the same queue with the corresponding Source filter applied. `/assurance/performance` presents both studies with an explicit non-comparability boundary. `/assurance/narratives?mode=operational` demonstrates the S0 structured validator, while the research guardrail evidence remains available through the recorded benchmark mode.

Optional live generation requires Ollama in a separate terminal:

```bash
ollama serve
ollama pull llama3:8b
```

The demonstration follows three fixed scenarios:

1. Accepted S0 case brief: open `/queue`, filter Source to Operational simulation, start the first accepted case, inspect the detector and signed SHAP evidence, compare the deterministic and guarded summaries, confirm that all four narrative checks pass, and record a provisional routing action.
2. Narrative service unavailable: stop Ollama, request live regeneration, and show that the application returns `llm_transport_unavailable` with deterministic reason-code fallback while recorded evidence and workflow controls remain usable.
3. Guardrail rejection: open Explanation Assurance in operational mode, select S0 case 2365335092145894, apply the direction-flip mutation, and show the failed direction check, rejection verdict, and fallback output.

<!-- pagebreak -->

# Appendix D. Prompt Templates and Validator Contract

## D.1 Recorded Strict Prompt

The final strict-arm prompt had SHA-256 `34f7e5baa4e8562039e3b12db51a4d3fd5dc33af990c39e41f3f9c4410997381`. The `{evidence}` placeholder was replaced by the serialised case evidence without any other prompt transformation.

```text
You are a fraud-analyst assistant. Translate the supplied evidence into a concise narrative.

Return ONLY plain text in this exact template. Do not use Markdown fences, headings before NARRATIVE, or Unicode bullets:
NARRATIVE: This case is rated <High|Medium|Low> risk. <one evidence sentence>
EVIDENCE:
- <feature> - <increases risk|decreases risk>
ACTION: Recommended for manual review.

STRICT RULES:
- Mention ONLY the features listed in the evidence. Never introduce other features or reasons.
- Mention every listed feature exactly once in the narrative sentence.
- Include every listed feature exactly once in EVIDENCE and preserve rank order.
- Keep each feature's direction exactly as stated (increases risk / decreases risk).
- Keep the stated overall risk level unchanged.
- Do not state exact numbers, probabilities, or feature values.
- Join feature-direction clauses only with commas, semicolons, "and", "while", "but", or "whereas".
- Give every feature an explicit direction and do not add explanations.

Evidence:
{evidence}
```

## D.2 Recorded Simple Prompt

The final simple-arm prompt had SHA-256 `761d56f6e29f5ee08d41a0985a1ada0b5d119f1818142e1fe90255b80d756d42`.

```text
You are a fraud-analyst assistant. Explain why this transaction was flagged from the supplied evidence.

Return ONLY plain text in this exact template. Do not use Markdown fences, headings before NARRATIVE, or Unicode bullets:
NARRATIVE: This case is rated <High|Medium|Low> risk. <one evidence sentence>
EVIDENCE:
- <feature> - <increases risk|decreases risk>
ACTION: Recommended for manual review.

Evidence:
{evidence}
```

The simple prompt is intentionally not an unconstrained chat prompt. It retains the same requested output shape and evidence package so the arms differ primarily in the explicit evidence-preservation rules.

## D.3 Accepted Document and Clause Grammar

The validator strips outer whitespace and applies the following document-level contract:

```text
document := "NARRATIVE: " narrative NEWLINE NEWLINE
            "EVIDENCE:" NEWLINE evidence_bullets NEWLINE
            "ACTION: Recommended for manual review."

narrative := risk_sentence SPACE evidence_sentence
risk_sentence := "This case is rated " <High|Medium|Low> " risk."
evidence_sentence := [first_clause_prefix] clause (separator clause)* "."
clause := feature_list ["also"|"all"] direction_phrase ["for this transaction"]
feature_list := feature | feature ("," feature)* [", and" feature] | feature "and" feature
separator := comma | semicolon | "and" | "while" | "but" | "whereas"
evidence_bullet := "- " feature " - " <increases risk|decreases risk>
```

The accepted first-clause prefixes are empty, `both`, `together`, `overall`, `the presence of`, or `this case is rated <level> risk due to`, with the punctuation variants implemented in the source. Accepted direction phrase families are increases or raises risk, decreases or lowers risk, and contributes to increased or decreased risk, including the implemented article, inflection, and `the risk` variants. Neutral phrases such as `is relevant to risk` may be parsed for grounding but do not satisfy the direction check.

The feature vocabulary comes from the bound detector feature list. A V-number token or underscore-form feature token outside the case evidence fails grounding. After known feature identifiers are scrubbed, any remaining integer, decimal, signed number, or percentage fails format. The complete source implementation is recorded by hash in the G5 manifest.

## D.4 Check and Fallback Semantics

The four reported checks operate as follows:

1. **Format:** requires the complete document structure, exactly two narrative sentences, parseable evidence bullets, and no unauthorised numbers.
2. **Completeness:** requires the evidence bullets in reason-code rank order and requires every expected feature to appear in the narrative.
3. **Grounding:** requires parseable content sections, only allowed features, the exact risk bucket, and narrative clauses within the accepted grounding grammar.
4. **Direction:** requires the evidence bullets to match the ordered feature-direction pairs and requires every narrative feature to have the corresponding explicit direction.

Completeness, grounding, and direction depend on successful content-section parsing, so the checks are separately implemented but not independent failure modes. `Detected-any violation` means that at least one check returned false. The delivery decision is the conjunction of all four checks. Any failure returns deterministic reason-code fallback generated from the bound record; rejected model text is never used to construct the fallback.

## D.5 S0 Structured Prompt and Summary Options

The S0 semantic and operational evaluation uses a separate JSON contract. The prompt is reproduced below because its design determines what the S0 language-layer result can and cannot mean.

```text
Return only one JSON object with exactly the keys risk_bucket, summary, evidence, action.
Copy risk_bucket and evidence exactly from case_evidence. Set action to manual_review.
Set summary to exactly one string from allowed_summary_options. Do not add keys, facts,
identifiers, or exact numbers.
{payload}
```

The serialised payload contains `case_evidence` and `allowed_summary_options`. The first permitted summary is a detailed deterministic sentence naming all three ranked evidence items, value buckets, and directions. The second is a shorter deterministic relationship sentence naming only the leading signal. The semantic validator requires the returned summary to match one of these two options exactly. Consequently, this experiment evaluates option selection, structured-field copying, validator decisions, and fallback delivery. It does not evaluate open-ended narrative discovery or the model's ability to introduce additional fraud knowledge.

<!-- pagebreak -->

# Appendix E. Supporting Detector Results

Table E.1. Supporting detector ranking metrics, reported as mean +/- sample standard deviation across five seeds

| Group | Test ROC-AUC | Precision@100 | Recall@100 |
|---|---:|---:|---:|
| G0 | 0.975011 +/- 0.009049 | 0.606000 +/- 0.008944 | 0.853521 +/- 0.012598 |
| G1 | 0.972330 +/- 0.008128 | 0.598000 +/- 0.027749 | 0.842254 +/- 0.039083 |
| G2 | 0.976282 +/- 0.008116 | 0.606000 +/- 0.005477 | 0.853521 +/- 0.007714 |
| G3 | 0.974185 +/- 0.006540 | 0.602000 +/- 0.030332 | 0.847887 +/- 0.042720 |
| G6 | 0.977474 +/- 0.005915 | 0.606000 +/- 0.011402 | 0.853521 +/- 0.016059 |
| G7 | 0.977322 +/- 0.007290 | 0.606000 +/- 0.005477 | 0.853521 +/- 0.007714 |

As shown in Table E.1, the six groups produced closely clustered ranked-alert metrics, with mean Precision@100 between 0.598 and 0.606 and mean Recall@100 between 0.842 and 0.854.

Table E.2. Supporting detector confusion counts and runtime, reported as mean +/- sample standard deviation across five seeds

| Group | TP | FP | FN | TN | Train seconds | Test inference seconds |
|---|---:|---:|---:|---:|---:|---:|
| G0 | 56.0 +/- 4.301 | 4.6 +/- 4.722 | 15.0 +/- 4.301 | 42,483.4 +/- 4.722 | 0.964 +/- 0.340 | 0.00608 +/- 0.00215 |
| G1 | 56.4 +/- 3.209 | 3.2 +/- 1.924 | 14.6 +/- 3.209 | 42,484.8 +/- 1.924 | 2.186 +/- 0.822 | 0.01169 +/- 0.00549 |
| G2 | 57.8 +/- 3.564 | 4.0 +/- 2.739 | 13.2 +/- 3.564 | 42,484.0 +/- 2.739 | 0.993 +/- 0.356 | 0.00650 +/- 0.00255 |
| G3 | 54.2 +/- 6.221 | 6.0 +/- 4.301 | 16.8 +/- 6.221 | 42,482.0 +/- 4.301 | 1.999 +/- 1.371 | 0.01018 +/- 0.00732 |
| G6 | 54.6 +/- 5.273 | 2.8 +/- 2.775 | 16.4 +/- 5.273 | 42,485.2 +/- 2.775 | 0.946 +/- 0.126 | 0.00634 +/- 0.00086 |
| G7 | 58.0 +/- 2.915 | 4.8 +/- 3.114 | 13.0 +/- 2.915 | 42,483.2 +/- 3.114 | 1.832 +/- 0.685 | 0.01130 +/- 0.00343 |

As shown in Table E.2, the confusion counts reflect each seed's validation-selected threshold rather than a common test threshold. Runtime was measured on the project machine and is reported for reproducibility, not as a hardware-independent performance benchmark.
