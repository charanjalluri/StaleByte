"""
StaleByte
=========
Compiled cache staleness verification and content-addressable caching primitive.
"""

from __future__ import annotations

from cache import CacheEntry, CacheStore, InMemoryCacheStore
from clock import VirtualClock
from invalidators import BaseInvalidator, InvalidationDecision, NaiveInvalidator, RobustInvalidator
from invalidators import BaseInvalidator as Invalidator
from runtime import ExecutionResult, Runtime
from source import SourceFile

__version__ = "1.3.0"

__all__ = [
    "BaseInvalidator",
    "CacheEntry",
    "CacheStore",
    "ExecutionResult",
    "InMemoryCacheStore",
    "InvalidationDecision",
    "Invalidator",
    "NaiveInvalidator",
    "RobustInvalidator",
    "Runtime",
    "SourceFile",
    "VirtualClock",
]
