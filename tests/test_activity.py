"""Actividades: ítems que cada estudiante resuelve a su paso, con preguntas abiertas e imágenes."""

from __future__ import annotations

from pathlib import Path

from policlase_gen import activity, deck
from policlase_gen.grading import grade
from policlase_gen.validate import validate_file

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "actividad" / "deber-newton.yaml"

HEAD = """
schema: policlase.activity/v1
title: 'Deber'
items:
"""

IMAGE = """
  - id: A-foto
    questions:
      - id: q1
        type: image
        prompt: 'Suba su certificado'
"""


def codes(items_yaml: str, head: str = HEAD) -> list[str]:
    _, report = activity.load_activity_text(head + items_yaml)
    return sorted(d.code for d in report)


def test_el_ejemplo_valida_y_compila():
    text = EXAMPLE.read_text(encoding="utf-8")
    document, report = activity.load_activity_text(text)
    assert report.errors == [] and report.warnings == []
    compiled = activity.compile_activity(document)
    assert compiled["points"] == 9
    assert compiled["review"] and compiled["ai"]
    keys = [q["key"] for item in compiled["items"] for q in item["questions"]]
    assert keys == ["D03-newton-raiz.q1", "D03-newton-raiz.q2", "D03-newton-raiz.q3",
                    "D03-newton-reflexion.q1", "D03-newton-reflexion.q2"]


def test_validate_file_reconoce_actividades():
    assert validate_file(EXAMPLE).ok()


def test_actividad_minima_de_evidencia():
    assert codes(IMAGE) == []


def test_titulo_e_items_obligatorios():
    assert "E003" in codes(IMAGE, HEAD.replace("title: 'Deber'\n", ""))
    assert "E004" in codes("", HEAD.replace("items:\n", "items: []\n"))


def test_las_fechas_no_van_en_el_archivo():
    # Vencimiento, peso y atrasos los fija la plataforma: en el YAML son claves desconocidas.
    assert "E001" in codes(IMAGE, HEAD.replace("title:", "due: 2026-11-01\ntitle:"))


def test_E091_max_files_fuera_de_rango():
    assert "E091" in codes(IMAGE.replace("type: image", "type: image\n        max_files: 0"))
    assert "E091" in codes(IMAGE.replace("type: image", "type: image\n        max_files: 11"))
    assert "E091" in codes(IMAGE.replace("type: image", "type: image\n        max_files: 'tres'"))
    assert codes(IMAGE.replace("type: image", "type: image\n        max_files: 10")) == []


def test_E092_sin_aleatorizacion_por_ahora():
    with_marker = """
  - id: A-x
    questions:
      - { id: q1, type: numeric, prompt: 'Raíz de {{ f }}', solution: 1, grading: { atol: 0.1 } }
"""
    assert "E092" in codes(with_marker)


def test_rubrica_de_imagen_suma_los_puntos():
    bad = IMAGE.replace("type: image", """type: image
        points: 3
        grading:
          rubric:
            - { criterion: 'a', points: 1 }""")
    assert "E046" in codes(bad)
    assert "E045" in codes(IMAGE.replace("type: image", "type: image\n        grading: { mode: ai }"))


def test_la_rubrica_es_publica_y_la_referencia_no():
    text = EXAMPLE.read_text(encoding="utf-8")
    compiled = activity.compile_activity(activity.load_activity_text(text)[0])
    open_q = compiled["items"][1]["questions"][0]
    assert [r["points"] for r in open_q["rubric"]] == [1, 1]
    assert "reference" not in str(compiled["items"][1]["questions"])
    assert "reference" in str(compiled["items"][1]["solutions"])


def test_follow_ups_quedan_a_la_vista_en_orden():
    text = HEAD + """
  - id: A-f
    questions:
      - id: q1
        type: numeric
        solution: 1
        grading: { atol: 0.1 }
        follow_ups:
          - { id: q1a, type: numeric, solution: 2, grading: { atol: 0.1 } }
"""
    compiled = activity.compile_activity(activity.load_activity_text(text)[0])
    questions = compiled["items"][0]["questions"]
    assert [(q["id"], q["follow_up"]) for q in questions] == [("q1", False), ("q1a", True)]
    assert compiled["points"] == 2


def test_imagen_no_se_responde_en_vivo():
    _, report = deck.load_deck_text("""
schema: policlase.deck/v1
title: 'Clase'
slides:
  - item:
      id: L-img
      questions:
        - { id: q1, type: image, prompt: 'Foto' }
""")
    assert "E082" in [d.code for d in report]


def test_imagen_queda_pendiente_de_revision():
    question = {"id": "q1", "type": "image", "points": 2}
    assert grade(question, ["a1", "a2"]).needs_review
    empty = grade(question, [])
    assert not empty.needs_review and empty.points == 0
