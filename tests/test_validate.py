"""Validador: cada código del catálogo tiene su prueba."""

from __future__ import annotations

import textwrap

import pytest

from policlase_gen import loader, template
from policlase_gen.generator import expected_collisions
from policlase_gen.validate import validate_document

BASE = """
schema: policlase.item/v1
items:
  - id: U01-demo
    points: 1
    questions:
      - id: q1
        type: numeric
        points: 1
        prompt: "¿Cuánto es dos más dos?"
        solution: 4
        grading: { rtol: 0.01 }
"""


def codes(yaml_text: str, **kwargs) -> list[str]:
    document = loader.load_text(textwrap.dedent(yaml_text))
    report = validate_document(document, run_generators=False, **kwargs)
    return sorted(d.code for d in report)


def test_documento_minimo_valido():
    assert codes(BASE) == []


# ------------------------------------------------------------------ estructura


def test_E001_clave_desconocida():
    assert "E001" in codes(BASE.replace("items:", "inventada: 1\nitems:"))


def test_E002_version_desconocida():
    assert "E002" in codes(BASE.replace("policlase.item/v1", "policlase.item/v99"))


def test_E003_falta_clave_requerida():
    assert "E003" in codes(BASE.replace("        solution: 4\n", ""))


def test_E010_id_duplicado():
    assert "E010" in codes(BASE + """\
  - id: U01-demo
    points: 1
    questions:
      - id: q1
        type: numeric
        points: 1
        solution: 1
        grading: { rtol: 0.01 }
""")


def test_E011_id_invalido():
    assert "E011" in codes(BASE.replace("U01-demo", "U01 demo!"))


def test_E012_pregunta_duplicada():
    assert "E012" in codes("""
schema: policlase.item/v1
items:
  - id: U01-demo
    points: 2
    questions:
      - id: q1
        type: numeric
        points: 1
        solution: 4
        grading: { rtol: 0.01 }
      - id: q1
        type: numeric
        points: 1
        solution: 5
        grading: { rtol: 0.01 }
""")


# ------------------------------------------------------------------- variables


def test_E020_marcador_no_declarado():
    assert "E020" in codes(BASE.replace('"¿Cuánto es dos más dos?"', '"¿Cuánto es {{ a }} + 2?"'))


def test_E021_variable_declarada_sin_usar():
    assert "E021" in codes("""
schema: policlase.item/v1
items:
  - id: U01-demo
    points: 1
    variables:
      public: [sobrante]
      private: []
    questions:
      - id: q1
        type: numeric
        points: 1
        solution: 4
        grading: { rtol: 0.01 }
""")


# ---------------------------------------------------------------- por tipo


def test_E040_tipo_desconocido():
    assert "E040" in codes(BASE.replace("type: numeric", "type: telepatia"))


def test_E041_shape_no_concuerda():
    yaml_text = BASE.replace(
        "        type: numeric\n        points: 1\n        prompt: \"¿Cuánto es dos más dos?\"\n        solution: 4\n",
        "        type: numeric_list\n        points: 1\n        shape: [1, 3]\n        solution: [1, 2]\n",
    )
    assert "E041" in codes(yaml_text)


def test_E042_falta_tolerancia():
    assert "E042" in codes(BASE.replace("        grading: { rtol: 0.01 }", "        grading: {}"))


def test_E042_no_aplica_a_enteros():
    assert "E042" not in codes(BASE.replace("{ rtol: 0.01 }", "{ integer: true }"))


CHOICE = """
schema: policlase.item/v1
items:
  - id: U01-sel
    points: 2
    questions:
      - id: q1
        type: choice
        points: 2
        prompt: "Elija"
        options:
          - { text: "a", correct: true }
          - { text: "b" }
"""


def test_E043_choice_con_dos_correctas():
    assert "E043" in codes(CHOICE.replace('{ text: "b" }', '{ text: "b", correct: true }'))


def test_E043_choice_sin_correctas():
    assert "E043" in codes(CHOICE.replace(', correct: true', ''))


def test_W070_none_of_the_above_nunca_correcta():
    assert "W070" in codes(CHOICE + "        none_of_the_above: true\n")


