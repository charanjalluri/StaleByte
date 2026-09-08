"""
test_runtime_end_to_end.py
--------------------------
End-to-end tests proving that the naive and smart runtimes produce
the correct results when exercised against the full collision scenario.

These tests cover requirements 7 & 8:
  • Naive runtime genuinely executes the old cached artifact (returns 20).
  • Smart runtime genuinely detects staleness, rebuilds, and executes V2 (returns 30).
  • Unchanged source does not cause the smart runtime to rebuild.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from lib import cache_manager, compiler, source_manager
from runtime import run_naive, run_smart

FIXED_TS = source_manager.SIMULATED_MTIME


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_cache(monkeypatch, tmp_path):
    """Redirect cache paths to a temporary directory."""
    monkeypatch.setattr(cache_manager, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(cache_manager, "ARTIFACT_PATH", tmp_path / "artifact.json")
    monkeypatch.setattr(cache_manager, "METADATA_PATH", tmp_path / "metadata.json")
    return tmp_path


@pytest.fixture()
def collision_state(tmp_cache, tmp_path):
    """
    Arrange the collision scenario:
      1. Write V1 source → compile → save cache with FIXED_TS.
      2. Overwrite source with V2 (disk file changes, simulated mtime unchanged).

    Returns the path to the (now V2) source file.
    """
    src_file = tmp_path / "program.src"

    # Step 1 — V1 on disk, V1 in cache
    src_file.write_text(source_manager.V1_CONTENT, encoding="utf-8")
    artifact_v1 = compiler.compile_source(source_manager.V1_CONTENT)
    h_v1 = source_manager.compute_hash(source_manager.V1_CONTENT)
    cache_manager.save_cache(
        artifact=artifact_v1,
        source_content=source_manager.V1_CONTENT,
        source_hash=h_v1,
        source_version="V1",
        t_cache=FIXED_TS,
    )

    # Step 2 — V2 on disk, V1 still in cache (collision state)
    src_file.write_text(source_manager.V2_CONTENT, encoding="utf-8")
    return src_file


# ---------------------------------------------------------------------------
# Requirement 7: Naive runtime executes stale V1 artifact
# ---------------------------------------------------------------------------

def test_naive_runtime_returns_stale_v1_result(collision_state):
    """
    In the collision scenario the naive runtime must execute the cached V1
    artifact (factor=2) and return 10 * 2 = 20, not the V2 result of 30.
    """
    out = run_naive(
        10,
        source_path=collision_state,
        get_mtime=source_manager.simulated_mtime,
    )
    assert out["result"] == 20, f"Expected stale V1 result=20, got {out['result']}"
    assert out["cache_used"] is True, "Naive runtime should have reused the stale cache"
    assert out["artifact"]["factor"] == 2, "Executed artifact must be V1 (factor=2)"


# ---------------------------------------------------------------------------
# Requirement 8: Smart runtime rebuilds and executes V2 artifact
# ---------------------------------------------------------------------------

def test_smart_runtime_detects_staleness_and_returns_v2_result(collision_state):
    """
    In the collision scenario the smart runtime must detect the hash mismatch,
    invalidate the V1 cache, rebuild from V2 (factor=3), and return 10 * 3 = 30.
    """
    out = run_smart(
        10,
        source_path=collision_state,
        get_mtime=source_manager.simulated_mtime,
    )
    assert out["result"] == 30, f"Expected rebuilt V2 result=30, got {out['result']}"
    assert out["rebuilt"] is True, "Smart runtime must report a rebuild"
    assert out["cache_used"] is False, "Smart runtime must not reuse the stale cache"
    assert out["artifact"]["factor"] == 3, "Executed artifact must be V2 (factor=3)"


def test_smart_runtime_decision_explains_collision(collision_state):
    """The SmartDecision returned must confirm timestamp_match=True, hash_match=False."""
    out = run_smart(
        10,
        source_path=collision_state,
        get_mtime=source_manager.simulated_mtime,
    )
    d = out["decision"]
    assert d.timestamp_match is True
    assert d.hash_match is False
    assert d.is_stale is True


# ---------------------------------------------------------------------------
# Requirement 9: Unchanged source does not trigger unnecessary invalidation
# ---------------------------------------------------------------------------

def test_smart_runtime_no_rebuild_when_source_unchanged(tmp_cache, tmp_path):
    """
    When source content is unchanged between two runs, the smart runtime must
    reuse the cache on the second call without rebuilding.
    """
    src_file = tmp_path / "program.src"
    src_file.write_text(source_manager.V1_CONTENT, encoding="utf-8")

    # First call — no cache exists, must build fresh
    first = run_smart(
        10,
        source_path=src_file,
        get_mtime=source_manager.simulated_mtime,
    )
    assert first["result"] == 20
    assert first["rebuilt"] is False
    assert first["cache_used"] is False

    # Second call — source unchanged, must reuse cache
    second = run_smart(
        10,
        source_path=src_file,
        get_mtime=source_manager.simulated_mtime,
    )
    assert second["result"] == 20
    assert second["cache_used"] is True
    assert second["rebuilt"] is False
