"""
test_fuzz.py
------------
Statistical tests verifying the quantifiable exposure of silent cache staleness bugs.
Proves that RobustInvalidator has a strictly 0.0% failure rate across randomized trials,
while NaiveInvalidator exhibits a non-zero, measurable silent failure rate.
"""

from __future__ import annotations

import json

import cli
import fuzz


def test_robust_failure_rate_is_strictly_zero_percent():
    """
    Assert that the robust SHA-256 validator never fails silently across randomized trials.
    """
    summary = fuzz.run_fuzz_suite(trials=2000, seed=12345)
    assert summary.robust_failures == 0
    assert summary.robust_failure_rate_pct == 0.0
    assert summary.robust_correct == 2000


def test_naive_failure_rate_is_strictly_greater_than_zero():
    """
    Assert that naive timestamp validation fails silently in a non-zero percentage of trials,
    empirically proving the bug exists and is measurable.
    """
    summary = fuzz.run_fuzz_suite(trials=2000, seed=12345)
    assert summary.naive_silent_failures > 0
    assert summary.naive_failure_rate_pct > 0.0
    # Both failure causes must be present in a diverse randomized run
    assert summary.naive_causes["resolution_collision"] > 0
    assert summary.naive_causes["clock_skew"] > 0


def test_fuzz_json_serialization():
    """
    Verify machine-readable dictionary format for reporting and slides.
    """
    summary = fuzz.run_fuzz_suite(trials=100, seed=999)
    data = summary.to_dict()

    assert data["total_trials"] == 100
    assert "naive" in data
    assert "robust" in data
    assert data["robust"]["failure_rate_pct"] == 0.0
    assert data["naive"]["failure_rate_pct"] > 0.0
    assert "causes" in data["naive"]
    assert "resolution_collision" in data["naive"]["causes"]
    assert "clock_skew" in data["naive"]["causes"]
    assert "exposure_summary" in data


def test_cli_fuzz_subcommand_json(capsys):
    """
    Verify `python cli.py fuzz --trials 100 --json` CLI integration.
    """
    code = cli.main(["fuzz", "--trials", "100", "--seed", "42", "--json"])
    assert code == 0

    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["total_trials"] == 100
    assert parsed["robust"]["failures"] == 0
    assert parsed["naive"]["silent_failures"] > 0
