"""Local Ollama client for constrained evidence-to-narrative translation."""

from __future__ import annotations

import requests


class LLMUnavailable(RuntimeError):
    """Raised when the local Ollama service cannot return a usable response."""


PROMPT_TEMPLATE = """You are a fraud-analyst assistant. Convert the model evidence below into the fixed report template.

STRICT RULES:
- Mention ONLY the features listed in the evidence. Never introduce other features or reasons.
- Mention every listed feature exactly once in the EVIDENCE section and preserve rank order.
- Keep each feature's direction exactly as stated (increases risk / decreases risk).
- Keep the stated overall risk level unchanged.
- Do not state exact numbers, probabilities, or feature values.
- Output exactly this template, nothing else:

NARRATIVE: <2-3 sentences: first sentence states the overall risk level; the rest summarize every listed feature and its direction>
EVIDENCE:
- <one bullet per listed feature, in rank order, restating feature and direction>
ACTION: Recommended for manual review.

Evidence:
{evidence}
"""

SIMPLE_PROMPT_TEMPLATE = """You are a fraud-analyst assistant. Explain why this transaction was flagged, based on the evidence below.

Use this template:

NARRATIVE: <2-3 sentences>
EVIDENCE:
- <one bullet per feature>
ACTION: Recommended for manual review.

Evidence:
{evidence}
"""

PROMPT_TEMPLATES = {
    "strict": PROMPT_TEMPLATE,
    "simple": SIMPLE_PROMPT_TEMPLATE,
}


def generate_narrative(
    evidence_text: str,
    model: str = "llama3:8b",
    host: str = "http://localhost:11434",
    timeout: int = 60,
    prompt_style: str = "strict",
) -> str:
    """Generate one raw narrative; validation and fallback happen elsewhere."""
    if prompt_style not in PROMPT_TEMPLATES:
        raise ValueError(f"unknown prompt_style: {prompt_style}")
    prompt = PROMPT_TEMPLATES[prompt_style].format(evidence=evidence_text)
    try:
        response = requests.post(
            f"{host.rstrip('/')}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        text = response.json()["response"]
        if not isinstance(text, str) or not text.strip():
            raise KeyError("response")
        return text.strip()
    except (requests.RequestException, ConnectionError, KeyError, ValueError) as error:
        raise LLMUnavailable(str(error)) from error
