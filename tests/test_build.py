"""Generadores y materialización de variantes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from policlase_gen import build, generator as gen, loader
from policlase_gen.errors import Report
from policlase_gen.validate import validate_document

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "biseccion" / "item.yaml"


def write_generator(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "g.py"
    path.write_text(body, encoding="utf-8")
    return path


def test_determinismo_se_verifica(tmp_path):
    """Un generador que use random global produce exámenes irreproducibles."""
    path = write_generator(tmp_path, """
import random
def generate(seed):
    return {"public": {"a": random.random()}, "private": {}}
""")
    entry = gen.load_entry(path)
    with pytest.raises(gen.GeneratorError, match="inestables"):
        gen.run_twice(entry, 1)


def test_generador_sembrado_es_estable(tmp_path):
    path = write_generator(tmp_path, """
import random
def generate(seed):
    rng = random.Random(seed)
    return {"public": {"a": rng.randint(1, 100)}, "private": {}}
""")
    entry = gen.load_entry(path)
    assert gen.run_twice(entry, 7).public == gen.run_seed(entry, 7).public


def test_nan_no_es_serializable():
    assert gen.check_serializable({"a": float("nan")}) == "a"
    assert gen.check_serializable({"a": float("inf")}) == "a"
    assert gen.check_serializable({"a": None}) is None
    assert gen.check_serializable({"a": [1, {"b": "x"}]}) is None
    assert gen.check_serializable({"a": {1, 2}}) == "a"


def test_excepcion_del_generador_se_reporta(tmp_path):
    path = write_generator(tmp_path, """
def generate(seed):
    raise ValueError("me equivoqué")
""")
    entry = gen.load_entry(path)
    with pytest.raises(gen.GeneratorError, match="me equivoqué"):
        gen.run_seed(entry, 1)


def test_forma_incorrecta_del_retorno(tmp_path):
    path = write_generator(tmp_path, """
def generate(seed):
    return {"valores": 1}
