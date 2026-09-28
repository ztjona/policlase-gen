"""Calificadores numéricos: ``numeric`` y ``numeric_list`` (docs/schema.md §8)."""

from __future__ import annotations

import math
import re
from typing import Any

from .result import Result

DEFAULT_NAN_ALIASES = ("nan", "no existe", "no hay", "-", "—", "ninguna")

_NUMBER = re.compile(r"^[+-]?(\d+([.,]\d*)?|[.,]\d+)([eE][+-]?\d+)?$")


class ParseError(ValueError):
    """Texto que no es un número; el mensaje se le muestra al estudiante."""


def parse_number(text: Any, decimal_input: str = "both") -> float | None:
    """Convierte la entrada del estudiante en un número, o ``None`` para NaN.

    ``decimal_input='both'`` acepta ``4.23`` y ``4,23``. Solo es seguro porque las listas
    numéricas usan una casilla por celda: en un campo separado por comas, ``1,234`` sería
    ambiguo entre un número y dos.
    """
    if text is None:
        return None
    if isinstance(text, bool):
        raise ParseError("Se esperaba un número.")
    if isinstance(text, (int, float)):
        value = float(text)
        return None if math.isnan(value) else value

    raw = str(text).strip()
    if not raw:
        raise ParseError("La casilla está vacía.")
    if raw.casefold() in {a.casefold() for a in DEFAULT_NAN_ALIASES}:
        return None

    candidate = raw
    if decimal_input in ("both", "comma"):
        if "," in candidate and "." in candidate:
            # "1.234,56" -> separador de miles a la izquierda de la coma decimal.
            candidate = candidate.replace(".", "").replace(",", ".")
        elif "," in candidate:
            candidate = candidate.replace(",", ".")
    elif "," in candidate:
        raise ParseError("Use el punto como separador decimal.")

    if not _NUMBER.match(candidate):
        raise ParseError(f"{raw!r} no es un número.")
    try:
        return float(candidate)
    except ValueError as exc:                     # pragma: no cover - lo cubre el regex
        raise ParseError(f"{raw!r} no es un número.") from exc


def close(student: float | None, reference: float | None, grading: dict) -> bool:
    """Compara con la tolerancia declarada.

    ``|a-b| <= atol + rtol*|b|``. Declarar solo ``rtol`` hace que toda respuesta cercana a
    cero falle, que es el error más común al escribir tolerancias, y por eso ``atol`` tiene
    un valor por defecto distinto de cero.
    """
    if student is None or reference is None:
        return student is None and reference is None
    if grading.get("integer"):
        return abs(student - round(student)) < 1e-9 and round(student) == round(reference)
    rtol = float(grading.get("rtol", 0.0) or 0.0)
    atol = float(grading.get("atol", 1e-9) or 0.0)
    return abs(student - reference) <= atol + rtol * abs(reference)


def grade_numeric(question: dict, response: Any, solution: Any, decimal_input: str = "both") -> Result:
    grading = question.get("grading") or {}
    try:
        value = parse_number(response, decimal_input)
    except ParseError as exc:
        return Result.invalid(str(exc))

    try:
        expected = parse_number(solution, decimal_input)
    except ParseError as exc:                      # pragma: no cover - lo atrapa el validador
        return Result.invalid(f"Solución mal formada: {exc}")

    ok = close(value, expected, grading)
    return Result(fraction=1.0 if ok else 0.0, correct=ok,
                  detail={"value": value, "expected": expected})


def grade_numeric_list(question: dict, response: Any, solution: Any, decimal_input: str = "both") -> Result:
    grading = question.get("grading") or {}
    expected_cells = _flatten(solution)

    if not isinstance(response, (list, tuple)):
        return Result.invalid("Se esperaba una lista de valores.")
    given = _flatten(response)
    if len(given) != len(expected_cells):
        return Result.invalid(
            f"Se esperaban {len(expected_cells)} valores y se recibieron {len(given)}."
        )

    errors, student_values = [], []
    for index, raw in enumerate(given):
        try:
            student_values.append(parse_number(raw, decimal_input))
        except ParseError as exc:
            errors.append(f"Casilla {index + 1}: {exc}")
    if errors:
        return Result.invalid(" ".join(errors))

    expected_values = [parse_number(v, decimal_input) for v in expected_cells]

    order = (grading.get("order") or "exact").lower()
    if order in ("ascending", "sorted", "descending", "any"):
        student_values = _ordered(student_values, order)
        expected_values = _ordered(expected_values, order)

    matches = [close(a, b, grading) for a, b in zip(student_values, expected_values)]
    hits = sum(matches)

    if (grading.get("partial") or "per_cell") == "per_cell":
        fraction = hits / len(matches) if matches else 0.0
    else:
        fraction = 1.0 if all(matches) else 0.0

    return Result(
        fraction=fraction,
        correct=all(matches),
        detail={"cells": matches, "value": student_values, "expected": expected_values},
    )


def _ordered(values: list[float | None], order: str) -> list[float | None]:
    """Ordena dejando los NaN (``None``) al final, donde el enunciado los pide."""
    numbers = sorted(v for v in values if v is not None)
    if order == "descending":
        numbers.reverse()
    return numbers + [None] * (len(values) - len(numbers))


def _flatten(value: Any) -> list[Any]:
    if not isinstance(value, (list, tuple)):
        return [value]
    out: list[Any] = []
    for item in value:
        out.extend(_flatten(item)) if isinstance(item, (list, tuple)) else out.append(item)
    return out
