# policlase-gen

Cadena de herramientas de autoría de preguntas de **policlase**: el esquema YAML, el validador, el
contrato del generador sembrado y la CLI que materializa las variantes de cada estudiante.

Es un paquete autónomo. No tiene autenticación, ni base de datos, ni servidor: corre en tu
computador y produce archivos. La plataforma `policlase` lo importa como dependencia, de modo que
servidor y CLI no puedan discrepar sobre qué es un ítem válido.

## Por qué existe

Las preguntas se escriben una vez y se instancian por estudiante a partir de una semilla, de manera
que dos estudiantes resuelven el mismo problema con valores distintos. El generador de valores es
código de Python **que corre en tu máquina, nunca en el servidor** — de ahí la separación entre este
repositorio y la plataforma.

## Documentación

- [`docs/schema.md`](docs/schema.md) — referencia normativa del formato.
- [`examples/biseccion/`](examples/biseccion/) — un ítem completo con su generador.

## Estado

Borrador de `policlase.item/v1`. El esquema se congela tras el primer semestre en uso.

## Licencia

MIT.
