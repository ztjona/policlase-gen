# 6. Reglas de la plataforma

[← Índice](../schema.md)

Cómo trata la plataforma lo escrito en el formato, para que quede asentado en un solo lugar.
Implementación: `policlase/apps/activities/engine.py` (intentos), `debate.py` (debate),
`apps/live/engine.py` (clases en vivo) y `apps/grades/gradebook.py` (notas).

## Intentos y fechas

- **Cuenta el último intento enviado.** Entre intentos el estudiante ve su puntaje; la corrección
  detallada, en la revisión (o cuando se le acaban los intentos).
- **Vencimiento**: fijo, relativo a una fecha clave («3 días antes de la prueba») o relativo a la
  apertura («7 días después del taller»). Si la fecha de referencia cambia, el vencimiento la sigue.
- **Envío automático** (por omisión): al vencer la fecha, el borrador empezado a tiempo se envía con
  lo que tenga, como entrega a tiempo; una respuesta ilegible vale cero, como una en blanco. Si el
  docente mueve la fecha hacia adelante, vuelve a ser borrador (salvo que ya lo haya calificado).
- **Entregas atrasadas**: bloqueadas, o aceptadas con la penalización de la actividad (30 % por
  omisión) hasta el cierre del parcial, solo de quien no entregó a tiempo.
- **Prórrogas**: el docente da a un estudiante su propia fecha de entrega en una actividad (si su
  intento se había enviado solo, vuelve a quedar abierto) o, en una evaluación, su propio horario y,
  si hace falta, su propia duración (una adecuación).
- Una pregunta en blanco vale cero; una respuesta ilegible («uno coma cuatro» en una numérica) se
  devuelve para corregirla antes de enviar.
- **Secciones deshabilitadas**: el docente puede deshabilitar ítems o secciones enteras (la parte de
  un taller a la que no se llegó). El estudiante no las ve, no suman ni cuentan en el máximo, en
  todos los intentos, también los ya enviados; ninguna respuesta se borra.

## Revisión

Desde que vence la fecha hasta su cierre, que decide el docente (sin límite, hasta una fecha
relativa a una fecha clave —por ejemplo, el día de la prueba—, hasta una fecha fija, en una
evaluación hasta unos días después de publicar las notas, o sin revisión). Durante ella el estudiante ve su corrección detallada y las explicaciones; después, solo
su puntaje. Quien no entregó las ve únicamente cuando ya no puede entregar: verlas antes sería
responder con las soluciones a la vista.

## Explicaciones

Cada diapositiva `solution` explica el ítem que la precede. En la revisión aparece junto a ese
ítem, detrás de «Ver la explicación»: el estudiante ve primero su corrección. Se muestra la versión
vigente de la explicación, también a quien empezó antes de que se escribiera. Las de un ítem con una
pregunta de debate esperan al cierre del debate; en un repaso, se abren al comprobar el ítem entero.

## Preguntas con tiempo

`time_limit_s` en un segmento de una actividad o evaluación: la pregunta no se ve hasta que el
estudiante la abre; desde ahí corre el reloj del servidor (cerrar la página no da más tiempo). **No
hay cuenta regresiva a la vista**: el límite se dice antes de abrirla y, 10 s antes del final, el
marco cambia. Al acabarse no se avisa nada; la pregunta sigue abierta, y lo que se responda después
(pasada una gracia de unos segundos por la conexión) vale con la penalización por atraso de la
actividad. Se cierra con «Responder» (si está en blanco, se pide confirmación) o al enviar el
intento, y se responde una sola vez; una que no se abrió vale cero.

## Clases en vivo

Ni el proyector ni los teléfonos muestran la cuenta regresiva (el docente ve el tiempo pequeño en
sus controles); 10 s antes, el teléfono cambia el marco. Al acabarse, la pregunta sigue abierta
hasta que el docente la cierra o responden todos, y lo que llega después vale un 30 % menos. Con
bono por rapidez, una mención en la sala de espera invita a responder pronto. La primera respuesta
es la que cuenta. Cada clase terminada cuenta para la participación de todos los inscritos: faltar
vale cero.

## Debate

