# 3. Ítems y preguntas

[← Índice](../schema.md)

## El objeto `item`

Un ítem es la unidad de autoría, de versionado y de analítica: un enunciado compartido y las
preguntas que cuelgan de él. Se escribe igual en un banco de ítems (abajo) y dentro de un
documento de contenido ([parte 5](05-documentos.md)).

| Campo | Tipo | | Descripción |
|---|---|---|---|
| `id` | string | **requerido** | Único en el curso (`E010`). Solo `[a-zA-Z0-9._-]` (`E011`). Clave de la analítica histórica; se trata como permanente. |
| `title` | string | opcional | Nombre corto: lo usan el índice del intento y los listados. |
| `tags` | array\<string\> | opcional | Temas. Habilitan el reporte de dominio por tema y la reutilización entre semestres. |
| `difficulty` | integer 1–5 | opcional | La estimación del docente; la dificultad observada se calcula aparte. |
| `points` | number | suma de las preguntas | Si se declara, debe igualar la suma de sus preguntas (`E050`). |
| `generator` | object | opcional | Variantes por estudiante ([parte 4](04-generador.md)). |
| `variables` | object | condicional | Requerido con `generator`: dos listas, `public` y `private`. |
| `stem` | string (markdown) | opcional | Enunciado común, encima de todas las preguntas. |
| `questions` | array\<question\> | **requerido** | Al menos una; cada `id` único dentro del ítem (`E012`). |

**La separación entre `public` y `private` es estructural, no un filtro**: las variables privadas
viven en un subárbol que el serializador del estudiante no puede alcanzar.

### Bancos de ítems (`policlase.item/v1`)

Un archivo de ítems sueltos (para reutilizarlos o generar variantes) tiene en la raíz `schema`
(requerido; una versión desconocida es `E002`), `items` (la lista) y `meta`, con valores por omisión
para todos sus ítems: `meta.locale` (`es-EC`; formato de los números al mostrarlos y mensajes al
estudiante) y `meta.decimal_input` (`both` · `point` · `comma`; cómo se interpreta lo que el
estudiante escribe). `both` acepta `4.23` y `4,23`, y es seguro porque las listas numéricas usan
una casilla por celda.

## Tipos de pregunta

Toda pregunta tiene `id`, `type` (`E040` si es desconocido), `prompt`, `points` (1 si se omite) y,
salvo `open` e `image`, una `solution`. El bloque `grading` cambia según el tipo.

### `numeric`

```yaml
- id: q2
  type: numeric
  prompt: '¿Cuántas raíces hay en $[1, 3]$?'
  solution: 1
  grading:
    integer: true          # rechaza 2.0001 en una pregunta de conteo
    rtol: 0.01             # tolerancia relativa
    atol: 1.0e-9           # absoluta; domina cerca de cero
    units: 'm/s'           # opcional; si está, la unidad es obligatoria
```

Se acepta si `|a − b| ≤ atol + rtol·|b|`. Debe tener `rtol` o `atol` (`E042`). Declarar solo `rtol`
hace fallar toda respuesta cercana a cero: es el error más común al escribir tolerancias.

### `numeric_list`

Varios valores en una rejilla, una casilla por celda.

```yaml
- id: q1
  type: numeric_list
  points: 4
  shape: [1, 3]                         # debe concordar con la longitud de solution (E041)
  solution: [-1.0, 1.0, null]           # null: «no existe»
  grading:
    rtol: 0.01
    order: ascending                    # sorted · ascending · descending · exact · any
    partial: per_cell                   # per_cell · all_or_nothing
    nan_aliases: ['NaN', 'nan', 'no existe', '-']
```

`order` lleva al calificador lo que antes solo decía el enunciado; con `any` se comparan como conjuntos.

### `expression`

El estudiante escribe una expresión algebraica.

```yaml
- id: q1
  type: expression
  points: 3
  prompt: 'Sea $f(x) = x^3 \sin x$. Escriba $f''(x)$.'
  solution: '3*x**2*sin(x) + x**3*cos(x)'   # infija plana, NO LaTeX
  grading:
    vars: [x]                              # un símbolo ausente es E044
    domain: { x: [-3, 3] }
    sample_points: 20
    rtol: 1.0e-6
    allow: [sin, cos, tan, exp, ln, log, sqrt, abs, pi, e]
```

**La solución es una expresión plana, en el mismo lenguaje que teclea el estudiante**, no LaTeX.
Sintaxis: números, los símbolos de `vars`, `pi` y `e` (constantes, salvo que una variable declarada
se llame así), las funciones de `allow`, `+ - * / % ** ^` y paréntesis. **La multiplicación es
explícita** (`2*x`, no `2x`; escribir `2x` produce un mensaje que lo dice). Todo lo demás se
rechaza en el árbol sintáctico antes de evaluar: nunca `eval()` ni `sympify()` sobre una cadena.

Se compara **por muestreo numérico**: ambas expresiones se evalúan en puntos aleatorios del dominio.
Así `(x-1)(x+1)` y `x^2-1` son equivalentes sin simplificación simbólica, y la comparación no puede
colgarse.

### `choice`

Una sola opción correcta (`E043` si hay cero o más de una).

```yaml
- id: q4
  type: choice
  points: 2
  options:
    - { text: 'Rango con signos iguales: no hay solución.', correct: true }
    - { text: 'Solución única.' }
    - { text: 'Infinitas soluciones.' }
  none_of_the_above: true
  sample: { distractors: 3, shuffle: seeded }
```

