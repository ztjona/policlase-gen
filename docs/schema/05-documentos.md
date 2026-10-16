# 5. Documentos de contenido

[← Índice](../schema.md)

Una clase en vivo, una actividad, una evaluación y un repaso se escriben con **el mismo formato** y
en el mismo editor: una secuencia de diapositivas de contenido, ítems, soluciones y **segmentos**.
`use` dice para qué es el documento y pone los comportamientos por omisión; un segmento los cambia
para lo que le sigue.

```yaml
schema: policlase/v1
title: 'Deber 1 — Teclado y LaTeX'
use: activity                       # class · activity · evaluation · practice
instructions: |                     # se ven antes de empezar (no en una clase)
  Resuelva a su ritmo. La última parte tiene tiempo por pregunta.

slides:
  - markdown: |
      ## La distribución del teclado
      Lo que cuenta es la configurada en el sistema, no lo impreso en las teclas.

  - item:
      id: U00-teclado
      questions:
        - id: q1
          type: choice
          prompt: '¿Qué distribución tiene su teclado?'
          grading: { mode: survey }
          options: [{ text: 'Español (Latinoamérica)' }, { text: 'Español (España)' }, { text: 'Inglés' }]

  - segment:                        # desde aquí: 15 s por pregunta y sin pegar
      title: 'Símbolos'
      time_limit_s: 15
      block_paste: true

  - item:
      id: U00-barra
      questions:
        - { id: q1, type: text, prompt: 'Escriba la barra invertida.', grading: { accept: ['\'], normalize: [] } }

  - solution: |                     # explica el ítem anterior (U00-barra)
      ## Cómo escribir la barra invertida
      En el teclado latinoamericano: AltGr + `?`.

  - segment: {}                     # vuelve a lo del documento
```

## Campos

