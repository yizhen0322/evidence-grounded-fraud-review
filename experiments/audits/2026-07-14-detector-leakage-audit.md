# Detector Leakage Audit — 2026-07-14

Each path below was passed explicitly to `tools.leakage_audit.audit_run`;
wildcard discovery was not used. Every returned check was `true`, every
manifest recorded `git_dirty: false`, and all 30 runs validated their artifact
hashes, split assignments, test prediction IDs, frozen thresholds, feature
names, and untouched validation/test distributions.

| Group | Seed 42 | Seed 43 | Seed 44 | Seed 45 | Seed 46 |
| --- | --- | --- | --- | --- | --- |
| G0 | PASS | PASS | PASS | PASS | PASS |
| G1 | PASS | PASS | PASS | PASS | PASS |
| G2 | PASS | PASS | PASS | PASS | PASS |
| G3 | PASS | PASS | PASS | PASS | PASS |
| G6 | PASS | PASS | PASS | PASS | PASS |
| G7 | PASS | PASS | PASS | PASS | PASS |

Audited paths use `experiments/runs/2026-07-14_<group>_seed<seed>`, with groups
`g0,g1,g2,g3,g6,g7` and seeds `42,43,44,45,46` expanded explicitly.