Se declaran todos los distractores y `sample.distractors` elige cuántos mostrar, de forma
determinista según la semilla. `none_of_the_above` agrega esa opción y la ancla al final; si nunca
es la correcta en ninguna variante, se avisa (`W070`): los estudiantes aprenden a descartarla.

**Encuesta** (`grading: { mode: survey }`, también en `multi_choice`): se registra lo elegido, sin
opción correcta (`E093`) ni puntos (`E094` si `points` no es 0). La plataforma nunca la muestra como
correcta o incorrecta, y al docente le muestra cuántos eligieron cada opción.

### `multi_choice`

Varias opciones correctas (`E048` si no hay ninguna, salvo en una encuesta); se marcan todas las
que apliquen.

```yaml
grading:
  partial: per_option    # per_option · all_or_nothing
  penalty: 1.0           # cada marca incorrecta anula un acierto
  floor: 0               # la pregunta nunca aporta negativo
```

Con `per_option`: `nota = max(floor, (aciertos − penalty × errores) / correctas) × points`. **Una
`penalty` menor que 1 premia marcar todo** y se avisa (`W071`).

### `true_false`

Un bloque de afirmaciones; cada una declara `answer` (`E047`).

```yaml
- id: q2
  type: true_false
  points: 4
  statements:
    - { text: 'La bisección converge si hay cambio de signo.', answer: true }
    - { text: 'Newton garantiza convergencia global.', answer: false }
  grading: { partial: per_statement, penalty: 1.0, floor: 0 }   # o all_or_nothing
```

Los puntos se reparten por igual entre las afirmaciones. El azar da 50 % en este tipo: con
`penalty: 1.0` una respuesta al azar tiende a cero.

### `text`

Respuesta corta comparada literalmente, para términos, nombres y símbolos.

```yaml
grading:
  accept: ['bisección', 'método de bisección']
  normalize: [lowercase, strip_accents, collapse_spaces]   # también strip_punctuation
```

Sin `normalize` se aplican las tres del ejemplo; `normalize: []` compara literalmente (para `\` o
`{`, o cuando importan las mayúsculas).

### `open`

Respuesta escrita, que califica el docente, con rúbrica opcional y una respuesta de referencia que
solo ve quien califica.

```yaml
- id: q4a
  type: open
  points: 2
  prompt: '¿Qué método es más adecuado para este rango y por qué?'
  grading:
    mode: manual                # manual · ai
    reference: |
      Se espera que note que $f(a)$ y $f(b)$ tienen el mismo signo...
    rubric:
      - { criterion: 'Identifica que no hay cambio de signo', points: 1 }
      - { criterion: 'Propone un método alternativo y lo justifica', points: 1 }
```

Los puntos de la rúbrica deben sumar los de la pregunta (`E046`); `mode: ai` exige rúbrica (`E045`)
y marca la pregunta para que la plataforma proponga una calificación, que el docente revisa
siempre antes de que la vea el estudiante ([parte 6](06-reglas-de-la-plataforma.md#calificación-asistida-por-ia)).

### `image`

Una o varias imágenes que sube el estudiante (la foto del desarrollo a mano, un certificado). La
califica el docente, como `open`, con rúbrica opcional. `max_files` va de 1 a 10 (1 por omisión;
`E091` fuera de rango). En una clase en vivo no se responde (`E082`). Qué formatos se aceptan y cómo
se guardan es de la plataforma (JPEG, PNG y WebP, re-codificados sin metadatos).

`grading.mode` debe existir para el tipo (`E095`): `manual` o `ai` en `open` e `image`; `survey` en
`choice` y `multi_choice`.

## `follow_ups`

Preguntas anidadas que se muestran debajo de la de arriba. Sus `points` son propios y suman al
total del ítem. Anidamiento máximo: un nivel. No existen en vivo (`E081`).

## Preguntas de debate (`debate`)

`debate: true` vuelve una pregunta **de debate**: el estudiante la responde con una justificación y,
desde la fecha de entrega, la discute con sus compañeros ([parte 6](06-reglas-de-la-plataforma.md#debate)).
Solo en actividades: en una clase, una evaluación o un repaso se ignora con un aviso (`W097`).
Admiten debate los tipos con una respuesta breve que se pueda mostrar: `choice`, `multi_choice`,
`true_false`, `numeric`, `numeric_list`, `text` y `expression` (`E098` en `open` e `image`; `E085`
si no es booleano). Conviene una o dos por actividad, en preguntas cuyos errores frecuentes valga la
pena discutir.

```yaml
- id: q1
  type: choice
  debate: true
  prompt: '¿Qué método converge más rápido cerca de una raíz simple?'
  options: [{ text: 'Bisección' }, { text: 'Newton-Raphson', correct: true }, { text: 'Punto fijo' }]
```

## El registro de solución

Lo compilado separa lo que ve el estudiante de lo que usa el calificador:

```json
{
  "public":    { "stem": "...", "questions": [ { "id": "q4", "options": [ {"key": "o0_4c9c5ff6", "text": "..."} ] } ] },
  "solutions": { "q1": { "solution": [-1.0, 1.0, null] }, "q4": { "correct": ["o3_cbc5ab1d"] } }
}
```

- **La solución conserva su tipo, no su texto**: `null` es un valor, no la cadena `\mathrm{NaN}`;
  las soluciones se comparan, no se muestran.
- **La mezcla de opciones se materializa al compilar**: las opciones guardadas, con su `key`
  estable, son literalmente las que vio el estudiante, y el calificador nunca recalcula la
  presentación desde la fuente.
- **La rúbrica es pública** (el estudiante sabe con qué se le califica); la referencia, no.