""")
    with pytest.raises(gen.GeneratorError, match="public"):
        gen.run_seed(gen.load_entry(path), 1)


@pytest.mark.parametrize(
    "spec,expected",
    [("1..5", [1, 2, 3, 4, 5]), (3, [1, 2, 3]), ([7, 9], [7, 9]), (None, list(range(1, 201)))],
)
def test_parse_seeds(spec, expected):
    assert gen.parse_seeds(spec) == expected


# --------------------------------------------------------------------- build


def test_el_ejemplo_construye_y_separa_las_soluciones():
    document = loader.load_file(EXAMPLE)
    item = document["items"][0]
    report = Report()
    built = build.build_item(item, path=EXAMPLE, report=report, max_seeds=5)

    assert len(built.variants) == 5
    variant = built.variants[0]

    # Lo que ve el estudiante no contiene ninguna respuesta.
    public_blob = json.dumps(variant["public"], ensure_ascii=False)
    assert "root_1" not in public_blob
    assert "{{" not in public_blob                      # todo quedó renderizado
    solutions = variant["solutions"]
    assert "q1" in solutions and "solution" in solutions["q1"]


def test_la_rubrica_y_la_referencia_no_viajan_al_estudiante():
    document = loader.load_file(EXAMPLE)
    item = document["items"][0]
    built = build.build_item(item, path=EXAMPLE, report=Report(), max_seeds=1)
    blob = json.dumps(built.variants[0]["public"], ensure_ascii=False)
    assert "rubric" not in blob and "Bolzano" not in blob


def test_item_sin_generador_produce_una_variante_estatica():
    document = loader.load_file(EXAMPLE)
    lecture = next(i for i in document["items"] if not i.get("generator"))
    built = build.build_item(lecture, path=EXAMPLE, report=Report())
    assert len(built.variants) == 1 and built.variants[0]["seed"] == 0


def test_item_version_cambia_con_el_contenido():
    a = build.item_version({"id": "x", "points": 1})
    b = build.item_version({"id": "x", "points": 2})
    c = build.item_version({"id": "x", "points": 1}, b"# generador distinto")
    assert a != b and a != c


def test_assign_seed_es_estable_y_depende_del_secreto():
    seeds = list(range(1, 201))
    args = ("MN-2026", "U01-biseccion", "1727364550", "Ana Pérez")
    first = build.assign_seed(*args, seeds)
    assert first == build.assign_seed(*args, seeds)
    assert first in seeds

    # Sin el secreto del curso, conocer la cédula bastaría para calcular la variante.
    otro = build.assign_seed("otro-secreto", *args[1:], seeds)
    distinto = build.assign_seed(args[0], args[1], "9999", args[3], seeds)
    assert otro != first or distinto != first


def test_el_ejemplo_del_repo_valida_sin_errores():
    document = loader.load_file(EXAMPLE)
    report = validate_document(document, path=EXAMPLE, run_generators=True, max_seeds=10)
    assert report.errors == []


def test_la_solucion_conserva_su_valor_y_no_su_texto_latex():
    """`{{ root_3 }}` debe resolverse a None, no a la cadena `\\mathrm{NaN}`.

    Renderizarla como texto la volvía imposible de reanalizar: el calificador numérico
    rechazaba su propia solución.
    """
    document = loader.load_file(EXAMPLE)
    item = document["items"][0]
    built = build.build_item(item, path=EXAMPLE, report=Report(), max_seeds=1)
    solution = built.variants[0]["solutions"]["q1"]["solution"]
    assert solution[-1] is None
    assert all(not isinstance(v, str) for v in solution)


def test_la_variante_guarda_la_presentacion_real_de_las_opciones():
    """Muestreo y mezcla se materializan: la variante es lo que el estudiante vio."""
    document = loader.load_file(EXAMPLE)
    item = document["items"][0]
    built = build.build_item(item, path=EXAMPLE, report=Report(), max_seeds=1)
    variant = built.variants[0]

    question = next(q for q in variant["public"]["questions"] if q["id"] == "q4")
    shown = [o["text"] for o in question["options"]]
    assert shown[-1] == "Ninguna de las anteriores"      # anclada al final
    assert len(question["options"]) == 5                 # 1 correcta + 3 distractores + NOTA
    assert not any("correct" in o for o in question["options"])

    correct_keys = variant["solutions"]["q4"]["correct"]
    assert len(correct_keys) == 1
    assert correct_keys[0] in {o["key"] for o in question["options"]}


def test_ida_y_vuelta_construir_y_calificar():
    """La solución materializada, devuelta como respuesta, debe dar nota completa."""
    from policlase_gen.grading import grade

    document = loader.load_file(EXAMPLE)
    item = document["items"][0]
    built = build.build_item(item, path=EXAMPLE, report=Report(), max_seeds=3)

    for variant in built.variants:
        solutions = variant["solutions"]
        for question in variant["public"]["questions"]:
            qid = question["id"]
            record = solutions[qid]
            if question["type"] in ("numeric", "numeric_list"):
                answer = record["solution"]
            elif question["type"] == "choice":
                answer = record["correct"][0]
            else:
                continue
            # Se le pasa el registro completo de la variante, no el ítem fuente: es lo que
            # hará el servidor al calificar.
            result = grade(question, answer, solution=record, seed=variant["seed"])
            assert result.correct, f"{qid} en la semilla {variant['seed']}: {result.format_errors}"
            assert result.points == question["points"]


def test_editar_el_item_no_altera_una_variante_ya_publicada():
    """El corazón de la inmutabilidad de la capa 2.

    Si el calificador recalculara la presentación desde el ítem fuente, reordenar las
    opciones en octubre cambiaría cuál es la correcta en un examen de septiembre.
    """
    from policlase_gen.grading import grade

    document = loader.load_file(EXAMPLE)
    item = document["items"][0]
    built = build.build_item(item, path=EXAMPLE, report=Report(), max_seeds=1)
    variant = built.variants[0]
    question = next(q for q in variant["public"]["questions"] if q["id"] == "q4")
    record = variant["solutions"]["q4"]

    # El autor reordena las opciones del ítem fuente después de publicar.
    item["questions"][3]["options"].reverse()

    result = grade(question, record["correct"][0], solution=record, seed=variant["seed"])
    assert result.correct


# ------------------------------------- el validador corriendo generadores de verdad


def _course(tmp_path: Path, generator_body: str, variables: str) -> Path:
    (tmp_path / "generators").mkdir()
    (tmp_path / "generators" / "g.py").write_text(generator_body, encoding="utf-8")
    item = tmp_path / "item.yaml"
    item.write_text(f"""
