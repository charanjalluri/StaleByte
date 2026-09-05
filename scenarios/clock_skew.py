"""
clock_skew.py
-------------
Scenario: the source file reports an mtime *older* than the cache timestamp
(simulating a clock-skew situation where the build machine's clock was ahead).

Both checkers treat an older-appearing source as valid — the smart checker
still confirms via hash whether the content actually changed.
"""

import sys
from pathlib import Path

# Make stalebyte/ importable when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import simulation_service

INPUT = 10


def run() -> None:
    print("=" * 60)
    print("SCENARIO: Clock Skew (source mtime < t_cache)")
    print("=" * 60)

    data = simulation_service.run_clock_skew_scenario(input_value=INPUT)

    print(f"\n[1] V1 cached at t_cache={data['t_cache']}")
    print(f"    Simulated source mtime = {data['t_source_skewed']}  (clock skew!)")

    # Naive checker
    print(f"\n[2] Naive checker:")
    print(f"    is_stale = {data['naive_decision']['is_stale']}")
    print(f"    reason   = {data['naive_decision']['reason']}")

    # Smart checker
    print(f"\n[3] Smart checker:")
    print(f"    is_stale        = {data['smart_decision']['is_stale']}")
    print(f"    timestamp_match = {data['smart_decision']['timestamp_match']}")
    print(f"    hash_match      = {data['smart_decision']['hash_match']}")
    print(f"    reason          = {data['smart_decision']['reason']}")

    print(f"\n[4] Execute(10) → {data['result']}")
    assert data["result"] == 20

    assert not data["naive_decision"]["is_stale"], "Naive should see cache as valid under skew"
    assert not data["smart_decision"]["is_stale"], "Smart should confirm valid (hash unchanged)"

    print("\n✓ Clock skew scenario passed — no false invalidation.")


if __name__ == "__main__":
    run()
