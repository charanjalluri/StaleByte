"""
ai_service.py
-------------
AI Chat Service for StaleByte using Meta's Muse Spark 1.3 model via
an OpenAI-compatible chat completions endpoint.

Features:
- Encapsulated system prompt on cache staleness and runtime correctness
- Server-side API key retrieval via META_API_KEY / MUSE_API_KEY env vars
- Streaming response generator (SSE) with graceful error handling
- Friendly, plain-language error messages on network or rate limit issues
"""

from __future__ import annotations

import json
import os
from typing import Any, Generator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Model configuration
MODEL_ID = "muse-spark-1.3"
DEFAULT_BASE_URL = "https://api.meta.ai/v1"

SYSTEM_PROMPT = (
    "You are the StaleByte Assistant. Your goal is to explain StaleByte clearly to anyone, "
    "from judges, investors, and business leaders to first-time visitors and engineers.\n\n"
    "Core Voice & Tone Rules:\n"
    "1. Always answer in plain, everyday language first. Do not use jargon, code syntax, "
    "or acronyms without immediate, plain-language explanation.\n"
    "2. Explain WHAT the problem is and WHY it matters in terms a non-technical person understands. "
    "For example: 'Imagine editing a file and your program keeps running the old version without "
    "telling you — that's the bug this catches.'\n"
    "3. Only introduce a technical term (such as 'mtime', 'SHA-256', 'hash', 'invalidation', or 'bytecode') "
    "if the visitor's own question is clearly technical (they use those terms themselves). Otherwise, "
    "remain in everyday plain language throughout.\n"
    "4. Never dump raw comparison operators (e.g. 'mtime <= t_cache'), code snippets, or raw implementation "
    "details unless explicitly asked 'how does it work technically'.\n"
    "5. Keep answers short: 3 to 5 sentences for general questions. Only provide longer answers if the "
    "visitor explicitly asks for technical depth.\n\n"
    "Style Examples:\n\n"
    "Q: Would people buy this?\n"
    "A: Yes, software teams and developer companies invest heavily in build reliability and productivity tools. "
    "When build systems silently reuse old code because timestamps appear identical, engineers can waste hours "
    "or days hunting down phantom bugs that have already been fixed. By guaranteeing that every run executes the "
    "exact code written on disk with zero guesswork, StaleByte eliminates expensive debugging time and prevents "
    "broken code from slipping into production.\n\n"
    "Q: What does this actually do?\n"
    "A: StaleByte ensures that when you change a file and run your program, it always runs your new code instead "
    "of secretly reusing an outdated version. Standard build systems trust file clocks, which easily get fooled "
    "if edits happen too quickly or if different computers have unsynchronized clocks. StaleByte creates a unique "
    "digital fingerprint of the code content itself, so it never gets tricked into running stale files.\n\n"
    "Q: Why should I care?\n"
    "A: Silent errors are the most dangerous and expensive problems in software development because no warning or "
    "error message appears. You might believe you fixed a critical bug, while your system is quietly executing the "
    "broken version behind your back. StaleByte gives teams complete confidence that their software is always running "
    "the true, current code.\n"
)


from pathlib import Path


_ENV_LOADED = False


