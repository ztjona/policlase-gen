"""Formato único (`policlase/v1`): el mismo contenido para clase, actividad o evaluación, con
segmentos que cambian el comportamiento de lo que les sigue."""

from __future__ import annotations

from pathlib import Path

from policlase_gen import document as doc
from policlase_gen.grading import grade
from policlase_gen.validate import validate_file

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

SOURCE = """schema: policlase/v1
title: 'Deber 1'
use: activity
instructions: 'Resuelva a su ritmo.'
slides:
  - markdown: '## Teclado'
  - item:
      id: U00-teclado
      questions:
        - id: q1
          type: choice
          prompt: '¿Qué distribución tiene su teclado?'
          grading: { mode: survey }
          options: [{ text: 'Latinoamérica' }, { text: 'España' }]
  - segment: { title: 'Símbolos', time_limit_s: 15, block_paste: true }
  - item:
      id: U00-barra
      questions:
        - { id: q1, type: text, prompt: 'Escriba la barra invertida', grading: { accept: ['\\'], normalize: [] } }
  - segment: {}
  - item:
      id: U00-fin
      questions:
        - { id: q1, type: numeric, prompt: '2 + 2', solution: 4, grading: { atol: 0 } }
"""


def codes(text: str) -> list[str]:
    _, report, _ = doc.load_text(text)
    return sorted(d.code for d in report)


def test_actividad_con_segmentos():
    document, report, kind = doc.load_text(SOURCE)
    assert report.errors == [] and report.warnings == []
    assert kind == "activity"
    compiled = doc.compile_content(document)
    assert compiled["use"] == "activity"
    assert [b["kind"] for b in compiled["items"]] == ["content", "item", "segment", "item", "segment", "item"]
    limits = {q["key"]: (q["time_limit_s"], q["block_paste"]) for b in compiled["items"] for q in b["questions"]}
    assert limits == {"U00-teclado.q1": (None, False), "U00-barra.q1": (15, True), "U00-fin.q1": (None, False)}
    assert compiled["points"] == 2                                 # la encuesta no da puntos
    assert [b["at"] for b in compiled["items"]] == [0, 1, 2, 3, 4, 5]
    assert compiled["items"][2]["title"] == "Símbolos"


def test_el_mismo_contenido_como_clase():
    text = SOURCE.replace("use: activity", "use: class").replace("block_paste: true", "speed_bonus: false")
    document, report, kind = doc.load_text(text)
    assert kind == "class"
    assert sorted(d.code for d in report) == ["E001"]                # speed_bonus es de toda la clase
    text = SOURCE.replace("use: activity", "use: class").replace(", block_paste: true", "")
    document, report, kind = doc.load_text(text)
    assert report.errors == [] and report.warnings == []
    compiled = doc.compile_content(document)
    questions = [s for s in compiled["slides"] if s["kind"] == "question"]
    assert [q["time_limit_s"] for q in questions] == [30, 15, 30]   # la clase: 30 s por omisión
    assert questions[1]["segment"] == "Símbolos"
    assert compiled["slides"][-1]["kind"] == "feedback"
    assert [s.get("at") for s in compiled["slides"]] == [0, 1, 3, 5, None]
    assert compiled["segments"][0]["at"] == 2


def test_comportamiento_en_la_raiz_y_valores_por_uso():
    text = SOURCE.replace("instructions:", "time_limit_s: 60\ninstructions:")
    compiled = doc.compile_content(doc.load_text(text)[0])
    limits = [q["time_limit_s"] for b in compiled["items"] for q in b["questions"]]
    assert limits == [60, 15, 60]                                    # `segment: {}` vuelve a la raíz
    evaluation = doc.compile_content(doc.load_text(SOURCE.replace("use: activity", "use: evaluation"))[0])
    assert all(q["block_paste"] for b in evaluation["items"] for q in b["questions"])


