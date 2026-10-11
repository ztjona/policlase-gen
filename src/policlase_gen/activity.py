"""Actividades: deberes, talleres y evidencias (docs/schema.md §10).

Una actividad es un conjunto de ítems que cada estudiante resuelve a su paso, dentro de una
ventana de tiempo. A diferencia de una presentación, admite todos los tipos de pregunta —también
`open` y `expression`, que piden escribir con calma— y el tipo `image`, para entregar fotos
(evidencia, un certificado, el desarrollo a mano).

    schema: policlase.activity/v1
    title: 'Deber 3 — Newton-Raphson'
    instructions: |
      Resuelva a mano y suba la foto de su desarrollo.
    items:
      - id: D03-newton
        questions:
          - { id: q1, type: numeric, prompt: '...', solution: 1.4142, grading: { rtol: 0.001 } }
          - { id: q2, type: image, prompt: 'Foto del desarrollo', points: 2, max_files: 3 }

El archivo describe solo el contenido. Cuándo abre y vence, cuánto vale y qué pasa con lo
atrasado lo decide la plataforma: reprogramar una prueba no debe exigir un commit por deber, y
la misma actividad sirve otro semestre con otras fechas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import build, loader, template
from .errors import Report
from .points import question_points
from .validate import REVIEW_TYPES

ACTIVITY_VERSIONS = {"policlase.activity/v1"}
ACTIVITY_KEYS = {"schema", "title", "instructions", "items", "meta"}
COMPILED_SCHEMA = "policlase.activity.compiled/v1"


def is_activity(document: Any) -> bool:
    return isinstance(document, dict) and str(document.get("schema", "")).startswith("policlase.activity/")


def validate_activity(document: Any, *, path: Path | str = "<memoria>", report: Report | None = None) -> Report:
    from .validate import _validate_item       # diferido: validate importa este módulo

    report = report if report is not None else Report()
    path = Path(path)
    here = {"file": str(path)}

    if not isinstance(document, dict):
        report.add("E004", key="<raíz>", expected="mapping", found=type(document).__name__, **here)
        return report

    for key in set(document) - ACTIVITY_KEYS:
        report.add("E001", key=key, line=loader.line_of(document, key), **here)

    if document.get("schema") not in ACTIVITY_VERSIONS:
        report.add("E002", found=document.get("schema"), line=loader.line_of(document, "schema"), **here)

    if not str(document.get("title") or "").strip():
        report.add("E003", key="title", **here)

    instructions = document.get("instructions")
    if instructions is not None:
        problem = template.unbalanced_math(str(instructions))
        if problem:
            report.add("E060", where="instructions", detail=problem,
                       line=loader.line_of(document, "instructions"), **here)

    items = document.get("items")
    if not isinstance(items, list) or not items:
        report.add("E004", key="items", expected="lista no vacía", found=type(items).__name__,
                   line=loader.line_of(document, "items"), **here)
        return report

    seen_ids: dict[str, str] = {}
    for item in items:
        _validate_item(
            item, report=report, path=path, root=path.parent, seen_ids=seen_ids,
            run_generators=False, enrolled=0, max_seeds=None,
        )
        if not isinstance(item, dict):
            continue
        # Las variantes por estudiante se materializan con `policlase build` en la máquina del
        # docente; la plataforma todavía no las recibe, y nunca corre el generador.
        scanned = {k: v for k, v in item.items() if k != "generator"}
        if item.get("generator") or item.get("variables") \
                or any(True for _ in template.iter_placeholders(loader.plain(scanned))):
            report.add("E092", item_id=item.get("id"), line=loader.line_of(item), **here)
    return report


def _flatten(questions: list[dict], follow_up: bool = False) -> list[dict]:
    """Preguntas y sus `follow_ups` en orden de lectura: en una actividad todas están a la vista."""
    out = []
    for question in questions:
        children = question.pop("follow_ups", None) or []
        out.append({**question, "follow_up": follow_up})
        out.extend(_flatten(children, True))
    return out


def compile_activity(document: dict) -> dict:
    """Convierte una actividad válida en la forma que usa la plataforma.

    Igual que en una presentación, las opciones salen con su clave estable y las soluciones en
    un subárbol aparte (`solutions`), fuera del alcance de lo que se le muestra al estudiante.
    La plataforma copia este resultado en cada intento: corregir la actividad después no
    altera lo que respondió quien ya la entregó.
    """
    items, total, review, ai = [], 0.0, False, False
    for item in document.get("items") or []:
        rendered = build.render_item(item, {}, seed=0)
        questions = _flatten(rendered["public"]["questions"])
        solutions = rendered["solutions"]
        for question in questions:
            question["key"] = f"{item.get('id')}.{question['id']}"
            if question["type"] in REVIEW_TYPES:
                review = True
                grading = question.get("grading") or {}
                ai = ai or grading.get("mode") == "ai"
                # En una actividad la rúbrica es pública: el estudiante sabe con qué se le califica.
                # La respuesta de referencia (`reference`) sigue siendo solo del calificador.
                rubric = (solutions.get(question["id"], {}).get("grading") or {}).get("rubric")
                if rubric:
                    question["rubric"] = [{"criterion": str(r.get("criterion", "")),
                                           "points": float(r.get("points", 0))} for r in rubric]
        points = sum(question_points(q) for q in questions)
        total += points
        items.append({
            "item_id": str(item.get("id")),
            "item_version": build.item_version(item),
            "stem": rendered["public"].get("stem", ""),
            "points": points,
            "questions": questions,
            "solutions": solutions,
        })
    return {
        "schema": COMPILED_SCHEMA,
        "title": str(document.get("title") or ""),
        "instructions": str(document.get("instructions") or ""),
        "items": loader.plain(items),
        "points": total,
        #: Hay preguntas que califica una persona (`open`, `image`): la nota queda pendiente.
        "review": review,
        #: Alguna está marcada para calificación asistida por IA (`grading.mode: ai`). Por ahora
        #: es solo una etiqueta: la propuesta de la IA no está activa y la califica el docente.
        "ai": ai,
    }


def load_activity_text(text: str) -> tuple[Any, Report]:
    """Carga y valida desde texto; devuelve el documento (o None) y el reporte."""
    report = Report()
    repairs: list[dict] = []
    try:
        document = loader.load_text(text, "<actividad>", repairs)
    except loader.LoadError as exc:
        report.add("E060", where="el archivo", detail=exc.detail, line=exc.line)
        return None, report
    for fix in repairs:
        report.add("W061", sequences=", ".join(fix["sequences"]), line=fix["line"])
    validate_activity(document, path="<actividad>", report=report)
    return document, report
