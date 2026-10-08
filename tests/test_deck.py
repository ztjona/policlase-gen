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
    assert kinds == ["content", "question", "content", "question", "question", "question", "content", "feedback"]
    assert compiled["slides"][-1]["hidden"] is False      # retroalimentación activa por defecto

    first = compiled["slides"][1]
    assert first["time_limit_s"] == 20
    assert all("correct" not in o for o in first["question"]["options"])
    right = first["solution"]["correct"][0]
    assert grade(first["question"], right, solution=first["solution"]).correct

    numeric = compiled["slides"][3]
    assert numeric["time_limit_s"] == 30                # hereda de defaults
    assert grade(numeric["question"], "10", solution=numeric["solution"]).points == 2


def test_hidden_y_feedback():
    source = HEAD + "  - markdown: a\n    hidden: true\n  - markdown: b\n"
    document, report = deck.load_deck_text(source)
    assert not report.errors
    slides = deck.compile_deck(document)["slides"]
    assert [s["hidden"] for s in slides] == [True, False, False]

    document, _ = deck.load_deck_text(source.replace("slides:", "feedback: false\nslides:"))
    assert deck.compile_deck(document)["slides"][-1] == {"kind": "feedback", "notes": "", "hidden": True}


def test_E085_hidden_y_feedback_booleanos():
    assert codes("  - markdown: a\n    hidden: si\n") == ["E085"]
    _, report = deck.load_deck_text(HEAD.replace("slides:", "feedback: 1\nslides:") + "  - markdown: a\n")
    assert [d.code for d in report] == ["E085"]


def test_points_por_omision_uno():
    source = HEAD + """  - item:
      id: L-sin-puntos
      questions:
        - id: q1
          type: choice
          prompt: '¿?'
          options:
            - { text: a, correct: true }
            - { text: b }
"""
    document, report = deck.load_deck_text(source)
    assert not report.errors, [d.message for d in report]
    question = deck.compile_deck(document)["slides"][0]
    assert question["points"] == 1.0
    right = question["solution"]["correct"][0]
    assert grade(question["question"], right, solution=question["solution"]).points == 1.0


def test_latex_entre_comillas_dobles_se_corrige_y_avisa():
    source = HEAD + '  - item:\n      id: L-t\n      questions:\n        - id: q1\n          type: choice\n' \
        '          prompt: "Sea $\\tilde{x} = \\frac{a}{b}$"\n          options:\n' \
        '            - { text: "$\\beta$", correct: true }\n            - { text: \'$\\nabla f$\' }\n'
    document, report = deck.load_deck_text(source)
    assert [d.code for d in report] == ["W061", "W061"]
    slide = deck.compile_deck(document)["slides"][0]
    assert slide["question"]["prompt"] == "Sea $\\tilde{x} = \\frac{a}{b}$"
    assert sorted(o["text"] for o in slide["question"]["options"]) == ["$\\beta$", "$\\nabla f$"]


def test_escape_desconocido_explica_las_comillas():
    _, report = deck.load_deck_text(HEAD + '  - markdown: "$\\sqrt{2}$"\n')
    (diagnostic,) = list(report)
    assert diagnostic.code == "E060" and "comillas simples" in diagnostic.message


def test_speed_bonus():
    document, _ = deck.load_deck_text(HEAD + "  - markdown: a\n")
    assert deck.compile_deck(document)["speed_bonus"] is True
    document, report = deck.load_deck_text(HEAD.replace("slides:", "speed_bonus: false\nslides:") + "  - markdown: a\n")
    assert not report.errors and deck.compile_deck(document)["speed_bonus"] is False


def test_tiempo_sin_limite():
    source = HEAD.replace("slides:", "defaults: { time_limit_s: null }\nslides:") + CHOICE + CHOICE.replace("L-x", "L-y").replace(
        "      points: 1\n", "      points: 1\n      lecture: { time_limit_s: 20 }\n", 1)
    document, report = deck.load_deck_text(source)
    assert not report.errors, [d.message for d in report]
    slides = deck.compile_deck(document)["slides"]
    assert [s["time_limit_s"] for s in slides[:2]] == [None, 20]
    document, report = deck.load_deck_text(HEAD + CHOICE.replace("      points: 1\n", "      points: 1\n      lecture: { time_limit_s: .inf }\n", 1))
    assert not report.errors and deck.compile_deck(document)["slides"][0]["time_limit_s"] is None
    assert codes(CHOICE.replace("      points: 1\n", "      points: 1\n      lecture: { time_limit_s: 2 }\n", 1)) == ["E084"]
