"""
clock.py
--------
VirtualClock abstraction for deterministic time, timestamp resolution truncation,
machine clock skew simulation, and real system clock mode.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

DEFAULT_EPOCH: float = 1_700_000_000.0


@dataclass
class VirtualClock:
    """
    Controllable virtual or real clock.

    Parameters
    ----------
    current_time : Current base epoch timestamp in seconds (used when real_mode is False).
    resolution   : Timestamp resolution window in seconds (e.g., 1.0 for 1s, 2.0 for FAT32).
                   Timestamps are truncated/quantized to multiples of this resolution.
                   Use 0.0 or <= 0 for unquantized / native resolution.
    skew_offset  : Clock skew offset in seconds added to current_time (e.g., -50.0 for machine lag).
    real_mode    : If True, now() queries the actual system time (time.time()).
    """

    current_time: float = DEFAULT_EPOCH
    resolution: float = 1.0
    skew_offset: float = 0.0
    real_mode: bool = False

    @classmethod
    def real(cls, resolution: float = 0.0, skew_offset: float = 0.0) -> VirtualClock:
        """Factory for a clock reflecting actual system time."""
        return cls(resolution=resolution, skew_offset=skew_offset, real_mode=True)

    def now(self) -> float:
        """Return the raw observed time including skew offset."""
        if self.real_mode:
            return time.time() + self.skew_offset
        return self.current_time + self.skew_offset

    def quantized_now(self) -> float:
        """Return the observed time quantized/truncated to the configured resolution window."""
        return self.quantize(self.now())

    def quantize(self, timestamp: float) -> float:
        """Quantize a timestamp to the configured resolution window."""
        if self.resolution <= 0:
            return timestamp
        # Truncate to resolution boundary (floor division)
        steps = math.floor(timestamp / self.resolution)
        return float(steps * self.resolution)

    def advance(self, seconds: float) -> float:
        """Advance the base clock forward by *seconds* and return new quantized_now()."""
        if self.real_mode:
            self.skew_offset += seconds
        else:
            self.current_time += seconds
        return self.quantized_now()

    def set_time(self, timestamp: float) -> None:
        """Set the base clock time directly (simulated mode only)."""
        self.current_time = float(timestamp)

    def with_skew(self, skew_offset: float) -> VirtualClock:
        """Return a new VirtualClock sharing the base time/mode but with a different skew offset."""
        return VirtualClock(
            current_time=self.current_time,
            resolution=self.resolution,
            skew_offset=skew_offset,
            real_mode=self.real_mode,
        )
