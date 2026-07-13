# Detector Freeze Decisions

## 2026-07-14 — Frozen detector

The detector was selected using validation AUC-PR only. The two strongest
untuned groups by validation AUC-PR were G6 (cost-sensitive XGBoost, 0.875841)
and G2 (AE reconstruction error plus XGBoost, 0.865897), so those groups received
the seeded 20-trial random search.

The frozen detector is **G6 cost-sensitive XGBoost** with:

```yaml
max_depth: 6
n_estimators: 500
learning_rate: 0.2
subsample: 1.0
colsample_bytree: 0.7
```

Its best tuning-run validation AUC-PR was 0.877447. The best G2 tuning-run
validation AUC-PR was 0.868929. The G6 tuning evidence is stored in
`experiments/tuning/g6_tuning.json`; the G2 comparison is stored in
`experiments/tuning/g2_tuning.json`.

Test results were not consulted for this decision.

The validation AUC-PR values are used consistently for model selection but are
not treated as unbiased generalization estimates because the same validation
split also drives XGBoost early stopping. Final performance claims use the
frozen detector's untouched test evaluation and multi-seed summaries.

## Post-freeze reporting constraint

Only G6 and G2 received the 20-trial search; the other reported groups retain
their predeclared defaults. Cross-group differences therefore must not be
attributed solely to architecture or imbalance handling. G6 was frozen because
of its validation result, not because it was guaranteed to lead every test seed.

## 2026-07-14 — G5 structured transport and fixed-template rendering

Two local quick passes showed that `llama3:8b` repeatedly added preambles,
Unicode bullets, blank lines, or altered the fixed ACTION line even under the
strict prompt. This made transport-format noise dominate the faithfulness
experiment and produced 100% fallback in both prompt arms.

G5 therefore uses Ollama's local JSON-schema structured-output parameter for
both strict and simple prompt arms. The schema stabilizes transport shape only:
it accepts free narrative text plus feature/direction items and does not bind
features to the evidence. The raw JSON response is retained, local code renders
it once into the fixed text template, and that same rendered candidate is used
for both OFF-policy detected-violation measurement and ON-policy
validate-or-fallback delivery. The strict and simple arms use the same schema,
temperature, model, and evidence; only their faithfulness instructions differ.

An 8-case quick pass after this change produced 5/8 accepted strict candidates
and 0/8 accepted simple candidates under the current validator. These quick-run
figures are diagnostic only and are not reportable G5 results. The final run is
created only from a clean committed tree, requires zero unavailable model calls,
and records the exact prompt/client/validator/calibration hashes.
