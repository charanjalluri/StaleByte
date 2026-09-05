# Testing and Verification

## 1. Purpose

The StaleByte project demonstrates compiled-cache staleness caused by a timestamp-only validation flaw and provides a cryptographically sound resolution. Specifically, the test suite and verification framework prove two foundational claims:

1. **A timestamp-only cache validator can be silently fooled**: When a source file is edited within the filesystem timestamp resolution window (or under simulated equal mtimes), a naive validator observes `source_mtime <= t_cache`, declares the stale cached artifact valid, and silently returns an incorrect runtime output (executing V1 factor=2 returning 20 on input 10 instead of V2 factor=3 returning 30).
2. **The StaleByte smart validator detects the stale artifact and forces a correct rebuild**: By comparing the current source SHA-256 digest against the cached fingerprint alongside timestamps, StaleByte detects content changes even when timestamps match, invalidates the stale cache, recompiles the current source, persists the new artifact, and executes the rebuilt artifact (returning 30 on input 10).

---

## 2. Test Strategy

The verification strategy spans three distinct layers: isolated unit tests, filesystem-isolated integration tests, and end-to-end runtime verification.

```
+-----------------------------------------------------------------------+
|                       End-to-End Runtime Tests                        |
|        (runtime engine & run_naive / run_smart on tmp_path)           |
+-----------------------------------------------------------------------+
                                    |
+-----------------------------------------------------------------------+
|                          Integration Tests                            |
|       (cache_manager save/load/invalidation with tmp_path fixtures)   |
+-----------------------------------------------------------------------+
                                    |
+-----------------------------------------------------------------------+
|                             Unit Tests                                |
|    (Pure functions: compute_hash, parse/validate, staleness checkers)  |
+-----------------------------------------------------------------------+
```

### Unit Tests
- **SHA-256 Computation (`test_hash.py`)**: Tests stability across identical inputs, divergence on single-byte changes, 64-character hex length, empty string handling, and case sensitivity.
- **Timestamp Boundary & Checker Logic (`test_naive_checker.py`, `test_smart_checker.py`, `test_timestamp_window.py`)**: Tests decisions when `mtime > t_cache`, `mtime == t_cache`, `mtime < t_cache`, zero timestamps, and future timestamps.

### Integration Tests
- **Cache Persistence Round-Trips (`test_cache.py`)**: Verifies `save_cache()`, `load_artifact()`, `load_metadata()`, `cache_exists()`, and `invalidate_cache()` using temporary isolated directories (`tmp_path`) without mocking file I/O.
- **Error Handling**: Verifies graceful error raising (`FileNotFoundError` and `ValueError`) on missing or malformed JSON artifacts and metadata.

### End-to-End Runtime Tests
- **Runtime Execution (`test_runtime_end_to_end.py`)**: Executes public entry points `runtime.run_naive()` and `runtime.run_smart()` with a real filesystem source file and cache state.
  - Naive Runtime: Demonstrates silent return of stale result `20`.
  - Smart Runtime: Demonstrates automatic cache invalidation, recompilation, persistence of updated artifact, and return of correct result `30`.
  - Idempotence: Verifies that unchanged source does not trigger redundant invalidation or rebuilds.

---

## 3. Timestamp Resolution Collision

The timestamp collision scenario creates an environment where physical filesystem clock resolution prevents the timestamp from advancing between source edits.

```
       V1 Source                     V1 Artifact Cache
 (factor=2, mtime=T)             (factor=2, source_hash=HASH_V1,
          |                                 t_cache=T)
          |                                     |
          +------------------+------------------+
                             |
                     [ SOURCE EDITED ]
                             |
                             v
                       V2 Source
                  (factor=3, mtime=T,
                   source_hash=HASH_V2)
                             |
            +----------------+----------------+
            |                                 |
            v                                 v
     [ Naive Runtime ]                [ Smart Runtime ]
    mtime (T) <= t_cache (T)        mtime (T) <= t_cache (T)
    -> Declares VALID [FAIL]        HASH_V2 != HASH_V1
    -> Reuses V1 Artifact           -> Declares STALE [PASS]
    -> Returns: 20 (WRONG)          -> Invalidate & Recompile V2
                                    -> Persist V2 Cache
                                    -> Returns: 30 (CORRECT)
```

In `lib/source_manager.py`, `SIMULATED_MTIME = 1_700_000_000.0` provides a deterministic timestamp for both V1 and V2, ensuring tests do not depend on system clock speed or sleep intervals.

---

## 4. Clock Skew Simulation

The clock skew tests (`test_clock_skew.py` and `scenarios/clock_skew.py`) simulate environments where the source file timestamp is behind the build artifact timestamp (`source_mtime < t_cache`).

### Verified Properties
- When source content is unchanged and `source_mtime < t_cache`, both naive and smart validators correctly treat the cache as valid (no false invalidation).
- When source content changes while `source_mtime < t_cache`, the naive validator fails to detect the change because `source_mtime <= t_cache`, whereas the smart validator checks `source_hash == cached_hash`, detects the mismatch, and flags staleness.

### Scope Limitation
This simulation models clock skew at the timestamp decision level. It demonstrates that content hashing is invariant to clock ordering anomalies, but does not implement distributed NTP synchronization or vector clocks.

---

## 5. AI Output Verification

Every component produced with AI assistance was subjected to strict engineering verification:

