"""Generate manifest-backed G4 SHAP reason codes for a frozen detector run."""

import argparse
import datetime
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import yaml
from tensorflow import keras
from xgboost import XGBClassifier

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.load import CASE_ID, FEATURES, dedupe, load_raw
from src.data.preprocess import apply_scaler, fit_scaler
from src.data.split import stratified_split
from src.explainability.reason_codes import (
    global_importance,
    local_reason_codes,
    shap_values_for,
)
from src.models.autoencoder import latent_features, reconstruction_error
from src.provenance import validate_run_manifest, write_run_manifest

DETECTOR_GROUPS = {"g0", "g1", "g2", "g3", "g6", "g7"}


def risk_bucket(probability: float) -> str:
    if probability >= 0.9:
        return "High"
    if probability >= 0.5:
        return "Medium"
    return "Low"


def select_flagged(
    predictions: pd.DataFrame,
    X_test: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Join flagged detector predictions to rebuilt features by case_id."""
    required = {CASE_ID, "y_true", "score", "pred"}
    if required - set(predictions.columns):
        raise ValueError("detector predictions violate the case_id contract")
    if (
        predictions[CASE_ID].isna().any()
        or not predictions[CASE_ID].is_unique
    ):
        raise ValueError("detector case_id must be non-null and unique")
    if X_test.index.name != CASE_ID or not X_test.index.is_unique:
        raise ValueError("rebuilt features require a unique case_id index")
    if set(predictions[CASE_ID]) != set(X_test.index):
        raise ValueError(
            "detector predictions and rebuilt features have different case_id sets"
        )
    flagged = predictions.loc[predictions["pred"] == 1].set_index(CASE_ID)
    return flagged, X_test.loc[flagged.index]


def validate_reason_records(
    records: list[dict],
    predictions: pd.DataFrame,
) -> None:
    """Ensure G4 preserves the detector's exact flagged IDs, scores, and labels."""
    expected = predictions.loc[
        predictions["pred"] == 1,
        [CASE_ID, "score", "y_true"],
    ].copy()
    actual = pd.DataFrame(records)
    if actual.empty and not expected.empty:
        raise ValueError("missing G4 reason records")
    if not actual.empty and (
        actual[CASE_ID].isna().any() or not actual[CASE_ID].is_unique
    ):
        raise ValueError("G4 case_id must be non-null and unique")
    if set(actual.get(CASE_ID, [])) != set(expected[CASE_ID]):
        raise ValueError("G4 case_id set does not equal flagged detector case_id set")
    if actual.empty:
        return
    joined = actual.merge(
        expected,
        on=CASE_ID,
        suffixes=("_g4", "_detector"),
        validate="one_to_one",
    )
    if not (joined["score_g4"] == joined["score_detector"]).all():
        raise ValueError("G4 score differs from detector prediction")
    if not (joined["y_true_g4"] == joined["y_true_detector"]).all():
        raise ValueError("G4 label differs from detector prediction")


def rebuild_test_matrix(
    config: dict,
    detector_run: Path,
    data_path: str | Path = "data/raw/creditcard.csv",
) -> pd.DataFrame:
    """Rebuild the detector's test features without recomputing predictions."""
    seed = int(config.get("seed", 42))
    dataframe = load_raw(data_path)
    if config.get("dedup", True):
        dataframe, _ = dedupe(dataframe)
    splits = stratified_split(dataframe, seed=seed)
    scaler = fit_scaler(splits.train)
    X_test = apply_scaler(scaler, splits.test)[FEATURES].copy()

    if config["features"] in {"recon_error", "latent"}:
        autoencoder = keras.models.load_model(
            detector_run / "model" / "ae.keras"
        )
        if config["features"] == "recon_error":
            X_test["recon_error"] = reconstruction_error(
                autoencoder,
                X_test.to_numpy(),
            )
        else:
            latent = latent_features(
                autoencoder,
                X_test[FEATURES].to_numpy(),
            )
            for index in range(latent.shape[1]):
                X_test[f"latent_{index}"] = latent[:, index]

    X_test.index = splits.test[CASE_ID].to_numpy()
    X_test.index.name = CASE_ID
    if not X_test.index.is_unique:
        raise RuntimeError("rebuilt test features have duplicate case_id")
    return X_test


def run_g4(
    detector_run: str | Path,
    top_k: int = 3,
    out_root: str | Path = "experiments/runs",
    data_path: str | Path = "data/raw/creditcard.csv",
    require_clean: bool = True,
) -> Path:
    detector_run = Path(detector_run)
    detector_manifest = validate_run_manifest(detector_run)
    if detector_manifest["group"] not in DETECTOR_GROUPS:
        raise ValueError("G4 source must be a reported detector group")
    config = yaml.safe_load((detector_run / "config.yaml").read_text())
    predictions = pd.read_parquet(detector_run / "predictions.parquet")
    model = XGBClassifier()
    model.load_model(detector_run / "model" / "xgb.json")

    X_test = rebuild_test_matrix(config, detector_run, data_path=data_path)
    feature_names = list(X_test.columns)
    if feature_names != detector_manifest["feature_names"]:
        raise ValueError(
            "rebuilt feature_names differ from the frozen detector manifest"
        )

    seed = int(config.get("seed", 42))
    output = Path(out_root) / (
        f"{datetime.date.today().isoformat()}_g4_seed{seed}"
    )
    output.mkdir(parents=True, exist_ok=False)

    flagged, X_flagged = select_flagged(predictions, X_test)
    flagged_shap = shap_values_for(model, X_flagged)
    records = []
    with (output / "reason_codes.jsonl").open("w") as handle:
        for row_index, case_id in enumerate(flagged.index):
            prediction = flagged.loc[case_id]
            record = {
                CASE_ID: int(case_id),
                "score": float(prediction["score"]),
                "y_true": int(prediction["y_true"]),
                "risk_bucket": risk_bucket(float(prediction["score"])),
                "codes": local_reason_codes(
                    flagged_shap[row_index],
                    feature_names,
                    top_k,
                ),
            }
            records.append(record)
            handle.write(json.dumps(record) + "\n")
    validate_reason_records(records, predictions)

    sample = X_test.sample(min(2000, len(X_test)), random_state=42)
    importance = global_importance(
        shap_values_for(model, sample),
        feature_names,
    )
    importance.to_frame().to_csv(output / "global_importance.csv")
    importance.head(15)[::-1].plot.barh(
        figsize=(8, 6),
        title="Global SHAP importance (top 15)",
    )
    plt.xlabel("mean |SHAP|")
    plt.tight_layout()
    plt.savefig(output / "shap_global_bar.png", dpi=200)
    plt.close()
    (output / "source_detector_run.txt").write_text(
        str(detector_run.resolve()) + "\n"
    )

    write_run_manifest(
        run_dir=output,
        group="g4",
        seed=seed,
        source_run_dirs=[detector_run],
        source_files=[
            "src/data/load.py",
            "src/data/preprocess.py",
            "src/data/split.py",
            "src/explainability/reason_codes.py",
            "src/models/autoencoder.py",
            "src/provenance.py",
            "tools/run_g4_shap.py",
        ],
        require_clean=require_clean,
    )
    print(f"G4 written to {output}: {len(flagged)} flagged cases explained")
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--detector-run", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    arguments = parser.parse_args()
    run_g4(arguments.detector_run, top_k=arguments.top_k)


if __name__ == "__main__":
    main()
