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

from services import simulation_service


def run() -> None:
    print("=" * 60)
    print("SCENARIO: Normal Flow (V1, no collision)")
    print("=" * 60)

    data = simulation_service.run_normal_flow(input_value=10)

    print(f"\n[1] Source written (V1):\n{data['source_content'].strip()}")
    print(f"\n[2] Compiled artifact: {data['artifact']}")
    print(f"\n[3] Cache metadata: {data['metadata']}")
    print(f"\n[4] Execute(10) → {data['result']}")

    if data["result"] != 20:
        raise AssertionError(f"Expected 20, got {data['result']}")
    print("\n✓ Normal flow passed.")


if __name__ == "__main__":
    run()
