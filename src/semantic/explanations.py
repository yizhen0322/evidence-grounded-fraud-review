"""Raw, deterministic, and guarded structured-LLM explanation comparison."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from src.provenance import sha256_file, sha256_json
from src.semantic.catalog import FEATURE_CATALOG

LOCAL_OLLAMA_HOSTS = {"localhost", "127.0.0.1", "::1"}
NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?")
STRUCTURED_PROMPT_TEMPLATE = (
    "Return only one JSON object with exactly the keys risk_bucket, summary, evidence, action. "
    "Copy risk_bucket and evidence exactly from case_evidence. Set action to manual_review. "
    "Set summary to exactly one string from allowed_summary_options. Do not add keys, facts, "
    "identifiers, or exact numbers.\n{payload}"
)


class SemanticLLMUnavailable(RuntimeError):
    """Raised when the local structured LLM transport is unavailable."""


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    checks: dict[str, bool]
    fallback_reason: str | None


def risk_bucket(score: float, threshold: float) -> str:
    if score < threshold:
        return "Low"
    available_margin = max(1e-9, 1.0 - threshold)
    relative_margin = (score - threshold) / available_margin
    if relative_margin >= 2 / 3:
        return "High"
    if relative_margin >= 1 / 3:
        return "Medium"
    return "Low"


def raw_reason_codes(reason_record: dict[str, Any]) -> list[dict[str, str | int]]:
    return [
        {
            "rank": int(code["rank"]),
            "key": str(code["key"]),
            "direction": "up" if code["direction"] == "increases_risk" else "down",
        }
        for code in sorted(reason_record["codes"], key=lambda item: item["rank"])
    ]


def deterministic_brief(reason_record: dict[str, Any], bucket: str) -> str:
    lines = [
        f"This above-threshold synthetic alert has {bucket} relative review priority."
    ]
    for code in sorted(reason_record["codes"], key=lambda item: item["rank"]):
        direction = "raises risk" if code["direction"] == "increases_risk" else "reduces risk"
        lines.append(f"{code['rank']}. {code['label']} {direction}; value bucket: {code['coarse_bucket']}.")
    return "\n".join(lines)


def public_reason_codes(reason_record: dict[str, Any]) -> list[dict[str, Any]]:
    """Render reason codes in the operational backend contract."""
    rows = []
    for code in sorted(reason_record["codes"], key=lambda item: item["rank"]):
        rows.append(
            {
                "feature": code["key"],
                "evidence_key": code["key"],
                "display_label": code["label"],
                "direction": "up" if code["direction"] == "increases_risk" else "down",
                "rank": int(code["rank"]),
                "value_bucket": code["coarse_bucket"],
                "shap_value": float(code["shap_value"]),
            }
        )
    return rows


def minimized_payload(reason_record: dict[str, Any], bucket: str) -> dict[str, Any]:
    return {
        "risk_bucket": bucket,
        "evidence": [
            {
                "rank": int(code["rank"]),
                "feature": code["key"],
                "display_label": code["label"],
                "direction": "up" if code["direction"] == "increases_risk" else "down",
                "value_bucket": code["coarse_bucket"],
            }
            for code in sorted(reason_record["codes"], key=lambda item: item["rank"])
        ],
    }


def _joined(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def allowed_summaries(payload: dict[str, Any]) -> tuple[str, str]:
    """Return two feature-bound, validator-checkable synthesis options."""
    evidence = payload["evidence"]
    clauses = [
        (
            f"{item['display_label']} ({str(item['value_bucket']).replace('_', ' ')}) "
            f"{'raises' if item['direction'] == 'up' else 'lowers'} risk"
        )
        for item in evidence
    ]
    upward = [
        item["display_label"] for item in evidence if item["direction"] == "up"
    ]
    downward = [
        item["display_label"] for item in evidence if item["direction"] == "down"
    ]
    if upward and downward:
        relationship = (
            f"Risk-raising evidence from {_joined(upward)} is partly offset by "
            f"counter-evidence from {_joined(downward)}."
        )
    elif upward:
        relationship = (
            f"All supplied signals raise risk, led by {evidence[0]['display_label']}."
        )
    else:
        relationship = (
            f"All supplied signals lower risk, led by {evidence[0]['display_label']}."
        )
    detailed = f"The ranked evidence shows {_joined(clauses)}."
    return detailed, relationship


def _assert_local_host(host: str) -> str:
    parsed = urlparse(host)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in LOCAL_OLLAMA_HOSTS:
        raise ValueError("Ollama host must be an explicit loopback URL")
    return host.rstrip("/")


def ollama_identity(model: str, host: str, timeout: int) -> tuple[dict[str, Any] | None, str]:
    base = _assert_local_host(host)
    session = requests.Session()
    session.trust_env = False
    try:
        version = session.get(f"{base}/api/version", timeout=timeout, allow_redirects=False)
        version.raise_for_status()
        tags = session.get(f"{base}/api/tags", timeout=timeout, allow_redirects=False)
        tags.raise_for_status()
        return {
            "host": base,
            "model": model,
            "version": version.json().get("version"),
            "models": tags.json().get("models", []),
        }, "available"
    except (requests.RequestException, ValueError) as error:
        return None, f"unavailable: {error}"


def request_structured_brief(
    payload: dict[str, Any],
    *,
    model: str,
    host: str,
    timeout: int,
    seed: int,
) -> tuple[dict[str, Any], str]:
    base = _assert_local_host(host)
    prompt = STRUCTURED_PROMPT_TEMPLATE.format(
        payload=json.dumps(
            {
                "case_evidence": payload,
                "allowed_summary_options": allowed_summaries(payload),
            },
            sort_keys=True,
        )
    )
    session = requests.Session()
    session.trust_env = False
    try:
        response = session.post(
            f"{base}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0, "seed": int(seed)},
            },
            timeout=timeout,
            allow_redirects=False,
        )
        response.raise_for_status()
        envelope = response.json()
        text = envelope.get("response") if isinstance(envelope, dict) else None
        if not isinstance(text, str):
            raise SemanticLLMUnavailable("missing response field")
        return json.loads(text), "ok"
    except (requests.RequestException, ValueError, json.JSONDecodeError) as error:
        raise SemanticLLMUnavailable(str(error)) from error


def validate_structured_brief(candidate: Any, payload: dict[str, Any]) -> ValidationResult:
    expected = payload["evidence"]
    raw_checks = {
        "schema": isinstance(candidate, dict)
        and set(candidate) == {"risk_bucket", "summary", "evidence", "action"}
        and isinstance(candidate.get("summary"), str)
        and isinstance(candidate.get("evidence"), list),
        "risk_bucket": isinstance(candidate, dict)
        and candidate.get("risk_bucket") == payload["risk_bucket"],
        "evidence_order": False,
        "grounding": False,
        "direction": False,
        "no_unauthorized_numbers": False,
        "allowed_action": isinstance(candidate, dict)
        and candidate.get("action") == "manual_review",
    }
    if not raw_checks["schema"]:
        checks = {
            "format": False,
            "completeness": False,
            "grounding": False,
            "direction": False,
        }
        return ValidationResult(False, checks, "format")

    actual = candidate["evidence"]
    expected_features = [item["feature"] for item in expected]
    raw_checks["evidence_order"] = [
        item.get("rank") for item in actual if isinstance(item, dict)
    ] == [item["rank"] for item in expected]
    raw_checks["grounding"] = (
        len(actual) == len(expected)
        and [item.get("feature") for item in actual if isinstance(item, dict)] == expected_features
        and all(item["feature"] in FEATURE_CATALOG for item in expected)
        and all(
            isinstance(item, dict)
            and set(item) == {
                "rank",
                "feature",
                "display_label",
                "direction",
                "value_bucket",
            }
            and item.get("display_label") == expected[index]["display_label"]
            and item.get("value_bucket") == expected[index]["value_bucket"]
            for index, item in enumerate(actual)
        )
    )
    raw_checks["direction"] = len(actual) == len(expected) and all(
        isinstance(item, dict)
        and item.get("direction") == expected[index]["direction"]
        for index, item in enumerate(actual)
    )
    number_scan = candidate["summary"]
    for item in expected:
        number_scan = number_scan.replace(item["display_label"], "")
    raw_checks["no_unauthorized_numbers"] = NUMBER_RE.search(number_scan) is None
    raw_checks["summary_grounding"] = candidate["summary"] in allowed_summaries(payload)
    checks = {
        "format": bool(
            raw_checks["schema"]
            and raw_checks["risk_bucket"]
            and raw_checks["no_unauthorized_numbers"]
            and raw_checks["allowed_action"]
            and raw_checks["summary_grounding"]
        ),
        "completeness": bool(
            raw_checks["evidence_order"] and len(actual) == len(expected)
        ),
        "grounding": bool(raw_checks["grounding"]),
        "direction": bool(raw_checks["direction"]),
    }
    ok = all(checks.values())
    failed = next((name for name, passed in checks.items() if not passed), None)
    return ValidationResult(ok, checks, None if ok else failed)


def wilson_ci(successes: int, n: int, z: float = 1.96) -> dict[str, float | int]:
    if n <= 0:
        return {"n": 0, "rate": 0.0, "lower": 0.0, "upper": 0.0}
    p = successes / n
    denominator = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denominator
    half_width = z * ((p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5) / denominator
    return {
        "n": int(n),
        "rate": float(p),
        "lower": float(max(0.0, centre - half_width)),
        "upper": float(min(1.0, centre + half_width)),
    }


def load_validator_corpus(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(Path(path).read_text().splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"semantic validator corpus line {line_number} is not an object")
        for field in ("id", "category", "payload", "candidate", "expected_ok"):
            if field not in row:
                raise ValueError(f"semantic validator corpus line {line_number} missing {field}")
        rows.append(row)
    if not rows:
        raise ValueError("semantic validator corpus is empty")
    return rows


def calibrate_validator(
    corpus_path: str | Path,
    *,
    validator_source: str | Path = "src/semantic/explanations.py",
) -> dict[str, Any]:
    rows = load_validator_corpus(corpus_path)
    results = []
    by_category: dict[str, dict[str, int]] = {}
    for row in rows:
        result = validate_structured_brief(row["candidate"], row["payload"])
        expected = bool(row["expected_ok"])
        matched = result.ok == expected
        category = str(row["category"])
        by_category.setdefault(category, {"n": 0, "matched": 0})
        by_category[category]["n"] += 1
        by_category[category]["matched"] += int(matched)
        results.append(
            {
                "id": row["id"],
                "category": category,
                "expected_ok": expected,
                "observed_ok": result.ok,
                "matched": matched,
                "fallback_reason": result.fallback_reason,
                "checks": result.checks,
            }
        )

    attacks = [row for row in results if row["category"] != "control"]
    controls = [row for row in results if row["category"] == "control"]
    attack_interceptions = sum(not row["observed_ok"] for row in attacks)
    control_acceptances = sum(row["observed_ok"] for row in controls)
    matched_total = sum(row["matched"] for row in results)
    artifact = {
        "schema_version": 1,
        "corpus_version": "semantic_guardrail_corpus_v1",
        "corpus_path": str(corpus_path),
        "corpus_sha256": sha256_file(corpus_path),
        "validator_source": str(validator_source),
        "validator_sha256": sha256_file(validator_source),
        "prompt_sha256": sha256_json(STRUCTURED_PROMPT_TEMPLATE),
        "n": len(results),
        "matched": matched_total,
        "passed": matched_total == len(results) and control_acceptances == len(controls),
        "control_acceptance": wilson_ci(control_acceptances, len(controls)),
        "attack_interception": wilson_ci(attack_interceptions, len(attacks)),
        "by_category": {
            category: {
                **counts,
                "match_rate": wilson_ci(counts["matched"], counts["n"]),
            }
            for category, counts in sorted(by_category.items())
        },
        "results": results,
    }
    if not artifact["passed"]:
        raise ValueError("semantic validator calibration failed")
    return artifact


def build_explanation_row(
    prediction: dict[str, Any],
    reason_record: dict[str, Any],
    *,
    threshold: float,
    llm_config: dict[str, Any],
    seed: int,
) -> tuple[dict[str, Any], dict[str, int]]:
    bucket = risk_bucket(float(prediction["score"]), threshold)
    payload = minimized_payload(reason_record, bucket)
    deterministic = deterministic_brief(reason_record, bucket)
    transport_status = "not_requested"
    llm_candidate: dict[str, Any] | None = None
    fallback = True
    validation = ValidationResult(
        False,
        {
            "schema": False,
            "risk_bucket": False,
            "evidence_order": False,
            "grounding": False,
            "direction": False,
            "no_unauthorized_numbers": False,
            "allowed_action": False,
        },
        "disabled",
    )
    if llm_config.get("enabled", True):
        try:
            request_started = time.perf_counter()
            llm_candidate, transport_status = request_structured_brief(
                payload,
                model=llm_config.get("model", "llama3:8b"),
                host=llm_config.get("host", "http://localhost:11434"),
                timeout=int(llm_config.get("timeout_seconds", 2)),
                seed=seed,
            )
            latency_ms = (time.perf_counter() - request_started) * 1000
            validation = validate_structured_brief(llm_candidate, payload)
            fallback = not validation.ok
        except SemanticLLMUnavailable as error:
            transport_status = f"transport_unavailable: {error}"
            validation = ValidationResult(False, validation.checks, "transport_unavailable")
            latency_ms = None
    else:
        latency_ms = None

    row = {
        "case_id": int(prediction["case_id"]),
        "deterministic_brief": deterministic,
        "guarded_llm_brief": deterministic if fallback else str(llm_candidate["summary"]),
        "minimized_llm_payload": payload,
        "llm_candidate": llm_candidate,
        "llm_transport_status": transport_status,
        "llm_latency_ms": latency_ms,
        "validation": {
            key: bool(validation.checks.get(key, False))
            for key in ("format", "completeness", "grounding", "direction")
        },
        "fallback": fallback,
        "fallback_reason": validation.fallback_reason,
        "delivered_brief": deterministic if fallback else str(llm_candidate["summary"]),
        "delivery": "deterministic_fallback" if fallback else "guarded_llm",
    }
    summary = {
        "rows": 1,
        "fallbacks": int(fallback),
        "transport_failures": int(transport_status.startswith("transport_unavailable")),
        "validator_failures": int(validation.fallback_reason not in {None, "transport_unavailable"}),
        "llm_latency_ms_total": 0.0 if latency_ms is None else float(latency_ms),
        "llm_latency_ms_n": int(latency_ms is not None),
    }
    return row, summary
