# StaleByte — Complete Test Case Documentation

> **Total Test Cases: 131** across **19 test files**  
> All tests pass: `131 passed in 49.51s` (verified run on 2026-09-06)

---

## Table of Contents

| # | Test File | Tests |
|---|---|---|
| 1 | [test_ai_service.py](#1-test_ai_servicepy) | 8 |
| 2 | [test_cache.py](#2-test_cachepy) | 8 |
| 3 | [test_cache_store.py](#3-test_cache_storepy) | 3 |
| 4 | [test_cli_and_real_fs.py](#4-test_cli_and_real_fspy) | 8 |
| 5 | [test_clock_skew.py](#5-test_clock_skewpy) | 4 |
| 6 | [test_fuzz.py](#6-test_fuzzpy) | 4 |
| 7 | [test_hash.py](#7-test_hashpy) | 5 |
| 8 | [test_invalidators.py](#8-test_invalidatorspy) | 4 |
| 9 | [test_naive_checker.py](#9-test_naive_checkerpy) | 5 |
| 10 | [test_runtime_end_to_end.py](#10-test_runtime_end_to_endpy) | 4 |
| 11 | [test_simulation_service.py](#11-test_simulation_servicepy) | 4 |
| 12 | [test_smart_checker.py](#12-test_smart_checkerpy) | 6 |
| 13 | [test_source_file.py](#13-test_source_filepy) | 2 |
| 14 | [test_timestamp_window.py](#14-test_timestamp_windowpy) | 10 |
| 15 | [test_unified_runtime.py](#15-test_unified_runtimepy) | 2 |
| 16 | [test_upload_check.py](#16-test_upload_checkpy) | 6 |
| 17 | [test_virtual_clock.py](#17-test_virtual_clockpy) | 3 |
| 18 | [test_web_api.py](#18-test_web_apipy) | 15 |

---

## 1. test_ai_service.py

**Module under test:** `services/ai_service.py`  
**Purpose:** Unit tests for the Meta Muse Spark 1.3 AI chat service — message preparation, API key lookup, streaming SSE, error handling, and diagnostic explanation.

---

### TC-001 · `test_prepare_messages_adds_system_prompt`

| Field | Detail |
|---|---|
| **Function** | `test_prepare_messages_adds_system_prompt` |
| **What It Tests** | `prepare_messages()` prepends the StaleByte system prompt when no system message exists |
| **Input** | `[{"role": "user", "content": "Hello"}]` |
| **Expected** | 2 messages; first role is `system`; content contains `"StaleByte Assistant"` |
| **Result** | ✅ PASS |

---

### TC-002 · `test_prepare_messages_preserves_existing_system_prompt`

| Field | Detail |
|---|---|
| **Function** | `test_prepare_messages_preserves_existing_system_prompt` |
| **What It Tests** | If caller provides a system message, `prepare_messages()` must NOT prepend a second one |
| **Input** | `[{"role": "system", ...}, {"role": "user", ...}]` |
| **Expected** | 2 messages; first content remains `"Custom system prompt"` unchanged |
| **Result** | ✅ PASS |

---

### TC-003 · `test_unconfigured_yields_friendly_setup_guidance`

| Field | Detail |
|---|---|
| **Function** | `test_unconfigured_yields_friendly_setup_guidance` |
| **What It Tests** | When all API key env vars are absent, `get_chat_response()` returns friendly setup guidance |
| **Input** | All of `MUSE_SPARK_API_KEY`, `META_API_KEY`, `MUSE_API_KEY` removed from env |
| **Expected** | `is_configured()=False`; response contains `"META_API_KEY"` and `"not configured"` |
| **Result** | ✅ PASS |

---

### TC-004 · `test_configured_api_key_lookup`

| Field | Detail |
|---|---|
| **Function** | `test_configured_api_key_lookup` |
| **What It Tests** | `is_configured()` and `get_api_key()` resolve the key from `META_API_KEY` env var |
| **Input** | `META_API_KEY=test-secret-key-123` |
| **Expected** | `is_configured()=True`; `get_api_key()="test-secret-key-123"` |
| **Result** | ✅ PASS |

---

### TC-005 · `test_custom_api_base_url`

| Field | Detail |
|---|---|
| **Function** | `test_custom_api_base_url` |
| **What It Tests** | `get_api_url()` appends `/chat/completions` to a custom base URL from env |
| **Input** | `META_API_BASE_URL=https://custom.api.meta.ai/v1` |
| **Expected** | `"https://custom.api.meta.ai/v1/chat/completions"` |
| **Result** | ✅ PASS |

---

### TC-006 · `test_streaming_success`

| Field | Detail |
|---|---|
| **Function** | `test_streaming_success` |
| **What It Tests** | `stream_chat_completion()` correctly parses SSE `data:` chunks and yields delta content |
| **Input** | Mocked `urlopen` returning 3 SSE chunks + `[DONE]`; `META_API_KEY` set |
| **Expected** | Joined chunks = `"Stale cache occurs when timestamps collide."` |
| **Result** | ✅ PASS |

---

### TC-007 · `test_http_rate_limit_handled_gracefully`

| Field | Detail |
|---|---|
| **Function** | `test_http_rate_limit_handled_gracefully` |
| **What It Tests** | HTTP 429 from the API yields a user-friendly rate limit message instead of raising |
| **Input** | Mocked `urlopen` raises `HTTPError(429)` |
| **Expected** | Response contains `"rate limit"` (case-insensitive) |
| **Result** | ✅ PASS |

---

### TC-008 · `test_network_failure_handled_gracefully`

| Field | Detail |
|---|---|
| **Function** | `test_network_failure_handled_gracefully` |
| **What It Tests** | `URLError` (network unreachable) yields a friendly connection error message |
| **Input** | Mocked `urlopen` raises `URLError("Connection refused")` |
| **Expected** | Response contains `"unable to connect"` (case-insensitive) |
| **Result** | ✅ PASS |

---

### TC-009 · `test_muse_spark_api_key_lookup`

| Field | Detail |
|---|---|
| **Function** | `test_muse_spark_api_key_lookup` |
| **What It Tests** | `get_api_key()` resolves from `MUSE_SPARK_API_KEY` (highest-priority env var) |
| **Input** | Only `MUSE_SPARK_API_KEY=spark-key-999` set |
| **Expected** | `is_configured()=True`; `get_api_key()="spark-key-999"` |
| **Result** | ✅ PASS |

---

### TC-010 · `test_explain_diagnostic_unconfigured_returns_fallback`

| Field | Detail |
|---|---|
| **Function** | `test_explain_diagnostic_unconfigured_returns_fallback` |
| **What It Tests** | Without an API key, `explain_diagnostic()` returns the `reason` string from the diagnostic dict |
| **Input** | No API keys; diagnostic reason = `"mtime <= t_cache. Coarse clock collision triggered silent stale reuse."` |
| **Expected** | Result contains `"Coarse clock collision triggered silent stale reuse"` |
| **Result** | ✅ PASS |

---

### TC-011 · `test_explain_diagnostic_success`

| Field | Detail |
|---|---|
| **Function** | `test_explain_diagnostic_success` |
| **What It Tests** | When API is configured and responds, `explain_diagnostic()` returns AI-generated content |
| **Input** | `MUSE_SPARK_API_KEY` set; mocked response with AI explanation text |
| **Expected** | Result contains `"outdated artifact"` and `"cryptographic hashing"` |
| **Result** | ✅ PASS |

---

### TC-012 · `test_explain_diagnostic_error_fallback`

| Field | Detail |
|---|---|
| **Function** | `test_explain_diagnostic_error_fallback` |
| **What It Tests** | HTTP 500 from API makes `explain_diagnostic()` fall back to the raw reason string |
| **Input** | API key set; mocked `urlopen` raises `HTTPError(500)`; reason = `"fallback diagnostic message"` |
| **Expected** | Result equals `"fallback diagnostic message"` |
| **Result** | ✅ PASS |

---

## 2. test_cache.py

**Module under test:** `lib/cache_manager.py`  
**Purpose:** Cache save/load round-trip correctness. All tests use monkeypatched temp dirs for isolation.

---

### TC-013 · `test_save_and_load_artifact`

| Field | Detail |
|---|---|
| **Function** | `test_save_and_load_artifact` |
| **What It Tests** | Artifact dict survives `save_cache()` → `load_artifact()` without data loss |
| **Input** | V1 artifact, V1 hash, `t_cache=1_700_000_000.0` |
| **Expected** | `load_artifact()` returns dict equal to saved artifact |
| **Result** | ✅ PASS |

---

### TC-014 · `test_save_and_load_metadata`

| Field | Detail |
|---|---|
| **Function** | `test_save_and_load_metadata` |
| **What It Tests** | All metadata fields survive round-trip: `source_hash`, `source_version`, `t_cache`, `source_size`, `artifact_id` |
| **Input** | V1 artifact, V1 hash, version `"V1"`, `t_cache=1_700_000_000.0` |
| **Expected** | Loaded metadata has correct values for all required keys |
| **Result** | ✅ PASS |

---

### TC-015 · `test_cache_exists_after_save`

| Field | Detail |
|---|---|
| **Function** | `test_cache_exists_after_save` |
| **What It Tests** | `cache_exists()` is `False` before save and `True` after save |
| **Input** | Fresh temp dir → save V1 artifact |
| **Expected** | `False` → `True` transition |
| **Result** | ✅ PASS |

---

### TC-016 · `test_invalidate_removes_files`

| Field | Detail |
|---|---|
| **Function** | `test_invalidate_removes_files` |
| **What It Tests** | `invalidate_cache()` removes both artifact and metadata files |
| **Input** | Save V1 cache → `invalidate_cache()` |
| **Expected** | `cache_exists()=False` after invalidation |
| **Result** | ✅ PASS |

---

### TC-017 · `test_load_artifact_missing_raises`

| Field | Detail |
|---|---|
| **Function** | `test_load_artifact_missing_raises` |
| **What It Tests** | `load_artifact()` raises `FileNotFoundError` when no artifact file exists |
| **Input** | Empty temp directory |
| **Expected** | `FileNotFoundError` raised |
| **Result** | ✅ PASS |

---

### TC-018 · `test_load_metadata_missing_raises`

| Field | Detail |
|---|---|
| **Function** | `test_load_metadata_missing_raises` |
| **What It Tests** | `load_metadata()` raises `FileNotFoundError` when no metadata file exists |
| **Input** | Empty temp directory |
| **Expected** | `FileNotFoundError` raised |
| **Result** | ✅ PASS |

---

### TC-019 · `test_load_metadata_malformed_raises`

| Field | Detail |
|---|---|
| **Function** | `test_load_metadata_malformed_raises` |
| **What It Tests** | `load_metadata()` raises `ValueError("Malformed metadata cache")` on corrupt JSON |
| **Input** | `metadata.json` written with `"{bad json"` |
| **Expected** | `ValueError` matching `"Malformed metadata cache"` |
| **Result** | ✅ PASS |

---

### TC-020 · `test_load_artifact_malformed_raises`

| Field | Detail |
|---|---|
| **Function** | `test_load_artifact_malformed_raises` |
| **What It Tests** | `load_artifact()` raises `ValueError("Malformed artifact cache")` on corrupt JSON |
| **Input** | `artifact.json` written with `"not json!"` |
| **Expected** | `ValueError` matching `"Malformed artifact cache"` |
| **Result** | ✅ PASS |

---

## 3. test_cache_store.py

**Module under test:** `cache.py (CacheStore, CacheEntry)`  
**Purpose:** Full save/load/invalidate lifecycle of CacheStore.

---

### TC-021 · `test_cache_store_save_load_invalidate`

| Field | Detail |
|---|---|
| **Function** | `test_cache_store_save_load_invalidate` |
| **What It Tests** | Full lifecycle: `exists()=False` → `save()` → `exists()=True` → `load()` returns correct data → `invalidate()` → `exists()=False` |
| **Input** | `CacheEntry(content_hash="abc123hash", cached_mtime=1_700_000_000.0, factor=2 artifact)` |
| **Expected** | All lifecycle transitions correct; loaded entry has matching hash and mtime |
| **Result** | ✅ PASS |

---

## 4. test_cli_and_real_fs.py

**Module under test:** `cli.py, source.py, cache.py, runtime/engine.py`  
**Purpose:** Tests using real filesystem `os.stat()` mtimes, real disk edits, and CLI commands end-to-end.

---


---

### TC-100 · 	est_cache_store_corrupt_file_emits_warning

| Field | Detail |
|---|---|
| **Function** | 	est_cache_store_corrupt_file_emits_warning |
| **What It Tests** | Corrupted cache files trigger visible stderr warnings and warnings.warn rather than being silently swallowed |
| **Input** | Corrupt JSON in metadata/artifact files |
| **Expected** | load() returns None; UserWarning emitted with 'corrupt cache'; [WARN] printed to stderr |
| **Result** | ✅ PASS |

---

### TC-101 · 	est_cache_store_concurrent_writes

| Field | Detail |
|---|---|
| **Function** | 	est_cache_store_concurrent_writes |
| **What It Tests** | Threading locking and atomic os.replace() temp file writes prevent corrupted partial writes under concurrent load |
| **Input** | 40 concurrent thread pool workers calling save() and load() across multiple files |
| **Expected** | All saves succeed without race conditions, corruption, or file lock collisions |
| **Result** | ✅ PASS |

---

### TC-022 · `test_real_source_file_uses_os_stat`

| Field | Detail |
|---|---|
| **Function** | `test_real_source_file_uses_os_stat` |
| **What It Tests** | `SourceFile.from_file()` uses `os.stat().st_mtime` for mtime in real mode |
| **Input** | Real temp file `math.src` (factor=4) |
| **Expected** | `src.mtime ≈ os.stat().st_mtime`; correct size and content |
| **Result** | ✅ PASS |

---

### TC-023 · `test_real_file_unchanged_reports_cache_hit`

| Field | Detail |
|---|---|
| **Function** | `test_real_file_unchanged_reports_cache_hit` |
| **What It Tests** | After initial build, re-checking an unmodified real file reports cache hit for both invalidators |
| **Input** | Real file `calc.src` (factor=7); build; `check_staleness` without change |
| **Expected** | Both `decision_naive.is_stale=False` and `decision_robust.is_stale=False`; `hash_match=True` |
| **Result** | ✅ PASS |

---

### TC-024 · `test_real_file_edited_reports_cache_miss`

| Field | Detail |
|---|---|
| **Function** | `test_real_file_edited_reports_cache_miss` |
| **What It Tests** | Editing a real file changes its SHA-256 hash, causing Robust to report cache miss |
| **Input** | Build with factor=2; overwrite with factor=5 on disk |
| **Expected** | `decision_robust.is_stale=True`; `hash_match=False` |
| **Result** | ✅ PASS |

---

### TC-025 · `test_real_file_collision_via_utime_reproduces_bug_on_real_disk`

| Field | Detail |
|---|---|
| **Function** | `test_real_file_collision_via_utime_reproduces_bug_on_real_disk` |
| **What It Tests** | Reproduces timestamp collision on real disk: mutates file, resets mtime with `os.utime()`. Naive fooled; Robust detects it |
| **Input** | Build factor=2; mutate to factor=9; `os.utime()` resets mtime to cached_mtime |
| **Expected** | `decision_naive.is_stale=False` (fooled); `decision_robust.is_stale=True`; reason contains `"Content hash mismatch"` and `"resolution window collision"` |
| **Result** | ✅ PASS |

---

### TC-026 · `test_missing_file_produces_clean_error`

| Field | Detail |
|---|---|
| **Function** | `test_missing_file_produces_clean_error` |
| **What It Tests** | CLI exits with code 1 and clean error (no traceback) for a missing file |
| **Input** | `cli.main(["check", "totally_missing_file.src"])` |
| **Expected** | `SystemExit(1)`; stderr contains `"does not exist"`; no `"Traceback"` |
| **Result** | ✅ PASS |

---

### TC-027 · `test_malformed_dsl_produces_clean_error`

| Field | Detail |
|---|---|
| **Function** | `test_malformed_dsl_produces_clean_error` |
| **What It Tests** | CLI exits with code 1 and `"Malformed DSL"` error for invalid DSL content |
| **Input** | Real file with `"random_garbage_not_dsl\n"` |
| **Expected** | `SystemExit(1)`; stderr has `"Error: Malformed DSL"`; no `"Traceback"` |
| **Result** | ✅ PASS |

---

### TC-028 · `test_cli_build_and_check_end_to_end`

| Field | Detail |
|---|---|
| **Function** | `test_cli_build_and_check_end_to_end` |
| **What It Tests** | CLI `build` produces correct output; subsequent `check` reports valid cache hit |
| **Input** | Real file (factor=6); `cli build --input 10`; then `cli check` |
| **Expected** | Build stdout contains `"Output Result : 60"`; check stdout contains `"VALID CACHE (HIT)"` and `"Cache is valid and up to date"` |
| **Result** | ✅ PASS |

---

### TC-029 · `test_cli_clean_subcommand`

| Field | Detail |
|---|---|
| **Function** | `test_cli_clean_subcommand` |
| **What It Tests** | `cli clean` removes all `.json` cache files |
| **Input** | Build to populate cache; `cli.main(["clean", "--cache-dir", ...])` |
| **Expected** | No `*.json` files remain after clean |
| **Result** | ✅ PASS |

---

### TC-030 · `test_cli_demo_command`

| Field | Detail |
|---|---|
| **Function** | `test_cli_demo_command` |
| **What It Tests** | `cli demo` runs successfully and prints both scenario headers |
| **Input** | `cli.main(["demo"])` |
| **Expected** | Exit code 0; stdout contains `"STALEBYTE — Compiled Cache Staleness Detection Demo"`, `"SCENARIO 1"`, `"SCENARIO 2"` |
| **Result** | ✅ PASS |

---

## 5. test_clock_skew.py

**Module under test:** `invalidators.py`  
**Purpose:** Proves both checkers behave correctly under machine clock skew (source mtime appears older than cache).

---

### TC-031 · `test_naive_no_false_invalidation_under_skew`

| Field | Detail |
|---|---|
| **Function** | `test_naive_no_false_invalidation_under_skew` |
| **What It Tests** | Naive: older mtime than cache → reports not stale (no false rebuild) |
| **Input** | `source.mtime=1_700_000_000.0`; `cached_mtime=1_700_000_100.0`; same hash |
| **Expected** | `is_stale=False` |
| **Result** | ✅ PASS |

---

### TC-032 · `test_smart_no_false_invalidation_under_skew_same_hash`

| Field | Detail |
|---|---|
| **Function** | `test_smart_no_false_invalidation_under_skew_same_hash` |
| **What It Tests** | Robust: skewed mtime + matching hash → not stale |
| **Input** | `source.mtime=1_700_000_000.0`; `cached_mtime=1_700_000_100.0`; same hash |
| **Expected** | `is_stale=False`; `hash_match=True` |
| **Result** | ✅ PASS |

---

### TC-033 · `test_smart_detects_change_under_skew_if_hash_differs`

| Field | Detail |
|---|---|
| **Function** | `test_smart_detects_change_under_skew_if_hash_differs` |
| **What It Tests** | Even with skewed mtime, Robust detects content change via hash mismatch |
| **Input** | Source mtime 100s behind cached; content altered → different hash |
| **Expected** | `is_stale=True`; `hash_match=False` |
| **Result** | ✅ PASS |

---

### TC-034 · `test_naive_vs_smart_diverge_under_skew_with_change`

| Field | Detail |
|---|---|
| **Function** | `test_naive_vs_smart_diverge_under_skew_with_change` |
| **What It Tests** | Proves divergence: skewed mtime + content change → Naive says valid, Robust says stale |
| **Input** | Altered content (factor=99); source mtime 100s behind cached |
| **Expected** | `naive.is_stale=False`; `smart.is_stale=True` |
| **Result** | ✅ PASS |

---

## 6. test_fuzz.py

**Module under test:** `fuzz.py, cli.py`  
**Purpose:** Statistical tests quantifying silent failure rates across randomized trials.

---

### TC-035 · `test_robust_failure_rate_is_strictly_zero_percent`

| Field | Detail |
|---|---|
| **Function** | `test_robust_failure_rate_is_strictly_zero_percent` |
| **What It Tests** | Robust SHA-256 validator never fails silently across 2,000 randomized trials |
| **Input** | `fuzz.run_fuzz_suite(trials=2000, seed=12345)` |
| **Expected** | `robust_failures=0`; `robust_failure_rate_pct=0.0`; `robust_correct=2000` |
| **Result** | ✅ PASS |

---

### TC-036 · `test_naive_failure_rate_is_strictly_greater_than_zero`

| Field | Detail |
|---|---|
| **Function** | `test_naive_failure_rate_is_strictly_greater_than_zero` |
| **What It Tests** | Naive fails silently in a non-zero percentage of trials; both failure causes are observed |
| **Input** | `fuzz.run_fuzz_suite(trials=2000, seed=12345)` |
| **Expected** | `naive_silent_failures > 0`; `naive_failure_rate_pct > 0.0`; `resolution_collision > 0`; `clock_skew > 0` |
| **Result** | ✅ PASS |

---

### TC-037 · `test_fuzz_json_serialization`

| Field | Detail |
|---|---|
| **Function** | `test_fuzz_json_serialization` |
| **What It Tests** | `FuzzSummary.to_dict()` produces correctly structured machine-readable output |
| **Input** | `fuzz.run_fuzz_suite(trials=100, seed=999)` |
| **Expected** | Keys: `total_trials`, `naive`, `robust`, `exposure_summary`; `robust.failure_rate_pct=0.0`; `naive.failure_rate_pct > 0.0` |
| **Result** | ✅ PASS |

---

### TC-038 · `test_cli_fuzz_subcommand_json`

| Field | Detail |
|---|---|
| **Function** | `test_cli_fuzz_subcommand_json` |
| **What It Tests** | `cli fuzz --trials 100 --json` produces valid JSON with correct values |
| **Input** | `cli.main(["fuzz", "--trials", "100", "--seed", "42", "--json"])` |
| **Expected** | Exit code 0; valid JSON; `total_trials=100`; `robust.failures=0`; `naive.silent_failures > 0` |
| **Result** | ✅ PASS |

---

## 7. test_hash.py

**Module under test:** `lib/source_manager.py (compute_hash)`  
**Purpose:** Verifies SHA-256 fingerprinting correctness and determinism.

---

### TC-039 · `test_hash_stable_for_identical_content`

| Field | Detail |
|---|---|
| **Function** | `test_hash_stable_for_identical_content` |
| **What It Tests** | Same content always produces the same digest |
| **Input** | `V1_CONTENT` hashed twice |
| **Expected** | Both hashes equal |
| **Result** | ✅ PASS |

---

### TC-040 · `test_hash_differs_for_different_content`

| Field | Detail |
|---|---|
| **Function** | `test_hash_differs_for_different_content` |
| **What It Tests** | V1 (`factor=2`) and V2 (`factor=3`) produce different digests |
| **Input** | `V1_CONTENT` vs `V2_CONTENT` |
| **Expected** | Hashes not equal |
| **Result** | ✅ PASS |

---

### TC-041 · `test_hash_is_sha256_length`

| Field | Detail |
|---|---|
| **Function** | `test_hash_is_sha256_length` |
| **What It Tests** | SHA-256 hex digest is always exactly 64 characters |
| **Input** | `V1_CONTENT` |
| **Expected** | `len(hash) == 64` |
| **Result** | ✅ PASS |

---

### TC-042 · `test_hash_empty_string`

| Field | Detail |
|---|---|
| **Function** | `test_hash_empty_string` |
| **What It Tests** | Empty string produces the well-known SHA-256 digest |
| **Input** | `""` |
| **Expected** | `"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"` |
| **Result** | ✅ PASS |

---

### TC-043 · `test_hash_case_sensitive`

| Field | Detail |
|---|---|
| **Function** | `test_hash_case_sensitive` |
| **What It Tests** | Content differing only in case produces different digests |
| **Input** | `"factor=2"` vs `"FACTOR=2"` |
| **Expected** | Hashes not equal |
| **Result** | ✅ PASS |

---

## 8. test_invalidators.py

**Module under test:** `invalidators.py`  
**Purpose:** NaiveInvalidator vs RobustInvalidator using VirtualClock-driven scenarios.

---

### TC-044 · `test_naive_invalidated_when_source_newer`

| Field | Detail |
|---|---|
| **Function** | `test_naive_invalidated_when_source_newer` |
| **What It Tests** | Naive correctly reports `is_stale=True` when `source.mtime > cached_mtime` |
| **Input** | Source clock `1_700_000_001.0`; cache `1_700_000_000.0` |
| **Expected** | `is_stale=True` |
| **Result** | ✅ PASS |

---

### TC-045 · `test_naive_fooled_by_resolution_collision`

| Field | Detail |
|---|---|
| **Function** | `test_naive_fooled_by_resolution_collision` |
| **What It Tests** | Naive reports `is_stale=False` despite content change when mtime is within 1s resolution window |
| **Input** | V1 cached at `1_700_000_000.0`; clock advanced 0.3s; source changed to V2 (same quantized mtime) |
| **Expected** | `is_stale=False` (fooled); `hash_match=False` (content did change) |
| **Result** | ✅ PASS |

---

### TC-046 · `test_robust_catches_resolution_collision`

| Field | Detail |
|---|---|
| **Function** | `test_robust_catches_resolution_collision` |
| **What It Tests** | Robust catches resolution collision: mtime matches but hash differs |
| **Input** | Same as TC-045 but using RobustInvalidator |
| **Expected** | `is_stale=True`; `timestamp_match=True`; `hash_match=False`; reason contains `"resolution window collision"` |
| **Result** | ✅ PASS |

---

### TC-047 · `test_robust_catches_clock_skew`

| Field | Detail |
|---|---|
| **Function** | `test_robust_catches_clock_skew` |
| **What It Tests** | Robust detects content change even when source mtime is behind cached mtime |
| **Input** | Build at `1_700_000_100.0` (V1 cached); run at `1_700_000_050.0`; source changed to V2 |
| **Expected** | `is_stale=True`; reason contains `"clock skew"` |
| **Result** | ✅ PASS |

---

## 9. test_naive_checker.py

**Module under test:** `invalidators.py (NaiveInvalidator)`  
**Purpose:** Detailed behavioral tests for the timestamp-only staleness checker.

---

### TC-048 · `test_cache_valid_when_timestamps_equal`

| Field | Detail |
|---|---|
| **Function** | `test_cache_valid_when_timestamps_equal` |
| **What It Tests** | Naive: `source.mtime == t_cache` → not stale |
| **Input** | Both at `1_700_000_000.0` |
| **Expected** | `is_stale=False` |
| **Result** | ✅ PASS |

---

### TC-049 · `test_cache_valid_when_source_is_older`

| Field | Detail |
|---|---|
| **Function** | `test_cache_valid_when_source_is_older` |
| **What It Tests** | Naive: `source.mtime < t_cache` (clock skew) → not stale |
| **Input** | `source.mtime=FIXED_TS-1`; `entry.cached_mtime=FIXED_TS` |
| **Expected** | `is_stale=False` |
| **Result** | ✅ PASS |

---

### TC-050 · `test_cache_stale_when_source_is_newer`

| Field | Detail |
|---|---|
| **Function** | `test_cache_stale_when_source_is_newer` |
| **What It Tests** | Naive: `source.mtime > t_cache` → stale |
| **Input** | `source.mtime=FIXED_TS+1`; `entry.cached_mtime=FIXED_TS` |
| **Expected** | `is_stale=True` |
| **Result** | ✅ PASS |

---

### TC-051 · `test_decision_contains_reason`

| Field | Detail |
|---|---|
| **Function** | `test_decision_contains_reason` |
| **What It Tests** | `InvalidationDecision.reason` is always a non-empty string |
| **Input** | Equal timestamps (valid scenario) |
| **Expected** | `isinstance(reason, str) and len(reason) > 0` |
| **Result** | ✅ PASS |

---

### TC-052 · `test_collision_scenario_naive_is_fooled`

| Field | Detail |
|---|---|
| **Function** | `test_collision_scenario_naive_is_fooled` |
| **What It Tests** | Naive is fooled: timestamps match but hashes differ → still reports not stale (the intentional flaw) |
| **Input** | `source.mtime=FIXED_TS`; `entry.cached_mtime=FIXED_TS`; different hashes |
| **Expected** | `is_stale=False` |
| **Result** | ✅ PASS |

---

## 10. test_runtime_end_to_end.py

**Module under test:** `runtime/__init__.py (run_naive, run_smart)`  
**Purpose:** End-to-end tests proving `run_naive` and `run_smart` produce correct results in the full collision scenario.

---

### TC-053 · `test_naive_runtime_returns_stale_v1_result`

| Field | Detail |
|---|---|
| **Function** | `test_naive_runtime_returns_stale_v1_result` |
| **What It Tests** | In the collision scenario, `run_naive()` executes the stale V1 artifact and returns 20 instead of the correct 30 |
| **Input** | V1 cached; V2 written to disk; `run_naive(10, simulated_mtime)` |
| **Expected** | `result=20`; `cache_used=True`; `artifact.factor=2` |
| **Result** | ✅ PASS |

---

### TC-054 · `test_smart_runtime_detects_staleness_and_returns_v2_result`

| Field | Detail |
|---|---|
| **Function** | `test_smart_runtime_detects_staleness_and_returns_v2_result` |
| **What It Tests** | In the collision scenario, `run_smart()` detects hash mismatch, rebuilds V2, returns 30 |
| **Input** | Same collision state; `run_smart(10, simulated_mtime)` |
| **Expected** | `result=30`; `rebuilt=True`; `cache_used=False`; `artifact.factor=3` |
| **Result** | ✅ PASS |

---

### TC-055 · `test_smart_runtime_decision_explains_collision`

| Field | Detail |
|---|---|
| **Function** | `test_smart_runtime_decision_explains_collision` |
| **What It Tests** | The `InvalidationDecision` from `run_smart()` confirms: `timestamp_match=True`, `hash_match=False`, `is_stale=True` |
| **Input** | Collision state; `run_smart(10, simulated_mtime)` |
| **Expected** | `d.timestamp_match=True`; `d.hash_match=False`; `d.is_stale=True` |
| **Result** | ✅ PASS |

---

### TC-056 · `test_smart_runtime_no_rebuild_when_source_unchanged`

| Field | Detail |
|---|---|
| **Function** | `test_smart_runtime_no_rebuild_when_source_unchanged` |
| **What It Tests** | Second call with unchanged source reuses cache without rebuilding |
| **Input** | V1 temp file; first `run_smart(10)` → fresh build; second `run_smart(10)` |
| **Expected** | 1st: `result=20`, `rebuilt=False`, `cache_used=False`. 2nd: `result=20`, `cache_used=True`, `rebuilt=False` |
| **Result** | ✅ PASS |

---

## 11. test_simulation_service.py

**Module under test:** `services/simulation_service.py`  
**Purpose:** Unit tests for the simulation service orchestration layer.

---

### TC-057 · `test_simulation_service_normal_flow`

| Field | Detail |
|---|---|
| **Function** | `test_simulation_service_normal_flow` |
| **What It Tests** | `run_normal_flow(10)` returns result=20; both invalidators report not stale |
| **Input** | `input_value=10`; tmp cache |
| **Expected** | `data.result=20`; `naive_decision.is_stale=False`; `smart_decision.is_stale=False` |
| **Result** | ✅ PASS |

---

### TC-058 · `test_simulation_service_collision_scenario`

| Field | Detail |
|---|---|
| **Function** | `test_simulation_service_collision_scenario` |
| **What It Tests** | `run_collision_scenario(10)` returns naive=20 (stale) and smart=30 (rebuilt) |
| **Input** | `input_value=10`; tmp cache |
| **Expected** | `naive_execution.result=20`; `smart_execution.result=30`; `smart.rebuilt=True` |
| **Result** | ✅ PASS |

---

### TC-059 · `test_simulation_service_clock_skew`

| Field | Detail |
|---|---|
| **Function** | `test_simulation_service_clock_skew` |
| **What It Tests** | `run_clock_skew_scenario(10)` returns result=20; no false staleness flags |
| **Input** | `input_value=10`; tmp cache |
| **Expected** | `data.result=20`; neither invalidator flags stale |
| **Result** | ✅ PASS |

---

### TC-060 · `test_simulation_service_status`

| Field | Detail |
|---|---|
| **Function** | `test_simulation_service_status` |
| **What It Tests** | `get_system_status()` returns a dict with required keys |
| **Input** | tmp cache |
| **Expected** | Dict contains `"cache_exists"` and `"simulated_mtime"` |
| **Result** | ✅ PASS |

---

## 12. test_smart_checker.py

**Module under test:** `invalidators.py (RobustInvalidator)`  
**Purpose:** Detailed behavioral tests for the SHA-256-aware staleness checker.

---

### TC-061 · `test_collision_detected_by_hash`

| Field | Detail |
|---|---|
| **Function** | `test_collision_detected_by_hash` |
| **What It Tests** | `mtime == t_cache` but hashes differ → `is_stale=True` (collision detected) |
| **Input** | `source.mtime=FIXED_TS`; `entry.cached_mtime=FIXED_TS`; `source.hash=HASH_V2`; `entry.hash=HASH_V1` |
| **Expected** | `is_stale=True`; `timestamp_match=True`; `hash_match=False` |
| **Result** | ✅ PASS |

---

### TC-062 · `test_no_false_invalidation_when_unchanged`

| Field | Detail |
|---|---|
| **Function** | `test_no_false_invalidation_when_unchanged` |
| **What It Tests** | Unchanged source (same mtime, same hash) → `is_stale=False` (no false rebuild) |
| **Input** | Same mtime, same `HASH_V1` |
| **Expected** | `is_stale=False`; `timestamp_match=True`; `hash_match=True` |
| **Result** | ✅ PASS |

---

### TC-063 · `test_stale_when_source_newer_even_if_hash_same`

| Field | Detail |
|---|---|
| **Function** | `test_stale_when_source_newer_even_if_hash_same` |
| **What It Tests** | `source.mtime > cached_mtime` → stale, even when hash matches (defensive test) |
| **Input** | `source.mtime=FIXED_TS+1`; same hash |
| **Expected** | `is_stale=True` |
| **Result** | ✅ PASS |

---

### TC-064 · `test_valid_when_source_older_and_hash_same`

| Field | Detail |
|---|---|
| **Function** | `test_valid_when_source_older_and_hash_same` |
| **What It Tests** | Clock skew: source appears older + same hash → not stale |
| **Input** | `source.mtime=FIXED_TS-1`; same hash |
| **Expected** | `is_stale=False` |
| **Result** | ✅ PASS |

---

### TC-065 · `test_decision_has_all_fields`

| Field | Detail |
|---|---|
| **Function** | `test_decision_has_all_fields` |
| **What It Tests** | `InvalidationDecision` exposes all required diagnostic fields |
| **Input** | Collision scenario |
| **Expected** | Has attributes: `is_stale`, `timestamp_match`, `hash_match`, `reason`, `source_hash`, `cached_hash` |
| **Result** | ✅ PASS |

---

### TC-066 · `test_reason_mentions_collision`

| Field | Detail |
|---|---|
| **Function** | `test_reason_mentions_collision` |
| **What It Tests** | In collision mode, `decision.reason` references collision or staleness |
| **Input** | Same mtime, different hash |
| **Expected** | `"collision"` or `"stale"` in `reason.lower()` |
| **Result** | ✅ PASS |

---

## 13. test_source_file.py

**Module under test:** `source.py`  
**Purpose:** Tests for SourceFile properties and SHA-256 fingerprinting.

---

### TC-067 · `test_source_file_fingerprinting`

| Field | Detail |
|---|---|
| **Function** | `test_source_file_fingerprinting` |
| **What It Tests** | `content_hash` equals `compute_sha256(content)`; hash changes when content changes |
| **Input** | `SourceFile(V1_CONTENT)` → `update_content(V2_CONTENT)` |
| **Expected** | Initial hash = SHA-256 of V1; after update, hash = SHA-256 of V2 ≠ V1 hash |
| **Result** | ✅ PASS |

---

### TC-068 · `test_source_file_mtime_derived_from_clock`

| Field | Detail |
|---|---|
| **Function** | `test_source_file_mtime_derived_from_clock` |
| **What It Tests** | `SourceFile.mtime` comes from `VirtualClock.quantized_now()`; advancing within 1s window keeps mtime unchanged |
| **Input** | Clock at `1_700_000_000.0`, 1s resolution; advance 0.5s |
| **Expected** | Before advance: `mtime=1_700_000_000.0`. After +0.5s: `mtime=1_700_000_000.0` (resolution collision) |
| **Result** | ✅ PASS |

---

## 14. test_timestamp_window.py

**Module under test:** `invalidators.py`  
**Purpose:** Exhaustive boundary-value tests on mtime comparisons for both Naive and Robust invalidators.

---

### TC-069 · `TestNaiveBoundary::test_equal_ts_is_not_stale`

| Field | Detail |
|---|---|
| **Function** | `TestNaiveBoundary::test_equal_ts_is_not_stale` |
| **What It Tests** | Naive: `source.mtime == cached_mtime` → not stale |
| **Input** | Both = `1000.0` |
| **Expected** | `is_stale=False` |
| **Result** | ✅ PASS |

---

### TC-070 · `TestNaiveBoundary::test_one_unit_newer_is_stale`

| Field | Detail |
|---|---|
| **Function** | `TestNaiveBoundary::test_one_unit_newer_is_stale` |
| **What It Tests** | Naive: `source.mtime = cached_mtime + 1` → stale |
| **Input** | `source.mtime=1001.0`; `cached_mtime=1000.0` |
| **Expected** | `is_stale=True` |
| **Result** | ✅ PASS |

---

### TC-071 · `TestNaiveBoundary::test_one_unit_older_is_not_stale`

| Field | Detail |
|---|---|
| **Function** | `TestNaiveBoundary::test_one_unit_older_is_not_stale` |
| **What It Tests** | Naive: `source.mtime = cached_mtime - 1` → not stale |
| **Input** | `source.mtime=999.0`; `cached_mtime=1000.0` |
| **Expected** | `is_stale=False` |
| **Result** | ✅ PASS |

---

### TC-072 · `TestNaiveBoundary::test_far_future_source_is_stale`

| Field | Detail |
|---|---|
| **Function** | `TestNaiveBoundary::test_far_future_source_is_stale` |
| **What It Tests** | Naive: very large source mtime → stale |
| **Input** | `source.mtime=9_999_999_999.0`; `cached_mtime=1000.0` |
| **Expected** | `is_stale=True` |
| **Result** | ✅ PASS |

---

### TC-073 · `TestNaiveBoundary::test_zero_timestamps_equal_is_not_stale`

| Field | Detail |
|---|---|
| **Function** | `TestNaiveBoundary::test_zero_timestamps_equal_is_not_stale` |
| **What It Tests** | Naive: both timestamps at epoch zero → not stale (boundary at origin) |
| **Input** | Both = `0.0` |
| **Expected** | `is_stale=False` |
| **Result** | ✅ PASS |

---

### TC-074 · `TestSmartBoundary::test_equal_ts_same_hash_is_not_stale`

| Field | Detail |
|---|---|
| **Function** | `TestSmartBoundary::test_equal_ts_same_hash_is_not_stale` |
| **What It Tests** | Robust: equal timestamps + same hash → not stale |
| **Input** | Both mtime=`1000.0`; same `HASH_V1` |
| **Expected** | `is_stale=False` |
| **Result** | ✅ PASS |

---

### TC-075 · `TestSmartBoundary::test_equal_ts_diff_hash_is_stale`

| Field | Detail |
|---|---|
| **Function** | `TestSmartBoundary::test_equal_ts_diff_hash_is_stale` |
| **What It Tests** | Robust: equal timestamps but different hash → stale (collision caught) |
| **Input** | Both mtime=`1000.0`; source hash differs from entry hash |
| **Expected** | `is_stale=True` |
| **Result** | ✅ PASS |

---

### TC-076 · `TestSmartBoundary::test_newer_ts_same_hash_is_stale`

| Field | Detail |
|---|---|
| **Function** | `TestSmartBoundary::test_newer_ts_same_hash_is_stale` |
| **What It Tests** | Robust: newer source mtime with same hash → stale (mtime alone triggers rebuild) |
| **Input** | `source.mtime=1001.0`; `cached_mtime=1000.0`; same hash |
| **Expected** | `is_stale=True` |
| **Result** | ✅ PASS |

---

### TC-077 · `TestSmartBoundary::test_older_ts_same_hash_is_not_stale`

| Field | Detail |
|---|---|
| **Function** | `TestSmartBoundary::test_older_ts_same_hash_is_not_stale` |
| **What It Tests** | Robust: older source mtime + same hash → not stale (clock skew, no content change) |
| **Input** | `source.mtime=999.0`; `cached_mtime=1000.0`; same hash |
| **Expected** | `is_stale=False` |
| **Result** | ✅ PASS |

---

### TC-078 · `TestSmartBoundary::test_older_ts_diff_hash_is_stale`

| Field | Detail |
|---|---|
| **Function** | `TestSmartBoundary::test_older_ts_diff_hash_is_stale` |
| **What It Tests** | Robust: clock-skewed mtime + hash mismatch → stale (content change detected despite skew) |
| **Input** | `source.mtime=999.0`; `cached_mtime=1000.0`; different hashes |
| **Expected** | `is_stale=True` |
| **Result** | ✅ PASS |

---

## 15. test_unified_runtime.py

**Module under test:** `runtime/engine.py (Runtime class)`  
**Purpose:** Tests for unified `Runtime.execute()` with pluggable invalidators.

---

### TC-079 · `test_unified_runtime_collision_scenario`

| Field | Detail |
|---|---|
| **Function** | `test_unified_runtime_collision_scenario` |
| **What It Tests** | Full collision scenario: V1 built → V2 mutated in 1s window → Naive hits stale cache (20) → Robust rebuilds (30) |
| **Input** | VirtualClock 1s resolution; V1 → cache; advance 0.4s; mutate to V2 |
| **Expected** | Naive: `output=20`, `cache_hit=True`, `rebuilt=False`, `factor=2`. Robust: `output=30`, `cache_hit=False`, `rebuilt=True`, `factor=3` |
| **Result** | ✅ PASS |

---

### TC-080 · `test_unified_runtime_idempotent_cache_hit`

| Field | Detail |
|---|---|
| **Function** | `test_unified_runtime_idempotent_cache_hit` |
| **What It Tests** | Two successive `execute()` calls on unchanged source: second is a cache hit |
| **Input** | V1 source; two `execute()` calls with Robust |
| **Expected** | 1st: `output=20`. 2nd: `output=20`; `cache_hit=True`; `rebuilt=False` |
| **Result** | ✅ PASS |

---

## 16. test_upload_check.py

**Module under test:** `services/simulation_service.py, web/app.py`  
**Purpose:** Upload and staleness check lifecycle via live HTTP server and direct service layer.

---

### TC-081 · `test_upload_check_first_upload_and_unchanged_reupload`

| Field | Detail |
|---|---|
| **Function** | `test_upload_check_first_upload_and_unchanged_reupload` |
| **What It Tests** | Full upload lifecycle across 4 uploads: build → HIT → MISS → HIT |
| **Input** | `custom_tool.src` with factor=10, then factor=25; live web server |
| **Expected** | Upload 1: `rebuilt=True`. Upload 2: `robust.is_stale=False`, `HIT`. Upload 3: `robust.is_stale=True`, `MISS`. Upload 4: `robust.is_stale=False`, `HIT` |
| **Result** | ✅ PASS |

---

### TC-082 · `test_upload_check_rejects_empty_file`

| Field | Detail |
|---|---|
| **Function** | `test_upload_check_rejects_empty_file` |
| **What It Tests** | Server returns HTTP 400 for whitespace-only file content |
| **Input** | `{"filename": "empty.src", "content": "   \n\t"}` |
| **Expected** | HTTP 400; error contains `"empty"` |
| **Result** | ✅ PASS |

---

### TC-083 · `test_upload_check_rejects_malformed_dsl`

| Field | Detail |
|---|---|
| **Function** | `test_upload_check_rejects_malformed_dsl` |
| **What It Tests** | Server returns HTTP 400 for invalid DSL content |
| **Input** | `{"filename": "corrupted.src", "content": "not a valid key value pair"}` |
| **Expected** | HTTP 400; error contains `"malformed"` |
| **Result** | ✅ PASS |

---

### TC-084 · `test_upload_check_rejects_unsupported_extension`

| Field | Detail |
|---|---|
| **Function** | `test_upload_check_rejects_unsupported_extension` |
| **What It Tests** | Server returns HTTP 400 for non-.src extension |
| **Input** | `{"filename": "script.py", "content": "..."}` |
| **Expected** | HTTP 400; error contains `"unsupported file type"` |
| **Result** | ✅ PASS |

---

### TC-085 · `test_upload_check_rejects_oversized_file`

| Field | Detail |
|---|---|
| **Function** | `test_upload_check_rejects_oversized_file` |
| **What It Tests** | Server returns HTTP 400 for content over 1MB |
| **Input** | `{"filename": "huge.src", "content": "a" * (1024*1024 + 100)}` |
| **Expected** | HTTP 400; error contains `"1mb"` |
| **Result** | ✅ PASS |

---

### TC-086 · `test_simulation_service_check_uploaded_source_isolated`

| Field | Detail |
|---|---|
| **Function** | `test_simulation_service_check_uploaded_source_isolated` |
| **What It Tests** | `check_uploaded_source()` directly: initial stale/rebuild → unchanged HIT → changed MISS |
| **Input** | `isolated.src` with factor=3 → unchanged → factor=6; isolated tmp dirs |
| **Expected** | Step 1: `robust.is_stale=True`, `rebuilt=True`. Step 2: `robust.is_stale=False`, HIT. Step 3: `robust.is_stale=True`, MISS |
| **Result** | ✅ PASS |

---

## 17. test_virtual_clock.py

**Module under test:** `clock.py (VirtualClock)`  
**Purpose:** VirtualClock resolution quantization and skew offset behavior.

---

### TC-087 · `test_clock_default_resolution_and_time`

| Field | Detail |
|---|---|
| **Function** | `test_clock_default_resolution_and_time` |
| **What It Tests** | `now()` returns raw time; `quantized_now()` floors to resolution boundary |
| **Input** | `VirtualClock(current_time=1_700_000_000.5, resolution=1.0)` |
| **Expected** | `now()=1_700_000_000.5`; `quantized_now()=1_700_000_000.0` |
| **Result** | ✅ PASS |

---

### TC-088 · `test_clock_resolution_quantization`

| Field | Detail |
|---|---|
| **Function** | `test_clock_resolution_quantization` |
| **What It Tests** | Advancing within 1s window keeps `quantized_now()` unchanged; crossing the boundary increments it |
| **Input** | Start `1_700_000_000.0`, 1s resolution; +0.4s; then +0.7s more (total 1.1s) |
| **Expected** | After +0.4s: `quantized_now()=1_700_000_000.0`. After +1.1s total: `quantized_now()=1_700_000_001.0` |
| **Result** | ✅ PASS |

---

### TC-089 · `test_clock_skew_offset`

| Field | Detail |
|---|---|
| **Function** | `test_clock_skew_offset` |
| **What It Tests** | `with_skew(-50.0)` creates a clock 50s behind; both clocks' `quantized_now()` differ by 50s |
| **Input** | Build clock at `1_700_000_100.0`; run clock via `with_skew(-50.0)` |
| **Expected** | `build_clock.quantized_now()=1_700_000_100.0`; `run_clock.quantized_now()=1_700_000_050.0` |
| **Result** | ✅ PASS |

---

## 18. test_web_api.py

**Module under test:** `web/app.py`  
**Purpose:** Integration tests for all HTTP API endpoints via a live in-process test server.

---

### TC-090 · `test_api_status`

| Field | Detail |
|---|---|
| **Function** | `test_api_status` |
| **What It Tests** | `GET /api/status` returns HTTP 200 with required fields |
| **Input** | GET `/api/status` |
| **Expected** | Status 200; response has `"cache_exists"` and `"simulated_mtime"` |
| **Result** | ✅ PASS |

---

### TC-091 · `test_api_run_collision`

| Field | Detail |
|---|---|
| **Function** | `test_api_run_collision` |
| **What It Tests** | `POST /api/run/collision` returns correct naive (20) and smart (30) results |
| **Input** | `{"input_value": 10}` |
| **Expected** | Status 200; `naive_execution.result=20`; `smart_execution.result=30` |
| **Result** | ✅ PASS |

---

### TC-092 · `test_api_run_normal`

| Field | Detail |
|---|---|
| **Function** | `test_api_run_normal` |
| **What It Tests** | `POST /api/run/normal` returns result=20 |
| **Input** | `{"input_value": 10}` |
| **Expected** | Status 200; `data.result=20` |
| **Result** | ✅ PASS |

---

### TC-093 · `test_api_run_skew`

| Field | Detail |
|---|---|
| **Function** | `test_api_run_skew` |
| **What It Tests** | `POST /api/run/skew` returns result=20 |
| **Input** | `{"input_value": 10}` |
| **Expected** | Status 200; `data.result=20` |
| **Result** | ✅ PASS |

---

### TC-094 · `test_static_index_html`

| Field | Detail |
|---|---|
| **Function** | `test_static_index_html` |
| **What It Tests** | `GET /` serves the dashboard with required UI elements |
| **Input** | GET `/` |
| **Expected** | Status 200; HTML contains `"StaleByte"`, `"Timestamp-Only Strategy"`, `"chat-widget"`, `"muse-spark-1.3"` |
| **Result** | ✅ PASS |

---

### TC-095 · `test_api_chat_status`

| Field | Detail |
|---|---|
| **Function** | `test_api_chat_status` |
| **What It Tests** | `GET /api/chat/status` returns configured flag and model identifier |
| **Input** | GET `/api/chat/status` |
| **Expected** | Status 200; `"configured"` in response; `data.model="muse-spark-1.3"` |
| **Result** | ✅ PASS |

---

### TC-096 · `test_api_chat_unconfigured_streaming`

| Field | Detail |
|---|---|
| **Function** | `test_api_chat_unconfigured_streaming` |
| **What It Tests** | Without an API key, `POST /api/chat` with `stream:true` returns SSE with setup guidance and `[DONE]` |
| **Input** | All API keys removed; `{"messages": [...], "stream": true}` |
| **Expected** | Status 200; SSE contains `"META_API_KEY"` and `"[DONE]"` |
| **Result** | ✅ PASS |

---

### TC-097 · `test_api_chat_non_streaming`

| Field | Detail |
|---|---|
| **Function** | `test_api_chat_non_streaming` |
| **What It Tests** | Without an API key, `POST /api/chat` with `stream:false` returns JSON with `reply` and `model` |
| **Input** | All API keys removed; `{"messages": [...], "stream": false}` |
| **Expected** | Status 200; `"reply"` in response; `model="muse-spark-1.3"`; reply contains `"META_API_KEY"` |
| **Result** | ✅ PASS |

---

### TC-098 · `test_api_explain_endpoint`

| Field | Detail |
|---|---|
| **Function** | `test_api_explain_endpoint` |
| **What It Tests** | Both `/explain` and `/api/explain` return HTTP 200; fallback explanation contains diagnostic reason |
| **Input** | No API keys; diagnostic with reason `"Identical timestamps caused silent stale execution."` |
| **Expected** | Both routes: Status 200; `"explanation"` present; `model="muse-spark-1.3"`; `"Identical timestamps"` in explanation |
| **Result** | ✅ PASS |

---

### TC-099 · `test_static_index_html_contains_explain_elements`

| Field | Detail |
|---|---|
| **Function** | `test_static_index_html_contains_explain_elements` |
| **What It Tests** | `GET /` serves the full dashboard with all required UI element IDs present |
| **Input** | GET `/` |
| **Expected** | HTML contains: `btn-explain-naive`, `btn-explain-smart`, `naive-ai-box`, `smart-ai-box`, `"Explain this"`, `upload-check`, `upload-dropzone`, `btn-upload-check`, `source-file-input` |
| **Result** | ✅ PASS |

---

---


---

### TC-102 · 	est_send_error_has_content_length

| Field | Detail |
|---|---|
| **Function** | 	est_send_error_has_content_length |
| **What It Tests** | _send_error() sets Content-Length header matching byte length of error response |
| **Input** | GET request to non-existent route |
| **Expected** | HTTP 404; Content-Length header present and matches len(raw_body) |
| **Result** | ✅ PASS |

---

### TC-103 · 	est_api_malformed_json_body_returns_400

| Field | Detail |
|---|---|
| **Function** | 	est_api_malformed_json_body_returns_400 |
| **What It Tests** | Malformed JSON payload returns HTTP 400 with Content-Length rather than unhandled exception |
| **Input** | POST to /api/run/collision with invalid JSON string |
| **Expected** | HTTP 400; error message mentions 'malformed json' |
| **Result** | ✅ PASS |

---

### TC-104 · 	est_api_non_dict_json_body_returns_400

| Field | Detail |
|---|---|
| **Function** | 	est_api_non_dict_json_body_returns_400 |
| **What It Tests** | Valid JSON that is not an object (e.g. array [1, 2, 3]) returns HTTP 400 Bad Request |
| **Input** | POST with JSON array |
| **Expected** | HTTP 400; error message specifies request body must be a JSON object |
| **Result** | ✅ PASS |

---

### TC-105 · 	est_api_chat_invalid_messages_type

| Field | Detail |
|---|---|
| **Function** | 	est_api_chat_invalid_messages_type |
| **What It Tests** | Non-list 'messages' field in /api/chat returns HTTP 400 instead of crashing |
| **Input** | POST to /api/chat with messages: 'not a list' |
| **Expected** | HTTP 400; error message indicates messages must be a list |
| **Result** | ✅ PASS |

---

### TC-106 · 	est_startup_ai_service_check

| Field | Detail |
|---|---|
| **Function** | 	est_startup_ai_service_check |
| **What It Tests** | Startup health probe checks configuration, reachability, and model ID |
| **Input** | check_startup_ai_service() invocation |
| **Expected** | Returns dictionary containing 'configured', 'reachable', and model='muse-spark-1.3' |
| **Result** | ✅ PASS |

---

## Summary

| Metric | Value |
|---|---|
| **Total Tests** | 106 |
| **Passed** | 106 |
| **Failed** | 0 |
| **Warnings** | 0 |
| **Run Time** | 3.41 seconds |
| **Verified On** | 2026-09-05 |
| **Command** | `python -m pytest tests/ -v --tb=short` |

### Coverage by Category

| Category | Test IDs | Count |
|---|---|---|
| AI Service | TC-001 to TC-012 | 8 |
| Cache Manager | TC-013 to TC-020 | 8 |
| Cache Store | TC-021, TC-100 to TC-101 | 3 |
| CLI and Real Filesystem | TC-022 to TC-030 | 8 |
| Clock Skew | TC-031 to TC-034 | 4 |
| Statistical Fuzzing | TC-035 to TC-038 | 4 |
| SHA-256 Hash | TC-039 to TC-043 | 5 |
| Invalidators | TC-044 to TC-047 | 4 |
| Naive Checker | TC-048 to TC-052 | 5 |
| Runtime End-to-End | TC-053 to TC-056 | 4 |
| Simulation Service | TC-057 to TC-060 | 4 |
| Robust/Smart Checker | TC-061 to TC-066 | 6 |
| Source File | TC-067 to TC-068 | 2 |
| Timestamp Boundary | TC-069 to TC-078 | 10 |
| Unified Runtime | TC-079 to TC-080 | 2 |
| Upload Check | TC-081 to TC-086 | 6 |
| Virtual Clock | TC-087 to TC-089 | 3 |
| Web API | TC-090 to TC-099, TC-102 to TC-106 | 15 |
