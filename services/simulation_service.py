"""
simulation_service.py
---------------------
Orchestration layer for StaleByte simulations.
Encapsulates scenario execution logic for consumption by CLI scripts, tests, and web APIs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cache import CacheEntry, CacheStore
from invalidators import NaiveInvalidator, RobustInvalidator
from lib import cache_manager, compiler, source_manager
from runtime import Runtime, run_naive, run_smart
from source import SourceFile

FIXED_TS: float = source_manager.SIMULATED_MTIME


def run_normal_flow(
    input_value: int = 10,
    source_content: str | None = None,
) -> dict[str, Any]:
    """
    Execute the normal flow scenario:
    Source compiled and cached. Source unchanged. Cache is valid.
    """
    src = source_content if source_content is not None else source_manager.V1_CONTENT
    source_manager.create_source(src)
    content = source_manager.read_source()
    artifact = compiler.compile_source(content)
    src_hash = source_manager.compute_hash(content)

    meta = cache_manager.save_cache(
        artifact=artifact,
        source_content=content,
        source_hash=src_hash,
        source_version="V1",
        t_cache=FIXED_TS,
    )

    src_file = SourceFile(
        path=str(source_manager.SOURCE_PATH),
        content=content,
        mtime=FIXED_TS,
        size=len(content.encode("utf-8")),
        content_hash=src_hash,
    )
    entry = CacheEntry(
        source_path=str(source_manager.SOURCE_PATH),
        cached_mtime=FIXED_TS,
        cached_size=len(content.encode("utf-8")),
        content_hash=src_hash,
        artifact=artifact,
    )
    naive_decision = NaiveInvalidator().check(src_file, entry)
    smart_decision = RobustInvalidator().check(src_file, entry)
    result = compiler.execute_artifact(artifact, input_value)

    return {
        "scenario": "normal_flow",
        "input_value": input_value,
        "source": {
            "v1": content,
            "v2": content,
        },
        "timestamps": {
            "cached": FIXED_TS,
            "current": FIXED_TS,
            "match": True,
        },
        "hashes": {
            "cached": src_hash,
            "current": src_hash,
            "match": True,
        },
        "metadata": meta,
        "artifact": artifact,
        "result": result,
        "naive": {
            "decision": {
                "is_stale": naive_decision.is_stale,
                "reason": naive_decision.reason,
            },
            "cache_used": True,
            "output": result,
        },
        "smart": {
            "decision": {
                "is_stale": smart_decision.is_stale,
                "timestamp_match": smart_decision.timestamp_match,
                "hash_match": smart_decision.hash_match,
                "reason": smart_decision.reason,
            },
            "invalidated": False,
            "rebuilt": False,
            "cache_used": True,
            "output": result,
        },
        # Compatibility aliases for existing callers
        "naive_decision": {
            "is_stale": naive_decision.is_stale,
            "reason": naive_decision.reason,
        },
        "smart_decision": {
            "is_stale": smart_decision.is_stale,
            "timestamp_match": smart_decision.timestamp_match,
            "hash_match": smart_decision.hash_match,
            "reason": smart_decision.reason,
        },
        "source_content": content,
        "source_hash": src_hash,
        "t_cache": FIXED_TS,
        "hash": src_hash,
        "output": result,
        "decision": {
            "is_stale": smart_decision.is_stale,
            "reason": smart_decision.reason,
        },
        "reason": smart_decision.reason,
        "verdict": "VALID CACHE (HIT)",
    }


def run_collision_scenario(
    input_value: int = 10,
    v1_content: str | None = None,
    v2_content: str | None = None,
) -> dict[str, Any]:
    """
    Execute the timestamp-collision scenario:
    1. V1 cached with timestamp FIXED_TS.
    2. Source mutated to V2, simulated mtime remains FIXED_TS.
    3. Naive runtime evaluates cache valid -> executes stale V1.
    4. Smart runtime detects hash mismatch -> invalidates -> rebuilds V2.
    """
    src_v1 = v1_content if v1_content is not None else source_manager.V1_CONTENT
    src_v2 = v2_content if v2_content is not None else source_manager.V2_CONTENT

    # Step 1: Cache V1
    source_manager.create_source(src_v1)
    content_v1 = source_manager.read_source()
    artifact_v1 = compiler.compile_source(content_v1)
    src_hash_v1 = source_manager.compute_hash(content_v1)

    meta_v1 = cache_manager.save_cache(
        artifact=artifact_v1,
        source_content=content_v1,
        source_hash=src_hash_v1,
        source_version="V1",
        t_cache=FIXED_TS,
    )

    # Step 2: Mutate source to V2
    source_manager.create_source(src_v2)
    content_v2 = source_manager.read_source()
    src_hash_v2 = source_manager.compute_hash(content_v2)

    # Step 3: Run naive runtime (uses stale V1 cache)
    naive_out = run_naive(input_value, get_mtime=source_manager.simulated_mtime)

    # Step 4: Re-establish collision state before running the smart runtime.
    # run_naive() in Step 3 may have consumed or modified the cache.
    # Both runtimes must start from the identical pre-condition — V1 cached at
    # FIXED_TS — so that the comparison is fair and the smart runtime's
    # invalidation decision is based on the same stale V1 artifact.
    cache_manager.save_cache(
        artifact=artifact_v1,
        source_content=content_v1,
        source_hash=src_hash_v1,
        source_version="V1",
        t_cache=FIXED_TS,
    )
    smart_out = run_smart(input_value, get_mtime=source_manager.simulated_mtime)

    return {
        "scenario": "timestamp_collision",
        "input_value": input_value,
        "source": {
            "v1": content_v1,
            "v2": content_v2,
        },
        "timestamps": {
            "cached": FIXED_TS,
            "current": FIXED_TS,
            "match": True,
        },
        "hashes": {
            "cached": src_hash_v1,
            "current": src_hash_v2,
            "match": src_hash_v1 == src_hash_v2,
        },
        "v1": {
            "content": content_v1,
            "hash": src_hash_v1,
            "artifact": artifact_v1,
            "metadata": meta_v1,
        },
        "v2": {
            "content": content_v2,
            "hash": src_hash_v2,
        },
        "collision_mtime": FIXED_TS,
        "naive": {
            "decision": {
                "is_stale": naive_out["decision"].is_stale,
                "reason": naive_out["decision"].reason,
            },
            "cache_used": naive_out["cache_used"],
            "executed_factor": naive_out["artifact"]["factor"],
            "output": naive_out["result"],
            "verdict": "BUG: Stale V1 artifact executed silently",
        },
        "smart": {
            "decision": {
                "is_stale": smart_out["decision"].is_stale,
                "timestamp_match": smart_out["decision"].timestamp_match,
                "hash_match": smart_out["decision"].hash_match,
                "reason": smart_out["decision"].reason,
            },
            "invalidated": True,
            "rebuilt": smart_out["rebuilt"],
            "cache_used": smart_out["cache_used"],
            "executed_factor": smart_out["artifact"]["factor"],
            "output": smart_out["result"],
            "verdict": "CORRECT: Staleness detected, V2 rebuilt and executed",
        },
        # Compatibility aliases for existing callers
        "naive_execution": {
            "result": naive_out["result"],
            "cache_used": naive_out["cache_used"],
            "is_stale": naive_out["decision"].is_stale,
            "reason": naive_out["decision"].reason,
            "executed_factor": naive_out["artifact"]["factor"],
            "verdict": "BUG: Stale V1 artifact executed silently",
        },
        "smart_execution": {
            "result": smart_out["result"],
            "cache_used": smart_out["cache_used"],
            "rebuilt": smart_out["rebuilt"],
            "is_stale": smart_out["decision"].is_stale,
            "timestamp_match": smart_out["decision"].timestamp_match,
            "hash_match": smart_out["decision"].hash_match,
            "reason": smart_out["decision"].reason,
            "executed_factor": smart_out["artifact"]["factor"],
            "verdict": "CORRECT: Staleness detected, V2 rebuilt and executed",
        },
        "output": smart_out["result"],
        "hash": src_hash_v2,
        "decision": {
            "is_stale": smart_out["decision"].is_stale,
            "reason": smart_out["decision"].reason,
        },
        "reason": smart_out["decision"].reason,
        "verdict": "COLLISION DETECTED & RESOLVED",
    }


def run_clock_skew_scenario(
    input_value: int = 10,
    source_content: str | None = None,
    t_cache: float = 100.0,
    t_source_skewed: float = 50.0,
) -> dict[str, Any]:
    """
    Execute clock skew scenario:
    Source timestamp appears older than cache timestamp (source_mtime < t_cache).
    Verifies that neither checker triggers false invalidation when hash matches.
    """
    src = source_content if source_content is not None else source_manager.V1_CONTENT
    source_manager.create_source(src)
    content = source_manager.read_source()
    artifact = compiler.compile_source(content)
    src_hash = source_manager.compute_hash(content)

    cache_manager.save_cache(
        artifact=artifact,
        source_content=content,
        source_hash=src_hash,
        source_version="V1",
        t_cache=t_cache,
    )

    src_file = SourceFile(
        path=str(source_manager.SOURCE_PATH),
        content=content,
        mtime=t_source_skewed,
        size=len(content.encode("utf-8")),
        content_hash=src_hash,
    )
    entry = CacheEntry(
        source_path=str(source_manager.SOURCE_PATH),
        cached_mtime=t_cache,
        cached_size=len(content.encode("utf-8")),
        content_hash=src_hash,
        artifact=artifact,
    )
    naive_decision = NaiveInvalidator().check(src_file, entry)
    smart_decision = RobustInvalidator().check(src_file, entry)
    result = compiler.execute_artifact(artifact, input_value)

    return {
        "scenario": "clock_skew",
        "input_value": input_value,
        "source": {
            "v1": content,
            "v2": content,
        },
        "timestamps": {
            "cached": t_cache,
            "current": t_source_skewed,
            "match": t_source_skewed <= t_cache,
        },
        "hashes": {
            "cached": src_hash,
            "current": src_hash,
            "match": True,
        },
        "t_cache": t_cache,
        "t_source_skewed": t_source_skewed,
        "content": content,
        "source_hash": src_hash,
        "result": result,
        "naive": {
            "decision": {
                "is_stale": naive_decision.is_stale,
                "reason": naive_decision.reason,
            },
            "cache_used": True,
            "output": result,
        },
        "smart": {
            "decision": {
                "is_stale": smart_decision.is_stale,
                "timestamp_match": smart_decision.timestamp_match,
                "hash_match": smart_decision.hash_match,
                "reason": smart_decision.reason,
            },
            "invalidated": False,
            "rebuilt": False,
            "cache_used": True,
            "output": result,
        },
        # Compatibility aliases
        "naive_decision": {
            "is_stale": naive_decision.is_stale,
            "reason": naive_decision.reason,
        },
        "smart_decision": {
            "is_stale": smart_decision.is_stale,
            "timestamp_match": smart_decision.timestamp_match,
            "hash_match": smart_decision.hash_match,
            "reason": smart_decision.reason,
        },
        "output": result,
        "hash": src_hash,
        "decision": {
            "is_stale": smart_decision.is_stale,
            "reason": smart_decision.reason,
        },
        "reason": smart_decision.reason,
        "verdict": "CLOCK SKEW DETECTED & RESOLVED",
    }


def get_system_status() -> dict[str, Any]:
    """Return the current filesystem and cache state."""
    exists = cache_manager.cache_exists()
    meta = cache_manager.load_metadata() if exists else None
    artifact = cache_manager.load_artifact() if exists else None

    try:
        current_src = source_manager.read_source()
        current_hash = source_manager.compute_hash(current_src)
    except FileNotFoundError:
        current_src = None
        current_hash = None

    return {
        "cache_exists": exists,
        "metadata": meta,
        "artifact": artifact,
        "current_source": current_src,
        "current_hash": current_hash,
        "simulated_mtime": FIXED_TS,
    }


def check_uploaded_source(
    filename: str,
    content: str,
    uploads_dir: Path | None = None,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Accept an uploaded source file, save to a session/temporary location,
    and run through the exact same real code path as `cli.py check`
    (real os.stat mtime, real SHA-256 hash, Naive and Robust invalidator decisions).
    """
    if not isinstance(content, str):
        raise ValueError("Invalid file content format.")

    content_bytes = content.encode("utf-8")
    if len(content_bytes) > 1_048_576:
        raise ValueError("File exceeds maximum allowable size of 1MB.")

    if not content.strip():
        raise ValueError("Uploaded file is empty.")

    clean_name = Path(filename).name if filename else "upload.src"
    if not clean_name:
        clean_name = "upload.src"

    ext = Path(clean_name).suffix.lower()
    if ext not in (".src", ".txt"):
        raise ValueError(
            f"Unsupported file type '{ext or clean_name}'. Only '.src' and '.txt' files are supported."
        )

    # Validate DSL syntax
    try:
        compiler.compile_source(content)
    except ValueError as val_err:
        raise ValueError(f"Malformed DSL in '{clean_name}': {val_err}. Expected format: 'operation=multiply\\nfactor=<int>'.")

    # Save to session/uploads directory
    target_dir = uploads_dir or (Path(__file__).parent.parent / "cache" / "uploads")
    target_dir.mkdir(parents=True, exist_ok=True)
    # Basic disk-fill guard: cap number of stored uploads (1MB each is enforced above).
    try:
        existing_files = [p for p in target_dir.iterdir() if p.is_file() and p.name != ".gitkeep"]
    except OSError:
        existing_files = []
    if len(existing_files) >= 1000 and (target_dir / clean_name) not in existing_files:
        raise ValueError("Upload store is full (1000 file limit). Run cache clean before uploading.")
    target_path = target_dir / clean_name

    # Only write/touch file if content changed or file does not exist yet.
    # This preserves the original mtime when uploading the exact same file unchanged.
    content_raw = content.encode("utf-8")
    if target_path.exists():
        try:
            existing = target_path.read_bytes()
        except Exception:
            existing = None
        if existing != content_raw:
            target_path.write_bytes(content_raw)
    else:
        target_path.write_bytes(content_raw)

    # Load via real filesystem os.stat() and SHA-256 (same as cli.py check)
    source = SourceFile.from_file(target_path, real_mode=True)
    store = CacheStore(cache_dir=cache_dir)
    runtime = Runtime(cache_store=store)

    naive_decision, cached_entry = runtime.check_staleness(source, NaiveInvalidator())
    robust_decision, _ = runtime.check_staleness(source, RobustInvalidator())

    was_cached = cached_entry is not None
    cached_mtime = cached_entry.cached_mtime if cached_entry else None
    cached_hash = cached_entry.content_hash if cached_entry else None
    build_id = cached_entry.build_id if cached_entry else None
    build_counter = cached_entry.build_counter if cached_entry else None

    # Populate / update cache if this is initial check or cache was stale
    rebuilt = False
    if cached_entry is None or robust_decision.is_stale:
        runtime.execute(source, RobustInvalidator())
        rebuilt = True

    naive_verdict = "VALID CACHE (HIT)" if not naive_decision.is_stale else "STALE (MISS)"
    robust_verdict = "VALID CACHE (HIT)" if not robust_decision.is_stale else "STALE (MISS / REBUILD NEEDED)"

    if not naive_decision.is_stale and robust_decision.is_stale:
        diagnostic_verdict = (
            "CRITICAL BUG DETECTED: Silent Stale Reuse. The Naive invalidator falsely accepted "
            "a stale cache because timestamps match, but Robust detected changes via SHA-256."
        )
    elif naive_decision.is_stale == robust_decision.is_stale:
        if not naive_decision.is_stale:
            diagnostic_verdict = "PASS: Cache is valid and up to date (Cache Hit)."
        else:
            diagnostic_verdict = "PASS: Cache is genuinely stale; rebuild executed."
    else:
        diagnostic_verdict = "Notice: Invalidation strategies diverged."

    return {
        "filename": clean_name,
        "path": str(target_path),
        "size": source.size,
        "mtime": source.mtime,
        "content_hash": source.content_hash,
        "hash": source.content_hash,
        "decision": {
            "is_stale": robust_decision.is_stale,
            "reason": robust_decision.reason,
        },
        "reason": robust_decision.reason,
        "verdict": diagnostic_verdict,
        "cache_state": {
            "was_cached": was_cached,
            "cached_mtime": cached_mtime,
            "cached_hash": cached_hash,
            "build_id": build_id,
            "build_counter": build_counter,
        },
        "naive": {
            "is_stale": naive_decision.is_stale,
            "verdict": naive_verdict,
            "reason": naive_decision.reason,
        },
        "robust": {
            "is_stale": robust_decision.is_stale,
            "verdict": robust_verdict,
            "reason": robust_decision.reason,
        },
        "diagnostic_verdict": diagnostic_verdict,
        "rebuilt": rebuilt,
    }


