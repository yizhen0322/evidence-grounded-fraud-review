"""Random-search tuning on validation AUC-PR with no test scoring."""

import argparse
import copy
import json
import random
import sys
from pathlib import Path

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.run_experiment import run

SPACE = {
    "max_depth": [3, 4, 6, 8],
    "n_estimators": [200, 300, 500],
    "learning_rate": [0.03, 0.1, 0.2],
    "subsample": [0.7, 0.9, 1.0],
    "colsample_bytree": [0.7, 0.9, 1.0],
}


def tune(
    config_path: str | Path,
    n_trials: int = 20,
    data_path: str | Path = "data/raw/creditcard.csv",
    out_root: str | Path = "experiments/tuning_runs",
    results_root: str | Path = "experiments/tuning",
    require_clean: bool = True,
) -> Path:
    """Run a seeded random search and write trials ranked by validation AUC-PR."""
    if n_trials <= 0:
        raise ValueError("n_trials must be positive")
    base = yaml.safe_load(Path(config_path).read_text())
    rng = random.Random(42)
    trials = []
    for index in range(n_trials):
        config = copy.deepcopy(base)
        config["xgb_params"] = {
            name: rng.choice(candidates)
            for name, candidates in SPACE.items()
        }
        config["group"] = f"{base['group']}_tune{index:02d}"
        run_dir = run(
            config,
            data_path=data_path,
            out_root=out_root,
            require_clean=require_clean,
            evaluate_test=False,
        )
        metrics = json.loads((run_dir / "metrics.json").read_text())
        if "test" in metrics or (run_dir / "predictions.parquet").exists():
            raise RuntimeError("tuning run touched the test evaluation path")
        validation = metrics["val"]
        trial = {
            "trial": index,
            "run_id": run_dir.name,
            "params": config["xgb_params"],
            "val_auc_pr": validation["auc_pr"],
            "val_f1": validation["f1"],
        }
        trials.append(trial)
        print(
            f"trial {index:02d} val_auc_pr={validation['auc_pr']:.4f} "
            f"{config['xgb_params']}"
        )

    trials.sort(key=lambda item: (-item["val_auc_pr"], item["trial"]))
    output = Path(results_root) / f"{base['group']}_tuning.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(trials, indent=2) + "\n")
    print(f"best: {trials[0]}")
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--n-trials", type=int, default=20)
    parser.add_argument("--data", default="data/raw/creditcard.csv")
    arguments = parser.parse_args()
    tune(
        arguments.config,
        n_trials=arguments.n_trials,
        data_path=arguments.data,
    )


if __name__ == "__main__":
    main()
