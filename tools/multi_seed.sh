#!/usr/bin/env bash
# Usage: tools/multi_seed.sh configs/g3_ae_xgb_smote.yaml
set -euo pipefail

config=${1:?usage: tools/multi_seed.sh CONFIG}
for seed in 42 43 44 45 46; do
  uv run python -m src.run_experiment --config "$config" --seed "$seed"
done
