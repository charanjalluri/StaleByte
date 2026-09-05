"""
timestamp_collision.py
----------------------
Scenario: V1 cached → source mutated to V2 → timestamps pinned to the same
value → naive checker is fooled, smart checker catches the change.

Input 10:
  Naive  → executes stale V1 → returns 20  (WRONG)
  Smart  → detects staleness, rebuilds V2 → returns 30 (CORRECT)
"""

import sys
from pathlib import Path

# Make stalebyte/ importable when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import simulation_service

INPUT = 10


def run() -> None:
    print("=" * 60)
    print("SCENARIO: Timestamp Collision (V1 cached → V2 source)")
    print("=" * 60)

    data = simulation_service.run_collision_scenario(input_value=INPUT)

    # --- Setup ---
    print(f"\n[1] V1 cached.  t_cache = {data['collision_mtime']}")

    print(f"\n[2] Source mutated to V2:\n{data['v2']['content'].strip()}")
    print(f"    Simulated mtime still = {data['collision_mtime']}  ← collision!")

    # Naive
    naive = data["naive_execution"]
    print(f"\n[3] Naive checker decision:")
    print(f"    is_stale        = {naive['is_stale']}")
    print(f"    reason          = {naive['reason']}")
    print(f"    Naive result    = {naive['result']}  (expected 20 — stale V1)")
    assert naive["result"] == 20, f"Naive should return 20, got {naive['result']}"

    # Smart
    smart = data["smart_execution"]
    print(f"\n[4] Smart checker decision:")
    print(f"    is_stale        = {smart['is_stale']}")
    print(f"    timestamp_match = {smart['timestamp_match']}")
    print(f"    hash_match      = {smart['hash_match']}")
    print(f"    reason          = {smart['reason']}")
    print(f"    Smart result    = {smart['result']}  (expected 30 — rebuilt V2)")
    assert smart["result"] == 30, f"Smart should return 30, got {smart['result']}"

    # Summary
    print("\n" + "=" * 60)
    print("COLLISION SCENARIO RESULTS")
    print("=" * 60)
    print(f"  Naive runtime  → {naive['result']}  ← stale V1 executed (BUG)")
    print(f"  Smart runtime  → {smart['result']}  ← V2 rebuilt and executed (CORRECT)")
    print("\n✓ Timestamp collision scenario passed.")


if __name__ == "__main__":
    run()
