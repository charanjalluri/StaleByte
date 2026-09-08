# CLAUDE.md — StaleByte Engineering Guidelines

Engineering principles and project rules for AI coding assistants and developers working on the StaleByte repository.
Incorporates Andrej Karpathy engineering principles adapted specifically for the StaleByte systems laboratory.

---

## 1. Core Engineering Principles (Karpathy Guidelines)

### 1.1 Think Before Coding
* **Inspect first**: Inspect all relevant files and understand the execution flow before writing or modifying any code.
* **Understand tests**: Inspect existing tests to understand the intended invariants and failure modes.
* **Surface assumptions**: State assumptions explicitly. If uncertain or if multiple interpretations exist, ask rather than guessing silently.
* **Identify root cause**: Distinguish between symptoms and the actual problem. Determine the smallest correct solution.
* **Push back when warranted**: If a simpler approach exists or a proposed feature introduces unnecessary complexity, say so. Do not immediately start editing.

### 1.2 Simplicity First
* **Prefer**:
  - Straightforward, idiomatic Python.
  - Explicit control flow and readable logic over clever abstractions.
  - Small, focused functions and simple standard-library data structures (`dict`, `tuple`, `dataclass`).
  - Minimal external dependencies (standard library preferred; zero unnecessary dependencies).
* **Avoid**:
  - Unnecessary abstractions, wrapper classes, or speculative design patterns.
  - Framework additions without explicit justification.
  - Premature optimization or configurability for scenarios that do not exist.
  - If 50 lines solves a problem cleanly, never write 200 lines.

### 1.3 Surgical Changes
* **Touch only what is necessary**: Modify only the relevant area required to solve the task.
* **Preserve existing behavior**: Do not break working production code or rewrite things simply out of stylistic preference.
* **Avoid drive-by refactoring**:
  - Do not "improve" adjacent code, comments, or formatting unless directly requested.
  - Do not perform mass renames or cosmetic churn.
* **Clean up only your own orphans**: Remove unused imports, variables, or helpers created by your changes; do not purge pre-existing unrelated code without authorization.
* **Clear rationale**: Every modified line must trace directly to the stated goal.

### 1.4 Goal-Driven Execution
* **Optimize for**: Correctness, Security, Simplicity, Maintainability, Testability, and Reliability.
* **Do NOT optimize for**: Number of changed files, lines of code, number of abstractions, or architectural complexity.
* **Define success criteria**: Transform every task into concrete, verifiable outcomes (e.g. "Write reproducing test → make it pass → verify full test suite").
* **Verify iteratively**: State a plan, execute, and verify each step against real runtime behavior.

---

## 2. StaleByte Domain & PDR Invariants

StaleByte is a deterministic systems laboratory demonstrating how timestamp-only build cache validation fails and how cryptographic SHA-256 content-addressing guarantees correctness.

Future coding sessions **MUST** preserve this foundational lifecycle:
1. **Source V1** compiled into controlled artifact.
2. **Artifact cached** alongside metadata (`cached_mtime`, `content_hash`).
3. **Source updated to V2** (content changes from `factor=2` to `factor=3`).
4. **Timestamp collision / clock skew simulated**:
   - Resolution collision: Coarse filesystem `mtime` (e.g. 1.0s window) makes `source.mtime == t_cache`.
   - Clock skew: Build machine ahead of run machine makes `source.mtime < t_cache`.
5. **Naive Validator fooled**: Evaluates `source.mtime <= t_cache`, reports `is_stale=False` (False Cache Hit).
6. **Naive Runtime bug**: Reuses stale V1 artifact, producing output `20` (Silent Runtime Mismatch Bug).
7. **Smart Validator (Robust)**: Computes SHA-256 from current source bytes, detects hash mismatch (`1055b92b... != 45e28b09...`), reports `is_stale=True` (Cache Miss).
8. **Smart Runtime correction**: Evicts stale cache entry, recompiles V2 source, updates cache metadata, and executes rebuilt artifact producing output `30` (Correct V2 output).

---

## 3. Security & Controlled Execution Model

Arbitrary Python code execution is strictly prohibited. StaleByte's security model must remain intact:
* **Zero `eval()` / Zero `exec()`**: Source files are never dynamically evaluated as Python scripts.
* **No `os.system()` or `subprocess(..., shell=True)`**: Do not introduce shell execution or external subprocess invocations.
* **No unsafe deserialization**: Do not use `pickle` or uncontrolled object unpickling; persist cache data strictly as standard JSON.
* **No unsafe dynamic imports**: Do not load arbitrary modules dynamically.
* **Sandboxed Bytecode VM**: The controlled domain-specific language (DSL: `operation=multiply\nfactor=<int>`) parses strictly to stack bytecode instructions (`LOAD_INPUT`, `PUSH <val>`, `MUL`, `RETURN`) interpreted by the in-memory stack VM.
* **Strict parameter validation**: Factors must be validated as positive integers (`factor > 0`). Reject negative numbers, floats, non-integers, duplicate keys, and syntax injections.
* **Safe Cache Persistence**: `CacheStore` enforces path traversal defense, rejects OS-critical paths (`/etc`, `/bin`, `C:\Windows`), and performs atomic file writes (`.tmp` + `os.replace`).

---

## 4. Cache Integrity Rules

* **Cryptographic SHA-256 Ground Truth**: Hash validation must always compute SHA-256 from actual source content bytes.
* **Never substitute**:
  - Never replace content validation with filename validation or file size alone.
  - Never use timestamp-only validation for cache safety.
  - Never use hardcoded or mocked hashes in production validators.
* **Deterministic simulation**: Timestamp collision and clock skew scenarios must remain deterministic (using `VirtualClock` or isolated test environments). Never manipulate the host operating system clock.

---

## 5. Testing Discipline

* **Test before and after**:
  - Run the test suite before making meaningful changes to establish a baseline.
  - Run relevant tests during development and the full test suite after completing changes.
* **Comprehensive test suite**:
  - Full suite command: `python -m pytest tests/ -q`
  - Focused PDR command: `python -m pytest tests/test_runtime_end_to_end.py tests/test_timestamp_window.py tests/test_smart_checker.py tests/test_invalidators.py tests/test_cli_and_real_fs.py -q`
* **Zero test weakening**:
  - Never weaken test assertions to force a passing build.
  - Never delete failing tests without understanding and addressing the underlying failure.
  - Prefer real end-to-end behavior tests over mocks for all core PDR scenarios (e.g. testing real arithmetic output `20` vs `30` and real disk `os.utime()` collisions).

---

## 6. Presentation & Demo Invariants

* **Deterministic Demo**:
  - Command: `python demo.py`
  - Reset command: `python demo.py --reset`
* **Presentation requirements**:
  - Scenario 1 must clearly display the 12-step lifecycle from V1 compile to V2 recompiled output.
  - Scenario 2 must display the parameters and decisions under clock skew.
  - The live side-by-side comparison matrix must be computed from actual runtime objects (`ExecutionResult`, `InvalidationDecision`), never hardcoded strings.
  - `python demo.py --reset` must safely clear only temporary cache JSON files in `cache/` and `cache/uploads/`, strictly preserving `.gitkeep`, source files, tests, and Git history.

---

## 7. Documentation Standards

* **Technical honesty**: Keep all claims in `README.md` and documentation technically accurate and backed by passing tests.
* **Scope boundaries**: Do not claim StaleByte is a universal production compiler or complete build-system replacement. It is an educational, deterministic systems laboratory and standalone content-addressable cache primitive.
