"""Calificación de respuestas.

Vive en el paquete público, no en la plataforma, para que el servidor y la CLI apliquen
literalmente las mismas reglas. Una vista previa que califique distinto que el servidor es
peor que no tener vista previa.

Las soluciones que llegan aquí ya deben venir **resueltas** con los valores de la variante del
estudiante: este módulo no conoce plantillas. Se le pasa el registro de solución que produjo
``build`` —``{"solution": ..., "correct": [...], "answers": {...}}``— o, para pruebas rápidas
sobre el ítem fuente, el valor de la solución a secas.
"""

from __future__ import annotations

from typing import Any

from . import choices, expression as expr, numbers
from .result import Result
from ..points import question_points

__all__ = ["Result", "grade", "GRADERS", "choices", "numbers", "expr"]

RECORD_KEYS = {"solution", "correct", "answers", "grading"}


def grade(
    question: dict,
    response: Any,
    *,
    solution: Any = None,
    seed: int = 0,
    decimal_input: str = "both",
) -> Result:
    """Califica una respuesta y devuelve el resultado escalado a los puntos de la pregunta."""
    kind = question.get("type")
    points = question_points(question)

    if solution is None and "solution" in question:
        solution = question["solution"]
    record = _as_record(solution)

    handler = GRADERS.get(kind)
    if handler is None:
        return Result.invalid(f"Tipo de pregunta no calificable: {kind!r}")

    return handler(question, response, record, seed, decimal_input).scaled(points)


def _as_record(solution: Any) -> dict:
    """Acepta tanto el registro completo de `build` como el valor pelado."""
    if isinstance(solution, dict) and RECORD_KEYS & set(solution):
        return solution
    return {"solution": solution}


def _presented_options(question: dict, record: dict, seed: int) -> list[dict]:
    """Opciones tal como se le mostraron al estudiante, con la marca de correcta.

    Una variante ya materializada trae sus opciones con ``key`` y sin ``correct`` —las
    respuestas viajan aparte—, así que la marca se reconstruye desde el registro. Recalcular
    la presentación desde el ítem fuente daría claves distintas si el ítem se editó después,
    que es justo lo que la inmutabilidad de la capa 2 existe para impedir.
    """
    options = question.get("options") or []
    if options and all(isinstance(o, dict) and "key" in o for o in options):
        correct = set(record.get("correct") or [])
        return [{**option, "correct": option["key"] in correct} for option in options]
    return choices.present_options(question, seed)


def _presented_statements(question: dict, record: dict, seed: int) -> list[dict]:
    statements = question.get("statements") or []
    if statements and all(isinstance(s, dict) and "key" in s for s in statements):
        answers = record.get("answers") or {}
        return [{**s, "answer": answers.get(s["key"])} for s in statements]
    return choices.present_statements(question, seed)


def _numeric(question, response, record, seed, decimal_input):
    return numbers.grade_numeric(question, response, record.get("solution"), decimal_input)


def _numeric_list(question, response, record, seed, decimal_input):
    return numbers.grade_numeric_list(question, response, record.get("solution"), decimal_input)


def _expression(question, response, record, seed, decimal_input):
    grading = question.get("grading") or {}
    variables = set(grading.get("vars") or [])
    allow = grading.get("allow")
    allow = set(allow) if allow is not None else None

    try:
        student = expr.parse(response, variables, allow)
    except expr.FormatError as exc:
        return Result.invalid(str(exc))

    try:
        reference = expr.parse(str(record.get("solution")), variables, allow)
    except expr.FormatError as exc:
        return Result.invalid(f"Solución mal formada: {exc}")

    domain = {k: tuple(v) for k, v in (grading.get("domain") or {}).items()}
    ok = expr.equivalent(
        student,
        reference,
        domain=domain,
        samples=int(grading.get("sample_points", 20)),
        rtol=float(grading.get("rtol", 1e-6)),
        seed=seed,
    )
    return Result(fraction=1.0 if ok else 0.0, correct=ok, detail={"value": student.source})


def _choice(question, response, record, seed, decimal_input):
    return choices.grade_choice(question, response, _presented_options(question, record, seed))


def _multi_choice(question, response, record, seed, decimal_input):
    return choices.grade_multi_choice(question, response, _presented_options(question, record, seed))


def _true_false(question, response, record, seed, decimal_input):
    return choices.grade_true_false(question, response, _presented_statements(question, record, seed))


def _text(question, response, record, seed, decimal_input):
    accept = (record.get("grading") or {}).get("accept")
    if accept and not (question.get("grading") or {}).get("accept"):
        question = {**question, "grading": {**(question.get("grading") or {}), "accept": accept}}
    return choices.grade_text(question, response)


def _open(question, response, record, seed, decimal_input):
    """Nunca produce una nota por sí solo.

    ``review: required`` es el valor por defecto y no se puede desactivar globalmente: tanto
    la calificación manual como la propuesta por IA pasan por una persona.
    """
    empty = response is None or not str(response).strip()
    return Result(
        fraction=0.0,
        correct=False,
        needs_review=not empty,
        detail={"value": response, "mode": (question.get("grading") or {}).get("mode", "manual")},
    )


GRADERS = {
    "numeric": _numeric,
    "numeric_list": _numeric_list,
    "expression": _expression,
    "choice": _choice,
    "multi_choice": _multi_choice,
    "true_false": _true_false,
    "text": _text,
    "open": _open,
}
