# StaleByte — System Architecture

## 1. Executive Summary

StaleByte is a deterministic verification engine demonstrating **compiled-cache staleness caused by timestamp validation failure** and its resolution via **SHA-256 cryptographic content fingerprinting**.

Build systems traditionally rely on file modification timestamps (`mtime`) to skip unnecessary recompilation. However, when edits occur within the filesystem timestamp resolution window (e.g. 1-second FAT32/ext3 granularity, sub-second rapid rebuilds, or distributed clock skew), two distinct source versions can have identical observable timestamps. A timestamp-only validator incorrectly reuses a stale binary, resulting in silent runtime behavioral divergence.

StaleByte implements a dual-invalidation architecture to reproduce this critical vulnerability deterministically, contrast naive vs. robust strategies side by side, and provide verifiable cryptographic certainty.

---

## 2. Complete System Architecture Diagram

```mermaid
flowchart TD
    %% Styling Classes
    classDef clientStyle fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,color:#1e3a8a;
    classDef apiStyle fill:#f0fdf4,stroke:#22c55e,stroke-width:2px,color:#14532d;
    classDef svcStyle fill:#fdf4ff,stroke:#a855f7,stroke-width:2px,color:#581c87;
    classDef runtimeStyle fill:#f8fafc,stroke:#475569,stroke-width:2px,color:#0f172a;
    classDef naiveStyle fill:#fef2f2,stroke:#ef4444,stroke-width:2px,color:#991b1b;
    classDef robustStyle fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#065f46;
    classDef cacheStyle fill:#fffbeb,stroke:#f59e0b,stroke-width:2px,color:#78350f;
    classDef vmStyle fill:#f1f5f9,stroke:#64748b,stroke-width:2px,color:#1e293b;

    subgraph CLIENTS [" 1. Presentation & Client Layer "]
        WEB["🖥️ Web Dashboard (HTML5 / CSS3 / ES6)"]:::clientStyle
        CLI["💻 CLI & Pre-Commit Tools (cli.py / .pre-commit-hooks.yaml)"]:::clientStyle
        TEST["🧪 Test Suite (pytest · 131 tests)"]:::clientStyle
    end

    subgraph API [" 2. API Server & Gateway (web/app.py) "]
        ROUTER["⚡ ThreadingHTTPServer Request Handler"]:::apiStyle
        ENDPOINTS["REST Routes: /upload-check · /run/collision · /run/normal · /check · /build · /chat"]:::apiStyle
    end

    subgraph SERVICES [" 3. Orchestration & Intelligence (services/) "]
        SIM["⚙️ Simulation Service (simulation_service.py)<br/>Scenario coordinator & live file checker"]:::svcStyle
        AI["🤖 Assistant Service (ai_service.py)<br/>Meta Muse Spark 1.3 · Auto-summaries & Chat"]:::svcStyle
    end

    subgraph CORE [" 4. Deterministic Core Engine (Off-Limits) "]
        SRC["📄 SourceFile (source.py)<br/>Real os.stat() mtime & SHA-256 hash"]:::vmStyle
        RUNTIME["🔄 Unified Runtime (runtime/engine.py)<br/>check_staleness() & execute()"]:::runtimeStyle

        subgraph STRATEGIES [" Staleness Strategies (invalidators.py) "]
            NAIVE["❌ Naive Invalidator<br/>mtime > t_cache<br/>⚠️ Fails on timestamp collision"]:::naiveStyle
            ROBUST["🛡️ Robust Invalidator<br/>hash != cached_hash OR mtime > t_cache<br/>✅ Cryptographic certainty"]:::robustStyle
        end

        VM["⚙️ Stack Bytecode VM (lib/compiler.py)<br/>LOAD_INPUT · PUSH · MUL · RETURN (zero eval/exec)"]:::vmStyle
    end

    subgraph STORAGE [" 5. Thread-Safe Storage (cache.py) "]
        CACHE["💾 Atomic CacheStore<br/>threading.Lock · metadata.json & artifact.json"]:::cacheStyle
    end

    %% Connections
    WEB --> ROUTER
    CLI --> SIM
    TEST --> ROUTER
    TEST --> SIM

    ROUTER --> ENDPOINTS
    ENDPOINTS --> SIM
    ENDPOINTS --> AI

    SIM --> RUNTIME
    SIM --> SRC
    SIM -.->|Passes Finished Results| AI

    RUNTIME --> NAIVE
    RUNTIME --> ROBUST
    RUNTIME --> VM
    RUNTIME --> CACHE

    SRC -.->|Supplies Current Metadata| RUNTIME
    CACHE -.->|Supplies Cached Envelope| RUNTIME
```

---

## 3. Naive vs. Robust Decision Flow

