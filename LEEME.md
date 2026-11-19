# Marexada Celeste · Instagram automático · v71

Diseños de partido + lector de la web del club (rccelta.es).
Todavía NO descubre noticias nuevas solo ni publica en Instagram: eso es lo siguiente.

## Novedades v71 (Tesouros Celestes, con las fotos de la peña de fondo)
- La sección de los miércoles se llama ahora **TESOUROS CELESTES** (cabecera, pie de Telegram y avisos). Se ha quitado el número de edición.
- **Fotos de fondo de la peña** (carpeta `assets/fondos_tesouros/`): el recorte de periódico «El Celta, un grande en Europa» sale en las 35 efemérides europeas (las de la categoría Europa / Gran noite europea y las que hablan de Champions, UEFA, Recopa, EuroCelta…), y la foto histórica de la bandera en todas las demás. Si dejas más fotos en esa carpeta, el programa las va rotando: las que empiezan por `europa_` son para las noites europeas y las demás para el resto. La foto apaisada se usa a todo el ancho y nítida (es pequeña, 640×360) sobre una versión desenfocada de sí misma; la vertical ocupa toda la historia.
- **«HAI 27 ANOS»**: ya no es un recuadro; ahora es un sello tipográfico con el número enorme entre «HAI» y «ANOS» y filetes con rombos a los lados.
- **Invitación a deslizar**: pastilla oscura con el texto en blanco y más grande, y tres flechas que se van apagando.
- El fondo se oscurece por zonas: la foto se ve en el centro y queda oscura donde hay texto, para que siempre se lea.

## Novedades v70 (imagen de las efemérides más seria y editorial)
- Nuevo diseño del Almanaque, pensado como publicación de referencia y no como cartel: cabecera «ALMANAQUE CELESTE · Nº 001» (el número es el de la edición: del 1 al 209), marco fino con esquinas, fondo de foto antigua más oscuro y sobrio, y luz suave tras el protagonista.
- **Portada:** placa de fecha (día enorme | mes y año), los dos escudos con doble aro y el nombre de cada club, placa «HAI 20 ANOS» y titular en serif. Si el partido no tiene rival claro (fundación, ascenso…), sale el escudo del Celta solo.
- **Historia 2:** marcador gigante con los escudos, los datos en un panel con rótulo «A HISTORIA EN DATOS» y los protagonistas en cursiva.
- **Historia 3:** «E TI?», el peche en cursiva, la pregunta en una placa y «CÓNTANOLO POR MENSAXE». Barras de avance 1-2-3 en las historias 2 y 3.
- Nuevas tipografías libres incluidas en `assets/fuentes`: Big Shoulders (números y rótulos, estilo marcador de estadio) y Lora (textos, serif editorial), además de Poppins.
- Corregido el resplandor tras los escudos, que dejaba cortes rectos.

## Novedades v69 (el horario de GitHub deja de coincidir con cron-job)
- cron-job.org lanza el modo rápido cada 5 minutos (:00, :05, :10…). El horario propio de `diario.yml` pasa a **cada 10 minutos en los minutos :02, :12, :22…** de 15:00 a 00:52 (invierno), como copia de seguridad: nunca coincide con cron-job. Si una ejecución de cron-job falla, la de GitHub lo recoge en pocos minutos.
- Las ejecuciones se hacen de una en una (`concurrency`), y las webs delicadas siguen con su freno (rccelta.es 1 vez por hora; besoccer y futbolme cada 10 min).

## Novedades v68 (Almanaque en gallego, imagen nueva y modo rápido cada 5 minutos)
- **Textos en gallego.** `assets/almanaque.json` sale ahora del Excel «Almanaque_Celta_48_meses_GL.xlsx» (209 miércoles, del 18/11/2026 al 13/11/2030). `convertir_almanaque.py` entiende el Excel en español y en gallego.
- **Imagen nueva de las 3 historias del miércoles.** Portada: el año enorme de fondo, rayos de luz celestes, escudos con brillo, cinta inclinada «HAI 20 ANOS», fecha completa en gallego y titular en mayúsculas con «DESLIZA PARA VER A HISTORIA». Historia 2: marcador gigante con escudos y los datos en tarjeta, con los protagonistas. Historia 3: «E TI?», el cierre y la pregunta en un recuadro grande con «CÓNTANOLO POR MENSAXE». Si el titular empezaba por «Hai 13 anos: …» se quita ese comienzo en la portada (ya lo dice la cinta).
- **Modo rápido cada 5 minutos** (lo lanza cron-job.org cada 5 minutos; ver v69 para el horario de GitHub). Para no parecer un robot hay un **freno por web** en el modo rápido: rccelta.es como mucho **1 vez por hora**; besoccer.com y futbolme.com cada 10 minutos. Los goles, el inicio y el descanso salen de ESPN/TheSportsDB (datos abiertos) y se miran cada 5 minutos. Las 3 ejecuciones completas del día consultan siempre. Se puede cambiar con las variables `MIN_RCCELTA`, `MIN_BESOCCER` y `MIN_FUTBOLME` (minutos). La hora de la última consulta se guarda en `estado/consultas_web.json`.
- Si usas cron-job.org para lanzar el flujo, no hace falta duplicar: o el horario de `diario.yml` o cron-job, pero no los dos a la vez.
- Ojo con los minutos de GitHub Actions: cada 5 minutos son unas 120 ejecuciones al día. En un repositorio público no hay límite; en uno privado la cuota gratuita (2000 min/mes) se gasta en pocos días.

