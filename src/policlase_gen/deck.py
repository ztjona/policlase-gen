"""Presentaciones para clases en vivo (docs/schema.md §9).

Una presentación es una secuencia de diapositivas que el profesor avanza; algunas son de
contenido (markdown con matemáticas) y otras son preguntas que los estudiantes responden desde
su dispositivo. Las preguntas son ítems ordinarios del esquema v1, sin generador: en clase
todos ven lo mismo al mismo tiempo, y así los sondeos entran en la misma analítica de ítems.

    schema: policlase.deck/v1
    title: "Bisección — clase 1"
    defaults: { time_limit_s: 30 }
    slides:
      - markdown: |
          # El teorema de Bolzano
      - item:
          id: L01-bolzano
          points: 1
          questions:
            - { id: q1, type: choice, points: 1, prompt: "...", options: [...] }
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import build, loader, template
from .errors import Report
from .points import question_points

DECK_VERSIONS = {"policlase.deck/v1"}
DECK_KEYS = {"schema", "title", "defaults", "slides", "meta", "feedback", "speed_bonus"}
SLIDE_KEYS = {"markdown", "item", "notes", "hidden"}
DEFAULT_KEYS = {"time_limit_s"}

#: Tipos que se pueden responder en vivo con un toque o un número. `open` y `expression`
#: quedan fuera: exigen escribir con calma, que no es lo que pide una pregunta cronometrada.
LIVE_TYPES = {"choice", "multi_choice", "true_false", "numeric", "text"}

DEFAULT_TIME_LIMIT_S = 30
#: `time_limit_s: null` (o `.inf`): la pregunta no tiene límite; la cierra el docente o se cierra
#: sola cuando respondieron todos.
UNLIMITED = None
MIN_TIME_LIMIT_S, MAX_TIME_LIMIT_S = 5, 600


def is_deck(document: Any) -> bool:
    return isinstance(document, dict) and str(document.get("schema", "")).startswith("policlase.deck/")


def validate_deck(document: Any, *, path: Path | str = "<memoria>", report: Report | None = None) -> Report:
    # Import diferido: validate importa este módulo para despachar por tipo de documento.
    from .validate import _validate_item

    report = report if report is not None else Report()
    path = Path(path)
    here = {"file": str(path)}

    if not isinstance(document, dict):
        report.add("E004", key="<raíz>", expected="mapping", found=type(document).__name__, **here)
        return report

    for key in set(document) - DECK_KEYS:
        report.add("E001", key=key, line=loader.line_of(document, key), **here)

    version = document.get("schema")
    if version not in DECK_VERSIONS:
        report.add("E002", found=version, line=loader.line_of(document, "schema"), **here)

    if not str(document.get("title") or "").strip():
        report.add("E003", key="title", **here)

    for flag in ("feedback", "speed_bonus"):
        if flag in document and not isinstance(document[flag], bool):
            report.add("E085", key=flag, found=document[flag], line=loader.line_of(document, flag), **here)

    defaults = document.get("defaults") or {}
    if isinstance(defaults, dict):
        for key in set(defaults) - DEFAULT_KEYS:
            report.add("E001", key=f"defaults.{key}", line=loader.line_of(defaults, key), **here)
        if "time_limit_s" in defaults:
            _check_time_limit(defaults["time_limit_s"], report, here)

    slides = document.get("slides")
    if not isinstance(slides, list) or not slides:
        report.add("E004", key="slides", expected="lista no vacía",
                   found=type(slides).__name__, **here)
        return report

    seen_ids: dict[str, str] = {}
    for number, slide in enumerate(slides, start=1):
        at = {**here, "line": loader.line_of(slides, number - 1)}
        if not isinstance(slide, dict):
            report.add("E080", number=number, **at)
            continue
        for key in set(slide) - SLIDE_KEYS:
            report.add("E001", key=f"slides[{number}].{key}", **at)
        if "hidden" in slide and not isinstance(slide["hidden"], bool):
            report.add("E085", key=f"slides[{number}].hidden", found=slide["hidden"], **at)

        has_markdown, has_item = "markdown" in slide, "item" in slide
        if has_markdown == has_item:
            report.add("E080", number=number, **at)
            continue

        if has_markdown:
            problem = template.unbalanced_math(str(slide["markdown"] or ""))
            if problem:
                report.add("E060", where=f"diapositiva {number}", detail=problem, **at)
            if template.placeholders(str(slide["markdown"] or "")):
                report.add("E083", number=number, **at)
            continue

        item = slide["item"]
        if not isinstance(item, dict):
            report.add("E004", key=f"slides[{number}].item", expected="mapping",
                       found=type(item).__name__, **at)
            continue

        _validate_item(
            item, report=report, path=path, root=path.parent, seen_ids=seen_ids,
            run_generators=False, enrolled=0, max_seeds=None,
        )
        item_at = {**here, "item_id": item.get("id"), "line": loader.line_of(item)}

        if item.get("generator") or item.get("variables"):
            report.add("E083", number=number, **item_at)

        questions = item.get("questions") or []
        if len(questions) != 1:
            report.add("E081", count=len(questions), **item_at)
        for question in questions:
            if isinstance(question, dict) and question.get("type") not in LIVE_TYPES:
                report.add("E082", type=question.get("type"),
                           **{**item_at, "question_id": question.get("id")})
            if isinstance(question, dict) and question.get("follow_ups"):
                report.add("E081", count=1 + len(question["follow_ups"]), **item_at)

        lecture = item.get("lecture") or {}
        if isinstance(lecture, dict) and "time_limit_s" in lecture:
            _check_time_limit(lecture["time_limit_s"], report, item_at)

    return report


def _unlimited(value: Any) -> bool:
    return value is None or (isinstance(value, float) and value == float("inf"))


def _check_time_limit(value: Any, report: Report, at: dict) -> None:
    if _unlimited(value):
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not MIN_TIME_LIMIT_S <= value <= MAX_TIME_LIMIT_S:
        report.add("E084", value=value, low=MIN_TIME_LIMIT_S, high=MAX_TIME_LIMIT_S, **at)


def _limit(container: Any, inherited: int | None) -> int | None:
    """Límite declarado en `container` (null/.inf = sin límite) o el heredado si no lo declara."""
    if not isinstance(container, dict) or "time_limit_s" not in container:
        return inherited
    value = container["time_limit_s"]
    return UNLIMITED if _unlimited(value) else int(value)


def compile_deck(document: dict) -> dict:
    """Convierte una presentación válida en la forma que usa la plataforma en vivo.

    Cada pregunta sale con su presentación materializada —claves de opción estables— y su
    registro de solución aparte, igual que una variante de `build`. La plataforma copia este
    resultado al iniciar una sesión, así que editar la presentación después no altera una
    clase ya dictada.
    """
    defaults = document.get("defaults") or {}
    default_limit = _limit(defaults, DEFAULT_TIME_LIMIT_S)
    slides = []

    for slide in document.get("slides") or []:
        hidden = slide.get("hidden") is True
        if "markdown" in slide:
            slides.append({"kind": "content", "markdown": str(slide["markdown"] or ""),
                           "notes": str(slide.get("notes") or ""), "hidden": hidden})
            continue

        item = slide["item"]
        rendered = build.render_item(item, {}, seed=0)
        question = rendered["public"]["questions"][0]
        record = rendered["solutions"].get(question["id"], {})
        lecture = item.get("lecture") or {}
        slides.append({
            "kind": "question",
            "item_id": str(item.get("id")),
            "item_version": build.item_version(item),
            "stem": rendered["public"].get("stem", ""),
            "question": question,
            "solution": record,
            "points": question_points(question),
            "time_limit_s": _limit(lecture, default_limit),
            "notes": str(slide.get("notes") or ""),
            "hidden": hidden,
        })

    # Retroalimentación anónima de la clase: siempre al final, salvo `feedback: false`. Se
    # compila igual (oculta) para que el editor pueda mostrarla y reactivarla.
    slides.append({"kind": "feedback", "notes": "", "hidden": document.get("feedback") is False})

    return {"schema": "policlase.deck.compiled/v1",
            "title": str(document.get("title") or ""),
            # Bono por rapidez en el marcador de la clase (no en la nota): activo salvo `false`.
            "speed_bonus": document.get("speed_bonus") is not False,
            "slides": loader.plain(slides)}


def load_deck_text(text: str) -> tuple[Any, Report]:
    """Carga y valida desde texto; devuelve el documento (o None) y el reporte."""
    report = Report()
    repairs: list[dict] = []
    try:
        document = loader.load_text(text, "<presentación>", repairs)
    except loader.LoadError as exc:
        report.add("E060", where="el archivo", detail=exc.detail, line=exc.line)
        return None, report
    for fix in repairs:
        report.add("W061", sequences=", ".join(fix["sequences"]), line=fix["line"])
    validate_deck(document, path="<presentación>", report=report)
    return document, report
