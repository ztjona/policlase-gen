# 4. Contrato del generador

[← Índice](../schema.md)

Un generador es una función de Python que convierte una semilla en una variante. Corre en el
computador del docente con `policlase build`; el resultado se sube ya materializado. El servidor
nunca lo ejecuta ([parte 1](01-modelo-y-repositorios.md)). Por ahora la plataforma no recibe
variantes: un ítem aleatorizado en un documento de contenido es un error (`E083` en una clase,
`E092` en los demás; ver [parte 8](08-versionado-y-pendientes.md)).

```yaml
generator:
  file: generators/biseccion.py   # relativo a la raíz del curso
  entry: generate                 # por omisión, generate
  seeds: 1..200                   # cuántas variantes materializar
variables:
  public: [fcn, range_1]
  private: [root_1, root_2, root_3, range_1_count]
```

```python
import random

def generate(seed: int) -> dict:
    rng = random.Random(seed)          # única fuente de aleatoriedad permitida
    r1, r2 = sorted(rng.sample([-4, -3, -2, -1, 1, 2, 3, 4], 2))
    return {
        "public":  {"fcn": "x^{2}+x-2", "range_1": [r1 - 1, r1 + 1]},
        "private": {"root_1": float(r1), "root_2": float(r2), "root_3": None, "range_1_count": 1},
    }
```

## Reglas obligatorias

- **Forma.** Devuelve un dict con `public` y `private` (`E027`).
- **Determinismo.** La misma semilla produce siempre la misma variante: sin `random` global, sin
  reloj, sin red, sin leer archivos. El validador corre cada semilla dos veces y compara (`E025`).
- **Claves exactas.** Lo devuelto coincide con `variables`, ni de más (`E022`) ni de menos
  (`E023`). Sin esta verificación, un marcador mal escrito se vería literal en la pantalla.
- **Tipos serializables.** Solo `int`, `float`, `str`, `bool`, `None`, listas y diccionarios de
  estos (`E024`). `float('nan')` no se serializa: se usa `None`.
- **Sin excepciones ni demoras** (`E026`).
- **Funciones en LaTeX**: `x^{2}+x-2`, no texto plano ambiguo; lo que compare `expression`, en su
  forma plana, en otra variable.

## Asignación de semillas

La plataforma deriva la semilla de cada estudiante de forma estable y no adivinable:

```
seed = H(course_secret, item_id, student_id, student_name) mod |seeds|
```

Sin el `course_secret` (una cadena aleatoria por curso, fuera del repositorio), cualquiera que
conozca la derivación y la cédula de un compañero podría calcular su variante.

## Entropía de variantes

`policlase build` informa cuántas variantes distintas produjo el generador y cuántas colisiones cabe
esperar para la matrícula del curso (`I030`, informativo). El ejemplo elige dos raíces de ocho
candidatas: 28 funciones distintas en 200 semillas, así que con 25 estudiantes varios reciben la
misma. Una colisión solo importa si esos dos estudiantes se comunican sobre ese ítem, pero una
entropía muy baja suele indicar un generador más pobre de lo que se pretendía.
