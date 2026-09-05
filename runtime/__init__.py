"""
runtime package
---------------
Exports unified Runtime engine and convenience helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from cache import CacheEntry, CacheStore
from invalidators import NaiveInvalidator, RobustInvalidator
from lib import cache_manager, compiler, source_manager
from runtime.engine import ExecutionResult, Runtime
from source import SourceFile

__all__ = ["Runtime", "ExecutionResult", "run_naive", "run_smart"]


def run_naive(
    input_value: int,
    source_path: Path | str = source_manager.SOURCE_PATH,
    get_mtime: Callable[[Path], float] | None = None,
    cache_store: CacheStore | None = None,
) -> dict[str, Any]:
    """Execute using unified Runtime with NaiveInvalidator."""
    p = Path(source_path)
    content = p.read_text(encoding="utf-8") if p.exists() else ""
    if get_mtime is not None:
        mtime = get_mtime(p)
    elif p.exists():
        mtime = p.stat().st_mtime
    else:
        mtime = 0.0

    src = SourceFile(path=str(p), content=content, mtime=mtime)
    store = cache_store or CacheStore(cache_dir=cache_manager.CACHE_DIR)
    rt = Runtime(cache_store=store)
    res = rt.execute(source=src, invalidator=NaiveInvalidator(), input_value=input_value)
    return {
        "result": res.output,
        "cache_used": res.cache_hit,
        "rebuilt": res.rebuilt,
        "decision": res.decision,
        "artifact": res.artifact,
    }


def run_smart(
    input_value: int,
    source_path: Path | str = source_manager.SOURCE_PATH,
    get_mtime: Callable[[Path], float] | None = None,
    cache_store: CacheStore | None = None,
) -> dict[str, Any]:
    """Execute using unified Runtime with RobustInvalidator."""
    p = Path(source_path)
    content = p.read_text(encoding="utf-8") if p.exists() else ""
    if get_mtime is not None:
        mtime = get_mtime(p)
    elif p.exists():
        mtime = p.stat().st_mtime
    else:
        mtime = 0.0

    src = SourceFile(path=str(p), content=content, mtime=mtime)
    store = cache_store or CacheStore(cache_dir=cache_manager.CACHE_DIR)
    rt = Runtime(cache_store=store)
    res = rt.execute(source=src, invalidator=RobustInvalidator(), input_value=input_value)
    return {
        "result": res.output,
        "cache_used": res.cache_hit,
        "rebuilt": res.rebuilt,
        "decision": res.decision,
        "artifact": res.artifact,
    }
