"""
test_cli_and_real_fs.py
-----------------------
Tests for real filesystem mode, persistent multi-file caching, and the CLI tool.
Verifies real os.stat() mtimes, disk writes, cache hit/miss on edited files,
and clean error reporting.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

import cli
from cache import CacheStore
from invalidators import NaiveInvalidator, RobustInvalidator
from runtime import Runtime
from source import SourceFile


def test_real_source_file_uses_os_stat(tmp_path):
    real_file = tmp_path / "math.src"
    real_file.write_text("operation=multiply\nfactor=4\n", encoding="utf-8")

    src = SourceFile.from_file(real_file, real_mode=True)
    expected_stat = os.stat(real_file)

    assert src.path == real_file.resolve()
    assert src.mtime == pytest.approx(expected_stat.st_mtime, abs=1e-4)
    assert src.size == expected_stat.st_size
    assert "factor=4" in src.content


def test_real_file_unchanged_reports_cache_hit(tmp_path):
    src_file = tmp_path / "calc.src"
    src_file.write_text("operation=multiply\nfactor=7\n", encoding="utf-8")

    cache_dir = tmp_path / "test_cache"
    store = CacheStore(cache_dir=cache_dir)
    runtime = Runtime(cache_store=store)

    src = SourceFile.from_file(src_file, real_mode=True)

    # Initial build
    res_init = runtime.execute(src, RobustInvalidator(), input_value=5)
    assert res_init.output == 35
    assert not res_init.cache_hit

    # Second check without file change -> real cache hit
    src.refresh()
    decision_naive, entry = runtime.check_staleness(src, NaiveInvalidator())
    decision_robust, _ = runtime.check_staleness(src, RobustInvalidator())

    assert entry is not None
    assert not decision_naive.is_stale
    assert not decision_robust.is_stale
    assert decision_robust.hash_match
    assert decision_robust.timestamp_match


def test_real_file_edited_reports_cache_miss(tmp_path):
    src_file = tmp_path / "calc.src"
    src_file.write_text("operation=multiply\nfactor=2\n", encoding="utf-8")

    cache_dir = tmp_path / "test_cache"
    store = CacheStore(cache_dir=cache_dir)
    runtime = Runtime(cache_store=store)

    src = SourceFile.from_file(src_file, real_mode=True)
    runtime.execute(src, RobustInvalidator(), input_value=10)

    # Edit file on disk to factor=5
    time.sleep(0.01)
    src_file.write_text("operation=multiply\nfactor=5\n", encoding="utf-8")

    src_reloaded = SourceFile.from_file(src_file, real_mode=True)
    decision_robust, _ = runtime.check_staleness(src_reloaded, RobustInvalidator())

    assert decision_robust.is_stale
    assert not decision_robust.hash_match


def test_real_file_collision_via_utime_reproduces_bug_on_real_disk(tmp_path):
    src_file = tmp_path / "calc.src"
    src_file.write_text("operation=multiply\nfactor=2\n", encoding="utf-8")

    cache_dir = tmp_path / "test_cache"
    store = CacheStore(cache_dir=cache_dir)
    runtime = Runtime(cache_store=store)

    src = SourceFile.from_file(src_file, real_mode=True)
    runtime.execute(src, RobustInvalidator(), input_value=10)
    cached_entry = store.load(src.path)
    assert cached_entry is not None

    # Mutate file content on real disk
    src_file.write_text("operation=multiply\nfactor=9\n", encoding="utf-8")

    # Set real filesystem mtime back to cached_mtime (simulating resolution window collision on real disk)
    os.utime(src_file, (cached_entry.cached_mtime, cached_entry.cached_mtime))

    src_collided = SourceFile.from_file(src_file, real_mode=True)
    decision_naive, _ = runtime.check_staleness(src_collided, NaiveInvalidator())
    decision_robust, _ = runtime.check_staleness(src_collided, RobustInvalidator())

    # Naive validator is fooled on real disk!
    assert not decision_naive.is_stale
    assert decision_naive.timestamp_match

    # Robust validator detects change via content hash!
    assert decision_robust.is_stale
    assert not decision_robust.hash_match
    assert "Content hash mismatch" in decision_robust.reason
    assert "resolution window collision" in decision_robust.reason


def test_missing_file_produces_clean_error(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["check", "totally_missing_file.src"])
    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "Error: Source file 'totally_missing_file.src' does not exist." in captured.err
    assert "Traceback" not in captured.err


def test_malformed_dsl_produces_clean_error(tmp_path, capsys):
    bad_file = tmp_path / "syntax_error.src"
    bad_file.write_text("random_garbage_not_dsl\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["check", str(bad_file)])
    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "Error: Malformed DSL" in captured.err
    assert "Traceback" not in captured.err


def test_cli_build_and_check_end_to_end(tmp_path, capsys):
    src_file = tmp_path / "prog.src"
    src_file.write_text("operation=multiply\nfactor=6\n", encoding="utf-8")
    cache_dir = tmp_path / "cli_cache"

    # 1. Build
    build_code = cli.main(["build", str(src_file), "--input", "10", "--cache-dir", str(cache_dir)])
    assert build_code == 0
    out_build = capsys.readouterr().out
    assert "Output Result : 60" in out_build

    # 2. Check
    check_code = cli.main(["check", str(src_file), "--cache-dir", str(cache_dir)])
    assert check_code == 0
    out_check = capsys.readouterr().out
    assert "VALID CACHE (HIT)" in out_check
    assert "Cache is valid and up to date" in out_check


def test_cli_clean_subcommand(tmp_path, capsys):
    src_file = tmp_path / "prog.src"
    src_file.write_text("operation=multiply\nfactor=2\n", encoding="utf-8")
    cache_dir = tmp_path / "clean_cache"

    cli.main(["build", str(src_file), "--cache-dir", str(cache_dir)])
    assert any(cache_dir.glob("*.json"))

    # Clean
    code = cli.main(["clean", "--cache-dir", str(cache_dir)])
    assert code == 0
    assert not any(cache_dir.glob("*.json"))


def test_cli_demo_command(capsys):
    code = cli.main(["demo"])
    assert code == 0
    out = capsys.readouterr().out
    assert "STALEBYTE — Compiled Cache Staleness Detection Demo" in out
    assert "SCENARIO 1" in out
    assert "SCENARIO 2" in out


def test_cli_check_directory_end_to_end(tmp_path, capsys):
    src_dir = tmp_path / "project_src"
    src_dir.mkdir()
    f1 = src_dir / "f1.src"
    f2 = src_dir / "f2.src"
    f1.write_text("operation=multiply\nfactor=3\n", encoding="utf-8")
    f2.write_text("operation=multiply\nfactor=4\n", encoding="utf-8")
    cache_dir = tmp_path / "dir_cache"

    # Before build -> check directory reports no baseline -> exit 0 with notice
    code_before = cli.main(["check", str(src_dir), "--cache-dir", str(cache_dir)])
    assert code_before == 0
    assert "no baseline established" in capsys.readouterr().out

    # Build both files
    assert cli.main(["build", str(f1), "--cache-dir", str(cache_dir)]) == 0
    assert cli.main(["build", str(f2), "--cache-dir", str(cache_dir)]) == 0
    capsys.readouterr()

    # After build -> check directory reports fresh -> exit 0
    code_after = cli.main(["check", str(src_dir), "--cache-dir", str(cache_dir)])
    assert code_after == 0
    out_after = capsys.readouterr().out
    assert "f1.src" in out_after
    assert "f2.src" in out_after
    assert "VALID CACHE (HIT)" in out_after

    # Mutate f1 -> check directory reports staleness -> exit 1
    f1.write_text("operation=multiply\nfactor=9\n", encoding="utf-8")
    code_mutated = cli.main(["check", str(src_dir), "--cache-dir", str(cache_dir)])
    assert code_mutated == 1


def test_pre_commit_hooks_yaml_manifest():
    manifest_path = Path(__file__).parent.parent / ".pre-commit-hooks.yaml"
    assert manifest_path.exists(), ".pre-commit-hooks.yaml must exist at repo root"
    content = manifest_path.read_text(encoding="utf-8")

    import yaml
    hooks = yaml.safe_load(content)
    assert isinstance(hooks, list)
    hook_ids = {h["id"]: h for h in hooks}
    assert "stalebyte-check" in hook_ids

    hook = hook_ids["stalebyte-check"]
    assert "stalebyte check ." in hook["entry"]
    assert hook.get("language") == "python"
    assert hook.get("pass_filenames") is False


def test_demo_reset_command(tmp_path):
    import demo
    cache_dir = tmp_path / "test_cache"
    cache_dir.mkdir()
    (cache_dir / "artifact.json").write_text("{}", encoding="utf-8")
    (cache_dir / ".gitkeep").write_text("", encoding="utf-8")
    uploads_dir = cache_dir / "uploads"
    uploads_dir.mkdir()
    (uploads_dir / "upload_artifact.json").write_text("{}", encoding="utf-8")

    code = demo.reset_demo_cache(cache_dir_path=cache_dir)
    assert code == 0
    assert not (cache_dir / "artifact.json").exists()
    assert not (uploads_dir / "upload_artifact.json").exists()
    assert (cache_dir / ".gitkeep").exists()


def test_demo_main_reset(monkeypatch):
    import demo
    monkeypatch.setattr(demo, "reset_demo_cache", lambda *args, **kwargs: 0)
    code = demo.main(["--reset"])
    assert code == 0

