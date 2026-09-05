"""
test_naive_checker.py
---------------------
Tests proving the behaviour of the timestamp-only staleness checker (NaiveInvalidator).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cache import CacheEntry
from invalidators import NaiveInvalidator
from source import SourceFile

FIXED_TS = 1_700_000_000.0
checker = NaiveInvalidator()


def _entry(t_cache: float) -> CacheEntry:
    return CacheEntry(
        source_path="src/program.src",
        cached_mtime=t_cache,
        cached_size=10,
        content_hash="hash_v1",
        artifact={"factor": 2},
    )


def _source(mtime: float, content_hash: str = "hash_v1") -> SourceFile:
    return SourceFile(
        path="src/program.src",
        content="operation=multiply\nfactor=2",
        mtime=mtime,
        size=10,
        content_hash=content_hash,
    )


def test_cache_valid_when_timestamps_equal():
    """When source_mtime == t_cache, naive checker must report NOT stale."""
    decision = checker.check(_source(FIXED_TS), _entry(FIXED_TS))
    assert not decision.is_stale


def test_cache_valid_when_source_is_older():
    """When source_mtime < t_cache (clock skew), naive reports NOT stale."""
    decision = checker.check(_source(FIXED_TS - 1), _entry(FIXED_TS))
    assert not decision.is_stale


def test_cache_stale_when_source_is_newer():
    """When source_mtime > t_cache, naive reports STALE."""
    decision = checker.check(_source(FIXED_TS + 1), _entry(FIXED_TS))
    assert decision.is_stale


def test_decision_contains_reason():
    """Decision must always carry a non-empty reason string."""
    decision = checker.check(_source(FIXED_TS), _entry(FIXED_TS))
    assert isinstance(decision.reason, str) and len(decision.reason) > 0


def test_collision_scenario_naive_is_fooled():
    """
    Collision: source_mtime == t_cache even after content changed.
    Naive checker reports NOT stale — proving the flaw.
    """
    decision = checker.check(_source(FIXED_TS, content_hash="hash_v2"), _entry(FIXED_TS))
    assert not decision.is_stale, (
        "Naive checker should be fooled during a timestamp collision"
    )
