"""
test_timestamp_window.py
------------------------
Tests focusing on timestamp boundary conditions for both checkers.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from cache import CacheEntry
from invalidators import NaiveInvalidator, RobustInvalidator
from lib.source_manager import compute_hash, V1_CONTENT
from source import SourceFile

HASH_V1 = compute_hash(V1_CONTENT)

naive_checker = NaiveInvalidator()
smart_checker = RobustInvalidator()


def _entry(t_cache: float, h: str = HASH_V1) -> CacheEntry:
    return CacheEntry(
        source_path="src/program.src",
        cached_mtime=t_cache,
        cached_size=len(V1_CONTENT),
        content_hash=h,
        artifact={"factor": 2},
    )


def _source(mtime: float, h: str = HASH_V1) -> SourceFile:
    return SourceFile(
        path="src/program.src",
        content=V1_CONTENT,
        mtime=mtime,
        size=len(V1_CONTENT),
        content_hash=h,
    )


# ---------------------------------------------------------------------------
# Boundary values
# ---------------------------------------------------------------------------

class TestNaiveBoundary:
    def test_equal_ts_is_not_stale(self):
        d = naive_checker.check(_source(1000.0), _entry(1000.0))
        assert not d.is_stale

    def test_one_unit_newer_is_stale(self):
        d = naive_checker.check(_source(1001.0), _entry(1000.0))
        assert d.is_stale

    def test_one_unit_older_is_not_stale(self):
        d = naive_checker.check(_source(999.0), _entry(1000.0))
        assert not d.is_stale

    def test_far_future_source_is_stale(self):
        d = naive_checker.check(_source(9_999_999_999.0), _entry(1000.0))
        assert d.is_stale

    def test_zero_timestamps_equal_is_not_stale(self):
        d = naive_checker.check(_source(0.0), _entry(0.0))
        assert not d.is_stale


class TestSmartBoundary:
    def test_equal_ts_same_hash_is_not_stale(self):
        d = smart_checker.check(_source(1000.0, HASH_V1), _entry(1000.0, HASH_V1))
        assert not d.is_stale

    def test_equal_ts_diff_hash_is_stale(self):
        d = smart_checker.check(
            _source(1000.0, compute_hash("something_else")), _entry(1000.0, HASH_V1)
        )
        assert d.is_stale

    def test_newer_ts_same_hash_is_stale(self):
        d = smart_checker.check(_source(1001.0, HASH_V1), _entry(1000.0, HASH_V1))
        assert d.is_stale

    def test_older_ts_same_hash_is_not_stale(self):
        d = smart_checker.check(_source(999.0, HASH_V1), _entry(1000.0, HASH_V1))
        assert not d.is_stale

    def test_older_ts_diff_hash_is_stale(self):
        # Even clock-skewed, differing hash reveals content change
        d = smart_checker.check(
            _source(999.0, compute_hash("changed_content")), _entry(1000.0, HASH_V1)
        )
        assert d.is_stale
