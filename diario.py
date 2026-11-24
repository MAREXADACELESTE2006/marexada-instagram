"""Marexada Celeste · programa diario de historias de Instagram (v63) — MODO REVISIÓN.

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
import caras
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
CONSULTAS_WEB = os.path.join(BASE, "estado", "consultas_web.json")
# v68: freno por web. En modo RÁPIDO (que puede lanzarse cada 5 min) cada web «delicada» solo se consulta si pasaron N minutos desde la última vez.
# Las ejecuciones COMPLETAS (3 al día) consultan siempre. ESPN / TheSportsDB (APIs abiertas de datos) no llevan freno: son las que dan los goles.
FUENTE_HOST = {"noticias.py": "rccelta.es", "partemedico.py": "rccelta.es", "entradas.py": "rccelta.es", "besoccer.py": "besoccer.com", "futbolme.py": "futbolme.com", "baloncesto.py": "betexplorer.com"}
MIN_RAPIDO = {"rccelta.es": float(os.environ.get("MIN_RCCELTA", "60")),         # el club: como mucho 1 vez por hora
              "besoccer.com": float(os.environ.get("MIN_BESOCCER", "10")),      # webs que se leen como página (HTML): sin prisas
              "futbolme.com": float(os.environ.get("MIN_FUTBOLME", "10")),
              "betexplorer.com": float(os.environ.get("MIN_BETEXPLORER", "10"))}
AGENDA = os.path.join(BASE, "estado", "agenda.json")           # fechas de los partidos cercanos (la usa el modo rápido para saber si hay algo que vigilar)
RAPIDAS = {"calendario.py", "noticias.py", "resultados.py", "futbolme.py", "baloncesto.py", "besoccer.py", "directo.py", "alineacion.py"}     # fuentes del modo rápido: convocatorias y resultados
CLAVES_RAPIDAS = ("convocatoria-", "cronica-", "resultado-", "inicio-", "descanso-", "gol-", "alineacion-", "tarjeta-", "penalti-parado-")
HASHTAGS = "#RCCelta #Celta #MarexadaCeleste"

RECORDATORIOS = {
    0: ["Noticia do día (mañá, de rccelta.es)"],
    1: ["Noticia do día (mañá, de rccelta.es)", "Celta Fortuna / cantera (tarde, de rccelta.es)"],
    2: ["Noticia do día (mañá, de rccelta.es)"],                  # Tesouros Celestes (as 3 historias do mércores, 19:00) saen soas
    3: ["Noticia do día (mañá, de rccelta.es)"],
    4: ["Convocatoria (tarde, cando a publique o club)"],
    5: ["Aniversarios ou goleadores (mañá)", "Contido de peña: viaxe, merchandising, socios (tarde)"],
    6: ["Entradas / abonos ou peña (mañá)", "Resumo da semana (tarde)"],
}


# ---------------------------------------------------------------- utilidades
def web_toca(rapido, ahora, ultima_iso, minutos):
    """True si toca consultar esa web. Completo: siempre. Rápido: solo si pasaron `minutos` desde la última consulta."""
    if not rapido or not ultima_iso:
        return True
    try:
        ultima = datetime.datetime.fromisoformat(ultima_iso)
    except ValueError:
        return True
    return (ahora - ultima) >= datetime.timedelta(minutes=minutos)


def cargar(ruta):
    try:
        return json.load(open(ruta, encoding="utf-8"))
    except (OSError, ValueError):
        return None


CREDITO_FOTOS = "📸 Fotos: Web oficial do RC Celta (@rccelta)"


def retocar_tras_generar(h):
    """v80: justo después de dibujar la imagen de una historia: si lleva caras de jugadores, el texto lleva el crédito de la web del club;
    y la mención a un jugador se coloca donde la imagen indica (si no indica nada, Instagram usa el sitio por defecto)."""
    import generar_historia as HIST
    if HIST.USO_FOTOS and CREDITO_FOTOS not in h["texto"]:
        h["texto"] += " " + CREDITO_FOTOS
    if h.get("etiquetas"):
        xy = HIST.ULTIMA_ETIQUETA
        h["etiquetas"] = [{"username": u, "x": xy[0], "y": xy[1]} if (xy and isinstance(u, str)) else u for u in h["etiquetas"]]


def fecha_de(d):
    try:
        return datetime.date.fromisoformat(d["_fecha"])
    except (KeyError, ValueError, TypeError):
        return None


# v62: fallos PASAJEROS de una web (502, 503, 504, tiempo agotado, «no responde»): no son un error del programa. Van aparte (LEVES),
# se muestran en el resumen pero no disparan por sí solos un mensaje de Telegram, y se reintentan solos en la siguiente ejecución.
TEMPORAL = re.compile(r"HTTP Error (?:408|429|5\d\d)|Bad Gateway|Service Unavailable|Gateway Time-?out|no responde|timed out|Temporary failure", re.I)
LEVES = []


def correr(script, args, etiqueta, avisos):
    try:
        r = subprocess.run([sys.executable, os.path.join(BASE, script), *args], capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired:
        avisos.append(f"{etiqueta}: tardó demasiado y se cortó")
        return False
    if r.returncode != 0:
        ultima = ((r.stderr or r.stdout).strip().splitlines() or ["sin detalle"])[-1]
        if re.search(r"HTTP Error 403|bloquea las peticiones", ultima):
            avisos.append(f"{etiqueta}: rccelta.es bloquea las peticiones (HTTP 403 Forbidden); no es un fallo pasajero")
        elif TEMPORAL.search(ultima):
            codigo = re.search(r"HTTP Error (\d{3})", ultima)
            LEVES.append(f"{etiqueta}: la web no respondía ({'HTTP ' + codigo.group(1) if codigo else 'sin respuesta'}); se reintenta sola en la próxima ejecución")
        else:
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
    nuevas = {(p["equipo"], p["fecha"]): p.get("hora") for p in viejas if p.get("fecha") and (hoy - datetime.date.fromisoformat(p["fecha"])).days <= 3}
    for nombre in ("celta", "fortuna", "as_celtas_fem", "baloncesto_fem"):
        for pref in ("proximo", "resultado"):
            d = datos.get(f"{pref}_{nombre}.json")
            f = fecha_de(d)
            if f:
                h = re.search(r"(\d{1,2}:\d{2})", (d or {}).get("fecha_hora") or "") if pref == "proximo" else None
                clave = (nombre, f.isoformat())
                nuevas[clave] = h.group(1) if h else nuevas.get(clave)          # v50: se recuerda la hora de inicio para no dar «final» antes de tiempo
    os.makedirs(os.path.dirname(AGENDA), exist_ok=True)
    json.dump({"actualizada": hoy.isoformat(), "partidos": [{"equipo": e, "fecha": f, "hora": h} for (e, f), h in sorted(nuevas.items())]},
              open(AGENDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def partido_acabado(nombre, f):
    """v50: ¿puede haber terminado ya el partido? Si es de hoy y conocemos la hora de inicio, no se da por terminado hasta 115 min después
    (así un marcador en directo, p. ej. 0-0 al empezar, nunca sale como «RESULTADO FINAL»). Sin hora conocida, se asume que sí."""
    ahora = datetime.datetime.now(MADRID)
    if f != ahora.date():
        return True
    for p in (cargar(AGENDA) or {}).get("partidos", []):
        if p.get("equipo") == nombre.replace("-", "_") and p.get("fecha") == f.isoformat() and p.get("hora"):
            hh, mm = (int(x) for x in p["hora"].split(":"))
            return ahora >= ahora.replace(hour=hh, minute=mm, second=0, microsecond=0) + datetime.timedelta(minutes=115)
    return True


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
    if nombre == "baloncesto-fem":
        return "#CeltaBaloncesto #CeltaFemxaZorka #MarexadaCeleste"
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


def crear_historia(datos, hoy, d_datos, avisos, offline=False, rapido=False):
    """v63: «ESTA SEMANA NA HISTORIA CELESTE». Los miércoles: portada + una historia por cada partido histórico del Celta que cumple años esta
    semana (lo busca solo historia.py en ESPN, más las de efemerides.json marcadas como revisadas). El resto de días, y solo en las ejecuciones
    completas, va descargando y guardando en caché las temporadas pasadas para que el miércoles ya esté todo listo."""
    if rapido:
        return
    import almanaque                                               # v67: las historias de los miércoles vienen del Excel (assets/almanaque.json)
    try:
        todas = almanaque.cargar()
    except Exception as e:
        todas = []
        avisos.append(f"Tesouros Celestes: no se pudo leer assets/almanaque.json ({e})")
    if hoy.weekday() == 2:
        e = almanaque.entrada(hoy, todas)
        if e:
            for h in almanaque.historias(e):
                nombre_f = f"almanaque_{h['pantalla']}.json"
                with open(os.path.join(d_datos, nombre_f), "w", encoding="utf-8") as fh:
                    json.dump(h, fh, ensure_ascii=False, indent=1)
                datos[nombre_f] = h
            return
    else:
        proximo = hoy + datetime.timedelta(days=(2 - hoy.weekday()) % 7)
        if almanaque.entrada(proximo, todas):
            return                                                 # el próximo miércoles ya está en el almanaque: no hace falta calentar la caché de ESPN
    import historia
    desde = os.path.join(BASE, "fixtures", "espn_historia_EJEMPLO.json") if offline else None
    if hoy.weekday() != 2:
        if not offline:
            try:
                historia.partidos(hoy, None, [])
            except Exception as e:
                print(f"aviso: historia (calentar caché): {e}", file=sys.stderr)
        return
    try:
        ps, cov = historia.elegir(hoy, desde, avisos)
    except Exception as e:
        avisos.append(f"Historia: {e}")
        return
    if not ps:
        return
    for nombre_f, d in [("historia_portada_hoy.json", cov)] + [(f"historia_partido_{i}.json", x) for i, x in enumerate(ps, 1)]:
        with open(os.path.join(d_datos, nombre_f), "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
        datos[nombre_f] = d


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

    for nombre, fichero in (("celta", "proximo_celta.json"), ("fortuna", "proximo_fortuna.json"), ("as-celtas-fem", "proximo_as_celtas_fem.json"), ("baloncesto-fem", "proximo_baloncesto_fem.json")):
        d = datos.get(fichero)
        f = fecha_de(d)
        if not d or not f or not (0 <= (f - hoy).days <= 1):
            continue
        if nombre == "celta" and previa and f == hoy:
            continue                                   # el día del partido en casa ya sale la previa
        cuando = "Hoxe" if f == hoy else "Mañá"
        clave_prox = f"proximo-{nombre}-{d['fecha_hora']}"
        if f == hoy:
            # v55: el aviso del día del partido es una publicación propia (antes compartía clave con el de «Mañá» y, si ya había salido el día anterior, hoy no salía nada)
            clave_prox = f"proximo-{nombre}-hoxe-{d['fecha_hora']}"
            hh = re.search(r"(\d{1,2}):(\d{2})", d["fecha_hora"] or "")
            ahora_m = datetime.datetime.now(MADRID)
            if hh and ahora_m.date() == hoy and ahora_m >= ahora_m.replace(hour=int(hh.group(1)), minute=int(hh.group(2)), second=0, microsecond=0):
                continue                               # el partido ya ha empezado: ya no tiene sentido «Hoxe xogamos»
        add(clave_prox, fichero, "mañana", "10:00",
            f"{cuando} xogamos! {nombre_lado(d, 'local')} - {nombre_lado(d, 'visitante')}, {d['fecha_hora']}. Forza! 💙 {etiquetas(nombre)}")

    pr = datos.get("pronostico_celta.json")                       # viernes: pronóstico da peña (el resultado lo pone la gente con la enquisa)
    if pr and pr.get("_fecha"):
        loc, vis = nombre_lado(pr, "local"), nombre_lado(pr, "visitante")
        add(f"pronostico-{pr['_fecha']}", "pronostico_celta.json", "mañana", "10:00",
            f"🔮 PRONÓSTICO DA PEÑA: {loc} - {vis} ({pr['fecha_hora']}). Cal será o resultado? Vota na enquisa (pegatina de ligazón no oco de abaixo): "
            f"1 ({loc}) · X (empate) · 2 ({vis}) 💙 {etiquetas('celta')}")

    for i in (1, 2, 3):                                           # v67: miércoles, Almanaque Celta: gancho, datos y cierre (a las 19:00, 19:02 y 19:04)
        ah = datos.get(f"almanaque_{i}.json")
        if not ah:
            break
        add(f"almanaque-{ah['_fecha']}-{i}", f"almanaque_{i}.json", "tarde", f"19:{(i - 1) * 2:02d}",
            f"TESOUROS CELESTES ({i}/3): {ah['titular']} 💙 {HASHTAGS}")

    cov = datos.get("historia_portada_hoy.json")                  # v63: miércoles, «Esta semana na historia celeste»: portada y después un partido por historia
    if cov:
        add(f"historia-portada-{hoy.isoformat()}", "historia_portada_hoy.json", "tarde", "19:00",
            f"ESTA SEMANA NA HISTORIA CELESTE: {cov['tema'].capitalize()}. Desliza para ver os partidos 💙 {HASHTAGS}")
        for i in range(1, 6):
            hp = datos.get(f"historia_partido_{i}.json")
            if not hp:
                break
            nl, nv = nombre_lado(hp, "local"), nombre_lado(hp, "visitante")
            n = hp["titulo"].split()[1]
            add(f"historia-{hp['_fecha']}-{re.sub(r'[^a-z0-9]+', '-', (nl + '-' + nv).lower()).strip('-')}", f"historia_partido_{i}.json", "tarde", f"19:{i * 2:02d}",
                f"Hai {n} {'ano' if hp['titulo'].endswith('ANO') else 'anos'}: {nl} {hp['goles_local']} - {hp['goles_visitante']} {nv} ({hp.get('competicion_texto', '')}). 💙 {HASHTAGS}")

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

    for nombre, fichero in (("celta", "resultado_celta.json"), ("fortuna", "resultado_fortuna.json"), ("as-celtas-fem", "resultado_as_celtas_fem.json"), ("baloncesto-fem", "resultado_baloncesto_fem.json")):
        r = datos.get(fichero)
        f = fecha_de(r)
        if not r or not f or not (0 <= (hoy - f).days <= 1) or nombre in con_cronica:
            continue
        if nombre in ("as-celtas-fem", "baloncesto-fem") and not partido_acabado(nombre, f):
            continue                                   # marcador en directo, todavía no es el final                                   # si ya hay crónica (con goleadores) no se saca la del marcador
        cierre = {"as-celtas-fem": "Orgullosas do AS Celtas!", "baloncesto-fem": "Forza Celta Femxa Zorka! 🏀"}.get(nombre, "Forza Celta!")
        con_gol = bool(r.get("goleadores_local") or r.get("goleadores_visitante"))     # v42: si más tarde aparecen los goleadores, sale otra historia (clave distinta) para sustituir la primera
        aviso_gol = " (Versión con goleadores: se xa subiches a do marcador, substitúea.)" if con_gol else ""
        add(f"resultado-{nombre}-{r['fecha_hora']}-{r['goles_local']}-{r['goles_visitante']}" + ("-g" if con_gol else ""), fichero, "resultado", "xusto ao rematar o partido",
            f"Final: {nombre_lado(r, 'local')} {r['goles_local']} - {r['goles_visitante']} {nombre_lado(r, 'visitante')}. {cierre} 💙 {etiquetas(nombre)}{aviso_gol}")

    for eq_al, quien_al in (("celta", "Celta"), ("fortuna", "Celta Fortuna")):        # v85/v86: once antes del partido (ESPN), por posiciones y con caras
        al = datos.get(f"alineacion_{eq_al}.json")
        if al and al.get("grupos") and al.get("_fecha") == hoy.isoformat():
            add(f"alineacion-{eq_al}-{al['_fecha']}-{al['_id']}", f"alineacion_{eq_al}.json", "resultado", "xusto agora (antes do partido)",
                f"Aliñación! 📋 O once do {quien_al} para o partido: {nombre_lado(al, 'local')} - {nombre_lado(al, 'visitante')}. Forza {quien_al}! 💙 {HASHTAGS}")
    for nombre, quien in (("celta", "Celta"), ("fortuna", "Celta Fortuna")):          # v53: directo del Celta y del Celta Fortuna: inicio y descanso
        dv = datos.get(f"directo_{nombre}_inicio.json")
        if dv:
            add(f"inicio-{nombre}-{dv['_fecha']}-{dv['_id']}", f"directo_{nombre}_inicio.json", "resultado", "xusto ao comezar o partido",
                f"Comeza o partido! {nombre_lado(dv, 'local')} - {nombre_lado(dv, 'visitante')}. Forza {quien}! 💙 {HASHTAGS}")
        dd = datos.get(f"directo_{nombre}_descanso.json")
        if dd:
            add(f"descanso-{nombre}-{dd['_fecha']}-{dd['_id']}", f"directo_{nombre}_descanso.json", "resultado", "no descanso",
                f"Descanso! {nombre_lado(dd, 'local')} {dd['goles_local']} - {dd['goles_visitante']} {nombre_lado(dd, 'visitante')}. Forza {quien}! 💙 {HASHTAGS}")
    for eq, equipo_txt in (("celta", "Celta"), ("fortuna", "Celta Fortuna")):        # v86: goles, expulsiones y penaltis parados en directo, del Celta y del Celta Fortuna
        tags = HASHTAGS if eq == "celta" else etiquetas(eq)
        for fichero in sorted(f for f in datos if re.fullmatch(rf"directo_{eq}_gol_\d+\.json", f)):         # un «GOOOOOOL!» por cada gol del equipo (los del rival no se publican)
            g = datos[fichero]
            if not g or not g.get("goleador"):
                continue
            quien = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", g["goleador"]).encode("ascii", "ignore").decode().lower()).strip("-")
            extra = {"penalti": " (de penalti)", "propia": " (en propia porta)"}.get(g.get("modo"), "")
            add(f"gol-{eq}-{g['_fecha']}-{g['_id']}-{g['_n']}-{g['goles_local']}-{g['goles_visitante']}-{quien}", fichero, "resultado", "xusto agora (en directo)",
                f"GOOOOOOL! ⚽ {g['goleador']}{extra} ({g['minuto']}). {nombre_lado(g, 'local')} {g['goles_local']} - {g['goles_visitante']} {nombre_lado(g, 'visitante')}. Forza {equipo_txt}! 💙 {tags}")
        # v84: expulsiones (roja directa / doble amarilla, de cualquier equipo) y penaltis que para el equipo, en directo
        for fichero in sorted(f for f in datos if re.fullmatch(rf"directo_{eq}_tarjeta_\d+\.json", f)):
            t = datos[fichero]
            if not t or not t.get("goleador"):
                continue
            quien = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", t["goleador"]).encode("ascii", "ignore").decode().lower()).strip("-")
            marcador = f"{nombre_lado(t, 'local')} {t['goles_local']} - {t['goles_visitante']} {nombre_lado(t, 'visitante')}"
            donde = f" ({t['equipo']})" if t.get("equipo") else ""
            if t.get("clase") == "doble":
                texto = f"🟨🟥 Dobre amarela e expulsión de {t['goleador']}{donde} no minuto {t['minuto'].rstrip(chr(39))}. {marcador}. {tags}"
            else:
                texto = f"🟥 Tarxeta vermella directa para {t['goleador']}{donde} no minuto {t['minuto'].rstrip(chr(39))}. {marcador}. {tags}"
            add(f"tarjeta-{eq}-{t['_fecha']}-{t['_id']}-{quien}-{t.get('clase', 'roja')}", fichero, "resultado", "xusto agora (en directo)", texto)
        for fichero in sorted(f for f in datos if re.fullmatch(rf"directo_{eq}_penalti_\d+\.json", f)):
            t = datos[fichero]
            if not t or not t.get("minuto"):
                continue
            marcador = f"{nombre_lado(t, 'local')} {t['goles_local']} - {t['goles_visitante']} {nombre_lado(t, 'visitante')}"
            quien_para = f"{t['portero']} detén" if t.get("portero") else f"O {equipo_txt} detén"
            de_quen = f" o penalti de {t['lanzador']} ({t['rival']})" if t.get("lanzador") else " un penalti"
            add(f"penalti-parado-{eq}-{t['_fecha']}-{t['_id']}-{re.sub(r'[^0-9]+', '', t['minuto'])}", fichero, "resultado", "xusto agora (en directo)",
                f"🧤 PENALTI PARADO! {quien_para}{de_quen} no minuto {t['minuto'].rstrip(chr(39))}. {marcador}. Forza {equipo_txt}! 💙 {tags}")

    tabla = {0: ("clasificacion_celta_laliga.json", "laliga", "LaLiga"), 1: ("clasificacion_celta_fortuna.json", "fortuna", "LaLiga Hypermotion (Celta Fortuna)"),
             3: ("clasificacion_as_celtas_fem.json", "as-celtas-fem", "Segunda Federación Femenina (AS Celtas)")}.get(wd)
    if tabla:
        d = datos.get(tabla[0])
        if d:
            add(f"clasificacion-{tabla[1]}-{d['jornada']}", tabla[0], "tarde", "19:00",
                f"Así está a clasificación de {tabla[2]} tras a {d['jornada'].lower()}. 💙 {etiquetas(tabla[1])}")
    # v87: clasificación de la Liga Femenina Endesa (Celta Femxa Zorka), de la web de la Federación: los LUNES a las 13:00 (hora que no usa ninguna otra historia),
    # cuando ya ha terminado la jornada del fin de semana. Una sola vez por jornada (la clave lleva la jornada).
    cb = datos.get("clasificacion_baloncesto_fem.json")
    fecha_cb = fecha_de(cb) if cb else None
    if cb and fecha_cb and wd == 0 and 0 <= (hoy - fecha_cb).days <= 6 and cb.get("filas"):
        mio = next((f for f in cb["filas"] if f.get("nombre") == cb.get("destacado")), None)
        donde = f" O Celta Femxa Zorka é {mio['pos']}º con {mio['pts']} puntos." if mio else ""
        add(f"clasificacion-baloncesto-fem-{cb['jornada']}", "clasificacion_baloncesto_fem.json", "mañana", "13:00",
            f"Así está a clasificación da Liga Femenina Endesa tras a {cb['jornada'].lower()}.{donde} 🏀 💙 {etiquetas('baloncesto-fem')}")
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
        mencion = f" @{c['instagram'].lstrip('@')}" if c.get("instagram") else ""                  # v76: se menciona al jugador en el texto
        quien = f"o noso adestrador {c['nombre']}" if "adestrador" in (c.get("posicion") or "").lower() else c["nombre"]
        add(f"cumple-{fichero[10:-5]}-{c.get('año', hoy.year)}", fichero, "mañana", "09:00",
            f"🎂 O {c['fecha']} cumpre {c['edad']} anos {quien}! Moitas felicidades e que cumpra moitos máis co celeste no peito 💙{mencion} {etiquetas(c.get('equipo', 'celta'))}"
            + (" 📸 Fotos: Web oficial do RC Celta (@rccelta)" if c.get("foto") else ""))      # v72: crédito obligatorio cuando se usa la foto del club
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
def ventana_instagram(h, t=None):
    """(desde, hasta) para publicar la historia en Instagram: la hora sugerida si es una hora concreta (10:00, 19:00...), si no, ya;
    y hasta cuándo sigue valiendo (en directo, poco; resultados y convocatorias, unas horas; el resto, hasta final del día)."""
    t = t or datetime.datetime.now(MADRID)
    desde = t
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", h.get("hora") or "")
    if m:
        previsto = t.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        desde = max(t, previsto)
    c = h["clave"]
    if c.startswith(("gol-", "inicio-", "descanso-", "tarjeta-", "penalti-parado-")):
        hasta = desde + datetime.timedelta(minutes=45)
    elif c.startswith("alineacion-"):
        hasta = desde + datetime.timedelta(minutes=90)             # v85: la alineación solo vale justo antes del partido
    elif c.startswith(("resultado-", "cronica-")):
        hasta = desde + datetime.timedelta(hours=8)
    elif c.startswith("convocatoria-"):
        hasta = desde + datetime.timedelta(hours=10)
    else:
        hasta = t.replace(hour=23, minute=59, second=0, microsecond=0)
    return desde, max(hasta, desde + datetime.timedelta(minutes=30))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hoy", default=None, help="AAAA-MM-DD (por defecto, hoy en Madrid)")
    ap.add_argument("--offline", action="store_true", help="usa los datos de ejemplo de fixtures/ en vez de internet")
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--sin-estado", action="store_true")
    ap.add_argument("--sin-telegram", action="store_true")
    ap.add_argument("--sin-instagram", action="store_true", help="no sube las imágenes ni las apunta para publicar en Instagram")
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
            ("clasificacion_baloncesto.py", ["--desde", fx("feb_clasificacion_RECONSTRUIDO.html"), "--salida", d_datos], "Clasificación LF Endesa (Federación)"),
            ("baloncesto.py", ["--feb", fx("feb_resultados_RECONSTRUIDO.html"), "--calendario", fx("betexplorer_baloncesto_calendario_RECONSTRUIDO.html"), "--resultados", fx("betexplorer_baloncesto_resultados_RECONSTRUIDO.html"), "--hoy", hoy.isoformat(), "--salida", d_datos], "Celta Femxa Zorka (prueba)"),
        ]
    else:
        ahora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        fuentes = [
            ("calendario.py", ["--ahora", ahora, "--salida", d_datos], "Calendario"),
            ("clasificaciones.py", ["--salida", d_datos], "Clasificaciones"),
            ("noticias.py", ["--salida", d_datos], "Noticias rccelta.es"),
            ("resultados.py", ["--ahora", ahora, "--salida", d_datos], "Resultados Celta/Fortuna"),
            ("directo.py", ["--salida", d_datos], "Celta y Celta Fortuna en directo"),
            ("alineacion.py", ["--ahora", ahora, "--salida", d_datos], "Alineación del Celta (ESPN)"),     # v85
            ("futbolme.py", ["--hoy", hoy.isoformat(), "--salida", d_datos], "AS Celtas Fem (futbolme)"),
            ("baloncesto.py", ["--hoy", hoy.isoformat(), "--salida", d_datos], "Celta Femxa Zorka (BetExplorer)"),        # v87
            ("clasificacion_baloncesto.py", ["--salida", d_datos], "Clasificación LF Endesa (Federación)"),               # v87
            ("partemedico.py", ["--hoy", hoy.isoformat(), "--salida", d_datos], "Parte médico (rccelta.es)"),
            ("entradas.py", ["--hoy", hoy.isoformat(), "--salida", d_datos], "Entradas (rccelta.es)"),
            ("cumpleanos.py", ["--hoy", hoy.isoformat(), "--salida", d_datos], "Cumpleaños"),
        ]
    if rapido:
        fuentes = [f for f in fuentes if f[0] in RAPIDAS]
    ahora_utc = datetime.datetime.now(datetime.timezone.utc)
    control = {} if (a.offline or a.sin_estado) else (cargar(CONSULTAS_WEB) or {})
    if rapido and not a.offline:
        quedan = []
        for f in fuentes:
            host = FUENTE_HOST.get(f[0])
            if host and not web_toca(True, ahora_utc, control.get(host), MIN_RAPIDO[host]):
                print(f"{f[0]}: {host} consultada hace poco (mínimo {MIN_RAPIDO[host]:g} min en modo rápido); se salta.")
                continue
            quedan.append(f)
        fuentes = quedan
    ok = [correr(s, args, etq, avisos) for s, args, etq in fuentes]
    if not a.offline and not a.sin_estado:
        usados = {FUENTE_HOST[f[0]] for f in fuentes if f[0] in FUENTE_HOST}
        if usados:                                                  # se anota aunque falle (403, 502): así no se insiste antes de tiempo
            for h in usados:
                control[h] = ahora_utc.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            os.makedirs(os.path.dirname(CONSULTAS_WEB), exist_ok=True)
            json.dump(control, open(CONSULTAS_WEB, "w", encoding="utf-8"))

    datos = {f: cargar(os.path.join(d_datos, f)) for f in os.listdir(d_datos) if f.endswith(".json")}
    crear_pronostico(datos, hoy, d_datos)
    crear_historia(datos, hoy, d_datos, avisos, offline=a.offline, rapido=rapido)
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
            retocar_tras_generar(h)
        except Exception as e:
            avisos.append(f"No se pudo generar {h['clave']}: {e}")
            h["imagen"] = None
    historias = [h for h in historias if h["imagen"]]
    if not a.offline and not a.sin_instagram:                          # v57: las historias nuevas se suben y se apuntan para publicarlas en Instagram (lo hace instagram.py)
        import instagram
        if instagram.activo():
            for h in historias:
                if h["clave"].startswith("pronostico-"):                  # v85: el pronóstico lleva la pegatina de la encuesta, que pones tú a mano: solo va a Telegram
                    continue
                try:
                    instagram.encolar(h["clave"], h["imagen"], h["texto"], *ventana_instagram(h))        # v86: sin etiquetas a jugadores
                except Exception as e:
                    avisos.append(f"Instagram (preparar {h['clave']}): {e}")

    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    L = [f"# Historias de {dias[hoy.weekday()]} {hoy.strftime('%d/%m/%Y')}", ""]
    if historias:
        L += ["| Hora sugerida | Imagen | Texto sugerido |", "|---|---|---|"]
        L += [f"| {h['hora']} | {os.path.basename(h['imagen'])} | {h['texto']} |" for h in historias]
    else:
        L.append("Hoy no hay historias automáticas nuevas.")
    L += ["", "## Contido propio que toca hoxe (aínda sen automatizar)"] + [f"- {r}" for r in RECORDATORIOS[hoy.weekday()]]
    L += ["- Aliñación do Celta e do Celta Fortuna: saen soas (ESPN) cando se coñece o once."]
    L_tg = list(L)                                             # lo que llega a Telegram: sin el control de actualidad (ocupa mucho; sigue en resumen.md)
    if controles:
        L += ["", "## Control de actualidad"] + [f"- {x}" for x in controles]
    if avisos:
        L += ["", "## Avisos"] + [f"- {x}" for x in avisos]
        L_tg += ["", "## Avisos"] + [f"- {x}" for x in avisos]
    if LEVES:
        L += ["", "## Fallos pasajeros de la web (no hay que hacer nada)"] + [f"- {x}" for x in LEVES]
        L_tg += ["", "## Fallos pasajeros de la web (no hay que hacer nada)"] + [f"- {x}" for x in LEVES]
    resumen = "\n".join(L) + "\n"
    resumen_tg = "\n".join(L_tg) + "\n"
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
        enviado = telegram(historias, resumen_tg, avisos, rapido)
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
