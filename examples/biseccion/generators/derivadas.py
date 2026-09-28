"""Segundo generador de ejemplo: derivada de un producto.

Muestra la distinción que impone el tipo `expression`: el enunciado se muestra en LaTeX,
pero la solución que el calificador compara es una expresión infija plana, escrita en el
mismo lenguaje que teclea el estudiante.
"""

import random


def generate(seed: int) -> dict:
    rng = random.Random(seed)
    a = rng.randint(2, 9)
    n = rng.randint(2, 4)

    # f(x) = a·x^n·sin(x)  =>  f'(x) = a·n·x^(n-1)·sin(x) + a·x^n·cos(x)
    f_latex = rf"{a}x^{{{n}}}\sin(x)"
    df_expr = f"{a}*{n}*x**{n - 1}*sin(x) + {a}*x**{n}*cos(x)"

    return {
        "public": {"f_latex": f_latex},
        "private": {"df_expr": df_expr},
    }
