"""Deterministic scoring (prereg section 6) and error categories.

No randomness, no model call, no network. The answer that is scored is the one
recorded after the final retry (mode C) or the single answer (modes A and B).
"""

from __future__ import annotations

import math
import re
from typing import Any

from bench.props import Property

ELEMENT_RE = re.compile(r"([A-Z][a-z]?)(\d*)")
FORMULA_RE = re.compile(r"(?:[A-Z][a-z]?\d*)+")


def parse_formula(text: str) -> dict[str, int] | None:
    """Parse a Hill-style formula into element counts, or None if malformed."""
    if not isinstance(text, str):
        return None
    value = text.strip()
    if not value or not FORMULA_RE.fullmatch(value):
        return None
    counts: dict[str, int] = {}
    for symbol, digits in ELEMENT_RE.findall(value):
        count = int(digits) if digits else 1
        counts[symbol] = counts.get(symbol, 0) + count
    return counts


def hill_normalize(counts: dict[str, int]) -> str:
    if "C" in counts:
        order = ["C"]
        if "H" in counts:
            order.append("H")
        order.extend(sorted(k for k in counts if k not in {"C", "H"}))
    else:
        order = sorted(counts)
    parts = []
    for symbol in order:
        count = counts[symbol]
        parts.append(symbol if count == 1 else f"{symbol}{count}")
    return "".join(parts)


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def is_valid_format(prop: Property, value: Any) -> bool:
    if prop.kind == "formula":
        return isinstance(value, str) and parse_formula(value) is not None
    return _as_number(value) is not None


def score_answer(prop: Property, answer: Any, reference: Any) -> dict:
    """Return ``{"correct": bool, "detail": str}`` for one answer."""
    if answer is None:
        return {"correct": False, "detail": "missing_answer"}

    if prop.kind == "formula":
        got = parse_formula(answer) if isinstance(answer, str) else None
        want = parse_formula(reference) if isinstance(reference, str) else None
        if got is None:
            return {"correct": False, "detail": "formula_unparseable"}
        if want is None:
            raise ValueError(f"reference formula unparseable: {reference!r}")
        return {
            "correct": got == want,
            "detail": f"got={hill_normalize(got)} want={hill_normalize(want)}",
        }

    number = _as_number(answer)
    if number is None:
        return {"correct": False, "detail": "not_a_number"}

    if prop.kind == "int":
        if not math.isfinite(number) or not float(number).is_integer():
            return {"correct": False, "detail": f"not_an_integer({answer!r})"}
        return {"correct": int(number) == int(reference), "detail": f"got={answer} want={reference}"}

    tolerance = prop.tolerance if prop.tolerance is not None else 0.0
    difference = abs(number - float(reference))
    return {
        "correct": difference <= tolerance + 1e-12,
        "detail": f"got={answer} want={reference} |diff|={difference:.6f} tol={tolerance}",
    }


def _ratio_is_unit_slip(answer: float, reference: float) -> bool:
    if reference == 0:
        return False
    ratio = answer / reference
    for factor in (1000.0, 0.001):
        if abs(ratio - factor) <= 1e-6 * factor:
            return True
    return False


def classify_error(
    *,
    mode: str,
    prop: Property,
    answer: Any,
    reference: Any,
    trace: list[dict],
) -> str:
    """Deterministic category from the tool trace first (prereg section 6)."""
    if answer is None:
        return "parse_failure"
    if not is_valid_format(prop, answer):
        return "parse_failure"
    if mode == "A":
        return "chemistry_knowledge_error"

    if not trace:
        return "no_tool_call"

    matching = [call for call in trace if call.get("canonical_match")]
    if not matching:
        return "bad_smiles_passed"

    property_calls = [call for call in matching if call.get("tool") == prop.key]
    number = _as_number(answer)
    if property_calls:
        tool_value = property_calls[-1].get("value")
        if number is not None and isinstance(tool_value, (int, float)):
            if _ratio_is_unit_slip(number, float(tool_value)):
                return "unit_error"
            return "arithmetic_error"
        if prop.kind == "formula":
            return "other"
        return "arithmetic_error"

    return "chemistry_knowledge_error"


PROCESS_CATEGORIES = frozenset(
    {"no_tool_call", "bad_smiles_passed", "parse_failure", "unit_error"}
)
