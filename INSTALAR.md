# Instalar el programa diario en GitHub (paso a paso)

Resultado: cada día, solo, GitHub prepara las historias que tocan, con su hora y su texto sugeridos.
Tú las revisas y las subes a Instagram. (Todavía no publica solo.)

## 1. Crear el repositorio
1. Entra en https://github.com con tu cuenta y pulsa **New repository**.
2. Nombre: `marexada-instagram`. Márcalo como **Private** (privado). Pulsa **Create repository**.

## 2. Subir los archivos
1. Descomprime el ZIP en tu ordenador. Dentro hay una carpeta `Marexada-Instagram_v13`. Entra en ella.
2. En el repositorio, pulsa **uploading an existing file** (o *Add file → Upload files*).
3. Arrastra **el contenido** de esa carpeta (no la carpeta entera): tiene que quedar `diario.py` en la raíz del repositorio.
   Arrastra también la carpeta `.github` (es una carpeta oculta; en Windows, activa *Ver → Elementos ocultos* si no la ves).
4. Pulsa **Commit changes**.

Si `.github` no se sube, créala a mano: *Add file → Create new file*, escribe como nombre
`.github/workflows/diario.yml`, pega el contenido del archivo `diario.yml` que hay en esa carpeta y pulsa *Commit*.

## 3. Comprobar que funciona
1. Pestaña **Actions**. Si te pide activarlas, pulsa el botón verde.
2. Elige **Historias diarias (revisión)** → **Run workflow** → **Run workflow**.
3. Espera 1-2 minutos. Entra en la ejecución: abajo, en **Artifacts**, descarga `historias`. Dentro, en `salida/FECHA/`,
   están las imágenes y `resumen.md` (hora y texto sugeridos). Los avisos salen al final de `resumen.md`.
4. Si ves un aviso rojo o el trabajo falla, **cópiame el texto del error**. Es la primera vez que se ejecuta con datos reales
   y puede hacer falta un ajuste.

A partir de ahí corre solo dos veces al día: a las 06:00 UTC (07:00 en invierno, 08:00 en verano, hora de Galicia) y a las 22:30 UTC
(23:30 / 00:30), para recoger el resultado de los partidos de la tarde-noche.

## 4. (Opcional, muy recomendable) Recibir las historias en el móvil por Telegram
1. En Telegram, habla con **@BotFather**, escribe `/newbot` y sigue los pasos. Te dará un **token**.
2. Escribe cualquier mensaje a tu bot nuevo.
3. Abre en el navegador `https://api.telegram.org/bot<TU_TOKEN>/getUpdates` y busca `"chat":{"id":` : ese número es tu **chat id**.
4. En GitHub: **Settings → Secrets and variables → Actions → New repository secret**. Crea dos:
   `TELEGRAM_TOKEN` (el token) y `TELEGRAM_CHAT_ID` (el número).
5. Vuelve a ejecutar el trabajo a mano. Te llegarán las historias con su hora y texto.
(Esta parte no se ha podido probar desde aquí; si falla, saldrá en los avisos.)

## Qué hace y qué no
- Hace: convocatorias y crónicas con goleadores del Celta y del Celta Fortuna (las lee de rccelta.es), previa de la Cafetería Kiev (mañana de partido del Celta en casa), anuncio de próximo partido (el día antes y el mismo día)
  del Celta, Celta Fortuna y AS Celtas Fem, resultado final por marcador (si no hay crónica) y crónica con goleadores, y la
  clasificación (lunes LaLiga, martes Fortuna, jueves AS Celtas Fem).
- No hace todavía: noticias sueltas (lesiones, fichajes), efemérides, cumpleaños ni contenido de peña. Alineaciones: no se generan. `resumen.md` te recuerda lo que toca cada día.
- No publica en Instagram: las subes tú. La publicación automática vendría más adelante.
- No repite: lo ya generado se anota en `estado/publicado.json`.
