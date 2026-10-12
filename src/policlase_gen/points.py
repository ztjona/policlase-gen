"""Puntos por omisión: una pregunta sin `points` vale 1 (una encuesta, 0), y un ítem sin `points`
vale la suma de sus preguntas. Validación, build, calificación y presentaciones leen los puntos
solo por aquí."""

from __future__ import annotations

from typing import Any

DEFAULT_POINTS = 1.0


def is_survey(question: Any) -> bool:
    """Una encuesta (`grading.mode: survey`): se registra lo elegido, sin correcta ni puntos."""
    grading = question.get("grading") if isinstance(question, dict) else None
    return isinstance(grading, dict) and grading.get("mode") == "survey"


def question_points(question: Any) -> float:
    value = question.get("points") if isinstance(question, dict) else None
    if value is None:
        return 0.0 if is_survey(question) else DEFAULT_POINTS
    return float(value)


def item_points(item: Any) -> float:
    value = item.get("points") if isinstance(item, dict) else None
    if value is not None:
        return float(value)
    questions = item.get("questions") if isinstance(item, dict) else None
    return sum(question_points(q) for q in questions or [] if isinstance(q, dict))
