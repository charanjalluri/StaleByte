"""
test_unified_runtime.py
-----------------------
Tests for unified Runtime.execute with NaiveInvalidator vs RobustInvalidator.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from cache import CacheStore
from clock import VirtualClock
from invalidators import NaiveInvalidator, RobustInvalidator
from runtime import Runtime
from source import SourceFile, V1_CONTENT, V2_CONTENT


@pytest.fixture()
def tmp_runtime(tmp_path):
    store = CacheStore(cache_dir=tmp_path)
    return Runtime(cache_store=store)


def test_unified_runtime_collision_scenario(tmp_runtime):
    clock = VirtualClock(current_time=1_700_000_000.0, resolution=1.0)
    source = SourceFile(content=V1_CONTENT, clock=clock)

    # 1. Build & Cache V1 (factor=2)
    res1 = tmp_runtime.execute(source, RobustInvalidator(), input_value=10)
    assert res1.output == 20

    # 2. Modify to V2 (factor=3) within same 1s resolution window
    clock.advance(0.4)
    source.update_content(V2_CONTENT)
    assert source.mtime == 1_700_000_000.0  # collision!

    # 3. Naive execution -> reuses stale V1 cache -> returns 20 (BUG)
    naive_res = tmp_runtime.execute(source, NaiveInvalidator(), input_value=10)
    assert naive_res.output == 20
    assert naive_res.cache_hit is True
    assert naive_res.rebuilt is False
    assert naive_res.artifact["factor"] == 2

    # 4. Robust execution -> detects collision -> rebuilds V2 -> returns 30 (CORRECT)
    robust_res = tmp_runtime.execute(source, RobustInvalidator(), input_value=10)
    assert robust_res.output == 30
    assert robust_res.cache_hit is False
    assert robust_res.rebuilt is True
    assert robust_res.artifact["factor"] == 3


def test_unified_runtime_idempotent_cache_hit(tmp_runtime):
    clock = VirtualClock(current_time=1_700_000_000.0, resolution=1.0)
    source = SourceFile(content=V1_CONTENT, clock=clock)

    # First run builds
    res1 = tmp_runtime.execute(source, RobustInvalidator(), input_value=10)
    assert res1.output == 20

    # Second run with unchanged source reuses cache
    res2 = tmp_runtime.execute(source, RobustInvalidator(), input_value=10)
    assert res2.output == 20
    assert res2.cache_hit is True
    assert res2.rebuilt is False