def load_env_file() -> None:
    """Load key-value pairs from .env once on startup without external dependencies."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True

    search_dirs = [Path.cwd(), Path(__file__).parent.parent, Path(__file__).parent]
    seen = set()
    for directory in search_dirs:
        try:
            resolved = directory.resolve()
        except Exception:
            resolved = directory
        if resolved in seen:
            continue
        seen.add(resolved)
        env_file = resolved / ".env"
        if env_file.is_file():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
            except Exception:
                pass


# Auto-load on import
load_env_file()


def get_api_key() -> str | None:
    """Retrieve the interactive chat/explain API key from environment variables."""
    return (
        os.environ.get("MUSE_SPARK_API_KEY")
        or os.environ.get("META_API_KEY")
        or os.environ.get("MUSE_API_KEY")
    )


def get_summary_api_key() -> str | None:
    """Retrieve the dedicated API key for automatic route summaries (SUMMARY_API_KEY)."""
    return os.environ.get("SUMMARY_API_KEY")


def get_api_url() -> str:
    """Retrieve the chat completions endpoint URL."""
    base = os.environ.get("META_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def is_configured() -> bool:
    """Return True if an API key is present in the environment."""
    return bool(get_api_key())


def check_ai_health(timeout: float = 3.0) -> dict[str, Any]:
    """
    Perform a lightweight health check on the AI endpoint and configuration.
    Returns status details including reachability and configuration.
    """
    endpoint = get_api_url()
    api_key = get_api_key()
    configured = bool(api_key)

    headers = {
        "User-Agent": "StaleByte-HealthCheck/1.0",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = Request(endpoint, headers=headers, method="GET")

    try:
        with urlopen(req, timeout=timeout) as resp:
            return {
                "configured": configured,
                "reachable": True,
                "endpoint": endpoint,
                "model": MODEL_ID,
                "status": "ok",
                "message": f"Endpoint reachable and responded with HTTP {resp.status}."
            }
    except HTTPError as err:
        if err.code in (401, 403):
            status = "unauthorized" if configured else "unconfigured"
            msg = "Authentication failed (invalid API key)." if configured else "Endpoint reachable, no API key configured."
            return {
                "configured": configured,
                "reachable": True,
                "endpoint": endpoint,
                "model": MODEL_ID,
                "status": status,
                "message": msg
            }
        elif err.code in (400, 405):
            return {
                "configured": configured,
                "reachable": True,
                "endpoint": endpoint,
                "model": MODEL_ID,
                "status": "ok" if configured else "unconfigured",
                "message": f"Endpoint reachable (HTTP {err.code})."
            }
        else:
            return {
                "configured": configured,
                "reachable": True,
                "endpoint": endpoint,
                "model": MODEL_ID,
                "status": f"http_{err.code}",
                "message": f"Endpoint reachable, returned HTTP {err.code}."
            }
    except (URLError, TimeoutError) as err:
        return {
            "configured": configured,
            "reachable": False,
            "endpoint": endpoint,
            "model": MODEL_ID,
            "status": "unreachable",
            "message": f"Endpoint unreachable ({err})."
        }
    except Exception as exc:
        return {
            "configured": configured,
            "reachable": False,
            "endpoint": endpoint,
            "model": MODEL_ID,
            "status": "error",
            "message": f"Health check failed: {exc}."
        }


def prepare_messages(user_messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Ensure the StaleByte system prompt is present at the beginning of the conversation."""
    if not isinstance(user_messages, list):
        user_messages = []
    filtered = [m for m in user_messages if isinstance(m, dict) and m.get("role") in ("user", "assistant", "system")]
    if not filtered or filtered[0].get("role") != "system":
        return [{"role": "system", "content": SYSTEM_PROMPT}] + filtered
    return filtered


