# StaleByte — AI Engineering & Verification Workflow

## 1. Philosophy

In the StaleByte engineering lifecycle, AI assistance is treated as a **hypothesis generator**, never as automatically trusted authoritative output. Every architecture decision, library implementation, and test suite was subjected to rigorous verification against explicit requirements.

```
       AI-Assisted Architecture & Code Generation
                           |
                           v
          Manual Inspection & Code Structure Review
                           |
                           v
        Requirement Checklist & Boundary Analysis
                           |
                           v
        Deterministic Test Scaffolding & Pytest Run
                           |
                           v
              Gap Analysis & Targeted Fixes
                           |
                           v
        Full Test Suite Pass (42/42 Tests, 0 Mocks)
```

---

## 2. Iteration History & Concrete Corrections

During the Phase 1–3 development and verification cycles, multiple specific corrections were made to AI-scaffolded code:

### 2.1 End-to-End Runtime Test Coverage
- **Discovery**: Early test modules (`test_naive_checker.py`, `test_smart_checker.py`) tested isolated function returns but lacked full runtime invocation verifying that `runtime_naive.run()` returned `20` and `runtime_smart.run()` returned `30` on actual files.
- **Fix**: Authored `tests/test_runtime_end_to_end.py` with isolated `tmp_path` fixtures executing complete file-driven runtime cycles for both checkers.

### 2.2 Unused Imports & Dead Artifacts
- **Discovery**: Code inspection in `lib/compiler.py` discovered residual imports (`import json`, `from pathlib import Path`) and an unnecessary format string literal `f"LOAD_INPUT"`.
- **Fix**: Removed unused imports and simplified static token emission.

### 2.3 Diagnostic String Precision in Decision Dataclasses
- **Discovery**: In `lib/staleness_smart.py`, the initial decision string reported every hash mismatch as a "Timestamp collision", even when the source timestamp was strictly older than `t_cache` (simulated clock skew).
- **Fix**: Separated diagnostic messages to distinguish true timestamp collision (`source_mtime == t_cache`) from content modification under clock skew (`source_mtime < t_cache`).

---

## 3. Verification Standards

1. **No Timing Flakiness**: Time is simulated using fixed timestamps (`SIMULATED_MTIME`) rather than `time.sleep()`, ensuring rapid, deterministic testing in CI/CD.
2. **Zero Mocks on Business Logic**: Real cryptographic SHA-256 digests and file serialization are executed on ephemeral temporary directories (`tmp_path`).
3. **Traceability**: All 12 critical requirements map directly to verified unit, integration, and E2E tests in the test evidence matrix.
