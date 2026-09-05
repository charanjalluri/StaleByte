"""
test_naive_checker.py
---------------------
Tests proving the behaviour of the timestamp-only staleness checker.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.staleness_naive import check_staleness

FIXED_TS = 1_700_000_000.0


def _meta(t_cache: float) -> dict:
    return {"t_cache": t_cache, "source_hash": "irrelevant", "source_version": "V1"}


def test_cache_valid_when_timestamps_equal():
    """When source_mtime == t_cache, naive checker must report NOT stale."""
    decision = check_staleness(FIXED_TS, _meta(FIXED_TS))
    assert not decision.is_stale


def test_cache_valid_when_source_is_older():
    """When source_mtime < t_cache (clock skew), naive reports NOT stale."""
    decision = check_staleness(FIXED_TS - 1, _meta(FIXED_TS))
    assert not decision.is_stale


def test_cache_stale_when_source_is_newer():
    """When source_mtime > t_cache, naive reports STALE."""
    decision = check_staleness(FIXED_TS + 1, _meta(FIXED_TS))
    assert decision.is_stale


def test_decision_contains_reason():
    """Decision must always carry a non-empty reason string."""
    decision = check_staleness(FIXED_TS, _meta(FIXED_TS))
    assert isinstance(decision.reason, str) and len(decision.reason) > 0


def test_collision_scenario_naive_is_fooled():
    """
    Collision: source_mtime == t_cache even after content changed.
    Naive checker reports NOT stale — proving the flaw.
    """
    decision = check_staleness(FIXED_TS, _meta(FIXED_TS))
    assert not decision.is_stale, (
        "Naive checker should be fooled during a timestamp collision"
    )