def test_errores_del_formato():
    assert "E003" in codes(SOURCE.replace("use: activity\n", ""))
    assert "E086" in codes(SOURCE.replace("use: activity", "use: taller"))
    assert "E001" in codes(SOURCE.replace("title: 'Símbolos'", "titulo: 'Símbolos'"))
    assert "E084" in codes(SOURCE.replace("time_limit_s: 15", "time_limit_s: 2"))
    assert "E085" in codes(SOURCE.replace("block_paste: true", "block_paste: 'sí'"))
    assert "W087" in codes(SOURCE.replace("instructions:", "feedback: false\ninstructions:"))
    assert "E080" in codes(SOURCE.replace("  - markdown: '## Teclado'", "  - { markdown: 'x', segment: {} }"))
    only_segments = "schema: policlase/v1\ntitle: x\nuse: activity\nslides:\n  - segment: {}\n"
    assert "E004" in codes(only_segments)
    assert "E082" in codes(SOURCE.replace("use: activity", "use: class").replace(
        "type: numeric, prompt: '2 + 2', solution: 4, grading: { atol: 0 }", "type: open, prompt: 'x'"))


def test_formatos_anteriores_siguen_valiendo():
    deck_text = (EXAMPLES / "clase-en-vivo" / "biseccion-clase-1.yaml")
    if deck_text.exists():
        document, report, kind = doc.load_text(deck_text.read_text(encoding="utf-8"))
        assert kind == "class" and not report.errors
        assert doc.compile_content(document)["slides"][0]["at"] == 0
    activity_text = (EXAMPLES / "actividad" / "deber-newton.yaml").read_text(encoding="utf-8")
    document, report, kind = doc.load_text(activity_text)
    assert kind == "activity" and not report.errors
    assert doc.entries(document) is document["items"]


def test_validate_file_reconoce_el_formato_unico(tmp_path):
    path = tmp_path / "deber.yaml"
    path.write_text(SOURCE, encoding="utf-8")
    report = validate_file(path)
    assert report.errors == [] and report.warnings == []


def test_encuesta():
    question = {"type": "choice", "grading": {"mode": "survey"},
                "options": [{"key": "a", "text": "Sí"}, {"key": "b", "text": "No"}]}
    result = grade(question, "a")
    assert result.points == 0 and result.correct is False and result.detail["survey"]
    assert grade(question, "z").format_errors
    multi = {**question, "type": "multi_choice"}
    assert not grade(multi, ["a", "b"]).format_errors and grade(multi, ["a", "b"]).points == 0
    assert "E093" in codes(SOURCE.replace("options: [{ text: 'Latinoamérica' }", "options: [{ text: 'Latinoamérica', correct: true }"))
    assert "E094" in codes(SOURCE.replace("grading: { mode: survey }", "grading: { mode: survey }\n          points: 2"))
    assert "E095" in codes(SOURCE.replace("grading: { mode: survey }", "grading: { mode: encuesta }"))


def test_diapositiva_de_solucion():
    text = SOURCE.replace("  - segment: {}\n", "  - solution: |\n      La barra invertida: $\\\\backslash$.\n  - segment: {}\n")
    document, report, _ = doc.load_text(text)
    assert report.errors == [] and report.warnings == []
    compiled = doc.compile_content(document)
    solution = next(b for b in compiled["items"] if b["kind"] == "solution")
    assert solution["at"] == 4 and "barra invertida" in solution["markdown"]
    assert solution["questions"] == [] and solution["points"] == 0
    assert compiled["points"] == 2                                   # no cambia el puntaje
    # En una clase en vivo se avisa y se ignora.
    clase = text.replace("use: activity", "use: class").replace(", block_paste: true", "")
    document, report, _ = doc.load_text(clase)
    assert [d.code for d in report] == ["W096"]
    assert all(s["kind"] != "solution" for s in doc.compile_content(document)["slides"])
    assert "E060" in codes(text.replace("$\\\\backslash$", "$x"))
    assert "E080" in codes(SOURCE.replace("  - markdown: '## Teclado'", "  - { markdown: 'x', solution: 'y' }"))


def test_el_titulo_del_item_se_compila():
    text = SOURCE.replace("      id: U00-teclado\n", "      id: U00-teclado\n      title: 'Distribución del teclado'\n")
    compiled = doc.compile_content(doc.load_text(text)[0])
    titles = [b.get("title") for b in compiled["items"] if b["kind"] == "item"]
    assert titles == ["Distribución del teclado", "", ""]
