# Marexada Celeste · Instagram automático · v13

Diseños de partido + lector de la web del club (rccelta.es).
Todavía NO descubre noticias nuevas solo ni publica en Instagram: eso es lo siguiente.

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
