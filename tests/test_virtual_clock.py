"""
test_virtual_clock.py
---------------------
Tests for VirtualClock resolution quantization and skew offset.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from clock import VirtualClock


def test_clock_default_resolution_and_time():
    clock = VirtualClock(current_time=1_700_000_000.5, resolution=1.0)
    assert clock.now() == 1_700_000_000.5
    assert clock.quantized_now() == 1_700_000_000.0


def test_clock_resolution_quantization():
    clock = VirtualClock(current_time=1_700_000_000.0, resolution=1.0)
    # Advancing by 0.4s within the same 1s resolution window produces the same quantized mtime
    assert clock.quantized_now() == 1_700_000_000.0
    clock.advance(0.4)
    assert clock.now() == 1_700_000_000.4
    assert clock.quantized_now() == 1_700_000_000.0  # Same quantized timestamp!

    # Advancing past the 1.0s boundary increments quantized time
    clock.advance(0.7)  # total 1.1s
    assert clock.quantized_now() == 1_700_000_001.0


def test_clock_skew_offset():
    build_clock = VirtualClock(current_time=1_700_000_100.0, resolution=1.0, skew_offset=0.0)
    run_clock = build_clock.with_skew(-50.0)

    assert build_clock.quantized_now() == 1_700_000_100.0
    assert run_clock.quantized_now() == 1_700_000_050.0  # 50s behind
