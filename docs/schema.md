# El formato de policlase

**Versión:** `policlase/v1` (contenido) y `policlase.item/v1` (bancos de ítems) · **Estado:** en uso,
se congela tras el primer semestre.

Referencia normativa: cómo se escriben los ítems, las clases, las actividades, las evaluaciones y los
repasos; el contrato del generador; las reglas con las que la plataforma los califica y el catálogo
de diagnósticos del validador. Lo que no está aquí (sincronización con GitHub, despliegue, guía
visual) está en la documentación de la plataforma.

Cada parte trata un tema y nada más, para que una regla se escriba una sola vez. Cuando una parte
necesita algo de otra, la enlaza en vez de repetirla.

| Parte | Trata de |
|---|---|
| [1. Modelo y repositorios](schema/01-modelo-y-repositorios.md) | Las tres capas (fuente, variantes, respuestas), dónde corre cada cosa y cómo se organizan los repositorios y sus carpetas. |
| [2. YAML, plantillas y markdown](schema/02-yaml-plantillas-markdown.md) | Cómo se carga el YAML, LaTeX y comillas, marcadores `{{ }}`, markdown con matemáticas e imágenes. |
| [3. Ítems y preguntas](schema/03-items-y-preguntas.md) | El objeto `item`, cada tipo de pregunta, encuestas, `follow_ups`, preguntas de debate y el registro de solución. |
| [4. Contrato del generador](schema/04-generador.md) | Variantes por estudiante: el generador sembrado, sus reglas y la asignación de semillas. |
| [5. Documentos de contenido](schema/05-documentos.md) | El formato único `policlase/v1`: `use` (clase, actividad, evaluación, repaso), diapositivas, segmentos, soluciones y la forma compilada. Los formatos anteriores. |
| [6. Reglas de la plataforma](schema/06-reglas-de-la-plataforma.md) | Intentos, fechas, revisión, explicaciones, tiempo, atrasos, prórrogas, debate, evaluaciones, repasos, calificación con IA y ponderación. |
| [7. Catálogo de validación](schema/07-validacion.md) | Todos los códigos `E`, `W` e `I`. |
| [8. Versionado y pendientes](schema/08-versionado-y-pendientes.md) | Cómo evoluciona el formato y qué falta decidir. |

**Convenciones.** «Debe» es obligatorio y lo comprueba el validador (con el código entre
paréntesis); «conviene» es una recomendación. Los ejemplos usan comillas simples para el texto con
LaTeX ([parte 2](schema/02-yaml-plantillas-markdown.md#latex-y-comillas)).
