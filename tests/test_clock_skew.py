"""
test_clock_skew.py
------------------
Tests proving that neither checker triggers a false rebuild when the source
mtime appears older than the cache (clock-skew scenario).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cache import CacheEntry
from invalidators import NaiveInvalidator, RobustInvalidator
from lib.source_manager import V1_CONTENT, compute_hash
from source import SourceFile

HASH_V1 = compute_hash(V1_CONTENT)
T_CACHE = 1_700_000_100.0
T_SKEWED = 1_700_000_000.0  # 100 seconds "in the past" due to skew

naive_checker = NaiveInvalidator()
smart_checker = RobustInvalidator()


def _entry(h: str = HASH_V1) -> CacheEntry:
    return CacheEntry(
        source_path="src/program.src",
        cached_mtime=T_CACHE,
        cached_size=len(V1_CONTENT),
        content_hash=h,
        artifact={"factor": 2},
    )


def _source(mtime: float, h: str = HASH_V1, content: str = V1_CONTENT) -> SourceFile:
    return SourceFile(
        path="src/program.src",
        content=content,
        mtime=mtime,
        size=len(content),
        content_hash=h,
    )


def test_naive_no_false_invalidation_under_skew():
    """Naive checker: older mtime -> cache considered valid."""
    decision = naive_checker.check(_source(T_SKEWED), _entry())
    assert not decision.is_stale


def test_smart_no_false_invalidation_under_skew_same_hash():
    """Smart checker: older mtime + same hash -> cache is valid."""
    decision = smart_checker.check(_source(T_SKEWED, HASH_V1), _entry(HASH_V1))
    assert not decision.is_stale
    assert decision.hash_match


def test_smart_detects_change_under_skew_if_hash_differs():
    """
    Even with a skewed (older) mtime, if the content hash changed the smart
    checker must flag the cache as stale.
    """
    altered_content = V1_CONTENT + "extra"
    altered_hash = compute_hash(altered_content)
    decision = smart_checker.check(_source(T_SKEWED, altered_hash, content=altered_content), _entry(HASH_V1))
    assert decision.is_stale
    assert not decision.hash_match


def test_naive_vs_smart_diverge_under_skew_with_change():
    """
    When content changes but mtime is skewed:
    - Naive: NOT stale (cannot see the change)
    - Smart: IS stale (hash reveals the change)
    """
    altered_content = "factor=99\noperation=multiply\n"
    altered_hash = compute_hash(altered_content)
    naive = naive_checker.check(_source(T_SKEWED, altered_hash, content=altered_content), _entry(HASH_V1))
    smart = smart_checker.check(_source(T_SKEWED, altered_hash, content=altered_content), _entry(HASH_V1))
    assert not naive.is_stale
    assert smart.is_stale
