"""
normal_flow.py
--------------
Scenario: standard V1 build → cache → execute without any collision.
Demonstrates the happy path: source unchanged, cache is valid, result is 20.
"""

import sys
from pathlib import Path

# Make stalebyte/ importable when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import cache_manager, compiler, source_manager


def run() -> None:
    print("=" * 60)
    print("SCENARIO: Normal Flow (V1, no collision)")
    print("=" * 60)

    # Step 1 — write V1 source
    source_manager.create_source(source_manager.V1_CONTENT)
    content = source_manager.read_source()
    print(f"\n[1] Source written (V1):\n{content.strip()}")

    # Step 2 — compile
    artifact = compiler.compile_source(content)
    print(f"\n[2] Compiled artifact: {artifact}")

    # Step 3 — cache with a deterministic timestamp
    fixed_ts = 1_700_000_000.0
    src_hash = source_manager.compute_hash(content)
    meta = cache_manager.save_cache(
        artifact=artifact,
        source_content=content,
        source_hash=src_hash,
        source_version="V1",
        t_cache=fixed_ts,
    )
    print(f"\n[3] Cache metadata: {meta}")

    # Step 4 — execute
    result = compiler.execute_artifact(artifact, 10)
    print(f"\n[4] Execute(10) → {result}")
    assert result == 20, f"Expected 20, got {result}"
    print("\n✓ Normal flow passed.")


if __name__ == "__main__":
    run()
