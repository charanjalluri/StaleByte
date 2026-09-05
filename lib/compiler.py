"""
compiler.py
-----------
Parses the controlled key=value source format and produces a deterministic
JSON artifact.  No arbitrary code is executed.
"""

from __future__ import annotations

from typing import Any

VALID_OPERATIONS = {"multiply"}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_source(content: str) -> dict[str, Any]:
    """
    Parse a key=value source string into a dict.

    Rules
    -----
    * Lines starting with '#' are comments and are ignored.
    * Blank lines are ignored.
    * Each data line must contain exactly one '=' character.
    * Duplicate keys raise ValueError.
    """
    result: dict[str, str] = {}
    for lineno, raw in enumerate(content.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Line {lineno}: missing '=' separator → {raw!r}")
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key in result:
            raise ValueError(f"Line {lineno}: duplicate key {key!r}")
        result[key] = value
    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(parsed: dict[str, Any]) -> tuple[str, int]:
    """
    Validate parsed source and return (operation, factor).

    Raises
    ------
    ValueError  if required keys are missing or values are out of range.
    """
    if "operation" not in parsed:
        raise ValueError("Source missing required key: 'operation'")
    if "factor" not in parsed:
        raise ValueError("Source missing required key: 'factor'")

    operation = parsed["operation"]
    if operation not in VALID_OPERATIONS:
        raise ValueError(
            f"Unsupported operation {operation!r}. "
            f"Allowed: {sorted(VALID_OPERATIONS)}"
        )

    try:
        factor = int(parsed["factor"])
    except ValueError:
        raise ValueError(
            f"'factor' must be an integer, got {parsed['factor']!r}"
        )

    if factor <= 0:
        raise ValueError(f"'factor' must be positive, got {factor}")

    return operation, factor


# ---------------------------------------------------------------------------
# Artifact generation
# ---------------------------------------------------------------------------

def compile_source(content: str) -> dict[str, Any]:
    """
    Compile *content* into a deterministic artifact dict.

    The artifact encodes the operation and factor so the runtime can execute
    it without re-parsing the source.
    """
    parsed = parse_source(content)
    operation, factor = validate(parsed)
    artifact = {
        "operation": operation,
        "factor": factor,
        "bytecode": _generate_bytecode(operation, factor),
    }
    return artifact


def _generate_bytecode(operation: str, factor: int) -> list[str]:
    """
    Produce a deterministic, human-readable 'bytecode' list.

    This toy bytecode is just a stable representation; it is not executed
    as real code — the runtime interprets it directly.
    """
    if operation == "multiply":
        return ["LOAD_INPUT", f"PUSH {factor}", "MUL", "RETURN"]
    raise ValueError(f"No bytecode template for operation {operation!r}")


# ---------------------------------------------------------------------------
# Bytecode execution (interpreter — no eval/exec)
# ---------------------------------------------------------------------------

def execute_artifact(artifact: dict[str, Any], input_value: int) -> int:
    """
    Interpret the artifact's bytecode against *input_value*.

    Supported instructions
    ----------------------
    LOAD_INPUT   – push input_value onto the stack
    PUSH <n>     – push integer n onto the stack
    MUL          – pop two values, push their product
    RETURN       – pop top of stack and return it
    """
    stack: list[int] = []
    for instruction in artifact["bytecode"]:
        parts = instruction.split()
        op = parts[0]
        if op == "LOAD_INPUT":
            stack.append(input_value)
        elif op == "PUSH":
            stack.append(int(parts[1]))
        elif op == "MUL":
            if len(stack) < 2:
                raise RuntimeError("MUL requires two stack values")
            b = stack.pop()
            a = stack.pop()
            stack.append(a * b)
        elif op == "RETURN":
            if not stack:
                raise RuntimeError("RETURN on empty stack")
            return stack.pop()
        else:
            raise RuntimeError(f"Unknown instruction: {instruction!r}")
    raise RuntimeError("Artifact bytecode terminated without RETURN")
