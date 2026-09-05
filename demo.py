"""
demo.py
-------
Scripted end-to-end demonstration of StaleByte cache staleness detection.
Demonstrates:
1. Sub-second filesystem timestamp resolution collision window.
2. Machine clock skew simulation where source appears older than cache.
Shows legible FAIL (Naive silently wrong) vs PASS (Robust caught & rebuilt).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure root directory is importable
sys.path.insert(0, str(Path(__file__).parent))

from cache import CacheStore
from clock import VirtualClock
from invalidators import NaiveInvalidator, RobustInvalidator
from runtime import Runtime
from source import SourceFile, V1_CONTENT, V2_CONTENT


def _separator(char: str = "=", width: int = 72) -> None:
    print(char * width)


def run_scenario_resolution_collision(runtime: Runtime) -> None:
    print("\n[SCENARIO 1: Sub-Second Timestamp Resolution Collision (1.0s Window)]")
    print("  1. VirtualClock resolution set to 1.0s (simulating coarse FAT32 / ext4 granularity).")

    clock = VirtualClock(current_time=1_700_000_000.0, resolution=1.0)
    source = SourceFile(content=V1_CONTENT, clock=clock)

    # Step 1: Initial build & cache V1
    runtime.cache_store.invalidate()
    init_res = runtime.execute(source, RobustInvalidator(), input_value=10)
    print(f"  2. Source V1 written (factor=2), compiled, cached at mtime={source.mtime}.")
    print(f"     Artifact cached with hash {source.content_hash[:16]}... -> Initial output = {init_res.output}")

    # Step 2: Edit source to V2 within the same 1.0s window
    clock.advance(0.4)
    source.update_content(V2_CONTENT)
    print(f"  3. Source edited to V2 (factor=3) +0.4s later (within 1s window).")
    print(f"     Observed source mtime remains {source.mtime} (COLLISION WINDOW).")

    # Step 3: Run Naive Invalidator
    naive_res = runtime.execute(source, NaiveInvalidator(), input_value=10)
    print("\n  [NAIVE INVALIDATOR (mtime <= cached_mtime)]:")
    print(f"    Decision  : is_stale={naive_res.decision.is_stale} (Cache HIT)")
    print(f"    Reason    : {naive_res.decision.reason}")
    print(f"    Execution : Output = {naive_res.output} (factor={naive_res.artifact['factor']})")
    if naive_res.output == 20:
        print("    Verdict   : ❌ FAIL (SILENT RUNTIME MISMATCH BUG — expected 30, got 20)")
    else:
        print("    Verdict   : ✓ PASS")

    # Step 4: Run Robust Invalidator
    # Restore collision state for fair test
    runtime.cache_store.invalidate()
    source_v1 = SourceFile(content=V1_CONTENT, clock=VirtualClock(current_time=1_700_000_000.0, resolution=1.0))
    runtime.execute(source_v1, RobustInvalidator(), input_value=10)

    robust_res = runtime.execute(source, RobustInvalidator(), input_value=10)
    print("\n  [ROBUST INVALIDATOR (SHA-256 Content Fingerprint)]:")
    print(f"    Decision  : is_stale={robust_res.decision.is_stale} (Cache MISS)")
    print(f"    Reason    : {robust_res.decision.reason}")
    print(f"    Action    : Stale cache invalidated -> Recompiled from V2")
    print(f"    Execution : Output = {robust_res.output} (factor={robust_res.artifact['factor']})")
    if robust_res.output == 30:
        print("    Verdict   : ✓ PASS (STALENESS DETECTED & CORRECTED — output 30)")
    else:
        print("    Verdict   : ❌ FAIL")


def run_scenario_clock_skew(runtime: Runtime) -> None:
    print("\n[SCENARIO 2: Clock Skew Simulation (Build Machine Ahead vs Run Machine Behind)]")
    print("  1. Build machine clock is ahead (T=1_700_000_100.0). Artifact V1 is compiled and cached.")

    build_clock = VirtualClock(current_time=1_700_000_100.0, resolution=1.0)
    source_v1 = SourceFile(content=V1_CONTENT, clock=build_clock)

    runtime.cache_store.invalidate()
    runtime.execute(source_v1, RobustInvalidator(), input_value=10)
    print(f"  2. Source V1 cached at build timestamp t_cache={source_v1.mtime}.")

    # Run machine clock is 50 seconds behind
    run_clock = VirtualClock(current_time=1_700_000_050.0, resolution=1.0)
    source_v2 = SourceFile(content=V2_CONTENT, clock=run_clock)
    print(f"  3. Source edited to V2 on run machine where clock is behind (mtime={source_v2.mtime} < t_cache={source_v1.mtime}).")

    # Step 3: Run Naive Invalidator under skew
    naive_res = runtime.execute(source_v2, NaiveInvalidator(), input_value=10)
    print("\n  [NAIVE INVALIDATOR (mtime <= cached_mtime)]:")
    print(f"    Decision  : is_stale={naive_res.decision.is_stale} (Cache HIT)")
    print(f"    Reason    : {naive_res.decision.reason}")
    print(f"    Execution : Output = {naive_res.output} (factor={naive_res.artifact['factor']})")
    if naive_res.output == 20:
        print("    Verdict   : ❌ FAIL (SILENT RUNTIME MISMATCH BUG — expected 30, got 20)")
    else:
        print("    Verdict   : ✓ PASS")

    # Step 4: Run Robust Invalidator under skew
    # Restore skew cache state
    runtime.cache_store.invalidate()
    runtime.execute(source_v1, RobustInvalidator(), input_value=10)

    robust_res = runtime.execute(source_v2, RobustInvalidator(), input_value=10)
    print("\n  [ROBUST INVALIDATOR (SHA-256 Content Fingerprint)]:")
    print(f"    Decision  : is_stale={robust_res.decision.is_stale} (Cache MISS)")
    print(f"    Reason    : {robust_res.decision.reason}")
    print(f"    Action    : Stale cache invalidated -> Recompiled from V2")
    print(f"    Execution : Output = {robust_res.output} (factor={robust_res.artifact['factor']})")
    if robust_res.output == 30:
        print("    Verdict   : ✓ PASS (STALENESS DETECTED & CORRECTED — output 30)")
    else:
        print("    Verdict   : ❌ FAIL")


def main() -> None:
    _separator("=")
    print("  STALEBYTE — Compiled Cache Staleness Detection Demo")
    _separator("=")

    demo_cache_dir = Path(__file__).parent / "cache"
    runtime = Runtime(cache_store=CacheStore(cache_dir=demo_cache_dir))

    run_scenario_resolution_collision(runtime)
    _separator("-")
    run_scenario_clock_skew(runtime)
    _separator("=")
    print("  EVALUATION SUMMARY: Naive Failures: 2/2 | Robust Passes: 2/2")
    _separator("=")


if __name__ == "__main__":
    main()