```mermaid
flowchart TD
    classDef danger fill:#fef2f2,stroke:#ef4444,stroke-width:2px,color:#991b1b;
    classDef success fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#065f46;
    classDef neutral fill:#f8fafc,stroke:#64748b,stroke-width:2px,color:#0f172a;
    classDef decision fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,color:#1e3a8a;

    START["📝 Source File Edited (V1 -> V2)<br/>Occurs within same 1-second timestamp window"]:::neutral

    START --> COND{"Filesystem Check<br/>mtime = T_cache?"}:::decision

    %% Naive Branch
    COND -->|Yes: Timestamp Unchanged| NAIVE_PATH["❌ Naive Strategy (Clock-Only)"]:::danger
    NAIVE_PATH --> N_DEC["mtime <= T_cache: Declares Cache VALID"]:::danger
    N_DEC --> N_EXEC["Reuses Outdated V1 Bytecode (factor=2)"]:::danger
    N_EXEC --> N_OUT["❌ Output = 20<br/>CRITICAL BUG: Silent Stale Execution!"]:::danger

    %% Robust Branch
    COND -->|Compare SHA-256 Hashes| ROBUST_PATH["🛡️ Robust Strategy (StaleByte)"]:::success
    ROBUST_PATH --> R_DEC["Hash(V2) != Hash(V1): Declares Cache STALE"]:::success
    R_DEC --> R_REBUILD["Invalidates Cache & Recompiles V2 (factor=3)"]:::success
    R_REBUILD --> R_OUT["✅ Output = 30<br/>VERIFIED PASS: Correct Execution!"]:::success
```

---

## 4. Component Deep Dive

### 4.1 Presentation Layer (`web/static/`)
- **Dashboard Interface**: Single-page application built with clean semantic HTML5, custom design system CSS (responsive, glassmorphism accents, accessible contrast ratios), and vanilla ES6 JavaScript.
- **Simulation Suite**: One-click triggers for:
  - Timestamp Collision scenario (identical filesystem mtime, diverging content)
  - Normal Flow scenario (unchanged source, legitimate cache hit)
  - Distributed Clock Skew scenario (backward clock skew simulating unsynchronized cluster nodes)
- **Real File Upload Dropzone**: Drag-and-drop file inspection executing real `os.stat` filesystem calls and live SHA-256 generation.
- **Assistant Widget**: Non-intrusive floating drawer offering natural language explanations without technical jargon.

### 4.2 Application & Service Layer (`web/app.py`, `services/`)
- **API Server (`web/app.py`)**: High-performance HTTP server using Python's standard library `ThreadingHTTPServer`. Enforces strict request body validation (1MB upload limit, RFC-compliant Content-Length on error responses).
- **Simulation Service (`services/simulation_service.py`)**: Pure orchestration layer isolating business logic from network handlers. Supplies structured diagnostic payloads with verdicts, timestamps, hashes, and decisions.
- **AI Intelligence Service (`services/ai_service.py`)**:
  - Encapsulated Meta Muse Spark 1.3 LLM client over standard OpenAI-compatible completions protocol.
  - **Quota Isolation**: Independent `MUSE_SPARK_API_KEY` (interactive chat) and `SUMMARY_API_KEY` (automatic core output summaries).
  - **Graceful Fault Tolerance**: Background summary failures or missing keys safely fall back to `null` with HTTP 200, guaranteeing deterministic core execution never halts.
  - **Plain-Language Tone**: Strict system prompt constraints forbidding raw math operators (`<=`, raw bytecode) for business and non-technical clarity.

### 4.3 Deterministic Core Layer (`invalidators.py`, `source.py`, `cache.py`, `runtime/`, `lib/`)
- **Source Model (`source.py`)**: Encapsulates disk-backed and in-memory source files. Calculates SHA-256 digests deterministically. Supports `VirtualClock` for discrete time resolution quantization.
- **Cache Store (`cache.py`)**: Thread-safe cache persistence using `threading.Lock` and atomic file write replacements (`_atomic_write_text` via temp files).
- **Pluggable Invalidators (`invalidators.py`)**: Polymorphic validator interface implementing `check(source, cache_entry) -> InvalidationDecision`.
- **Compiler & Bytecode VM (`lib/compiler.py`)**: Safe stack machine supporting arithmetic transformations without dynamic interpreters (`eval`, `exec`).

### 4.4 CLI & Pre-Commit Integration (`cli.py`, `.pre-commit-hooks.yaml`)
- **CLI Subcommands**: `stalebyte check <path>`, `build`, `demo`, `fuzz`, and `clean`.
- **Recursive Directory Inspection**: `stalebyte check <directory>` walks all `.src` files recursively, skipping hidden and cache directories. Returns exit code `0` on clean state or unbuilt initial baseline, and exit code `1` if any file is genuinely stale.
- **Pre-Commit Hook**: Integrates via `.pre-commit-hooks.yaml` (`id: stalebyte-check`, `entry: stalebyte check .`), preventing commits of modified source files without updated cache baselines.

---

## 5. Security & Reliability Model

- **Safe Execution**: Stack VM operations (`LOAD_INPUT`, `PUSH`, `MUL`, `RETURN`) prevent code injection.
- **Atomic Concurrency**: Thread-safe write locks prevent corrupted cache files during concurrent build requests.
- **Air-Gapped Core Determinism**: All staleness decisions (`is_stale`, `rebuilt`, `output`) are 100% deterministic and computed locally before optional AI presentation layers are invoked.
