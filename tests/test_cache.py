"""
test_cache.py
-------------
Tests proving that cache save/load round-trips preserve all data.
Uses a temporary directory so tests are isolated and leave no side effects.
"""

import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import cache_manager, compiler, source_manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_cache(monkeypatch, tmp_path):
    """Redirect cache paths to a temporary directory for each test."""
    monkeypatch.setattr(cache_manager, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(cache_manager, "ARTIFACT_PATH", tmp_path / "artifact.json")
    monkeypatch.setattr(cache_manager, "METADATA_PATH", tmp_path / "metadata.json")
    return tmp_path


@pytest.fixture()
def v1_artifact():
    return compiler.compile_source(source_manager.V1_CONTENT)


@pytest.fixture()
def v1_hash():
    return source_manager.compute_hash(source_manager.V1_CONTENT)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_save_and_load_artifact(tmp_cache, v1_artifact, v1_hash):
    """Artifact round-trips through save → load without data loss."""
    cache_manager.save_cache(
        artifact=v1_artifact,
        source_content=source_manager.V1_CONTENT,
        source_hash=v1_hash,
        source_version="V1",
        t_cache=1_700_000_000.0,
    )
    loaded = cache_manager.load_artifact()
    assert loaded == v1_artifact


def test_save_and_load_metadata(tmp_cache, v1_artifact, v1_hash):
    """Metadata round-trips with correct values."""
    cache_manager.save_cache(
        artifact=v1_artifact,
        source_content=source_manager.V1_CONTENT,
        source_hash=v1_hash,
        source_version="V1",
        t_cache=1_700_000_000.0,
    )
    meta = cache_manager.load_metadata()
    assert meta["source_hash"] == v1_hash
    assert meta["source_version"] == "V1"
    assert meta["t_cache"] == 1_700_000_000.0
    assert meta["source_size"] == len(source_manager.V1_CONTENT.encode("utf-8"))
    assert "artifact_id" in meta


def test_cache_exists_after_save(tmp_cache, v1_artifact, v1_hash):
    assert not cache_manager.cache_exists()
    cache_manager.save_cache(
        artifact=v1_artifact,
        source_content=source_manager.V1_CONTENT,
        source_hash=v1_hash,
        source_version="V1",
        t_cache=1_700_000_000.0,
    )
    assert cache_manager.cache_exists()


def test_invalidate_removes_files(tmp_cache, v1_artifact, v1_hash):
    cache_manager.save_cache(
        artifact=v1_artifact,
        source_content=source_manager.V1_CONTENT,
        source_hash=v1_hash,
        source_version="V1",
        t_cache=1_700_000_000.0,
    )
    cache_manager.invalidate_cache()
    assert not cache_manager.cache_exists()


def test_load_artifact_missing_raises(tmp_cache):
    with pytest.raises(FileNotFoundError):
        cache_manager.load_artifact()


def test_load_metadata_missing_raises(tmp_cache):
    with pytest.raises(FileNotFoundError):
        cache_manager.load_metadata()


def test_load_metadata_malformed_raises(tmp_cache):
    (tmp_cache / "metadata.json").write_text("{bad json", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed metadata cache"):
        cache_manager.load_metadata()


def test_load_artifact_malformed_raises(tmp_cache):
    (tmp_cache / "artifact.json").write_text("not json!", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed artifact cache"):
        cache_manager.load_artifact()
