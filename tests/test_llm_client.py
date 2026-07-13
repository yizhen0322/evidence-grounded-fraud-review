from unittest.mock import Mock, patch

import pytest

from src.narratives.llm_client import (
    LLMUnavailable,
    PROMPT_TEMPLATE,
    PROMPT_TEMPLATES,
    _OLLAMA_SESSION,
    assert_local_ollama_host,
    generate_narrative,
    generate_narrative_response,
    generation_options,
    get_ollama_runtime,
)


RAW_TEXT = """NARRATIVE: This case is rated High risk. V1 increases risk.
EVIDENCE:
- V1 - increases risk
ACTION: Recommended for manual review."""


def test_prompt_contains_rules_evidence_and_plaintext_template():
    assert "ONLY the features listed" in PROMPT_TEMPLATE
    assert "NARRATIVE:" in PROMPT_TEMPLATE
    assert "{evidence}" in PROMPT_TEMPLATE


def test_two_prompt_arms_exist_and_differ_but_share_template_shape():
    assert set(PROMPT_TEMPLATES) == {"strict", "simple"}
    assert "ONLY the features listed" in PROMPT_TEMPLATES["strict"]
    assert "ONLY the features listed" not in PROMPT_TEMPLATES["simple"]
    assert "NARRATIVE:" in PROMPT_TEMPLATES["simple"]
    assert "{evidence}" in PROMPT_TEMPLATES["simple"]


@patch("src.narratives.llm_client._OLLAMA_SESSION.post")
def test_generate_narrative_calls_ollama_with_seed_and_no_schema(mock_post):
    mock_post.return_value = Mock(
        status_code=200,
        json=lambda: {"response": RAW_TEXT},
    )
    output = generate_narrative("Case ID: 1", generation_seed=46)
    assert output == RAW_TEXT
    payload = mock_post.call_args.kwargs["json"]
    assert payload["stream"] is False
    assert payload["options"] == {"temperature": 0.1, "seed": 46}
    assert "format" not in payload
    assert "Case ID: 1" in payload["prompt"]
    assert mock_post.call_args.kwargs["allow_redirects"] is False


@patch("src.narratives.llm_client._OLLAMA_SESSION.post")
def test_prompt_style_selects_template(mock_post):
    mock_post.return_value = Mock(status_code=200, json=lambda: {"response": RAW_TEXT})
    generate_narrative("Case ID: 1", prompt_style="simple")
    assert "ONLY the features listed" not in mock_post.call_args.kwargs["json"][
        "prompt"
    ]


def test_unknown_prompt_style_rejected_before_http():
    with pytest.raises(ValueError, match="unknown prompt_style"):
        generate_narrative("x", prompt_style="creative")


@pytest.mark.parametrize(
    "host",
    [
        "https://example.com:11434",
        "http://localhost.evil.example:11434",
        "http://192.168.1.20:11434",
    ],
)
def test_non_loopback_ollama_hosts_are_rejected(host):
    with pytest.raises(ValueError, match="loopback"):
        assert_local_ollama_host(host)
    with pytest.raises(ValueError, match="loopback"):
        generate_narrative("x", host=host)


def test_loopback_ollama_hosts_are_accepted():
    assert assert_local_ollama_host("http://localhost:11434")
    assert assert_local_ollama_host("http://127.0.0.1:11434")
    assert assert_local_ollama_host("http://[::1]:11434")


def test_ollama_session_ignores_proxy_environment():
    assert _OLLAMA_SESSION.trust_env is False


@patch("src.narratives.llm_client._OLLAMA_SESSION.post", side_effect=ConnectionError)
def test_connection_error_raises_llm_unavailable(_mock_post):
    with pytest.raises(LLMUnavailable):
        generate_narrative("x")


@patch("src.narratives.llm_client._OLLAMA_SESSION.post")
def test_empty_model_text_is_preserved_for_guardrail_judgment(mock_post):
    mock_post.return_value = Mock(status_code=200, json=lambda: {"response": ""})
    generation = generate_narrative_response("x")
    assert generation.raw_response == ""
    assert generation.text == ""


@patch("src.narratives.llm_client._OLLAMA_SESSION.post")
def test_missing_api_response_field_is_transport_unavailable(mock_post):
    mock_post.return_value = Mock(status_code=200, json=lambda: {})
    with pytest.raises(LLMUnavailable):
        generate_narrative("x")


@patch("src.narratives.llm_client._OLLAMA_SESSION.post")
def test_raw_response_is_the_unmodified_candidate(mock_post):
    raw = "not-json and not a valid template"
    mock_post.return_value = Mock(status_code=200, json=lambda: {"response": raw})
    generation = generate_narrative_response("Case ID: 1")
    assert generation.raw_response == raw
    assert generation.text == raw


def test_generation_options_are_complete_and_seeded():
    assert generation_options(42) == {"temperature": 0.1, "seed": 42}


@patch("src.narratives.llm_client._OLLAMA_SESSION.post")
@patch("src.narratives.llm_client._OLLAMA_SESSION.get")
def test_runtime_identity_records_version_digest_and_configuration(
    mock_get,
    mock_post,
):
    mock_get.side_effect = [
        Mock(status_code=200, json=lambda: {"version": "0.31.1"}),
        Mock(
            status_code=200,
            json=lambda: {
                "models": [
                    {
                        "name": "llama3:8b",
                        "model": "llama3:8b",
                        "digest": "abc123",
                        "size": 10,
                        "details": {"parameter_size": "8B"},
                    }
                ]
            },
        ),
    ]
    mock_post.return_value = Mock(
        status_code=200,
        json=lambda: {
            "parameters": "temperature 0.8",
            "template": "template",
            "system": "",
            "modelfile": "FROM sha256-abc123",
        },
    )
    identity = get_ollama_runtime("llama3:8b")
    assert identity["version"] == "0.31.1"
    assert identity["digest"] == "abc123"
    assert identity["model_configuration"]["show_payload_sha256"]
    assert identity["model_configuration"]["parameters"] == "temperature 0.8"
    assert all(
        call.kwargs["allow_redirects"] is False
        for call in mock_get.call_args_list
    )
    assert mock_post.call_args.kwargs["allow_redirects"] is False


@patch("src.narratives.llm_client._OLLAMA_SESSION.post")
@patch("src.narratives.llm_client._OLLAMA_SESSION.get")
def test_runtime_identity_rejects_missing_model(mock_get, mock_post):
    mock_get.side_effect = [
        Mock(status_code=200, json=lambda: {"version": "0.31.1"}),
        Mock(status_code=200, json=lambda: {"models": []}),
    ]
    mock_post.return_value = Mock(status_code=200, json=lambda: {})
    with pytest.raises(LLMUnavailable, match="not installed"):
        get_ollama_runtime("missing")
