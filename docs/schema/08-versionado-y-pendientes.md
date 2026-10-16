# 8. Versionado y pendientes

[← Índice](../schema.md)

## Versionado

El campo `schema` usa `nombre/vN`. Dentro de una versión mayor solo se agregan campos opcionales;
renombrar o eliminar un campo, o cambiar el significado de uno existente, exige `v2` y un migrador
incluido en el paquete público.

Aparte, cada ítem lleva una `item_version` interna que cambia con su contenido. Lo que un estudiante
vio conserva la versión con la que lo vio ([parte 1](01-modelo-y-repositorios.md)): es lo que permite
comparar el rendimiento de un ítem entre semestres sabiendo si es realmente el mismo.

## Pendientes

- **Variantes por estudiante en actividades y evaluaciones.** El formato las admite
  ([parte 4](04-generador.md)), pero la plataforma aún no recibe las variantes compiladas (`E092`).
  Se construirán en el computador del docente y llegarán por GitHub.
- **Respuestas en LaTeX calificadas.** `expression` compara expresiones de una línea; leer LaTeX
  (`\frac`, `\sqrt`, sumatorias) y evaluarlo por valor queda para más adelante.
- **Calificación asistida de imágenes.** La IA propone notas de respuestas abiertas
  ([parte 6](06-reglas-de-la-plataforma.md#calificación-asistida-por-ia)); las fotos de un
  desarrollo a mano necesitarían un modelo que lea imágenes.
