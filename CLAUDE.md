# CLAUDE.md

Read and follow `AGENTS.md` in this directory — it is the single source of truth for research-integrity rules, data-leakage rules, test-set discipline, the G0–G7 experiment matrix, metrics, LLM guardrails, and engineering conventions for this FYP repo. All of its "hard rules" apply to every session.

Quick orientation:
- CP2 implementation plan: `docs/plans/2026-07-13-cp2-implementation-plan.md`
- Approved methodology: `../CP1/01_FINAL_SUBMISSION/Proposal_Capstone_Project.pdf` (Chapter 3)
- Run experiments only via configs in `configs/` + code in `src/`; results live in `experiments/runs/`
- `uv run pytest` must pass before any commit that touches `src/`
