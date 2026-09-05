"""
test_upload_check.py
--------------------
Tests for real file upload and staleness verification route (/api/upload-check).
"""

from __future__ import annotations

import json
import socket
import sys
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services import simulation_service
from web.app import create_server


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def web_server(tmp_path_factory):
    port = find_free_port()
    server = create_server("127.0.0.1", port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    yield base_url
    server.shutdown()
    server.server_close()


@pytest.fixture(autouse=True)
def isolate_ai_summary(monkeypatch):
    monkeypatch.delenv("SUMMARY_API_KEY", raising=False)


def test_upload_check_first_upload_and_unchanged_reupload(web_server):
    filename = "custom_tool.src"
    content_v1 = "operation=multiply\nfactor=10"

    # First upload: initial check
    req1 = Request(
        f"{web_server}/api/upload-check",
        data=json.dumps({"filename": filename, "content": content_v1}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req1, timeout=5) as resp:
        assert resp.status == 200
        data1 = json.loads(resp.read().decode("utf-8"))
        assert data1["filename"] == filename
        assert data1["size"] == len(content_v1.encode("utf-8"))
        assert data1["naive"]["is_stale"] is True  # No prior artifact
        assert data1["robust"]["is_stale"] is True
        assert data1["rebuilt"] is True

    # Second upload: unchanged re-upload should report CACHE HIT!
    req2 = Request(
        f"{web_server}/api/upload-check",
        data=json.dumps({"filename": filename, "content": content_v1}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req2, timeout=5) as resp:
        assert resp.status == 200
        data2 = json.loads(resp.read().decode("utf-8"))
        assert data2["robust"]["is_stale"] is False
        assert "HIT" in data2["robust"]["verdict"]
        assert data2["cache_state"]["was_cached"] is True
        assert data2["content_hash"] == data1["content_hash"]

    # Third upload: edited re-upload should report CACHE MISS!
    content_v2 = "operation=multiply\nfactor=25"
    req3 = Request(
        f"{web_server}/api/upload-check",
        data=json.dumps({"filename": filename, "content": content_v2}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req3, timeout=5) as resp:
        assert resp.status == 200
        data3 = json.loads(resp.read().decode("utf-8"))
        assert data3["robust"]["is_stale"] is True
        assert "MISS" in data3["robust"]["verdict"]
        assert data3["content_hash"] != data1["content_hash"]

    # Fourth upload: unchanged re-upload of edited version reports CACHE HIT!
    req4 = Request(
        f"{web_server}/api/upload-check",
        data=json.dumps({"filename": filename, "content": content_v2}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req4, timeout=5) as resp:
        assert resp.status == 200
        data4 = json.loads(resp.read().decode("utf-8"))
        assert data4["robust"]["is_stale"] is False
        assert "HIT" in data4["robust"]["verdict"]


def test_upload_check_rejects_empty_file(web_server):
    req = Request(
        f"{web_server}/api/upload-check",
        data=json.dumps({"filename": "empty.src", "content": "   \n\t"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(HTTPError) as exc_info:
        urlopen(req, timeout=5)
    assert exc_info.value.code == 400
    err_body = json.loads(exc_info.value.read().decode("utf-8"))
    assert "empty" in err_body["error"].lower()


def test_upload_check_rejects_malformed_dsl(web_server):
    req = Request(
        f"{web_server}/api/upload-check",
        data=json.dumps({"filename": "corrupted.src", "content": "not a valid key value pair"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(HTTPError) as exc_info:
        urlopen(req, timeout=5)
    assert exc_info.value.code == 400
    err_body = json.loads(exc_info.value.read().decode("utf-8"))
    assert "malformed" in err_body["error"].lower()


def test_upload_check_rejects_unsupported_extension(web_server):
    req = Request(
        f"{web_server}/api/upload-check",
        data=json.dumps({"filename": "script.py", "content": "operation=multiply\nfactor=2"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(HTTPError) as exc_info:
        urlopen(req, timeout=5)
    assert exc_info.value.code == 400
    err_body = json.loads(exc_info.value.read().decode("utf-8"))
    assert "unsupported file type" in err_body["error"].lower()


def test_upload_check_rejects_oversized_file(web_server):
    oversized = "a" * (1024 * 1024 + 100)
    req = Request(
        f"{web_server}/api/upload-check",
        data=json.dumps({"filename": "huge.src", "content": oversized}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(HTTPError) as exc_info:
        urlopen(req, timeout=5)
    assert exc_info.value.code == 400
    err_body = json.loads(exc_info.value.read().decode("utf-8"))
    assert "1mb" in err_body["error"].lower()


def test_simulation_service_check_uploaded_source_isolated(tmp_path):
    uploads_dir = tmp_path / "uploads"
    cache_dir = tmp_path / "cache"

    # Step 1: Initial upload
    res1 = simulation_service.check_uploaded_source(
        "isolated.src",
        "operation=multiply\nfactor=3",
        uploads_dir=uploads_dir,
        cache_dir=cache_dir,
    )
    assert res1["robust"]["is_stale"] is True
    assert res1["rebuilt"] is True

    # Step 2: Unchanged re-upload -> HIT
    res2 = simulation_service.check_uploaded_source(
        "isolated.src",
        "operation=multiply\nfactor=3",
        uploads_dir=uploads_dir,
        cache_dir=cache_dir,
    )
    assert res2["robust"]["is_stale"] is False
    assert "HIT" in res2["robust"]["verdict"]

    # Step 3: Edited upload -> MISS
    res3 = simulation_service.check_uploaded_source(
        "isolated.src",
        "operation=multiply\nfactor=6",
        uploads_dir=uploads_dir,
        cache_dir=cache_dir,
    )
    assert res3["robust"]["is_stale"] is True
    assert "MISS" in res3["robust"]["verdict"]
