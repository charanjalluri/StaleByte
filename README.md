# StaleByte

> **Compiled Cache Staleness Causing Silent Runtime Behavior Mismatch**

StaleByte is a deterministic prototype demonstrating how timestamp-based build cache validation can silently execute outdated logic, and how SHA-256 content fingerprinting resolves the issue.

---

## The Problem

Build systems and compilers frequently use **filesystem modification timestamps (`mtime`)** to decide whether a cached artifact is still valid. However, when source files are modified within the filesystem's timestamp resolution window (or in environments with clock skew), the new source file can share the exact same observable timestamp as the cached build artifact.

A timestamp-only cache validator observes `source_mtime <= t_cache`, assumes the cache is up to date, and silently skips recompilation. This causes the runtime to execute outdated logic without throwing any error or warning.

---

## Demonstration

StaleByte demonstrates this failure deterministically:

1. **Source Version 1 (V1)**:
   ```text
   operation=multiply
   factor=2
   ```
   - Compiled and cached at timestamp `T`.
   - Input `10` produces `20`.

2. **Source Version 2 (V2)**:
   ```text
   operation=multiply
   factor=3
   ```
   - Source is edited, but the observable timestamp remains `T` (simulating a timestamp collision).
   - Input `10` should now produce `30`.

3. **Runtime Divergence**:
   - **Naive Runtime (Timestamp-Only)**: Observes matching timestamps, considers the cache valid, and executes stale V1 artifact -> returns **`20`** (Silent Bug).
   - **StaleByte Smart Runtime (Timestamp + SHA-256)**: Compares source content hash against cached metadata hash, detects the mismatch, invalidates the stale cache, recompiles V2, and returns **`30`** (Correct).

| Validator | Collision Handling | Cache Action | Result (Input 10) | Verdict |
| :--- | :--- | :--- | :---: | :--- |
| **Naive (Timestamp-Only)** | `mtime == t_cache` | Reuses stale V1 cache | **20** | ⚠️ Silent Stale Execution (BUG) |
| **Smart (Timestamp + SHA-256)** | `hash_v2 != hash_v1` | Invalidates & Rebuilds V2 | **30** | ✓ Staleness Detected & Fixed |

---

## Architecture

The project consists of modular components under `lib/` and `runtime/`:

- **Source Manager (`lib/source_manager.py`)**: Handles source I/O, calculates SHA-256 digests (`compute_hash`), and exposes deterministic timestamp simulation (`simulated_mtime`).
- **Toy Compiler (`lib/compiler.py`)**: Parses key-value source definitions, validates syntax, emits bytecode instructions (`LOAD_INPUT`, `PUSH`, `MUL`, `RETURN`), and executes artifacts in a safe stack-based interpreter.
- **Cache Manager (`lib/cache_manager.py`)**: Manages cache persistence (`artifact.json` and `metadata.json`), storing `artifact_id`, `t_cache`, `source_hash`, `source_size`, and `source_version`.
- **Naive Staleness Checker (`lib/staleness_naive.py`)**: Evaluates staleness using only timestamps (`source_mtime > t_cache`).
- **Smart Staleness Checker (`lib/staleness_smart.py`)**: Evaluates staleness using both timestamps and SHA-256 source hashes.
- **Naive Runtime (`runtime/runtime_naive.py`)**: Executes programs using the naive timestamp-only strategy.
- **Smart Runtime (`runtime/runtime_smart.py`)**: Executes programs using the smart content-hash strategy with automated invalidation and rebuilding.

---

## Key Scenarios

Executable demonstration scripts are located in `scenarios/`:

- **Normal Flow (`scenarios/normal_flow.py`)**: Standard compilation, caching, and execution where source is unchanged.
- **Timestamp Collision (`scenarios/timestamp_collision.py`)**: V1 cached -> source mutated to V2 with identical timestamp -> naive vs smart execution comparison.
- **Clock Skew (`scenarios/clock_skew.py`)**: Source timestamp appears in the past (`source_mtime < t_cache`) simulating clock drift without false invalidation.

To run the complete interactive demo:
```bash
python demo.py
```

---

## Project Structure

```text
stalebyte/
├── docs/
│   ├── architecture.md             # System architecture & component design
│   ├── ai-workflow.md                # AI engineering & verification process
│   └── testing-and-verification.md  # Test evidence matrix & verification limits
├── src/
│   └── program.src                 # Controlled key=value source file
├── cache/                          # Cached bytecode artifact and metadata
├── lib/
│   ├── source_manager.py           # Source I/O, SHA-256 fingerprinting, timestamps
│   ├── compiler.py                 # Parser, validator, bytecode generator, interpreter
│   ├── cache_manager.py            # Save, load, and invalidate cache files
│   ├── staleness_naive.py          # Timestamp-only checker (flawed)
│   └── staleness_smart.py          # Timestamp + SHA-256 checker (correct)
├── runtime/
│   ├── runtime_naive.py            # Executes artifact using naive checker
│   └── runtime_smart.py            # Executes artifact using smart checker
├── scenarios/
│   ├── normal_flow.py              # Happy path: V1 build -> cache -> execute
│   ├── timestamp_collision.py      # V1 cached -> V2 source collision demonstration
│   └── clock_skew.py               # Clock skew simulation without false rebuild
├── tests/
│   ├── test_hash.py                # SHA-256 fingerprint correctness
│   ├── test_cache.py               # Cache save/load/invalidation round-trips
│   ├── test_naive_checker.py       # Naive checker fooled during collision
│   ├── test_smart_checker.py       # Smart checker detects collision via hash
│   ├── test_timestamp_window.py    # Boundary timestamp conditions
│   ├── test_clock_skew.py          # Clock skew behavior verification
│   └── test_runtime_end_to_end.py  # Full end-to-end naive vs smart runtime tests
├── conftest.py                     # Test configuration & path setup
├── demo.py                         # End-to-end CLI demonstration
└── requirements.txt
```

---

## Testing

The test suite provides comprehensive coverage across unit, integration, and end-to-end runtime layers:

- **Unit Tests**: SHA-256 stability, timestamp boundary conditions, checker logic.
- **Integration Tests**: Cache persistence, file-level error handling, cache invalidation with temporary isolated fixtures (`tmp_path`).
- **End-to-End Runtime Tests**: Full execution of `runtime_naive.run()` and `runtime_smart.run()` proving naive returns `20` and smart returns `30` in collision scenarios.

### Verified Test Results
```text
42 passed
0 failed
0 skipped
0 warnings
```

To execute tests:
```bash
pytest tests/ -v
```

---

## Security & Safety

- **Controlled DSL**: Source programs only support key-value pairs with integer factors and allowed operations (`operation=multiply`).
- **No Dynamic Code Execution**: The project completely avoids `eval()`, `exec()`, `pickle`, or arbitrary shell execution.
- **Safe Path Handling**: All file paths are validated and resolved via `pathlib.Path`.
