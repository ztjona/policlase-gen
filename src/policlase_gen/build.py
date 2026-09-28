"""Materialización de variantes (docs/schema.md §1, capa 1 → 2).

``build`` corre los generadores y produce las variantes ya renderizadas. Es la frontera del
sistema: a partir de aquí no vuelve a ejecutarse código de autoría, ni en el servidor ni al
calificar.

Las variantes son inmutables. Editar la fuente en octubre no altera lo que un estudiante vio
en septiembre; genera una ``item_version`` nueva, y las variantes viejas conservan la suya.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import generator as gen
from . import loader, template
from .grading import choices
from .errors import Report
from .validate import DEFAULT_ENROLLED, find_course_root

BUILD_SCHEMA = "policlase.build/v1"


@dataclass
class BuiltItem:
    item_id: str
    item_version: str
    points: float
    variants: list[dict] = field(default_factory=list)
    distinct: int = 0
    enrolled: int = DEFAULT_ENROLLED

    @property
    def collisions(self) -> float:
        return gen.expected_collisions(self.distinct, self.enrolled)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["schema"] = BUILD_SCHEMA
        data["collisions"] = self.collisions
        return data


def item_version(item: dict, generator_source: bytes = b"") -> str:
    """Huella del contenido del ítem más el código de su generador.

    Cambiar cualquiera de los dos produce una versión nueva, que es lo que permite comparar
    el rendimiento de un ítem entre semestres sabiendo si lo comparado es realmente lo mismo.
    """
    canonical = json.dumps(loader.plain(item), sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8"))
    digest.update(generator_source)
    return digest.hexdigest()[:16]


def render_item(item: dict, variables: dict[str, Any], seed: int = 0) -> dict:
    """Aplica los valores de una variante al texto del ítem.

    Solo se renderiza lo que el estudiante ve más las soluciones. Las soluciones viajan en un
    subárbol aparte para que el serializador del estudiante no pueda alcanzarlas por descuido.
    """
    public: dict[str, Any] = {"questions": []}
    solutions: dict[str, Any] = {}

    if isinstance(item.get("stem"), str):
        public["stem"] = template.render(item["stem"], variables)

    for question in item.get("questions") or []:
        rendered, solution = _render_question(question, variables, seed)
        public["questions"].append(rendered)
        solutions.update(solution)

    return {"public": public, "solutions": solutions}


def _render_question(question: dict, variables: dict[str, Any], seed: int = 0) -> tuple[dict, dict]:
    qid = question.get("id")
    rendered: dict[str, Any] = {"id": qid, "type": question.get("type"),
                                "points": question.get("points")}
    solutions: dict[str, Any] = {}

    if isinstance(question.get("prompt"), str):
        rendered["prompt"] = template.render(question["prompt"], variables)
    if question.get("shape"):
        rendered["shape"] = loader.plain(question["shape"])

    # La mezcla y el muestreo se materializan aquí: la variante guardada debe ser
    # literalmente lo que el estudiante vio, aunque el ítem se edite después.
    if question.get("options"):
        shown = choices.present_options(question, seed)
        rendered["options"] = [
            {"key": option["key"], "text": template.render(option["text"], variables)}
            for option in shown
        ]
        solutions.setdefault(qid, {})["correct"] = [
            option["key"] for option in shown if option.get("correct")
        ]

    if question.get("statements"):
        shown = choices.present_statements(question, seed)
        rendered["statements"] = [
            {"key": statement["key"], "text": template.render(statement["text"], variables)}
            for statement in shown
        ]
        solutions.setdefault(qid, {})["answers"] = {
            statement["key"]: bool(statement.get("answer")) for statement in shown
        }

    if "solution" in question:
        solutions.setdefault(qid, {})["solution"] = template.resolve_deep(
            loader.plain(question["solution"]), variables
        )

    grading = question.get("grading") or {}
    if grading:
        # `reference` y `rubric` son material del calificador, nunca del estudiante.
        public_grading = {
            k: loader.plain(v) for k, v in grading.items()
            if k not in ("reference", "rubric", "accept")
        }
        if public_grading:
            rendered["grading"] = public_grading
        private_grading = {
            k: template.resolve_deep(loader.plain(v), variables)
            for k, v in grading.items()
            if k in ("reference", "rubric", "accept")
        }
        if private_grading:
            solutions.setdefault(qid, {})["grading"] = private_grading

    for follow_up in question.get("follow_ups") or []:
        child, child_solution = _render_question(follow_up, variables, seed)
        rendered.setdefault("follow_ups", []).append(child)
        solutions.update(child_solution)

    return rendered, solutions


def build_item(
    item: dict,
    *,
    path: Path,
    root: Path | None = None,
    enrolled: int = DEFAULT_ENROLLED,
    report: Report | None = None,
    max_seeds: int | None = None,
) -> BuiltItem:
    """Genera todas las variantes de un ítem.

    Un ítem sin ``generator`` —una pregunta de lección, por ejemplo— produce una única
    variante con la semilla 0 y sin variables.
    """
    report = report or Report()
    root = root or find_course_root(path)
    item_id = str(item.get("id"))
    at = {"file": str(path), "item_id": item_id}

    spec = item.get("generator")
    if not spec:
        built = BuiltItem(
            item_id=item_id,
            item_version=item_version(item),
            points=float(item.get("points", 0) or 0),
            enrolled=enrolled,
        )
        built.variants = [{"seed": 0, "fingerprint": "static", **render_item(item, {}, 0)}]
        built.distinct = 1
        return built

    source_path = next(
        (c for c in (root / spec["file"], path.parent / spec["file"]) if c.is_file()),
        root / spec["file"],
    )
    entry = gen.load_entry(source_path, spec.get("entry", "generate"))
    seeds = gen.parse_seeds(spec.get("seeds"))
    if max_seeds is not None:
        seeds = seeds[:max_seeds]
    timeout = float(spec.get("timeout_s", gen.DEFAULT_TIMEOUT_S))

    built = BuiltItem(
        item_id=item_id,
        item_version=item_version(item, source_path.read_bytes()),
        points=float(item.get("points", 0) or 0),
        enrolled=enrolled,
    )

    fingerprints: set[str] = set()
    for seed in seeds:
        try:
            variant = gen.run_seed(entry, seed, timeout)
        except gen.GeneratorError as exc:
            report.add("E026", seed=seed, detail=str(exc), **at)
            continue

        merged = {**variant.public, **variant.private}
        try:
            rendered = render_item(item, merged, seed)
        except template.TemplateError as exc:
            report.add("E020", name=str(exc), seed=seed, **at)
            continue

        fingerprint = variant.fingerprint()
        fingerprints.add(fingerprint)
        built.variants.append({
            "seed": seed,
            "fingerprint": fingerprint,
            "vars": {"public": variant.public, "private": variant.private},
            **rendered,
        })

    built.distinct = len(fingerprints)
    if seeds:
        report.add("I030", distinct=built.distinct, total=len(seeds),
                   enrolled=enrolled, collisions=built.collisions, **at)
    return built


def build_file(
    path: Path | str,
    *,
    out_dir: Path | str | None = None,
    enrolled: int = DEFAULT_ENROLLED,
    report: Report | None = None,
    max_seeds: int | None = None,
) -> list[BuiltItem]:
    path = Path(path)
    report = report or Report()
    document = loader.load_file(path)
    root = find_course_root(path)

    built = [
        build_item(item, path=path, root=root, enrolled=enrolled,
                   report=report, max_seeds=max_seeds)
        for item in (document.get("items") or [])
        if isinstance(item, dict)
    ]

    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        for item in built:
            target = out / f"{item.item_id}.json"
            target.write_text(
                json.dumps(item.to_dict(), ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
    return built


def assign_seed(course_secret: str, item_id: str, student_id: str,
                student_name: str, seeds: list[int]) -> int:
    """Semilla estable y no adivinable para un estudiante (docs/schema.md §7).

    El secreto del curso es lo que impide que alguien que conozca la derivación y la cédula
    de un compañero calcule su variante. Se lee del entorno, nunca del repositorio.
    """
    if not seeds:
        raise ValueError("no hay semillas disponibles")
    material = "\x1f".join([course_secret, item_id, str(student_id), student_name])
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return seeds[int.from_bytes(digest[:8], "big") % len(seeds)]
