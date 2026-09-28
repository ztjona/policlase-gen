"""Catálogo de diagnósticos.

Los códigos y sus severidades son parte del contrato público del esquema: la CLI, el
*hook* de pre-commit y la plataforma reportan exactamente los mismos.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Severity(enum.Enum):
    ERROR = "error"
    WARNING = "aviso"
    INFO = "info"

    @property
    def blocking(self) -> bool:
        """Un error bloquea siempre; un aviso solo en CI (`--strict`)."""
        return self is Severity.ERROR


#: Código -> (severidad, plantilla del mensaje). Ver docs/schema.md §11.
CATALOG: dict[str, tuple[Severity, str]] = {
    "E001": (Severity.ERROR, "Clave desconocida: {key}"),
    "E002": (Severity.ERROR, "Versión de schema desconocida: {found!r}"),
    "E003": (Severity.ERROR, "Falta la clave requerida: {key}"),
    "E004": (Severity.ERROR, "Tipo inválido en {key}: se esperaba {expected}, se encontró {found}"),
    "E010": (Severity.ERROR, "id de ítem duplicado: {id!r} (ya definido en {where})"),
    "E011": (Severity.ERROR, "id inválido {id!r}: solo se permite [a-zA-Z0-9._-]"),
    "E012": (Severity.ERROR, "id de pregunta duplicado dentro del ítem: {id!r}"),
    "E020": (Severity.ERROR, "El marcador {{{{ {name} }}}} no está declarado en variables"),
    "E021": (Severity.WARNING, "La variable {name!r} está declarada pero no se usa"),
    "E022": (Severity.ERROR, "El generador devolvió una clave no declarada: {name!r}"),
    "E023": (Severity.ERROR, "El generador no devolvió la clave declarada: {name!r}"),
    "E024": (Severity.ERROR, "Valor no serializable en {name!r}: {detail}"),
    "E025": (Severity.ERROR, "Generador no determinista: la semilla {seed} produjo dos resultados distintos ({detail})"),
    "E026": (Severity.ERROR, "El generador falló con la semilla {seed}: {detail}"),
    "E027": (Severity.ERROR, "El generador debe devolver un dict con las claves 'public' y 'private'; devolvió {found}"),
    "I030": (Severity.INFO, "Entropía: {distinct} variantes distintas en {total} semillas; con {enrolled} estudiantes se esperan {collisions} colisiones"),
    "E040": (Severity.ERROR, "Tipo de pregunta desconocido: {type!r}"),
    "E041": (Severity.ERROR, "shape {shape} no concuerda con solution de longitud {length}"),
    "E042": (Severity.ERROR, "El tipo {type!r} requiere rtol o atol en grading"),
    "E043": (Severity.ERROR, "choice requiere exactamente una opción correcta; hay {count}"),
    "E044": (Severity.ERROR, "La expresión usa el símbolo {name!r}, ausente de grading.vars"),
    "E045": (Severity.ERROR, "grading.mode 'ai' requiere una rubric"),
    "E046": (Severity.ERROR, "Los puntos de la rúbrica suman {found}, la pregunta vale {expected}"),
    "E047": (Severity.ERROR, "La afirmación {index} de true_false no declara answer"),
    "E048": (Severity.ERROR, "multi_choice requiere al menos una opción correcta"),
    "E050": (Severity.ERROR, "Los puntos de las preguntas suman {found}, el ítem declara {expected}"),
    "E060": (Severity.ERROR, "Matemáticas inválidas en {where}: {detail}"),
    "W070": (Severity.WARNING, "none_of_the_above nunca es correcta; los estudiantes aprenden a descartarla"),
    "W071": (Severity.WARNING, "multi_choice con partial 'per_option' y penalty {penalty}: marcar todas las opciones da nota completa"),
}


@dataclass(frozen=True)
class Diagnostic:
    """Un hallazgo, ubicado con la precisión que se pueda."""

    code: str
    params: dict = field(default_factory=dict)
    file: str | None = None
    line: int | None = None
    item_id: str | None = None
    question_id: str | None = None
    seed: int | None = None

    @property
    def severity(self) -> Severity:
        return CATALOG[self.code][0]

    @property
    def message(self) -> str:
        # Los campos de ubicación también pueden aparecer en la plantilla del mensaje
        # (E025 y E026 citan la semilla), así que se mezclan con los parámetros.
        context = {
            "seed": self.seed,
            "item_id": self.item_id,
            "question_id": self.question_id,
            **self.params,
        }
        return CATALOG[self.code][1].format(**context)

    def location(self) -> str:
        parts = []
        if self.file:
            parts.append(f"{self.file}:{self.line}" if self.line else self.file)
        path = ".".join(p for p in (self.item_id, self.question_id) if p)
        if path:
            parts.append(path)
        if self.seed is not None:
            parts.append(f"semilla {self.seed}")
        return " · ".join(parts)

    def __str__(self) -> str:
        loc = self.location()
        head = f"{self.code} {self.severity.value}"
        return f"{head}: {self.message}" + (f"\n    {loc}" if loc else "")


class Report:
    """Acumula diagnósticos y decide si la validación pasa."""

    def __init__(self) -> None:
        self.diagnostics: list[Diagnostic] = []

    def add(self, code: str, **kwargs) -> None:
        known = {"file", "line", "item_id", "question_id", "seed"}
        loc = {k: kwargs.pop(k) for k in list(kwargs) if k in known}
        self.diagnostics.append(Diagnostic(code=code, params=kwargs, **loc))

    def extend(self, other: "Report") -> None:
        self.diagnostics.extend(other.diagnostics)

    def of(self, severity: Severity) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.severity is severity]

    @property
    def errors(self) -> list[Diagnostic]:
        return self.of(Severity.ERROR)

    @property
    def warnings(self) -> list[Diagnostic]:
        return self.of(Severity.WARNING)

    def ok(self, strict: bool = False) -> bool:
        """En CI (`strict`) los avisos también bloquean."""
        return not self.errors and (not strict or not self.warnings)

    def __len__(self) -> int:
        return len(self.diagnostics)

    def __iter__(self):
        return iter(self.diagnostics)
