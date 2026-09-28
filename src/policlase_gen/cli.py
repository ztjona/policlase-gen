"""Interfaz de línea de comandos.

``policlase validate`` corre idéntico aquí, en el *hook* de pre-commit y en CI; la única
diferencia es ``--strict``, que hace que los avisos también bloqueen.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import build as build_mod
from . import loader, template
from .errors import Report, Severity
from .validate import DEFAULT_ENROLLED, validate_file

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
GREEN = "\033[32m"
COLORS = {Severity.ERROR: "\033[31m", Severity.WARNING: "\033[33m", Severity.INFO: "\033[36m"}


def _color(enabled: bool):
    if enabled:
        return lambda text, code="": f"{code}{text}{RESET}"
    return lambda text, code="": text


def _targets(paths: list[str]) -> list[Path]:
    found: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found.extend(sorted(p for p in path.rglob("*.y*ml") if p.is_file()))
        else:
            found.append(path)
    return found


def _print_report(report: Report, paint) -> None:
    for diagnostic in sorted(report, key=lambda d: (d.severity is not Severity.ERROR, d.code)):
        head = paint(f"{diagnostic.code} {diagnostic.severity.value}", COLORS[diagnostic.severity])
        print(f"  {head}: {diagnostic.message}")
        location = diagnostic.location()
        if location:
            print(paint(f"        {location}", DIM))


def cmd_validate(args) -> int:
    paint = _color(sys.stdout.isatty() and not args.no_color)
    total = Report()

    for path in _targets(args.paths):
        report = validate_file(
            path,
            run_generators=not args.no_generators,
            enrolled=args.enrolled,
            max_seeds=args.max_seeds,
        )
        total.extend(report)
        status = "OK" if report.ok(args.strict) else "FALLA"
        colour = GREEN if report.ok(args.strict) else COLORS[Severity.ERROR]
        print(f"{paint(status, colour)} {paint(str(path), BOLD)}")
        _print_report(report, paint)

    errors, warnings = len(total.errors), len(total.warnings)
    print(f"\n{errors} error(es), {warnings} aviso(s)")
    if args.strict and warnings:
        print(paint("--strict: los avisos también bloquean", DIM))
    return 0 if total.ok(args.strict) else 1


def cmd_build(args) -> int:
    paint = _color(sys.stdout.isatty() and not args.no_color)
    total = Report()
    built_count = 0

    for path in _targets(args.paths):
        report = validate_file(path, run_generators=False, enrolled=args.enrolled)
        if report.errors:
            print(f"{paint('FALLA', COLORS[Severity.ERROR])} {path} — no se construye con errores")
            _print_report(report, paint)
            total.extend(report)
            continue

        items = build_mod.build_file(
            path, out_dir=args.out, enrolled=args.enrolled,
            report=total, max_seeds=args.max_seeds,
        )
        for item in items:
            built_count += 1
            collisions = item.collisions
            note = f"{item.distinct} variantes distintas"
            if collisions >= 1:
                note += paint(
                    f" · ~{collisions} de {item.enrolled} estudiantes compartirán variante",
                    COLORS[Severity.WARNING],
                )
            label = paint("OK", GREEN)
            print(f"{label} {paint(item.item_id, BOLD)} "
                  f"({len(item.variants)} variantes, versión {item.item_version}) — {note}")

    if args.out:
        print(paint(f"\nEscrito en {Path(args.out).resolve()}", DIM))
    print(f"{built_count} ítem(s) construido(s), {len(total.errors)} error(es)")
    return 0 if not total.errors else 1


def cmd_preview(args) -> int:
    """Renderiza una semilla concreta a Markdown, para revisarla de un vistazo."""
    paint = _color(sys.stdout.isatty() and not args.no_color)
    document = loader.load_file(args.path)

    for item in document.get("items") or []:
        if args.item and item.get("id") != args.item:
            continue
        built = build_mod.build_item(
            item, path=Path(args.path), enrolled=args.enrolled, max_seeds=None,
        )
        variant = next(
            (v for v in built.variants if v["seed"] == args.seed), built.variants[0] if built.variants else None
        )
        if variant is None:
            print(f"sin variantes para {item.get('id')}")
            continue

        print(paint(f"\n# {item.get('id')} — semilla {variant['seed']}", BOLD))
        if variant["public"].get("stem"):
            print(f"\n{variant['public']['stem'].strip()}\n")
        for question in variant["public"]["questions"]:
            _print_question(question, variant["solutions"], paint, show_solutions=args.solutions)
    return 0


def _print_question(question, solutions, paint, show_solutions, indent="") -> None:
    points = question.get("points")
    print(paint(f"{indent}## {question['id']} · {question['type']} · {points} pt", BOLD))
    if question.get("prompt"):
        print(f"{indent}{question['prompt'].strip()}")
    for option in question.get("options") or []:
        print(f"{indent}  - {option['text']}")
    for statement in question.get("statements") or []:
        print(f"{indent}  [ ] {statement['text']}")

    if show_solutions and question["id"] in solutions:
        detail = solutions[question["id"]]
        print(paint(f"{indent}  → {detail}", DIM))
    for follow_up in question.get("follow_ups") or []:
        _print_question(follow_up, solutions, paint, show_solutions, indent + "  ")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="policlase",
        description="Autoría y validación de ítems de policlase.",
    )
    parser.add_argument("--no-color", action="store_true", help="salida sin colores")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--enrolled", type=int, default=DEFAULT_ENROLLED,
                        help="matrícula del curso, para el reporte de entropía")
    common.add_argument("--max-seeds", type=int, default=None,
                        help="limita las semillas, para iterar rápido")

    validate = sub.add_parser("validate", parents=[common], help="valida archivos de ítems")
    validate.add_argument("paths", nargs="+")
    validate.add_argument("--strict", action="store_true",
                          help="los avisos también bloquean (así corre CI)")
    validate.add_argument("--no-generators", action="store_true",
                          help="omite correr los generadores")
    validate.set_defaults(func=cmd_validate)

    build = sub.add_parser("build", parents=[common], help="materializa las variantes")
    build.add_argument("paths", nargs="+")
    build.add_argument("-o", "--out", default=None, help="directorio de salida")
    build.set_defaults(func=cmd_build)

    preview = sub.add_parser("preview", parents=[common], help="renderiza una semilla")
    preview.add_argument("path")
    preview.add_argument("--seed", type=int, default=1)
    preview.add_argument("--item", default=None, help="solo este id de ítem")
    preview.add_argument("--solutions", action="store_true", help="muestra las respuestas")
    preview.set_defaults(func=cmd_preview)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except loader.LoadError as exc:
        print(f"YAML inválido — {exc}", file=sys.stderr)
        return 2
    except (template.TemplateError, OSError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":                        # pragma: no cover
    raise SystemExit(main())
