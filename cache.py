"""
cache.py
--------
CacheStore and CacheEntry models for compiled artifact persistence
and build metadata management, supporting both global and per-file path keys.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import uuid
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CacheEntry:
    """
    Complete cache entry containing compiled artifact and build provenance.
    """

    source_path: str
    cached_mtime: float
    cached_size: int
    content_hash: str
    artifact: dict[str, Any]
    build_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    build_counter: int = 1
    version_label: str = "V1"


def compute_path_key(source_path: str | Path) -> str:
    """Compute a deterministic short hash key for a normalized absolute file path."""
    try:
        norm = str(Path(source_path).resolve())
    except Exception:
        norm = str(source_path)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def _atomic_write_text(target: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text atomically to target path via temporary file and atomic os.replace."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_name(f"{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        temp_path.write_text(text, encoding=encoding)
        os.replace(temp_path, target)
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


class CacheStore:
    """
    On-disk persistence manager for cache artifacts and metadata.
    Supports both default single-artifact caching and multi-file caching
    keyed by normalized source file path.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else (Path(__file__).parent / "cache")
        self.artifact_path = self.cache_dir / "artifact.json"
        self.metadata_path = self.cache_dir / "metadata.json"
        self._build_count = 0
        self._lock = threading.RLock()

    def _get_paths(self, source_path: str | Path | None = None) -> tuple[Path, Path]:
        """Return (artifact_path, metadata_path) for the given source_path or default."""
        if source_path is not None:
            key = compute_path_key(source_path)
            return (
                self.cache_dir / f"artifact_{key}.json",
                self.cache_dir / f"metadata_{key}.json",
            )
        return (self.artifact_path, self.metadata_path)

    def exists(self, source_path: str | Path | None = None) -> bool:
        """Return True if both artifact and metadata exist for the given source_path or default."""
        with self._lock:
            art_p, meta_p = self._get_paths(source_path)
            if art_p.exists() and meta_p.exists():
                return True
            # If source_path was given but specific cache doesn't exist, check default cache
            if source_path is not None and self.artifact_path.exists() and self.metadata_path.exists():
                try:
                    meta = json.loads(self.metadata_path.read_text(encoding="utf-8"))
                    cached_sp = meta.get("source_path")
                    if (
                        cached_sp is None
                        or cached_sp == str(source_path)
                        or cached_sp == str(Path(source_path).resolve())
                        or Path(cached_sp).name == Path(source_path).name
                    ):
                        return True
                except Exception:
                    pass
            return False

    def save(self, entry: CacheEntry) -> CacheEntry:
        """Persist CacheEntry to disk atomically via temporary files and locking."""
        with self._lock:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._build_count += 1
            entry.build_counter = self._build_count

            metadata = {
                "artifact_id": entry.build_id,
                "build_counter": entry.build_counter,
                "source_path": str(entry.source_path),
                "t_cache": entry.cached_mtime,
                "source_hash": entry.content_hash,
                "source_size": entry.cached_size,
                "source_version": entry.version_label,
            }

            art_json = json.dumps(entry.artifact, indent=2)
            meta_json = json.dumps(metadata, indent=2)

            # Save to path-keyed files atomically
            art_p, meta_p = self._get_paths(entry.source_path)
            _atomic_write_text(art_p, art_json)
            _atomic_write_text(meta_p, meta_json)

            # Also write to default artifact.json and metadata.json for backward compatibility
            _atomic_write_text(self.artifact_path, art_json)
            _atomic_write_text(self.metadata_path, meta_json)

            return entry

    def load(self, source_path: str | Path | None = None) -> CacheEntry | None:
        """
        Load CacheEntry from disk, returning None if missing.
        Logs an explicit warning if the cache files exist but are corrupted.
        """
        with self._lock:
            art_p, meta_p = self._get_paths(source_path)

            if source_path is not None:
                if art_p.exists() and meta_p.exists():
                    target_art, target_meta = art_p, meta_p
                elif self.artifact_path.exists() and self.metadata_path.exists():
                    try:
                        meta_check = json.loads(self.metadata_path.read_text(encoding="utf-8"))
                        cached_sp = meta_check.get("source_path")
                        if (
                            cached_sp is None
                            or cached_sp == str(source_path)
                            or cached_sp == str(Path(source_path).resolve())
                            or Path(cached_sp).name == Path(source_path).name
                        ):
                            target_art, target_meta = self.artifact_path, self.metadata_path
                        else:
                            return None
                    except Exception:
                        return None
                else:
                    return None
            else:
                target_art, target_meta = self.artifact_path, self.metadata_path

            if not (target_art.exists() and target_meta.exists()):
                return None

            try:
                artifact = json.loads(target_art.read_text(encoding="utf-8"))
                meta = json.loads(target_meta.read_text(encoding="utf-8"))
                return CacheEntry(
                    source_path=meta.get("source_path", "program.src"),
                    cached_mtime=float(meta["t_cache"]),
                    cached_size=int(meta["source_size"]),
                    content_hash=str(meta["source_hash"]),
                    artifact=artifact,
                    build_id=str(meta.get("artifact_id", "")),
                    build_counter=int(meta.get("build_counter", 1)),
                    version_label=str(meta.get("source_version", "")),
                )
            except Exception as exc:
                warn_msg = f"[WARN] CacheStore: corrupt cache detected at '{target_art}' / '{target_meta}': {exc}"
                print(warn_msg, file=sys.stderr)
                warnings.warn(warn_msg, UserWarning, stacklevel=2)
                return None

    def invalidate(self, source_path: str | Path | None = None) -> None:
        """Remove cached artifact and metadata from disk."""
        with self._lock:
            paths_to_remove = set()
            if source_path is not None:
                art_p, meta_p = self._get_paths(source_path)
                paths_to_remove.add(art_p)
                paths_to_remove.add(meta_p)
            elif self.cache_dir.exists():
                for p in self.cache_dir.glob("*.json"):
                    paths_to_remove.add(p)

            # Also remove default paths
            paths_to_remove.add(self.artifact_path)
            paths_to_remove.add(self.metadata_path)

            for p in paths_to_remove:
                if p.exists():
                    try:
                        p.unlink()
                    except OSError:
                        pass


class InMemoryCacheStore(CacheStore):
    """
    Isolated in-memory cache store for deterministic simulations, testing,
    and scripted demonstrations. Does not read or write from the filesystem,
    preventing any real-disk timestamps or state from leaking into simulations.
    """

    def __init__(self) -> None:
        super().__init__(cache_dir=Path(".in_memory_cache"))
        self._entries: dict[str, CacheEntry] = {}
        self._build_count = 0
        self._lock = threading.RLock()

    def exists(self, source_path: str | Path | None = None) -> bool:
        with self._lock:
            key = str(Path(source_path).resolve()) if source_path else "__default__"
            return key in self._entries or "__default__" in self._entries

    def save(self, entry: CacheEntry) -> CacheEntry:
        with self._lock:
            self._build_count += 1
            entry.build_counter = self._build_count
            key = str(Path(entry.source_path).resolve()) if entry.source_path else "__default__"
            self._entries[key] = entry
            self._entries["__default__"] = entry
            return entry

    def load(self, source_path: str | Path | None = None) -> CacheEntry | None:
        with self._lock:
            key = str(Path(source_path).resolve()) if source_path else "__default__"
            return self._entries.get(key) or self._entries.get("__default__")

    def invalidate(self, source_path: str | Path | None = None) -> None:
        with self._lock:
            if source_path is not None:
                key = str(Path(source_path).resolve())
                self._entries.pop(key, None)
            else:
                self._entries.clear()

