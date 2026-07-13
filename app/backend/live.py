"""Ephemeral live replay orchestration using the evaluated narrative modules."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from app.backend.artifacts import DashboardSnapshot
from app.backend.schemas import check_states
from app.backend.settings import DashboardSettings
from src.narratives.evidence import serialize_evidence
from src.narratives.guardrails import fallback_text, validate_narrative
from src.narratives.llm_client import (
    LLMUnavailable,
    generate_narrative_response,
    get_ollama_runtime,
)


class LiveNarrativeService:
    """Generate, validate, and discard one demo narrative without persistence."""

    def __init__(
        self,
        settings: DashboardSettings,
        snapshot: DashboardSnapshot,
        *,
        generate_fn: Callable[..., Any] = generate_narrative_response,
        runtime_fn: Callable[..., dict[str, Any]] = get_ollama_runtime,
    ) -> None:
        self._settings = settings
        self._snapshot = snapshot
        self._generate = generate_fn
        self._runtime = runtime_fn

    def availability(self) -> str:
        try:
            self._runtime(
                model=self._settings.config.ollama.model,
                host=self._settings.config.ollama.host,
                timeout=min(2, self._settings.config.ollama.timeout_seconds),
            )
        except LLMUnavailable:
            return "unavailable"
        return "available"

    def generate(self, case_id: int) -> dict[str, Any]:
        case = self._snapshot.case(case_id)
        record = case.guardrail_record()
        evidence = serialize_evidence(record)
        started = time.perf_counter()
        try:
            generated = self._generate(
                evidence,
                model=self._settings.config.ollama.model,
                host=self._settings.config.ollama.host,
                timeout=self._settings.config.ollama.timeout_seconds,
                prompt_style="strict",
                generation_seed=self._snapshot.generation_seed,
            )
        except LLMUnavailable:
            latency = time.perf_counter() - started
            return {
                "mode": "live_demo",
                "reported": False,
                "case_id": case.case_id,
                "raw_text": None,
                "final_text": fallback_text(record),
                "checks": check_states(None),
                "fallback": True,
                "fallback_reason": "llm_transport_unavailable",
                "latency_seconds": latency,
                "notice": "Demo-only; not a reported G5 result",
            }
        latency = time.perf_counter() - started
        raw_text = generated.text
        result = validate_narrative(raw_text, record, list(self._snapshot.known_features))
        failed = [key for key, passed in result.checks.items() if not passed]
        return {
            "mode": "live_demo",
            "reported": False,
            "case_id": case.case_id,
            "raw_text": raw_text,
            "final_text": result.final_text,
            "checks": check_states(result.checks),
            "fallback": result.fallback,
            "fallback_reason": (
                f"guardrail_failed:{','.join(failed)}" if result.fallback else None
            ),
            "latency_seconds": latency,
            "notice": "Demo-only; not a reported G5 result",
        }
