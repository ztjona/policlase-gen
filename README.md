# policlase-gen

Cadena de herramientas de autoría de preguntas de **policlase**: el esquema YAML, el validador, el
contrato del generador sembrado y la CLI que materializa las variantes de cada estudiante.

Es un paquete autónomo. No tiene autenticación, ni base de datos, ni servidor: corre en tu
computador y produce archivos. La plataforma `policlase` lo importa como dependencia, de modo que
servidor y CLI no puedan discrepar sobre qué es un ítem válido ni sobre cómo se califica una
respuesta.

## Por qué existe

Las preguntas se escriben una vez y se instancian por estudiante a partir de una semilla, de manera
que dos estudiantes resuelven el mismo problema con valores distintos. El generador de valores es
código de Python **que corre en tu máquina, nunca en el servidor**: `build` sube variantes ya
materializadas. Eso elimina por completo el problema de ejecutar código de autoría en producción.

## Instalación

```bash
pip install -e ".[dev]"
```

## Uso

```bash
policlase validate cursos/            # valida; --strict hace que los avisos bloqueen (así corre CI)
policlase build cursos/ -o out/       # materializa las variantes a JSON
policlase preview item.yaml --seed 7 --solutions
```

`validate` corre idéntico en tu editor, en el *hook* de pre-commit y en CI. Cada diagnóstico cita
archivo, línea, ítem y —cuando aplica— la semilla que reprodujo el fallo, de modo que
`policlase build --seed 47` lo reproduce de inmediato.

## Documentación

- [`docs/schema.md`](docs/schema.md) — referencia normativa del formato y catálogo de diagnósticos.
- [`policlase/docs/github.md`](../policlase/docs/github.md) — cómo la plataforma sincroniza las presentaciones con un repositorio (carpetas = secciones).
- [`policlase/docs/guia-de-estilo.md`](../policlase/docs/guia-de-estilo.md) — guía de estilo y patrones de código de ambos repositorios.
- [`examples/biseccion/`](examples/biseccion/) — dos ítems generados y uno de lección, con sus
  generadores.
- [`examples/clase-en-vivo/`](examples/clase-en-vivo/) — una presentación para clase en vivo.

## Estado

Borrador de `policlase.item/v1`. El esquema se congela tras el primer semestre en uso.

## Licencia

MIT.