## Novedades v67 (Almanaque Celta + escudos de Europa)
- **Miércoles = Almanaque Celta.** Cada miércoles (a partir de las 19:00) salen **3 historias** con los textos del Excel «Almanaque Celta 48 meses»: 1) gancho, 2) datos (con marcador y escudos si es un partido) y 3) cierre con la pregunta para la afición. Cubre del 18/11/2026 al 13/11/2030 (209 miércoles). Hoy, 18/11/2026: «20 años de una victoria celeste en Riazor» (Deportivo 0-1 Celta).
- El programa NO lee el Excel: lee `assets/almanaque.json` (228 KB). Si cambias textos en el Excel: `pip install openpyxl` y luego `python convertir_almanaque.py TuExcel.xlsx` (regenera el json) y sube el json.
- Los textos salen tal cual están en el Excel (se quitan solo los emojis, que la tipografía no puede dibujar, y la pregunta final si ya está repetida en el recuadro).
- Nuevo diseño `almanaque` en `generar_historia.py` (mismo fondo de «foto antigua» y marco que la portada de la historia celeste). Escudos de los dos equipos cuando el dato trae marcador o rival y el club tiene escudo; si no, solo el del Celta.
- El buscador automático de partidos históricos en ESPN (v63) queda de reserva: solo se usa si un miércoles no está en el Excel. Mientras haya Excel ya no calienta su caché de lunes a martes.
- **20 escudos nuevos** de equipos europeos (Arsenal, Aston Villa, Borussia Dortmund, Club Brugge, Fenerbahçe, Feyenoord, Galatasaray, Liverpool, Lille, Manchester United, PSV, Lens, Roma, Shakhtar, Slovan Bratislava, Slavia Praha, Sporting CP, VfB Stuttgart, AEK Atenas y Oporto), reducidos a 360 px y 128 colores como los que ya había: 244 KB en total (12 KB cada uno, en vez de 2,7 MB originales). Los otros 20 del paquete ya estaban y se han dejado como estaban.
- No incluye la v66 (la de espaciar las consultas a rccelta.es): esta versión está hecha sobre la v65.

## Novedades v65 (rccelta.es da «403 Forbidden»)
- Síntoma: noticias, parte médico y entradas fallaban a la vez con `HTTP Error 403: Forbidden`. A diferencia del 502, un 403 no es una caída: la web rechaza la petición.
- `red.py` ahora identifica todas las descargas como un navegador Chrome normal (cabeceras completas) en lugar de «compatible; MarexadaCeleste/1.0». Es lo primero que suelen filtrar las webs.
- Si rccelta.es sigue respondiendo 403, el programa deja de insistir al segundo intento (no se martillea una web que nos bloquea) y avisa: «rccelta.es bloquea las peticiones (HTTP 403 Forbidden); no es un fallo pasajero».
- Si tras esto sigue el 403, lo más probable es que bloqueen las IP de GitHub Actions y no el nombre del programa; en ese caso hay que cambiar desde dónde se descarga, no el código.

## Novedades v64 (fondos propios)
- Tres fotos nuevas en `assets/fondos/`: `fondo_victoria.jpg` (resultado con victoria del Celta, primer equipo), `fondo_inicio.jpg` (inicio de partido del Celta, primer equipo) y `fondo_europa.jpg` (todos los partidos de Europa League: previa, próximo partido, convocatoria, alineación, inicio, descanso y resultado).
- Las fotos se colocan sin deformar (nítidas arriba, fundiéndose con el color de la competición hacia abajo). El resto de historias no cambia. Si en Europa League gana el Celta, manda la foto de Europa.
- Para cambiar una foto, basta con sustituir el archivo por otro con el mismo nombre.

## Novedades v63
- **«ESTA SEMANA NA HISTORIA CELESTE»**, todo automático. Cada miércoles (a partir de las 19:00) sale una **portada** y después **una historia por partido** (hasta 3). El programa busca solo en ESPN los partidos del Celta de temporadas pasadas que cumplen años esa semana (±3 días), de **Copa del Rey, Europa (Europa League/Champions) y LaLiga**, y elige los más interesantes: solo victorias del Celta; puntúan más Europa y Copa, las goleadas y los rivales grandes.
- Las de `efemerides.json` marcadas `"revisada": true` entran siempre y primero (son las comprobadas a mano).
- **Foto de la portada**: se usa `assets/fondos/historia.jpg` (si no existe, una provisional).
- Seguridad: los goleadores solo salen si cuadran con el marcador y no hay goles en propia puerta. Si ESPN no responde, no se inventa nada.
- Nuevo `historia.py` y `fixtures/espn_historia_EJEMPLO.json` (para probar sin internet). La caché se guarda en `estado/historia_cache.json`: la primera vez se descargan las temporadas poco a poco (máx. 2 min por ejecución) y el miércoles solo publica cuando el histórico está completo.

## Novedades v62 (rccelta.es caída: 502 / tiempo agotado)
- Nuevo `red.py`: las descargas de rccelta.es (parte médico, entradas, noticias) reintentan 3 veces (pausas de 3 y 8 s) si la web devuelve 502/503/504 o no contesta.
- Si sigue caída, se marca como «caída» y el resto de peticiones fallan al instante: antes `entradas.py` probaba decenas de direcciones y se cortaba a los 4 minutos («tardó demasiado»); ahora termina en ~11 s.
- Los fallos pasajeros de la web ya no salen como «ERROR»: van en un apartado aparte («Fallos pasajeros de la web (no hay que hacer nada)») y no disparan por sí solos un mensaje de Telegram. Se reintentan solos en la siguiente ejecución.
- Los errores definitivos (404, cambio de formato de la web…) se siguen avisando como antes.

## Novedades v61
- Menos brillo alrededor de los escudos (próximo partido, resultado y gol).
- Cada equipo con su color también en el parte médico (Celta Fortuna = turquesa, aunque no lleve logo de competición) y en las clasificaciones: la fila destacada usa el color de la competición.
- En los equipos/competiciones con color propio la foto de fondo se desatura un poco, así el turquesa, el lila, el rojo y el naranja se notan de verdad.
- Bordes de las tarjetas (fecha, goleadores) en el color de la competición y viñeteado más suave para que el blanco de los títulos no se apague.

## Novedades v60 (diseño de las historias)
- **Color por competición**: LaLiga = celeste, Copa del Rey = rojo, Europa League = naranja, LaLiga Hypermotion (Celta Fortuna) = turquesa, AS Celtas femenino = lila. Cambia el fondo, los rótulos, las píldoras y el halo.
- **Próximo partido**: cuenta atrás en píldora («FALTAN 3 DÍAS», «MAÑÁ», «HOXE», hasta 14 días antes), resplandor tras los escudos y «VS» más grande.
- **Resultado**: marcador más grande con borde y resplandor, el que gana en el color de la competición y su escudo resaltado.
- **Acabado en todas las historias**: sombra suave en los textos, halo de color arriba, viñeteado en los bordes y grano muy fino.
- Para probar la cuenta atrás con otra fecha: `MAREXADA_HOY=2026-11-20 python generar.py datos_ejemplo/proximo_celta_EJEMPLO.json salida.jpg`.

