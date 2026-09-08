"""
source.py
---------
SourceFile abstraction managing source content, SHA-256 fingerprinting,
and either VirtualClock-driven or actual os.stat() filesystem modification timestamps.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from clock import VirtualClock

V1_CONTENT: str = "operation=multiply\nfactor=2\n"
V2_CONTENT: str = "operation=multiply\nfactor=3\n"


def compute_sha256(content: str) -> str:
    """Return the SHA-256 hex digest of the UTF-8 encoded *content*."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class SourceFile:
    """
    Source file representation with content fingerprint and mtime.

    In simulated mode (real_mode=False), mtime is derived from the VirtualClock or an explicit mtime.
    In real filesystem mode (real_mode=True), mtime and content are read directly
    from actual disk metadata via os.stat().
    """

    def __init__(
        self,
        path: Path | str = "src/program.src",
        content: str = V1_CONTENT,
        clock: VirtualClock | None = None,
        real_mode: bool = False,
        mtime: float | None = None,
        size: int | None = None,
        content_hash: str | None = None,
    ) -> None:
        self.path = Path(path)
        self.content = content
        if clock is not None:
            self.clock = clock
        elif mtime is not None:
            self.clock = VirtualClock(current_time=mtime, resolution=0.0)
        else:
            self.clock = VirtualClock()
        self.real_mode = real_mode
        self._explicit_mtime = mtime
        self._explicit_size = size
        self._explicit_hash = content_hash

    @classmethod
    def from_file(cls, path: Path | str, real_mode: bool = True) -> SourceFile:
        """
        Instantiate a SourceFile from an actual path on disk.

        Raises
        ------
        FileNotFoundError: If the target file does not exist.
        IsADirectoryError: If the target path is a directory.
        PermissionError: If the target file cannot be read.
        """
        p = Path(path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Source file '{p}' does not exist.")
        if p.is_dir():
            raise IsADirectoryError(f"Target path '{p}' is a directory, not a file.")

        try:
            raw_content = p.read_text(encoding="utf-8")
        except PermissionError as exc:
            raise PermissionError(f"Cannot read source file '{p}': Permission denied.") from exc

        return cls(
            path=p,
            content=raw_content,
            clock=VirtualClock.real() if real_mode else VirtualClock(),
            real_mode=real_mode,
        )

    @property
    def size(self) -> int:
        """Byte length of the content on disk or in memory."""
        if self._explicit_size is not None:
            return self._explicit_size
        if self.real_mode and self.path.is_file():
            try:
                return os.stat(self.path).st_size
            except OSError:
                pass
        return len(self.content.encode("utf-8"))

    @property
    def mtime(self) -> float:
        """
        Modification timestamp.
        Queries os.stat().st_mtime in real_mode; otherwise queries VirtualClock.
        """
        if self._explicit_mtime is not None:
            return self._explicit_mtime
        if self.real_mode and self.path.is_file():
            try:
                return os.stat(self.path).st_mtime
            except OSError:
                pass
        return self.clock.quantized_now()

    @property
    def content_hash(self) -> str:
        """Cryptographic SHA-256 hex digest of the in-memory content.

        Pure read — never touches disk and never mutates ``.content``.
        Call :meth:`refresh` or :meth:`snapshot` first when disk state
        is needed in ``real_mode``.
        """
        if self._explicit_hash is not None:
            return self._explicit_hash
        return compute_sha256(self.content)

    def snapshot(self) -> tuple[str, float, int, str]:
        """Atomically capture ``(content, mtime, size, content_hash)``.

        In ``real_mode`` the disk content is re-read exactly once before
        deriving mtime/size/hash, so the hash always corresponds to the
        returned content (no A-mtime/B-hash Frankenstein reads). In
        simulated mode the in-memory state is returned as-is.
        """
        if self.real_mode and self.path.is_file():
            try:
                self.content = self.path.read_text(encoding="utf-8")
            except OSError:
                pass
        return (self.content, self.mtime, self.size, self.content_hash)

    def refresh(self) -> None:
        """Re-read content from disk if in real_mode."""
        if self.real_mode and self.path.is_file():
            self.content = self.path.read_text(encoding="utf-8")

    def update_content(self, new_content: str) -> None:
        """Update source content (mtime will reflect current clock or disk time)."""
        self.content = new_content
        if self.real_mode and self.path.is_file():
            self.path.write_text(new_content, encoding="utf-8")

    def write_to_disk(self, target_path: Path | None = None) -> None:
        """Persist content to filesystem."""
        dst = target_path or self.path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(self.content, encoding="utf-8")

    def read_from_disk(self, source_path: Path | None = None) -> str:
        """Read content from filesystem and update self."""
        src = source_path or self.path
        self.content = src.read_text(encoding="utf-8")
        return self.content
