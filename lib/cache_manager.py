"""
cache_manager.py
----------------
Saves, loads, and invalidates the compiled artifact and its metadata.
Both files live under stalebyte/cache/.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).parent.parent / "cache"
ARTIFACT_PATH = CACHE_DIR / "artifact.json"
METADATA_PATH = CACHE_DIR / "metadata.json"


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_cache(
    artifact: dict[str, Any],
    source_content: str,
    source_hash: str,
    source_version: str,
    t_cache: float | None = None,
) -> dict[str, Any]:
    """
    Persist *artifact* and its metadata to disk.

    Parameters
    ----------
    artifact        : Compiled artifact dict produced by compiler.compile_source.
    source_content  : Raw source text (used to compute source_size).
    source_hash     : Pre-computed SHA-256 hex digest of the source.
    source_version  : Human-readable version label, e.g. 'V1'.
    t_cache         : Optional override for the cache timestamp (float epoch).
                      Defaults to current UTC time.  Use in tests/scenarios for
                      deterministic behaviour.

    Returns
    -------
    The metadata dict that was written to disk.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if t_cache is None:
        t_cache = datetime.now(timezone.utc).timestamp()

    metadata: dict[str, Any] = {
        "artifact_id": str(uuid.uuid4()),
        "t_cache": t_cache,
        "source_hash": source_hash,
        "source_size": len(source_content.encode("utf-8")),
        "source_version": source_version,
    }

    # Clean up any stale path-keyed artifacts from previous runs
    for pattern in ("artifact_*.json", "metadata_*.json"):
        for p in CACHE_DIR.glob(pattern):
            try:
                p.unlink()
            except OSError:
                pass

    ARTIFACT_PATH.write_text(
        json.dumps(artifact, indent=2), encoding="utf-8"
    )
    METADATA_PATH.write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return metadata


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_artifact() -> dict[str, Any]:
    """
    Load and return the cached artifact.

    Raises
    ------
    FileNotFoundError  if the artifact file is absent.
    ValueError         if the file is not valid JSON.
    """
    _require_file(ARTIFACT_PATH)
    try:
        return json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed artifact cache: {exc}") from exc


def load_metadata() -> dict[str, Any]:
    """
    Load and return the cache metadata.

    Raises
    ------
    FileNotFoundError  if the metadata file is absent.
    ValueError         if the file is not valid JSON or required keys are missing.
    """
    _require_file(METADATA_PATH)
    try:
        meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed metadata cache: {exc}") from exc

    required = {"artifact_id", "t_cache", "source_hash", "source_size", "source_version"}
    missing = required - meta.keys()
    if missing:
        raise ValueError(f"Metadata missing required keys: {missing}")
    return meta


def cache_exists() -> bool:
    """Return True only when *both* cache files are present."""
    return ARTIFACT_PATH.exists() and METADATA_PATH.exists()


# ---------------------------------------------------------------------------
# Invalidation
# ---------------------------------------------------------------------------

def invalidate_cache() -> None:
    """
    Remove both cache files if they exist.

    Safe to call even when no cache is present.
    """
    for pattern in ("artifact*.json", "metadata*.json"):
        for path in CACHE_DIR.glob(pattern):
            if path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Cache file not found: {path}. "
            "Run a build step first to populate the cache."
        )
