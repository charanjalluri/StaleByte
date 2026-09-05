"""
test_timestamp_window.py
------------------------
Tests focusing on timestamp boundary conditions for both checkers.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import staleness_naive, staleness_smart
from lib.source_manager import compute_hash, V1_CONTENT

HASH_V1 = compute_hash(V1_CONTENT)


def _naive_meta(t_cache: float) -> dict:
    return {"t_cache": t_cache}


def _smart_meta(t_cache: float, h: str = HASH_V1) -> dict:
    return {"t_cache": t_cache, "source_hash": h}


# ---------------------------------------------------------------------------
# Boundary values
# ---------------------------------------------------------------------------

class TestNaiveBoundary:
    def test_equal_ts_is_not_stale(self):
        d = staleness_naive.check_staleness(1000.0, _naive_meta(1000.0))
        assert not d.is_stale

    def test_one_unit_newer_is_stale(self):
        d = staleness_naive.check_staleness(1001.0, _naive_meta(1000.0))
        assert d.is_stale

    def test_one_unit_older_is_not_stale(self):
        d = staleness_naive.check_staleness(999.0, _naive_meta(1000.0))
        assert not d.is_stale

    def test_far_future_source_is_stale(self):
        d = staleness_naive.check_staleness(9_999_999_999.0, _naive_meta(1000.0))
        assert d.is_stale

    def test_zero_timestamps_equal_is_not_stale(self):
        d = staleness_naive.check_staleness(0.0, _naive_meta(0.0))
        assert not d.is_stale


class TestSmartBoundary:
    def test_equal_ts_same_hash_is_not_stale(self):
        d = staleness_smart.check_staleness(1000.0, HASH_V1, _smart_meta(1000.0))
        assert not d.is_stale

    def test_equal_ts_diff_hash_is_stale(self):
        d = staleness_smart.check_staleness(
            1000.0, compute_hash("something_else"), _smart_meta(1000.0)
        )
        assert d.is_stale

    def test_newer_ts_same_hash_is_stale(self):
        d = staleness_smart.check_staleness(1001.0, HASH_V1, _smart_meta(1000.0))
        assert d.is_stale

    def test_older_ts_same_hash_is_not_stale(self):
        d = staleness_smart.check_staleness(999.0, HASH_V1, _smart_meta(1000.0))
        assert not d.is_stale

    def test_older_ts_diff_hash_is_stale(self):
        # Even clock-skewed, differing hash reveals content change
        d = staleness_smart.check_staleness(
            999.0, compute_hash("changed_content"), _smart_meta(1000.0)
        )
        assert d.is_stale
