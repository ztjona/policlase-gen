# 2. YAML, plantillas y markdown

[← Índice](../schema.md)

## Cómo se carga el YAML

El archivo se carga con `ruamel.yaml` en modo **YAML 1.2**, con el cargador seguro. Ninguna de las
dos restricciones es estilística.

> **Nunca el cargador completo.** El cargador por defecto de PyYAML construye objetos Python
> arbitrarios a partir de etiquetas del documento. Como los archivos llegan desde un repositorio,
> eso sería una vía de ejecución de código. Solo carga segura.

Y YAML 1.2, no 1.1, porque el resolvedor de 1.1 convierte en silencio valores que este formato usa:

| Escrito | YAML 1.1 (PyYAML) | YAML 1.2 (ruamel) |
|---|---|---|
| `1e-9` | `'1e-9'` — cadena | `1e-09` — flotante |
| `no` | `False` | `'no'` — cadena |
| `12:30` | `750` — sexagesimal | `'12:30'` — cadena |

Una tolerancia `1e-9` convertida en cadena no falla: compara mal, en silencio.

## LaTeX y comillas

En YAML, la barra invertida es un escape **dentro de comillas dobles**: `"$\tilde{x}$"` se lee como
un tabulador seguido de `ilde{x}`, y `"$\sqrt{x}$"` ni siquiera carga (`\s` no es un escape
válido). El texto con LaTeX va entre **comillas simples** (`'$\tilde{x}$'`) o en un bloque `|`. Si
de todos modos un comando quedó tragado dentro de las matemáticas (`\t`ilde, `\f`rac, `\b`eta,
`\n`abla, `\v`ec, `\r`ho…), el cargador lo restituye y avisa (`W061`).

## Marcadores de plantilla

Los marcadores usan `{{ nombre }}` (el formato original usaba `<nombre>`, que choca con las
desigualdades y con HTML). Solo existen en ítems con generador ([parte 4](04-generador.md)). Los
valores llegan estructurados desde el generador y se formatean con filtros; un generador nunca
devuelve una cadena ya formateada como `"[-5, 4]"`, porque el calificador necesita el valor.

| Filtro | Entrada | Salida |
|---|---|---|
| `{{ r \| interval }}` | `[-5, 4]` | `[-5,\,4]` |
| `{{ x \| num(2) }}` | `4.23456` | `4.23` |
| `{{ v \| latex }}` | cualquier escalar | forma LaTeX segura |
| `{{ n \| sci(3) }}` | `0.000123` | `1.23 \times 10^{-4}` |

Un marcador sin declarar es un error (`E020`); una variable declarada que no se usa, un aviso
(`W021`).

## Markdown y matemáticas

El texto del docente (enunciados, contenido, soluciones, indicaciones) es CommonMark con tablas y
tachado de GFM. Las matemáticas van entre `$…$` (en línea) y `$$…$$` (en bloque): se separan
*antes* de que markdown interprete `_` o `*`, y las dibuja KaTeX en el navegador. El validador las
analiza con KaTeX al validar, así que una fórmula rota es un error (`E060`), no un cuadro rojo en
la pantalla del estudiante.

El HTML escrito en el markdown se descarta, y todo lo que sale del markdown pasa por un saneador:
un enunciado con HTML arbitrario llegaría a los teléfonos de todo el curso.

**Imágenes:** `![descripción](ruta)`. Una dirección `https://…` se muestra tal cual. Una ruta
relativa (`img/error.png`, o `/comun/logo.png` desde la carpeta del curso) la resuelve la
plataforma cuando el curso está vinculado a un repositorio: relativa al archivo que la cita, como
en GitHub. El validador no comprueba que la imagen exista; la plataforma lo avisa al sincronizar.

**Lo que escribe un estudiante** no es parte del formato, pero sigue la misma idea: una
justificación o un comentario del debate admite markdown y LaTeX, sin enlaces ni imágenes; una
respuesta abierta solo marca las fórmulas y respeta los saltos de línea, porque suele llevar código
pegado y markdown lo estropearía.