```
+-----------------------------------+
|     AI-Assisted Implementation    |
+-----------------------------------+
                  |
                  v
+-----------------------------------+
|    Manual Inspection & Review     |
+-----------------------------------+
                  |
                  v
+-----------------------------------+
|      Requirements Checklist       |
+-----------------------------------+
                  |
                  v
+-----------------------------------+
|  Unit, Integration & E2E Tests    |
+-----------------------------------+
                  |
                  v
+-----------------------------------+
|  Targeted Fixes & Regression Run  |
+-----------------------------------+
                  |
                  v
+-----------------------------------+
|    Full Passing Test Suite (42)   |
+-----------------------------------+
```

### Concrete Verification & Remediation Examples
1. **Missing End-to-End Coverage**: Initial test scaffolding covered unit checkers but lacked full runtime invocation tests. `tests/test_runtime_end_to_end.py` was authored to test `runtime_naive.run()` and `runtime_smart.run()` end-to-end on temporary filesystem paths.
2. **Code Cleanliness & Dead Imports**: Code review identified unused imports (`import json`, `from pathlib import Path`) in `lib/compiler.py` and a redundant f-string literal `f"LOAD_INPUT"`. These were removed.
3. **Diagnostic Precision in Decision Objects**: Review of `lib/staleness_smart.py` revealed that the decision reason string labeled any `not hash_match` as a "collision", even when `source_mtime < t_cache` (clock skew). The logic was refined to distinguish timestamp collision (`mtime == t_cache`) from content modification under clock skew (`mtime < t_cache`).

---

## 6. Test Evidence Matrix

| Project Claim | Test File | Test Name | Test Type | Evidence | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Hash Stability | `tests/test_hash.py` | `test_hash_stable_for_identical_content` | Unit | Identical strings produce identical SHA-256 digests | PASS |
| Hash Sensitivity | `tests/test_hash.py` | `test_hash_differs_for_different_content` | Unit | V1 and V2 contents yield distinct hex digests | PASS |
| Cache Persistence | `tests/test_cache.py` | `test_save_and_load_artifact` | Integration | Artifact dictionary serializes and deserializes cleanly | PASS |
| Metadata Integrity | `tests/test_cache.py` | `test_save_and_load_metadata` | Integration | Stores `source_hash`, `t_cache`, `source_size`, `source_version`, `artifact_id` | PASS |
| Cache Invalidation | `tests/test_cache.py` | `test_invalidate_removes_files` | Integration | Deletes artifact.json and metadata.json from disk | PASS |
| Naive Timestamp Match | `tests/test_naive_checker.py` | `test_cache_valid_when_timestamps_equal` | Unit | `source_mtime == t_cache` returns `is_stale=False` | PASS |
| Naive Collision Flaw | `tests/test_naive_checker.py` | `test_collision_scenario_naive_is_fooled` | Unit | Equal timestamps fool naive checker into valid verdict | PASS |
| Smart Collision Catch | `tests/test_smart_checker.py` | `test_collision_detected_by_hash` | Unit | Hash mismatch triggers `is_stale=True` despite equal mtimes | PASS |
| No False Invalidation | `tests/test_smart_checker.py` | `test_no_false_invalidation_when_unchanged` | Unit | Same mtime + same hash returns `is_stale=False` | PASS |
| Clock Skew Detection | `tests/test_clock_skew.py` | `test_smart_detects_change_under_skew_if_hash_differs` | Unit | `mtime < t_cache` with altered hash returns `is_stale=True` | PASS |
| Naive Stale Execution | `tests/test_runtime_end_to_end.py` | `test_naive_runtime_returns_stale_v1_result` | E2E | Collision returns 20 (stale V1 factor=2) on input 10 | PASS |
| Smart Rebuild Execution | `tests/test_runtime_end_to_end.py` | `test_smart_runtime_detects_staleness_and_returns_v2_result` | E2E | Collision returns 30 (rebuilt V2 factor=3) on input 10 | PASS |
| Smart Idempotence | `tests/test_runtime_end_to_end.py` | `test_smart_runtime_no_rebuild_when_source_unchanged` | E2E | Second run reuses cache without rebuild (`cache_used=True`) | PASS |

---

## 7. Final Results

Executed using pytest in the project virtual environment:

```text
============================= test session starts =============================
platform win32 -- Python 3.8.10, pytest-8.3.5, pluggy-1.5.0
rootdir: stalebyte
collected 42 items

tests/test_cache.py ........                                             [ 19%]
tests/test_clock_skew.py ....                                            [ 28%]
tests/test_hash.py .....                                                 [ 40%]
tests/test_naive_checker.py .....                                        [ 52%]
tests/test_runtime_end_to_end.py ....                                    [ 61%]
tests/test_smart_checker.py ......                                       [ 76%]
tests/test_timestamp_window.py ..........                                [100%]

============================= 42 passed in 0.20s ==============================
```

- **Total Tests**: 42
- **Passed**: 42
- **Failed**: 0
- **Skipped**: 0
- **Warnings**: 0

---

## 8. Verification Limits

1. **Toy Compiler Domain**: The compiler parses a controlled key=value DSL (`operation=multiply`, `factor=<int>`) and interprets a safe bytecode stack. It does not compile arbitrary ASTs or C/LLVM binaries.
2. **Deterministic Time Modeling**: Simulated epoch floats are used to reliably model sub-second filesystem timestamp collisions without race conditions or flaky sleep loops.
3. **Cache Storage Scale**: Metadata and artifacts are serialized as formatted JSON on local disk. Large-scale blob hashing overhead and distributed cloud caches are outside the MVP scope.
4. **Execution Safety**: The runtime is intentionally sandboxed: no `eval()`, `exec()`, or dynamic imports are used.
