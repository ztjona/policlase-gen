"""Formato único (docs/schema/05-documentos.md): clases en vivo, actividades, evaluaciones y repasos.

Una sola forma de escribir el contenido —diapositivas de contenido, ítems y segmentos— y un
`use` que dice para qué es. Un segmento cambia el comportamiento de las diapositivas que le
siguen, hasta el próximo segmento:

    schema: policlase/v1
    title: 'Deber 1 — Teclado y LaTeX'
    use: activity                  # class (clase en vivo) · activity (actividad) · evaluation (evaluación) · practice (repaso)
    instructions: |                # se muestran antes de empezar (actividades y evaluaciones)
      Resuelva a su ritmo; la última parte tiene tiempo.
    slides:
      - markdown: |
          ## Distribución del teclado
      - item: { id: U00-teclado, questions: [...] }
      - segment:                   # desde aquí: 15 s por pregunta y sin pegar
          title: 'Símbolos'
          time_limit_s: 15
          block_paste: true
      - item: { id: U00-barra, questions: [...] }
      - solution: |                # solución: el estudiante la ve en la revisión, al vencer la fecha
          La barra invertida está en AltGr + ?.

Los comportamientos se escriben en la raíz (valen para todo el documento) o en un segmento (para
sus diapositivas); `use` pone los valores por omisión (`PROFILES`), y cada segmento parte de los
del documento: `segment: {}` vuelve a ellos.

`policlase.deck/v1` (una clase) y `policlase.activity/v1` (una actividad) siguen valiendo: son el
mismo contenido con otra forma, y `load_text` / `compile_content` los tratan igual.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import activity, deck, loader, template
from .errors import Report

VERSION = "policlase/v1"
USES = ("class", "activity", "evaluation", "practice")
USE_LABELS = {"class": "una clase en vivo", "activity": "una actividad", "evaluation": "una evaluación",
              "practice": "un repaso"}

#: Comportamientos y a qué uso aplican. `speed_bonus` y `feedback` son de toda la clase: solo en la raíz.
BEHAVIOR = {"time_limit_s", "block_paste", "speed_bonus", "feedback"}
APPLIES = {"class": {"time_limit_s", "speed_bonus", "feedback"},
           "activity": {"time_limit_s", "block_paste"},
           "evaluation": {"time_limit_s", "block_paste"},
           # Un repaso no tiene tiempo: se practica sin presión, y cada pregunta se comprueba al momento.
           "practice": {"block_paste"}}
PROFILES = {
    "class": {"time_limit_s": deck.DEFAULT_TIME_LIMIT_S, "block_paste": False, "speed_bonus": True, "feedback": True},
    "activity": {"time_limit_s": None, "block_paste": False, "speed_bonus": False, "feedback": False},
    # Una evaluación se escribe sin ayuda: pegar viene bloqueado salvo que se diga otra cosa.
    "evaluation": {"time_limit_s": None, "block_paste": True, "speed_bonus": False, "feedback": False},
    "practice": {"time_limit_s": None, "block_paste": False, "speed_bonus": False, "feedback": False},
}

ROOT_KEYS = {"schema", "title", "use", "instructions", "slides", "meta"} | BEHAVIOR
SLIDE_KEYS = {"markdown", "item", "segment", "solution", "notes", "hidden"}
SEGMENT_KEYS = {"title", "instructions", "time_limit_s", "block_paste"}
#: Lo que puede ser una diapositiva. `solution` es contenido que el estudiante ve solo en la revisión,
#: cuando vence la fecha de entrega (actividades y evaluaciones).
KINDS = ("markdown", "item", "segment", "solution")
ALLOWED = "'markdown', 'item', 'segment' o 'solution'"


def is_document(document: Any) -> bool:
    return isinstance(document, dict) and str(document.get("schema", "")).startswith("policlase/")


def kind_of(document: Any) -> str | None:
    """`class`, `activity`, `evaluation` o `practice` para cualquier formato de contenido; None si no es uno."""
    if deck.is_deck(document):
        return "class"
    if activity.is_activity(document):
        return "activity"
    if is_document(document):
        use = document.get("use")
        return use if use in USES else None
    return None


# ------------------------------------------------------------------ validación


def _check_behavior(container: dict, keys: set[str], use: str | None, prefix: str,
                    report: Report, here: dict) -> None:
    for key in sorted(keys & set(container)):
        at = {**here, "line": loader.line_of(container, key)}
        value = container[key]
        if key == "time_limit_s":
            deck._check_time_limit(value, report, at)
        elif not isinstance(value, bool):
            report.add("E085", key=f"{prefix}{key}", found=value, **at)
        if use in APPLIES and key not in APPLIES[use]:
            report.add("W087", key=f"{prefix}{key}", use=USE_LABELS[use], **at)


def _check_math(text: Any, where: str, report: Report, at: dict) -> None:
    problem = template.unbalanced_math(str(text or ""))
    if problem:
        report.add("E060", where=where, detail=problem, **at)


def validate_v1(document: Any, *, path: Path | str = "<memoria>", report: Report | None = None) -> Report:
    from .validate import _validate_item       # diferido: validate importa este módulo

    report = report if report is not None else Report()
    path = Path(path)
    here = {"file": str(path)}
    if not isinstance(document, dict):
        report.add("E004", key="<raíz>", expected="mapping", found=type(document).__name__, **here)
        return report

    for key in set(document) - ROOT_KEYS:
        report.add("E001", key=key, line=loader.line_of(document, key), **here)
    if document.get("schema") != VERSION:
        report.add("E002", found=document.get("schema"), line=loader.line_of(document, "schema"), **here)
    if not str(document.get("title") or "").strip():
        report.add("E003", key="title", line=1, **here)

    use = document.get("use")
    if use is None:
        report.add("E003", key="use", line=1, **here)
    elif use not in USES:
        report.add("E086", found=use, line=loader.line_of(document, "use"), **here)
        use = None

    _check_behavior(document, BEHAVIOR, use, "", report, here)
    if document.get("instructions") is not None:
        _check_math(document["instructions"], "instructions", report,
                    {**here, "line": loader.line_of(document, "instructions")})

    slides = document.get("slides")
    if not isinstance(slides, list) or not slides:
        report.add("E004", key="slides", expected="lista no vacía", found=type(slides).__name__,
                   line=loader.line_of(document, "slides"), **here)
        return report

    seen_ids: dict[str, str] = {}
    content = 0
    seen_item = False                                  # una solución explica el ítem que la precede
    for number, slide in enumerate(slides, start=1):
        at = {**here, "line": loader.line_of(slides, number - 1)}
        if not isinstance(slide, dict):
            report.add("E080", number=number, allowed=ALLOWED, **at)
            continue
        present = [k for k in KINDS if k in slide]
        if len(present) != 1:
            report.add("E080", number=number, allowed=ALLOWED, **at)
            continue
        kind = present[0]
        allowed = {"segment"} if kind == "segment" else SLIDE_KEYS - {"segment"}
        for key in set(slide) - allowed:
            report.add("E001", key=f"slides[{number}].{key}", **at)
        if "hidden" in slide and not isinstance(slide["hidden"], bool):
            report.add("E085", key=f"slides[{number}].hidden", found=slide["hidden"], **at)

        if kind == "segment":
            segment = slide["segment"]
            if segment is None:
                continue                                   # `segment:` a secas: vuelve a lo del documento
            if not isinstance(segment, dict):
                report.add("E004", key=f"slides[{number}].segment", expected="mapping",
                           found=type(segment).__name__, **at)
                continue
            for key in set(segment) - SEGMENT_KEYS:
                report.add("E001", key=f"slides[{number}].segment.{key}",
                           **{**here, "line": loader.line_of(segment, key) or at["line"]})
            _check_behavior(segment, SEGMENT_KEYS & BEHAVIOR, use, f"slides[{number}].segment.", report, here)
            for key in ("title", "instructions"):
                if key in segment:
                    _check_math(segment[key], f"segmento {number}", report,
                                {**here, "line": loader.line_of(segment, key)})
            continue

        if kind == "solution":
            text = str(slide["solution"] or "")
            _check_math(text, f"diapositiva {number}", report, at)
            if template.placeholders(text):
                report.add("E083" if use == "class" else "E092", number=number, item_id=None, **at)
            if use == "class":
                report.add("W096", number=number, **at)
            elif not seen_item:
                report.add("W099", number=number, **at)
            continue

        content += 1
        if kind == "markdown":
            text = str(slide["markdown"] or "")
            _check_math(text, f"diapositiva {number}", report, at)
            if template.placeholders(text):
                report.add("E083" if use == "class" else "E092", number=number, item_id=None, **at)
            continue

        item = slide["item"]
        if not isinstance(item, dict):
            report.add("E004", key=f"slides[{number}].item", expected="mapping",
                       found=type(item).__name__, **at)
            continue
        seen_item = True
        _validate_item(item, report=report, path=path, root=path.parent, seen_ids=seen_ids,
                       run_generators=False, enrolled=0, max_seeds=None)
        item_at = {**here, "item_id": item.get("id"), "line": loader.line_of(item)}
        if use != "activity":
            for question in _all_questions(item):
                if question.get("debate") is True:
                    report.add("W097", question_id=question.get("id"), use=USE_LABELS[use], **item_at)
        scanned = {k: v for k, v in item.items() if k != "generator"}
        randomized = bool(item.get("generator") or item.get("variables")
                          or any(True for _ in template.iter_placeholders(loader.plain(scanned))))
        if use == "class":
            if randomized:
                report.add("E083", number=number, **item_at)
            questions = item.get("questions") or []
            if len(questions) != 1:
                report.add("E081", count=len(questions), **item_at)
            for question in questions:
                if isinstance(question, dict) and question.get("type") not in deck.LIVE_TYPES:
                    report.add("E082", type=question.get("type"),
                               **{**item_at, "question_id": question.get("id")})
                if isinstance(question, dict) and question.get("follow_ups"):
                    report.add("E081", count=1 + len(question["follow_ups"]), **item_at)
            lecture = item.get("lecture") or {}
            if isinstance(lecture, dict) and "time_limit_s" in lecture:
                deck._check_time_limit(lecture["time_limit_s"], report, item_at)
        elif randomized:
            report.add("E092", **item_at)

    if not content:
        report.add("E004", key="slides", expected="al menos una diapositiva de contenido o un ítem",
                   found="solo segmentos", line=loader.line_of(document, "slides"), **here)
    return report


# ------------------------------------------------------------------ compilación


def _all_questions(item: dict) -> list[dict]:
    """Las preguntas de un ítem y sus `follow_ups`."""
    out = []
    for question in item.get("questions") or []:
        if isinstance(question, dict):
            out.append(question)
            out.extend(_all_questions({"questions": question.get("follow_ups")}))
    return out


def _settings(document: dict, use: str) -> dict:
    """Comportamiento de todo el documento: los valores de su uso, con lo que declare la raíz."""
    out = dict(PROFILES[use])
    for key in BEHAVIOR & set(document):
        out[key] = document[key]
    if deck._unlimited(out["time_limit_s"]) or "time_limit_s" not in APPLIES[use]:
        out["time_limit_s"] = None                     # en un repaso no hay tiempo (W087)
    return out


def _walk(document: dict, use: str):
    """Cada diapositiva con el comportamiento que rige en ella y el segmento al que pertenece."""
    base = _settings(document, use)
    current, segment = dict(base), None
    for at, slide in enumerate(document.get("slides") or []):
        if "segment" in slide:
            spec = slide["segment"] or {}
            current = {**base, **{k: spec[k] for k in SEGMENT_KEYS & BEHAVIOR & APPLIES[use] if k in spec}}
            if deck._unlimited(current["time_limit_s"]):
                current["time_limit_s"] = None
            segment = {"at": at, "title": str(spec.get("title") or ""),
                       "instructions": str(spec.get("instructions") or ""),
                       "time_limit_s": current["time_limit_s"], "block_paste": bool(current["block_paste"])}
            yield at, slide, current, segment, True
            continue
        yield at, slide, current, segment, False


def compile_v1(document: dict) -> dict:
    use = document["use"]
    if use == "class":
        return _compile_class(document)
    return _compile_work(document, use)


def _compile_class(document: dict) -> dict:
    settings = _settings(document, "class")
    slides, segments = [], []
    for at, slide, current, segment, starts in _walk(document, "class"):
        if starts:
            segments.append(segment)
            continue
        if "solution" in slide:                       # en clase no se usa (W096)
            continue
        compiled = deck.compile_slide(slide, current["time_limit_s"], at)
        if segment and segment["title"]:
            compiled["segment"] = segment["title"]
        slides.append(compiled)
    slides.append({"kind": "feedback", "notes": "", "hidden": settings["feedback"] is False})
    return {"schema": "policlase.deck.compiled/v1", "use": "class",
            "title": str(document.get("title") or ""),
            "speed_bonus": settings["speed_bonus"] is not False,
            "slides": loader.plain(slides),
            # Para el panel del editor: dónde empieza cada segmento y qué cambia.
            "segments": loader.plain(segments)}


def _compile_work(document: dict, use: str) -> dict:
    blocks, total, review, ai = [], 0.0, False, False
    last = None                                        # el ítem que explica la próxima solución
    for at, slide, current, segment, starts in _walk(document, use):
        if starts:
            blocks.append({"kind": "segment", "item_id": "", "questions": [], "points": 0.0, **segment})
            continue
        if slide.get("hidden") is True:
            continue
        if "markdown" in slide:
            blocks.append({"kind": "content", "item_id": "", "questions": [], "points": 0.0,
                           "markdown": str(slide["markdown"] or ""), "at": at})
            continue
        if "solution" in slide:
            blocks.append({"kind": "solution", "item_id": "", "questions": [], "points": 0.0,
                           "markdown": str(slide["solution"] or ""), "at": at,
                           "explains": last["item_id"] if last else "", "explains_title": last["title"] if last else ""})
            continue
        block = activity.compile_item(slide["item"], at, current["time_limit_s"], current["block_paste"])
        if use != "activity":                          # el debate solo existe en las actividades (W097)
            for question in block["questions"]:
                question.pop("debate", None)
        review = review or block.pop("_review")
        ai = ai or block.pop("_ai")
        total += block["points"]
        blocks.append(block)
        last = block
    return {"schema": activity.COMPILED_SCHEMA, "use": use,
            "title": str(document.get("title") or ""),
            "instructions": str(document.get("instructions") or ""),
            "items": loader.plain(blocks), "points": total, "review": review, "ai": ai}


# ------------------------------------------------------------------ cualquier formato


def validate_content(document: Any, *, path: Path | str = "<memoria>", report: Report | None = None) -> Report:
    if deck.is_deck(document):
        return deck.validate_deck(document, path=path, report=report)
    if activity.is_activity(document):
        return activity.validate_activity(document, path=path, report=report)
    return validate_v1(document, path=path, report=report)


def compile_content(document: dict) -> dict:
    """El documento válido, compilado según su uso: forma de presentación para una clase, forma de
    actividad para una actividad o evaluación."""
    if deck.is_deck(document):
        return deck.compile_deck(document)
    if activity.is_activity(document):
        return activity.compile_activity(document)
    return compile_v1(document)


def entries(document: Any) -> list | None:
    """La lista del archivo cuyas posiciones (`at`) usan las diapositivas o ítems compilados."""
    if not isinstance(document, dict):
        return None
    found = document.get("items") if activity.is_activity(document) else document.get("slides")
    return found if isinstance(found, list) else None


def load_text(text: str) -> tuple[Any, Report, str | None]:
    """Carga y valida cualquier formato de contenido. Devuelve (documento o None, reporte, uso)."""
    report = Report()
    repairs: list[dict] = []
    try:
        document = loader.load_text(text, "<contenido>", repairs)
    except loader.LoadError as exc:
        report.add("E060", where="el archivo", detail=exc.detail, line=exc.line)
        return None, report, None
    for fix in repairs:
        report.add("W061", sequences=", ".join(fix["sequences"]), line=fix["line"])
    validate_content(document, path="<contenido>", report=report)
    return document, report, kind_of(document)
