"""
test_clock_skew.py
------------------
Tests proving that neither checker triggers a false rebuild when the source
mtime appears older than the cache (clock-skew scenario).
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import staleness_naive, staleness_smart
from lib.source_manager import compute_hash, V1_CONTENT

HASH_V1 = compute_hash(V1_CONTENT)
T_CACHE = 1_700_000_100.0
T_SKEWED = 1_700_000_000.0   # 100 seconds "in the past" due to skew


def _naive_meta() -> dict:
    return {"t_cache": T_CACHE}


def _smart_meta() -> dict:
    return {"t_cache": T_CACHE, "source_hash": HASH_V1}


def test_naive_no_false_invalidation_under_skew():
    """Naive checker: older mtime → cache considered valid."""
    decision = staleness_naive.check_staleness(T_SKEWED, _naive_meta())
    assert not decision.is_stale


def test_smart_no_false_invalidation_under_skew_same_hash():
    """Smart checker: older mtime + same hash → cache is valid."""
    decision = staleness_smart.check_staleness(T_SKEWED, HASH_V1, _smart_meta())
    assert not decision.is_stale
    assert decision.hash_match


def test_smart_detects_change_under_skew_if_hash_differs():
    """
    Even with a skewed (older) mtime, if the content hash changed the smart
    checker must flag the cache as stale.
    """
    altered_hash = compute_hash(V1_CONTENT + "extra")
    decision = staleness_smart.check_staleness(T_SKEWED, altered_hash, _smart_meta())
    assert decision.is_stale
    assert not decision.hash_match


def test_naive_vs_smart_diverge_under_skew_with_change():
    """
    When content changes but mtime is skewed:
    - Naive: NOT stale (cannot see the change)
    - Smart: IS stale (hash reveals the change)
    """
    altered_hash = compute_hash("factor=99\noperation=multiply\n")
    naive = staleness_naive.check_staleness(T_SKEWED, _naive_meta())
    smart = staleness_smart.check_staleness(T_SKEWED, altered_hash, _smart_meta())
    assert not naive.is_stale
    assert smart.is_stale
