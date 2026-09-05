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

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import cache_manager, compiler, source_manager, staleness_naive, staleness_smart

# Cache was written at T=100; source mtime appears to be T=50 (clock skew).
T_CACHE = 100.0
T_SOURCE_SKEWED = 50.0   # appears older → naive thinks cache is fine
INPUT = 10


def run() -> None:
    print("=" * 60)
    print("SCENARIO: Clock Skew (source mtime < t_cache)")
    print("=" * 60)

    # --- Setup ---
    source_manager.create_source(source_manager.V1_CONTENT)
    content = source_manager.read_source()
    artifact = compiler.compile_source(content)
    src_hash = source_manager.compute_hash(content)
    metadata = cache_manager.save_cache(
        artifact=artifact,
        source_content=content,
        source_hash=src_hash,
        source_version="V1",
        t_cache=T_CACHE,
    )
    print(f"\n[1] V1 cached at t_cache={T_CACHE}")
    print(f"    Simulated source mtime = {T_SOURCE_SKEWED}  (clock skew!)")

    # ---------------------------------------------------------------
    # Naive checker — source looks older, cache seems valid
    # ---------------------------------------------------------------
    naive_decision = staleness_naive.check_staleness(T_SOURCE_SKEWED, metadata)
    print(f"\n[2] Naive checker:")
    print(f"    is_stale = {naive_decision.is_stale}")
    print(f"    reason   = {naive_decision.reason}")

    # ---------------------------------------------------------------
    # Smart checker — hash confirms content is unchanged → valid
    # ---------------------------------------------------------------
    smart_decision = staleness_smart.check_staleness(
        T_SOURCE_SKEWED, src_hash, metadata
    )
    print(f"\n[3] Smart checker:")
    print(f"    is_stale        = {smart_decision.is_stale}")
    print(f"    timestamp_match = {smart_decision.timestamp_match}")
    print(f"    hash_match      = {smart_decision.hash_match}")
    print(f"    reason          = {smart_decision.reason}")

    result = compiler.execute_artifact(artifact, INPUT)
    print(f"\n[4] Execute(10) → {result}")
    assert result == 20

    assert not naive_decision.is_stale, "Naive should see cache as valid under skew"
    assert not smart_decision.is_stale, "Smart should confirm valid (hash unchanged)"

    print("\n✓ Clock skew scenario passed — no false invalidation.")


if __name__ == "__main__":
    run()
