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

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import cache_manager, compiler, source_manager, staleness_naive, staleness_smart

FIXED_TS = source_manager.SIMULATED_MTIME   # 1_700_000_000.0 — same for V1 & V2
INPUT = 10


def _cache_v1() -> None:
    """Write V1 and populate the cache with the fixed timestamp."""
    source_manager.create_source(source_manager.V1_CONTENT)
    content = source_manager.read_source()
    artifact = compiler.compile_source(content)
    src_hash = source_manager.compute_hash(content)
    cache_manager.save_cache(
        artifact=artifact,
        source_content=content,
        source_hash=src_hash,
        source_version="V1",
        t_cache=FIXED_TS,
    )


def _mutate_to_v2() -> None:
    """Overwrite source with V2 content (timestamps stay fixed at FIXED_TS)."""
    source_manager.create_source(source_manager.V2_CONTENT)


def run() -> None:
    print("=" * 60)
    print("SCENARIO: Timestamp Collision (V1 cached → V2 source)")
    print("=" * 60)

    # --- Setup ---
    _cache_v1()
    print(f"\n[1] V1 cached.  t_cache = {FIXED_TS}")

    _mutate_to_v2()
    content_v2 = source_manager.read_source()
    print(f"\n[2] Source mutated to V2:\n{content_v2.strip()}")
    print(f"    Simulated mtime still = {FIXED_TS}  ← collision!")

    metadata = cache_manager.load_metadata()

    # ---------------------------------------------------------------
    # Naive checker
    # ---------------------------------------------------------------
    naive_decision = staleness_naive.check_staleness(FIXED_TS, metadata)
    print(f"\n[3] Naive checker decision:")
    print(f"    is_stale        = {naive_decision.is_stale}")
    print(f"    reason          = {naive_decision.reason}")

    if not naive_decision.is_stale:
        # Uses stale V1 artifact
        artifact_used = cache_manager.load_artifact()
        naive_result = compiler.execute_artifact(artifact_used, INPUT)
    else:
        artifact_used = compiler.compile_source(content_v2)
        naive_result = compiler.execute_artifact(artifact_used, INPUT)

    print(f"    Naive result    = {naive_result}  (expected 20 — stale V1)")
    assert naive_result == 20, f"Naive should return 20, got {naive_result}"

    # ---------------------------------------------------------------
    # Smart checker
    # ---------------------------------------------------------------
    src_hash_v2 = source_manager.compute_hash(content_v2)
    smart_decision = staleness_smart.check_staleness(FIXED_TS, src_hash_v2, metadata)
    print(f"\n[4] Smart checker decision:")
    print(f"    is_stale        = {smart_decision.is_stale}")
    print(f"    timestamp_match = {smart_decision.timestamp_match}")
    print(f"    hash_match      = {smart_decision.hash_match}")
    print(f"    reason          = {smart_decision.reason}")

    if smart_decision.is_stale:
        cache_manager.invalidate_cache()
        artifact_v2 = compiler.compile_source(content_v2)
        cache_manager.save_cache(
            artifact=artifact_v2,
            source_content=content_v2,
            source_hash=src_hash_v2,
            source_version="V2",
            t_cache=FIXED_TS,
        )
        smart_result = compiler.execute_artifact(artifact_v2, INPUT)
    else:
        smart_result = compiler.execute_artifact(cache_manager.load_artifact(), INPUT)

    print(f"    Smart result    = {smart_result}  (expected 30 — rebuilt V2)")
    assert smart_result == 30, f"Smart should return 30, got {smart_result}"

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------
    print("\n" + "=" * 60)
    print("COLLISION SCENARIO RESULTS")
    print("=" * 60)
    print(f"  Naive runtime  → {naive_result}  ← stale V1 executed (BUG)")
    print(f"  Smart runtime  → {smart_result}  ← V2 rebuilt and executed (CORRECT)")
    print("\n✓ Timestamp collision scenario passed.")


if __name__ == "__main__":
    run()
