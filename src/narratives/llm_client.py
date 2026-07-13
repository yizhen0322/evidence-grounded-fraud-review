"""Local Ollama client for constrained evidence-to-narrative translation."""

from __future__ import annotations

import json
from dataclasses import dataclass

import requests


class LLMUnavailable(RuntimeError):
    """Raised when the local Ollama service cannot return a usable response."""


NARRATIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "narrative": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "feature": {"type": "string"},
                    "direction": {
                        "type": "string",
                        "enum": ["increases risk", "decreases risk"],
                    },
                },
                "required": ["feature", "direction"],
                "additionalProperties": False,
            },
            "minItems": 1,
        },
        "action": {
            "type": "string",
            "enum": ["Recommended for manual review."],
        },
    },
    "required": ["narrative", "evidence", "action"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class NarrativeGeneration:
    raw_response: str
    text: str


PROMPT_TEMPLATE = """You are a fraud-analyst assistant. Convert the model evidence below into the supplied JSON schema.

SHARED FORMAT RULES:
- The narrative field contains exactly two sentences and no NARRATIVE label.
- The first sentence uses exactly: This case is rated <risk level> risk.
- The evidence array contains feature and direction fields only.
- The action field uses the schema's exact value.

STRICT RULES:
- Mention ONLY the features listed in the evidence. Never introduce other features or reasons.
- Mention every listed feature exactly once in the narrative field.
- Mention every listed feature exactly once in the EVIDENCE section and preserve rank order.
- Keep each feature's direction exactly as stated (increases risk / decreases risk).
- Keep the stated overall risk level unchanged.
- Do not state exact numbers, probabilities, or feature values.
- In the narrative's second sentence, use only listed feature-direction clauses joined by commas, "and", or "while". Give every feature an explicit direction and do not add explanations.

Evidence:
{evidence}
"""

SIMPLE_PROMPT_TEMPLATE = """You are a fraud-analyst assistant. Explain why this transaction was flagged using the supplied JSON schema.

SHARED FORMAT RULES:
- The narrative field contains exactly two sentences and no NARRATIVE label.
- The first sentence uses exactly: This case is rated <risk level> risk.
- The evidence array contains feature and direction fields only.
- The action field uses the schema's exact value.

Evidence:
{evidence}
"""

PROMPT_TEMPLATES = {
    "strict": PROMPT_TEMPLATE,
    "simple": SIMPLE_PROMPT_TEMPLATE,
}


def _render_payload(payload: dict) -> str:
    if set(payload) != {"narrative", "evidence", "action"}:
        raise ValueError("structured response has unexpected fields")
    narrative = payload["narrative"]
    evidence = payload["evidence"]
    action = payload["action"]
    if not isinstance(narrative, str) or not isinstance(evidence, list):
        raise ValueError("structured response has invalid field types")
    if action != "Recommended for manual review.":
        raise ValueError("structured response has invalid action")
    bullets = []
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"feature", "direction"}:
            raise ValueError("structured evidence item is invalid")
        if item["direction"] not in {"increases risk", "decreases risk"}:
            raise ValueError("structured evidence direction is invalid")
        bullets.append(f"- {item['feature']} - {item['direction']}")
    if not bullets:
        raise ValueError("structured response has no evidence items")
    bullet_text = "\n".join(bullets)
    return (
        f"NARRATIVE: {narrative.strip()}\n"
        f"EVIDENCE:\n{bullet_text}\n"
        f"ACTION: {action}"
    )


def generate_narrative_response(
    evidence_text: str,
    model: str = "llama3:8b",
    host: str = "http://localhost:11434",
    timeout: int = 60,
    prompt_style: str = "strict",
) -> NarrativeGeneration:
    """Generate structured content and render it deterministically for validation."""
    if prompt_style not in PROMPT_TEMPLATES:
        raise ValueError(f"unknown prompt_style: {prompt_style}")
    prompt = PROMPT_TEMPLATES[prompt_style].format(evidence=evidence_text)
    try:
        response = requests.post(
            f"{host.rstrip('/')}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "format": NARRATIVE_SCHEMA,
                "stream": False,
                "options": {"temperature": 0.1},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        raw_response = response.json()["response"]
        if not isinstance(raw_response, str) or not raw_response.strip():
            raise KeyError("response")
        payload = json.loads(raw_response)
        return NarrativeGeneration(
            raw_response=raw_response,
            text=_render_payload(payload),
        )
    except (
        requests.RequestException,
        ConnectionError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise LLMUnavailable(str(error)) from error


def generate_narrative(
    evidence_text: str,
    model: str = "llama3:8b",
    host: str = "http://localhost:11434",
    timeout: int = 60,
    prompt_style: str = "strict",
) -> str:
    """Compatibility interface returning the deterministic fixed-template text."""
    return generate_narrative_response(
        evidence_text,
        model=model,
        host=host,
        timeout=timeout,
        prompt_style=prompt_style,
    ).text
