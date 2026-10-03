"""Validación de archivos de ítems (docs/schema.md §11).

Corre idéntica en el editor, en el *hook* de pre-commit y en CI. Un error bloquea la
publicación; un aviso bloquea solo con ``--strict``, que es como corre CI.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import generator as gen
from . import loader, template
from .errors import Report
from .grading import expression as expr

SCHEMA_VERSIONS = {"policlase.item/v1"}

ROOT_KEYS = {"schema", "meta", "items"}
META_KEYS = {"locale", "decimal_input", "timezone", "enrolled"}
ITEM_KEYS = {
    "id", "title", "tags", "difficulty", "points", "generator", "variables", "stem",
    "questions", "lecture", "category", "weight", "extra_credit", "grading_granularity",
}
QUESTION_KEYS = {
    "id", "type", "points", "prompt", "solution", "shape", "options", "statements",
    "grading", "sample", "none_of_the_above", "follow_ups",
}
GENERATOR_KEYS = {"file", "entry", "seeds", "timeout_s"}

QUESTION_TYPES = {
    "numeric", "numeric_list", "expression", "choice", "multi_choice",
    "true_false", "text", "open",
}
NUMERIC_TYPES = {"numeric", "numeric_list"}

ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DEFAULT_ENROLLED = 25


def find_course_root(path: Path) -> Path:
    """Sube por el árbol buscando ``policlase.toml``; si no aparece, usa el directorio."""
    path = Path(path).resolve()
    for candidate in [path if path.is_dir() else path.parent, *path.parents]:
        if (candidate / "policlase.toml").is_file():
            return candidate
    return path if path.is_dir() else path.parent


def validate_file(
    path: Path | str,
    *,
    run_generators: bool = True,
    enrolled: int = DEFAULT_ENROLLED,
    max_seeds: int | None = None,
) -> Report:
    path = Path(path)
    report = Report()
    try:
        document = loader.load_file(path)
    except loader.LoadError as exc:
        report.add("E060", where="el archivo", detail=exc.detail, file=str(path), line=exc.line)
        return report

    from .deck import is_deck, validate_deck      # diferido: deck importa este módulo
    if is_deck(document):
        return validate_deck(document, path=path, report=report)

    return validate_document(
        document, path=path, report=report, run_generators=run_generators,
        enrolled=enrolled, max_seeds=max_seeds,
    )


def validate_document(
    document: Any,
    *,
    path: Path | str = "<memoria>",
    report: Report | None = None,
    run_generators: bool = True,
    enrolled: int = DEFAULT_ENROLLED,
    max_seeds: int | None = None,
    seen_ids: dict[str, str] | None = None,
) -> Report:
    report = report if report is not None else Report()
    path = Path(path)
    seen_ids = seen_ids if seen_ids is not None else {}
    here = {"file": str(path)}

    if not isinstance(document, dict):
        report.add("E004", key="<raíz>", expected="mapping", found=type(document).__name__, **here)
        return report

    for key in set(document) - ROOT_KEYS:
        report.add("E001", key=key, line=loader.line_of(document, key), **here)

    version = document.get("schema")
    if version is None:
        report.add("E003", key="schema", **here)
    elif version not in SCHEMA_VERSIONS:
        report.add("E002", found=version, line=loader.line_of(document, "schema"), **here)

    meta = document.get("meta") or {}
    if isinstance(meta, dict):
        for key in set(meta) - META_KEYS:
            report.add("E001", key=f"meta.{key}", line=loader.line_of(meta, key), **here)
        enrolled = int(meta.get("enrolled") or enrolled)
    else:
        report.add("E004", key="meta", expected="mapping", found=type(meta).__name__, **here)

    items = document.get("items")
    if items is None:
        report.add("E003", key="items", **here)
        return report
    if not isinstance(items, list) or not items:
        report.add("E004", key="items", expected="lista no vacía",
                   found=type(items).__name__, **here)
        return report

    root = find_course_root(path)
    for item in items:
        _validate_item(
            item, report=report, path=path, root=root, seen_ids=seen_ids,
            run_generators=run_generators, enrolled=enrolled, max_seeds=max_seeds,
        )
    return report


# --------------------------------------------------------------------------- ítem


def _validate_item(item, *, report, path, root, seen_ids, run_generators, enrolled, max_seeds):
    here = {"file": str(path)}
    if not isinstance(item, dict):
        report.add("E004", key="item", expected="mapping", found=type(item).__name__, **here)
        return

    item_id = item.get("id")
    line = loader.line_of(item, "id")
    if not item_id:
        report.add("E003", key="item.id", line=loader.line_of(item), **here)
        item_id = "<sin id>"
    else:
        if not ID_PATTERN.match(str(item_id)):
            report.add("E011", id=item_id, line=line, **here)
        if item_id in seen_ids:
            report.add("E010", id=item_id, where=seen_ids[item_id], line=line, **here)
        else:
            seen_ids[item_id] = f"{path}:{line}"

    at = {**here, "item_id": item_id}

    for key in set(item) - ITEM_KEYS:
        report.add("E001", key=key, line=loader.line_of(item, key), **at)

    if "points" not in item:
        report.add("E003", key="points", line=loader.line_of(item), **at)
    elif not isinstance(item["points"], (int, float)) or isinstance(item["points"], bool):
        report.add("E004", key="points", expected="number",
                   found=type(item["points"]).__name__, line=loader.line_of(item, "points"), **at)

    questions = item.get("questions")
    if not isinstance(questions, list) or not questions:
        report.add("E004", key="questions", expected="lista no vacía",
                   found=type(questions).__name__, line=loader.line_of(item), **at)
        questions = []

    seen_questions: set[str] = set()
    total_points = 0.0
    for question in questions:
        total_points += _validate_question(
            question, report=report, path=path, item_id=item_id, seen=seen_questions
        )

    declared_points = item.get("points")
    if isinstance(declared_points, (int, float)) and not isinstance(declared_points, bool):
        if abs(total_points - float(declared_points)) > 1e-9:
            report.add("E050", found=_pretty(total_points), expected=_pretty(declared_points),
                       line=loader.line_of(item, "points"), **at)

    _validate_variables(item, report=report, path=path, item_id=item_id)
    _validate_math(item, report=report, path=path, item_id=item_id)

    if item.get("generator") and run_generators:
        _run_generator(item, report=report, path=path, root=root, item_id=item_id,
                       enrolled=enrolled, max_seeds=max_seeds)


def _validate_question(question, *, report, path, item_id, seen) -> float:
    here = {"file": str(path), "item_id": item_id}
    if not isinstance(question, dict):
        report.add("E004", key="question", expected="mapping",
                   found=type(question).__name__, **here)
        return 0.0

    qid = question.get("id") or "<sin id>"
    at = {**here, "question_id": qid, "line": loader.line_of(question, "id")}

    if question.get("id") is None:
        report.add("E003", key="question.id", **{**here, "line": loader.line_of(question)})
    elif qid in seen:
        report.add("E012", id=qid, **at)
    else:
        seen.add(qid)

    for key in set(question) - QUESTION_KEYS:
        report.add("E001", key=key, **{**at, "line": loader.line_of(question, key)})

    kind = question.get("type")
    if kind not in QUESTION_TYPES:
        report.add("E040", type=kind, **{**at, "line": loader.line_of(question, "type")})
        kind = None

    points = question.get("points")
    if not isinstance(points, (int, float)) or isinstance(points, bool):
        report.add("E004", key="points", expected="number",
                   found=type(points).__name__, **at)
        points = 0.0

    grading = question.get("grading") or {}
    if not isinstance(grading, dict):
        report.add("E004", key="grading", expected="mapping",
                   found=type(grading).__name__, **at)
        grading = {}

    if kind in NUMERIC_TYPES:
        if not grading.get("integer") and grading.get("rtol") is None and grading.get("atol") is None:
            report.add("E042", type=kind, **at)
        if "solution" not in question:
            report.add("E003", key="solution", **at)

    if kind == "numeric_list":
        shape = question.get("shape")
        solution = question.get("solution")
        if isinstance(solution, list):
            length = len(_flat(solution))
            if isinstance(shape, list) and shape:
                expected = 1
                for dim in shape:
                    expected *= int(dim) if isinstance(dim, int) else 0
                if expected != length:
                    report.add("E041", shape=shape, length=length, **at)
        else:
            report.add("E004", key="solution", expected="lista",
                       found=type(solution).__name__, **at)

    if kind == "expression":
        if not grading.get("vars"):
            report.add("E003", key="grading.vars", **at)
        solution = question.get("solution")
        if isinstance(solution, str) and not template.placeholders(solution):
            _check_expression(solution, grading, report=report, at=at)

    if kind in ("choice", "multi_choice"):
        options = question.get("options")
        if not isinstance(options, list) or not options:
            report.add("E004", key="options", expected="lista no vacía",
                       found=type(options).__name__, **at)
            options = []
        correct = [o for o in options if isinstance(o, dict) and o.get("correct")]
        nota = question.get("none_of_the_above")
        nota_correct = isinstance(nota, dict) and bool(nota.get("correct"))

        if kind == "choice":
            if len(correct) + (1 if nota_correct else 0) != 1:
                report.add("E043", count=len(correct) + (1 if nota_correct else 0), **at)
            if nota and not nota_correct:
                report.add("W070", **at)
        else:
            if not correct:
                report.add("E048", **at)
            partial = grading.get("partial", "per_option")
            penalty = float(grading.get("penalty", 1.0))
            if partial == "per_option" and penalty < 1.0:
                report.add("W071", penalty=penalty, **at)

    if kind == "true_false":
        statements = question.get("statements")
        if not isinstance(statements, list) or not statements:
            report.add("E004", key="statements", expected="lista no vacía",
                       found=type(statements).__name__, **at)
            statements = []
        for index, statement in enumerate(statements, start=1):
            if not isinstance(statement, dict) or not isinstance(statement.get("answer"), bool):
                report.add("E047", index=index, **at)

    if kind == "text" and not grading.get("accept"):
        report.add("E003", key="grading.accept", **at)

    if kind == "open":
        mode = grading.get("mode", "manual")
        rubric = grading.get("rubric")
        if mode == "ai" and not rubric:
            report.add("E045", **at)
        if isinstance(rubric, list) and rubric:
            total = sum(
                float(entry.get("points", 0))
                for entry in rubric
                if isinstance(entry, dict)
            )
            if abs(total - float(points)) > 1e-9:
                report.add("E046", found=_pretty(total), expected=_pretty(points), **at)

    for follow_up in question.get("follow_ups") or []:
        points += _validate_question(
            follow_up, report=report, path=path, item_id=item_id, seen=seen
        )

    return float(points)


def _check_expression(source: str, grading: dict, *, report, at) -> None:
    variables = set(grading.get("vars") or [])
    allow = grading.get("allow")
    allow = set(allow) if allow is not None else None
    try:
        parsed = expr.parse(source, variables, allow)
    except expr.FormatError as exc:
        message = str(exc)
        unknown = re.search(r"Símbolo no reconocido: ([^.]+)", message)
        if unknown:
            report.add("E044", name=unknown.group(1).strip(), **at)
        else:
            report.add("E060", where="solution", detail=message, **at)
        return
    missing = set(parsed.names) - variables - {"pi", "e"}
    for name in sorted(missing):
        report.add("E044", name=name, **at)


# ----------------------------------------------------------------------- variables


def _validate_variables(item, *, report, path, item_id) -> None:
    at = {"file": str(path), "item_id": item_id}
    variables = item.get("variables") or {}
    declared: set[str] = set()
    if isinstance(variables, dict):
        for scope in ("public", "private"):
            names = variables.get(scope) or []
            if isinstance(names, list):
                declared |= {str(n) for n in names}
            else:
                report.add("E004", key=f"variables.{scope}", expected="lista",
                           found=type(names).__name__, **at)
    elif variables:
        report.add("E004", key="variables", expected="mapping",
                   found=type(variables).__name__, **at)

    scanned = {k: v for k, v in item.items() if k != "generator"}
    used = set(template.iter_placeholders(loader.plain(scanned)))

    for name in sorted(used - declared):
        report.add("E020", name=name, line=loader.line_of(item), **at)
    for name in sorted(declared - used):
        report.add("E021", name=name, line=loader.line_of(item), **at)


def _validate_math(item, *, report, path, item_id) -> None:
    at = {"file": str(path), "item_id": item_id}
    for where, text in _texts(item):
        problem = template.unbalanced_math(text)
        if problem:
            report.add("E060", where=where, detail=problem, **at)


def _texts(item):
    if isinstance(item.get("stem"), str):
        yield "stem", item["stem"]
    for question in item.get("questions") or []:
        if not isinstance(question, dict):
            continue
        qid = question.get("id", "?")
        if isinstance(question.get("prompt"), str):
            yield f"{qid}.prompt", question["prompt"]
        for option in question.get("options") or []:
            if isinstance(option, dict) and isinstance(option.get("text"), str):
                yield f"{qid}.options", option["text"]
        for statement in question.get("statements") or []:
            if isinstance(statement, dict) and isinstance(statement.get("text"), str):
                yield f"{qid}.statements", statement["text"]
        for follow_up in question.get("follow_ups") or []:
            if isinstance(follow_up, dict) and isinstance(follow_up.get("prompt"), str):
                yield f"{follow_up.get('id', '?')}.prompt", follow_up["prompt"]


# ---------------------------------------------------------------------- generador


def _run_generator(item, *, report, path, root, item_id, enrolled, max_seeds) -> None:
    at = {"file": str(path), "item_id": item_id}
    spec = item.get("generator")
    if not isinstance(spec, dict):
        report.add("E004", key="generator", expected="mapping",
                   found=type(spec).__name__, **at)
        return
    for key in set(spec) - GENERATOR_KEYS:
        report.add("E001", key=f"generator.{key}", line=loader.line_of(spec, key), **at)

    file_name = spec.get("file")
    if not file_name:
        report.add("E003", key="generator.file", **at)
        return

    candidates = [root / file_name, Path(path).parent / file_name]
    source = next((c for c in candidates if c.is_file()), candidates[0])

    try:
        entry = gen.load_entry(source, spec.get("entry", "generate"))
    except gen.GeneratorError as exc:
        report.add("E026", seed=0, detail=str(exc), **at)
        return

    try:
        seeds = gen.parse_seeds(spec.get("seeds"))
    except gen.GeneratorError as exc:
        report.add("E026", seed=0, detail=str(exc), **at)
        return
    if max_seeds is not None:
        seeds = seeds[:max_seeds]

    variables = item.get("variables") or {}
    declared = {
        "public": {str(n) for n in (variables.get("public") or [])},
        "private": {str(n) for n in (variables.get("private") or [])},
    }

    timeout = float(spec.get("timeout_s", gen.DEFAULT_TIMEOUT_S))
    fingerprints: set[str] = set()
    reported_keys: set[str] = set()

    for index, seed in enumerate(seeds):
        try:
            # Solo la primera semilla se corre dos veces: el determinismo es una propiedad
            # del generador, no de la semilla, y duplicar 200 corridas no aporta nada.
            variant = (gen.run_twice if index == 0 else gen.run_seed)(entry, seed, timeout)
        except gen.GeneratorError as exc:
            code = "E025" if "inestables" in str(exc) else "E026"
            report.add(code, seed=seed, detail=str(exc), **at)
            return

        for scope in ("public", "private"):
            produced = set(getattr(variant, scope))
            for name in sorted(produced - declared[scope]):
                if name not in reported_keys:
                    reported_keys.add(name)
                    report.add("E022", name=name, seed=seed, **at)
            for name in sorted(declared[scope] - produced):
                if name not in reported_keys:
                    reported_keys.add(name)
                    report.add("E023", name=name, seed=seed, **at)

        merged = {**variant.public, **variant.private}
        bad = gen.check_serializable(merged)
        if bad:
            report.add("E024", name=bad, detail="usa None en vez de NaN o infinitos",
                       seed=seed, **at)
            return

        fingerprints.add(variant.fingerprint())

        if index == 0:
            _check_rendered(item, merged, report=report, at=at, seed=seed)

    if seeds:
        report.add(
            "I030",
            distinct=len(fingerprints),
            total=len(seeds),
            enrolled=enrolled,
            collisions=gen.expected_collisions(len(fingerprints), enrolled),
            **at,
        )


def _check_rendered(item, variables, *, report, at, seed) -> None:
    """Comprobaciones que solo tienen sentido con una variante ya renderizada."""
    for question in item.get("questions") or []:
        if not isinstance(question, dict) or question.get("type") != "expression":
            continue
        solution = question.get("solution")
        if not isinstance(solution, str) or not template.placeholders(solution):
            continue
        try:
            rendered = template.render(solution, variables)
        except template.TemplateError as exc:
            report.add("E060", where="solution", detail=str(exc), seed=seed,
                       **{**at, "question_id": question.get("id")})
            continue
        _check_expression(
            rendered, question.get("grading") or {},
            report=report, at={**at, "question_id": question.get("id"), "seed": seed},
        )


def _flat(value):
    if not isinstance(value, (list, tuple)):
        return [value]
    out = []
    for item in value:
        out.extend(_flat(item)) if isinstance(item, (list, tuple)) else out.append(item)
    return out


def _pretty(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(round(float(value), 4))
