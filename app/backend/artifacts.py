"""Fail-closed loader for the dashboard's immutable recorded snapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import pandas as pd

from app.backend.schemas import check_states
from app.backend.evidence import serialize_operational_evidence
from app.backend.settings import DashboardSettings
from src.provenance import (
    assert_source_hashes,
    sha256_file,
    source_run_ref,
    validate_run_manifest,
)
from tools.make_results import validate_results_manifest
from tools.run_g5_narratives import load_g4_context, validate_reportable_g5_run


DETECTOR_GROUPS = {"g0", "g1", "g2", "g3", "g6", "g7"}
SHARED_PROVENANCE_FIELDS = (
    "dataset_sha256",
    "config_sha256",
    "split_sha256",
    "seed",
    "threshold",
    "feature_names",
)


class ArtifactValidationError(ValueError):
    """Raised when recorded dashboard evidence is not exactly reproducible."""


@dataclass(frozen=True)
class ReasonCode:
    feature: str
    direction: str
    rank: int
    shap_value: float

    def public(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "direction": self.direction,
            "rank": self.rank,
            "shap_value": self.shap_value,
        }


@dataclass(frozen=True)
class RecordedNarrative:
    arm: str
    raw_output: str
    final_text: str
    checks: Mapping[str, bool]
    fallback: bool
    fallback_reason: str | None
    latency_seconds: float

    def public(self) -> dict[str, Any]:
        return {
            "mode": "recorded",
            "reported": True,
            "arm": self.arm,
            "final_text": self.final_text,
            "checks": check_states(dict(self.checks)),
            "fallback": self.fallback,
            "fallback_reason": self.fallback_reason,
            "latency_seconds": self.latency_seconds,
        }


@dataclass(frozen=True)
class TransactionContext:
    amount: float
    elapsed_seconds: float

    def public(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "elapsed_seconds": self.elapsed_seconds,
            "currency": None,
            "time_basis": "seconds_since_dataset_start",
            "source": "hash_verified_dataset_row",
        }


@dataclass(frozen=True)
class RecordedCase:
    case_id: int
    score: float
    pred: int
    y_true: int
    risk_bucket: str
    threshold: float
    reason_codes: tuple[ReasonCode, ...]
    narrative: RecordedNarrative
    evidence_payload: str
    transaction_context: TransactionContext
    score_rank: int
    flagged_total: int

    @property
    def historical_label(self) -> str:
        return "Fraud" if self.y_true == 1 else "Legitimate"

    @property
    def detector_label(self) -> str:
        return "Flagged" if self.pred == 1 else "Not flagged"

    @property
    def outcome(self) -> str:
        if self.pred == 1 and self.y_true == 1:
            return "Flagged true positive"
        if self.pred == 1 and self.y_true == 0:
            return "Flagged false positive"
        if self.pred == 0 and self.y_true == 1:
            return "Missed fraud"
        return "Correctly unflagged legitimate transaction"

    def guardrail_record(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "score": self.score,
            "y_true": self.y_true,
            "risk_bucket": self.risk_bucket,
            "codes": [code.public() for code in self.reason_codes],
        }

    def queue_item(self) -> dict[str, Any]:
        ordered_reasons = sorted(self.reason_codes, key=lambda code: code.rank)
        top = ordered_reasons[0]
        return {
            "case_id": self.case_id,
            "risk_bucket": self.risk_bucket,
            "score_rank": self.score_rank,
            "flagged_total": self.flagged_total,
            "pred": self.pred,
            "detector_flagged": self.pred == 1,
            "detector": self.detector_label,
            "top_reason": top.public(),
            "top_reasons": [code.public() for code in ordered_reasons[:3]],
            "recorded_narrative_status": (
                "Fallback" if self.narrative.fallback else "Passed"
            ),
            "recorded_fallback": self.narrative.fallback,
            "transaction_context": self.transaction_context.public(),
        }

    def public_detail(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "risk_bucket": self.risk_bucket,
            "score_rank": self.score_rank,
            "flagged_total": self.flagged_total,
            "pred": self.pred,
            "detector_flagged": self.pred == 1,
            "detector": self.detector_label,
            "threshold": self.threshold,
            "reason_codes": [code.public() for code in self.reason_codes],
            "narrative": self.narrative.public(),
            "transaction_context": self.transaction_context.public(),
            "data_sent_to_llm": {
                "payload": self.evidence_payload,
                "included": [
                    "coarse risk bucket",
                    "feature name",
                    "direction",
                    "rank",
                ],
                "excluded": [
                    "raw transaction row",
                    "exact feature values",
                    "detector score or probability",
                    "SHAP magnitudes",
                    "historical label",
                ],
            },
        }


@dataclass(frozen=True)
class DashboardSnapshot:
    cases: Mapping[int, RecordedCase]
    known_features: tuple[str, ...]
    detector_results: tuple[Mapping[str, Any], ...]
    result_rows: tuple[Mapping[str, Any], ...]
    faithfulness: Mapping[str, Any]
    figures: Mapping[str, Path]
    scenarios: tuple[Mapping[str, Any], ...]
    provenance: Mapping[str, Any]
    generation_seed: int

    def case(self, case_id: int) -> RecordedCase:
        try:
            return self.cases[int(case_id)]
        except KeyError as error:
            raise KeyError(f"unknown recorded case_id: {case_id}") from error

    def public_provenance(self) -> dict[str, Any]:
        return dict(self.provenance)


def _risk_bucket(score: float) -> str:
    if score >= 0.9:
        return "High"
    if score >= 0.5:
        return "Medium"
    return "Low"


def _load_transaction_context(
    dataset_path: Path,
    expected_sha256: str,
    case_ids: set[int],
) -> dict[int, TransactionContext]:
    if sha256_file(dataset_path) != expected_sha256:
        raise ArtifactValidationError(
            "configured dataset differs from the detector's recorded dataset hash"
        )
    frame = pd.read_csv(dataset_path, usecols=["Time", "Amount"])
    if not case_ids:
        return {}
    if min(case_ids) < 0 or max(case_ids) >= len(frame):
        raise ArtifactValidationError(
            "recorded case_id falls outside the configured dataset"
        )
    selected = frame.iloc[sorted(case_ids)]
    if selected[["Time", "Amount"]].isna().any().any():
        raise ArtifactValidationError(
            "configured dataset has missing transaction context values"
        )
    return {
        case_id: TransactionContext(
            amount=float(frame.iloc[case_id]["Amount"]),
            elapsed_seconds=float(frame.iloc[case_id]["Time"]),
        )
        for case_id in case_ids
    }


def _assert_shared_chain(child: dict, parent: dict, label: str) -> None:
    for field in SHARED_PROVENANCE_FIELDS:
        if child[field] != parent[field]:
            raise ArtifactValidationError(
                f"{label} source chain differs on {field}"
            )


def _manifest_public(run_dir: Path, manifest: dict) -> dict[str, Any]:
    return {
        "run_id": manifest["run_id"],
        "group": manifest["group"],
        "seed": int(manifest["seed"]),
        "manifest_sha256": sha256_file(run_dir / "run_manifest.json"),
    }


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _records(frame: pd.DataFrame) -> tuple[Mapping[str, Any], ...]:
    rows = []
    for record in frame.to_dict(orient="records"):
        rows.append(MappingProxyType({key: _json_value(value) for key, value in record.items()}))
    return tuple(rows)


def _assert_file_points_to(path: Path, expected: Path, label: str) -> None:
    try:
        actual = Path(path.read_text().strip()).expanduser().resolve()
    except OSError as error:
        raise ArtifactValidationError(f"cannot read {label} source pointer") from error
    if actual != expected.resolve():
        raise ArtifactValidationError(f"{label} source pointer does not match configured run")


def _validate_scenarios(
    settings: DashboardSettings,
    cases: Mapping[int, RecordedCase],
) -> tuple[Mapping[str, Any], ...]:
    config = settings.config.demo_cases
    try:
        faithful = cases[config.faithful_case_id]
        error = cases[config.error_or_uncertainty_case_id]
        attack = cases[config.attack_case_id]
    except KeyError as missing:
        raise ArtifactValidationError(
            f"curated scenario case_id is absent from recorded cases: {missing.args[0]}"
        ) from missing
    if faithful.narrative.fallback or not all(faithful.narrative.checks.values()):
        raise ArtifactValidationError(
            "faithful scenario requires a strict accepted recorded narrative"
        )
    if not (error.pred == 1 and error.y_true == 0):
        raise ArtifactValidationError(
            "error scenario must be a real recorded flagged false positive"
        )
    if attack.narrative.fallback or not all(attack.narrative.checks.values()):
        raise ArtifactValidationError(
            "attack scenario requires a strict accepted recorded narrative"
        )
    return (
        MappingProxyType(
            {
                "id": "faithful_recorded",
                "key": "faithful",
                "kind": "faithful",
                "case_id": faithful.case_id,
                "title": "Faithful recorded case",
                "description": "Strict recorded narrative passed all four guardrail checks.",
            }
        ),
        MappingProxyType(
            {
                "id": "real_false_positive",
                "key": "error",
                "kind": "error",
                "case_id": error.case_id,
                "title": "Real recorded false positive",
                "description": (
                    "The detector flagged this transaction, while evaluation-only "
                    "historical ground truth labels it legitimate."
                ),
            }
        ),
        MappingProxyType(
            {
                "id": "guardrail_attack",
                "key": "attack",
                "kind": "attack",
                "case_id": attack.case_id,
                "title": "Guardrail attack case",
                "description": (
                    "A faithful base narrative supports deterministic server-side mutations."
                ),
            }
        ),
    )


def load_snapshot(settings: DashboardSettings) -> DashboardSnapshot:
    """Validate every configured source, then build a read-only joined snapshot."""
    try:
        if settings.repo_root != Path.cwd().resolve():
            raise ArtifactValidationError(
                "dashboard validation must run from the repository root"
            )
        detector = validate_run_manifest(settings.detector_run)
        if detector["group"] not in DETECTOR_GROUPS or detector["git_dirty"]:
            raise ArtifactValidationError("configured detector is not a clean reportable group")
        assert_source_hashes(
            detector,
            detector["source_code_sha256"],
            repo_root=settings.repo_root,
        )

        g4, g4_records, _seed, known_features = load_g4_context(settings.g4_run)
        if g4["git_dirty"]:
            raise ArtifactValidationError("configured G4 is not a clean recorded run")
        assert_source_hashes(
            g4,
            g4["source_code_sha256"],
            repo_root=settings.repo_root,
        )
        expected_detector_ref = source_run_ref(settings.detector_run)
        if g4["source_runs"] != [expected_detector_ref]:
            raise ArtifactValidationError("G4 detector source chain is not the exact configured run")
        _assert_file_points_to(
            settings.g4_run / "source_detector_run.txt",
            settings.detector_run,
            "G4 detector",
        )
        _assert_shared_chain(g4, detector, "G4")

        g5, g5_rows = validate_reportable_g5_run(settings.g5_run)
        assert_source_hashes(
            g5,
            g5["source_code_sha256"],
            repo_root=settings.repo_root,
        )
        expected_g4_ref = source_run_ref(settings.g4_run)
        if g5["source_runs"] != [expected_g4_ref]:
            raise ArtifactValidationError("G5 source chain is not the exact configured G4 run")
        _assert_file_points_to(
            settings.g5_run / "source_g4_run.txt",
            settings.g4_run,
            "G5 G4",
        )
        _assert_shared_chain(g5, g4, "G5")

        results_manifest = validate_results_manifest(settings.results_manifest)
        if expected_detector_ref not in results_manifest["inputs"]:
            raise ArtifactValidationError(
                "configured detector is absent from the exact results allowlist"
            )

        predictions = pd.read_parquet(settings.detector_run / "predictions.parquet")
        flagged = predictions.loc[predictions["pred"] == 1].copy()
        prediction_by_id = flagged.set_index("case_id")
        if not prediction_by_id.index.is_unique:
            raise ArtifactValidationError("detector flagged case_id values are not unique")
        g4_by_id = {int(record["case_id"]): record for record in g4_records}
        if set(prediction_by_id.index.map(int)) != set(g4_by_id):
            raise ArtifactValidationError(
                "detector flagged case_id set differs from configured G4"
            )
        for case_id, record in g4_by_id.items():
            prediction = prediction_by_id.loc[case_id]
            if float(record["score"]) != float(prediction["score"]):
                raise ArtifactValidationError(f"G4 score mismatch for case_id {case_id}")
            if int(record["y_true"]) != int(prediction["y_true"]):
                raise ArtifactValidationError(f"G4 label mismatch for case_id {case_id}")
            if record["risk_bucket"] != _risk_bucket(float(record["score"])):
                raise ArtifactValidationError(f"G4 risk bucket mismatch for case_id {case_id}")

        ranked_case_ids = sorted(
            g4_by_id,
            key=lambda case_id: (-float(g4_by_id[case_id]["score"]), case_id),
        )
        score_rank_by_id = {
            case_id: index
            for index, case_id in enumerate(ranked_case_ids, start=1)
        }
        transaction_context_by_id = _load_transaction_context(
            settings.dataset_path,
            str(detector["dataset_sha256"]),
            set(g4_by_id),
        )

        arm = settings.config.recorded_narrative_arm
        selected_rows = [row for row in g5_rows if row["arm"] == arm]
        narrative_by_id = {int(row["case_id"]): row for row in selected_rows}
        if len(narrative_by_id) != len(selected_rows) or set(narrative_by_id) != set(g4_by_id):
            raise ArtifactValidationError(
                "recorded strict G5 case_id set differs from configured G4"
            )

        joined: dict[int, RecordedCase] = {}
        for case_id, record in g4_by_id.items():
            prediction = prediction_by_id.loc[case_id]
            row = narrative_by_id[case_id]
            checks = row["checks"]
            if set(checks) != {"format", "completeness", "grounding", "direction"}:
                raise ArtifactValidationError("G5 checks do not match the four-check contract")
            reason_codes = tuple(
                ReasonCode(
                    feature=str(code["feature"]),
                    direction=str(code["direction"]),
                    rank=int(code["rank"]),
                    shap_value=float(code["shap_value"]),
                )
                for code in sorted(record["codes"], key=lambda item: item["rank"])
            )
            narrative = RecordedNarrative(
                arm=arm,
                raw_output=str(row["raw_output"]),
                final_text=str(row["final_text"]),
                checks=MappingProxyType({key: bool(value) for key, value in checks.items()}),
                fallback=bool(row["fallback"]),
                fallback_reason=row["fallback_reason"],
                latency_seconds=float(row["latency_seconds"]),
            )
            joined[case_id] = RecordedCase(
                case_id=case_id,
                score=float(record["score"]),
                pred=int(prediction["pred"]),
                y_true=int(record["y_true"]),
                risk_bucket=str(record["risk_bucket"]),
                threshold=float(detector["threshold"]),
                reason_codes=reason_codes,
                narrative=narrative,
                evidence_payload=serialize_operational_evidence(record),
                transaction_context=transaction_context_by_id[case_id],
                score_rank=score_rank_by_id[case_id],
                flagged_total=len(g4_by_id),
            )

        cases = MappingProxyType(
            dict(sorted(joined.items(), key=lambda item: (-item[1].score, item[0])))
        )
        scenarios = _validate_scenarios(settings, cases)
        attack_case = cases[settings.config.demo_cases.attack_case_id]
        if not (set(known_features) - {code.feature for code in attack_case.reason_codes}):
            raise ArtifactValidationError(
                "attack scenario has no known unlisted feature for grounding demo"
            )

        output_records = results_manifest["outputs"]
        required_outputs = {
            "reports/tables/results_main.csv",
            "reports/tables/results_summary.csv",
            "reports/figures/pr_curves.png",
        }
        if not required_outputs.issubset(output_records):
            raise ArtifactValidationError("results manifest lacks required dashboard outputs")
        main = pd.read_csv(settings.repo_root / "reports/tables/results_main.csv")
        summary = pd.read_csv(settings.repo_root / "reports/tables/results_summary.csv")
        if set(summary["group"]) != DETECTOR_GROUPS:
            raise ArtifactValidationError("detector results contain wrong experiment groups")
        faithfulness = json.loads((settings.g5_run / "faithfulness.json").read_text())

        figures = MappingProxyType(
            {
                "pr_curves": settings.repo_root / "reports/figures/pr_curves.png",
                "shap_global_bar": settings.g4_run / "shap_global_bar.png",
            }
        )
        provenance = MappingProxyType(
            {
                "detector": _manifest_public(settings.detector_run, detector),
                "g4": _manifest_public(settings.g4_run, g4),
                "g5": _manifest_public(settings.g5_run, g5),
                "results": {
                    "run_id": "task7.1_results",
                    "group": "results",
                    "manifest_sha256": sha256_file(settings.results_manifest),
                    "input_run_count": len(results_manifest["inputs"]),
                },
                "source_chain_verified": True,
                "source_chain_valid": True,
                "narrative_source_code_compatible": True,
                "source_code_compatible": True,
            }
        )
        return DashboardSnapshot(
            cases=cases,
            known_features=tuple(known_features),
            detector_results=_records(summary),
            result_rows=_records(main),
            faithfulness=MappingProxyType(faithfulness),
            figures=figures,
            scenarios=scenarios,
            provenance=provenance,
            generation_seed=int(g5["extra"]["generation_seed"]),
        )
    except ArtifactValidationError:
        raise
    except Exception as error:
        raise ArtifactValidationError(f"dashboard artifact validation failed: {error}") from error
