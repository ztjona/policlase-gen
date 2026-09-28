"""Sustitución de marcadores ``{{ var | filtro(args) }}`` (docs/schema.md §6).

Los valores llegan estructurados desde el generador y se les da formato aquí. Un generador
nunca debe devolver una cadena ya formateada como ``"[-5, 4]"``: eso impide que el
calificador reutilice el valor.
"""

from __future__ import annotations

import math
import re
from typing import Any, Callable

#: ``{{ nombre }}`` o ``{{ nombre | filtro }}`` o ``{{ nombre | filtro(2) }}``.
#: Se eligió esta delimitación sobre ``<nombre>`` porque esta última choca con las
#: desigualdades (``$x < 3$``) y con HTML.
PLACEHOLDER = re.compile(
    r"\{\{\s*(?P<name>[A-Za-z_]\w*)"
    r"(?:\s*\|\s*(?P<filter>[a-z_]\w*)"
    r"(?:\(\s*(?P<arg>-?\d+)\s*\))?)?"
    r"\s*\}\}"
)

NAN_TEXT = r"\mathrm{NaN}"


class TemplateError(Exception):
    """Marcador con un filtro desconocido o un valor que ese filtro no admite."""


def placeholders(text: str) -> set[str]:
    """Nombres de variable referidos por ``text``."""
    return {m.group("name") for m in PLACEHOLDER.finditer(text)}


def iter_placeholders(value: Any):
    """Recorre recursivamente cadenas dentro de dicts y listas, devolviendo nombres."""
    if isinstance(value, str):
        yield from placeholders(value)
    elif isinstance(value, dict):
        for v in value.values():
            yield from iter_placeholders(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from iter_placeholders(v)


# --------------------------------------------------------------------------- filtros


def _num(value: Any, digits: int | None = None) -> str:
    if value is None:
        return NAN_TEXT
    if isinstance(value, bool):
        return "V" if value else "F"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return NAN_TEXT
        if digits is None:
            # Un flotante entero se escribe sin cola: 2.0 -> "2".
            if isinstance(value, float) and value.is_integer():
                return str(int(value))
            return str(value)
        return f"{value:.{digits}f}"
    return str(value)


def _interval(value: Any, digits: int | None = None) -> str:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise TemplateError(f"el filtro 'interval' espera [a, b], recibió {value!r}")
    lo, hi = (_num(v, digits) for v in value)
    return f"[{lo},\\,{hi}]"


def _latex(value: Any, digits: int | None = None) -> str:
    if isinstance(value, (list, tuple)):
        inner = ",\\,".join(_num(v, digits) for v in value)
        return f"[{inner}]"
    return _num(value, digits)


def _sci(value: Any, digits: int | None = 3) -> str:
    if value is None:
        return NAN_TEXT
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TemplateError(f"el filtro 'sci' espera un número, recibió {value!r}")
    value = float(value)
    if value == 0:
        return "0"
    exponent = math.floor(math.log10(abs(value)))
    mantissa = value / (10**exponent)
    return f"{mantissa:.{digits if digits is not None else 3}f} \\times 10^{{{exponent}}}"


FILTERS: dict[str, Callable[..., str]] = {
    "num": _num,
    "interval": _interval,
    "latex": _latex,
    "sci": _sci,
}


def _default(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return _latex(value)
    return _num(value)


# --------------------------------------------------------------------------- render


def render(text: str, variables: dict[str, Any]) -> str:
    """Sustituye los marcadores de ``text``.

    Un nombre ausente de ``variables`` es un error, no una cadena vacía: renderizar
    ``{{ root_2 }}`` literalmente en la pantalla de veinticinco estudiantes es exactamente
    el fallo que el validador existe para impedir.
    """

    def replace(match: re.Match) -> str:
        name = match.group("name")
        if name not in variables:
            raise TemplateError(f"variable no definida: {name!r}")
        value = variables[name]
        filter_name = match.group("filter")
        if filter_name is None:
            return _default(value)
        if filter_name not in FILTERS:
            raise TemplateError(f"filtro desconocido: {filter_name!r}")
        arg = match.group("arg")
        if arg is None:
            return FILTERS[filter_name](value)
        return FILTERS[filter_name](value, int(arg))

    return PLACEHOLDER.sub(replace, text)


#: ``"{{ x }}"`` a secas: el marcador ocupa toda la cadena y no lleva filtro.
_LONE = re.compile(r"^\s*\{\{\s*([A-Za-z_]\w*)\s*\}\}\s*$")


def resolve(value: Any, variables: dict[str, Any]) -> Any:
    r"""Como :func:`render`, pero conserva el tipo cuando la cadena es un solo marcador.

    Las soluciones se comparan, no se muestran: ``"{{ root_3 }}"`` debe resolverse al valor
    ``None`` —que el calificador entiende como NaN— y no a la cadena ``\mathrm{NaN}``, que
    ningún analizador numérico aceptaría de vuelta.
    """
    if isinstance(value, str):
        lone = _LONE.match(value)
        if lone:
            name = lone.group(1)
            if name not in variables:
                raise TemplateError(f"variable no definida: {name!r}")
            return variables[name]
        return render(value, variables)
    return value


def resolve_deep(value: Any, variables: dict[str, Any]) -> Any:
    """:func:`resolve` aplicado a cada cadena dentro de una estructura anidada."""
    if isinstance(value, dict):
        return {k: resolve_deep(v, variables) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [resolve_deep(v, variables) for v in value]
    return resolve(value, variables)


def render_deep(value: Any, variables: dict[str, Any]) -> Any:
    """``render`` aplicado a cada cadena dentro de una estructura anidada."""
    if isinstance(value, str):
        return render(value, variables)
    if isinstance(value, dict):
        return {k: render_deep(v, variables) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [render_deep(v, variables) for v in value]
    return value


# ------------------------------------------------------------------- comprobación math

_DISPLAY = re.compile(r"\$\$")
_INLINE = re.compile(r"(?<!\\)\$")


def unbalanced_math(text: str) -> str | None:
    """Detecta ``$`` sin cerrar. Devuelve el detalle del problema, o ``None``.

    No valida la sintaxis interna de KaTeX —eso lo hace el renderizador del servidor, que sí
    tiene KaTeX disponible— pero el delimitador sin cerrar es el error más común al escribir
    y se atrapa aquí sin dependencias.
    """
    without_display = _DISPLAY.sub("", text)
    if _DISPLAY.findall(text).__len__() % 2:
        return "delimitador $$ sin cerrar"
    if len(_INLINE.findall(without_display)) % 2:
        return "delimitador $ sin cerrar"
    return None