## Novedades v59
- Arreglo en `instagram.py`: al crear por primera vez la rama «imagenes» daba el error `'default_branch'` (la prueba de v58 falló por eso; la publicación real habría fallado igual).
  Ahora la rama se crea a partir del commit que ejecuta el workflow.

## Novedades v58
- **Prueba de publicación real** sin activar el diario: nuevo workflow «Prueba de Instagram» (`.github/workflows/prueba-instagram.yml`) y `python instagram.py --prueba`.
  Publica UNA historia fija («PRUEBA DE PUBLICACIÓN») en la cuenta, aunque `IG_SIMULACRO=1`. Hay que escribir SI en la casilla de confirmación. No toca la cola ni el diario.

## Novedades v57
- **Publicación automática en Instagram** (historias): `instagram.py` + guía de montaje en `INSTAGRAM.md`. Las imágenes se alojan en la rama `imagenes` del repositorio (público),
  se apuntan en `estado/cola_instagram.json` y se publican con la API oficial. Avisos por Telegram (✅ publicada, ⏱️ caducada, ❌ error). Modo prueba `IG_SIMULACRO=1` y freno `IG_PAUSA=1`.

## Novedades v56
- Arreglo del directo (goles, inicio y descanso): la lista de partidos del equipo en ESPN (`/schedule`) solo trae los ya terminados, por eso un partido en juego no se veía
  (comprobado con el Albacete – Celta Fortuna del 16/11). Ahora `directo.py` mira además `/schedule?fixture=true` y el marcador de la liga (`/scoreboard`).
- Nuevo `directo_log.txt` dentro de `salida/AAAA-MM-DD/datos/` (artifact «historias»): dice qué ha visto ESPN en cada revisión (eventos y estados), para comprobar el directo.

## Novedades v55
- El «Hoxe xogamos!» del día del partido (Celta, Fortuna, AS Celtas Fem) ya es una publicación independiente del «Mañá xogamos!»: antes, si el de «Mañá» ya había salido,
  el del día del partido no salía. No sale si el partido ya ha empezado.

## Qué hay en el zip
- `generar.py`: lee un JSON y crea la imagen (1080x1350, vertical de Instagram).
- `rccelta.py`: lee el título y el texto de una noticia del club y la convierte en ese JSON.
  Entiende hoy, del primer equipo y del Celta Fortuna: convocatorias (con dorsales, bajas por lesión y
  por sanción) y crónicas (resultado, goleadores, jornada, competición). Reconoce el club rival y elige su escudo.
- `fixtures/`: noticias reales del club: primer equipo (Celta–Levante, convocatoria y crónica; Celta 1-2 Union Saint-Gilloise)
  y Celta Fortuna (convocatorias ante Córdoba, Burgos y Sporting; crónica del Celta Fortuna 2-2 Córdoba).
- `datos_reales/`: el JSON que sale de esas noticias.
- `datos_ejemplo/`: JSON de ejemplo (los dos resultados `EJEMPLO` son inventados).
- `ejemplos/`: imágenes generadas (`real_*` salen de las noticias reales del club).
- `assets/`: fondos, 74 escudos con `equipos.json`, tipografía Poppins.

## Cómo usarlo
1. `pip install pillow`
2. `python generar.py` (genera todos los ejemplos) o
   `python generar.py datos_ejemplo/convocatoria_celta_osasuna.json salida.png`

## Formato de los datos
Todos llevan: `tipo` (convocatoria, alineacion o resultado), `competicion` (liga o europa),
`local` y `visitante` (nombre del escudo, por ejemplo `celta-vigo`, `real-madrid`; la lista está en
`assets/equipos.json`), `jornada`, `lugar` y `fecha_hora`. Opcional: `tag` para cambiar la etiqueta de arriba.
- convocatoria: `convocados` = grupos (Porteiros, Defensas...) con la lista de jugadores.
- alineacion: `once`, `suplentes` y `entrenador` (opcional).
- resultado: `goles_local`, `goles_visitante`, `goleadores_local` y `goleadores_visitante`.
Cada jugador puede ser un texto ("Iago Aspas") o `{"dorsal": 10, "nombre": "Iago Aspas"}`.
El texto se ajusta solo si hay nombres largos o más jugadores de lo normal.

## Decisiones tomadas
- Contenido: convocatorias, alineaciones, resultados, lesiones (parte médico de la web del club)
  y fichajes (solo con anuncio oficial). Del Celta, Celta Fortuna y AS Celtas.
- Más contenido para llegar a dos publicaciones al día: cuenta atrás, clasificación, efemérides,
  Celta Fortuna / cantera, AS Celtas, cumpleaños, entradas, recuerdos de viajes (galería de la web),
  merchandising (web) y "hazte socio".
- Ventajas de socio para las publicaciones de captación: prioridad en entradas de visitante,
  gestión de entradas por la peña, descuentos en merchandising, sorteos, viajes organizados a dos
  partidos fuera, porra semanal con premio, liga propia en Biwenger y más sorpresas.
- Idioma: gallego, como la web.
- Alineación: se publica como lista (once inicial, suplentes y entrenador), como hace el club.
- Fondo azul con la foto de Balaídos para LaLiga y Copa; fondo negro y naranja con el trofeo
  para la Europa League.
- Fuente de datos: rccelta.es. Todo gratis (GitHub Actions + API oficial de Instagram,
  cuenta profesional).

## Novedades v53
- **Goles del Celta en directo («¡GOOOOOOL!»)**: vuelve la historia por gol (se quitó en v51), ahora con diseño propio: tu foto de la grada (`assets/fondos/fondo_gol.jpg`),
  «¡GOOOOOOL!», goleador, minuto (con «de penalti» o «en propia puerta» si toca), marcador en ese momento con los dos escudos (el del equipo que marca, resaltado), logo de la
  competición, «EN DIRECTO», logo de la peña y la web. Funciona en LaLiga, Copa del Rey (tono rojo) y Europa League (tono naranja). Solo salen los goles **del Celta**
  (primer equipo); los del rival no se publican. Si hay dos goles entre dos revisiones salen las dos imágenes, cada una con su marcador. Un gol de hace más de 30 min de juego
  no se saca (por si el programa estuvo parado). Un gol en propia puerta del rival cuenta como gol del Celta.
