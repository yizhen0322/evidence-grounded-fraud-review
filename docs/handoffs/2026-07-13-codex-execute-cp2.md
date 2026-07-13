# Codex handoff — execute the CP2 implementation plan (2026-07-13)

Paste everything below the line into Codex, run from the repo root `fraud-detection-fyp/`.

---

You are the implementation agent for this FYP repository. Your job now is to EXECUTE the implementation plan — write the code, tests, configs, and run the experiments. Design is frozen; do not re-litigate architecture decisions.

## Read first, in this order

1. `AGENTS.md` — hard rules (research integrity, leakage, test-set discipline, measurement wording, audit integrity). These override everything, including convenience and green tests.
2. `docs/plans/2026-07-13-cp2-implementation-plan.md` — the plan you are executing. Note the NEW **Phase 6R** (Tasks 6.6–6.9), added after examiner review: dual prompt arms, versioned guardrail corpus + validator calibration gate, four-check validator, paired delivery-policy metrics with Wilson CIs, blinded manual audit package.
3. `docs/specs/2026-07-13-react-fastapi-demo-dashboard-spec.md` — only when you reach Task 7.4.

## Execution rules

- Execute tasks **in plan order**: Phase 0 → 1 → 2 → 3 → 4 → 5 → 6 (with 6R interleaved: 6.6/6.7/6.8 must complete BEFORE Task 6.5's final full run; 6.9 after it) → 7.
- Follow the TDD steps as written: failing test first, verify failure, implement, verify pass, commit. One commit per task minimum, conventional-commit messages as specified.
- `uv run pytest` must be green before every commit that touches `src/`. Never weaken, skip, or delete an adversarial/regression test to get green.
- The plan's embedded code is the reference implementation. You added provenance/manifest machinery (`src/provenance.py`, `case_id`, manifest contracts) in your earlier revision — integrate Phase 6R deltas consistently with those contracts, keeping Phase 6R's specified schemas, function names, and file paths. If the two genuinely conflict, keep the Phase 6R schema and log the reconciliation in `docs/plans/DEVIATIONS.md` (create it; one dated line per deviation + reason). Do not silently diverge from the plan.
- Never modify anything under `experiments/runs/` by hand; runs are append-only. Tuning/quick outputs go to `experiments/tuning_runs/` exactly as the plan specifies.
- All randomness seeded as specified. No `notebooks/` results anywhere.

## Checkpoints — STOP and report back to the user at each

1. **End of Phase 2**: report pytest summary (all green) + `tools/check_data.py` output.
2. **After Task 3.3 (G0/G1/G6 real runs)**: report val/test AUC-PR/Recall/F1 per group + `tools/leakage_audit.py` output for each run. Sanity band: G0 test AUC-PR is expected roughly 0.70–0.90 on this dataset. If any group falls outside, STOP — investigate for leakage or bugs before proceeding. Do NOT tune anything against test results.
3. **After Task 4.4 Step 3 (detector freeze)**: report the exact `experiments/DECISIONS.md` entry (winning group + params + validation AUC-PR) BEFORE launching multi-seed runs. The freeze decision must cite validation numbers only.
4. **Task 6.1 (Ollama)**: if `ollama` is not installed or `llama3:8b` is not pulled, STOP and ask the user to run the install/pull (it is a ~4.7 GB download on their machine). Verify with the curl check in the plan before continuing.
5. **Before Task 6.5's final full G5 run**: confirm and report — guardrail suite green INCLUDING Task 6.4 Step 5 regression additions; `tools/calibrate_validator.py` exit 0 (paste the per-category PASS lines); both prompt arms wired. The full run is blocked until all three hold.
6. **After Phase 6**: report `faithfulness.json` (both arms) and generate the Task 6.9 audit sample. **Never fill the audit sheet's `violation_found`/`violation_category`/`notes` columns — human-only, per AGENTS.md.**
7. **End of Phase 7.1**: run `tools/make_results.py`, report the summary table. Then pause for the user before Task 7.2 (adversarial review is run as a separate session, not by you) and Task 7.4 (dashboard).

## Long-running steps

AE training (~minutes/run), tuning (2×20 trials), and multi-seed (6 configs × 5 seeds) are slow — run them sequentially, don't parallelize into resource contention, and report elapsed times in the checkpoint messages. If a run dir already exists for the same date/group/seed, do not delete it; use the plan's collision rules.

## What NOT to do

- No dashboard work before Phase 7.4. No new dependencies beyond the plan's `pyproject.toml`. No API/cloud LLM calls — Ollama only. No "improvements" to methodology (e.g., different split, extra SMOTE variants, threshold tweaks) without user approval. No git push unless the user asks.
- Never write the words "improves/outperforms/superior" in any doc you touch unless quoting a logged test result, and never claim guardrails "eliminate" violations — wording rules are in AGENTS.md.

Start now with Task 0.1. Report checkpoint 1 when Phase 2 is green.
