# StaleByte — System Architecture

## 1. Executive Summary

StaleByte is a deterministic prototype demonstrating **compiled-cache staleness caused by timestamp validation failure** and its resolution via **SHA-256 cryptographic content fingerprinting**.

Build systems traditionally rely on file modification timestamps (`mtime`) to skip unnecessary recompilation. However, when edits occur within the filesystem timestamp resolution window (or in environments with clock skew), two distinct source versions can have identical observable timestamps. A timestamp-only validator incorrectly reuses a stale binary, resulting in silent runtime behavioral divergence.

---

## 2. Core Components

```
                     +---------------------------------+
                     |         Source Manager          |
                     |  (File I/O, SHA-256, mtime)     |
                     +---------------------------------+
                                      |
                     +---------------------------------+
                     |          Toy Compiler           |
                     |   (Parse, Validate, Bytecode)   |
                     +---------------------------------+
                                      |
                     +---------------------------------+
                     |         Cache Manager           |
                     |  (artifact.json, metadata.json) |
                     +---------------------------------+
                                      |
               +----------------------+----------------------+
               |                                             |
               v                                             v
+-------------------------------+             +-------------------------------+
|     Naive Staleness Checker   |             |     Smart Staleness Checker   |
|   (mtime > t_cache ONLY)      |             |   (mtime AND SHA-256 Hash)    |
+-------------------------------+             +-------------------------------+
               |                                             |
               v                                             v
+-------------------------------+             +-------------------------------+
|         Naive Runtime         |             |         Smart Runtime         |
|  (Executes stale V1 -> 20)    |             |  (Rebuilds & runs V2 -> 30)   |
+-------------------------------+             +-------------------------------+
```

### 2.1 Source Manager (`lib/source_manager.py`)
- Reads and writes source programs in a controlled key-value format.
- Computes SHA-256 digests of source content (`compute_hash`).
- Provides `simulated_mtime()` returning a constant timestamp (`1_700_000_000.0`) to model deterministic timestamp collisions across edits.

### 2.2 Toy Compiler & Interpreter (`lib/compiler.py`)
- **Parser**: Parses strict `key=value` definitions (`operation=multiply`, `factor=<int>`).
- **Validator**: Enforces allowed operations and positive integer factor bounds.
- **Bytecode Generator**: Emits a deterministic instruction list:
  ```json
  ["LOAD_INPUT", "PUSH 2", "MUL", "RETURN"]
  ```
- **Interpreter**: Sandboxed stack-based virtual machine (`execute_artifact`). Contains no `eval()` or `exec()`.

### 2.3 Cache Manager (`lib/cache_manager.py`)
- Persists two synchronized files:
  - `artifact.json`: The compiled bytecode and operation parameters.
  - `metadata.json`: Structural cache envelope containing `artifact_id`, `t_cache`, `source_hash`, `source_size`, and `source_version`.
- Provides transactional invalidation (`invalidate_cache`) and atomic verification.

### 2.4 Staleness Checkers
- **Naive Checker (`lib/staleness_naive.py`)**:
  - Condition: `is_stale = source_mtime > t_cache`
  - Flaw: When `source_mtime == t_cache`, it declares the cache valid even if content changed.
- **Smart Checker (`lib/staleness_smart.py`)**:
  - Condition: `is_stale = (not hash_match) or (source_mtime > t_cache)`
  - Resilience: Even under timestamp equality (`source_mtime == t_cache`) or clock skew (`source_mtime < t_cache`), hash divergence flags staleness.

### 2.5 Execution Runtimes
- **Naive Runtime (`runtime/runtime_naive.py`)**: Reuses the cached artifact when naive checker approves; fails silently in collision scenarios by running stale V1 code (yielding `20` on input `10`).
- **Smart Runtime (`runtime/runtime_smart.py`)**: Rebuilds when smart checker detects hash mismatch, saves new metadata, and runs rebuilt V2 code (yielding `30` on input `10`).

---

## 3. Data Flow & Collision Lifecycle

```
1. Initial Build (V1)
   Source: factor=2, mtime=T
   -> Compile -> Artifact V1 (factor=2)
   -> Cache Metadata: t_cache=T, source_hash=HASH_V1

2. Source Mutation (V2)
   Source: factor=3, mtime=T  (Within resolution collision window)
   Current Hash: HASH_V2

3. Evaluation
   +-------------------+-----------------------------+-----------------------------+
   | Component         | Naive Strategy              | Smart Strategy              |
   +-------------------+-----------------------------+-----------------------------+
   | Timestamp Check   | T <= T -> Valid             | T <= T -> Valid             |
   | Content Hash Check| Skipped                     | HASH_V2 != HASH_V1 -> STALE |
   | Action            | Load stale V1 artifact      | Invalidate, Recompile V2    |
   | Execution (in=10) | 10 * 2 = 20 (FAIL)          | 10 * 3 = 30 (PASS)          |
   +-------------------+-----------------------------+-----------------------------+
```

---

## 4. Security & Isolation Model

- **Safe Execution**: All operations are evaluated by a strict stack interpreter supporting only `LOAD_INPUT`, `PUSH`, `MUL`, and `RETURN`.
- **Zero Dynamic Execution**: No `eval`, `exec`, `pickle`, or `subprocess` calls.
- **Isolated File I/O**: Strict `pathlib.Path` resolution prevents path traversal.
