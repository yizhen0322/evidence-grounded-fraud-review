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
