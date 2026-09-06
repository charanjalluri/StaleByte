# StaleByte — Project Summary

---

## Problem

Build systems and language runtimes use filesystem modification timestamps (`mtime`) to decide whether compiled artifacts are stale. This is a fundamentally unreliable signal. Two failure modes produce silent, undetected correctness bugs:

**1. Timestamp resolution collision.** When a source file is edited within the filesystem's resolution window (1–2 seconds on FAT32, ext3, NFS), the new and old version share the exact same `mtime`. The build system concludes the file is unchanged and executes the old compiled artifact — with no error, no warning, and no indication to the developer.

**2. Clock skew.** In distributed CI/CD environments, the build machine and the execution machine run on different system clocks. When a source file is edited on a machine whose clock is behind the build timestamp, the edited file's `mtime` appears *older* than the cached artifact, causing the cache check to pass falsely.

Both failures are silent by construction: the program runs to completion and returns a result — just the *wrong* result. This is the hardest class of bug to diagnose: no exception, no log line, no crash.

---

## Solution

StaleByte replaces timestamp comparison with **SHA-256 content-addressable invalidation**. The `RobustInvalidator` computes `SHA-256(source_bytes)` at read time and compares it against the hash stored in the cache entry at write time. Because the hash is derived from the actual bytes of the file — not from external, mutable filesystem metadata — it is immune to both clock skew and resolution window collisions. If a single byte changes, the hash changes. If the hash is unchanged, the file is unchanged, regardless of what the filesystem clock reports.

The system is architected around a pluggable invalidator interface: `invalidator.check(source: SourceFile, entry: CacheEntry) -> InvalidationDecision`. This makes the two strategies directly substitutable and their behavior directly comparable at every layer — unit tests, integration tests, CLI output, web dashboard, and statistical fuzz testing.

An AI layer (Meta Muse Spark 1.3) is integrated via `services/ai_service.py` to provide natural-language explanations of any `InvalidationDecision`, making the system accessible to developers who are not familiar with the low-level mechanics of cache invalidation.

---

## Results

The correctness claim is verified at three levels:

**Unit and integration testing (131 tests, 0 failures):** Every boundary condition is covered — equal timestamps, ±1 unit, epoch zero, far-future timestamps, hash mismatch under identical mtime, hash match under skewed mtime, compiler parsing and bytecode VM boundaries, and real-disk collision reproduction via `os.utime()`. The full test case document is in `test_case.md`.

**Statistical fuzz testing (10,000 randomized trials):** Trials randomly vary clock resolution (0.5s – 4.0s), skew offset (0s – 200s), and source content mutations. Across all 10,000 trials:

| Validator | Silent Failures | Failure Rate |
|---|---|---|
| `NaiveInvalidator` (mtime only) | 6,390 | **63.9%** |
| `RobustInvalidator` (SHA-256) | 0 | **0.0%** |

The naive strategy fails silently in nearly two-thirds of adversarial conditions. The robust strategy has a provable zero failure rate under the same conditions.

**Real-disk reproduction:** Using `os.utime()` to manually reset filesystem timestamps, the collision scenario is reproduced on a real disk — not a simulation — confirming the bug is not an artifact of the virtual clock model. Test `TC-025` in `test_cli_and_real_fs.py` verifies this.

---

## Technical Specifications

| Specification | Detail |
|---|---|
| Language | Python 3.8+ |
| External dependencies | None (stdlib only; `pytest` for tests) |
| Hash algorithm | SHA-256 (via `hashlib`) |
| Cache format | JSON, path-keyed by `artifact_<hash>.json` |
| Web server | stdlib `http.server.ThreadingHTTPServer` |
| AI model | Meta Muse Spark 1.3 via REST + SSE |
| Test framework | `pytest` |
| Test count | 131 passed, 0 failed, 0 warnings |
| Fuzz trials | 10,000 (seed=42) |

---

**Repository contains:** `clock.py`, `source.py`, `cache.py`, `invalidators.py`, `runtime/engine.py`, `compiler.py`, `fuzz.py`, `cli.py`, `web/app.py`, `services/ai_service.py`, `services/simulation_service.py`, 18 test files, `demo.py`, `test_case.md`.
