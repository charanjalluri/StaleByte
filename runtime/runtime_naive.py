"""
runtime_naive.py
----------------
Naive runtime: uses only the timestamp-based staleness checker.
During a timestamp-collision scenario it will run the stale V1 artifact.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib import cache_manager, compiler, source_manager, staleness_naive


def run(
    input_value: int,
    source_path: Path = source_manager.SOURCE_PATH,
    get_mtime=source_manager.simulated_mtime,
) -> dict[str, Any]:
    """
    Execute the compiled artifact using the naive staleness strategy.

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
        cache_used  – True if the existing cache was reused
        decision    – the NaiveDecision object
        artifact    – the artifact dict that was executed
    """
    content = source_manager.read_source(source_path)
    source_mtime = get_mtime(source_path)

    if cache_manager.cache_exists():
        metadata = cache_manager.load_metadata()
        decision = staleness_naive.check_staleness(source_mtime, metadata)

        if not decision.is_stale:
            # Cache considered valid — use stale artifact (intentional flaw)
            artifact = cache_manager.load_artifact()
            result = compiler.execute_artifact(artifact, input_value)
            return {
                "result": result,
                "cache_used": True,
                "decision": decision,
                "artifact": artifact,
            }

    # Cache absent or stale — rebuild
    artifact = compiler.compile_source(content)
    src_hash = source_manager.compute_hash(content)
    cache_manager.save_cache(
        artifact=artifact,
        source_content=content,
        source_hash=src_hash,
        source_version="rebuilt",
        t_cache=source_mtime,
    )
    metadata = cache_manager.load_metadata()
    decision = staleness_naive.check_staleness(source_mtime, metadata)
    result = compiler.execute_artifact(artifact, input_value)
    return {
        "result": result,
        "cache_used": False,
        "decision": decision,
        "artifact": artifact,
    }
