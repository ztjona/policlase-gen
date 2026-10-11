"""Ediciones de texto de una presentación: mover, ocultar, retroalimentación."""

from __future__ import annotations

import pytest

from policlase_gen import deck, deck_text

SOURCE = """schema: policlase.deck/v1
title: "Prueba"   # comentario en la raíz
defaults: { time_limit_s: 30 }

slides:
  # --- portada ---
  - markdown: |
      # Uno
      Texto con $x^2$.
    notes: "nota"

  - item:
      id: L-a
      points: 1
      questions:
        - { id: q1, type: choice, points: 1, prompt: "¿A?", options: [{ text: "a", correct: true }, { text: "b" }] }

  - markdown: Tres
"""


def titles(text: str) -> list[str]:
    document, report = deck.load_deck_text(text)
    assert not report.errors, [d.message for d in report]
    out = []
    for s in deck.compile_deck(document)["slides"]:
        if s["kind"] == "content":
            out.append(s["markdown"].strip().splitlines()[0] + ("*" if s["hidden"] else ""))
        elif s["kind"] == "question":
            out.append(s["item_id"] + ("*" if s["hidden"] else ""))
    return out


def test_rangos_incluyen_comentarios_previos():
    ranges = deck_text.slide_ranges(SOURCE)
    lines = SOURCE.splitlines()
    assert lines[ranges[0][0]].strip() == "# --- portada ---"
    assert lines[ranges[1][0]].strip() == "- item:"
    assert ranges[-1][1] == len(lines)


@pytest.mark.parametrize("source,target,expected", [
    (0, 2, ["L-a", "Tres", "# Uno"]),
    (2, 0, ["Tres", "# Uno", "L-a"]),
    (1, 0, ["L-a", "# Uno", "Tres"]),
])
def test_mover(source, target, expected):
    moved = deck_text.move_slide(SOURCE, source, target)
    assert titles(moved) == expected
    assert "# comentario en la raíz" in moved and "# --- portada ---" in moved
    assert "\n\n\n" not in moved                       # sin separadores duplicados


def test_mover_ida_y_vuelta_deja_el_texto_igual():
    assert deck_text.move_slide(deck_text.move_slide(SOURCE, 0, 2), 2, 0) == SOURCE


def test_mover_con_claves_despues_de_slides():
    source = SOURCE + "meta:\n  autor: x\n"
    moved = deck_text.move_slide(source, 2, 0)
    assert titles(moved) == ["Tres", "# Uno", "L-a"]
    assert moved.endswith("meta:\n  autor: x\n")


def test_ocultar_y_mostrar_bloque_literal():
    hidden = deck_text.set_hidden(SOURCE, 0, True)
    assert titles(hidden) == ["# Uno*", "L-a", "Tres"]
    assert "  - hidden: true\n    markdown: |\n      # Uno" in hidden
    assert deck_text.set_hidden(hidden, 0, False) == SOURCE


def test_ocultar_es_idempotente_y_respeta_hidden_existente():
    once = deck_text.set_hidden(SOURCE, 1, True)
    assert deck_text.set_hidden(once, 1, True) == once
    source = SOURCE.replace("    notes: \"nota\"", "    notes: \"nota\"\n    hidden: false")
    assert titles(deck_text.set_hidden(source, 0, True)) == ["# Uno*", "L-a", "Tres"]
    assert "hidden" not in deck_text.set_hidden(source, 0, False)


def test_ocultar_diapositiva_en_flujo():
    source = SOURCE.replace("  - markdown: Tres\n", "  - { markdown: Tres }\n")
    hidden = deck_text.set_hidden(source, 2, True)
    assert titles(hidden)[-1] == "Tres*"
    assert titles(deck_text.set_hidden(hidden, 2, False))[-1] == "Tres"


def test_retroalimentacion():
    off = deck_text.set_feedback(SOURCE, False)
    assert "feedback: false\nslides:" in off
    document, _ = deck.load_deck_text(off)
    assert deck.compile_deck(document)["slides"][-1]["hidden"] is True
    assert deck_text.set_feedback(off, True) == SOURCE


def test_errores():
    with pytest.raises(deck_text.EditError):
        deck_text.move_slide(SOURCE, 0, 9)
    with pytest.raises(deck_text.EditError):
        deck_text.slide_ranges("slides: [ :")


ACTIVITY = """schema: policlase.activity/v1
title: 'Deber'

items:
  # el primero
  - id: a
    questions:
      - { id: q1, type: numeric, prompt: 'Uno', solution: 1, grading: { atol: 0 } }

  - id: b
    questions:
      - { id: q1, type: numeric, prompt: 'Dos', solution: 2, grading: { atol: 0 } }
meta: { locale: es-EC }
"""


def test_mover_items_de_una_actividad():
    from policlase_gen import activity

    moved = deck_text.move_item(ACTIVITY, 0, 1)
    document, report = activity.load_activity_text(moved)
    assert not report.errors
    assert [item["id"] for item in document["items"]] == ["b", "a"]
    assert "  # el primero\n  - id: a" in moved                  # el comentario viaja con su ítem
    assert moved.endswith("meta: { locale: es-EC }\n")
    assert deck_text.move_item(moved, 1, 0) == ACTIVITY
    with pytest.raises(deck_text.EditError, match="ítems"):
        deck_text.move_item("schema: policlase.activity/v1\ntitle: x\nitems: []\n", 0, 1)