Para las preguntas con `debate: true` ([parte 3](03-items-y-preguntas.md#preguntas-de-debate-debate)):

- Se responden con una **justificación** (markdown y LaTeX, sin enlaces ni imágenes).
- **Desde la fecha de entrega hasta el cierre del debate** —por omisión, el cierre de la revisión; o
  una fecha fija; o cuando el docente lo cierre—, cada una tiene su foro: la respuesta y la
  justificación de cada estudiante con su nombre corto (el preferido, o el primer nombre, y el
  primer apellido), comentarios de un nivel y «me gusta» públicos.
- **Primero se publica, después se lee**: ve el foro de una pregunta quien tiene su respuesta en
  ella, y solo si ya no puede entregar con nota. Quien no entregó, y ya no puede, se suma publicando
  la suya.
- Durante el debate, cada estudiante puede actualizar su respuesta; la actualización no cambia la
  nota, que es la del intento enviado.
- Mientras dure, no se muestran la corrección de la pregunta ni la explicación de su ítem: aparecen
  al cerrarse, durante la revisión. (Si el debate se cierra cuando termina la revisión, ya no se
  verán: conviene cerrarlo antes, después de discutirlo en clase.)
- El docente lee todo, comenta y oculta lo que no corresponda; lo oculto lo sigue viendo su autor,
  con el aviso.

## Evaluaciones (`use: evaluation`)

Un intento, sin entregas atrasadas, dentro de su horario y con el código que el docente proyecta en
el aula (con un límite de intentos fallidos). Si hay duración, cada estudiante la tiene desde que
empieza, sin pasar del cierre; al acabarse, se envía con lo guardado. El reloj está oculto: se
consulta con «Ver tiempo restante» y avisa a los 10 y a los 2 minutos del final. El estudiante no
ve su puntaje ni su corrección hasta que el docente publica las notas; la revisión empieza entonces.

**Orden de las partes.** Si el docente lo activa, cada estudiante recibe las partes (lo que va de un
segmento al siguiente) en su propio orden, fijo desde que empieza. Se mezclan partes enteras, nunca
preguntas sueltas: el contenido y los ítems de una parte conservan su orden y su contexto. Por eso
conviene no referirse a otra parte por su posición («la parte anterior»).

**Corrección.** Si el docente la permite, al publicar las notas cada estudiante que rindió la
evaluación puede volver a resolverla completa, a su ritmo y en un solo intento, hasta el cierre de
la revisión. Es una actividad aparte, con el mismo contenido y el mismo orden de partes, que cuenta
en la fila de la ponderación que el docente elija (por lo general, una opcional). La revisión de la
evaluación se le muestra al enviar la corrección. Quien no quiere hacerla (por ejemplo, porque su
nota ya es la que esperaba) puede omitirla, antes de empezarla, y ver la revisión de inmediato; la
decisión no se deshace. Quien no la envía ni la omite no ve la revisión.

## Repasos (`use: practice`)

Para preparar una prueba: sin nota (no entran en ninguna fila de la ponderación), sin tiempo y con
intentos ilimitados. Cada pregunta se comprueba al momento con «Comprobar»: queda con su corrección
en ese intento y, cuando se comprobaron todas las de un ítem, se abre su explicación. Al terminar,
lo que no se comprobó también se corrige. Abren unos días antes de una fecha clave (y se mueven con
ella) o desde una fecha fija; pueden tener una fecha de cierre.

## Encuestas

Se registran y no cuentan para la nota; nunca se muestran como correctas o incorrectas.

## Calificación asistida por IA

Para las respuestas `open` (las imágenes no: el modelo solo lee texto), si el docente configuró su
clave de DeepSeek y habilitó la integración:

- **La IA solo propone.** La propuesta (puntos por criterio, total y una retroalimentación formal
  para el estudiante) llena el formulario de nota de la respuesta; el docente la revisa, la corrige
  si hace falta y la guarda. Hasta entonces el estudiante no ve nada, y la nota es siempre la del
  docente.
- **Una consulta por respuesta**, con un comienzo común a todas las de la pregunta (reglas, materia,
  unidad, actividad, enunciado, rúbrica y referencia) y la respuesta al final, entre delimitadores
  que el modelo trata solo como respuesta, nunca como instrucciones. Así el modelo no compara a los
  estudiantes entre sí y DeepSeek cobra a una fracción el comienzo repetido.
- **No sale del servidor nada que identifique al estudiante**: ni nombre, ni cédula, ni correo.
- Los puntos de cada criterio se limitan a su máximo, en múltiplos de 0,25, y el total, a los de la
  pregunta. Sin rúbrica, la pregunta es un solo criterio.
- Se guarda, para poder defender una calificación, el modelo, la versión del prompt, la salida cruda
  y los tokens usados.
- `grading.mode: ai` solo indica la intención en el archivo: la IA puede proponer en cualquier
  pregunta `open`, y en ninguna decide.

## Ponderación y aprobación

- Cada parcial tiene filas obligatorias que suman 100 % y opcionales que suman encima. La nota del
  parcial se topa en su máximo (20 por omisión): los extras compensan, no desbordan.
- Una actividad cuenta desde que vence; vencida y sin entregar, vale cero.
- **Aprobación** (por omisión): con la suma de parciales por debajo de 18 se pierde; desde 28 se
  aprueba; en medio, supletorio sobre 40, aprobado si parciales + supletorio ≥ 48 y supletorio ≥ 24.
- **Exportación a Moodle**: solo de salida. El CSV empareja por correo electrónico por omisión, con
  el número de identificación como alternativa.
