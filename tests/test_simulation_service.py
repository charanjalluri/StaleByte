"""
test_simulation_service.py
--------------------------
Unit tests for the simulation service layer.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from lib import cache_manager
from services import simulation_service


@pytest.fixture()
def tmp_cache(monkeypatch, tmp_path):
    """Redirect cache paths to a temporary directory."""
    monkeypatch.setattr(cache_manager, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(cache_manager, "ARTIFACT_PATH", tmp_path / "artifact.json")
    monkeypatch.setattr(cache_manager, "METADATA_PATH", tmp_path / "metadata.json")
    return tmp_path


def test_simulation_service_normal_flow(tmp_cache):
    """Normal flow returns expected valid result 20."""
    data = simulation_service.run_normal_flow(input_value=10)
    assert data["result"] == 20
    assert not data["naive_decision"]["is_stale"]
    assert not data["smart_decision"]["is_stale"]


def test_simulation_service_collision_scenario(tmp_cache):
    """Collision scenario returns naive=20 and smart=30."""
    data = simulation_service.run_collision_scenario(input_value=10)
    assert data["naive_execution"]["result"] == 20
    assert data["smart_execution"]["result"] == 30
    assert data["naive_execution"]["is_stale"] is False
    assert data["smart_execution"]["is_stale"] is True
    assert data["smart_execution"]["rebuilt"] is True


def test_simulation_service_clock_skew(tmp_cache):
    """Clock skew returns result 20 and no false staleness."""
    data = simulation_service.run_clock_skew_scenario(input_value=10)
    assert data["result"] == 20
    assert not data["naive_decision"]["is_stale"]
    assert not data["smart_decision"]["is_stale"]


def test_simulation_service_status(tmp_cache):
    """System status returns proper fields."""
    status = simulation_service.get_system_status()
    assert "cache_exists" in status
    assert "simulated_mtime" in status
