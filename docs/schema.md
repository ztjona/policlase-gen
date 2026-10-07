# Esquema de ítems de policlase

**Versión:** `policlase.item/v1` · **Estado:** borrador para revisión
**Locale de referencia:** es-EC · America/Guayaquil · escala 0–100, separador `.`

Referencia normativa del formato de autoría de preguntas: la fuente YAML, el contrato del
generador sembrado y las reglas de calificación que la plataforma aplica sobre ellos.

---

## Índice

1. [Modelo de tres capas](#1-modelo-de-tres-capas)
2. [Archivos y repositorios](#2-archivos-y-repositorios)
3. [Reglas de YAML](#3-reglas-de-yaml)
4. [Nivel raíz](#4-nivel-raíz)
5. [El objeto `item`](#5-el-objeto-item)
6. [Lenguaje de plantillas](#6-lenguaje-de-plantillas)
7. [Contrato del generador](#7-contrato-del-generador)
8. [Tipos de pregunta](#8-tipos-de-pregunta)
9. [Clases en vivo: presentaciones](#9-clases-en-vivo-presentaciones)
10. [Composición en actividades](#10-composición-en-actividades)
11. [Catálogo de validación](#11-catálogo-de-validación)
12. [Versionado](#12-versionado)
13. [Decisiones pendientes](#13-decisiones-pendientes)

---

## 1. Modelo de tres capas

Todo el diseño descansa en una separación que conviene entender antes que cualquier campo
individual. Un ítem existe en tres formas distintas, cada una en un lugar distinto y con reglas
de mutabilidad distintas.

| Capa | Qué es | Dónde vive | Mutabilidad |
|---|---|---|---|
| **1 · Fuente** | El archivo YAML y su generador de Python | git, tu PC | editable, revisable en un PR |
| **2 · Variantes** | El resultado de correr el generador sobre cada semilla | base de datos | **inmutable** tras publicar |
| **3 · Respuestas** | Una fila estructurada por respuesta, no solo una nota | base de datos | append-only |

La consecuencia práctica: **editar la fuente nunca altera una variante ya publicada.** Si corriges
un generador en octubre, los exámenes de septiembre siguen mostrando exactamente lo que mostraron.
Un ítem corregido genera una `item_version` nueva; las variantes viejas conservan la suya. Sin esta
regla, cualquier reclamo de un estudiante es indefendible.

**Dónde corre cada cosa.** La capa 1 → 2 corre *en tu computador*, mediante `policlase build`. El
servidor nunca ejecuta código Python de autoría. La capa 3 corre en el servidor, con un evaluador de
expresiones propio y auditado que no es código de autoría. Esta división elimina el problema de
sandboxing por completo.

---

## 2. Archivos y repositorios

El contenido vive en tres repositorios. La separación no es burocrática: hace que el servidor y la
CLI importen *la misma* implementación del esquema, de modo que no puedan discrepar sobre qué es
válido.

| Repositorio | Visibilidad | Licencia | Contenido |
|---|---|---|---|
| `policlase-gen` | pública | MIT | Esquema, validador, contrato del generador, CLI y renderizadores. Sin autenticación ni base de datos. |
| `policlase` | pública | MIT | La plataforma. Depende de `policlase-gen`. |
| `mis-cursos` | **privada** | — | Tus ítems y generadores. |

> **`mis-cursos` nunca se publica.** Los archivos de ítems contienen las respuestas correctas en
> texto plano. Es el único de los tres que debe permanecer privado, y conviene que su `.gitignore`
> y sus permisos lo reflejen.

Dentro del repositorio de contenido:

```
mis-cursos/
├── metodos-numericos/
│   ├── unidad-01/
│   │   ├── biseccion.yaml          # uno o varios ítems
│   │   └── newton.yaml
│   └── generators/
│       ├── biseccion.py
│       └── newton.py
└── policlase.toml                  # curso, locale, zona horaria
```

Un archivo YAML puede contener varios ítems. El `id` de cada ítem es global dentro del curso y es la
clave de la analítica a lo largo de semestres, así que no se renombra: si el contenido cambia tanto
que la comparación histórica deja de tener sentido, se crea un `id` nuevo.

---

## 3. Reglas de YAML

El archivo se carga con `ruamel.yaml` en modo **YAML 1.2**, con el cargador seguro. Las dos
restricciones no son estilísticas.

> **Nunca uses el cargador completo.** El *loader* por defecto de PyYAML construye objetos Python
> arbitrarios a partir de etiquetas del documento. Como los ítems llegan desde un repositorio, eso
> sería una vía de ejecución de código en el mismo formato de archivo que aceptas. Solo carga segura.

Y YAML 1.2, no 1.1, porque el resolvedor de 1.1 convierte silenciosamente valores que este esquema
usa de verdad:

| Escrito | YAML 1.1 (PyYAML) | YAML 1.2 (ruamel) |
|---|---|---|
| `1e-9` | `'1e-9'` — cadena | `1e-09` — flotante |
| `no` | `False` | `'no'` — cadena |
| `12:30` | `750` — sexagesimal | `'12:30'` — cadena |
| `NaN` | `'NaN'` | `'NaN'` |

Una tolerancia `1e-9` convertida en cadena no falla: compara mal, en silencio, y solo lo notas
cuando un estudiante reclama. Todo texto con matemáticas usa escalares de bloque (`|`) para que
LaTeX se escriba literal, sin escapar barras invertidas.

---

### LaTeX y comillas

En YAML, la barra invertida es un escape **dentro de comillas dobles**: `"$\tilde{x}$"` se lee
como un tabulador seguido de `ilde{x}`, y `"$\sqrt{x}$"` ni siquiera carga (`\s` no es un escape
válido). Escriba el texto con LaTeX entre **comillas simples** (`'$\tilde{x}$'`) o en un bloque
`|`. Si de todos modos un comando quedó tragado dentro de matemáticas (`\t`ilde, `\f`rac,
`\b`eta, `\n`abla, `\v`ec, `\r`ho…), el cargador lo restituye y avisa con `W061`.

## 4. Nivel raíz

| Campo | Tipo | | Descripción |
|---|---|---|---|
| `schema` | string | **requerido** | Identificador de versión, p. ej. `policlase.item/v1`. El validador rechaza versiones desconocidas en vez de adivinar. |
| `meta` | object | opcional | Valores por defecto para todos los ítems del archivo; cualquier ítem puede sobrescribirlos. |
| `meta.locale` | string | `es-EC` | Afecta el formato de números al *renderizar* y los mensajes de error mostrados al estudiante. |
| `meta.decimal_input` | `both` \| `point` \| `comma` | `both` | Cómo se *interpreta* lo que el estudiante escribe. |
| `items` | array\<item\> | **requerido** | La lista de ítems; puede tener un solo elemento. |

`decimal_input` es independiente de la escala de salida, que siempre usa punto. El valor `both`
acepta `4.23` y `4,23`, y solo es seguro porque las listas numéricas usan una casilla por celda: en
un campo de texto libre separado por comas, `1,234` sería ambiguo.

---

## 5. El objeto `item`

Un ítem es la unidad de autoría, de versionado y de analítica: un enunciado compartido y las
preguntas que cuelgan de él.

| Campo | Tipo | | Descripción |
|---|---|---|---|
| `id` | string | **requerido** | Único en el curso. Solo `[a-zA-Z0-9._-]`. Clave de la analítica histórica; se trata como permanente. |
| `title` | string | opcional | Para tus listados y el panel de analítica. Nunca se muestra al estudiante durante una evaluación. |
| `tags` | array\<string\> | opcional | Temas. Habilitan el reporte de dominio por tema y la reutilización entre semestres. |
| `difficulty` | integer 1–5 | opcional | Tu estimación al escribirlo. La dificultad observada se calcula aparte; la diferencia es informativa. |
| `points` | number | suma de las preguntas | Puntos del ítem completo. Si se declara, debe igualar la suma de sus preguntas (`E050`). |
| `generator` | object | opcional | Se omite en ítems sin aleatorización. Ver [sección 7](#7-contrato-del-generador). |
| `variables` | object | condicional | Requerido cuando hay `generator`. Dos listas: `public` y `private`. |
| `stem` | string (markdown) | opcional | Enunciado común mostrado encima de todas las preguntas. Admite marcadores. |
| `questions` | array\<question\> | **requerido** | Al menos una; cada una con `id` único dentro del ítem. |

Vale la pena poblar `tags` desde el primer día: la analítica sin etiquetas solo te dice *qué* falló,
no *de qué*.

Sobre `variables`: **la separación entre `public` y `private` es estructural, no un filtro.** Las
variables privadas viven en un subárbol que el serializador del estudiante no puede alcanzar, de modo
que filtrar una respuesta no es algo que se pueda olvidar en un *endpoint* nuevo.

---

## 6. Lenguaje de plantillas

Los marcadores usan `{{ nombre }}`. El formato original usaba `<nombre>`, que choca con las
desigualdades (`$x < 3$`) y con HTML; las llaves dobles no aparecen junto a un identificador en
LaTeX real.

Los valores llegan estructurados desde el generador y se les da formato con filtros. Un generador
nunca debe devolver una cadena ya formateada como `"[-5, 4]"`: eso impide que el calificador reutilice
el valor.

| Filtro | Entrada | Salida |
|---|---|---|
| `{{ r \| interval }}` | `[-5, 4]` | `[-5,\,4]` |
| `{{ x \| num(2) }}` | `4.23456` | `4.23` |
| `{{ v \| latex }}` | cualquier escalar | forma LaTeX segura |
| `{{ n \| sci(3) }}` | `0.000123` | `1.23 \times 10^{-4}` |

### Markdown y matemáticas

El texto es CommonMark con tablas de GFM. Las matemáticas usan `$…$` en línea y `$$…$$` en bloque,
renderizadas con KaTeX **en el servidor**. Renderizar en el servidor no es un detalle de rendimiento:
garantiza que la vista previa, la página del estudiante y el PDF impreso produzcan exactamente la
misma salida, y evita que HTML no saneado llegue al navegador.

El HTML crudo en el markdown se descarta, no se escapa. Un error de sintaxis de KaTeX es un error de
validación (`E060`), no un cuadro rojo en la pantalla del estudiante.

---

## 7. Contrato del generador

Un generador es una función de Python que convierte una semilla en una variante. Corre en tu
computador durante `policlase build`; el resultado se sube ya materializado.

```yaml
generator:
  file: generators/biseccion.py   # relativo a la raíz del curso
  entry: generate                 # por defecto: generate
  seeds: 1..200                   # cuántas variantes materializar
```

```python
import random

def generate(seed: int) -> dict:
    rng = random.Random(seed)          # única fuente de aleatoriedad permitida
    r1, r2 = sorted(rng.sample([-4, -3, -2, -1, 1, 2, 3, 4], 2))
    return {
        "public":  {"fcn": "x^{2}+x-2", "range_1": [r1 - 1, r1 + 1]},
        "private": {"root_1": float(r1), "root_2": float(r2),
                    "root_3": None,     # None se renderiza como NaN
                    "range_1_count": 1},
    }
```

### Reglas obligatorias

- **Determinismo.** La misma semilla produce siempre la misma variante. Sin `random` global, sin
  reloj, sin red, sin lectura de archivos. El validador corre cada semilla dos veces y compara.
- **Claves exactas.** Lo devuelto debe coincidir con `variables`, ni de más ni de menos. Sin esta
  verificación, un marcador mal escrito se renderiza literalmente como `{{ root_2 }}` en la pantalla
  de veinticinco estudiantes.
- **Tipos serializables.** Solo `int`, `float`, `str`, `bool`, `None`, listas y diccionarios de
  estos. `float('nan')` no es serializable en JSON: usa `None`.
- **Salida en LaTeX.** Las funciones se devuelven como `x^{2}+x-2`, no como texto plano ambiguo.

### Asignación de semillas

La plataforma deriva la semilla de cada estudiante de forma estable y no adivinable:

```
seed = H(course_secret, item_id, student_id, student_name) mod |seeds|
```

El `course_secret` importa: sin él, cualquiera que conozca la derivación y la cédula de un compañero
puede calcular su variante. Es una cadena aleatoria por curso, guardada fuera del repositorio.

### Entropía de variantes

`policlase build` reporta cuántas variantes distintas produjo el generador y cuántas colisiones cabe
esperar para la matrícula real del curso. El generador de ejemplo elegía dos raíces de ocho
candidatas: **28 funciones distintas en 200 semillas**, de modo que con 25 estudiantes varios reciben
ítems idénticos.

Es un reporte informativo (`I030`), no un error: con semillas derivadas de la identidad del
estudiante, una colisión solo importa si esos dos estudiantes concretos se comunican sobre ese ítem
concreto. Aun así conviene leer la cifra al escribir un ítem nuevo, porque una entropía de 3 o 4
suele indicar un generador más pobre de lo que se pretendía.

---

## 8. Tipos de pregunta

Toda pregunta tiene `id`, `type`, `prompt`, `points` (1 si se omite) y, salvo `open`, una `solution`. El bloque
`grading` cambia según el tipo.

### `numeric`

Un solo valor numérico.

```yaml
- id: q2
  type: numeric
  points: 1
  prompt: "¿Cuántas raíces existen en el rango ${{ range_1 | interval }}$?"
  solution: "{{ range_1_count }}"
  grading:
    integer: true          # rechaza 2.0001 en una pregunta de conteo
    rtol: 0.01             # tolerancia relativa
    atol: 1.0e-9           # absoluta; domina cerca de cero
    units: "m/s"           # opcional; si está, la unidad es obligatoria
```

Con ambas tolerancias se acepta si `|a-b| ≤ atol + rtol·|b|`. Declarar solo `rtol` hace que toda
respuesta cercana a cero falle, que es el error más común al escribir tolerancias.

### `numeric_list`

Varios valores en una rejilla. Sustituye al tipo `Matrix` original.

```yaml
- id: q1
  type: numeric_list
  points: 4
  shape: [1, 3]
  solution: ["{{ root_1 }}", "{{ root_2 }}", "{{ root_3 }}"]
  grading:
    rtol: 0.01
    order: ascending       # sorted | ascending | descending | exact | any
    partial: per_cell      # per_cell | all_or_nothing
    nan_aliases: ["NaN", "nan", "no existe", "-"]
```

`order` resuelve algo que en el formato original solo existía en la prosa del enunciado: el texto
pedía orden ascendente y el calificador no tenía forma de saberlo. Con `any` se comparan como
conjuntos.

### `expression`

El estudiante escribe una expresión algebraica. Es el único tipo que necesita evaluación en el
servidor al momento de calificar.

```yaml
- id: q1
  type: expression
  points: 3
  prompt: "Sea $f(x) = {{ f_latex }}$. Escriba $f'(x)$."
  solution: "{{ df_expr }}"     # infija plana, NO LaTeX
  grading:
    vars: [x]
    domain: { x: [-3, 3] }
    sample_points: 20
    rtol: 1.0e-6
    allow: [sin, cos, tan, exp, ln, log, sqrt, abs, pi, e]
```

**La solución es una expresión infija plana, no LaTeX.** El enunciado se muestra en LaTeX
(`f_latex`), pero lo que el calificador compara se escribe en el mismo lenguaje que teclea el
estudiante (`df_expr`): `3*2*x**1*sin(x) + 3*x**2*cos(x)`. Un generador que necesite ambas formas
declara ambas variables. Comparar LaTeX con lo que teclea un estudiante exigiría un analizador de
LaTeX, que es un problema mayor que el que resuelve.

Sintaxis admitida: números, los símbolos de `vars`, `pi` y `e`, las funciones de `allow`,
`+ - * / % ** ^` y paréntesis. **La multiplicación debe ser explícita** (`2*x`, no `2x`); escribir
`2x` produce un mensaje que lo dice. Todo lo demás —atributos, índices, listas, comparaciones— se
rechaza en el AST antes de evaluar nada.

La comparación es por **muestreo numérico**: ambas expresiones se evalúan en veinte puntos aleatorios
del dominio. Esto reconoce `(x-1)(x+1)` y `x^2-1` como equivalentes sin simplificación simbólica
completa, y no puede colgarse. La simplificación simbólica queda como verificación secundaria con
temporizador.

> **Sobre evaluar entradas del estudiante.** La entrada se tokeniza, se convierte en AST y se valida
> contra `allow` *antes* de evaluar nada. Nunca `eval()`, y nunca `sympy.sympify()` sobre una cadena
> cruda: internamente evalúa Python.

### `choice`

Una sola opción correcta.

```yaml
- id: q4
  type: choice
  points: 2
  options:
    - { text: "Rango con signos iguales, no hay solución.", correct: true }
    - { text: "Solución única." }
    - { text: "Infinitas soluciones, función periódica." }
    - { text: "Error de convergencia, máximas iteraciones alcanzadas." }
  none_of_the_above: true
  sample: { distractors: 3, shuffle: seeded }
```

Se declaran todos los distractores y `sample.distractors` elige cuántos mostrar, de forma
determinista según la semilla. `none_of_the_above` es un caso especial: la plataforma añade la opción
y la ancla siempre al final.

Una advertencia (`W070`) se dispara si esa opción nunca es correcta en ninguna variante del ítem,
porque los estudiantes aprenden a descartarla y deja de ser un distractor.

### `multi_choice`

Varias opciones correctas; el estudiante marca todas las que apliquen.

```yaml
- id: q1
  type: multi_choice
  points: 3
  prompt: "¿Cuáles condiciones se requieren para aplicar bisección?"
  options:
    - { text: "$f$ continua en $[a,b]$.", correct: true }
    - { text: "$f(a)$ y $f(b)$ con signos opuestos.", correct: true }
    - { text: "$f$ derivable en $[a,b]$." }
    - { text: "Conocer $f'(x)$ analíticamente." }
  grading:
    partial: per_option    # per_option | all_or_nothing
    penalty: 1.0           # cada marca incorrecta anula un acierto
    floor: 0               # la pregunta nunca aporta negativo
  sample: { shuffle: seeded }
```

Con `partial: per_option` la nota es:

```
score = max(floor, (aciertos − penalty × errores) / total_correctas) × points
```

**`penalty` por debajo de 1.0 premia marcar todo.** Con `penalty: 0`, seleccionar las cuatro opciones
da nota completa sin saber nada, y el validador lo advierte (`W071`).

### `true_false`

Un bloque de afirmaciones, cada una marcada verdadera o falsa.

```yaml
- id: q2
  type: true_false
  points: 4
  prompt: "Marque cada afirmación como verdadera o falsa."
  statements:
    - { text: "La bisección converge siempre que haya cambio de signo.", answer: true }
    - { text: "Newton-Raphson garantiza convergencia global.", answer: false }
    - { text: "La bisección tiene convergencia lineal.", answer: true }
    - { text: "El método de la secante requiere evaluar $f'(x)$.", answer: false }
  grading:
    partial: per_statement  # per_statement | all_or_nothing
    penalty: 1.0            # contra el 50% que da el azar
    floor: 0
  sample: { shuffle: seeded }
```

Los puntos se reparten por igual entre las afirmaciones salvo que cada una declare los suyos. Las
afirmaciones admiten marcadores de plantilla, así que un generador puede variar los valores dentro de
cada una.

El azar da 50 % en este tipo, cosa que no ocurre en `choice`. Con `penalty: 1.0` una respuesta al azar
tiende a cero, que es el comportamiento deseable; para evaluaciones de alto impacto,
`all_or_nothing` es más severo aún.

### `text`

Respuesta corta comparada literalmente. Para términos, nombres de métodos y unidades.

```yaml
grading:
  accept: ["bisección", "biseccion", "método de bisección"]
  normalize: [lowercase, strip_accents, collapse_spaces]
```

### `open`

Respuesta escrita, calificada con rúbrica. Con `mode: ai`, un modelo propone una puntuación por
criterio; con `mode: manual`, la ingresas tú.

```yaml
- id: q4a
  type: open
  points: 2
  prompt: "¿Qué método es más adecuado para este rango y por qué?"
  grading:
    mode: ai                    # ai | manual
    review: required            # nunca se publica sin tu aprobación
    reference: |
      Se espera que note que $f(a)$ y $f(b)$ tienen el mismo signo...
    rubric:
      - { criterion: "Identifica que no hay cambio de signo", points: 1 }
      - { criterion: "Propone un método alternativo y lo justifica", points: 1 }
```

**Reglas de la calificación asistida.** Los `points` de la rúbrica deben sumar los de la pregunta
(`E046`). El modelo recibe *la variante del estudiante*, con sus valores, no la plantilla. Se guardan
el modelo, la versión del *prompt* y la salida cruda, porque una recalificación sin ese registro no
se puede defender. `review: required` es el valor por defecto y no se puede desactivar globalmente.

**Panel de calificación manual.** Las preguntas `open` —tanto `manual` como las propuestas por IA
pendientes de revisión— se califican en una vista dedicada que agrupa **por pregunta, no por
estudiante**: todas las respuestas a `q4a` juntas, con la rúbrica y la referencia fijas al costado.
Calificar veinticinco respuestas a la misma pregunta seguidas es mucho más consistente que recorrer
veinticinco exámenes completos, y permite ajustar el criterio a mitad de camino y volver atrás.

### `follow_ups`

Preguntas anidadas que se muestran después de responder la de arriba. Sus `points` son propios y
suman al total del ítem. Anidamiento máximo: un nivel.

### El registro de solución

`build` separa cada variante en dos subárboles. El estudiante recibe `public`; el calificador
recibe `solutions`:

```json
{
  "seed": 3,
  "fingerprint": "a1b2c3d4e5f60718",
  "public":  { "stem": "...", "questions": [ { "id": "q4", "options": [ {"key": "o0_4c9c5ff6", "text": "..."} ] } ] },
  "solutions": { "q1": { "solution": [-1.0, 1.0, null] },
                 "q4": { "correct": ["o3_cbc5ab1d"] } }
}
```

Dos propiedades que conviene no perder de vista:

* **La solución conserva su tipo, no su texto.** `"{{ root_3 }}"` se resuelve al valor `null`, no a
  la cadena `\mathrm{NaN}`: las soluciones se comparan, no se muestran, y una solución renderizada
  como LaTeX no la puede reanalizar ni su propio calificador.
* **La mezcla de opciones se materializa al construir.** Las opciones guardadas, con su `key`
  estable, son literalmente las que vio el estudiante. El calificador usa ese registro y nunca
  recalcula la presentación desde el ítem fuente; si lo hiciera, reordenar las opciones en octubre
  cambiaría cuál era la correcta en un examen de septiembre.

---

## 9. Clases en vivo: presentaciones

Una clase en vivo es una **presentación**: una secuencia de diapositivas que el docente avanza desde
el proyector, algunas de contenido y otras con una pregunta que los estudiantes responden desde su
teléfono. Es un documento aparte, con su propio identificador de esquema:

```yaml
schema: policlase.deck/v1
title: "Bisección — clase 1"
defaults: { time_limit_s: 30 }

slides:
  - markdown: |
      # El teorema de Bolzano
      Si $f$ es continua en $[a,b]$ y $f(a)\,f(b) < 0$, existe $c$ con $f(c) = 0$.
    notes: "Solo las ve el docente en el proyector."

  - item:
      id: L01-bolzano
      tags: [unidad-01, biseccion]
      points: 1
      lecture: { time_limit_s: 20 }
      questions:
        - id: q1
          type: choice
          points: 1
          prompt: "¿Qué garantiza el teorema de Bolzano?"
          options:
            - { text: "Existe al menos una raíz en el intervalo.", correct: true }
            - { text: "La raíz es única." }
```

| Campo | Tipo | | Descripción |
|---|---|---|---|
| `schema` | string | **requerido** | `policlase.deck/v1`. |
| `title` | string | **requerido** | Título que ven docente y estudiantes. |
| `defaults.time_limit_s` | integer 5–600 | `30` | Tiempo por pregunta si el ítem no declara otro. |
| `slides` | array | **requerido** | Cada diapositiva tiene **exactamente una** de `markdown` o `item` (`E080`). |
| `slides[].markdown` | string | — | Contenido: markdown con matemáticas. |
| `slides[].item` | item | — | Un ítem ordinario del esquema v1, con las restricciones de abajo. |
| `slides[].notes` | string | opcional | Notas para el docente. |
| `slides[].hidden` | boolean | `false` | La diapositiva queda en el archivo pero no se presenta (`E085` si no es booleano). |
| `speed_bonus` | boolean | `true` | Bono por rapidez en el **marcador** de la clase: una respuesta correcta vale entre el 50 % (al final del tiempo) y el 100 % (al instante) de sus puntos de juego. La **nota** de participación no cambia: cuenta solo si se acertó. |
| `feedback` | boolean | `true` | Al final de cada clase se agrega una pregunta de retroalimentación **anónima** (valoración de 1 a 5 y comentario opcional). `false` la desactiva. |
| `item.lecture.time_limit_s` | integer 5–600 | opcional | Tiempo de esa pregunta (`E084` fuera de rango). |

Restricciones de un ítem en vivo, porque en clase todos ven lo mismo al mismo tiempo:

- **Una sola pregunta, sin `follow_ups`** (`E081`): cada diapositiva es un momento de la clase.
- **Sin aleatorización** (`E083`): ni `generator`, ni `variables`, ni marcadores `{{ }}`.
- **Tipos respondibles con un toque o un número** (`E082`): `choice`, `multi_choice`,
  `true_false`, `numeric` y `text`. `open` y `expression` exigen escribir con calma, que no es lo que
  pide una pregunta cronometrada.

La retroalimentación no es un ítem: no da puntos ni entra en el marcador, y la plataforma la guarda
sin vínculo con el estudiante. El docente ve el resumen solo cuando hay al menos tres respuestas,
para que en un grupo pequeño nadie pueda deducir quién escribió qué.

El orden de las diapositivas y `hidden` se pueden cambiar desde el panel lateral del editor web,
que edita solo las líneas afectadas (`policlase_gen.deck_text`): el diff en git queda igual que si
se hubiera hecho a mano.

Todos los demás errores del ítem —`E043`, `E050`, etc.— se siguen reportando igual. Y reutilizar el
esquema tiene una consecuencia que vale más que el ahorro de código: los sondeos de clase entran en
la analítica de ítems junto con todo lo demás, con las mismas etiquetas. Sus notas alimentan la
categoría de participación.

**Al iniciar una clase, la plataforma copia la presentación compilada.** Editarla después no altera
lo que se vio ni cómo se calificó una clase ya dictada — la misma inmutabilidad de la capa 2.

`policlase validate` reconoce las presentaciones por su campo `schema` y las valida igual que los
ítems.

---

## 10. Composición en actividades

Los ítems no se califican solos: se agrupan en actividades, y la actividad es lo que aparece en el
libro de calificaciones. Esta sección fija solo la parte que toca al esquema de ítems; el esquema
completo de actividades y políticas va con el plan.

| Campo | Tipo | | Descripción |
|---|---|---|---|
| `grading_granularity` | `whole` \| `items` | `whole` | `whole`: ingresas una sola nota de 0 a 100 para la actividad. `items`: la nota se acumula desde los `points` de cada pregunta. |
| `category` | string | — | `quiz`, `assignment`, `project`, `exam`, `participation`. |
| `weight` | number | `1` | Peso relativo dentro de su categoría. Los pesos *entre* categorías se ajustan en el panel de calificaciones, no en el YAML. |
| `extra_credit` | boolean | `false` | Suma puntos al numerador sin añadir nada al denominador. |

Empezar en `whole` y profundizar solo donde hace falta evita tener que descomponer en subítems una
actividad que no lo necesita.

Las reglas de agregación acordadas, para que queden asentadas: una actividad sin calificar cuenta
como **cero**; el crédito extra suma sin ampliar el denominador; un estudiante exonerado recibe una
nota compensatoria manual; y una categoría vacía se queda en cero, con su peso ajustado a cero al
cierre del curso.

**Dos vistas, una sola política.** Como lo no calificado cuenta cero, el libro de calificaciones
ofrece una vista *parcial* (solo lo ya calificado) junto a la vista *final*. Son los mismos datos
presentados de dos formas; la política oficial no cambia. Evita el pánico de la semana tres sin ceder
nada.

**Exportación a Moodle.** Solo de salida, nunca de entrada. El CSV empareja por **correo
electrónico** por defecto, con el número de identificación como alternativa configurable.

---

## 11. Catálogo de validación

`policlase validate` corre idéntico en tu editor, en el *hook* de pre-*commit* y en CI. Un error
bloquea la publicación; una advertencia bloquea solo en CI, donde el umbral es más estricto que en tu
iteración local. Los códigos `I` son informativos y nunca bloquean.

| Código | Severidad | Condición |
|---|---|---|
| `E002` | error | Versión de `schema` desconocida. |
| `E010` | error | `id` de ítem duplicado dentro del curso. |
| `E020` | error | Un marcador `{{ x }}` no aparece en `variables`. |
| `E021` | aviso | Una variable declarada no se usa en ninguna plantilla. |
| `E022` | error | El generador devolvió una clave no declarada. |
| `E023` | error | El generador omitió una clave declarada. |
| `E024` | error | Valor no serializable (típicamente `float('nan')`). |
| `E025` | error | No determinista: dos corridas de la misma semilla difieren. |
| `E026` | error | El generador lanzó excepción o excedió el tiempo límite. |
| `I030` | info | Reporte de entropía: variantes distintas y colisiones esperadas. |
| `E041` | error | `shape` no concuerda con la longitud de `solution`. |
| `E042` | error | Tipo numérico sin `rtol` ni `atol`. |
| `E043` | error | `choice` sin opción correcta, o con más de una. |
| `E044` | error | `expression` usa un símbolo ausente de `vars`. |
| `E045` | error | `mode: ai` sin `rubric`. |
| `E046` | error | Los puntos de la rúbrica no suman los de la pregunta. |
| `E047` | error | `true_false` con una afirmación sin `answer`. |
| `E048` | error | `multi_choice` sin ninguna opción correcta. |
| `E050` | error | Los puntos de las preguntas no suman los del ítem. |
| `E060` | error | KaTeX no pudo analizar una expresión, o hay `$` sin cerrar. |
| `W061` | aviso | LaTeX entre comillas dobles: un escape de YAML se tragó un comando; se corrigió. |
| `W070` | aviso | `none_of_the_above` nunca es correcta en ninguna variante. |
| `W071` | aviso | `multi_choice` con `partial: per_option` y `penalty` &lt; 1.0. |
| `E080` | error | Diapositiva sin `markdown` ni `item`, o con ambos. |
| `E081` | error | Ítem en vivo con más de una pregunta o con `follow_ups`. |
| `E082` | error | Tipo de pregunta no respondible en vivo. |
| `E083` | error | Aleatorización en una presentación (generador, variables o marcadores). |
| `E084` | error | `time_limit_s` fuera de 5–600 segundos. |
| `E085` | error | `hidden` o `feedback` no son booleanos. |

Cada mensaje cita archivo, línea, `id` del ítem y, cuando aplica, la semilla que reprodujo el fallo
—de modo que `policlase build --seed 47` lo reproduce de inmediato.

---

## 12. Versionado

El campo `schema` usa `nombre/vN`. Dentro de una versión mayor solo se agregan campos opcionales;
renombrar o eliminar un campo, o cambiar el significado de uno existente, exige `v2` y un migrador
incluido en el paquete público.

Aparte, cada ítem lleva una `item_version` interna que la plataforma incrementa cuando cambia su
contenido. Las variantes publicadas conservan la versión con la que se generaron: es lo que permite
comparar el rendimiento de un ítem entre semestres sabiendo si lo que se compara es realmente lo
mismo.

---

## 13. Decisiones pendientes

- **Adjuntos en la respuesta.** Falta un tipo `file` para entregas con código o escaneos. Depende de
  las cuotas de subida, que van con el plan.
- **Calificación asistida por IA.** Pendiente de la revisión de la política de privacidad de la
  universidad. El esquema ya la contempla; nada se activa hasta esa decisión.

---

*Borrador para revisión · el esquema se congela como v1 tras el primer semestre en uso.*
