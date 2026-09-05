"""
test_smart_checker.py
---------------------
Tests proving the behaviour of the SHA-256-aware staleness checker (RobustInvalidator).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cache import CacheEntry
from invalidators import RobustInvalidator
from lib.source_manager import compute_hash, V1_CONTENT, V2_CONTENT
from source import SourceFile

FIXED_TS = 1_700_000_000.0
HASH_V1 = compute_hash(V1_CONTENT)
HASH_V2 = compute_hash(V2_CONTENT)

checker = RobustInvalidator()


def _entry(t_cache: float, source_hash: str) -> CacheEntry:
    return CacheEntry(
        source_path="src/program.src",
        cached_mtime=t_cache,
        cached_size=len(V1_CONTENT),
        content_hash=source_hash,
        artifact={"factor": 2},
        version_label="V1",
    )


def _source(mtime: float, source_hash: str, content: str = V1_CONTENT) -> SourceFile:
    return SourceFile(
        path="src/program.src",
        content=content,
        mtime=mtime,
        size=len(content),
        content_hash=source_hash,
    )


# ---------------------------------------------------------------------------
# Core detection
# ---------------------------------------------------------------------------

def test_collision_detected_by_hash():
    """
    Timestamp collision scenario: mtime == t_cache but hashes differ.
    Robust checker must report is_stale=True.
    """
    entry = _entry(FIXED_TS, HASH_V1)
    source = _source(FIXED_TS, HASH_V2, content=V2_CONTENT)
    decision = checker.check(source, entry)
    assert decision.is_stale
    assert decision.timestamp_match
    assert not decision.hash_match


def test_no_false_invalidation_when_unchanged():
    """
    Unchanged source: same mtime, same hash.
    Robust checker must report is_stale=False.
    """
    entry = _entry(FIXED_TS, HASH_V1)
    source = _source(FIXED_TS, HASH_V1, content=V1_CONTENT)
    decision = checker.check(source, entry)
    assert not decision.is_stale
    assert decision.timestamp_match
    assert decision.hash_match


def test_stale_when_source_newer_even_if_hash_same():
    """
    If mtime is greater, is_stale must be True even when hash somehow matches.
    (Defensive test — hash should also differ in practice.)
    """
    entry = _entry(FIXED_TS, HASH_V1)
    source = _source(FIXED_TS + 1, HASH_V1, content=V1_CONTENT)
    decision = checker.check(source, entry)
    assert decision.is_stale


def test_valid_when_source_older_and_hash_same():
    """Clock skew: source appears older, same hash -> valid cache."""
    entry = _entry(FIXED_TS, HASH_V1)
    source = _source(FIXED_TS - 1, HASH_V1, content=V1_CONTENT)
    decision = checker.check(source, entry)
    assert not decision.is_stale


# ---------------------------------------------------------------------------
# Structured decision fields
# ---------------------------------------------------------------------------

def test_decision_has_all_fields():
    """InvalidationDecision must expose all required diagnostic fields."""
    entry = _entry(FIXED_TS, HASH_V1)
    source = _source(FIXED_TS, HASH_V2, content=V2_CONTENT)
    d = checker.check(source, entry)
    assert hasattr(d, "is_stale")
    assert hasattr(d, "timestamp_match")
    assert hasattr(d, "hash_match")
    assert hasattr(d, "reason")
    assert hasattr(d, "source_hash")
    assert hasattr(d, "cached_hash")


def test_reason_mentions_collision():
    """When in collision mode, reason must explain the collision."""
    entry = _entry(FIXED_TS, HASH_V1)
    source = _source(FIXED_TS, HASH_V2, content=V2_CONTENT)
    decision = checker.check(source, entry)
    assert "collision" in decision.reason.lower() or "stale" in decision.reason.lower()
