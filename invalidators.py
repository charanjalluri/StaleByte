"""
invalidators.py
---------------
Staleness validation strategies:
- NaiveInvalidator: Standard, flawed mtime-only comparison.
- RobustInvalidator: Cryptographic content-hash verification resistant to
  timestamp resolution collisions and clock skew.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from cache import CacheEntry
from source import SourceFile


@dataclass(frozen=True)
class InvalidationDecision:
    """
    Diagnostic result of a staleness check.
    """

    is_stale: bool
    timestamp_match: bool
    hash_match: bool
    source_mtime: float
    cached_mtime: float
    source_hash: str
    cached_hash: str
    reason: str


class BaseInvalidator(ABC):
    """Abstract base class for staleness checkers."""

    @abstractmethod
    def check(self, source: SourceFile, entry: CacheEntry) -> InvalidationDecision:
        """Evaluate if cached entry is stale with respect to current source."""
        pass


class NaiveInvalidator(BaseInvalidator):
    """
    Naive timestamp-only validator.
    Considers cache valid whenever source.mtime <= entry.cached_mtime.
    Intentionally vulnerable to timestamp resolution collisions.
    """

    def check(self, source: SourceFile, entry: CacheEntry) -> InvalidationDecision:
        timestamp_match = source.mtime <= entry.cached_mtime
        hash_match = source.content_hash == entry.content_hash

        if source.mtime > entry.cached_mtime:
            is_stale = True
            reason = (
                f"Source mtime ({source.mtime}) > cached mtime ({entry.cached_mtime}). "
                "Cache is stale (timestamp check)."
            )
        else:
            is_stale = False
            reason = (
                f"Source mtime ({source.mtime}) <= cached mtime ({entry.cached_mtime}). "
                "Timestamps match — cache considered valid (naive)."
            )

        return InvalidationDecision(
            is_stale=is_stale,
            timestamp_match=timestamp_match,
            hash_match=hash_match,
            source_mtime=source.mtime,
            cached_mtime=entry.cached_mtime,
            source_hash=source.content_hash,
            cached_hash=entry.content_hash,
            reason=reason,
        )


class RobustInvalidator(BaseInvalidator):
    """
    Robust content-addressable validator.
    Uses SHA-256 fingerprint as ground truth. Never fooled by timestamp collisions or skew.
    A newer mtime with identical content is NOT stale (e.g. touch / git checkout):
    timestamps are diagnostic only, the hash decides.
    """

    def check(self, source: SourceFile, entry: CacheEntry) -> InvalidationDecision:
        timestamp_match = source.mtime <= entry.cached_mtime
        hash_match = source.content_hash == entry.content_hash
        # Content hash is ground truth; timestamps are diagnostic context only.
        is_stale = not hash_match

        if not hash_match and timestamp_match:
            if source.mtime == entry.cached_mtime:
                reason = (
                    f"Content hash mismatch ({source.content_hash[:8]}... != {entry.content_hash[:8]}...) "
                    f"despite matching mtime ({source.mtime}) — resolution window collision."
                )
            else:
                reason = (
                    f"Content hash mismatch ({source.content_hash[:8]}... != {entry.content_hash[:8]}...) "
                    f"under clock skew (source mtime {source.mtime} < cached {entry.cached_mtime})."
                )
        elif not hash_match:
            reason = (
                f"Content hash mismatch ({source.content_hash[:8]}... != {entry.content_hash[:8]}...) "
                f"with newer source mtime ({source.mtime} > cached {entry.cached_mtime}). "
                "Cache is stale."
            )
        else:
            if not timestamp_match:
                reason = (
                    "Content hash matches; source mtime is newer (e.g. touch / checkout) "
                    "but content is unchanged. Cache is valid — no rebuild needed."
                )
            else:
                reason = "Content hash and timestamp both match. Cache is valid — no rebuild needed."

        return InvalidationDecision(
            is_stale=is_stale,
            timestamp_match=timestamp_match,
            hash_match=hash_match,
            source_mtime=source.mtime,
            cached_mtime=entry.cached_mtime,
            source_hash=source.content_hash,
            cached_hash=entry.content_hash,
            reason=reason,
        )
