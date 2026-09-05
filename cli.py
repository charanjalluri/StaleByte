"""
cli.py
------
Production-ready Command Line Interface for StaleByte.

Enables checking and building real files on disk with real filesystem mtimes
and SHA-256 content hashes, while providing an explicit --demo mode for scripted
timestamp collision and clock skew simulations.

Commands:
    python cli.py check <path> [--demo]
    python cli.py build <path> [--input <val>] [--demo]
    python cli.py demo
    python cli.py clean [<path>]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import NoReturn

from cache import CacheStore
from clock import VirtualClock
from invalidators import NaiveInvalidator, RobustInvalidator
from lib import compiler
from runtime import Runtime
from source import SourceFile


def _print_error(message: str) -> None:
    """Print a clean, user-facing error message to stderr."""
    print(f"Error: {message}", file=sys.stderr)


def _load_source_file(path_str: str, real_mode: bool = True) -> SourceFile:
    """
    Safely load a SourceFile, producing user-friendly errors without stack traces.
    """
    path = Path(path_str).resolve()
    if not path.exists():
        _print_error(f"Source file '{path_str}' does not exist.")
        sys.exit(1)

    if path.is_dir():
        _print_error(f"Target path '{path_str}' is a directory, not a source file.")
        sys.exit(1)

    try:
        source = SourceFile.from_file(path, real_mode=real_mode)
    except PermissionError:
        _print_error(f"Cannot read source file '{path_str}': Permission denied.")
        sys.exit(1)
    except Exception as exc:
        _print_error(f"Failed to read source file '{path_str}': {exc}")
        sys.exit(1)

    # Validate DSL syntax
    try:
        compiler.compile_source(source.content)
    except ValueError as val_err:
        _print_error(
            f"Malformed DSL in '{path_str}': {val_err}. "
            "Expected format: 'operation=multiply\\nfactor=<int>'."
        )
        sys.exit(1)

    return source


def cmd_check(args: argparse.Namespace) -> int:
    """Run Naive and Robust staleness checks on a source file."""
    real_mode = not args.demo
    source = _load_source_file(args.path, real_mode=real_mode)
    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    store = CacheStore(cache_dir=cache_dir)
    runtime = Runtime(cache_store=store)

    naive_decision, cached_entry = runtime.check_staleness(source, NaiveInvalidator())
    robust_decision, _ = runtime.check_staleness(source, RobustInvalidator())

    mode_label = "SIMULATED (VirtualClock)" if args.demo else "REAL FILESYSTEM (os.stat)"

    print("=" * 72)
    print(f"StaleByte Staleness Inspection [{mode_label}]")
    print("=" * 72)
    print(f"Source File   : {source.path}")
    print(f"Size          : {source.size} bytes")
    print(f"mtime         : {source.mtime:.6f}s")
    print(f"SHA-256 Hash  : {source.content_hash}")

    print("\n--- Cache State ---")
    if cached_entry is None:
        print("Status        : No cached artifact found on disk.")
        print("Recommendation: Run `python cli.py build <path>` to build and populate cache.")
        print("=" * 72)
        return 0

    print(f"Cached At (t) : {cached_entry.cached_mtime:.6f}s")
    print(f"Cached Hash   : {cached_entry.content_hash}")
    print(f"Build ID      : {cached_entry.build_id}")
    print(f"Build Count   : #{cached_entry.build_counter} (Version: {cached_entry.version_label})")

    print("\n--- Validation Decisions ---")
    print("[NAIVE INVALIDATOR (mtime <= t_cache)]:")
    naive_verdict = "VALID CACHE (HIT)" if not naive_decision.is_stale else "STALE (MISS)"
    print(f"  Decision : {naive_verdict}")
    print(f"  Reason   : {naive_decision.reason}")

    print("\n[ROBUST INVALIDATOR (SHA-256 + mtime)]:")
    robust_verdict = "VALID CACHE (HIT)" if not robust_decision.is_stale else "STALE (MISS / REBUILD NEEDED)"
    print(f"  Decision : {robust_verdict}")
    print(f"  Reason   : {robust_decision.reason}")

    # Divergence Analysis
    print("\n--- Diagnostic Verdict ---")
    if not naive_decision.is_stale and robust_decision.is_stale:
        print("🚨 CRITICAL BUG DETECTED: SILENT RUNTIME MISMATCH")
        print("   The Naive invalidator falsely accepted a stale cache because timestamps match.")
        print("   The Robust invalidator detected content change via SHA-256 and triggered invalidation.")
    elif naive_decision.is_stale == robust_decision.is_stale:
        if not naive_decision.is_stale:
            print("✓ PASS: Cache is valid and up to date.")
        else:
            print("✓ PASS: Cache is genuinely stale; rebuild required.")
    else:
        print("Notice: Validators diverged.")

    print("=" * 72)
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """Build and execute source file, updating persistent cache."""
    real_mode = not args.demo
    source = _load_source_file(args.path, real_mode=real_mode)
    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    store = CacheStore(cache_dir=cache_dir)
    runtime = Runtime(cache_store=store)

    mode_label = "SIMULATED (VirtualClock)" if args.demo else "REAL FILESYSTEM (os.stat)"

    print("=" * 72)
    print(f"StaleByte Build & Execute [{mode_label}]")
    print("=" * 72)
    print(f"Source File   : {source.path}")
    print(f"Input Value   : {args.input}")

    res = runtime.execute(source, RobustInvalidator(), input_value=args.input)

    status_str = "CACHE HIT (Reused cached artifact)" if res.cache_hit else (
        "CACHE MISS -> REBUILT" if res.rebuilt else "INITIAL BUILD"
    )

    print(f"Build Action  : {status_str}")
    print(f"Output Result : {res.output}")
    print(f"Artifact Hash : {source.content_hash[:16]}...")
    print(f"Reason        : {res.decision.reason}")
    print("=" * 72)
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Run scripted demo scenarios from demo.py."""
    import demo
    demo.main()
    return 0


