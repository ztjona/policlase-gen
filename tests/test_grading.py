"""Calificadores: tolerancias, crédito parcial y seguridad del evaluador."""

from __future__ import annotations

import pytest

from policlase_gen.grading import expression as expr
from policlase_gen.grading import choices, grade, numbers


# ------------------------------------------------------------------- numéricos


@pytest.mark.parametrize(
    "text,expected",
    [("4.23", 4.23), ("4,23", 4.23), ("  -2 ", -2.0), ("1e-3", 0.001),
     ("NaN", None), ("no existe", None), ("-", None), ("1.234,56", 1234.56)],
)
def test_parse_number_acepta_ambos_separadores(text, expected):
    assert numbers.parse_number(text) == expected


def test_parse_number_rechaza_coma_cuando_se_exige_punto():
    with pytest.raises(numbers.ParseError):
        numbers.parse_number("4,23", decimal_input="point")


def test_atol_domina_cerca_de_cero():
    """Declarar solo rtol hace que toda respuesta cercana a cero falle."""
    solo_rtol = {"rtol": 0.01, "atol": 0.0}
    assert not numbers.close(1e-9, 0.0, solo_rtol)          # 0.01 * 0 == 0
    assert numbers.close(1e-9, 0.0, {"rtol": 0.01, "atol": 1e-6})


def test_numeric_integer_rechaza_decimales():
    question = {"type": "numeric", "points": 1, "grading": {"integer": True}}
    assert grade(question, "2", solution=2).correct
    assert not grade(question, "2.4", solution=2).correct


def test_numeric_list_orden_ascendente_y_nan_al_final():
    question = {
        "type": "numeric_list", "points": 3, "shape": [1, 3],
        "grading": {"rtol": 0.01, "order": "ascending", "partial": "per_cell"},
    }
    result = grade(question, ["2", "-2", "NaN"], solution=[-2.0, 2.0, None])
    assert result.correct and result.points == 3


def test_numeric_list_credito_parcial_por_celda():
    question = {
        "type": "numeric_list", "points": 3, "shape": [1, 3],
        "grading": {"rtol": 0.01, "order": "exact", "partial": "per_cell"},
    }
    result = grade(question, ["1", "9", "3"], solution=[1, 2, 3])
    assert result.points == pytest.approx(2.0)
    assert result.detail["cells"] == [True, False, True]


def test_numeric_list_longitud_incorrecta_es_error_de_formato():
    question = {"type": "numeric_list", "points": 3, "shape": [1, 3], "grading": {"rtol": 0.01}}
    result = grade(question, ["1", "2"], solution=[1, 2, 3])
    assert not result.gradable and "3 valores" in result.format_errors[0]


# ------------------------------------------------------------------ expresiones


def test_expresiones_equivalentes_se_reconocen():
    question = {
        "type": "expression", "points": 3,
        "grading": {"vars": ["x"], "domain": {"x": [-3, 3]}, "allow": ["sin", "cos"]},
    }
    assert grade(question, "(x-1)*(x+1)", solution="x**2 - 1").correct
    assert grade(question, "x^2 - 1", solution="x**2 - 1").correct       # ^ es potencia
    assert not grade(question, "x**2 + 1", solution="x**2 - 1").correct


def test_evaluador_rechaza_todo_lo_que_no_sea_aritmetica():
    for hostil in ('__import__("os").system("ls")', "x.__class__", "[1,2]", "lambda: 1",
                   "open('/etc/passwd')", "x if x else 0"):
        with pytest.raises(expr.FormatError):
            expr.parse(hostil, {"x"}, {"sin", "cos"})


def test_funcion_fuera_de_allow_se_rechaza():
    with pytest.raises(expr.FormatError, match="no permitida"):
        expr.parse("tan(x)", {"x"}, {"sin", "cos"})


def test_multiplicacion_implicita_da_un_mensaje_util():
    with pytest.raises(expr.FormatError, match="multiplicación explícita"):
        expr.parse("2x", {"x"}, None)


def test_evaluador_no_hereda_builtins():
    parsed = expr.parse("x + 1", {"x"}, None)
    assert expr.evaluate(parsed, {"x": 2}) == 3


# --------------------------------------------------------------------- opciones


def _multi(penalty=1.0, partial="per_option"):
    return {
        "type": "multi_choice", "points": 4, "id": "q",
        "options": [
            {"text": "A", "correct": True}, {"text": "B", "correct": True},
            {"text": "C"}, {"text": "D"},
        ],
        "grading": {"partial": partial, "penalty": penalty, "floor": 0},
    }


def test_marcar_todo_no_da_nota_con_penalty_1():
    """La razón de ser de W071: con penalty 0 esto daría nota completa."""
    assert grade(_multi(penalty=1.0), ["A", "B", "C", "D"]).points == 0
    assert grade(_multi(penalty=0.0), ["A", "B", "C", "D"]).points == 4


def test_multi_choice_credito_parcial():
    assert grade(_multi(), ["A"]).points == pytest.approx(2.0)
    assert grade(_multi(), ["A", "B"]).points == pytest.approx(4.0)
    assert grade(_multi(partial="all_or_nothing"), ["A"]).points == 0


def test_none_of_the_above_va_siempre_al_final():
    question = {
        "id": "q", "type": "choice",
        "options": [{"text": f"opción {i}", "correct": i == 0} for i in range(5)],
        "none_of_the_above": True,
        "sample": {"shuffle": "seeded"},
    }
    for seed in range(20):
        shown = choices.present_options(question, seed)
        assert shown[-1]["text"] == choices.NONE_OF_THE_ABOVE
        assert shown[-1].get("pinned")


def test_sample_distractors_limita_las_opciones_mostradas():
    question = {
        "id": "q", "type": "choice",
        "options": [{"text": "correcta", "correct": True}] + [{"text": f"d{i}"} for i in range(5)],
        "sample": {"distractors": 3},
    }
    shown = choices.present_options(question, seed=7)
    assert len(shown) == 4
    assert sum(1 for o in shown if o.get("correct")) == 1


def test_true_false_al_azar_tiende_a_cero():
    question = {
        "id": "q", "type": "true_false", "points": 4,
        "statements": [
            {"text": "a", "answer": True}, {"text": "b", "answer": False},
            {"text": "c", "answer": True}, {"text": "d", "answer": False},
        ],
        "grading": {"partial": "per_statement", "penalty": 1.0, "floor": 0},
    }
    statements = choices.present_statements(question, seed=0)
    todo_verdadero = {s["key"]: True for s in statements}
    assert grade(question, todo_verdadero, seed=0).points == 0

    todas = {s["key"]: s["answer"] for s in statements}
    assert grade(question, todas, seed=0).points == 4


def test_text_normaliza_acentos_y_mayusculas():
    question = {
        "type": "text", "points": 1,
        "grading": {"accept": ["bisección"], "normalize": ["lowercase", "strip_accents"]},
    }
    assert grade(question, "BISECCION").correct
    assert not grade(question, "newton").correct


def test_open_nunca_califica_solo():
    question = {"type": "open", "points": 3, "grading": {"mode": "ai"}}
    result = grade(question, "una respuesta razonada")
    assert result.points == 0 and result.needs_review
