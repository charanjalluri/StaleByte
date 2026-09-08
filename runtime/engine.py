"""
engine.py
---------
Unified Runtime executing source artifacts through pluggable invalidators.
Provides polymorphic execution:
    result = runtime.execute(source, invalidator, input_val=10)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cache import CacheEntry, CacheStore
from invalidators import BaseInvalidator, InvalidationDecision, RobustInvalidator
from lib import compiler
from source import SourceFile


@dataclass(frozen=True)
class ExecutionResult:
    """Structured result returned by Runtime.execute."""

    output: int
    cache_hit: bool
    rebuilt: bool
    decision: InvalidationDecision
    artifact: dict[str, Any]


class Runtime:
    """
    Unified execution runtime coordinating CacheStore, compiler, and invalidators.
    """

    def __init__(self, cache_store: CacheStore | None = None) -> None:
        self.cache_store = cache_store or CacheStore()

    def check_staleness(
        self,
        source: SourceFile,
        invalidator: BaseInvalidator | None = None,
    ) -> tuple[InvalidationDecision, CacheEntry | None]:
        """
        Check staleness of the current source against the cache without modifying cache state.
        Returns (decision, cache_entry).
        """
        # Single atomic snapshot so mtime/hash/size correspond to the same
        # disk read (no A-mtime/B-hash Frankenstein state). The invalidator
        # then reads the already-synced in-memory values.
        source.snapshot()
        checker = invalidator or RobustInvalidator()
        entry = self.cache_store.load(source_path=str(source.path))
        if entry is None:
            return (
                InvalidationDecision(
                    is_stale=True,
                    timestamp_match=False,
                    hash_match=False,
                    source_mtime=source.mtime,
                    cached_mtime=0.0,
                    source_hash=source.content_hash,
                    cached_hash="",
                    reason="No cached artifact found for this source file.",
                ),
                None,
            )
        return checker.check(source, entry), entry

    def execute(
        self,
        source: SourceFile,
        invalidator: BaseInvalidator | None = None,
        input_value: int = 10,
    ) -> ExecutionResult:
        """
        Get-or-build artifact via the given invalidator, then execute it on *input_value*.
        """
        # Atomic snapshot once: content/mtime/size/hash below all derive
        # from this single read, so the built CacheEntry is self-consistent.
        content, src_mtime, src_size, src_hash = source.snapshot()
        checker = invalidator or RobustInvalidator()
        src_key = str(source.path)
        entry = self.cache_store.load(source_path=src_key)

        if entry is not None:
            decision = checker.check(source, entry)

            if not decision.is_stale:
                # Cache HIT: execute existing cached artifact
                output = compiler.execute_artifact(entry.artifact, input_value)
                return ExecutionResult(
                    output=output,
                    cache_hit=True,
                    rebuilt=False,
                    decision=decision,
                    artifact=entry.artifact,
                )

            # Cache MISS (stale): invalidate and rebuild
            self.cache_store.invalidate(source_path=src_key)
            new_artifact = compiler.compile_source(content)
            new_entry = CacheEntry(
                source_path=str(source.path),
                cached_mtime=src_mtime,
                cached_size=src_size,
                content_hash=src_hash,
                artifact=new_artifact,
                version_label="rebuilt",
            )
            self.cache_store.save(new_entry)
            output = compiler.execute_artifact(new_artifact, input_value)
            return ExecutionResult(
                output=output,
                cache_hit=False,
                rebuilt=True,
                decision=decision,
                artifact=new_artifact,
            )

        # Initial build (no cache exists)
        artifact = compiler.compile_source(content)
        new_entry = CacheEntry(
            source_path=str(source.path),
            cached_mtime=src_mtime,
            cached_size=src_size,
            content_hash=src_hash,
            artifact=artifact,
            version_label="initial",
        )
        self.cache_store.save(new_entry)
        decision = checker.check(source, new_entry)
        output = compiler.execute_artifact(artifact, input_value)
        return ExecutionResult(
            output=output,
            cache_hit=False,
            rebuilt=False,
            decision=decision,
            artifact=artifact,
        )
