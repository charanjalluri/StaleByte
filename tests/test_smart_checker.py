"""
test_smart_checker.py
---------------------
Tests proving the behaviour of the SHA-256-aware staleness checker.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.staleness_smart import check_staleness
from lib.source_manager import compute_hash, V1_CONTENT, V2_CONTENT

FIXED_TS = 1_700_000_000.0
HASH_V1 = compute_hash(V1_CONTENT)
HASH_V2 = compute_hash(V2_CONTENT)


def _meta(t_cache: float, source_hash: str) -> dict:
    return {
        "t_cache": t_cache,
        "source_hash": source_hash,
        "source_version": "V1",
    }


# ---------------------------------------------------------------------------
# Core detection
# ---------------------------------------------------------------------------

def test_collision_detected_by_hash():
    """
    Timestamp collision scenario: mtime == t_cache but hashes differ.
    Smart checker must report is_stale=True.
    """
    meta = _meta(FIXED_TS, HASH_V1)
    decision = check_staleness(FIXED_TS, HASH_V2, meta)
    assert decision.is_stale
    assert decision.timestamp_match
    assert not decision.hash_match


def test_no_false_invalidation_when_unchanged():
    """
    Unchanged source: same mtime, same hash.
    Smart checker must report is_stale=False.
    """
    meta = _meta(FIXED_TS, HASH_V1)
    decision = check_staleness(FIXED_TS, HASH_V1, meta)
    assert not decision.is_stale
    assert decision.timestamp_match
    assert decision.hash_match


def test_stale_when_source_newer_even_if_hash_same():
    """
    If mtime is greater, is_stale must be True even when hash somehow matches.
    (Defensive test — hash should also differ in practice.)
    """
    meta = _meta(FIXED_TS, HASH_V1)
    decision = check_staleness(FIXED_TS + 1, HASH_V1, meta)
    assert decision.is_stale


def test_valid_when_source_older_and_hash_same():
    """Clock skew: source appears older, same hash → valid cache."""
    meta = _meta(FIXED_TS, HASH_V1)
    decision = check_staleness(FIXED_TS - 1, HASH_V1, meta)
    assert not decision.is_stale


# ---------------------------------------------------------------------------
# Structured decision fields
# ---------------------------------------------------------------------------

def test_decision_has_all_fields():
    """SmartDecision must expose all required diagnostic fields."""
    meta = _meta(FIXED_TS, HASH_V1)
    d = check_staleness(FIXED_TS, HASH_V2, meta)
    assert hasattr(d, "is_stale")
    assert hasattr(d, "timestamp_match")
    assert hasattr(d, "hash_match")
    assert hasattr(d, "reason")
    assert hasattr(d, "source_hash")
    assert hasattr(d, "cached_hash")


def test_reason_mentions_collision():
    """When in collision mode, reason must explain the collision."""
    meta = _meta(FIXED_TS, HASH_V1)
    decision = check_staleness(FIXED_TS, HASH_V2, meta)
    assert "collision" in decision.reason.lower() or "stale" in decision.reason.lower()
