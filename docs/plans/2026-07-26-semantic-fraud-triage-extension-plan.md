# Semantic fraud triage extension implementation plan

## Phase 1: protect and specify

1. Preserve the existing submission report and builder with hashes.
2. Record the extension specification and official-source attribution.
3. Ask Claude Opus for an independent research-design and report-drafting pass.

## Phase 2: semantic experiment

1. Add a deterministic synthetic transaction generator.
2. Add past-only customer and terminal feature engineering.
3. Add a chronological 70/15/15 split and cost-sensitive XGBoost runner.
4. Produce SHAP reason codes and a semantic evidence catalogue.
5. Produce raw, deterministic, and guarded local-LLM explanation outputs.
6. Seal results and provenance in an S0 run directory.

## Phase 3: workbench

1. Add an optional semantic snapshot to the FastAPI backend.
2. Expose semantic queue, case-detail, and explanation-comparison endpoints.
3. Default the React workbench to the operational simulation while retaining the
   anonymous benchmark as a research view.
4. Add explicit synthetic-data and local-LLM boundaries.

## Phase 4: evidence and report

1. Generate semantic detector and explanation-comparison figures.
2. Update the report only with values read from sealed artifacts.
3. Run an Opus adversarial review and correct confirmed findings.
4. Apply the humanizer process without changing claims, numbers, or citations.
5. Rebuild and visually inspect DOCX and PDF output.

## Verification

- targeted unit and contract tests;
- full Python suite;
- frontend unit tests, lint, production build, and Playwright suite;
- manifest and hash validation;
- recorded and Ollama-unavailable application smoke tests;
- complete report rebuild and page rendering.
