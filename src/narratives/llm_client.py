"""Local Ollama client for raw evidence-to-narrative generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests


_OLLAMA_SESSION = requests.Session()
_OLLAMA_SESSION.trust_env = False


class LLMUnavailable(RuntimeError):
    """Raised only when the local Ollama service or API transport is unavailable."""


@dataclass(frozen=True)
class NarrativeGeneration:
    """Preserve the exact model text used by both delivery policies."""

    raw_response: str
    text: str


PROMPT_TEMPLATE = """You are a fraud-analyst assistant. Translate the supplied evidence into a concise narrative.

Return ONLY plain text in this exact template. Do not use Markdown fences, headings before NARRATIVE, or Unicode bullets:
NARRATIVE: This case is rated <High|Medium|Low> risk. <one evidence sentence>
EVIDENCE:
- <feature> - <increases risk|decreases risk>
ACTION: Recommended for manual review.

STRICT RULES:
- Mention ONLY the features listed in the evidence. Never introduce other features or reasons.
- Mention every listed feature exactly once in the narrative sentence.
- Include every listed feature exactly once in EVIDENCE and preserve rank order.
- Keep each feature's direction exactly as stated (increases risk / decreases risk).
- Keep the stated overall risk level unchanged.
- Do not state exact numbers, probabilities, or feature values.
- Join feature-direction clauses only with commas, semicolons, "and", "while", "but", or "whereas".
- Give every feature an explicit direction and do not add explanations.

Evidence:
{evidence}
"""

SIMPLE_PROMPT_TEMPLATE = """You are a fraud-analyst assistant. Explain why this transaction was flagged from the supplied evidence.

Return ONLY plain text in this exact template. Do not use Markdown fences, headings before NARRATIVE, or Unicode bullets:
NARRATIVE: This case is rated <High|Medium|Low> risk. <one evidence sentence>
EVIDENCE:
- <feature> - <increases risk|decreases risk>
ACTION: Recommended for manual review.

Evidence:
{evidence}
"""

PROMPT_TEMPLATES = {
    "strict": PROMPT_TEMPLATE,
    "simple": SIMPLE_PROMPT_TEMPLATE,
}
LOCAL_OLLAMA_HOSTS = {"localhost", "127.0.0.1", "::1"}


def assert_local_ollama_host(host: str) -> str:
    """Reject any Ollama endpoint that could send evidence off-device."""
    parsed = urlparse(host)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in LOCAL_OLLAMA_HOSTS:
        raise ValueError("Ollama host must be an explicit loopback URL")
    return host.rstrip("/")


def generation_options(seed: int) -> dict[str, int | float]:
    """Return the complete generation option set recorded in G5 provenance."""
    return {"temperature": 0.1, "seed": int(seed)}


def _sha256_value(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def get_ollama_runtime(
    model: str,
    host: str = "http://localhost:11434",
    timeout: int = 10,
) -> dict[str, Any]:
    """Resolve the mutable model tag to the exact local Ollama digest."""
    base = assert_local_ollama_host(host)
    try:
        version_response = _OLLAMA_SESSION.get(
            f"{base}/api/version",
            timeout=timeout,
            allow_redirects=False,
        )
        version_response.raise_for_status()
        tags_response = _OLLAMA_SESSION.get(
            f"{base}/api/tags",
            timeout=timeout,
            allow_redirects=False,
        )
        tags_response.raise_for_status()
        show_response = _OLLAMA_SESSION.post(
            f"{base}/api/show",
            json={"model": model},
            timeout=timeout,
            allow_redirects=False,
        )
        show_response.raise_for_status()
        version_payload = version_response.json()
        tags_payload = tags_response.json()
        show_payload = show_response.json()
    except (requests.RequestException, ConnectionError, ValueError) as error:
        raise LLMUnavailable(f"Ollama runtime identity unavailable: {error}") from error

    version = version_payload.get("version")
    models = tags_payload.get("models")
    if (
        not isinstance(version, str)
        or not isinstance(models, list)
        or not isinstance(show_payload, dict)
    ):
        raise LLMUnavailable("Ollama runtime identity response is malformed")
    match = next(
        (
            item
            for item in models
            if isinstance(item, dict)
            and model in {item.get("name"), item.get("model")}
        ),
        None,
    )
    if match is None or not isinstance(match.get("digest"), str):
        raise LLMUnavailable(f"Ollama model is not installed: {model}")
    return {
        "host": base,
        "version": version,
        "model": model,
        "digest": match["digest"],
        "size": match.get("size"),
        "modified_at": match.get("modified_at"),
        "details": match.get("details", {}),
        "capabilities": match.get("capabilities", []),
        "model_configuration": {
            "show_payload_sha256": _sha256_value(show_payload),
            "parameters": show_payload.get("parameters", ""),
            "template_sha256": _sha256_value(show_payload.get("template", "")),
            "system_sha256": _sha256_value(show_payload.get("system", "")),
            "modelfile_sha256": _sha256_value(
                show_payload.get("modelfile", "")
            ),
        },
    }


def generate_narrative_response(
    evidence_text: str,
    model: str = "llama3:8b",
    host: str = "http://localhost:11434",
    timeout: int = 60,
    prompt_style: str = "strict",
    generation_seed: int = 42,
) -> NarrativeGeneration:
    """Return the exact raw model text without parsing or normalization."""
    if prompt_style not in PROMPT_TEMPLATES:
        raise ValueError(f"unknown prompt_style: {prompt_style}")
    base = assert_local_ollama_host(host)
    prompt = PROMPT_TEMPLATES[prompt_style].format(evidence=evidence_text)
    try:
        response = _OLLAMA_SESSION.post(
            f"{base}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": generation_options(generation_seed),
            },
            timeout=timeout,
            allow_redirects=False,
        )
        response.raise_for_status()
        envelope = response.json()
    except (requests.RequestException, ConnectionError, ValueError) as error:
        raise LLMUnavailable(str(error)) from error

    raw_response = envelope.get("response") if isinstance(envelope, dict) else None
    if not isinstance(raw_response, str):
        raise LLMUnavailable("Ollama API response is missing a string response field")
    return NarrativeGeneration(raw_response=raw_response, text=raw_response)


def generate_narrative(
    evidence_text: str,
    model: str = "llama3:8b",
    host: str = "http://localhost:11434",
    timeout: int = 60,
    prompt_style: str = "strict",
    generation_seed: int = 42,
) -> str:
    """Compatibility interface returning the exact raw model text."""
    return generate_narrative_response(
        evidence_text,
        model=model,
        host=host,
        timeout=timeout,
        prompt_style=prompt_style,
        generation_seed=generation_seed,
    ).text
