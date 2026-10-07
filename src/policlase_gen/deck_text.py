"""Ediciones de una presentación sobre el texto, sin reformatear el YAML.

El editor de la plataforma reordena y oculta diapositivas desde un panel lateral; el archivo es
la fuente de verdad (y vive en git), así que cada operación toca solo las líneas necesarias:
mover una diapositiva mueve su bloque de líneas con sus comentarios; ocultarla agrega o quita
una línea `hidden: true`. El diff en GitHub queda igual de legible que si lo hubiera hecho a mano.
"""

from __future__ import annotations

import re

from . import loader

DASH = re.compile(r"^(?P<indent>[ ]*)-(?P<gap>[ ]+)(?P<rest>.*?)(?P<eol>\r?\n?)$")
TOP_KEY = re.compile(r"^[^\s#-][^:]*:")


class EditError(ValueError):
    pass


def _blank_or_comment(line: str) -> bool:
    return not line.strip() or line.lstrip().startswith("#")


def slide_ranges(text: str) -> list[tuple[int, int]]:
    """[inicio, fin) en índices de línea (0-based) del bloque de cada diapositiva.

    Los comentarios inmediatamente encima de una diapositiva viajan con ella; las líneas en
    blanco entre diapositivas quedan con la anterior.
    """
    try:
        document = loader.load_text(text, "<presentación>")
    except loader.LoadError as exc:
        raise EditError(str(exc.detail)) from None
    slides = document.get("slides") if isinstance(document, dict) else None
    if not isinstance(slides, list) or not slides:
        raise EditError("la presentación no tiene diapositivas")

    lines = text.splitlines(keepends=True)
    starts = []
    for i in range(len(slides)):
        line = (loader.line_of(slides, i) or 1) - 1
        while line > 0 and not DASH.match(lines[line]) and lines[line - 1].strip() == "-":
            line -= 1
        while line > 0 and lines[line - 1].lstrip().startswith("#"):
            line -= 1
        starts.append(line)

    # Fin de la última: la siguiente clave de nivel raíz (p. ej. `meta:`) o el final del archivo.
    end = len(lines)
    for n in range(starts[-1] + 1, len(lines)):
        if TOP_KEY.match(lines[n]):
            end = n
            while end > starts[-1] + 1 and not lines[end - 1].strip():
                end -= 1
            break
    return [(s, e) for s, e in zip(starts, starts[1:] + [end])]


def _ensure_eol(block: list[str]) -> list[str]:
    if block and not block[-1].endswith("\n"):
        block = block[:-1] + [block[-1] + "\n"]
    return block


def _trailing_blanks(block: list[str]) -> int:
    count = 0
    while count < len(block) and not block[len(block) - 1 - count].strip():
        count += 1
    return count


def move_slide(text: str, source: int, target: int) -> str:
    """Mueve la diapositiva `source` a la posición `target` (índices 0-based)."""
    ranges = slide_ranges(text)
    n = len(ranges)
    if not (0 <= source < n and 0 <= target < n):
        raise EditError("índice de diapositiva fuera de rango")
    if source == target:
        return text
    lines = text.splitlines(keepends=True)
    head, tail = lines[:ranges[0][0]], lines[ranges[-1][1]:]
    blocks = []
    for s, e in ranges:
        block = lines[s:e]
        block = block[:len(block) - _trailing_blanks(block)]   # el separador se repone abajo
        blocks.append(_ensure_eol(block))
    # Separador entre diapositivas: el que usaba el archivo después de la primera.
    gap = _trailing_blanks(lines[ranges[0][0]:ranges[0][1]])
    trailing = _trailing_blanks(lines[ranges[-1][0]:ranges[-1][1]])
    blocks.insert(target, blocks.pop(source))
    out = list(head)
    for k, block in enumerate(blocks):
        out += block + (["\n"] * gap if k < n - 1 else [])
    out += ["\n"] * trailing
    result = "".join(out + tail)
    if not text.endswith("\n") and result.endswith("\n"):
        result = result[:-1]
    return result


def set_hidden(text: str, index: int, hidden: bool) -> str:
    """Agrega o quita `hidden: true` en la diapositiva `index`."""
    ranges = slide_ranges(text)
    if not 0 <= index < len(ranges):
        raise EditError("índice de diapositiva fuera de rango")
    lines = text.splitlines(keepends=True)
    start, end = ranges[index]
    first = next(n for n in range(start, end) if DASH.match(lines[n]))
    m = DASH.match(lines[first])
    indent, gap, rest, eol = m["indent"], m["gap"], m["rest"], m["eol"] or "\n"
    key_indent = " " * (len(indent) + 1 + len(gap))

    if rest.startswith("{"):                                 # diapositiva en estilo de flujo
        body = re.sub(r"\bhidden\s*:\s*\w+\s*,?\s*", "", rest[1:]).lstrip()
        rest = "{ hidden: true, " + body if hidden else "{ " + body
        lines[first] = f"{indent}-{gap}{rest}{eol}"
        return "".join(lines)

    own = re.compile(rf"^{key_indent}hidden\s*:")
    if rest.startswith("hidden:") or re.match(r"hidden\s*:", rest):
        if hidden:
            lines[first] = f"{indent}-{gap}hidden: true{eol}"
            return "".join(lines)
        # Quitar la clave que abre la diapositiva: la siguiente clave pasa a llevar el guion.
        nxt = next((n for n in range(first + 1, end)
                    if lines[n].startswith(key_indent) and not lines[n].startswith(key_indent + " ")
                    and not lines[n].lstrip().startswith("#")), None)
        if nxt is None:
            raise EditError("la diapositiva no tiene contenido")
        lines[nxt] = f"{indent}-{gap}{lines[nxt][len(key_indent):]}"
        del lines[first]
        return "".join(lines)

    existing = next((n for n in range(first + 1, end) if own.match(lines[n])), None)
    if existing is not None:
        if hidden:
            lines[existing] = f"{key_indent}hidden: true{eol}"
        else:
            del lines[existing]
        return "".join(lines)
    if not hidden:
        return text
    # Se inserta como primera clave: después de la primera línea podría caer dentro de un `|`.
    lines[first:first + 1] = [f"{indent}-{gap}hidden: true{eol}", f"{key_indent}{rest}{eol}"]
    return "".join(lines)


def set_feedback(text: str, enabled: bool) -> str:
    """`feedback: false` en la raíz desactiva la pregunta final; activa es el valor por omisión."""
    lines = text.splitlines(keepends=True)
    at = next((n for n, line in enumerate(lines) if re.match(r"^feedback\s*:", line)), None)
    if enabled:
        if at is not None:
            del lines[at]
        return "".join(lines)
    if at is not None:
        lines[at] = "feedback: false\n"
        return "".join(lines)
    slides = next((n for n, line in enumerate(lines) if re.match(r"^slides\s*:", line)), len(lines))
    lines.insert(slides, "feedback: false\n")
    return "".join(lines)
