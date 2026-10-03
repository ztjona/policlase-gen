"""Presentaciones para clase en vivo."""

from __future__ import annotations

from pathlib import Path

from policlase_gen import deck, loader
from policlase_gen.grading import grade

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "clase-en-vivo" / "biseccion-clase-1.yaml"

HEAD = """
schema: policlase.deck/v1
title: "Prueba"
slides:
"""


def codes(slides_yaml: str) -> list[str]:
    _, report = deck.load_deck_text(HEAD + slides_yaml)
    return sorted(d.code for d in report)


CHOICE = """
  - item:
      id: L-x
      points: 1
      questions:
        - id: q1
          type: choice
          points: 1
          prompt: "¿?"
          options:
            - { text: "a", correct: true }
            - { text: "b" }
"""


def test_el_ejemplo_valida():
    _, report = deck.load_deck_text(EXAMPLE.read_text(encoding="utf-8"))
    assert report.errors == [] and report.warnings == []


def test_presentacion_minima():
    assert codes("  - markdown: 'Hola $x$'\n" + CHOICE) == []


def test_E080_diapositiva_sin_contenido_o_con_ambos():
    assert "E080" in codes("  - notes: 'solo notas'\n")
    assert "E080" in codes("  - markdown: 'a'\n    item: { id: x }\n")


def test_E081_una_sola_pregunta():
    two = CHOICE.replace("      points: 1\n", "      points: 2\n", 1) + """\
        - id: q2
          type: choice
          points: 1
          options:
            - { text: "a", correct: true }
"""
    assert "E081" in codes(two)


def test_E082_tipo_no_apto_en_vivo():
    assert "E082" in codes(CHOICE.replace("type: choice", "type: open")
                           .replace("""          options:
            - { text: "a", correct: true }
            - { text: "b" }
""", "          grading: { mode: manual }\n"))


def test_E083_sin_aleatorizacion():
    assert "E083" in codes(CHOICE.replace("      points: 1\n",
                                          "      points: 1\n      generator: { file: g.py }\n", 1))
    assert "E083" in codes("  - markdown: 'Sea {{ a }}'\n")


def test_E084_tiempo_fuera_de_rango():
    assert "E084" in codes(CHOICE.replace("      points: 1\n",
                                          "      points: 1\n      lecture: { time_limit_s: 2 }\n", 1))


def test_los_errores_del_item_se_siguen_reportando():
    assert "E043" in codes(CHOICE.replace('{ text: "b" }', '{ text: "b", correct: true }'))


def test_validate_file_despacha_a_presentaciones():
    from policlase_gen.validate import validate_file
    assert validate_file(EXAMPLE).errors == []


def test_compilar_y_calificar_ida_y_vuelta():
    document = loader.load_file(EXAMPLE)
    compiled = deck.compile_deck(document)
    kinds = [s["kind"] for s in compiled["slides"]]
    assert kinds == ["content", "question", "content", "question", "question", "question", "content"]

    first = compiled["slides"][1]
    assert first["time_limit_s"] == 20
    assert all("correct" not in o for o in first["question"]["options"])
    right = first["solution"]["correct"][0]
    assert grade(first["question"], right, solution=first["solution"]).correct

    numeric = compiled["slides"][3]
    assert numeric["time_limit_s"] == 30                # hereda de defaults
    assert grade(numeric["question"], "10", solution=numeric["solution"]).points == 2
