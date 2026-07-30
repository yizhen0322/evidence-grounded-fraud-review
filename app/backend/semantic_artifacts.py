"""Fail-closed loader for the optional semantic operational case-study run."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from app.backend.artifacts import ArtifactValidationError
from app.backend.schemas import check_states
from app.backend.settings import DashboardSettings
from src.provenance import sha256_file, sha256_json
from src.semantic.explanations import (
    STRUCTURED_PROMPT_TEMPLATE,
    ValidationResult,
    validate_structured_brief,
)


REQUIRED_SEMANTIC_ARTIFACTS = (
    "semantic_cases.jsonl",
    "explanation_comparison.jsonl",
    "metrics.json",
    "explanation_summary.json",
    "semantic_validator_calibration.json",
)
REQUIRED_REASON_FIELDS = {"display_label", "direction", "rank", "value_bucket"}
FORBIDDEN_OPERATIONAL_FIELDS = {
    "Class",
    "class",
    "ground_truth",
    "historical_label",
    "label",
    "outcome",
    "y_true",
}
FORBIDDEN_LLM_PAYLOAD_FIELDS = {
    "amount",
    "case_id",
    "customer_id",
    "detector_score",
    "historical_label",
    "probability",
    "score",
    "shap_value",
    "terminal_id",
    "transaction_id",
    "y_true",
}


@dataclass(frozen=True)
class SemanticReason:
    feature: str
    display_label: str
    direction: str
    rank: int
    value_bucket: str
    shap_value: float | None

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> "SemanticReason":
        missing = REQUIRED_REASON_FIELDS - set(raw)
        if missing:
            raise ArtifactValidationError(
                f"semantic reason missing fields: {sorted(missing)}"
            )
        feature = raw.get("feature", raw.get("evidence_key"))
        if feature is None:
            raise ArtifactValidationError("semantic reason missing feature")
        direction = str(raw["direction"])
        if direction not in {"up", "down", "↑ risk", "↓ risk"}:
            raise ArtifactValidationError("semantic reason has unknown direction")
        return cls(
            feature=str(feature),
            display_label=str(raw["display_label"]),
            direction=direction,
            rank=int(raw["rank"]),
            value_bucket=str(raw["value_bucket"]),
            shap_value=(
                None if raw.get("shap_value") is None else float(raw["shap_value"])
            ),
        )

    @property
    def direction_label(self) -> str:
        return "Increases risk" if self.direction in {"up", "↑ risk"} else "Lowers risk"

    def queue_public(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "display_label": self.display_label,
            "direction": (
                "increases_risk"
                if self.direction in {"up", "↑ risk"}
                else "decreases_risk"
            ),
            "direction_label": self.direction_label,
            "rank": self.rank,
            "value_bucket": self.value_bucket,
        }

    def detail_public(self) -> dict[str, Any]:
        payload = self.queue_public()
        payload["shap_value"] = self.shap_value
        return payload


@dataclass(frozen=True)
class SemanticBriefs:
    raw_reason_codes: tuple[Mapping[str, Any], ...]
    deterministic: str
    guarded_llm: str
    delivered: str
    validation: Mapping[str, str]
    fallback: bool
    fallback_reason: str | None
    minimized_llm_payload: Mapping[str, Any]
    llm_candidate: Mapping[str, Any] | None

    def public(self) -> dict[str, Any]:
        return {
            "raw_reason_codes": [dict(item) for item in self.raw_reason_codes],
            "deterministic": {
                "brief": self.deterministic,
                "source": "server_renderer",
            },
            "guarded_llm": {
                "brief": self.guarded_llm,
                "candidate": (
                    None if self.llm_candidate is None else dict(self.llm_candidate)
                ),
                "delivered_brief": self.delivered,
                "checks": dict(self.validation),
                "fallback": self.fallback,
                "fallback_reason": self.fallback_reason,
                "source": "validated_local_llm",
            },
            "minimized_llm_payload": dict(self.minimized_llm_payload),
        }


@dataclass(frozen=True)
class SemanticCase:
    case_id: str
    alert_rank: int
    flagged_total: int
    detector_score: float
    threshold: float
    risk_bucket: str
    review_status: str
    transaction_context: Mapping[str, Any]
    reason_codes: tuple[SemanticReason, ...]
    briefs: SemanticBriefs

    def queue_item(self) -> dict[str, Any]:
        reasons = sorted(self.reason_codes, key=lambda item: item.rank)
        context = dict(self.transaction_context)
        transaction_time = context.get("transaction_time")
        transaction_id = context.get("transaction_id")
        delivery = "deterministic_fallback" if self.briefs.fallback else "guarded_llm"
        return {
            "case_id": int(self.case_id) if self.case_id.isdigit() else self.case_id,
            "transaction_id": transaction_id,
            "synthetic": True,
            "risk_bucket": self.risk_bucket,
            "review_status": self.review_status,
            "review_state": self.review_status,
            "alert_rank": self.alert_rank,
            "rank": self.alert_rank,
            "score_rank": self.alert_rank,
            "flagged_total": self.flagged_total,
            "threshold": self.threshold,
            "top_reason": reasons[0].queue_public(),
            "top_reasons": [reason.queue_public() for reason in reasons[:3]],
            "readable_top_signal": (
                f"{reasons[0].display_label} {reasons[0].direction_label.lower()}"
            ),
            "transaction_context": context,
            "timestamp": transaction_time,
            "amount": context.get("amount"),
            "recorded_fallback": self.briefs.fallback,
            "recorded_narrative_status": (
                "fallback" if self.briefs.fallback else "passed"
            ),
            "explanation_delivery": delivery,
            "explanation_delivery_detail": {
                "fallback": self.briefs.fallback,
                "fallback_reason": self.briefs.fallback_reason,
                "status": "Fallback" if self.briefs.fallback else "Passed",
            },
        }

    def public_detail(self) -> dict[str, Any]:
        payload = self.queue_item()
        checks = dict(self.briefs.validation)
        payload["detector"] = {
            "flagged": self.detector_score >= self.threshold,
            "score": self.detector_score,
            "threshold": self.threshold,
            "alert_rank": self.alert_rank,
        }
        payload["detector_flagged"] = self.detector_score >= self.threshold
        payload["pred"] = int(self.detector_score >= self.threshold)
        payload["reason_codes"] = [
            reason.detail_public()
            for reason in sorted(self.reason_codes, key=lambda item: item.rank)
        ]
        payload["explanations"] = self.briefs.public()
        payload["deterministic_brief"] = self.briefs.deterministic
        payload["guarded_llm_brief"] = self.briefs.guarded_llm
        payload["fallback_reason"] = self.briefs.fallback_reason
        payload["validation"] = {
            "passed": all(value == "PASS" for value in checks.values()),
            "fallback": self.briefs.fallback,
            "fallback_reason": self.briefs.fallback_reason,
            "checks": checks,
        }
        payload["minimized_payload"] = dict(self.briefs.minimized_llm_payload)
        payload["explanation_comparison"] = {
            "raw_reason_codes": [
                reason.detail_public()
                for reason in sorted(self.reason_codes, key=lambda item: item.rank)
            ],
            "deterministic_brief": self.briefs.deterministic,
            "guarded_llm_brief": self.briefs.guarded_llm,
            "llm_candidate": (
                None
                if self.briefs.llm_candidate is None
                else dict(self.briefs.llm_candidate)
            ),
            "delivered_brief": self.briefs.delivered,
            "validation": payload["validation"],
            "minimized_payload": dict(self.briefs.minimized_llm_payload),
        }
        payload["data_sent_to_llm"] = {
            "payload": dict(self.briefs.minimized_llm_payload),
            "included": [
                "coarse risk bucket",
                "feature key",
                "display label",
                "direction",
                "rank",
                "coarse value bucket",
            ],
            "excluded": [
                "customer ID",
                "terminal ID",
                "exact transaction amount",
                "detector score or probability",
                "SHAP magnitudes",
                "synthetic historical label",
            ],
        }
        return payload


@dataclass(frozen=True)
class SemanticSnapshot:
    cases: Mapping[str, SemanticCase]
    metrics: Mapping[str, Any]
    explanation_summary: Mapping[str, Any]
    validator_calibration: Mapping[str, Any]
    provenance: Mapping[str, Any]

    def case(self, case_id: str) -> SemanticCase:
        try:
            return self.cases[str(case_id)]
        except KeyError as error:
            raise KeyError(f"unknown semantic case_id: {case_id}") from error

    def public_provenance(self) -> dict[str, Any]:
        return dict(self.provenance)


def semantic_unavailable_error() -> dict[str, str]:
    return {
        "code": "semantic_run_unavailable",
        "message": "Operational semantic case-study artifacts are not configured",
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ArtifactValidationError(
                f"{path.name} line {line_number} is not valid JSON"
            ) from error
        if not isinstance(row, dict):
            raise ArtifactValidationError(f"{path.name} line {line_number} is not an object")
        rows.append(row)
    if not rows:
        raise ArtifactValidationError(f"{path.name} is empty")
    return rows


def _manifest_artifacts(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ArtifactValidationError("semantic run manifest missing artifacts")
    return artifacts


def _validate_manifest(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.is_file():
        raise ArtifactValidationError("semantic run is missing run_manifest.json")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("group") != "s0":
        raise ArtifactValidationError("semantic run manifest must declare group s0")
    if manifest.get("run_id") != run_dir.name:
        raise ArtifactValidationError("semantic run_id does not match directory")
    artifacts = _manifest_artifacts(manifest)
    missing = [name for name in REQUIRED_SEMANTIC_ARTIFACTS if name not in artifacts]
    if missing:
        raise ArtifactValidationError(
            f"semantic run manifest missing required artifacts: {missing}"
        )
    for relative, recorded in artifacts.items():
        path = run_dir / relative
        if not path.is_file():
            raise ArtifactValidationError(f"semantic run missing artifact: {relative}")
        expected_hash = recorded.get("sha256") if isinstance(recorded, dict) else None
        if expected_hash is None:
            raise ArtifactValidationError(f"semantic artifact lacks sha256: {relative}")
        if sha256_file(path) != expected_hash:
            raise ArtifactValidationError(f"semantic artifact hash mismatch: {relative}")
    return manifest


def _case_id(raw: Mapping[str, Any]) -> str:
    if "case_id" not in raw:
        raise ArtifactValidationError("semantic row missing case_id")
    return str(raw["case_id"])


def _assert_no_forbidden_public_fields(raw: Mapping[str, Any]) -> None:
    exposed = FORBIDDEN_OPERATIONAL_FIELDS & set(raw)
    if exposed:
        raise ArtifactValidationError(
            f"semantic case contains operationally forbidden fields: {sorted(exposed)}"
        )


def _payload_forbidden_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_LLM_PAYLOAD_FIELDS:
                found.add(str(key))
            found.update(_payload_forbidden_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_payload_forbidden_keys(child))
    return found


def _semantic_context(raw: Mapping[str, Any]) -> Mapping[str, Any]:
    context = raw.get("transaction_context") or raw.get("semantic_context")
    if not isinstance(context, dict):
        raise ArtifactValidationError("semantic case missing transaction context")
    for required in ("transaction_time", "amount"):
        if required not in context:
            raise ArtifactValidationError(f"semantic context missing {required}")
    public = {
        key: value
        for key, value in context.items()
        if key not in {"fraud_label", "historical_label", "y_true", "Class", "class"}
    }
    public["timestamp"] = public["transaction_time"]
    public["synthetic"] = True
    return MappingProxyType(public)


def _expected_payload(
    reasons: tuple[SemanticReason, ...], risk_bucket: str
) -> dict[str, Any]:
    return {
        "risk_bucket": risk_bucket,
        "evidence": [
            {
                "feature": reason.feature,
                "display_label": reason.display_label,
                "direction": "up" if reason.direction in {"up", "↑ risk"} else "down",
                "rank": reason.rank,
                "value_bucket": reason.value_bucket,
            }
            for reason in sorted(reasons, key=lambda item: item.rank)
        ],
    }


def _stored_check_bools(checks: Mapping[str, Any]) -> dict[str, bool]:
    expected_names = {"format", "completeness", "grounding", "direction"}
    if set(checks) != expected_names:
        raise ArtifactValidationError(
            "semantic explanation checks do not match the four-check contract"
        )
    if any(not isinstance(value, bool) for value in checks.values()):
        raise ArtifactValidationError("semantic explanation checks must be booleans")
    return {name: bool(checks[name]) for name in expected_names}


def _recomputed_validation(
    candidate: Mapping[str, Any] | None,
    payload: dict[str, Any],
    transport_status: str,
) -> ValidationResult:
    if candidate is not None:
        if transport_status != "ok":
            raise ArtifactValidationError(
                "semantic LLM candidate requires an ok transport status"
            )
        return validate_structured_brief(dict(candidate), payload)
    if not transport_status.startswith("transport_unavailable"):
        raise ArtifactValidationError(
            "semantic explanation without a candidate must record transport unavailability"
        )
    return ValidationResult(
        False,
        {name: False for name in ("format", "completeness", "grounding", "direction")},
        "transport_unavailable",
    )


def _briefs(
    raw: Mapping[str, Any],
    reasons: tuple[SemanticReason, ...],
    risk_bucket: str,
) -> SemanticBriefs:
    payload = raw.get("minimized_llm_payload") or raw.get("llm_payload")
    if not isinstance(payload, dict):
        raise ArtifactValidationError("semantic explanation missing minimized LLM payload")
    forbidden = _payload_forbidden_keys(payload)
    if forbidden:
        raise ArtifactValidationError(
            f"semantic LLM payload exposes forbidden fields: {sorted(forbidden)}"
        )
    expected_payload = _expected_payload(reasons, risk_bucket)
    if payload != expected_payload:
        raise ArtifactValidationError(
            "semantic minimized payload evidence differs from ranked reason codes"
        )
    checks_raw = raw.get("validation") or raw.get("checks")
    if not isinstance(checks_raw, dict):
        raise ArtifactValidationError("semantic explanation missing validation checks")
    stored_checks = _stored_check_bools(checks_raw)
    raw_codes = tuple(
        MappingProxyType(reason.queue_public())
        for reason in sorted(reasons, key=lambda item: item.rank)
    )
    deterministic = str(raw.get("deterministic_brief", ""))
    delivered = str(raw.get("delivered_brief") or raw.get("final_brief") or deterministic)
    guarded = str(raw.get("guarded_llm_brief") or raw.get("llm_brief") or delivered)
    candidate = raw.get("llm_candidate")
    if candidate is not None and not isinstance(candidate, dict):
        raise ArtifactValidationError("semantic LLM candidate must be an object")
    if isinstance(candidate, dict):
        candidate_forbidden = _payload_forbidden_keys(candidate)
        if candidate_forbidden:
            raise ArtifactValidationError(
                "semantic LLM candidate exposes forbidden fields: "
                f"{sorted(candidate_forbidden)}"
            )
    if not deterministic or not delivered:
        raise ArtifactValidationError("semantic explanation missing deterministic/delivered brief")
    transport_status = str(raw.get("llm_transport_status", ""))
    recomputed = _recomputed_validation(candidate, payload, transport_status)
    if stored_checks != recomputed.checks:
        raise ArtifactValidationError(
            "semantic stored validation differs from recomputed validator outcome"
        )
    fallback = bool(raw.get("fallback", False))
    if fallback is recomputed.ok:
        raise ArtifactValidationError(
            "semantic stored fallback differs from recomputed validator outcome"
        )
    fallback_reason = (
        None if raw.get("fallback_reason") in {"", None} else str(raw["fallback_reason"])
    )
    if fallback_reason != recomputed.fallback_reason:
        raise ArtifactValidationError(
            "semantic stored fallback reason differs from recomputed validator outcome"
        )
    expected_brief = (
        deterministic
        if fallback
        else str(candidate["summary"] if isinstance(candidate, dict) else "")
    )
    if guarded != expected_brief or delivered != expected_brief:
        raise ArtifactValidationError(
            "semantic delivered brief is inconsistent with the validate-or-fallback policy"
        )
    expected_delivery = "deterministic_fallback" if fallback else "guarded_llm"
    if raw.get("delivery") not in {None, expected_delivery}:
        raise ArtifactValidationError(
            "semantic delivery label is inconsistent with the validate-or-fallback policy"
        )
    return SemanticBriefs(
        raw_reason_codes=raw_codes,
        deterministic=deterministic,
        guarded_llm=guarded,
        delivered=delivered,
        validation=MappingProxyType(check_states(recomputed.checks)),
        fallback=fallback,
        fallback_reason=fallback_reason,
        minimized_llm_payload=MappingProxyType(payload),
        llm_candidate=(
            None if candidate is None else MappingProxyType(dict(candidate))
        ),
    )


def _calibration_source_path(
    settings: DashboardSettings, relative: Any, label: str
) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ArtifactValidationError(f"semantic calibration missing {label}")
    candidate = (settings.repo_root / relative).resolve()
    try:
        candidate.relative_to(settings.repo_root)
    except ValueError as error:
        raise ArtifactValidationError(
            f"semantic calibration {label} escapes repository root"
        ) from error
    if not candidate.is_file():
        raise ArtifactValidationError(f"semantic calibration {label} is unavailable")
    return candidate


def _validate_calibration(
    calibration: Any,
    settings: DashboardSettings,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(calibration, dict):
        raise ArtifactValidationError(
            "semantic validator calibration must be a JSON object"
        )
    required = {
        "schema_version",
        "corpus_version",
        "corpus_path",
        "corpus_sha256",
        "validator_source",
        "validator_sha256",
        "prompt_sha256",
        "n",
        "matched",
        "passed",
        "control_acceptance",
        "attack_interception",
    }
    missing = required - set(calibration)
    if missing:
        raise ArtifactValidationError(
            f"semantic calibration missing required fields: {sorted(missing)}"
        )
    if calibration["passed"] is not True:
        raise ArtifactValidationError("semantic validator calibration did not pass")
    if int(calibration["n"]) <= 0 or int(calibration["matched"]) != int(
        calibration["n"]
    ):
        raise ArtifactValidationError(
            "semantic calibration counts do not show a complete match"
        )
    for name in ("control_acceptance", "attack_interception"):
        estimate = calibration[name]
        if (
            not isinstance(estimate, dict)
            or int(estimate.get("n", 0)) <= 0
            or float(estimate.get("rate", -1.0)) != 1.0
            or not all(field in estimate for field in ("lower", "upper"))
        ):
            raise ArtifactValidationError(
                f"semantic calibration {name} is incomplete or below the required gate"
            )
    manifest_extra = manifest.get("extra")
    if not isinstance(manifest_extra, dict):
        raise ArtifactValidationError("semantic run manifest missing calibration identities")
    identity_pairs = {
        "validator_corpus_sha256": calibration["corpus_sha256"],
        "validator_sha256": calibration["validator_sha256"],
        "prompt_sha256": calibration["prompt_sha256"],
        "validator_calibration_sha256": sha256_file(
            settings.semantic_run / "semantic_validator_calibration.json"
        ),
    }
    for name, expected in identity_pairs.items():
        if manifest_extra.get(name) != expected:
            raise ArtifactValidationError(
                f"semantic calibration identity differs from manifest: {name}"
            )
    corpus_candidate = (settings.repo_root / str(calibration["corpus_path"])).resolve()
    validator_candidate = (
        settings.repo_root / str(calibration["validator_source"])
    ).resolve()
    if corpus_candidate.is_file():
        corpus_path = _calibration_source_path(
            settings, calibration["corpus_path"], "corpus_path"
        )
        if sha256_file(corpus_path) != calibration["corpus_sha256"]:
            raise ArtifactValidationError("semantic calibration corpus hash mismatch")
    if validator_candidate.is_file():
        validator_path = _calibration_source_path(
            settings, calibration["validator_source"], "validator_source"
        )
        if sha256_file(validator_path) != calibration["validator_sha256"]:
            raise ArtifactValidationError("semantic calibration validator hash mismatch")
    if sha256_json(STRUCTURED_PROMPT_TEMPLATE) != calibration["prompt_sha256"]:
        raise ArtifactValidationError("semantic calibration prompt hash mismatch")
    return calibration


def load_semantic_snapshot(settings: DashboardSettings) -> SemanticSnapshot:
    """Validate and join configured semantic operational artifacts."""
    run_dir = settings.semantic_run
    if run_dir is None:
        raise ArtifactValidationError("semantic run is not configured")
    try:
        manifest = _validate_manifest(run_dir)
        cases_rows = _read_jsonl(run_dir / "semantic_cases.jsonl")
        explanation_rows = _read_jsonl(run_dir / "explanation_comparison.jsonl")
        metrics = json.loads((run_dir / "metrics.json").read_text())
        summary = json.loads((run_dir / "explanation_summary.json").read_text())
        artifacts = _manifest_artifacts(manifest)
        calibration = _validate_calibration(
            json.loads((run_dir / "semantic_validator_calibration.json").read_text()),
            settings,
            manifest,
        )
        threshold = float(manifest["threshold"])

        explanations = {_case_id(row): row for row in explanation_rows}
        if len(explanations) != len(explanation_rows):
            raise ArtifactValidationError("semantic explanation case_id values are not unique")

        joined: dict[str, SemanticCase] = {}
        for row in cases_rows:
            _assert_no_forbidden_public_fields(row)
            case_id = _case_id(row)
            if case_id in joined:
                raise ArtifactValidationError("semantic case_id values are not unique")
            if case_id not in explanations:
                raise ArtifactValidationError(
                    f"semantic case has no explanation comparison: {case_id}"
                )
            reasons_raw = row.get("reason_codes") or row.get("reasons")
            if not isinstance(reasons_raw, list) or not reasons_raw:
                raise ArtifactValidationError("semantic case missing reason codes")
            reasons = tuple(
                SemanticReason.from_raw(reason)
                for reason in sorted(reasons_raw, key=lambda item: int(item["rank"]))
            )
            ranks = [reason.rank for reason in reasons]
            if ranks != list(range(1, len(ranks) + 1)):
                raise ArtifactValidationError("semantic reason ranks must be contiguous")
            score = float(row.get("detector_score", row.get("score")))
            row_threshold = float(row.get("threshold", threshold))
            if row_threshold != threshold:
                raise ArtifactValidationError("semantic case threshold differs from manifest")
            if "risk_bucket" not in row:
                raise ArtifactValidationError("semantic case missing relative risk_bucket")
            case_risk_bucket = str(row["risk_bucket"])
            joined[case_id] = SemanticCase(
                case_id=case_id,
                alert_rank=int(row.get("alert_rank", row.get("rank", len(joined) + 1))),
                flagged_total=int(row.get("flagged_total", len(cases_rows))),
                detector_score=score,
                threshold=threshold,
                risk_bucket=case_risk_bucket,
                review_status=str(row.get("review_status", "unreviewed")),
                transaction_context=_semantic_context(row),
                reason_codes=reasons,
                briefs=_briefs(explanations[case_id], reasons, case_risk_bucket),
            )

        if set(explanations) != set(joined):
            raise ArtifactValidationError(
                "semantic explanation case_id set differs from semantic cases"
            )
        ordered = dict(sorted(joined.items(), key=lambda item: (item[1].alert_rank, item[0])))
        provenance = MappingProxyType(
            {
                "run_id": manifest["run_id"],
                "group": manifest["group"],
                "seed": int(manifest["seed"]),
                "synthetic": True,
                "manifest_sha256": sha256_file(run_dir / "run_manifest.json"),
                "dataset_sha256": manifest.get("dataset_sha256"),
                "config_sha256": manifest.get("config_sha256"),
                "threshold": threshold,
                "feature_names": tuple(manifest.get("feature_names", ())),
                "artifacts": {
                    name: {
                        "sha256": sha256_file(run_dir / name),
                        "source": f"semantic_run/{name}",
                    }
                    for name in REQUIRED_SEMANTIC_ARTIFACTS
                },
            }
        )
        return SemanticSnapshot(
            cases=MappingProxyType(ordered),
            metrics=MappingProxyType(metrics),
            explanation_summary=MappingProxyType(summary),
            validator_calibration=MappingProxyType(calibration),
            provenance=provenance,
        )
    except ArtifactValidationError:
        raise
    except Exception as error:
        raise ArtifactValidationError(
            f"semantic artifact validation failed: {error}"
        ) from error