def test_W071_multi_choice_con_penalty_bajo():
    multi = CHOICE.replace("type: choice", "type: multi_choice")
    multi += "        grading: { partial: per_option, penalty: 0 }\n"
    assert "W071" in codes(multi)


def test_E048_multi_choice_sin_correctas():
    multi = CHOICE.replace("type: choice", "type: multi_choice").replace(", correct: true", "")
    assert "E048" in codes(multi)


TRUE_FALSE = """
schema: policlase.item/v1
items:
  - id: U01-vf
    points: 2
    questions:
      - id: q1
        type: true_false
        points: 2
        prompt: "Marque"
        statements:
          - { text: "a", answer: true }
          - { text: "b" }
"""


def test_E047_afirmacion_sin_answer():
    assert "E047" in codes(TRUE_FALSE)


def test_true_false_completo_valida():
    assert codes(TRUE_FALSE.replace('{ text: "b" }', '{ text: "b", answer: false }')) == []


OPEN = """
schema: policlase.item/v1
items:
  - id: U01-abierta
    points: 2
    questions:
      - id: q1
        type: open
        points: 2
        prompt: "Explique"
        grading:
          mode: ai
"""


def test_E045_ai_sin_rubrica():
    assert "E045" in codes(OPEN)


def test_E046_rubrica_no_suma():
    assert "E046" in codes(OPEN + """\
          rubric:
            - { criterion: "uno", points: 1 }
""")


def test_rubrica_que_suma_valida():
    assert codes(OPEN + """\
          rubric:
            - { criterion: "uno", points: 1 }
            - { criterion: "dos", points: 1 }
""") == []


def test_E050_puntos_no_suman():
    assert "E050" in codes(BASE.replace("  - id: U01-demo\n    points: 1", "  - id: U01-demo\n    points: 5"))


def test_follow_ups_suman_al_total_del_item():
    assert codes("""
schema: policlase.item/v1
items:
  - id: U01-demo
    points: 3
    questions:
      - id: q1
        type: numeric
        points: 1
        solution: 4
        grading: { rtol: 0.01 }
        follow_ups:
          - id: q1a
            type: text
            points: 2
            prompt: "¿Por qué?"
            grading: { accept: ["porque sí"] }
""") == []


def test_E060_dolar_sin_cerrar():
    assert "E060" in codes(BASE.replace('"¿Cuánto es dos más dos?"', '"Calcule $x + 1"'))


def test_E044_simbolo_ausente_de_vars():
    yaml_text = """
    schema: policlase.item/v1
    items:
      - id: U01-expr
        points: 1
        questions:
          - id: q1
            type: expression
            points: 1
            prompt: "Derive"
            solution: "2*y"
            grading: { vars: [x] }
    """
    assert "E044" in codes(yaml_text)


# ------------------------------------------------------------------ auxiliares


def test_entropia_problema_del_cumpleanos():
    """28 variantes y 25 estudiantes: el caso que motivó el reporte I030."""
    assert expected_collisions(28, 25) == pytest.approx(9.0, abs=1.0)
    assert expected_collisions(10_000, 25) < 0.1
    assert expected_collisions(1, 25) == 24


def test_yaml_12_no_convierte_valores():
    """1e-9 debe seguir siendo flotante; 'no' y '12:30' deben seguir siendo cadenas."""
    parsed = loader.load_text("a: 1e-9\nb: no\nc: 12:30\nd: NaN\n")
    assert isinstance(parsed["a"], float) and parsed["a"] == pytest.approx(1e-9)
    assert parsed["b"] == "no"
    assert parsed["c"] == "12:30"
    assert parsed["d"] == "NaN"


def test_los_diagnosticos_citan_la_linea():
    document = loader.load_text(textwrap.dedent(BASE.replace("type: numeric", "type: telepatia")))
    report = validate_document(document, run_generators=False)
    unknown = next(d for d in report if d.code == "E040")
    assert unknown.line is not None and unknown.item_id == "U01-demo"


def test_math_desbalanceado_se_detecta():
    assert template.unbalanced_math("$x + 1$") is None
    assert template.unbalanced_math("$$x$$") is None
    assert template.unbalanced_math("$x + 1") is not None
