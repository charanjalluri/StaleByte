"""
runtime_smart.py
----------------
StaleByte smart runtime: uses both timestamp and SHA-256 hash to detect
staleness.  It correctly rebuilds from V2 even when timestamps collide.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib import cache_manager, compiler, source_manager, staleness_smart


def run(
    input_value: int,
    source_path: Path = source_manager.SOURCE_PATH,
    get_mtime=source_manager.simulated_mtime,
) -> dict[str, Any]:
    """
    Execute the compiled artifact using the smart staleness strategy.

    Parameters
    ----------
    input_value  : Integer fed to the artifact's bytecode interpreter.
    source_path  : Path to the source file (injectable for tests).
    get_mtime    : Callable(path) → float returning the mtime to use.
                   Defaults to simulated_mtime so tests are deterministic.

    Returns
    -------
    A dict with keys:
        result      – integer output of the artifact
        cache_used  – True if the existing cache was reused without rebuild
        rebuilt     – True if the cache was invalidated and rebuilt
        decision    – the SmartDecision object
        artifact    – the artifact dict that was executed
    """
    content = source_manager.read_source(source_path)
    source_mtime = get_mtime(source_path)
    src_hash = source_manager.compute_hash(content)

    if cache_manager.cache_exists():
        metadata = cache_manager.load_metadata()
        decision = staleness_smart.check_staleness(source_mtime, src_hash, metadata)

        if not decision.is_stale:
            artifact = cache_manager.load_artifact()
            result = compiler.execute_artifact(artifact, input_value)
            return {
                "result": result,
                "cache_used": True,
                "rebuilt": False,
                "decision": decision,
                "artifact": artifact,
            }

        # Staleness detected — invalidate and rebuild
        cache_manager.invalidate_cache()
        artifact = compiler.compile_source(content)
        cache_manager.save_cache(
            artifact=artifact,
            source_content=content,
            source_hash=src_hash,
            source_version="rebuilt-smart",
            t_cache=source_mtime,
        )
        result = compiler.execute_artifact(artifact, input_value)
        return {
            "result": result,
            "cache_used": False,
            "rebuilt": True,
            "decision": decision,
            "artifact": artifact,
        }

    # No cache at all — build fresh
    artifact = compiler.compile_source(content)
    cache_manager.save_cache(
        artifact=artifact,
        source_content=content,
        source_hash=src_hash,
        source_version="initial",
        t_cache=source_mtime,
    )
    metadata = cache_manager.load_metadata()
    decision = staleness_smart.check_staleness(source_mtime, src_hash, metadata)
    result = compiler.execute_artifact(artifact, input_value)
    return {
        "result": result,
        "cache_used": False,
        "rebuilt": False,
        "decision": decision,
        "artifact": artifact,
    }
