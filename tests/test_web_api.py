"""
test_web_api.py
---------------
Integration tests for the web API server endpoints.
"""

import json
import socket
import sys
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from lib import cache_manager
from web.app import create_server


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def web_server():
    port = find_free_port()
    server = create_server("127.0.0.1", port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    yield base_url
    server.shutdown()
    server.server_close()


@pytest.fixture()
def tmp_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(cache_manager, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(cache_manager, "ARTIFACT_PATH", tmp_path / "artifact.json")
    monkeypatch.setattr(cache_manager, "METADATA_PATH", tmp_path / "metadata.json")
    return tmp_path


def test_api_status(web_server, tmp_cache):
    with urlopen(f"{web_server}/api/status") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "cache_exists" in data
        assert "simulated_mtime" in data


def test_api_run_collision(web_server, tmp_cache):
    req = Request(
        f"{web_server}/api/run/collision",
        data=json.dumps({"input_value": 10}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["naive_execution"]["result"] == 20
        assert data["smart_execution"]["result"] == 30


def test_api_run_normal(web_server, tmp_cache):
    req = Request(
        f"{web_server}/api/run/normal",
        data=json.dumps({"input_value": 10}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["result"] == 20


def test_api_run_skew(web_server, tmp_cache):
    req = Request(
        f"{web_server}/api/run/skew",
        data=json.dumps({"input_value": 10}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["result"] == 20


def test_static_index_html(web_server):
    for route in ("/", "/index.html", "/dashboard", "/demo"):
        with urlopen(f"{web_server}{route}") as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "StaleByte" in content
            assert "Timestamp-Only Strategy" in content
            assert "chat-widget" in content
            assert "StaleByte Assistant" in content


def test_api_chat_status(web_server):
    with urlopen(f"{web_server}/api/chat/status") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "configured" in data
        assert data["model"] == "muse-spark-1.3"


def test_api_chat_unconfigured_streaming(web_server, monkeypatch):
    monkeypatch.delenv("MUSE_SPARK_API_KEY", raising=False)
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MUSE_API_KEY", raising=False)
    req = Request(
        f"{web_server}/api/chat",
        data=json.dumps({
            "messages": [{"role": "user", "content": "What is cache staleness?"}],
            "stream": True,
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        lines = []
        for raw in resp:
            line = raw.decode("utf-8")
            lines.append(line)
            if "[DONE]" in line:
                break
        content = "".join(lines)
        assert "META_API_KEY" in content
        assert "[DONE]" in content


def test_api_chat_non_streaming(web_server, monkeypatch):
    monkeypatch.delenv("MUSE_SPARK_API_KEY", raising=False)
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MUSE_API_KEY", raising=False)
    req = Request(
        f"{web_server}/api/chat",
        data=json.dumps({
            "messages": [{"role": "user", "content": "Explain timestamp collisions"}],
            "stream": False,
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "reply" in data
        assert data["model"] == "muse-spark-1.3"
        assert "META_API_KEY" in data["reply"]


def test_api_explain_endpoint(web_server, monkeypatch):
    monkeypatch.delenv("MUSE_SPARK_API_KEY", raising=False)
    monkeypatch.delenv("META_API_KEY", raising=False)
    monkeypatch.delenv("MUSE_API_KEY", raising=False)
    payload = {
        "scenario": "Timestamp Collision",
        "decision": {
            "is_stale": False,
            "reason": "mtime <= t_cache. Identical timestamps caused silent stale execution.",
        }
    }
    # Test POST /explain
    req1 = Request(
        f"{web_server}/explain",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req1) as resp:
        assert resp.status == 200
        data1 = json.loads(resp.read().decode("utf-8"))
        assert "explanation" in data1
        assert data1["model"] == "muse-spark-1.3"
        assert "Identical timestamps" in data1["explanation"]

    # Test POST /api/explain alias
    req2 = Request(
        f"{web_server}/api/explain",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req2) as resp:
        assert resp.status == 200
        data2 = json.loads(resp.read().decode("utf-8"))
        assert "explanation" in data2
        assert data2["model"] == "muse-spark-1.3"


def test_static_html_contains_interactive_elements(web_server):
    """Verify interactive dashboard elements across /, /dashboard, and /demo."""
    for route in ("/", "/dashboard", "/demo"):
        with urlopen(f"{web_server}{route}") as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "btn-explain-naive" in content
            assert "btn-explain-smart" in content
            assert "naive-ai-box" in content
            assert "smart-ai-box" in content
            assert "Explain this" in content
            assert "upload-check" in content
            assert "upload-dropzone" in content
            assert "btn-upload-check" in content
            assert "source-file-input" in content
            assert "chat-widget" in content
            assert "chat-panel" in content


def test_send_error_has_content_length(web_server):
    # Route not found returns 404 with Content-Length header
    req = Request(f"{web_server}/non-existent-route")
    with pytest.raises(HTTPError) as exc_info:
        urlopen(req)
    err = exc_info.value
    assert err.code == 404
    assert "Content-Length" in err.headers
    raw_body = err.read()
    assert int(err.headers["Content-Length"]) == len(raw_body)


def test_api_malformed_json_body_returns_400(web_server):
    req = Request(
        f"{web_server}/api/run/collision",
        data=b"{not valid json...",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(HTTPError) as exc_info:
        urlopen(req)
    err = exc_info.value
    assert err.code == 400
    assert "Content-Length" in err.headers
    data = json.loads(err.read().decode("utf-8"))
    assert "malformed json" in data["error"].lower()


def test_api_non_dict_json_body_returns_400(web_server):
    req = Request(
        f"{web_server}/api/run/collision",
        data=json.dumps([1, 2, 3]).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(HTTPError) as exc_info:
        urlopen(req)
    err = exc_info.value
    assert err.code == 400
    data = json.loads(err.read().decode("utf-8"))
    assert "must be a json object" in data["error"].lower()


def test_api_chat_invalid_messages_type(web_server):
    req = Request(
        f"{web_server}/api/chat",
        data=json.dumps({"messages": "not a list", "stream": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(HTTPError) as exc_info:
        urlopen(req)
    err = exc_info.value
    assert err.code == 400
    data = json.loads(err.read().decode("utf-8"))
    assert "'messages' must be a list" in data["error"]


def test_startup_ai_service_check():
    from web.app import check_startup_ai_service
    health = check_startup_ai_service()
    assert "configured" in health
    assert "reachable" in health
    assert "model" in health
    assert health["model"] == "muse-spark-1.3"


def test_api_clean_cache(web_server):
    req = Request(
        f"{web_server}/api/clean",
        data=b"{}",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["cleared"] is True


def test_core_routes_include_ai_summary_field(web_server, tmp_cache, monkeypatch):
    # Ensure SUMMARY_API_KEY is not set: ai_summary should be None (null in JSON), core output intact
    monkeypatch.delenv("SUMMARY_API_KEY", raising=False)

    # 1. /api/upload-check
    req = Request(
        f"{web_server}/api/upload-check",
        data=json.dumps({"filename": "test.src", "content": "operation=multiply\nfactor=5"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "decision" in data
        assert "reason" in data
        assert "hash" in data
        assert "verdict" in data
        assert "ai_summary" in data
        assert data["ai_summary"] is None

    # 2. /api/run/collision
    req = Request(
        f"{web_server}/api/run/collision",
        data=json.dumps({"input_value": 10}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "decision" in data
        assert "reason" in data
        assert "hash" in data
        assert "output" in data
        assert "verdict" in data
        assert "ai_summary" in data
        assert data["ai_summary"] is None

    # 3. /api/run/normal
    req = Request(
        f"{web_server}/api/run/normal",
        data=json.dumps({"input_value": 10}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "decision" in data
        assert "reason" in data
        assert "hash" in data
        assert "output" in data
        assert "verdict" in data
        assert "ai_summary" in data
        assert data["ai_summary"] is None

    # 4. /api/run/skew
    req = Request(
        f"{web_server}/api/run/skew",
        data=json.dumps({"input_value": 10}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "decision" in data
        assert "reason" in data
        assert "hash" in data
        assert "output" in data
        assert "verdict" in data
        assert "ai_summary" in data
        assert data["ai_summary"] is None

    # 5. /api/check
    req = Request(
        f"{web_server}/api/check",
        data=json.dumps({"content": "operation=multiply\nfactor=4"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "decision" in data
        assert "reason" in data
        assert "hash" in data
        assert "verdict" in data
        assert "ai_summary" in data
        assert data["ai_summary"] is None

    # 6. /api/build
    req = Request(
        f"{web_server}/api/build",
        data=json.dumps({"content": "operation=multiply\nfactor=4", "input_value": 5}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "decision" in data
        assert "reason" in data
        assert "hash" in data
        assert "output" in data
        assert data["output"] == 20
        assert "verdict" in data
        assert "ai_summary" in data
        assert data["ai_summary"] is None


def test_core_route_with_summary_api_key_mocked(web_server, tmp_cache, monkeypatch):
    from unittest.mock import patch
    with patch("services.ai_service.generate_result_summary", return_value="The file was checked and validated successfully."):
        req = Request(
            f"{web_server}/api/upload-check",
            data=json.dumps({"filename": "demo.src", "content": "operation=multiply\nfactor=7"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["ai_summary"] == "The file was checked and validated successfully."
            assert "decision" in data
            assert "reason" in data
            assert "hash" in data
            assert "verdict" in data


def test_core_route_ai_failure_does_not_break_result(web_server, tmp_cache, monkeypatch):
    from unittest.mock import patch
    # Even if generate_result_summary raises unexpectedly, the server must not break core output
    with patch("services.ai_service.generate_result_summary", side_effect=RuntimeError("Unexpected AI server crash")):
        req = Request(
            f"{web_server}/api/upload-check",
            data=json.dumps({"filename": "resilience.src", "content": "operation=multiply\nfactor=9"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            # ai_summary must be null/None, not an unhandled 500 error
            assert data["ai_summary"] is None
            # Core deterministic fields must be intact and correct
            assert "decision" in data
            assert "reason" in data
            assert "hash" in data
            assert "verdict" in data
            assert data["robust"]["is_stale"] is True or data["robust"]["is_stale"] is False







