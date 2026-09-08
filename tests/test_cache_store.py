"""
test_cache_store.py
-------------------
Tests for CacheStore and CacheEntry persistence and invalidation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from cache import CacheEntry, CacheStore


@pytest.fixture()
def tmp_store(tmp_path):
    return CacheStore(cache_dir=tmp_path)


def test_cache_store_save_load_invalidate(tmp_store):
    artifact = {"operation": "multiply", "factor": 2, "bytecode": ["LOAD_INPUT", "PUSH 2", "MUL", "RETURN"]}
    entry = CacheEntry(
        source_path="src/program.src",
        cached_mtime=1_700_000_000.0,
        cached_size=28,
        content_hash="abc123hash",
        artifact=artifact,
        version_label="V1",
    )

    assert not tmp_store.exists()
    assert tmp_store.load() is None

    tmp_store.save(entry)
    assert tmp_store.exists()

    loaded = tmp_store.load()
    assert loaded is not None
    assert loaded.content_hash == "abc123hash"
    assert loaded.cached_mtime == 1_700_000_000.0
    assert loaded.artifact == artifact

    tmp_store.invalidate()
    assert not tmp_store.exists()
    assert tmp_store.load() is None


def test_cache_store_corrupt_file_emits_warning(tmp_store, capsys):
    # Corrupt artifact file
    tmp_store.artifact_path.write_text("{corrupt json", encoding="utf-8")
    tmp_store.metadata_path.write_text("{\"t_cache\": 1.0}", encoding="utf-8")

    with pytest.warns(UserWarning) as record:
        loaded = tmp_store.load()

    assert loaded is None
    assert len(record) >= 1
    assert "corrupt cache" in str(record[0].message).lower()

    # Verify warning also printed to stderr
    captured = capsys.readouterr()
    assert "[WARN]" in captured.err


def test_cache_store_concurrent_writes(tmp_store):
    import concurrent.futures

    def worker(i):
        entry = CacheEntry(
            source_path=f"src/file_{i % 5}.src",
            cached_mtime=1_700_000_000.0 + i,
            cached_size=100 + i,
            content_hash=f"hash_{i}",
            artifact={"operation": "add", "factor": i, "bytecode": ["PUSH 1"]},
            version_label=f"V{i}",
        )
        tmp_store.save(entry)
        loaded = tmp_store.load(f"src/file_{i % 5}.src")
        return loaded is not None

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(worker, range(40)))

    assert all(results)
    assert tmp_store.exists()

