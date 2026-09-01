"""Generador de ejemplo — contrato policlase v1.

Corre en TU PC vía `policlase build`, nunca en el servidor.
Requisitos del contrato:
  - firma `generate(seed: int) -> dict` con claves 'public' y 'private'
  - determinista: mismo seed => misma variante, siempre
  - sin I/O, sin red, sin reloj ni aleatoriedad no sembrada
  - los valores devueltos deben coincidir exactamente con `variables:` del YAML
"""

import random


def generate(seed: int) -> dict:
    rng = random.Random(seed)

    # Raíces enteras distintas -> función construida a partir de ellas,
    # así los valores del enunciado y las respuestas nunca se desincronizan.
    r1, r2 = sorted(rng.sample([-4, -3, -2, -1, 1, 2, 3, 4], 2))

    # f(x) = (x - r1)(x - r2) = x^2 - (r1+r2)x + r1*r2
    b, c = -(r1 + r2), r1 * r2
    fcn = _quad_latex(b, c)

    range_1 = [r1 - 1, r1 + 1]          # contiene exactamente una raíz
    range_2 = [max(r1, r2) + 2, max(r1, r2) + 5]   # no contiene ninguna
    range_invalid = [min(r1, r2) - 1, max(r1, r2) + 1]  # signos iguales en los extremos

    return {
        "public": {
            "fcn": fcn,
            "range_1": range_1,
            "range_2": range_2,
            "range_invalid": range_invalid,
        },
        "private": {
            "root_1": float(r1),
            "root_2": float(r2),
            "root_3": None,             # None se renderiza como NaN
            # Antes se devolvía el VALOR de la raíz; la pregunta pide el CONTEO.
            "range_1_count": 1,
            "range_2_count": 0,
        },
    }


def _quad_latex(b: int, c: int) -> str:
    """x^2 + bx + c en LaTeX, sin '+-' ni coeficientes 1 redundantes."""
    out = "x^{2}"
    if b:
        out += f"{'-' if b < 0 else '+'}{abs(b) if abs(b) != 1 else ''}x"
    if c:
        out += f"{'-' if c < 0 else '+'}{abs(c)}"
    return out


if __name__ == "__main__":
    for s in (1, 2, 3):
        v = generate(s)
        print(s, v["public"]["fcn"], "| raíces:",
              v["private"]["root_1"], v["private"]["root_2"])
