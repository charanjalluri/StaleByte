"""
test_compiler.py
----------------
Direct unit tests for lib/compiler.py covering DSL parsing,
validation edge cases, bytecode generation, and interpreter boundaries.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.compiler import compile_source, execute_artifact, parse_source, validate


def test_compile_valid_source():
    """Valid source compiles to expected artifact with deterministic bytecode."""
    content = "operation=multiply\nfactor=4\n"
    artifact = compile_source(content)
    assert artifact["operation"] == "multiply"
    assert artifact["factor"] == 4
    assert artifact["bytecode"] == ["LOAD_INPUT", "PUSH 4", "MUL", "RETURN"]


def test_parse_source_handles_comments_and_blank_lines():
    """Comments and blank lines are ignored cleanly during parsing."""
    content = """
    # This is a comment
    operation=multiply

    # Another comment
    factor=5
    """
    parsed = parse_source(content)
    assert parsed == {"operation": "multiply", "factor": "5"}


def test_parse_source_missing_equals_raises():
    """Line without '=' separator raises ValueError."""
    content = "operation=multiply\ninvalid_line_without_equals\n"
    with pytest.raises(ValueError, match="missing '=' separator"):
        parse_source(content)


def test_parse_source_duplicate_key_raises():
    """Duplicate keys in source raise ValueError."""
    content = "operation=multiply\nfactor=2\nfactor=3\n"
    with pytest.raises(ValueError, match="duplicate key 'factor'"):
        parse_source(content)


def test_validate_missing_operation_raises():
    """Validation fails if 'operation' key is missing."""
    with pytest.raises(ValueError, match="missing required key: 'operation'"):
        validate({"factor": "2"})


def test_validate_missing_factor_raises():
    """Validation fails if 'factor' key is missing."""
    with pytest.raises(ValueError, match="missing required key: 'factor'"):
        validate({"operation": "multiply"})


def test_validate_unsupported_operation_raises():
    """Validation rejects unknown or unsupported operations."""
    with pytest.raises(ValueError, match="Unsupported operation 'divide'"):
        validate({"operation": "divide", "factor": "2"})


def test_validate_non_integer_factor_raises():
    """Validation rejects non-integer factor values."""
    with pytest.raises(ValueError, match="'factor' must be an integer"):
        validate({"operation": "multiply", "factor": "two"})


def test_validate_non_positive_factor_raises():
    """Validation rejects zero or negative factor values."""
    with pytest.raises(ValueError, match="'factor' must be positive"):
        validate({"operation": "multiply", "factor": "0"})
    with pytest.raises(ValueError, match="'factor' must be positive"):
        validate({"operation": "multiply", "factor": "-3"})


def test_execute_artifact_multiplication():
    """Bytecode interpreter correctly multiplies input by factor."""
    artifact = {
        "operation": "multiply",
        "factor": 7,
        "bytecode": ["LOAD_INPUT", "PUSH 7", "MUL", "RETURN"],
    }
    result = execute_artifact(artifact, 10)
    assert result == 70


def test_execute_artifact_mul_stack_underflow_raises():
    """MUL instruction with fewer than two values on stack raises RuntimeError."""
    artifact = {
        "operation": "multiply",
        "factor": 2,
        "bytecode": ["LOAD_INPUT", "MUL", "RETURN"],
    }
    with pytest.raises(RuntimeError, match="MUL requires two stack values"):
        execute_artifact(artifact, 10)


def test_execute_artifact_return_on_empty_stack_raises():
    """RETURN instruction on an empty stack raises RuntimeError."""
    artifact = {
        "operation": "multiply",
        "factor": 2,
        "bytecode": ["RETURN"],
    }
    with pytest.raises(RuntimeError, match="RETURN on empty stack"):
        execute_artifact(artifact, 10)


def test_execute_artifact_missing_return_raises():
    """Bytecode sequence terminating without RETURN raises RuntimeError."""
    artifact = {
        "operation": "multiply",
        "factor": 2,
        "bytecode": ["LOAD_INPUT", "PUSH 2"],
    }
    with pytest.raises(RuntimeError, match="terminated without RETURN"):
        execute_artifact(artifact, 10)


def test_execute_artifact_unknown_instruction_raises():
    """Interpreter raises RuntimeError on unrecognized instructions."""
    artifact = {
        "operation": "multiply",
        "factor": 2,
        "bytecode": ["NOOP", "RETURN"],
    }
    with pytest.raises(RuntimeError, match="Unknown instruction"):
        execute_artifact(artifact, 10)
