# 7. Catálogo de validación

[← Índice](../schema.md)

`policlase validate` corre idéntico en el editor web, en el *hook* de pre-*commit* y en CI. Un error
(`E`) impide guardar o publicar; un aviso (`W`) bloquea solo en CI, donde el umbral es más estricto;
un código `I` es informativo. Cada mensaje cita archivo, línea, `id` del ítem y, cuando aplica, la
semilla que reprodujo el fallo, de modo que `policlase build --seed 47` lo reproduce de inmediato.

| Código | Condición | Dónde se explica |
|---|---|---|
| `E001` | Clave desconocida. | [3](03-items-y-preguntas.md), [5](05-documentos.md) |
| `E002` | Versión de `schema` desconocida. | [3](03-items-y-preguntas.md#bancos-de-ítems-policlaseitemv1), [5](05-documentos.md#campos) |
| `E003` | Falta una clave requerida. | [3](03-items-y-preguntas.md), [5](05-documentos.md) |
| `E004` | Tipo inválido en una clave (o un documento sin contenido ni ítems). | [3](03-items-y-preguntas.md), [5](05-documentos.md) |
| `E010` | `id` de ítem duplicado en el curso. | [3](03-items-y-preguntas.md#el-objeto-item) |
| `E011` | `id` con caracteres fuera de `[a-zA-Z0-9._-]`. | [3](03-items-y-preguntas.md#el-objeto-item) |
| `E012` | `id` de pregunta duplicado dentro del ítem. | [3](03-items-y-preguntas.md#el-objeto-item) |
| `E020` | Un marcador `{{ x }}` no está en `variables`. | [2](02-yaml-plantillas-markdown.md#marcadores-de-plantilla) |
| `W021` | Una variable declarada no se usa. | [2](02-yaml-plantillas-markdown.md#marcadores-de-plantilla) |
| `E022` | El generador devolvió una clave no declarada. | [4](04-generador.md#reglas-obligatorias) |
| `E023` | El generador omitió una clave declarada. | [4](04-generador.md#reglas-obligatorias) |
| `E024` | Valor no serializable (típicamente `float('nan')`). | [4](04-generador.md#reglas-obligatorias) |
| `E025` | No determinista: dos corridas de la misma semilla difieren. | [4](04-generador.md#reglas-obligatorias) |
| `E026` | El generador lanzó una excepción o excedió el tiempo. | [4](04-generador.md#reglas-obligatorias) |
| `E027` | El generador no devolvió un dict con `public` y `private`. | [4](04-generador.md#reglas-obligatorias) |
| `I030` | Entropía: variantes distintas y colisiones esperadas. | [4](04-generador.md#entropía-de-variantes) |
| `E040` | Tipo de pregunta desconocido. | [3](03-items-y-preguntas.md#tipos-de-pregunta) |
| `E041` | `shape` no concuerda con la longitud de `solution`. | [3](03-items-y-preguntas.md#numeric_list) |
| `E042` | Tipo numérico sin `rtol` ni `atol`. | [3](03-items-y-preguntas.md#numeric) |
| `E043` | `choice` sin opción correcta, o con más de una. | [3](03-items-y-preguntas.md#choice) |
| `E044` | `expression` usa un símbolo ausente de `vars`. | [3](03-items-y-preguntas.md#expression) |
| `E045` | `mode: ai` sin `rubric`. | [3](03-items-y-preguntas.md#open) |
| `E046` | Los puntos de la rúbrica no suman los de la pregunta. | [3](03-items-y-preguntas.md#open) |
| `E047` | Una afirmación de `true_false` sin `answer`. | [3](03-items-y-preguntas.md#true_false) |
| `E048` | `multi_choice` sin opción correcta (salvo una encuesta). | [3](03-items-y-preguntas.md#multi_choice) |
| `E050` | Los puntos de las preguntas no suman los del ítem. | [3](03-items-y-preguntas.md#el-objeto-item) |
| `E060` | KaTeX no pudo analizar una fórmula, o hay un `$` sin cerrar. | [2](02-yaml-plantillas-markdown.md#markdown-y-matemáticas) |
| `W061` | LaTeX entre comillas dobles: un escape de YAML se tragó un comando (se corrigió). | [2](02-yaml-plantillas-markdown.md#latex-y-comillas) |
| `W070` | `none_of_the_above` nunca es correcta. | [3](03-items-y-preguntas.md#choice) |
| `W071` | `multi_choice` con `partial: per_option` y `penalty` menor que 1. | [3](03-items-y-preguntas.md#multi_choice) |
| `E080` | Una diapositiva sin `markdown`, `item`, `segment` ni `solution`, o con más de una. | [5](05-documentos.md#campos) |
| `E081` | Ítem en vivo con más de una pregunta o con `follow_ups`. | [5](05-documentos.md#clases-en-vivo-use-class) |
| `E082` | Tipo de pregunta que no se responde en vivo. | [5](05-documentos.md#clases-en-vivo-use-class) |
| `E083` | Aleatorización en una clase (generador, variables o marcadores). | [5](05-documentos.md#clases-en-vivo-use-class) |
| `E084` | `time_limit_s` fuera de 5–600 segundos. | [5](05-documentos.md#campos) |
| `E085` | `hidden`, `feedback`, `speed_bonus`, `block_paste` o `debate` no son booleanos. | [5](05-documentos.md#campos), [3](03-items-y-preguntas.md#preguntas-de-debate-debate) |
| `E086` | `use` no es `class`, `activity`, `evaluation` ni `practice`. | [5](05-documentos.md#campos) |
| `W087` | Un comportamiento que no aplica al uso del documento (se ignora). | [5](05-documentos.md#campos) |
| `E091` | `max_files` de una pregunta `image` fuera de 1–10. | [3](03-items-y-preguntas.md#image) |
| `E092` | Aleatorización en una actividad, evaluación o repaso. | [5](05-documentos.md#actividades-evaluaciones-y-repasos) |
| `E093` | Una encuesta con una opción correcta. | [3](03-items-y-preguntas.md#choice) |
| `E094` | Una encuesta con `points` distinto de 0. | [3](03-items-y-preguntas.md#choice) |
| `E095` | `grading.mode` que no existe para el tipo. | [3](03-items-y-preguntas.md#image) |
| `W096` | Una diapositiva `solution` en una clase (se ignora). | [5](05-documentos.md#campos) |
| `W097` | Una pregunta de debate fuera de una actividad (se ignora). | [3](03-items-y-preguntas.md#preguntas-de-debate-debate) |
| `E098` | Una pregunta `open` o `image` marcada como de debate. | [3](03-items-y-preguntas.md#preguntas-de-debate-debate) |
| `W099` | Una diapositiva `solution` sin un ítem antes. | [5](05-documentos.md#campos) |

El texto exacto de cada mensaje está en `policlase_gen/errors.py`, que es la fuente: una prueba
comprueba que este catálogo y ese archivo tengan los mismos códigos.
