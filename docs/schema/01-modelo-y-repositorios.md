# 1. Modelo y repositorios

[← Índice](../schema.md)

## Modelo de tres capas

Un ítem existe en tres formas distintas, cada una en un lugar distinto y con reglas de mutabilidad
distintas.

| Capa | Qué es | Dónde vive | Mutabilidad |
|---|---|---|---|
| **1 · Fuente** | El archivo YAML y su generador de Python | git, el computador del docente | editable, revisable en un PR |
| **2 · Variantes** | Lo que ve cada estudiante: el contenido compilado (y, con generador, la variante de su semilla) | base de datos | **inmutable** tras publicar |
| **3 · Respuestas** | Una fila estructurada por respuesta, no solo una nota | base de datos | solo se agrega |

**Editar la fuente nunca altera lo que un estudiante ya vio.** Al iniciar una clase, la plataforma
copia la presentación compilada; al empezar un intento, copia la actividad compilada. Corregir el
archivo después no cambia lo que se vio ni cómo se calificó. Un ítem corregido genera una
`item_version` nueva; las variantes viejas conservan la suya. Sin esta regla, cualquier reclamo de
un estudiante es indefendible. (La excepción deliberada: las diapositivas de solución se muestran en
su versión vigente; ver [parte 6](06-reglas-de-la-plataforma.md#explicaciones).)

**Dónde corre cada cosa.** La capa 1 → 2 con generador corre *en el computador del docente*, con
`policlase build`: el servidor nunca ejecuta código Python de autoría. La capa 3 corre en el
servidor, con calificadores propios (un evaluador de expresiones auditado, no código de autoría).
Así no hay nada que aislar en el servidor.

## Repositorios

| Repositorio | Visibilidad | Licencia | Contenido |
|---|---|---|---|
| `policlase-gen` | pública | MIT | Este formato: validador, compilador, calificadores, contrato del generador y CLI. Sin autenticación ni base de datos. |
| `policlase` | pública | MIT | La plataforma. Importa `policlase-gen`, así que el servidor y la CLI no pueden discrepar sobre qué es válido. |
| `mis-cursos` | **privada** | — | Los ítems, las clases y las actividades del docente, con sus generadores. |

> **`mis-cursos` nunca se publica.** Los archivos contienen las respuestas correctas en texto plano.

## Carpetas

```
mis-cursos/
└── metodos-numericos/                       ← la carpeta que se vincula al curso en policlase
    ├── Unidad 01 - Preliminares/            ← una sección: «Unidad 01 - Preliminares»
    │   ├── 01-clase-errores.yaml            ← use: class
    │   ├── deber-errores.yaml               ← use: activity
    │   └── img/tabla.png                    ← imágenes que citan los archivos de la carpeta
    ├── prueba-1.yaml                        ← use: evaluation (sin sección)
    └── generators/biseccion.py
```

Una carpeta es una **sección** (unidad) si contiene al menos un documento de contenido (una clase,
una actividad, una evaluación o un repaso) o el marcador vacío `.policlase-seccion`. El orden es el
de los nombres, así que conviene usar prefijos numéricos. Cómo se sincroniza la plataforma con el
repositorio —cuándo lee, qué commits hace, cómo resuelve conflictos— no es parte del formato: está
en [`policlase/docs/github.md`](../../../policlase/docs/github.md).

El `id` de cada ítem es global dentro del curso y es la clave de la analítica a lo largo de
semestres: no se renombra. Si el contenido cambia tanto que la comparación histórica deja de tener
sentido, se crea un `id` nuevo.
