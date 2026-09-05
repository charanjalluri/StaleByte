"""
test_hash.py
------------
Tests proving SHA-256 fingerprinting behaviour.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.source_manager import compute_hash, V1_CONTENT, V2_CONTENT


def test_hash_stable_for_identical_content():
    """Same content must always produce the same digest."""
    assert compute_hash(V1_CONTENT) == compute_hash(V1_CONTENT)


def test_hash_differs_for_different_content():
    """V1 and V2 content must produce different digests."""
    assert compute_hash(V1_CONTENT) != compute_hash(V2_CONTENT)


def test_hash_is_sha256_length():
    """SHA-256 hex digest is exactly 64 characters."""
    assert len(compute_hash(V1_CONTENT)) == 64


def test_hash_empty_string():
    """Empty string has a well-known SHA-256 digest."""
    known = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert compute_hash("") == known


def test_hash_case_sensitive():
    """Content differing only in case must yield different digests."""
    assert compute_hash("factor=2") != compute_hash("FACTOR=2")
