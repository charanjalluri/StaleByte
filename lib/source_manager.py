"""
source_manager.py
-----------------
Reads, writes, and fingerprints the controlled key=value source file.
All timestamps exposed here are *simulated* so scenarios remain deterministic.
"""

import hashlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOURCE_PATH = Path(__file__).parent.parent / "src" / "program.src"

V1_CONTENT = "operation=multiply\nfactor=2\n"
V2_CONTENT = "operation=multiply\nfactor=3\n"

# A fixed epoch used as the "simulated" mtime for collision scenarios.
SIMULATED_MTIME: float = 1_700_000_000.0


# ---------------------------------------------------------------------------
# Source I/O
# ---------------------------------------------------------------------------

def create_source(content: str, path: Path = SOURCE_PATH) -> None:
    """Write *content* to the source file."""
    path.write_text(content, encoding="utf-8")


def read_source(path: Path = SOURCE_PATH) -> str:
    """Return the raw text of the source file."""
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------

def compute_hash(content: str) -> str:
    """Return the SHA-256 hex digest of *content*."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def source_hash(path: Path = SOURCE_PATH) -> str:
    """Read *path* and return its SHA-256 hex digest."""
    return compute_hash(read_source(path))


def source_size(path: Path = SOURCE_PATH) -> int:
    """Return the byte-length of the source file content."""
    return len(read_source(path).encode("utf-8"))


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------

def real_mtime(path: Path = SOURCE_PATH) -> float:
    """Return the actual filesystem mtime of *path*."""
    return path.stat().st_mtime


def simulated_mtime(_path: Path = SOURCE_PATH) -> float:
    """
    Return a fixed simulated mtime.

    Both V1 and V2 will report this same value so that timestamp-only
    checkers cannot distinguish them — demonstrating the collision scenario.
    """
    return SIMULATED_MTIME
