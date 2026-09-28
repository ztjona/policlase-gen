"""Evaluador de expresiones algebraicas (docs/schema.md §8, tipo ``expression``).

Este es el único calificador que evalúa texto escrito por el estudiante, y por eso es la
pieza que hay que auditar. Tres decisiones sostienen su seguridad:

1. La entrada se convierte en AST y se valida contra una lista blanca de nodos y nombres
   **antes** de evaluar nada. Nunca ``eval`` sobre la cadena cruda, y nunca
   ``sympy.sympify``, que internamente evalúa Python.
2. La comparación es por **muestreo numérico** en el dominio declarado: reconoce
   ``(x-1)*(x+1)`` y ``x^2-1`` como equivalentes sin simplificación simbólica, y no puede
   colgarse.
3. El espacio de nombres de evaluación se construye desde cero; no hereda ``builtins``.

A diferencia del generador, esto sí corre en el servidor con entrada hostil, así que las
restricciones son deliberadamente severas.
"""

from __future__ import annotations

import ast
import math
import random
from dataclasses import dataclass

#: Funciones que un estudiante puede invocar. `allow` en el ítem restringe aún más.
FUNCTIONS = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "exp": math.exp, "sqrt": math.sqrt, "abs": abs,
    "ln": math.log, "log": math.log, "log10": math.log10,
    "floor": math.floor, "ceil": math.ceil,
}

CONSTANTS = {"pi": math.pi, "e": math.e}

_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Call, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd,
)

MAX_LENGTH = 500


class FormatError(Exception):
    """La entrada no es una expresión aceptable. El mensaje se le muestra al estudiante."""


@dataclass(frozen=True)
class Expression:
    source: str
    tree: ast.Expression
    names: frozenset[str]
    calls: frozenset[str]


def parse(text: str, variables: set[str] | None = None, allow: set[str] | None = None) -> Expression:
    """Analiza ``text`` y comprueba que solo use lo permitido.

    ``variables`` son los símbolos libres admitidos (p. ej. ``{"x"}``); ``allow`` restringe
    las funciones invocables a un subconjunto de :data:`FUNCTIONS`.
    """
    variables = variables or set()
    allowed_calls = (set(allow) & set(FUNCTIONS)) if allow is not None else set(FUNCTIONS)
    allowed_constants = {c for c in CONSTANTS if allow is None or c in allow}

    source = (text or "").strip()
    if not source:
        raise FormatError("La respuesta está vacía.")
    if len(source) > MAX_LENGTH:
        raise FormatError(f"La expresión supera los {MAX_LENGTH} caracteres.")

    # `^` es potencia en notación matemática; en Python es XOR bit a bit.
    normalized = source.replace("^", "**")

    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as exc:
        raise FormatError(_syntax_hint(source, exc)) from exc

    names: set[str] = set()
    calls: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, _NODES):
            raise FormatError(
                f"No se admite {type(node).__name__} en una expresión matemática."
            )
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise FormatError("Solo se admiten constantes numéricas.")
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise FormatError("Solo se admiten llamadas a funciones por su nombre.")
            if node.keywords:
                raise FormatError("Las funciones no admiten argumentos con nombre.")
            name = node.func.id
            if name not in allowed_calls:
                raise FormatError(f"Función no permitida en esta pregunta: {name}.")
            calls.add(name)
        elif isinstance(node, ast.Name):
            names.add(node.id)

    free = names - calls
    unknown = free - variables - allowed_constants
    if unknown:
        pretty = ", ".join(sorted(unknown))
        raise FormatError(
            f"Símbolo no reconocido: {pretty}. "
            f"Escriba la multiplicación explícita (2*x, no 2x)."
        )

    return Expression(source=source, tree=tree, names=frozenset(free), calls=frozenset(calls))


def _syntax_hint(source: str, exc: SyntaxError) -> str:
    """Convierte un SyntaxError de Python en algo que le sirva a un estudiante."""
    import re

    if re.search(r"\d\s*[A-Za-z(]", source):
        return "Escriba la multiplicación explícita: 2*x en vez de 2x."
    if source.count("(") != source.count(")"):
        return "Hay paréntesis sin cerrar."
    return "La expresión no se pudo interpretar. Revise operadores y paréntesis."


def evaluate(expression: Expression, values: dict[str, float]) -> float:
    """Evalúa en un punto. El espacio de nombres se construye desde cero."""
    namespace = {name: FUNCTIONS[name] for name in expression.calls}
    namespace.update({k: v for k, v in CONSTANTS.items() if k in expression.names})
    namespace.update(values)
    code = compile(expression.tree, filename="<expresión>", mode="eval")
    return eval(code, {"__builtins__": {}}, namespace)  # noqa: S307 - AST ya validado


def equivalent(
    student: Expression,
    reference: Expression,
    domain: dict[str, tuple[float, float]],
    samples: int = 20,
    rtol: float = 1e-6,
    atol: float = 1e-9,
    seed: int = 0,
) -> bool:
    """¿Coinciden numéricamente en el dominio?

    Se exige que al menos la mitad de los puntos sean evaluables en ambas expresiones: si
    casi ninguno lo es (``ln`` de negativos, división por cero), no hay evidencia suficiente
    y se responde ``False`` en vez de aceptar por vacío.
    """
    variables = sorted(set(student.names) | set(reference.names))
    if not variables:
        try:
            return _close(evaluate(student, {}), evaluate(reference, {}), rtol, atol)
        except Exception:
            return False

    rng = random.Random(seed)
    compared = 0
    for _ in range(samples * 3):
        if compared >= samples:
            break
        point = {}
        for name in variables:
            low, high = domain.get(name, (-5.0, 5.0))
            point[name] = rng.uniform(low, high)
        try:
            a = evaluate(student, point)
            b = evaluate(reference, point)
        except Exception:
            continue          # punto fuera de dominio para alguna de las dos
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            return False
        if isinstance(a, complex) or isinstance(b, complex):
            return False
        if math.isnan(a) or math.isnan(b) or math.isinf(a) or math.isinf(b):
            continue
        compared += 1
        if not _close(a, b, rtol, atol):
            return False

    return compared >= max(1, samples // 2)


def _close(a: float, b: float, rtol: float, atol: float) -> bool:
    return abs(a - b) <= atol + rtol * abs(b)
