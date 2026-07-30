# Prior-work comparison audit for Table 2.2

Date checked: 29 July 2026

Purpose: record the evidence used to code the four delivery-boundary properties in Table 2.2 of the CP2 report. The comparison describes the evaluated design reported by each source. `Not reported` means that the property was not described as part of that evaluated design; it is not proof that no related implementation exists elsewhere.

## Coding definitions

- **Deterministic code-level validator:** acceptance is decided by reproducible program logic rather than an LLM grader.
- **Fail-closed deterministic fallback:** rejected or unavailable generated text is withheld and replaced by a deterministic explanation derived from the source evidence.
- **Local narrative-model execution:** the evaluated narrative-generation model runs locally rather than through an external hosted API. A recommendation or a secondary feasibility probe is coded `Partial`.
- **Raw and delivered output measured separately:** the same candidate generation is retained and measured before the delivery policy, with post-policy delivery or fallback reported separately.

## Source checks

### AlMarri et al. (2025)

Source: AlMarri, S., Ravaut, M., Juhasz, K., Marti, G., Al Ahbabi, H., and Elfadel, I. (2025). *Measuring what LLMs think they do: SHAP faithfulness and deployability on financial tabular classification*. https://doi.org/10.48550/arXiv.2512.00163

- The Models and Inference section reports four open-source models with local inference through vLLM on two NVIDIA A10G GPUs.
- The evaluated study compares LLM self-explanations with SHAP attribution.
- No deterministic narrative validator, deterministic delivery fallback, or paired raw-versus-delivered measurement is reported as part of the evaluated design.
- Table coding: `Not reported`, `Not reported`, `Yes`, `Not reported`.

### Zytek et al. (2024)

Source: Zytek, A., Pido, S., Alnegheimish, S., Berti-Équille, L., and Veeramachaneni, K. (2024). *Explingo: Explaining AI predictions using large language models*. https://doi.org/10.1109/BIGDATA62323.2024.10825114

- Explingo evaluates narratives with an independent GPT-4o grader, so its acceptance mechanism is not deterministic code-level validation.
- The paper describes an optional threshold that can reject an unacceptable narrative and revert to the default graph-based explanation. This is relevant fallback behaviour, but the gate is an LLM score rather than a deterministic validator.
- The main narrator experiments use the GPT-4o API. A smaller local Mistral-7B experiment is reported separately as a feasibility step and gives weaker accuracy and completeness results.
- The study does not report paired measurement of the same raw candidate before and after a delivery policy.
- Table coding: `No`, `Partial`, `Partial`, `Not reported`.

### Bello et al. (2025)

Source: Bello, M., Bello, R., García, M.-M., Nowé, A., Sevillano-García, I., and Herrera, F. (2025). *A three-level framework for LLM-enhanced explainable AI: From technical explanations to natural language*. https://doi.org/10.1007/s10796-025-10668-1

- The framework recommends on-premise LLMs for privacy-sensitive settings.
- The reported case studies use GPT-4.5 illustratively, and the authors describe the framework as a conceptual foundation requiring empirical validation.
- A deterministic code-level validator, fail-closed deterministic delivery, and separate raw-versus-delivered measurement are not reported in the evaluated examples.
- Table coding: `Not reported`, `Not reported`, `Partial`, `Not reported`.

### Martens et al. (2025)

Source: Martens, D., Hinns, J., Dams, C., Vergouwen, M., and Evgeniou, T. (2025). *Tell me a story! Narrative-driven XAI with large language models*. https://doi.org/10.1016/j.dss.2025.114402

- The implementation uses GPT-4 through API calls for its narrative generation experiments.
- The study investigates narrative presentation and user responses rather than a guarded delivery mechanism.
- No deterministic code-level validator, deterministic fallback, or paired raw-versus-delivered measurement is reported as part of the evaluated design.
- Table coding: `Not reported`, `Not reported`, `No`, `Not reported`.

### This project

- Deterministic validators implement explicit format, completeness, grounding, and direction checks.
- Delivery fails closed to a deterministic brief when generation is unavailable or any implemented check fails.
- The recorded narrative experiments use local Ollama with a manifested model digest.
- Raw candidate outputs are retained and measured separately from ON-policy delivered narratives or fallback.
- Table coding: `Yes`, `Yes`, `Yes`, `Yes`.

## Permitted conclusion

Within the reviewed literature, no compared study evaluated all four properties together. This wording is a bounded comparison claim. It must not be shortened to an unqualified claim that the project is the first system to do so.
