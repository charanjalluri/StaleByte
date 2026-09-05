"""
test_invalidators.py
--------------------
Tests proving NaiveInvalidator vs RobustInvalidator behavior.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cache import CacheEntry
from clock import VirtualClock
from invalidators import NaiveInvalidator, RobustInvalidator
from source import SourceFile, V1_CONTENT, V2_CONTENT


def test_naive_invalidated_when_source_newer():
    clock = VirtualClock(current_time=1_700_000_001.0)
    source = SourceFile(content=V1_CONTENT, clock=clock)
    entry = CacheEntry(
        source_path="src/program.src",
        cached_mtime=1_700_000_000.0,
        cached_size=source.size,
        content_hash=source.content_hash,
        artifact={"factor": 2},
    )

    naive = NaiveInvalidator()
    decision = naive.check(source, entry)
    assert decision.is_stale is True


def test_naive_fooled_by_resolution_collision():
    clock = VirtualClock(current_time=1_700_000_000.0, resolution=1.0)
    # Cache created from V1
    source_v1 = SourceFile(content=V1_CONTENT, clock=clock)
    entry = CacheEntry(
        source_path="src/program.src",
        cached_mtime=1_700_000_000.0,
        cached_size=source_v1.size,
        content_hash=source_v1.content_hash,
        artifact={"factor": 2},
    )

    # Source modified to V2 within same 1s window (mtime remains 1_700_000_000.0)
    clock.advance(0.3)
    source_v2 = SourceFile(content=V2_CONTENT, clock=clock)
    assert source_v2.mtime == entry.cached_mtime

    naive = NaiveInvalidator()
    decision = naive.check(source_v2, entry)
    assert decision.is_stale is False  # Naive is fooled!
    assert decision.hash_match is False


def test_robust_catches_resolution_collision():
    clock = VirtualClock(current_time=1_700_000_000.0, resolution=1.0)
    source_v1 = SourceFile(content=V1_CONTENT, clock=clock)
    entry = CacheEntry(
        source_path="src/program.src",
        cached_mtime=1_700_000_000.0,
        cached_size=source_v1.size,
        content_hash=source_v1.content_hash,
        artifact={"factor": 2},
    )

    clock.advance(0.3)
    source_v2 = SourceFile(content=V2_CONTENT, clock=clock)

    robust = RobustInvalidator()
    decision = robust.check(source_v2, entry)
    assert decision.is_stale is True  # Robust catches collision
    assert decision.timestamp_match is True
    assert decision.hash_match is False
    assert "resolution window collision" in decision.reason


def test_robust_catches_clock_skew():
    build_clock = VirtualClock(current_time=1_700_000_100.0)
    source_v1 = SourceFile(content=V1_CONTENT, clock=build_clock)
    entry = CacheEntry(
        source_path="src/program.src",
        cached_mtime=1_700_000_100.0,
        cached_size=source_v1.size,
        content_hash=source_v1.content_hash,
        artifact={"factor": 2},
    )

    # Run machine clock is skewed behind (mtime=50 < cached=100), but source was edited to V2
    run_clock = VirtualClock(current_time=1_700_000_050.0)
    source_v2 = SourceFile(content=V2_CONTENT, clock=run_clock)

    robust = RobustInvalidator()
    decision = robust.check(source_v2, entry)
    assert decision.is_stale is True
    assert "clock skew" in decision.reason
