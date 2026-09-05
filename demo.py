"""
demo.py
-------
End-to-end demonstration of the StaleByte cache-staleness detection system.

Runs the full timestamp-collision scenario and prints a side-by-side
comparison showing:
  • Naive runtime → stale V1 result = 20  (INCORRECT)
  • Smart runtime → rebuilt V2 result = 30 (CORRECT)

Usage
-----
    python demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow imports from within stalebyte/
sys.path.insert(0, str(Path(__file__).parent))

from lib import cache_manager, compiler, source_manager
from lib import staleness_naive, staleness_smart

# ── Configuration ────────────────────────────────────────────────────────────

INPUT_VALUE = 10
FIXED_TS = source_manager.SIMULATED_MTIME   # same for V1 and V2 → collision


# ── Helpers ──────────────────────────────────────────────────────────────────

def _banner(title: str) -> None:
    width = 62
    print("\n" + "═" * width)
    print(f"  {title}")
    print("═" * width)


def _section(n: int, label: str) -> None:
    print(f"\n  [{n}] {label}")
    print("  " + "─" * 56)


# ── Demo steps ───────────────────────────────────────────────────────────────

def step_create_v1() -> None:
    _section(1, "Create & compile source V1  (operation=multiply, factor=2)")
    source_manager.create_source(source_manager.V1_CONTENT)
    content = source_manager.read_source()
    print(f"      Source content:\n{_indent(content)}")

    artifact = compiler.compile_source(content)
    print(f"      Compiled bytecode: {artifact['bytecode']}")
    print(f"      factor={artifact['factor']}")

    src_hash = source_manager.compute_hash(content)
    meta = cache_manager.save_cache(
        artifact=artifact,
        source_content=content,
        source_hash=src_hash,
        source_version="V1",
        t_cache=FIXED_TS,
    )
    print(f"\n      ✓ Cache written")
    print(f"        artifact_id    = {meta['artifact_id']}")
    print(f"        t_cache        = {meta['t_cache']}")
    print(f"        source_version = {meta['source_version']}")
    print(f"        source_hash    = {meta['source_hash'][:16]}…")
    print(f"        source_size    = {meta['source_size']} bytes")


def step_mutate_to_v2() -> None:
    _section(2, "Mutate source to V2  (factor=2 → factor=3)")
    source_manager.create_source(source_manager.V2_CONTENT)
    content = source_manager.read_source()
    print(f"      New source content:\n{_indent(content)}")
    print(f"\n      Simulated mtime = {FIXED_TS}  ← SAME as V1 (collision!)")


def step_naive_runtime() -> dict:
    _section(3, "Naive runtime  (timestamp-only checker)")
    metadata = cache_manager.load_metadata()
    content = source_manager.read_source()

    decision = staleness_naive.check_staleness(FIXED_TS, metadata)
    print(f"      is_stale   = {decision.is_stale}")
    print(f"      reason     = {decision.reason}")

    if not decision.is_stale:
        artifact = cache_manager.load_artifact()
        note = "⚠  Using STALE V1 cache — naive checker was fooled!"
    else:
        artifact = compiler.compile_source(content)
        note = "Cache rebuilt"

    result = compiler.execute_artifact(artifact, INPUT_VALUE)
    print(f"\n      {note}")
    print(f"      execute({INPUT_VALUE}) → {result}   (factor={artifact['factor']})")
    return {"result": result, "artifact": artifact, "decision": decision}


def step_smart_runtime() -> dict:
    _section(4, "Smart runtime  (timestamp + SHA-256 checker)")

    # Restore V2 source and the stale V1 cache (collision state)
    source_manager.create_source(source_manager.V2_CONTENT)
    content_v1 = source_manager.V1_CONTENT
    v1_artifact = compiler.compile_source(content_v1)
    v1_hash = source_manager.compute_hash(content_v1)
    cache_manager.save_cache(
        artifact=v1_artifact,
        source_content=content_v1,
        source_hash=v1_hash,
        source_version="V1",
        t_cache=FIXED_TS,
    )

    content_v2 = source_manager.read_source()
    src_hash_v2 = source_manager.compute_hash(content_v2)
    metadata = cache_manager.load_metadata()

    decision = staleness_smart.check_staleness(FIXED_TS, src_hash_v2, metadata)
    print(f"      is_stale        = {decision.is_stale}")
    print(f"      timestamp_match = {decision.timestamp_match}")
    print(f"      hash_match      = {decision.hash_match}")
    print(f"      reason          = {decision.reason}")

    if decision.is_stale:
        cache_manager.invalidate_cache()
        artifact = compiler.compile_source(content_v2)
        cache_manager.save_cache(
            artifact=artifact,
            source_content=content_v2,
            source_hash=src_hash_v2,
            source_version="V2",
            t_cache=FIXED_TS,
        )
        note = "✓  StaleByte detected staleness — rebuilt from V2!"
    else:
        artifact = cache_manager.load_artifact()
        note = "Cache reused"

    result = compiler.execute_artifact(artifact, INPUT_VALUE)
    print(f"\n      {note}")
    print(f"      execute({INPUT_VALUE}) → {result}   (factor={artifact['factor']})")
    return {"result": result, "artifact": artifact, "decision": decision}


def step_summary(naive_result: int, smart_result: int) -> None:
    _banner("RESULTS SUMMARY")
    print(f"""
  Input value : {INPUT_VALUE}

  ┌─────────────────┬────────┬──────────────────────────────────────┐
  │ Checker         │ Result │ Verdict                              │
  ├─────────────────┼────────┼──────────────────────────────────────┤
  │ Naive (ts only) │  {naive_result:4d}  │ ⚠  Stale V1 executed — BUG!          │
  │ Smart (ts+hash) │  {smart_result:4d}  │ ✓  Staleness detected, V2 rebuilt    │
  └─────────────────┴────────┴──────────────────────────────────────┘
""")
    assert naive_result == 20, f"Expected naive=20, got {naive_result}"
    assert smart_result == 30, f"Expected smart=30, got {smart_result}"
    print("  All assertions passed. StaleByte MVP demo complete.\n")


def _indent(text: str, spaces: int = 8) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in text.rstrip().splitlines())


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    _banner("StaleByte — Compiled-Cache Staleness Detection Demo")
    step_create_v1()
    step_mutate_to_v2()
    naive = step_naive_runtime()
    smart = step_smart_runtime()
    step_summary(naive["result"], smart["result"])


if __name__ == "__main__":
    main()