- **Celta Fortuna en directo**: «COMIENZA EL PARTIDO» y «DESCANSO» (con marcador y goleadores de la primera parte), igual que el primer equipo. El final ya salía por `resultados.py`.
  El Fortuna no lleva historia por gol.
- `directo.py` ahora vigila los dos equipos (ESPN: LaLiga, Europa League, Copa y Hypermotion). Prueba sin internet: `python directo.py --desde fixtures/espn_directo_EJEMPLO.json --salida /tmp/prueba`.
- Nuevo tipo de historia `gol` (`generar_historia.py`, función `gol`). Ejemplo: `datos_ejemplo/gol_celta_EJEMPLO.json` → `ejemplos/gol_celta_EJEMPLO.jpg`. Campos: `goleador`, `minuto`,
  `goles_local`, `goles_visitante`, `lado` (`local`/`visitante`: quién marca), `modo` (`""`, `penalti` o `propia`) y `titulo` (opcional, por defecto «¡GOOOOOOL!»).
- Arreglo: el Getafe (y otros clubes cuyo nombre en la base lleva «C.F») no salía con escudo cuando la fuente lo llamaba solo «Getafe».
- Ojo con el retraso: el programa mira cada 15 min (30 min por la mañana), así que el gol puede salir con unos minutos de retraso. Para acortarlo, cambiar el `cron` de
  `.github/workflows/diario.yml` a `*/5` (en un repositorio privado de GitHub gasta más minutos gratuitos al mes).

## Novedades v52
- Fondos distintos por tipo de historia (misma capa azul y mismo pie, solo cambia la foto): convocatoria y alineación → vestuario; parte médico → Ciudad Deportiva;
  clasificación → mural de Balaídos; el resto sigue con la grada. Se configura en `FONDO_POR_TIPO` (`generar_historia.py`); fotos en `assets/fondos/fondo_*.jpg`.