def cmd_fuzz(args: argparse.Namespace) -> int:
    """Run randomized fuzzing & statistical validation suite."""
    import fuzz
    summary = fuzz.run_fuzz_suite(trials=args.trials, seed=args.seed)
    if args.json:
        import json
        print(json.dumps(summary.to_dict(), indent=2))
    else:
        print(fuzz.format_summary_report(summary))
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    """Invalidate cache store."""
    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    store = CacheStore(cache_dir=cache_dir)

    if args.path:
        source_path = str(Path(args.path).resolve())
        store.invalidate(source_path=source_path)
        print(f"Cache cleared for '{args.path}'.")
    else:
        store.invalidate()
        # Clean any path-keyed artifacts in cache_dir
        for p in store.cache_dir.glob("*.json"):
            try:
                p.unlink()
            except OSError:
                pass
        print(f"All cache artifacts cleared from '{store.cache_dir}'.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="stalebyte",
        description="StaleByte — Compiled Cache Staleness Verification & Build Tool",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use simulated VirtualClock mode instead of real filesystem mtime/reads",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="Custom cache directory path (defaults to ./cache)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # check subcommand
    check_parser = subparsers.add_parser("check", help="Inspect cache staleness for a source file")
    check_parser.add_argument("path", type=str, help="Path to .src source file")
    check_parser.add_argument("--demo", action="store_true", help="Use simulated clock mode")
    check_parser.add_argument("--cache-dir", type=str, default=None, help="Custom cache directory")

    # build subcommand
    build_parser = subparsers.add_parser("build", help="Compile and execute source file with cache")
    build_parser.add_argument("path", type=str, help="Path to .src source file")
    build_parser.add_argument("--input", type=int, default=10, help="Input value to pass to artifact (default: 10)")
    build_parser.add_argument("--demo", action="store_true", help="Use simulated clock mode")
    build_parser.add_argument("--cache-dir", type=str, default=None, help="Custom cache directory")

    # fuzz subcommand
    fuzz_parser = subparsers.add_parser("fuzz", help="Run randomized fuzzing and statistical validation")
    fuzz_parser.add_argument("-n", "--trials", type=int, default=10000, help="Number of trials (default: 10,000)")
    fuzz_parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible results")
    fuzz_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # demo subcommand
    subparsers.add_parser("demo", help="Run scripted resolution collision & clock skew demos")

    # clean subcommand
    clean_parser = subparsers.add_parser("clean", help="Clear cache artifacts")
    clean_parser.add_argument("path", nargs="?", type=str, default=None, help="Specific file path to clear (optional)")
    clean_parser.add_argument("--cache-dir", type=str, default=None, help="Custom cache directory")

    args = parser.parse_args(argv)

    # Handle top-level --demo flag without subcommand
    if args.demo and not args.command:
        return cmd_demo(args)

    if args.command == "check":
        return cmd_check(args)
    elif args.command == "build":
        return cmd_build(args)
    elif args.command == "fuzz":
        return cmd_fuzz(args)
    elif args.command == "demo":
        return cmd_demo(args)
    elif args.command == "clean":
        return cmd_clean(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