| Campo | Tipo | | Descripción |
|---|---|---|---|
| `schema` | string | **requerido** | `policlase/v1` (`E002` si es otra versión). |
| `title` | string | **requerido** | Lo ven docente y estudiantes (`E003` si falta). |
| `use` | `class` · `activity` · `evaluation` · `practice` | **requerido** | Clase en vivo (pestaña Clases), actividad (pestaña Actividades), evaluación o repaso (pestaña Evaluaciones). `E086` si es otro valor. |
| `instructions` | markdown | opcional | Indicaciones generales; se muestran antes de empezar (actividades, evaluaciones y repasos). |
| `slides` | array | **requerido** | Cada elemento tiene **exactamente una** de `markdown`, `item`, `segment` o `solution` (`E080`), y al menos uno es contenido o un ítem (`E004`). |
| `slides[].markdown` | markdown | — | Contenido. En una actividad se lee entre los ítems. |
| `slides[].item` | item | — | Un ítem ([parte 3](03-items-y-preguntas.md)). En una clase, con las restricciones de abajo. |
| `slides[].solution` | markdown | — | La explicación **del ítem que la precede**. El estudiante no la ve mientras responde ([parte 6](06-reglas-de-la-plataforma.md#explicaciones)). Sin un ítem antes, se avisa (`W099`); en una clase se ignora (`W096`). |
| `slides[].segment` | mapping | — | `title`, `instructions` y comportamientos (abajo) desde aquí hasta el próximo segmento. Cada segmento parte de lo del documento: `segment: {}` vuelve a él. |
| `slides[].notes` | string | opcional | Notas para el docente. |
| `slides[].hidden` | boolean | `false` | Queda en el archivo, pero no se presenta ni se responde (`E085` si no es booleano). |
| `meta` | mapping | opcional | Datos libres. |

**Comportamientos.** En la raíz valen para todo el documento; en un segmento, para sus
diapositivas. `use` pone los valores por omisión. Una clave que no aplica al uso se ignora con un
aviso (`W087`).

| Clave | `class` | `activity` | `evaluation` | `practice` | Qué hace |
|---|---|---|---|---|---|
| `time_limit_s` (5–600 o `null`) | `30` | `null` | `null` | — | El tiempo de cada pregunta (`E084` fuera de rango). Cómo se aplica: [parte 6](06-reglas-de-la-plataforma.md#preguntas-con-tiempo). |
| `block_paste` | — | `false` | `true` | `false` | Impide pegar texto en las respuestas (`E085` si no es booleano). |
| `speed_bonus` (solo raíz) | `true` | — | — | — | Bono por rapidez en el marcador de la clase (no en la nota). |
| `feedback` (solo raíz) | `true` | — | — | — | Retroalimentación anónima al final de la clase. |

## El archivo describe solo el contenido

Cuándo abre y vence una actividad, a qué fila de la ponderación pertenece, cuántos intentos admite,
qué pasa con lo atrasado, el horario de una evaluación o cuándo abre un repaso lo decide el docente
en la plataforma: reprogramar una prueba no debe exigir un commit por deber, y la misma actividad
sirve otro semestre con otras fechas. Una clave como `due` en el archivo es un error (`E001`). Las
claves `category`, `weight`, `extra_credit` y `grading_granularity` de un ítem se siguen aceptando por
compatibilidad, pero no se usan.

## Clases en vivo (`use: class`)

En clase todos ven lo mismo al mismo tiempo, así que un ítem en vivo:

- lleva **una sola pregunta, sin `follow_ups`** (`E081`);
- **no se aleatoriza** (`E083`): ni `generator`, ni `variables`, ni marcadores `{{ }}`;
- es de un **tipo que se responde con un toque o un número** (`E082`): `choice`, `multi_choice`,
  `true_false`, `numeric` o `text`.

`item.lecture.time_limit_s` todavía manda sobre el segmento para esa pregunta; `null` (o `.inf`) es
sin límite: no lleva bono por rapidez y la cierra el docente o se cierra sola cuando respondieron
todos. Con bono, una respuesta correcta vale en el marcador entre el 50 % (al final del tiempo) y el
100 % (al instante) de sus puntos de juego; la nota de participación solo cuenta si se acertó.

La retroalimentación final no es un ítem: no da puntos ni entra en el marcador, se guarda sin
vínculo con el estudiante, y el docente ve el resumen solo con al menos tres respuestas.

El orden de las diapositivas y `hidden` se pueden cambiar desde el panel del editor web, que edita
solo las líneas afectadas: el diff en git queda igual que si se hubiera hecho a mano.

## Actividades, evaluaciones y repasos

Admiten todos los tipos de pregunta, varias preguntas por ítem y `follow_ups`, que se muestran en
orden de lectura. **Sin aleatorización por ahora** (`E092`). Las preguntas de debate solo existen en
las actividades (`W097`); el tiempo por pregunta, en actividades y evaluaciones (`W087` en un repaso).

## Forma compilada

`policlase_gen.document.compile_content` produce la de una presentación para `use: class` y la de
una actividad para los demás usos:

- Cada pregunta lleva su `key` (`<id del ítem>.<id de la pregunta>`), única en el documento, y en una
  actividad su `time_limit_s`, su `block_paste` y, si corresponde, `debate: true`.
- Los segmentos, el contenido y las soluciones son bloques (`kind: segment` / `content` /
  `solution`) entre los ítems (`kind: item`). Cada ítem lleva su `title` (vacío si no lo tiene);
  cada solución, el ítem que explica (`explains` y `explains_title`; vacíos si no hay un ítem antes).
- Todo lleva `at`, su posición en `slides`, para que el editor lo ubique.
- Las opciones salen con su clave estable y las soluciones en un subárbol aparte (`solutions`;
  [parte 3](03-items-y-preguntas.md#el-registro-de-solución)).
- `review: true` si alguna pregunta la califica una persona; `ai: true` si alguna está marcada con
  `grading.mode: ai`.

## Formatos anteriores

`policlase.deck/v1` (una clase) y `policlase.activity/v1` (una actividad) se siguen aceptando y
compilan igual que `use: class` y `use: activity`; no tienen segmentos ni soluciones.

- **`policlase.deck/v1`**: `schema`, `title`, `slides` (cada una con `markdown` o `item`, `notes` y
  `hidden`), `defaults.time_limit_s` (30 por omisión), `speed_bonus` y `feedback`.
- **`policlase.activity/v1`**: `schema`, `title`, `instructions` e `items` (los ítems directamente,
  sin diapositivas).
