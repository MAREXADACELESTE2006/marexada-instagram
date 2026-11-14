"""Marexada Celeste · programa diario de historias de Instagram (v20) — MODO REVISIÓN.

Cada día (lo ejecuta GitHub Actions, ver INSTALAR.md) este programa:
  1. lee las fuentes: noticias de rccelta.es (convocatorias y crónicas), calendario y resultados del Celta/Fortuna (ESPN/TheSportsDB), clasificaciones y AS Celtas Fem (besoccer);
  2. decide qué historias tocan hoy según el calendario semanal;
  3. genera las imágenes (1080x1920) en  salida/AAAA-MM-DD/  con un  resumen.md  (hora sugerida y texto para cada una);
  4. apunta lo generado en  estado/publicado.json  para no repetir nada;
  5. si hay Telegram configurado, te manda las historias al móvil para revisarlas y subirlas.
NO publica en Instagram: las subes tú tras revisarlas.

Uso:
    python diario.py                       (hoy, leyendo internet)
    python diario.py --offline --hoy 2026-11-08      (prueba sin internet con los datos de ejemplo de fixtures/)
Opciones: --forzar (ignora lo ya generado), --sin-estado (no actualiza estado/publicado.json), --sin-telegram.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import unicodedata
import subprocess
import sys
import urllib.request
import uuid
from zoneinfo import ZoneInfo

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
MADRID = ZoneInfo("Europe/Madrid")
ESTADO = os.path.join(BASE, "estado", "publicado.json")
AGENDA = os.path.join(BASE, "estado", "agenda.json")           # fechas de los partidos cercanos (la usa el modo rápido para saber si hay algo que vigilar)
RAPIDAS = {"calendario.py", "noticias.py", "resultados.py", "futbolme.py", "besoccer.py"}     # fuentes del modo rápido: convocatorias y resultados
CLAVES_RAPIDAS = ("convocatoria-", "cronica-", "resultado-")
HASHTAGS = "#RCCelta #Celta #MarexadaCeleste"

RECORDATORIOS = {
    0: ["Noticia do día (mañá, de rccelta.es)"],
    1: ["Noticia do día (mañá, de rccelta.es)", "Celta Fortuna / cantera (tarde, de rccelta.es)"],
    2: ["Noticia do día (mañá, de rccelta.es)", "Efeméride (tarde, contido propio)"],
    3: ["Noticia do día (mañá, de rccelta.es)"],
    4: ["Convocatoria (tarde, cando a publique o club)"],
    5: ["Aniversarios ou goleadores (mañá)", "Contido de peña: viaxe, merchandising, socios (tarde)"],
    6: ["Entradas / abonos ou peña (mañá)", "Resumo da semana (tarde)"],
}


# ---------------------------------------------------------------- utilidades
def cargar(ruta):
    try:
        return json.load(open(ruta, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def fecha_de(d):
    try:
        return datetime.date.fromisoformat(d["_fecha"])
    except (KeyError, ValueError, TypeError):
        return None


def correr(script, args, etiqueta, avisos):
    try:
        r = subprocess.run([sys.executable, os.path.join(BASE, script), *args], capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired:
        avisos.append(f"{etiqueta}: tardó demasiado y se cortó")
        return False
    if r.returncode != 0:
        ultima = ((r.stderr or r.stdout).strip().splitlines() or ["sin detalle"])[-1]
        avisos.append(f"{etiqueta}: {ultima}")
    return r.returncode == 0


def hay_partido_cerca(hoy):
    """Modo rápido: ¿hay un partido del Celta, del Fortuna o del AS Celtas ayer, hoy o en los próximos 2 días? Sin agenda guardada, sí."""
    ag = cargar(AGENDA)
    if not ag or not ag.get("partidos"):
        return True
    for p in ag["partidos"]:
        try:
            if -1 <= (datetime.date.fromisoformat(p["fecha"]) - hoy).days <= 2:
                return True
        except (KeyError, ValueError):
            continue
    return False


def guardar_agenda(datos, hoy):
    """Recuerda las fechas de los próximos partidos y de los últimos resultados (3 días atrás) para que el modo rápido sepa cuándo vigilar."""
    viejas = (cargar(AGENDA) or {}).get("partidos", [])
    nuevas = {(p["equipo"], p["fecha"]) for p in viejas if p.get("fecha") and (hoy - datetime.date.fromisoformat(p["fecha"])).days <= 3}
    for nombre in ("celta", "fortuna", "as_celtas_fem"):
        for pref in ("proximo", "resultado"):
            f = fecha_de(datos.get(f"{pref}_{nombre}.json"))
            if f:
                nuevas.add((nombre, f.isoformat()))
    os.makedirs(os.path.dirname(AGENDA), exist_ok=True)
    json.dump({"actualizada": hoy.isoformat(), "partidos": [{"equipo": e, "fecha": f} for e, f in sorted(nuevas)]},
              open(AGENDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def fecha_partido(c, hoy):
    """Fecha del partido de una convocatoria a partir de su texto «Ven 13/11 · 21:00» (el año se deduce: el más cercano a hoy)."""
    m = re.search(r"(\d{1,2})/(\d{1,2})", (c or {}).get("fecha_hora") or "")
    if not m:
        return None
    for anio in (hoy.year, hoy.year + 1, hoy.year - 1):
        try:
            f = datetime.date(anio, int(m.group(2)), int(m.group(1)))
        except ValueError:
            continue
        if abs((f - hoy).days) <= 40:
            return f
    return None


def hora_madrid():
    return datetime.datetime.now(MADRID).hour


def nombre_lado(d, lado):
    import generar_historia as H
    return H.nombre(d, lado)


def hora_previa(d):
    m = re.search(r"(\d{1,2}):(\d{2})", d.get("fecha_hora", ""))
    if not m:
        return None
    return f"{(int(m.group(1)) - d.get('horas_antes', 2)) % 24:02d}:{m.group(2)}"


def etiquetas(nombre):
    return "#ASCeltas #MarexadaCeleste" if nombre == "as-celtas-fem" else HASHTAGS


# ---------------------------------------------------------------- qué toca hoy

# ---------------------------------------------------------------- control de actualidad (obligatorio antes de generar una imagen)
MAX_DIAS_NOTICIA = 2
CONTROLADOS = {"entradas", "partemedico", "cumpleanos", "pronostico"}                 # historias basadas en noticias o datos que pueden quedarse viejos
RELATIVOS = re.compile(r"\b(hoy|hoxe|ma[ñn][aá]n?a|ma[ñn]á|ayer|onte|ahora mismo|[uú]ltimas? horas?|esta (?:tarde|noche|semana)|este fin de semana|"
                       r"en breve|dende hoxe|desde hoy)\b", re.I)


def control_actualidad(h, jd, datos, hoy):
    """Comprueba antes de generar la imagen: 1) fecha de la noticia, 2) fecha del acontecimiento (partido), 3) que se haya vuelto a
    consultar la fuente oficial en esta misma ejecución, 4) que el texto no use «hoy», «mañana»... sin corresponder.
    Devuelve (ok, resumen_para_el_control)."""
    pub = jd.get("publicada")
    evento = (jd.get("partido_fecha_hora") or "")[:10] or None
    info = (f"noticia {pub[8:10] + '/' + pub[5:7] if pub else '—'} · partido {evento[8:10] + '/' + evento[5:7] if evento else '—'}"
            if (pub or evento) else "dato de estado (sin fecha de noticia)")
    if pub and (hoy - datetime.date.fromisoformat(pub)).days > MAX_DIAS_NOTICIA:
        return False, f"{info} → DESCARTADA: noticia de hace {(hoy - datetime.date.fromisoformat(pub)).days} días"
    if jd.get("tipo") == "entradas":
        if not evento:                                           # sin fecha en la noticia: se contrasta con el calendario oficial
            rival = {jd.get("local"), jd.get("visitante")} - {"celta-vigo", None}
            for f in ("proximo_celta.json", "proximo_fortuna.json"):
                p = datos.get(f)
                if p and rival and rival & {p.get("local"), p.get("visitante")}:
                    evento = p.get("_fecha")
                    jd["partido_fecha_hora"] = jd.get("partido_fecha_hora") or None
        if not evento:
            return False, f"{info} → DESCARTADA: no puedo confirmar la fecha del partido"
        if datetime.date.fromisoformat(evento) < hoy:
            return False, f"{info} → DESCARTADA: el partido ya se jugó ({evento})"
        try:                                                     # (la ejecución corre en hora UTC y «hoy» es la fecha de Madrid: se admite 1 día)
            ok_ver = abs((hoy - datetime.date.fromisoformat((jd.get("verificada") or "")[:10])).days) <= 1
        except ValueError:
            ok_ver = False
        if not ok_ver:
            return False, f"{info} → DESCARTADA: la fuente oficial no se ha vuelto a consultar hoy"
    textos = [h["texto"]] + [str(x) for x in jd.get("puntos", [])] + [jd.get("intro", "")]
    for t in textos:
        m = RELATIVOS.search(t or "")
        if m and not (pub == hoy.isoformat()):
            return False, f"{info} → DESCARTADA: lenguaje temporal sin fecha real («{m.group(0)}»)"
    return True, f"{info} → OK" + (f" (verificada {jd['verificada'][11:16]})" if jd.get("verificada") else "")


def crear_pronostico(datos, hoy, d_datos):
    """Pronóstico da peña: los viernes, del próximo partido del Celta si se juega de viernes a lunes. Crea pronostico_celta.json a partir del
    calendario oficial (así la fecha del partido es la del calendario, nunca una frase suelta)."""
    p = datos.get("proximo_celta.json")
    f = fecha_de(p) if p else None
    if hoy.weekday() != 4 or not p or not f or not (0 <= (f - hoy).days <= 3):
        return
    hora = re.search(r"(\d{1,2}:\d{2})", p.get("fecha_hora") or "")
    pr = {**p, "tipo": "pronostico", "partido_fecha_hora": f"{f.isoformat()}T{hora.group(1) if hora else '00:00'}"}
    with open(os.path.join(d_datos, "pronostico_celta.json"), "w", encoding="utf-8") as fh:
        json.dump(pr, fh, ensure_ascii=False, indent=1)
    datos["pronostico_celta.json"] = pr


def plan(hoy, datos, avisos):
    """Devuelve una lista de historias: clave (para no repetir), fichero de datos, momento, hora sugerida y texto."""
    wd = hoy.weekday()
    out = []

    def add(clave, fichero, momento, hora, texto):
        out.append({"clave": clave, "fichero": fichero, "momento": momento, "hora": hora, "texto": texto})

    previa = datos.get("previa_hoy.json")
    if previa:
        hp = hora_previa(previa)
        add(f"previa-{previa['fecha_hora']}", "previa_hoy.json", "previa", "primeira hora da mañá",
            f"Hoxe hai previa na nosa sede, a Cafetería Kiev, ás {hp} h! Veña tomar algo antes do "
            f"{nombre_lado(previa, 'local')} - {nombre_lado(previa, 'visitante')} 🍻 {HASHTAGS}")

    for nombre, fichero in (("celta", "proximo_celta.json"), ("fortuna", "proximo_fortuna.json"), ("as-celtas-fem", "proximo_as_celtas_fem.json")):
        d = datos.get(fichero)
        f = fecha_de(d)
        if not d or not f or not (0 <= (f - hoy).days <= 1):
            continue
        if nombre == "celta" and previa and f == hoy:
            continue                                   # el día del partido en casa ya sale la previa
        cuando = "Hoxe" if f == hoy else "Mañá"
        add(f"proximo-{nombre}-{d['fecha_hora']}", fichero, "mañana", "10:00",
            f"{cuando} xogamos! {nombre_lado(d, 'local')} - {nombre_lado(d, 'visitante')}, {d['fecha_hora']}. Forza! 💙 {etiquetas(nombre)}")

    pr = datos.get("pronostico_celta.json")                       # viernes: pronóstico da peña (el resultado lo pone la gente con la enquisa)
    if pr and pr.get("_fecha"):
        loc, vis = nombre_lado(pr, "local"), nombre_lado(pr, "visitante")
        add(f"pronostico-{pr['_fecha']}", "pronostico_celta.json", "mañana", "10:00",
            f"🔮 PRONÓSTICO DA PEÑA: {loc} - {vis} ({pr['fecha_hora']}). Cal será o resultado? Responde coa túa aposta: "
            f"1 ({loc}) · X (empate) · 2 ({vis}) 💙 {etiquetas('celta')}")

    def corto(d):
        return re.sub(r"[^a-z0-9]+", "-", (d.get("_url") or "").rstrip("/").split("/")[-1].lower())[:60]

    con_cronica = set()
    for nombre in ("celta", "fortuna"):
        c = datos.get(f"convocatoria_{nombre}.json")
        f = fecha_de(c)
        fp = fecha_partido(c, hoy)
        # vale si la noticia es de hoy o ayer; si no se sabe su fecha, si el partido es hoy, mañana o pasado mañana
        vigente = (f is not None and 0 <= (hoy - f).days <= 1) or (f is None and fp is not None and 0 <= (fp - hoy).days <= 2)
        if c and f is None and fp is None:
            avisos.append(f"Convocatoria {nombre}: sin fecha de noticia ni de partido; no se publica")
        if c and vigente:
            add(f"convocatoria-{nombre}-{corto(c)}", f"convocatoria_{nombre}.json", "tarde", "cando a publica o club (ou a tarde)",
                f"Convocatoria: {nombre_lado(c, 'local')} - {nombre_lado(c, 'visitante')}, {c['fecha_hora']}. Estes son os convocados! 💙 {etiquetas(nombre)}")
        k = datos.get(f"cronica_{nombre}.json")
        f = fecha_de(k)
        if k and f is None:
            avisos.append(f"Crónica {nombre}: no se conoce su fecha; no se publica (el resultado sale igual por el calendario)")
        if k and f and 0 <= (hoy - f).days <= 1:
            con_cronica.add(nombre)
            add(f"cronica-{nombre}-{corto(k)}", f"cronica_{nombre}.json", "resultado", "xusto ao rematar o partido",
                f"Final: {nombre_lado(k, 'local')} {k['goles_local']} - {k['goles_visitante']} {nombre_lado(k, 'visitante')}. 💙 {etiquetas(nombre)}"
                " (Versión con goleadores: se xa subiches a do marcador, substitúea.)")

    for nombre, fichero in (("celta", "resultado_celta.json"), ("fortuna", "resultado_fortuna.json"), ("as-celtas-fem", "resultado_as_celtas_fem.json")):
        r = datos.get(fichero)
        f = fecha_de(r)
        if not r or not f or not (0 <= (hoy - f).days <= 1) or nombre in con_cronica:
            continue                                   # si ya hay crónica (con goleadores) no se saca la del marcador
        cierre = "Orgullosas do AS Celtas!" if nombre == "as-celtas-fem" else "Forza Celta!"
        con_gol = bool(r.get("goleadores_local") or r.get("goleadores_visitante"))     # v42: si más tarde aparecen los goleadores, sale otra historia (clave distinta) para sustituir la primera
        aviso_gol = " (Versión con goleadores: se xa subiches a do marcador, substitúea.)" if con_gol else ""
        add(f"resultado-{nombre}-{r['fecha_hora']}-{r['goles_local']}-{r['goles_visitante']}" + ("-g" if con_gol else ""), fichero, "resultado", "xusto ao rematar o partido",
            f"Final: {nombre_lado(r, 'local')} {r['goles_local']} - {r['goles_visitante']} {nombre_lado(r, 'visitante')}. {cierre} 💙 {etiquetas(nombre)}{aviso_gol}")

    tabla = {0: ("clasificacion_celta_laliga.json", "laliga", "LaLiga"), 1: ("clasificacion_celta_fortuna.json", "fortuna", "LaLiga Hypermotion (Celta Fortuna)"),
             3: ("clasificacion_as_celtas_fem.json", "as-celtas-fem", "Segunda Federación Femenina (AS Celtas)")}.get(wd)
    if tabla:
        d = datos.get(tabla[0])
        if d:
            add(f"clasificacion-{tabla[1]}-{d['jornada']}", tabla[0], "tarde", "19:00",
                f"Así está a clasificación de {tabla[2]} tras a {d['jornada'].lower()}. 💙 {etiquetas(tabla[1])}")
    # Parte médico: sale una historia cuando el parte cambia (entra o sale alguien, o cambia un diagnóstico).
    for nombre in ("celta", "fortuna"):
        for fichero in sorted(f for f in datos if re.fullmatch(rf"partemedico_{nombre}(_\d+)?\.json", f)):
            pm = datos[fichero]
            if not pm or not pm.get("firma"):
                continue
            pag = pm.get("pagina") or "1/1"
            quien = "do Celta Fortuna" if nombre == "fortuna" else "do Celta"
            n = pm.get("n_total", len(pm.get("lesionados", [])))
            if n:
                nombres = ", ".join(x["nombre"] for x in pm["lesionados"])
                txt = f"Parte médico {quien}: {n} {'xogador' if n == 1 else 'xogadores'} en baixa. {nombres}. Moito ánimo e pronta recuperación! 💙 {etiquetas(nombre)}"
            else:
                txt = f"Parte médico {quien}: sen baixas por lesión! 💙 {etiquetas(nombre)}"
            add(f"partemedico-{nombre}-{pm['firma']}-{pag.split('/')[0]}", fichero, "tarde", "cando o publique o club (ou a tarde)", txt)
    # Entradas: una historia por cada noticia nueva de entradas del Celta o del Celta Fortuna en rccelta.es.
    for fichero in sorted(f for f in datos if re.fullmatch(r"entradas_.+\.json", f)):
        en = datos[fichero]
        if not en or not en.get("nombre"):
            continue
        partido = en.get("partido") or "o próximo partido"
        primero = (" " + en["puntos"][0] + ".") if en.get("puntos") else ""
        que = "Entradas para afeccionados visitantes" if en.get("visitantes") else "Entradas dispoñibles"
        add(f"entradas-{en['nombre']}", fichero, "mañana", "canto antes (para avisar aos peñistas)",
            f"🎟️ {que}: {partido}.{primero} Todos os detalles: {en.get('url', 'rccelta.es')} {etiquetas('celta')}")

    # Cumpleaños: una historia por cada jugador o miembro del cuerpo técnico que cumple años hoy (datos en cumpleanos.json).
    for fichero in sorted(f for f in datos if re.fullmatch(r"cumpleanos_.+\.json", f)):
        c = datos[fichero]
        if not c or not c.get("nombre"):
            continue
        quien = f"o noso adestrador {c['nombre']}" if "adestrador" in (c.get("posicion") or "").lower() else c["nombre"]
        add(f"cumple-{fichero[10:-5]}-{c.get('año', hoy.year)}", fichero, "mañana", "09:00",
            f"🎂 O {c['fecha']} cumpre {c['edad']} anos {quien}! Moitas felicidades e que cumpra moitos máis co celeste no peito 💙 {etiquetas(c.get('equipo', 'celta'))}")
    return out


# ---------------------------------------------------------------- Telegram (opcional)
def telegram(historias, resumen, avisos, rapido=False):
    token, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False

    def llamar(metodo, campos, archivo=None):
        b = uuid.uuid4().hex
        cuerpo = b""
        for k, v in campos.items():
            cuerpo += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8")
        if archivo:
            cuerpo += (f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="{os.path.basename(archivo)}"\r\n'
                       f'Content-Type: image/jpeg\r\n\r\n').encode() + open(archivo, "rb").read() + b"\r\n"
        cuerpo += f"--{b}--\r\n".encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{metodo}", data=cuerpo,
                                     headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        urllib.request.urlopen(req, timeout=60).read()

    try:
        if not rapido:                                             # en modo rápido no se manda el resumen: solo la foto, con su texto, al momento
            llamar("sendMessage", {"chat_id": chat, "text": resumen[:4000]})
        for h in historias:
            cab = "⚡ " if rapido else f"{h['hora']} · "
            llamar("sendPhoto", {"chat_id": chat, "caption": f"{cab}{h['texto']}"[:1000]}, h["imagen"])
        return True
    except Exception as e:
        avisos.append(f"Telegram: {e}")
        return False


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hoy", default=None, help="AAAA-MM-DD (por defecto, hoy en Madrid)")
    ap.add_argument("--offline", action="store_true", help="usa los datos de ejemplo de fixtures/ en vez de internet")
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--sin-estado", action="store_true")
    ap.add_argument("--sin-telegram", action="store_true")
    ap.add_argument("--salida", default=os.path.join(BASE, "salida"))
    ap.add_argument("--modo", choices=("completo", "rapido"), default="completo",
                    help="rapido: solo convocatorias y resultados (se ejecuta cada 15-20 minutos; si no hay partido cerca, termina enseguida)")
    a = ap.parse_args()
    hoy = datetime.date.fromisoformat(a.hoy) if a.hoy else datetime.datetime.now(MADRID).date()
    rapido = a.modo == "rapido"
    if rapido and not a.offline and not hay_partido_cerca(hoy):
        print("Modo rápido: no hay partidos del Celta, del Fortuna ni del AS Celtas cerca. No hay nada que vigilar.")
        return
    carpeta = os.path.join(a.salida, hoy.isoformat())
    d_datos = os.path.join(carpeta, "datos")
    shutil.rmtree(carpeta, ignore_errors=True)
    os.makedirs(d_datos)
    avisos = []

    fx = lambda n: os.path.join(BASE, "fixtures", n)
    if a.offline:
        fuentes = [
            ("calendario.py", ["--desde", fx("partidos_api_EJEMPLO.json"), "--ahora", f"{hoy.isoformat()}T06:00:00", "--salida", d_datos], "Calendario"),
            ("clasificaciones.py", ["--desde", fx("web_respaldo_jornada8_LL_EL_HM.json"), "--salida", d_datos], "Clasificaciones"),
            ("noticias.py", ["--desde", fx("rccelta_web_RECONSTRUIDO"), "--salida", d_datos], "Noticias rccelta.es"),
            ("resultados.py", ["--desde", fx("espn_resultados_EJEMPLO.json"), "--ahora", f"{hoy.isoformat()}T06:00:00", "--salida", d_datos], "Resultados Celta/Fortuna"),
            ("besoccer.py", ["--clasif", fx("besoccer_clasificacion_RECONSTRUIDO.html"), "--partidos", fx("besoccer_partidos_RECONSTRUIDO.html"),
                             "--hoy", hoy.isoformat(), "--salida", d_datos], "AS Celtas Fem (besoccer)"),
            ("partemedico.py", ["--hoy", hoy.isoformat(), "--desde", fx("partemedico_REAL"), "--salida", d_datos], "Parte médico (rccelta.es)"),
            ("entradas.py", ["--hoy", hoy.isoformat(), "--desde", fx("entradas_RECONSTRUIDO"), "--salida", d_datos], "Entradas (rccelta.es)"),
            ("cumpleanos.py", ["--hoy", hoy.isoformat(), "--salida", d_datos], "Cumpleaños"),
        ]
    else:
        ahora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        fuentes = [
            ("calendario.py", ["--ahora", ahora, "--salida", d_datos], "Calendario"),
            ("clasificaciones.py", ["--salida", d_datos], "Clasificaciones"),
            ("noticias.py", ["--salida", d_datos], "Noticias rccelta.es"),
            ("resultados.py", ["--ahora", ahora, "--salida", d_datos], "Resultados Celta/Fortuna"),
            ("futbolme.py", ["--hoy", hoy.isoformat(), "--salida", d_datos], "AS Celtas Fem (futbolme)"),
            ("partemedico.py", ["--hoy", hoy.isoformat(), "--salida", d_datos], "Parte médico (rccelta.es)"),
            ("entradas.py", ["--hoy", hoy.isoformat(), "--salida", d_datos], "Entradas (rccelta.es)"),
            ("cumpleanos.py", ["--hoy", hoy.isoformat(), "--salida", d_datos], "Cumpleaños"),
        ]
    if rapido:
        fuentes = [f for f in fuentes if f[0] in RAPIDAS]
    ok = [correr(s, args, etq, avisos) for s, args, etq in fuentes]

    datos = {f: cargar(os.path.join(d_datos, f)) for f in os.listdir(d_datos) if f.endswith(".json")}
    crear_pronostico(datos, hoy, d_datos)
    if not a.offline and not a.sin_estado:
        try:
            guardar_agenda(datos, hoy)
        except Exception as e:                                     # la agenda es una ayuda: si falla, no se para nada
            avisos.append(f"Agenda: {e}")
    estado = cargar(ESTADO) or {}
    historias = []
    controles = []
    for h in plan(hoy, datos, avisos):
        if h["clave"] in estado and not a.forzar:
            continue
        if rapido and not h["clave"].startswith(CLAVES_RAPIDAS):
            continue                                              # el modo rápido solo saca convocatorias y resultados
        jd = datos.get(h["fichero"]) or {}
        if jd.get("tipo") in CONTROLADOS:
            ok_c, msg = control_actualidad(h, jd, datos, hoy)
            controles.append(f"{h['clave']}: {msg}")
            if not ok_c:
                continue
        historias.append(h)
    for c in (datos.get("control_entradas.json") or []):              # noticias de entradas que ya descartó el lector
        if c.get("decision") == "DESCARTADA":
            controles.append(f"{c['noticia']}: noticia {(c['publicada'] or '—')[8:10]}/{(c['publicada'] or '—')[5:7]} → DESCARTADA: {c['motivo']}")

    import generar
    for i, h in enumerate(historias, 1):
        limpio = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", h["clave"]).encode("ascii", "ignore").decode().lower()).strip("-")[:50]
        h["imagen"] = os.path.join(carpeta, f"{i:02d}_{limpio}.jpg")
        try:
            generar.generar(os.path.join(d_datos, h["fichero"]), h["imagen"])
        except Exception as e:
            avisos.append(f"No se pudo generar {h['clave']}: {e}")
            h["imagen"] = None
    historias = [h for h in historias if h["imagen"]]

    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    L = [f"# Historias de {dias[hoy.weekday()]} {hoy.strftime('%d/%m/%Y')}", ""]
    if historias:
        L += ["| Hora sugerida | Imagen | Texto sugerido |", "|---|---|---|"]
        L += [f"| {h['hora']} | {os.path.basename(h['imagen'])} | {h['texto']} |" for h in historias]
    else:
        L.append("Hoy no hay historias automáticas nuevas.")
    L += ["", "## Contido propio que toca hoxe (aínda sen automatizar)"] + [f"- {r}" for r in RECORDATORIOS[hoy.weekday()]]
    L += ["- Aliñación do Celta e do Fortuna: non se xera (non fai falta)."]
    if controles:
        L += ["", "## Control de actualidad"] + [f"- {x}" for x in controles]
    if avisos:
        L += ["", "## Avisos"] + [f"- {x}" for x in avisos]
    resumen = "\n".join(L) + "\n"
    open(os.path.join(carpeta, "resumen.md"), "w", encoding="utf-8").write(resumen)

    # Telegram: avisa cuando hay historias nuevas o algún aviso (error). Además, el resumen del día (con el contenido propio que
    # toca hoy) llega UNA vez al día, en la primera ejecución de la mañana (o siempre que lances el trabajo a mano).
    clave_resumen = f"resumen-{hoy.isoformat()}"
    manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    resumen_dia = not a.offline and not rapido and (manual or (5 <= hora_madrid() < 13 and clave_resumen not in estado))
    enviado = False
    configurado = bool(os.environ.get("TELEGRAM_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))
    quiere_envio = bool(historias) if rapido else bool(historias or avisos or resumen_dia)     # modo rápido: solo avisa si hay historias (los avisos van en las ejecuciones completas)
    if not a.sin_telegram and not a.offline and quiere_envio:
        enviado = telegram(historias, resumen, avisos, rapido)
    # Si Telegram está configurado y el envío falla, no se anota nada: las historias y el resumen se reintentan en la siguiente ejecución.
    fallo_envio = configurado and quiere_envio and not enviado and not a.sin_telegram and not a.offline
    if not a.sin_estado and not a.offline and not fallo_envio:
        if resumen_dia and not manual:
            estado[clave_resumen] = hoy.isoformat()
        for h in historias:
            estado[h["clave"]] = hoy.isoformat()
        os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
        json.dump(dict(sorted(estado.items())[-400:]), open(ESTADO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(resumen)
    if not any(ok):
        sys.exit("ERROR: fallaron las tres fuentes de datos (revisa los avisos).")


if __name__ == "__main__":
    main()
