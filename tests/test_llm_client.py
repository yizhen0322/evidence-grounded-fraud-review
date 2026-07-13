from unittest.mock import Mock, patch

import pytest

from src.narratives.llm_client import (
    LLMUnavailable,
    PROMPT_TEMPLATE,
    PROMPT_TEMPLATES,
    generate_narrative,
)


def test_prompt_contains_rules_and_evidence():
    assert "ONLY the features listed" in PROMPT_TEMPLATE
    assert "{evidence}" in PROMPT_TEMPLATE


def test_two_prompt_arms_exist_and_differ():
    assert set(PROMPT_TEMPLATES) == {"strict", "simple"}
    assert "ONLY the features listed" in PROMPT_TEMPLATES["strict"]
    assert "ONLY the features listed" not in PROMPT_TEMPLATES["simple"]
    assert "{evidence}" in PROMPT_TEMPLATES["simple"]
    assert "NARRATIVE:" in PROMPT_TEMPLATES["simple"]


@patch("src.narratives.llm_client.requests.post")
def test_generate_narrative_calls_ollama(mock_post):
    mock_post.return_value = Mock(
        status_code=200,
        json=lambda: {"response": "NARRATIVE: ..."},
    )
    output = generate_narrative("Case ID: 1")
    assert output == "NARRATIVE: ..."
    payload = mock_post.call_args.kwargs["json"]
    assert payload["stream"] is False
    assert payload["options"]["temperature"] == 0.1
    assert "Case ID: 1" in payload["prompt"]


@patch("src.narratives.llm_client.requests.post")
def test_prompt_style_selects_template(mock_post):
    mock_post.return_value = Mock(status_code=200, json=lambda: {"response": "x"})
    generate_narrative("Case ID: 1", prompt_style="simple")
    assert "ONLY the features listed" not in mock_post.call_args.kwargs["json"][
        "prompt"
    ]


def test_unknown_prompt_style_rejected_before_http():
    with pytest.raises(ValueError, match="unknown prompt_style"):
        generate_narrative("x", prompt_style="creative")


@patch("src.narratives.llm_client.requests.post", side_effect=ConnectionError)
def test_connection_error_raises_llm_unavailable(_mock_post):
    with pytest.raises(LLMUnavailable):
        generate_narrative("x")


@patch("src.narratives.llm_client.requests.post")
def test_empty_response_raises_llm_unavailable(mock_post):
    mock_post.return_value = Mock(status_code=200, json=lambda: {"response": " "})
    with pytest.raises(LLMUnavailable):
        generate_narrative("x")