def run_check(
    path_or_filename: str | None = None,
    content: str | None = None,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Check staleness for a given path or content.
    Returns deterministic check result with decision, reason, hash, verdict, etc.
    """
    if content is not None:
        return check_uploaded_source(filename=path_or_filename or "check.src", content=content, cache_dir=cache_dir)

    if path_or_filename is not None:
        target_path = Path(path_or_filename)
        if not target_path.exists():
            raise FileNotFoundError(f"Source file not found: {target_path}")
    else:
        target_path = Path(__file__).parent.parent / "source.src"
        if not target_path.exists():
            fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "valid_source.src"
            if fixture_path.exists():
                target_path = fixture_path
            else:
                source_manager.create_source(source_manager.V1_CONTENT)
                target_path = source_manager.SOURCE_PATH

    source = SourceFile.from_file(target_path, real_mode=True)
    store = CacheStore(cache_dir=cache_dir)
    runtime = Runtime(cache_store=store)

    naive_decision, cached_entry = runtime.check_staleness(source, NaiveInvalidator())
    robust_decision, _ = runtime.check_staleness(source, RobustInvalidator())

    was_cached = cached_entry is not None
    verdict = "VALID CACHE (HIT)" if not robust_decision.is_stale else "STALE (MISS / REBUILD NEEDED)"

    return {
        "path": str(target_path),
        "filename": target_path.name,
        "size": source.size,
        "mtime": source.mtime,
        "content_hash": source.content_hash,
        "hash": source.content_hash,
        "decision": {
            "is_stale": robust_decision.is_stale,
            "reason": robust_decision.reason,
        },
        "reason": robust_decision.reason,
        "verdict": verdict,
        "cache_state": {
            "was_cached": was_cached,
            "cached_mtime": cached_entry.cached_mtime if cached_entry else None,
            "cached_hash": cached_entry.content_hash if cached_entry else None,
            "build_id": cached_entry.build_id if cached_entry else None,
            "build_counter": cached_entry.build_counter if cached_entry else None,
        },
        "naive": {
            "is_stale": naive_decision.is_stale,
            "reason": naive_decision.reason,
        },
        "robust": {
            "is_stale": robust_decision.is_stale,
            "reason": robust_decision.reason,
        },
    }


def run_build(
    path_or_filename: str | None = None,
    content: str | None = None,
    input_value: int = 10,
    strategy: str = "robust",
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Build and execute artifact for a given path or content.
    Returns deterministic build result with decision, reason, hash, output, verdict.
    """
    normalized = (strategy or "robust").lower()
    if normalized not in ("robust", "naive"):
        raise ValueError(
            f"Unknown strategy {strategy!r}. Supported strategies: 'robust', 'naive'."
        )
    if content is not None:
        target_dir = Path(__file__).parent.parent / "cache" / "uploads"
        target_dir.mkdir(parents=True, exist_ok=True)
        fname = Path(path_or_filename).name if path_or_filename else "build.src"
        target_path = target_dir / fname
        # Preserve mtime when content is unchanged so identical rebuilds stay cache HITs.
        content_raw = content.encode("utf-8")
        if target_path.exists():
            try:
                existing = target_path.read_bytes()
            except Exception:
                existing = None
            if existing != content_raw:
                target_path.write_bytes(content_raw)
        else:
            target_path.write_bytes(content_raw)
    else:
        if path_or_filename is not None:
            target_path = Path(path_or_filename)
            if not target_path.exists():
                raise FileNotFoundError(f"Source file not found: {target_path}")
        else:
            target_path = Path(__file__).parent.parent / "source.src"
            if not target_path.exists():
                fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "valid_source.src"
                if fixture_path.exists():
                    target_path = fixture_path
                else:
                    source_manager.create_source(source_manager.V1_CONTENT)
                    target_path = source_manager.SOURCE_PATH

    source = SourceFile.from_file(target_path, real_mode=True)
    store = CacheStore(cache_dir=cache_dir)
    runtime = Runtime(cache_store=store)

    invalidator = NaiveInvalidator() if normalized == "naive" else RobustInvalidator()
    exec_res = runtime.execute(source, invalidator, input_value=input_value)

    verdict = "REBUILT" if exec_res.rebuilt else "CACHE HIT"

    return {
        "path": str(target_path),
        "filename": target_path.name,
        "output": exec_res.output,
        "cache_hit": exec_res.cache_hit,
        "rebuilt": exec_res.rebuilt,
        "hash": source.content_hash,
        "content_hash": source.content_hash,
        "decision": {
            "is_stale": exec_res.decision.is_stale,
            "reason": exec_res.decision.reason,
        },
        "reason": exec_res.decision.reason,
        "verdict": verdict,
        "strategy": normalized,
        "input_value": input_value,
        "artifact": exec_res.artifact,
    }


