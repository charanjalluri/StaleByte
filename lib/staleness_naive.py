"""
staleness_naive.py
------------------
Naive staleness checker: compares only the source timestamp against the
cached timestamp.  This checker is intentionally blind to content changes
and will incorrectly consider a stale cache valid whenever timestamps match.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NaiveDecision:
    """Structured result returned by the naive checker."""
    is_stale: bool
    source_mtime: float
    cached_t_cache: float
    reason: str


def check_staleness(
    source_mtime: float,
    metadata: dict[str, Any],
) -> NaiveDecision:
    """
    Decide whether the cache is stale using *only* timestamps.

    The cache is considered **stale** when the source mtime is strictly
    greater than the cached t_cache — meaning the source was modified after
    the cache was written.

    In a timestamp-collision scenario both values will be equal, so the
    checker will (incorrectly) report the cache as valid.

    Parameters
    ----------
    source_mtime : Observed mtime of the source file (may be simulated).
    metadata     : Loaded cache metadata dict (must contain 't_cache').

    Returns
    -------
    NaiveDecision with is_stale=False when timestamps are equal or the source
    appears older than the cache.
    """
    t_cache: float = metadata["t_cache"]

    if source_mtime > t_cache:
        return NaiveDecision(
            is_stale=True,
            source_mtime=source_mtime,
            cached_t_cache=t_cache,
            reason=(
                f"Source mtime ({source_mtime}) is newer than "
                f"cached t_cache ({t_cache}). Cache is stale."
            ),
        )

    return NaiveDecision(
        is_stale=False,
        source_mtime=source_mtime,
        cached_t_cache=t_cache,
        reason=(
            f"Source mtime ({source_mtime}) ≤ cached t_cache ({t_cache}). "
            "Timestamps match — cache considered valid (naive)."
        ),
    )
