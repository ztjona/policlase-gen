"""Ejecución de generadores (docs/schema.md §7).

Un generador convierte una semilla en una variante. **Corre en el computador del autor**,
durante ``policlase build``; el servidor solo recibe variantes ya materializadas. Esa
división es la que elimina el problema de ejecutar código de autoría en producción, así que
este módulo no pretende ser un sandbox: pretende atrapar generadores *equivocados*, no
generadores hostiles.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import signal
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

DEFAULT_TIMEOUT_S = 2.0

#: Tipos que sobreviven un viaje por JSON. ``float('nan')`` no está entre ellos: el
#: contrato pide ``None``, que el renderizador convierte en NaN.
SERIALIZABLE = (int, float, str, bool, type(None))


class GeneratorError(Exception):
    """El generador no cumple el contrato."""


@dataclass(frozen=True)
class Variant:
    """Una instancia materializada del ítem para una semilla concreta."""

    seed: int
    public: dict[str, Any]
    private: dict[str, Any]

    def fingerprint(self) -> str:
        """Huella de los valores visibles, para contar variantes distintas.

        Solo entra ``public``: dos estudiantes con el mismo enunciado tienen la misma
        variante a efectos de copia, aunque internamente difieran en algo que no ven.
        """
        blob = json.dumps(self.public, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


class _Timeout(Exception):
    pass


def _alarm(signum, frame):  # pragma: no cover - depende del reloj
    raise _Timeout()


def load_entry(path: Path, entry: str = "generate") -> Callable[[int], dict]:
    """Importa ``entry`` desde ``path``.

    El módulo se carga bajo un nombre derivado de su ruta para que dos generadores con el
    mismo nombre de archivo en unidades distintas no se pisen en ``sys.modules``.
    """
    path = Path(path)
    if not path.is_file():
        raise GeneratorError(f"no existe el archivo del generador: {path}")

    module_name = "policlase_gen._loaded." + hashlib.sha1(
        str(path.resolve()).encode("utf-8")
    ).hexdigest()[:12]

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise GeneratorError(f"no se pudo importar {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise GeneratorError(f"{type(exc).__name__} al importar {path.name}: {exc}") from exc

    func = getattr(module, entry, None)
    if func is None or not callable(func):
        raise GeneratorError(f"{path.name} no define una función {entry!r}")
    return func


def check_serializable(value: Any, path: str = "") -> str | None:
    """Devuelve la ruta del primer valor no serializable, o ``None``."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, float):
        # NaN e infinitos no tienen representación en JSON estricto.
        if value != value or value in (float("inf"), float("-inf")):
            return path or "<raíz>"
        return None
    if isinstance(value, SERIALIZABLE):
        return None
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                return f"{path}[{key!r}] (clave no textual)"
            found = check_serializable(item, f"{path}.{key}" if path else key)
            if found:
                return found
        return None
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found = check_serializable(item, f"{path}[{index}]")
            if found:
                return found
        return None
    return path or "<raíz>"


def run_seed(func: Callable[[int], dict], seed: int, timeout_s: float = DEFAULT_TIMEOUT_S) -> Variant:
    """Corre el generador una vez y valida la forma de lo devuelto."""
    has_alarm = hasattr(signal, "setitimer")
    previous = None
    if has_alarm:
        previous = signal.signal(signal.SIGALRM, _alarm)
        signal.setitimer(signal.ITIMER_REAL, timeout_s)
    try:
        result = func(seed)
    except _Timeout:
        raise GeneratorError(f"excedió el tiempo límite de {timeout_s}s") from None
    except Exception as exc:
        raise GeneratorError(f"{type(exc).__name__}: {exc}") from exc
    finally:
        if has_alarm:
            signal.setitimer(signal.ITIMER_REAL, 0)
            if previous is not None:
                signal.signal(signal.SIGALRM, previous)

    if not isinstance(result, dict) or not {"public", "private"} <= set(result):
        raise GeneratorError(
            f"se esperaba un dict con 'public' y 'private', se recibió {type(result).__name__}"
        )
    public, private = result["public"], result["private"]
    if not isinstance(public, dict) or not isinstance(private, dict):
        raise GeneratorError("'public' y 'private' deben ser diccionarios")

    return Variant(seed=seed, public=dict(public), private=dict(private))


def same(a: Any, b: Any) -> bool:
    """Igualdad estructural que trata NaN como igual a sí mismo.

    Sin esto, un generador que devuelva ``float('nan')`` se reporta como no determinista
    —porque en Python ``nan != nan``— cuando su problema real es que NaN no es serializable.
    El diagnóstico correcto es E024, y solo se llega a él si la comparación no miente antes.
    """
    if isinstance(a, float) and isinstance(b, float):
        if a != a and b != b:                     # ambos NaN
            return True
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def run_twice(func: Callable[[int], dict], seed: int, timeout_s: float = DEFAULT_TIMEOUT_S):
    """Corre la misma semilla dos veces y compara.

    Un generador que use ``random`` global, el reloj o la red devolverá resultados
    distintos, y ese es exactamente el fallo que hace irreproducible un examen.
    """
    first = run_seed(func, seed, timeout_s)
    second = run_seed(func, seed, timeout_s)
    if not same(first.public, second.public) or not same(first.private, second.private):
        differing = sorted(
            {
                key
                for key in set(first.public) | set(first.private)
                if not same(first.public.get(key), second.public.get(key))
                or not same(first.private.get(key), second.private.get(key))
            }
        )
        detail = ", ".join(differing[:4]) or "claves distintas"
        raise GeneratorError(f"claves inestables: {detail}")
    return first


def parse_seeds(spec: Any) -> list[int]:
    """Interpreta ``seeds``: ``"1..200"``, un entero, o una lista explícita."""
    if spec is None:
        return list(range(1, 201))
    if isinstance(spec, int) and not isinstance(spec, bool):
        return list(range(1, spec + 1))
    if isinstance(spec, (list, tuple)):
        return [int(s) for s in spec]
    if isinstance(spec, str) and ".." in spec:
        low, _, high = spec.partition("..")
        try:
            return list(range(int(low), int(high) + 1))
        except ValueError as exc:
            raise GeneratorError(f"rango de semillas inválido: {spec!r}") from exc
    raise GeneratorError(f"valor de 'seeds' inválido: {spec!r}")


def expected_collisions(distinct: int, enrolled: int) -> float:
    """Estudiantes que comparten variante con algún compañero, en promedio.

    Es el problema del cumpleaños: con ``d`` variantes equiprobables y ``n`` estudiantes,
    el número esperado de estudiantes *no* únicos es ``n - d(1 - (1-1/d)^n)``.
    """
    if distinct <= 0 or enrolled <= 0:
        return 0.0
    unique = distinct * (1 - (1 - 1 / distinct) ** enrolled)
    return max(0.0, round(enrolled - unique, 1))
