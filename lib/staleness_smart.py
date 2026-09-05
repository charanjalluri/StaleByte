"""
staleness_smart.py
------------------
StaleByte smart checker: compares the source timestamp *and* its SHA-256
fingerprint against the cached values.  This correctly detects content
changes even when timestamps are identical (collision scenario).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SmartDecision:
    """Structured result returned by the smart checker."""
    is_stale: bool
    timestamp_match: bool
    hash_match: bool
    source_mtime: float
    cached_t_cache: float
    source_hash: str
    cached_hash: str
    reason: str


def check_staleness(
    source_mtime: float,
    source_hash: str,
    metadata: dict[str, Any],
) -> SmartDecision:
    """
    Decide whether the cache is stale using timestamps **and** SHA-256 hashes.

    Logic
    -----
    1. Compare source_mtime with metadata['t_cache'].
    2. Compare source_hash with metadata['source_hash'].
    3. The cache is stale if *either* the timestamp indicates a newer source
       **or** the hashes differ.

    The hash check catches the timestamp-collision scenario: even when
    source_mtime == t_cache, differing hashes prove the content changed.

    Parameters
    ----------
    source_mtime : Observed mtime of the source file (may be simulated).
    source_hash  : Current SHA-256 hex digest of the source content.
    metadata     : Loaded cache metadata dict.

    Returns
    -------
    SmartDecision with full diagnostic fields.
    """
    t_cache: float = metadata["t_cache"]
    cached_hash: str = metadata["source_hash"]

    timestamp_match: bool = source_mtime <= t_cache
    hash_match: bool = source_hash == cached_hash
    is_stale: bool = not hash_match or not timestamp_match

    if not hash_match and timestamp_match:
        if source_mtime == t_cache:
            reason = (
                f"Timestamp collision detected: source_mtime ({source_mtime}) "
                f"== t_cache ({t_cache}), but SHA-256 hashes differ. "
                "Cache is STALE. [StaleByte caught it!]"
            )
        else:
            reason = (
                f"Source appears older (mtime={source_mtime} < t_cache={t_cache}) "
                "but SHA-256 hashes differ — content changed under clock skew. "
                "Cache is STALE. [StaleByte caught it!]"
            )
    elif not timestamp_match:
        reason = (
            f"Source mtime ({source_mtime}) > t_cache ({t_cache}). "
            "Cache is stale (timestamp alone is sufficient)."
        )
    else:
        reason = (
            f"Timestamp and hash both match. "
            "Cache is valid — no rebuild needed."
        )

    return SmartDecision(
        is_stale=is_stale,
        timestamp_match=timestamp_match,
        hash_match=hash_match,
        source_mtime=source_mtime,
        cached_t_cache=t_cache,
        source_hash=source_hash,
        cached_hash=cached_hash,
        reason=reason,
    )
