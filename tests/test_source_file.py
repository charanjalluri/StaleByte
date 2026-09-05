"""
test_source_file.py
-------------------
Tests for SourceFile properties and SHA-256 fingerprinting.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from clock import VirtualClock
from source import SourceFile, V1_CONTENT, V2_CONTENT, compute_sha256


def test_source_file_fingerprinting():
    src = SourceFile(content=V1_CONTENT)
    assert src.content_hash == compute_sha256(V1_CONTENT)
    assert src.size == len(V1_CONTENT.encode("utf-8"))

    # Update content to V2
    src.update_content(V2_CONTENT)
    assert src.content_hash == compute_sha256(V2_CONTENT)
    assert src.content_hash != compute_sha256(V1_CONTENT)


def test_source_file_mtime_derived_from_clock():
    clock = VirtualClock(current_time=1_700_000_000.0, resolution=1.0)
    src = SourceFile(content=V1_CONTENT, clock=clock)

    assert src.mtime == 1_700_000_000.0

    # Advance clock by 0.5s (within 1s window) -> mtime remains same
    clock.advance(0.5)
    src.update_content(V2_CONTENT)
    assert src.mtime == 1_700_000_000.0  # Resolution collision!