def stream_chat_completion(
    messages: list[dict[str, str]],
    timeout: float = 30.0,
) -> Generator[str, None, None]:
    """
    Stream chat completion chunks from the Meta Model API.
    Yields plain text delta chunks.
    """
    api_key = get_api_key()
    if not api_key:
        yield (
            "The AI assistant is not configured yet. "
            "To enable live answers, set the META_API_KEY environment variable on your server."
        )
        return

    payload: dict[str, Any] = {
        "model": MODEL_ID,
        "messages": prepare_messages(messages),
        "stream": True,
    }

    req = Request(
        get_api_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "StaleByte-Assistant/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            buffer = ""
            for raw_line in resp:
                line = raw_line.decode("utf-8")
                buffer += line
                while "\n" in buffer:
                    line_to_process, buffer = buffer.split("\n", 1)
                    line_to_process = line_to_process.strip()
                    if not line_to_process or not line_to_process.startswith("data:"):
                        continue
                    data_str = line_to_process[len("data:"):].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        chunk_json = json.loads(data_str)
                        choices = chunk_json.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue

    except HTTPError as err:
        if err.code in (401, 403):
            yield "Authentication failed: please verify that the META_API_KEY environment variable is valid."
        elif err.code == 429:
            yield "The assistant is temporarily busy (rate limit reached). Please try again in a few moments."
        elif err.code >= 500:
            yield "The AI service encountered a temporary server error. Please try again shortly."
        else:
            yield f"The assistant encountered an issue (Status code: {err.code}). Please try again later."
    except (URLError, TimeoutError):
        yield "Unable to connect to the AI service. Please check your network connection and server settings."
    except Exception:
        yield "An unexpected error occurred while communicating with the assistant. Please try again."


def get_chat_response(messages: list[dict[str, str]], timeout: float = 30.0) -> str:
    """Non-streaming helper that collects all tokens into a single string."""
    return "".join(stream_chat_completion(messages, timeout=timeout))


EXPLAIN_SYSTEM_PROMPT = (
    "You are an expert technical communicator for StaleByte explaining compiled cache staleness. "
    "Explain the specific staleness diagnostic (such as filesystem timestamp resolution collision "
    "or clock skew) in plain, non-technical language. "
    "Provide your explanation in 2 to 4 sentences. "
    "Do not invent any facts not present in the diagnostic data. "
    "Focus on why the cache was reused or invalidated, and the consequence of that decision."
)


def explain_diagnostic(diagnostic_data: dict[str, Any], timeout: float = 15.0) -> str:
    """
    Generate a 2-4 sentence plain-English explanation of the staleness diagnostic using
    Meta Muse Spark 1.3 via an OpenAI-compatible endpoint.
    If the API key is unconfigured, or if the API call fails or times out,
    returns a graceful fallback explanation based directly on the diagnostic reason.
    Staleness decisions remain 100% deterministic; this service only provides presentation text.
    """
    # Deterministic fallback text derivation
    fallback_reason = diagnostic_data.get("reason") or diagnostic_data.get("diagnostic", "")
    if not fallback_reason and "decision" in diagnostic_data:
        dec = diagnostic_data["decision"]
        if isinstance(dec, dict):
            fallback_reason = dec.get("reason", "")
    if not fallback_reason:
        fallback_reason = "Cache evaluation completed based on filesystem timestamps and cryptographic verification."

    api_key = get_api_key()
    if not api_key:
        return fallback_reason

    user_content = (
        "Please explain this cache invalidation diagnostic in 2 to 4 plain, non-technical sentences:\n"
        f"{json.dumps(diagnostic_data, indent=2)}"
    )

    payload: dict[str, Any] = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": EXPLAIN_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "temperature": 0.2,
    }

    req = Request(
        get_api_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "StaleByte-Explainer/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "").strip()
                if content:
                    return content
        return fallback_reason
    except Exception:
        return fallback_reason


def generate_result_summary(result_data: dict[str, Any], timeout: float = 25.0) -> str | None:
    """
    Generate an automatic plain-language summary of finished result data using Muse Spark 1.3
    authenticated via SUMMARY_API_KEY.
    Returns None if SUMMARY_API_KEY is not configured, or if the API call fails or times out.
    Deterministic staleness decisions remain 100% independent and unaffected.
    """
    api_key = get_summary_api_key()
    if not api_key:
        return None

    user_prompt = (
        "In 2 to 3 plain-language sentences without code syntax, jargon, or comparison operators, "
        "summarize this execution result for a non-technical reader, explaining what happened and whether "
        "the correct code was executed:\n"
        f"{json.dumps(result_data, default=str)}"
    )

    payload: dict[str, Any] = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "temperature": 0.2,
    }

    req = Request(
        get_api_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "StaleByte-AutoSummary/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "").strip()
                if content:
                    return content
        return None
    except Exception:
        return None


