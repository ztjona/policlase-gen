"""Carga de archivos YAML de ítems.

Dos reglas, ninguna estilística (docs/schema.md §3):

* **Carga segura.** El constructor de ruamel en modo round-trip desciende de SafeConstructor,
  así que no instancia objetos Python arbitrarios a partir de etiquetas del documento. Los
  ítems llegan desde un repositorio; el cargador completo de PyYAML sería una vía de
  ejecución de código en el propio formato de archivo.
* **YAML 1.2.** El resolvedor de 1.1 convierte ``1e-9`` en cadena, ``no`` en ``False`` y
  ``12:30`` en ``750``. Una tolerancia convertida en cadena no falla: compara mal, en silencio.

El modo round-trip además conserva el número de línea de cada clave, que es lo que permite
que un diagnóstico apunte al lugar exacto del archivo.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError


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


def load_text(text: str, path: Path | str = "<memoria>") -> Any:
    try:
        return _reader().load(io.StringIO(text))
    except YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        raise LoadError(
            Path(str(path)),
            getattr(exc, "problem", str(exc)),
            (mark.line + 1) if mark else None,
        ) from exc


def load_file(path: Path | str) -> Any:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LoadError(path, str(exc)) from exc
    return load_text(text, path)


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
