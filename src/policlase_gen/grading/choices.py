"""Calificadores de selección y texto: ``choice``, ``multi_choice``, ``true_false``, ``text``."""

from __future__ import annotations

import hashlib
import random
import unicodedata
from typing import Any

from .result import Result

NONE_OF_THE_ABOVE = "Ninguna de las anteriores"


# ------------------------------------------------------------------ presentación


def present_options(question: dict, seed: int) -> list[dict]:
    """Devuelve las opciones tal como las ve el estudiante, de forma determinista.

    ``none_of_the_above`` es un caso especial de la plataforma: se añade siempre y se ancla
    al final, nunca entra en la mezcla.
    """
    options = [dict(o) for o in (question.get("options") or [])]
    sample = question.get("sample") or {}
    rng = random.Random(f"{question.get('id', '')}:{seed}")

    correct = [o for o in options if o.get("correct")]
    distractors = [o for o in options if not o.get("correct")]

    limit = sample.get("distractors")
    if isinstance(limit, int) and 0 <= limit < len(distractors):
        distractors = rng.sample(distractors, limit)

    shown = correct + distractors
    if sample.get("shuffle", "seeded") != "none":
        rng.shuffle(shown)

    nota = question.get("none_of_the_above")
    if nota:
        text = NONE_OF_THE_ABOVE if nota is True else (nota.get("text") or NONE_OF_THE_ABOVE)
        is_correct = isinstance(nota, dict) and bool(nota.get("correct"))
        shown.append({"text": text, "correct": is_correct, "pinned": True})

    for index, option in enumerate(shown):
        option["key"] = _key(option["text"], index)
    return shown


def _key(text: str, index: int) -> str:
    """Identificador estable de una opción, independiente de su posición."""
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"o{index}_{digest}"


# ------------------------------------------------------------------ calificadores


def grade_choice(question: dict, response: Any, options: list[dict] | None = None) -> Result:
    options = options if options is not None else present_options(question, seed=0)
    if response is None or response == "":
        return Result.invalid("No se seleccionó ninguna opción.")

    chosen = _match(options, response)
    if chosen is None:
        return Result.invalid("La opción seleccionada no existe.")

    ok = bool(chosen.get("correct"))
    return Result(fraction=1.0 if ok else 0.0, correct=ok,
                  detail={"chosen": chosen["text"]})


def grade_multi_choice(question: dict, response: Any, options: list[dict] | None = None) -> Result:
    """Crédito parcial con penalización.

    ``score = max(floor, (aciertos - penalty*errores) / total_correctas)``

    La penalización no es un adorno: con ``penalty: 0``, marcar todas las opciones da nota
    completa sin saber nada, y por eso el validador avisa (W071) cuando baja de 1.0.
    """
    grading = question.get("grading") or {}
    options = options if options is not None else present_options(question, seed=0)

    if response is None:
        response = []
    if not isinstance(response, (list, tuple, set)):
        return Result.invalid("Se esperaba una lista de opciones.")

    selected = []
    for item in response:
        found = _match(options, item)
        if found is None:
            return Result.invalid("Una de las opciones seleccionadas no existe.")
        selected.append(found)

    correct_options = [o for o in options if o.get("correct")]
    total_correct = len(correct_options)
    if total_correct == 0:                        # pragma: no cover - lo atrapa E048
        return Result.invalid("La pregunta no declara opciones correctas.")

    hits = sum(1 for o in selected if o.get("correct"))
    misses = len(selected) - hits

    if (grading.get("partial") or "per_option") == "all_or_nothing":
        fraction = 1.0 if hits == total_correct and misses == 0 else 0.0
    else:
        penalty = float(grading.get("penalty", 1.0))
        floor = float(grading.get("floor", 0.0))
        fraction = max(floor, (hits - penalty * misses) / total_correct)
        fraction = min(1.0, fraction)

    return Result(
        fraction=fraction,
        correct=hits == total_correct and misses == 0,
        detail={"hits": hits, "misses": misses, "selected": [o["text"] for o in selected]},
    )


def present_statements(question: dict, seed: int) -> list[dict]:
    statements = [dict(s) for s in (question.get("statements") or [])]
    if (question.get("sample") or {}).get("shuffle", "seeded") != "none":
        random.Random(f"{question.get('id', '')}:tf:{seed}").shuffle(statements)
    for index, statement in enumerate(statements):
        statement["key"] = _key(statement.get("text", ""), index)
    return statements


def grade_true_false(question: dict, response: Any, statements: list[dict] | None = None) -> Result:
    """Cada afirmación se marca verdadera o falsa.

    El azar da 50 % en este tipo, cosa que no ocurre en ``choice``. Con ``penalty: 1.0`` una
    respuesta al azar tiende a cero, que es el comportamiento deseable.
    """
    grading = question.get("grading") or {}
    statements = statements if statements is not None else present_statements(question, seed=0)

    if not isinstance(response, dict):
        return Result.invalid("Se esperaba una marca por afirmación.")

    marks, missing = [], 0
    for statement in statements:
        given = response.get(statement["key"], response.get(statement.get("text")))
        if given is None:
            missing += 1
            marks.append(False)
            continue
        marks.append(bool(given) == bool(statement.get("answer")))

    if missing == len(statements):
        return Result.invalid("No se marcó ninguna afirmación.")

    hits = sum(marks)
    total = len(marks)
    if total == 0:                                # pragma: no cover - lo atrapa el validador
        return Result.invalid("La pregunta no tiene afirmaciones.")

    if (grading.get("partial") or "per_statement") == "all_or_nothing":
        fraction = 1.0 if hits == total else 0.0
    else:
        penalty = float(grading.get("penalty", 1.0))
        floor = float(grading.get("floor", 0.0))
        fraction = max(floor, (hits - penalty * (total - hits)) / total)
        fraction = min(1.0, fraction)

    return Result(fraction=fraction, correct=hits == total,
                  detail={"marks": marks, "hits": hits, "total": total})


def normalize(text: str, rules: list[str] | None) -> str:
    out = str(text).strip()
    for rule in rules or []:
        if rule == "lowercase":
            out = out.casefold()
        elif rule == "strip_accents":
            out = "".join(
                c for c in unicodedata.normalize("NFD", out)
                if unicodedata.category(c) != "Mn"
            )
        elif rule == "collapse_spaces":
            out = " ".join(out.split())
        elif rule == "strip_punctuation":
            out = "".join(c for c in out if c.isalnum() or c.isspace())
    return out


def grade_text(question: dict, response: Any) -> Result:
    grading = question.get("grading") or {}
    rules = grading.get("normalize") or ["lowercase", "strip_accents", "collapse_spaces"]

    if response is None or str(response).strip() == "":
        return Result.invalid("La respuesta está vacía.")

    given = normalize(response, rules)
    accepted = {normalize(a, rules) for a in (grading.get("accept") or [])}
    ok = given in accepted
    return Result(fraction=1.0 if ok else 0.0, correct=ok, detail={"value": given})


def _match(options: list[dict], response: Any) -> dict | None:
    """Acepta la clave estable o, por comodidad en pruebas, el texto literal."""
    token = str(response)
    for option in options:
        if option.get("key") == token or option.get("text") == token:
            return option
    return None
