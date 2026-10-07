r"""Carga de archivos YAML de ítems.

Dos reglas, ninguna estilística (docs/schema.md §3):

* **Carga segura.** El constructor de ruamel en modo round-trip desciende de SafeConstructor,
  así que no instancia objetos Python arbitrarios a partir de etiquetas del documento. Los
  ítems llegan desde un repositorio; el cargador completo de PyYAML sería una vía de
  ejecución de código en el propio formato de archivo.
* **YAML 1.2.** El resolvedor de 1.1 convierte ``1e-9`` en cadena, ``no`` en ``False`` y
  ``12:30`` en ``750``. Una tolerancia convertida en cadena no falla: compara mal, en silencio.

El modo round-trip además conserva el número de línea de cada clave, que es lo que permite
que un diagnóstico apunte al lugar exacto del archivo.

**LaTeX entre comillas dobles.** En YAML, `"$\tilde{x}$"` no es lo que parece: `\t` es un
tabulador y queda `<TAB>ilde{x}`; igual `\frac` (salto de página), `\beta` (retroceso),
`\nabla` (salto de línea), `\alpha`, `\vec`, `\rho`, `\epsilon`, `\Lambda`, `\Pi`… Dentro de
matemáticas esos caracteres de control no tienen otro origen posible, así que el cargador los
devuelve a su comando y avisa (W061). Los escapes que YAML no conoce (`\sqrt`, `\sin`, `\cdot`)
rompen el archivo: el error lo explica y sugiere comillas simples.
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

#: Carácter que produce un escape de comillas dobles → letra del escape (y del comando de LaTeX).
LATEX_SWALLOWED = {"\x00": "0", "\x07": "a", "\x08": "b", "\t": "t", "\n": "n", "\x0b": "v",
                   "\x0c": "f", "\r": "r", "\x1b": "e", "\x85": "N", "\xa0": "_",
                   "\u2028": "L", "\u2029": "P"}
MATH = re.compile(r"\$\$.+?\$\$|\$[^$]+\$", re.S)
ESCAPE_HINT = ("Entre comillas dobles, YAML interpreta la barra invertida: escriba el texto con LaTeX "
               "entre comillas simples ('$\\sqrt{x}$') o duplique las barras (\"$\\\\sqrt{x}$\").")


class LoadError(Exception):
    """El archivo no es YAML válido; no hay nada que validar todavía."""

    def __init__(self, path: Path, detail: str, line: int | None = None) -> None:
        self.path = path
        self.detail = detail
        self.line = line
        super().__init__(f"{path}:{line or '?'}: {detail}")


def _reader() -> YAML:
    yaml = YAML(typ="rt")          # round-trip: seguro y con información de línea
    yaml.preserve_quotes = True
    return yaml


def load_text(text: str, path: Path | str = "<memoria>", repairs: list | None = None) -> Any:
    """Carga YAML. Si se pasa `repairs`, recibe las correcciones de LaTeX hechas (ver arriba)."""
    try:
        document = _reader().load(io.StringIO(text))
    except YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        detail = getattr(exc, "problem", str(exc))
        if "escape" in str(detail):
            detail = f"{detail}. {ESCAPE_HINT}"
        raise LoadError(Path(str(path)), detail, (mark.line + 1) if mark else None) from exc
    found = _repair_latex(document)
    if repairs is not None:
        repairs.extend(found)
    return document


def load_file(path: Path | str, repairs: list | None = None) -> Any:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LoadError(path, str(exc)) from exc
    return load_text(text, path, repairs)


def _restore(text: str) -> tuple[str, list[str]]:
    """Devuelve a su comando los escapes de YAML que cayeron dentro de matemáticas."""
    found: list[str] = []

    def fix(match: re.Match) -> str:
        out = []
        for ch in match.group(0):
            if ch in LATEX_SWALLOWED:
                found.append("\\" + LATEX_SWALLOWED[ch])
                out.append("\\" + LATEX_SWALLOWED[ch])
            else:
                out.append(ch)
        return "".join(out)

    return MATH.sub(fix, text), found


def _repair_latex(node: Any) -> list[dict]:
    """Recorre el documento y corrige en su lugar las cadenas entre comillas dobles."""
    found: list[dict] = []
    if isinstance(node, CommentedMap):
        entries = [(key, node[key], (node.lc.data.get(key) or [None, None, None])[2]) for key in node]
    elif isinstance(node, CommentedSeq):
        entries = [(i, value, (node.lc.data[i][0] if i in node.lc.data else None))
                   for i, value in enumerate(node)]
    else:
        return found
    for key, value, line in entries:
        if isinstance(value, DoubleQuotedScalarString) and any(ch in value for ch in LATEX_SWALLOWED):
            fixed, sequences = _restore(str(value))
            if sequences:
                node[key] = DoubleQuotedScalarString(fixed)
                found.append({"line": (line + 1) if line is not None else None,
                              "sequences": sorted(set(sequences))})
        elif isinstance(value, (CommentedMap, CommentedSeq)):
            found.extend(_repair_latex(value))
    return found


def line_of(node: Any, key: Any = None) -> int | None:
    """Línea 1-based de ``key`` dentro de ``node``, o del nodo mismo.

    Devuelve ``None`` cuando el nodo no conserva posición (por ejemplo, si vino de un
    diccionario construido en memoria en vez de un archivo).
    """
    lc = getattr(node, "lc", None)
    if lc is None:
        return None
    if key is not None:
        data = getattr(lc, "data", None)
        if isinstance(data, dict) and key in data:
            return data[key][0] + 1
        if isinstance(data, list) and isinstance(key, int) and key < len(data):
            return data[key][0] + 1
    line = getattr(lc, "line", None)
    return None if line is None else line + 1


def plain(value: Any) -> Any:
    """Convierte los tipos de ruamel en tipos nativos, para serializar y comparar."""
    if isinstance(value, dict):
        return {plain(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, str):
        return str(value)
    return value