## Novedades v51
- Directo del Celta simplificado: ya no hay publicación por gol. Solo salen (los días de partido del Celta, primer equipo): inicio del partido, descanso
  (con marcador y goleadores de la primera parte; si se pasa el descanso entre revisiones se reconstruye con los goles ≤ 45') y el resultado final de siempre.

## Novedades v50
- Arreglo: el AS Celtas Fem ya no puede salir como «RESULTADO FINAL» al empezar el partido (marcador en directo 0-0). Se recuerda la hora de inicio
  (`estado/agenda.json`) y no se da por terminado hasta 115 min después; además `besoccer.py` exige «FIN» en la página.
- Nuevo `directo.py` (solo Celta, primer equipo): al empezar el partido saca «COMIENZA EL PARTIDO» y con cada gol «¡GOL!» con marcador y goleadores;
  después sigue saliendo el resultado final de siempre. Se vigila cada 15 min (workflow `diario.yml`), así que llegan con un retraso de unos minutos.

## Novedades v49
- El mensaje de Telegram ya no lleva el «Control de actualidad» (ocupaba mucho texto). Sigue apareciendo completo en `resumen.md` (artifact `historias`).
  Los avisos de error sí siguen llegando a Telegram.

## Novedades v48
- El pie alterna entre dos versiones, una por historia: escudo azul + letras, o letras + escudo rojo (nunca los dos a la vez). `LOGO_PIE` en
  `generar_historia.py`: `"alternar"` (por defecto), `"azul"`, `"rojo"` o `"ambos"`.

## Novedades v47
- Pie simplificado: se quita el escudo rojo (sobrecargaba). Queda el escudo azul + letras MAREXADA CELESTE + la web. Para volver a verlo: `LOGO_PIE = "ambos"`.

## Novedades v46
- Nuevo pie de todas las imágenes (`_pie_marca` en `generar_historia.py`): escudo azul de la peña + letras MAREXADA CELESTE (más pequeñas) + escudo rojo,
  los tres en la misma fila y con el escudo rojo centrado verticalmente con las letras. Logos más grandes.
- Calidad: el logo de texto se ha separado en `assets/marca/logo_marexada_letras.png` y `logo_marexada_rojo.png` (recortes de `logo_marexada_texto.png`
  sin reescalar) y cada logo se reduce una sola vez con LANCZOS desde su original grande.
- `LOGO_PIE = "ambos"` (por defecto) enseña los dos escudos; con `"alternar"` sale un día solo el azul y otro solo el rojo (nunca los dos).

## Novedades v28
- Se quita el `diario.yml` suelto de la carpeta principal del ZIP (era una copia vieja que confundía): el archivo que vale es SOLO `.github/workflows/diario.yml`.
  GitHub únicamente ejecuta los archivos de esa carpeta. Tiempo máximo de cada ejecución: 5 minutos.

## Novedades v27
- ARREGLO IMPORTANTE: el programa no leía la fecha de las noticias de rccelta.es (salía `_fecha: null`) y por eso las convocatorias y las crónicas
  NO llegaban a publicarse. Ahora `noticias.py` tolera «RC Celta 12-noviembre-2026» pegado o separado, prueba también los metadatos de la página
  y avisa en el resumen si una noticia no tiene fecha o no se puede interpretar. `CANDIDATA` ya no exige que la convocatoria empiece el título.
- `diario.py`: si una convocatoria no trae fecha de noticia, vale si el partido es hoy, mañana o pasado mañana (fecha del partido del propio texto).
- Ejecuciones rápidas más espaciadas: cada 30 minutos (10:05-14:35 y, de jueves a lunes, 15:05-23:35, horas de invierno). Consumo orientativo: unos 29 minutos
  de Actions al día (≈ 880 al mes de los 2.000 gratuitos).

## Novedades v26
- MODO RÁPIDO (`python diario.py --modo rapido`): solo convocatorias y resultados (fuentes: calendario, noticias de rccelta.es, resultados y AS Celtas).
  Se ejecuta cada 15 minutos de 10:00 a 14:45 (convocatorias) y cada 20 minutos de 15:00 a 23:40, de jueves a lunes (resultados), horas de invierno.
  Antes de gastar tiempo mira `estado/agenda.json`: si no hay partido de nadie entre ayer y dentro de 2 días, termina enseguida.
  En modo rápido Telegram manda SOLO la foto con su texto (con ⚡ delante), sin el resumen, y no avisa de errores (esos salen en las completas).
- Ejecuciones COMPLETAS (parte médico, entradas, cumpleaños, clasificaciones, resumen del día): 07:00, 17:30 y 23:30 (invierno) y al pulsar Run workflow.
- `estado/agenda.json`: fechas de los partidos cercanos; la crea la primera ejecución completa y la actualizan todas.
- `diario.yml`: una sola ejecución a la vez (concurrency), caché de pip y `estado/` completo en el commit.
- `plantillas/esta_semana_na_historia_celeste_EJEMPLO.json`: plantilla de la portada de la serie de los miércoles (solo cambian los datos cada semana).
- Consumo orientativo: unos 45 minutos de GitHub Actions al día (≈1.350 al mes; el plan gratuito de un repositorio privado trae 2.000).

## Novedades v25
- El pronóstico da peña tiene diseño PROPIO, verde, para distinguirlo del resto (fondo `assets/fondos/pronostico_verde.jpg` con el escudo «Sempre Celta · dende 1923»):
  título grande, escudos, píldora menta con día y hora, «Cal será o resultado?» y tres círculos 1 · X · 2 con el nombre de cada opción.
  La gente responde a la historia o comenta con 1, X o 2 (no depende de las pegatinas de Instagram). El texto sugerido lo dice así.

## Novedades v24
- Pronóstico da peña (`generar_historia.py` tipo `pronostico`, `diario.py`): los VIERNES, si el Celta juega de viernes a lunes, sale una historia con los dos
  escudos y «Cal será o resultado?». Se crea a partir del calendario oficial (`proximo_celta.json`). El texto sugerido trae las opciones de la enquisa:
  1 (local) · X (empate) · 2 (visitante). La pegatina de enquisa de Instagram la pone la persona al subir la historia (la imagen deja libre la zona de abajo).
- Nuevo tipo `efemeride` (partido histórico, serie «Tal semana coma esta»): SOLO para hacerlo a mano; no está en el programa diario.
- El pronóstico pasa por el control de actualidad (el partido no puede haberse jugado y el texto no usa «hoxe/mañá»).

## Novedades v23
- CONTROL DE ACTUALIDAD obligatorio antes de generar la imagen de entradas (`diario.py`, `entradas.py`):
  1. fecha de la noticia: se guarda cuándo se publicó; solo se avisa de noticias de los últimos 2 días;
  2. fecha del partido: si ya se jugó, se descarta; si la noticia no trae fecha se contrasta con el calendario (próximo partido); si no se puede confirmar, se descarta;
  3. estado actual: la noticia se vuelve a descargar de rccelta.es justo antes de generar la imagen (se guarda la hora de la comprobación);
  4. lenguaje temporal: «hoy», «desde hoy», «mañana», «últimas horas»... se convierten en la fecha real de la noticia o la frase no se usa.
  El resultado de cada comprobación sale en `resumen.md`, apartado «Control de actualidad» (OK o DESCARTADA con el motivo).
- Entradas con el diseño de la competición: logo y colores de Copa del Rey (rojo), Europa League (naranja), LaLiga e Hypermotion; escudo del Salamanca UDS.
- Parte médico rediseñado: escudo del Celta arriba, filete con cruz, barra de acento, días de baja, fecha de actualización en gallego y 6 jugadores por imagen.
- Cumpleaños: la fecha va escrita («19 de novembro»), sin «hoxe».

## Novedades v22
- `cumpleanos.py` + `cumpleanos.json`: historia «FELIZ ANIVERSARIO» el día que cumple años un jugador o miembro del cuerpo técnico del Celta o del
  Celta Fortuna (edad en un círculo grande, nombre y posición). Los datos están en `cumpleanos.json`; para añadir o corregir a alguien se edita
  ese archivo en GitHub. Las líneas con `"pendiente": true` no se usan (Hugo Burcio, hasta confirmar su fecha: 22/05/2006 o 31/10/2006).
- Entradas: ahora con los escudos de los dos equipos (como el resto de historias) y, si el Celta o el Fortuna juegan fuera, el título
  pasa a «ENTRADAS VISITANTES» (también si la noticia habla de visitantes o desplazamiento). Si un rival no tiene escudo en `assets/escudos`,
  sale con sus siglas.

## Novedades v21
- `entradas.py`: avisa de las noticias de ENTRADAS del Celta y del Celta Fortuna que publica el club en https://rccelta.es/club/actualidad/<noticia>/
  (ejemplo: `entradas-celta-fortuna-real-valladolid`). La lista de la página de actualidad se carga con JavaScript, así que busca las noticias
  por la API de WordPress (`/wp-json/wp/v2/search?search=entradas`), por el mapa del sitio (sitemap) y por los enlaces de la página y de
  «Noticias recomendadas». Solo noticias de los últimos 8 días, de partidos que aún no se han jugado, sin As Celtas ni femenino ni canteira.
  Lee el partido, la jornada, la fecha y hasta 3 puntos (venta general y precio, prioridad de carnés, canje) y escribe `entradas_<noticia>.json`.
- Nuevo tipo de historia `entradas` (`generar_historia.py`). Ejemplo: `ejemplos/ejemplo_entradas_fortuna_valladolid.jpg`.
- `diario.py`: una historia por cada noticia de entradas nueva (la clave es el nombre de la noticia), con el enlace en el texto sugerido.
- SIN PROBAR con internet real: de las tres formas de encontrar la lista, ninguna se ha podido comprobar desde aquí. Si fallan, sale un aviso
  «ERROR entradas» en `resumen.md` y se guarda `entradas_DEBUG.txt` en `datos/` con lo que probó cada una.

## Novedades v20
- `partemedico.py`: parte médico del Celta y del Celta Fortuna desde rccelta.es (`/equipos/primer-equipo/parte-medico/` y `/equipos/celta-fortuna/parte-medico/`).
  Lee cada lesionado (nombre, fecha de lesión, diagnóstico, observaciones) y escribe `partemedico_celta.json` y `partemedico_fortuna.json`
  (7 lesionados por imagen; si hay más, `_2`, `_3`...). Si el parte está vacío, sale una historia «Sen baixas por lesión».
- Nuevo tipo `partemedico` (diseño historia 1080x1920, `generar_historia.py`). Ejemplo: `ejemplos/real_partemedico_celta.jpg`
  (datos del parte del Celta del 07/11/2026; el del Fortuna de `fixtures/` es inventado).
- `diario.py`: la historia del parte médico sale solo cuando el parte cambia (entra o sale alguien o cambia un diagnóstico; la «firma» del JSON).
  La primera vez saldrá el parte actual del Celta y del Fortuna.
- `diario.py`: Telegram avisa cuando hay historias nuevas o algún aviso de error, y además manda el resumen del día (con el contenido propio que
  toca hoy: noticia del día, efeméride...) UNA vez, en la primera ejecución de la mañana (de 05:00 a 13:00 hora de Madrid), o siempre que lances el
  trabajo a mano con Run workflow. Si Telegram falla, no se anota nada como hecho y se reintenta en la siguiente ejecución.
- `diario.yml`: ahora corre 6 veces al día (07:00, 13:00, 18:30, 20:00, 22:00 y 23:30 hora de invierno, aprox.).
- Probado con copias REALES de las dos páginas del parte (`fixtures/partemedico_REAL/`, descargadas por GitHub el 11/11/2026): los datos vienen en el HTML,
  no hace falta JavaScript. Si la página en español no existe, el programa prueba la gallega y la inglesa (los diagnósticos saldrían en inglés).

## Novedades v13
- `noticias.py`: convocatorias y crónicas del Celta y del Celta Fortuna desde rccelta.es, sin ayuda manual. Las páginas de categoría de la web
  (https://rccelta.es/categorias-actualidad-equipo/primer-equipo/) traen la lista de noticias dentro del HTML (comprobado hoy desde aquí),
  así que no hace falta navegador. Toma las noticias candidatas (título «Convocatoria del Celta…» o con marcador), las descarga, las
  interpreta con `rccelta.py` y deja `convocatoria_<equipo>.json` y `cronica_<equipo>.json` (la más reciente de cada tipo).
  Fortuna: se usa https://rccelta.es/categorias-actualidad-fundacion/celta-fortuna/ y, si falla, https://rccelta.es/fundacion/actualidad/
  (SIN comprobar). Alineaciones: no se generan (decidido).
- `diario.py`: saca la convocatoria el día que se publica (o al siguiente) y la crónica con goleadores al acabar el partido. Si hay crónica,
  no saca el resultado por marcador (si ya subiste el del marcador, sustitúyelo: el resumen lo avisa).
- Copa del Rey: las historias de partidos de Copa usan tu imagen: el logo de la Copa (recorte cuadrado de tu imagen) en el hueco del logo
  de la competición y el fondo de Balaídos teñido de rojo con rótulos en rosa claro (`usar_tema` en `generar_historia.py`).
  Ejemplo: `ejemplos/proximo_copa_EJEMPLO.jpg`. Si prefieres el fondo rojo liso de tu imagen, se cambia en un minuto.
- Probado SOLO con copias HTML reconstruidas a mano (`fixtures/rccelta_web_RECONSTRUIDO/`) a partir de los textos de las noticias reales; no
  con la web en directo. Dudas abiertas: si rccelta.es deja descargar las páginas desde los servidores de GitHub, y la estructura exacta del HTML
  de las noticias (si cambia, saldrá un aviso en `resumen.md`).

## Novedades v12
- `resultados.py`: resultado final por marcador del Celta (LaLiga, Europa League, Copa del Rey) y del Celta Fortuna (Hypermotion), con
  las fuentes de tu web: ESPN (`teams/<id>/schedule`) y TheSportsDB de respaldo. Crea `resultado_celta.json` y `resultado_fortuna.json`
  sin goleadores (esos vendrán de la crónica de rccelta.es) y sin jornada. Probado solo con `fixtures/espn_resultados_EJEMPLO.json`,
  construido a mano con el formato de ESPN (no son datos en directo).
- `diario.py` genera el resultado del Celta, del Fortuna y de AS Celtas Fem el mismo día o al día siguiente del partido, y ejecuta a las
  06:00 UTC y a las 22:30 UTC (el resultado de la tarde-noche). Lo ya generado no se repite.
- El anuncio de partidos ya estaba desde v11: «próximo partido» el día antes y el mismo día (Celta, Fortuna y AS Celtas Fem).

## Novedades v11
- `diario.py`: programa diario en MODO REVISIÓN. Lee calendario (tu web), clasificaciones y besoccer, decide qué historias tocan
  hoy (previa de la Kiev en casa; próximo partido el día antes y el mismo día de Celta, Fortuna y AS Celtas Fem; resultado del AS Celtas
  Fem; clasificaciones: lunes LaLiga, martes Fortuna, jueves AS Celtas Fem) y deja en `salida/AAAA-MM-DD/` las imágenes y un
  `resumen.md` con hora y texto sugeridos (en gallego, editables) y los avisos. Anota lo generado en `estado/publicado.json`.
  No publica en Instagram. Opcional: envío a Telegram (variables TELEGRAM_TOKEN y TELEGRAM_CHAT_ID; sin probar).
- `.github/workflows/diario.yml` (copia en `diario.yml`): ejecución diaria a las 06:00 UTC y botón para lanzarlo a mano; guarda las
  historias como archivo descargable (14 días). Instalación paso a paso en `INSTALAR.md`.
- Probado SOLO sin internet (`python diario.py --offline --hoy 2026-11-08`, con 5 días distintos). La primera ejecución real puede
  necesitar ajustes en los lectores; los avisos salen en `resumen.md`.
- Lo que sigue sin automatizar: noticias y crónicas/convocatorias/alineaciones de rccelta.es, efemérides, cumpleaños y contenido de peña.

## Novedades v10
- TODO SE PUBLICA COMO HISTORIA (1080x1920): también la Europa League, que antes usaba un diseño cuadrado de publicación.
  Todos los tipos (resultado, próximo partido, convocatoria, alineación, clasificación y previa) salen con el mismo diseño historia.
- Imágenes y ZIP ligeros: las imágenes se guardan en JPEG (calidad 86, ~300 KB) en vez de PNG (~1,6 MB); `python generar.py datos.json`
  crea `ejemplos/datos.jpg` (si pones nombre de salida .png, sale PNG). Escudos y logos reducidos (de 10,9 MB a 1,3 MB) y ejemplos en JPEG de calidad 72 (4,6 MB). El ZIP completo pesa unos 7 MB.
- `clasificaciones.py`: clasificación de LaLiga (Celta), Europa League (fase liga) y LaLiga Hypermotion (Celta Fortuna), con las
  MISMAS fuentes y comprobaciones que tu web (js/clasificacion.js): ESPN primero y TheSportsDB (lookuptable) como respaldo.
  Escribe `datos_reales/clasificacion_celta_{laliga,europa,fortuna}.json`. Prueba sin internet con
  `python clasificaciones.py --desde fixtures/web_respaldo_jornada8_LL_EL_HM.json` (son los datos de respaldo de la web, jornada 8/9).
  Las tablas largas (Europa, 36 equipos) salen en una ventana de 18 equipos alrededor del Celta («postos 17-34 de 36»).
- `calendario.py`: lee https://marexadaceleste.com/api/partidos (tu función de Netlify, que junta ESPN y TheSportsDB) y crea
  `proximo_celta.json`, `proximo_fortuna.json` y, solo si hoy el Celta juega en casa y la hora está confirmada, `previa_hoy.json`
  (la previa de la Cafetería Kiev). Si hoy no hay previa borra `previa_hoy.json`. Con esto ya se puede enganchar la previa de
  cada mañana de partido a la ejecución automática.
- Probado SOLO sin internet: `fixtures/partidos_api_EJEMPLO.json` está construido a mano con el formato de la función
  (no son datos en directo) y las clasificaciones de prueba son los respaldos de la web. Primera ejecución real = posible ajuste.
- Si `/api/partidos` devuelve lista vacía o falla, `calendario.py` termina con un error claro (en tu captura se veían errores 403 y CORS
  de TheSportsDB: es la ruta de respaldo del navegador, que solo se usa cuando `/api/partidos` no da partidos de LaLiga y Europa).

## Novedades v9
- Previa: cervezas rehechas como dos jarras con asa (cristal grueso, cerveza ámbar, espuma abundante) brindando.
  Se quita la frase «dúas horas antes do partido»: la hora de la previa (hora del partido menos 2 h) se calcula sola.
- (Corregido en v10) Aquí había un aviso de tabla desactualizada: era el texto de relleno de la web antes de cargar los datos; la tabla en directo va al día.

## Novedades v8
- Nuevo tipo `previa` (diseño historia 1080x1920, mismo fondo): «PREVIA · NA NOSA SEDE · CAFETERÍA KIEV», con dos cervezas
  brindando, la hora de la previa en grande (hora del partido menos 2 horas), «dúas horas antes do partido» y el partido
  (escudos, hora, lugar y fecha). Ejemplo: `datos_reales/previa_celta_levante.json` -> `ejemplos/real_previa_celta_levante.png`.
  Datos: `local`, `visitante`, `lugar` y `fecha_hora` con hora («Dom 08/11 · 18:30»); si no hay hora da un error claro.
  Las horas de antelación se pueden cambiar con `horas_antes` (por defecto 2).
- Regla del calendario: la mañana de cada partido del Celta en Balaídos se publica esta previa (el Celta Fortuna y los partidos
  fuera no la llevan). En partidos de tarde la previa va a mediodía de antelación; si el partido es por la mañana, publicarla
  a primera hora. Falta engancharlo a la ejecución automática (necesita la lista de partidos en casa).
- Logo de la peña en alta calidad (1024 px, el que se adjuntó) en `assets/marca/escudo_marexada.png`; en el pie de todas las
  imágenes de diseño historia sale algo más grande (164 px) y más nítido. Todas las imágenes de `ejemplos/` regeneradas.

## Novedades v7
- `besoccer.py`: lector de AS Celtas Fem. Lee la clasificación y la página de partidos de besoccer y escribe en `datos_reales/`
  `clasificacion_as_celtas_fem.json`, `resultado_as_celtas_fem.json` (último partido jugado) y `proximo_as_celtas_fem.json`
  (próximo partido, con hora si besoccer ya la publica). Uso: `python besoccer.py` (lee internet) o
  `python besoccer.py --clasif archivo.html --partidos archivo.html --hoy 2026-11-10`.
  Soporta Segunda Federación Femenina y Copa de la Reina (con penaltis). Si besoccer cambia y no encuentra la tabla o los
  partidos, da un error claro en vez de inventar datos.
- AS Celtas lleva el escudo del Celta. Los escudos que faltan en el pack salen con siglas (decidido: no importa).
- PROBADO SOLO CON COPIAS RECONSTRUIDAS: `fixtures/besoccer_*_RECONSTRUIDO.html` están escritas a mano a partir del texto de
  las páginas, no son el HTML original de besoccer. La primera ejecución real (GitHub Actions) puede necesitar un ajuste.
- La copia de la página de partidos que se usó era de septiembre: el `resultado_as_celtas_fem.json` de ejemplo es el 5-0 al
  Osasuna B (xornada 2), no el último partido real. Con la página en directo saldrá el último.
- Sin goleadores: besoccer los tiene en la página de cada partido, no en el listado. Pendiente.

## Novedades v6
- Nuevo tipo `clasificacion` (diseño historia 1080x1920): tabla completa con posición, escudo, equipo, PJ, DG y puntos;
  resalta la fila del equipo indicado en `destacado`. Ejemplo real: `datos_reales/clasificacion_as_celtas_fem.json`
  (AS Celtas Fem, Segunda Federación Femenina Grupo 1, tras 8 jornadas) -> `ejemplos/real_clasificacion_as_celtas_fem.png`.
  Los clubes sin escudo en `assets/escudos/` salen con sus siglas en un círculo azul.
- Diseño historia con tipografía Poppins (antes DejaVu) y la jornada visible en resultados y próximos partidos.
  En los resultados, la fecha y los goleadores tienen más separación.
- AS Celtas: solo el equipo femenino. Datos de besoccer, que se leen como texto sin JavaScript:
  clasificación https://es.besoccer.com/equipo/clasificacion/ud-mos y partidos https://es.besoccer.com/equipo/partidos/ud-mos
  (el nombre «ud-mos» es el del equipo anterior). Desde la v7 las lee `besoccer.py`. Conviene revisar los términos de uso de besoccer.
- Escudos de AS Celtas Fem: se han asignado los que ya estaban en el pack (Deportivo, Oviedo, Sporting, Eibar, Burgos,
  Racing, Osasuna, Rayo). Faltan Real Avilés, CD Arratia, Club Bizkerre, Victoria CF, Madrid CFF B y el propio AS Celtas.

## Diseño «historia» (novedad v5)
- LaLiga, Hypermotion (Celta Fortuna) y Copa usan el diseño de las demos de la peña: 1080x1920, título grande, logo de la
  competición, escudos redondos, fecha y hora en grande, escudo y web de la peña abajo. Código en `generar_historia.py`.
  Europa League sigue con el diseño anterior (1080x1350, fondo negro y naranja).
- Tipos: `proximo` (nuevo), `resultado`, `convocatoria` y `alineacion`. `generar.py` elige el diseño solo según `competicion`.
- Logos de competición y escudo de la peña en `assets/marca/` (recortados de las demos: 280 px; con los originales saldrían más nítidos).
- Fecha larga en gallego («Sábado 31 de outubro»). En los resultados sale la fecha de publicación de la crónica.
- FONDO PROVISIONAL: `assets/fondos/historia_provisional.jpg` es la foto de Balaídos del proyecto ampliada y desenfocada.
  Para usar la foto original de las demos, copiarla (1080x1920) como `assets/fondos/historia.jpg`: se usa sola.
- Posiciones (POR/DEF/MED/DEL) de las demos: el club no las publica en la convocatoria. Si el JSON trae `pos` en un
  jugador, sale «Nombre (POS)»; si no, solo el nombre. Falta una tabla de plantilla para rellenarlas.
- Próximo partido: ya se dibuja desde un JSON (`datos_ejemplo/proximo_*.json`); falta leer los datos de la web.

## Celta Fortuna (v4)
- Juega en LaLiga Hypermotion 2026/27 (ascendió en junio de 2026). Los 22 rivales de la liga ya tienen escudo en `assets/`.
- Sus noticias están en rccelta.es/fundacion/actualidad/ (no en /equipo/actualidad/) y llevan la etiqueta «Celta Fortuna»
  (rccelta.es/categorias-actualidad-fundacion/celta-fortuna/).
- Las convocatorias tienen el mismo formato que las del primer equipo, pero pueden no nombrar al rival en el título
  («para su visita al estadio El Molinón»): el lector lo saca del primer párrafo. La jornada va en letra («duodécima»).
- Las crónicas tienen título libre («Un empate con sabor a poco ... (2-2)»): el lector toma equipos y marcador de la
  FICHA TÉCNICA (el primero que sale es el local). Los goles vienen separados por «. » y no por «;»: soportados los dos.
- En la imagen sale la etiqueta CELTA FORTUNA arriba, «Hypermotion · Xornada N» y el nombre del equipo. Usa el escudo del Celta
  (si el Fortuna tiene escudo propio, basta añadir un `celta-fortuna-logo-footylogos.png` y un cambio de una línea).
- Real Sociedad B sale con el escudo de la Real Sociedad y el nombre «REAL SOCIEDAD B».
- Bajas: las de sanción ahora también salen (antes solo las de lesión). Los que siguen concentrados con su selección no se listan.
- Los vídeos «Resumen y goles» del Fortuna no son crónicas: el lector los ignora.

## Calendario semanal (2 publicaciones al día, mañana ~10:00 y tarde ~19:00)
| Día | Mañana | Tarde |
|---|---|---|
| Lunes | Noticia del día (lesión, fichaje o rueda de prensa) | Clasificación |
| Martes | Noticia del día | Celta Fortuna / cantera |
| Miércoles | Noticia del día | Efeméride |
| Jueves | Noticia del día | AS Celtas |
| Viernes | Cuenta atrás / previa | Convocatoria |
| Sábado | Cumpleaños o goleadores | Contenido de peña (viaje, merchandising, socios) |
| Domingo | Entradas / abonos o peña | Resumen de la semana |

En día de partido: cuenta atrás, alineación una hora antes y resultado al terminar. Si el Celta juega en Balaídos,
además, por la mañana, la previa en la Cafetería Kiev (dos horas antes del comienzo).
Si un día no hay noticia nueva se usa contenido de relleno. Nunca se repite una publicación.

## Cómo está hecha la web del club (lo que se ha comprobado)
- Convocatoria: título "Convocatoria del Celta para recibir al X" y un párrafo "La lista de convocados la formarán
  Nombre (dorsal), ..." más "Serán baja por lesión Nombre (dorsal), ...". Fecha, hora y jornada van en el primer párrafo.
- Crónica: título "Frase | Celta 0-0 Levante"; al final "FICHA TÉCNICA" con los dos onces y los cambios,
  una línea "Goles: 1-0, min. 11: Nombre; ..." si hay goles, y "Incidencias" con la jornada y la competición.
- La página de listado de noticias carga las noticias con JavaScript: leída como texto simple no
  muestra la lista. Hay que descubrir las noticias nuevas por otro camino (feed, sitemap o API de WordPress,
  o un navegador automático). Se prueba en la primera ejecución en GitHub.

## Pendiente
1. Noticias del día (lesiones, fichajes, ruedas de prensa): la lista de rccelta.es ya se lee (v13); falta decidir cuáles merecen historia.
2. Alineación antes del partido: no se ha visto dónde la publica el club. La ficha técnica de la crónica
   solo sale al terminar.
3. Lesiones (parte médico) y fichajes oficiales: falta ver noticias de ejemplo.
4. Diseños de peña: viajes, merchandising, hazte socio, cuenta atrás, clasificación.
5. Publicación automática en Instagram (la ejecución diaria en GitHub Actions ya está en v11, en modo revisión).
6. AS Celtas Fem (Segunda Federación Femenina, Grupo 1): lector de besoccer, partido a partido y escudos que faltan (ver v6).
   Clubes que no estén en los packs (por ejemplo Salamanca UDS, de la Copa del Rey): hoy salen con sus siglas.
7. Fotos de fondo de más resolución, si se consigue.
