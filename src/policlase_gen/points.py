"""Puntos por omisión: una pregunta sin `points` vale 1, y un ítem sin `points` vale la suma de
sus preguntas. Validación, build, calificación y presentaciones leen los puntos solo por aquí."""

from __future__ import annotations

from typing import Any

DEFAULT_POINTS = 1.0


def question_points(question: Any) -> float:
    value = question.get("points") if isinstance(question, dict) else None
    return DEFAULT_POINTS if value is None else float(value)


def item_points(item: Any) -> float:
    value = item.get("points") if isinstance(item, dict) else None
    if value is not None:
        return float(value)
    questions = item.get("questions") if isinstance(item, dict) else None
    return sum(question_points(q) for q in questions or [] if isinstance(q, dict))
