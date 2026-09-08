"""
test_ai_service.py
------------------
Unit tests for the StaleByte AI chat service (Meta Muse Spark 1.3).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from services import ai_service


def test_prepare_messages_adds_system_prompt():
    user_msgs = [{"role": "user", "content": "Hello"}]
    prep = ai_service.prepare_messages(user_msgs)
    assert len(prep) == 2
    assert prep[0]["role"] == "system"
    assert "StaleByte Assistant" in prep[0]["content"]
    assert prep[1]["content"] == "Hello"


def test_prepare_messages_preserves_existing_system_prompt():
    user_msgs = [
        {"role": "system", "content": "Custom system prompt"},
        {"role": "user", "content": "Hello"},
    ]
    prep = ai_service.prepare_messages(user_msgs)
    assert len(prep) == 2
    assert prep[0]["content"] == "Custom system prompt"


def test_unconfigured_yields_friendly_setup_guidance(monkeypatch):
    # Prevent load_env_file() from re-reading the live .env file after the
    # delenv() calls above — _ENV_LOADED=True skips the disk read, keeping
    # the test deterministic regardless of what .env contains on disk.
    monkeypatch.setattr(ai_service, "_ENV_LOADED", True)
    monkeypatch.delenv("MUSE_SPARK_API_KEY", raising=False)
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MUSE_API_KEY", raising=False)
    assert not ai_service.is_configured()

    res = ai_service.get_chat_response([{"role": "user", "content": "Hi"}])
    assert "META_API_KEY" in res
    assert "not configured" in res.lower()


def test_configured_api_key_lookup(monkeypatch):
    monkeypatch.delenv("MUSE_SPARK_API_KEY", raising=False)
    monkeypatch.setenv("META_API_KEY", "test-secret-key-123")
    assert ai_service.is_configured()
    assert ai_service.get_api_key() == "test-secret-key-123"


def test_custom_api_base_url(monkeypatch):
    monkeypatch.setenv("META_API_BASE_URL", "https://custom.api.meta.ai/v1")
    assert ai_service.get_api_url() == "https://custom.api.meta.ai/v1/chat/completions"


def test_streaming_success(monkeypatch):
    monkeypatch.setenv("META_API_KEY", "dummy-key")

    mock_chunks = [
        b"data: {\"choices\": [{\"delta\": {\"content\": \"Stale cache \"}}]}\n\n",
        b"data: {\"choices\": [{\"delta\": {\"content\": \"occurs when \"}}]}\n\n",
        b"data: {\"choices\": [{\"delta\": {\"content\": \"timestamps collide.\"}}]}\n\n",
        b"data: [DONE]\n\n",
    ]

    mock_resp = MagicMock()
    mock_resp.__iter__.return_value = mock_chunks
    mock_resp.__enter__.return_value = mock_resp

    with patch("services.ai_service.urlopen", return_value=mock_resp):
        chunks = list(ai_service.stream_chat_completion([{"role": "user", "content": "Explain"}]))
        full = "".join(chunks)
        assert full == "Stale cache occurs when timestamps collide."


def test_http_rate_limit_handled_gracefully(monkeypatch):
    monkeypatch.setenv("META_API_KEY", "dummy-key")

    err = HTTPError("url", 429, "Too Many Requests", {}, None)
    with patch("services.ai_service.urlopen", side_effect=err):
        chunks = list(ai_service.stream_chat_completion([{"role": "user", "content": "Hi"}]))
        full = "".join(chunks)
        assert "rate limit" in full.lower()


def test_network_failure_handled_gracefully(monkeypatch):
    monkeypatch.setenv("META_API_KEY", "dummy-key")

    err = URLError("Connection refused")
    with patch("services.ai_service.urlopen", side_effect=err):
        chunks = list(ai_service.stream_chat_completion([{"role": "user", "content": "Hi"}]))
        full = "".join(chunks)
        assert "unable to connect" in full.lower()


def test_muse_spark_api_key_lookup(monkeypatch):
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MUSE_API_KEY", raising=False)
    monkeypatch.setenv("MUSE_SPARK_API_KEY", "spark-key-999")
    assert ai_service.is_configured()
    assert ai_service.get_api_key() == "spark-key-999"


def test_explain_diagnostic_unconfigured_returns_fallback(monkeypatch):
    monkeypatch.delenv("MUSE_SPARK_API_KEY", raising=False)
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MUSE_API_KEY", raising=False)

    diag = {
        "scenario": "Timestamp Collision",
        "decision": {
            "is_stale": False,
            "reason": "mtime <= t_cache. Coarse clock collision triggered silent stale reuse.",
        }
    }
    result = ai_service.explain_diagnostic(diag)
    assert "Coarse clock collision triggered silent stale reuse" in result


def test_explain_diagnostic_success(monkeypatch):
    monkeypatch.setenv("MUSE_SPARK_API_KEY", "test-spark-key")

    mock_resp = MagicMock()
    mock_payload = {
        "choices": [
            {
                "message": {
                    "content": "The naive build reused an outdated artifact because timestamps collided. StaleByte intercepted this via cryptographic hashing."
                }
            }
        ]
    }
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("services.ai_service.urlopen", return_value=mock_resp):
        diag = {"reason": "collision detected"}
        explanation = ai_service.explain_diagnostic(diag)
        assert "outdated artifact" in explanation
        assert "cryptographic hashing" in explanation


def test_explain_diagnostic_error_fallback(monkeypatch):
    monkeypatch.setenv("MUSE_SPARK_API_KEY", "test-spark-key")

    err = HTTPError("url", 500, "Internal Server Error", {}, None)
    with patch("services.ai_service.urlopen", side_effect=err):
        diag = {"reason": "fallback diagnostic message"}
        explanation = ai_service.explain_diagnostic(diag)
        assert explanation == "fallback diagnostic message"


def test_system_prompt_plain_language_and_examples():
    prompt = ai_service.SYSTEM_PROMPT
    assert "plain, everyday language" in prompt.lower()
    assert "would people buy this" in prompt.lower()
    assert "what does this actually do" in prompt.lower()
    assert "why should i care" in prompt.lower()
    assert "never dump raw comparison operators" in prompt.lower()


def test_summary_api_key_isolation(monkeypatch):
    monkeypatch.delenv("SUMMARY_API_KEY", raising=False)
    monkeypatch.setenv("MUSE_SPARK_API_KEY", "chat-key-111")
    assert ai_service.get_summary_api_key() is None
    assert ai_service.get_api_key() == "chat-key-111"

    monkeypatch.setenv("SUMMARY_API_KEY", "summary-key-222")
    assert ai_service.get_summary_api_key() == "summary-key-222"
    assert ai_service.get_api_key() == "chat-key-111"


def test_generate_result_summary_unconfigured_returns_none(monkeypatch):
    monkeypatch.delenv("SUMMARY_API_KEY", raising=False)
    res = ai_service.generate_result_summary({"decision": {"is_stale": False}})
    assert res is None


def test_generate_result_summary_success(monkeypatch):
    monkeypatch.setenv("SUMMARY_API_KEY", "test-summary-key")

    mock_resp = MagicMock()
    mock_payload = {
        "choices": [
            {
                "message": {
                    "content": "StaleByte detected that your file changed and rebuilt the program to ensure you ran the latest code."
                }
            }
        ]
    }
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("services.ai_service.urlopen", return_value=mock_resp):
        summary = ai_service.generate_result_summary({"verdict": "REBUILT", "output": 30})
        assert summary == "StaleByte detected that your file changed and rebuilt the program to ensure you ran the latest code."


def test_generate_result_summary_error_returns_none(monkeypatch):
    monkeypatch.setenv("SUMMARY_API_KEY", "test-summary-key")

    err = URLError("Network timeout")
    with patch("services.ai_service.urlopen", side_effect=err):
        summary = ai_service.generate_result_summary({"verdict": "REBUILT"})
        assert summary is None


