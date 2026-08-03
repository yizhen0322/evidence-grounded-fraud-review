# Evidence-Grounded Local-LLM Explanations for Credit Card Fraud Alert Review

Capstone Project 2 by **Ng Yi Zhen (23076003)**, Bachelor of Computer Science (Hons), Sunway University.

This project evaluates a fraud-alert review workflow that combines a reproducible detector benchmark, SHAP evidence, local narrative generation, deterministic validation, and fail-closed fallback. The objective is not to claim a new fraud-detection algorithm. It is to measure whether a local language model can translate signed model evidence into a readable analyst brief without allowing detected unsupported content to become the delivered explanation.

## System overview

The implementation contains:

- six detector configurations evaluated across five fixed seeds on the European Credit Card Fraud dataset;
- a frozen cost-sensitive XGBoost detector used as the recorded evidence source;
- SHAP-based signed feature attribution and deterministic reason codes;
- local narrative generation through Ollama;
- deterministic checks for format, evidence completeness, grounding, and direction;
- deterministic fallback whenever generation is unavailable or rejected; and
- a React and FastAPI workbench for reviewing alerts, evidence, narrative status, and experiment results.

The ULB benchmark and the S0 synthetic operational study have different roles. ULB compares detector configurations using anonymous features. S0 evaluates the explanation workflow using business-readable synthetic features. Their metrics are reported separately and are not treated as one model ranking.

## Complete system package

The GitHub release contains `PROJECT_SOURCE.zip`, the complete runnable system snapshot with the public dataset, frozen run directories, manifests, figures, tables, frontend build, and source code:

<https://github.com/yizhen0322/evidence-grounded-fraud-review/releases/tag/cp2-final>

Private participant response records are not included. Only aggregate human-evaluation results are published.
The assessed final report and signed logbook are submitted separately through the university portal and are intentionally not distributed in this system repository.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js and npm
- Optional for live generation: [Ollama](https://ollama.com/) with `llama3:8b`

Recorded mode does not require Ollama. Ollama is required only for live narrative generation.

## Installation

```bash
uv sync
cd app/frontend
npm install
npm run build
cd ../..
```

For the exact recorded dashboard, download and extract `PROJECT_SOURCE.zip` from the release page. From the extracted project directory, validate the frozen evidence chain:

```bash
uv run python tools/validate_dashboard.py --config configs/dashboard.yaml
```

Then start the workbench:

```bash
uv run python -m app.backend.server --config configs/dashboard.yaml
```

Open <http://127.0.0.1:8000/queue>.

## Optional live narrative generation

```bash
ollama serve
ollama pull llama3:8b
```

If Ollama is unavailable, or if generated text fails validation, the system delivers the deterministic evidence brief instead.

## Tests

Python:

```bash
uv run pytest -q
```

Frontend:

```bash
cd app/frontend
npm test
npm run lint
npm run build
```

## Repository structure

- `app/backend/`: FastAPI service and artifact-loading boundary
- `app/frontend/`: React analyst workbench
- `src/`: detector, explanation, provenance, and narrative modules
- `configs/`: experiment and dashboard configurations
- `corpus/`: versioned validator calibration corpora
- `experiments/`: frozen evaluation summaries and decision records
- `reports/`: aggregate tables, figures, and the research claim ledger
- `tools/`: experiment, validation, reporting, and audit utilities
- `tests/`: automated Python tests
