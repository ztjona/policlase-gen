"""Resultado común a todos los calificadores."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Result:
    """Lo que produce calificar una respuesta.

    ``fraction`` va de 0 a 1 y ``points`` es esa fracción del valor de la pregunta. Se
    guardan ambos porque la analítica de ítems compara fracciones entre preguntas de distinto
    valor, mientras que el libro de calificaciones suma puntos.
    """

    fraction: float = 0.0
    points: float = 0.0
    correct: bool = False
    #: Detalle por celda, opción o afirmación; alimenta el análisis de distractores.
    detail: dict = field(default_factory=dict)
    #: Problemas de formato, redactados para mostrárselos al estudiante.
    format_errors: list[str] = field(default_factory=list)
    #: Verdadero cuando la respuesta requiere intervención humana (rúbrica manual o IA).
    needs_review: bool = False

    @property
    def gradable(self) -> bool:
        return not self.format_errors

    @classmethod
    def invalid(cls, message: str, **kwargs) -> "Result":
        return cls(format_errors=[message], **kwargs)

    def scaled(self, points: float) -> "Result":
        self.points = round(self.fraction * points, 6)
        return self