schema: policlase.item/v1
items:
  - id: U01-x
    points: 1
    generator: {{ file: generators/g.py, seeds: 1..3 }}
    variables:
{variables}
    stem: "Sea $a = {{{{ a }}}}$."
    questions:
      - id: q1
        type: numeric
        points: 1
        prompt: "¿Cuánto vale?"
        solution: "{{{{ b }}}}"
        grading: {{ rtol: 0.01 }}
""", encoding="utf-8")
    return item


def _codes_of(path: Path) -> list[str]:
    from policlase_gen.validate import validate_file
    return sorted(d.code for d in validate_file(path))


OK_GEN = """
def generate(seed):
    return {"public": {"a": seed}, "private": {"b": seed * 2}}
"""
VARS = "      public:  [a]\n      private: [b]"


def test_generador_correcto_pasa_la_validacion(tmp_path):
    assert _codes_of(_course(tmp_path, OK_GEN, VARS)) == ["I030"]


def test_E022_clave_devuelta_de_mas(tmp_path):
    body = """
def generate(seed):
    return {"public": {"a": seed, "sobrante": 1}, "private": {"b": seed * 2}}
"""
    assert "E022" in _codes_of(_course(tmp_path, body, VARS))


def test_E023_clave_declarada_que_falta(tmp_path):
    body = """
def generate(seed):
    return {"public": {"a": seed}, "private": {}}
"""
    codes = _codes_of(_course(tmp_path, body, VARS))
    assert "E023" in codes


def test_E024_nan_en_lugar_de_none(tmp_path):
    body = """
def generate(seed):
    return {"public": {"a": seed}, "private": {"b": float("nan")}}
"""
    assert "E024" in _codes_of(_course(tmp_path, body, VARS))


def test_E025_generador_no_determinista(tmp_path):
    body = """
import random
def generate(seed):
    return {"public": {"a": random.random()}, "private": {"b": 1}}
"""
    assert "E025" in _codes_of(_course(tmp_path, body, VARS))


def test_E026_generador_que_revienta(tmp_path):
    body = """
def generate(seed):
    raise RuntimeError("boom")
"""
    assert "E026" in _codes_of(_course(tmp_path, body, VARS))


def test_E026_generador_que_se_cuelga(tmp_path):
    """El tiempo límite existe porque un bucle infinito colgaría el build entero."""
    body = """
def generate(seed):
    while True:
        pass
"""
    item = _course(tmp_path, body, VARS)
    item.write_text(item.read_text(encoding="utf-8").replace(
        "seeds: 1..3 }", "seeds: 1..3, timeout_s: 0.3 }"), encoding="utf-8")
    assert "E026" in _codes_of(item)


def test_E027_forma_incorrecta_del_retorno(tmp_path):
    body = """
def generate(seed):
    return [1, 2, 3]
"""
    # Se reporta como E026: el fallo llega envuelto en GeneratorError al correr la semilla.
    assert "E026" in _codes_of(_course(tmp_path, body, VARS))


def test_E004_tipo_invalido_en_points():
    from policlase_gen import loader
    from policlase_gen.validate import validate_document
    document = loader.load_text("""
schema: policlase.item/v1
items:
  - id: U01-x
    points: "mucho"
    questions:
      - id: q1
        type: numeric
        points: 1
        solution: 1
        grading: { rtol: 0.01 }
""")
    assert "E004" in {d.code for d in validate_document(document, run_generators=False)}
