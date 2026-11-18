"""Marexada Celeste · «ESTA SEMANA NA HISTORIA CELESTE» (v63): los miércoles, partidos históricos del Celta que cumplen años esa semana.

Todo automático: busca en ESPN (la misma fuente que el resto del programa) los partidos de Copa del Rey, Europa (UEFA/Champions) y LaLiga de
temporadas pasadas, se queda con los del Celta que cumplen años esta semana (de 3 días antes a 3 días después), elige los más interesantes
(victorias del Celta, y empates en Europa; pesan más Europa y Copa, las goleadas y los rivales grandes) y deja los datos para la portada + una historia por partido.
Además entran siempre, y primero, las de efemerides.json marcadas "revisada": true (las que se han comprobado a mano).

Seguridad: solo victorias del Celta (y empates en competición europea) con marcador completo; los goleadores solo salen si cuadran con el marcador y no hay goles en propia puerta
(para no atribuirlos mal); si ESPN no responde no se inventa nada: ese miércoles sale solo lo que haya.
Caché: estado/historia_cache.json (las temporadas pasadas no cambian; se descargan una vez y se reutilizan; con límite de tiempo por ejecución).
"""
import datetime
import json
import os
import re
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import resultados as R                       # reutiliza el lector de ESPN (de_espn, get, completar_goles...)
from calendario import MADRID, escudo, nombre

CACHE = os.path.join(BASE, "estado", "historia_cache.json")
PRIMERA_TEMPORADA = 2003                      # ESPN guarda partidos desde esta temporada (si una no existe se ignora)
PENDIENTES = 0                                # temporadas aún sin descargar en esta ejecución
PRESUPUESTO_S = 120                           # tiempo máximo descargando por ejecución (el resto, en la siguiente)
VENTANA_DIAS = 3
SERIE = "ESTA SEMANA NA HISTORIA CELESTE"
# (liga en ESPN, logo del diseño, texto de la competición, peso)
LIGAS = (("esp.copa_del_rey", "copa", "Copa do Rei", 4), ("uefa.europa", "europa", "UEFA Europa League", 5),
         ("uefa.champions", None, "UEFA Champions League", 5), ("esp.1", "laliga", "LaLiga", 1))
GRANDES = ("real madrid", "barcelona", "atletico", "atlético", "sevilla", "deportivo", "valencia", "athletic",
           "liverpool", "manchester", "arsenal", "chelsea", "tottenham", "juventus", "milan", "inter", "roma", "benfica", "porto", "ajax",
           "lyon", "marseille", "olympique", "bayern", "dortmund", "leverkusen", "psv", "sporting")
DIAS = ["Luns", "Martes", "Mércores", "Xoves", "Venres", "Sábado", "Domingo"]
MESES = ["xaneiro", "febreiro", "marzo", "abril", "maio", "xuño", "xullo", "agosto", "setembro", "outubro", "novembro", "decembro"]


def temporada_actual(hoy):
    return hoy.year if hoy.month >= 7 else hoy.year - 1


def _a_json(p):
    return {**p, "f": p["f"].isoformat()}


def _de_json(p):
    return {**p, "f": datetime.datetime.fromisoformat(p["f"])}


def _cargar_cache():
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _guardar_cache(c):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(c, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)


def _es_del_celta(p):
    return R.es_celta(p["home"] + p["away"]) and not R.es_fortuna(p["home"]) and not R.es_fortuna(p["away"])


def partidos(hoy, desde=None, avisos=None):
    """Todos los partidos del Celta de temporadas pasadas que se conocen: [(partido, texto_competicion, logo, peso)]."""
    global PENDIENTES
    PENDIENTES = 0
    out = []
    if desde:                                                       # prueba sin internet: {"esp.copa_del_rey": {"2016": {"events": [...]}}, ...}
        j = json.load(open(desde, encoding="utf-8"))
        for liga, logo, txt, peso in LIGAS:
            for _, resp in (j.get(liga) or {}).items():
                for e in resp.get("events", []):
                    p = R.de_espn(e, "x")
                    if p and _es_del_celta(p):
                        out.append((dict(p, liga=liga), txt, logo, peso))
        return out
    cache = _cargar_cache()
    t0, cambios, pendientes = time.time(), False, 0
    for temp in range(PRIMERA_TEMPORADA, temporada_actual(hoy)):
        for liga, logo, txt, peso in LIGAS:
            clave = f"{liga}|{temp}"
            c = cache.get(clave)
            if c and (c["ok"] or (hoy - datetime.date.fromisoformat(c["t"])).days < 2):
                ps = c["p"]
            elif time.time() - t0 > PRESUPUESTO_S:
                pendientes += 1
                continue
            else:
                try:
                    evs = R.get(R.ESPN.format(liga) + f"teams/{R.CELTA_ESPN}/schedule?season={temp}").get("events") or []
                    ps = [_a_json(dict(p, liga=liga)) for p in (R.de_espn(e, "x") for e in evs) if p and _es_del_celta(p)]
                    cache[clave] = {"ok": True, "t": hoy.isoformat(), "p": ps}
                except Exception as e:
                    ps = []
                    cache[clave] = {"ok": False, "t": hoy.isoformat(), "p": []}
                    print(f"aviso: historia: ESPN {liga} {temp}: {str(e)[:80]}", file=sys.stderr)
                cambios = True
            out += [(_de_json(p), txt, logo, peso) for p in ps]
    PENDIENTES = pendientes
    if cambios:
        _guardar_cache(cache)
    if pendientes and avisos is not None:
        avisos.append(f"Historia: faltan {pendientes} temporadas por descargar; se completan en las próximas ejecuciones")
    return out


def _puntos(p, peso, europa=False):
    celta_local = R.es_celta(p["home"])
    gc, gr = (p["gl"], p["gv"]) if celta_local else (p["gv"], p["gl"])
    if gc < gr or (gc == gr and not europa):
        return None                                                 # victorias; y empates solo si fueron en competición europea
    rival = p["away"] if celta_local else p["home"]
    pts = peso + (3 if gc - gr >= 3 else 2 if gc - gr == 2 else 0) - (1 if gc == gr else 0)
    if any(g in rival.lower() for g in GRANDES):
        pts += 3
    return pts


def _frase(p, gc, gr):
    return "Goleada celeste" if gc - gr >= 3 else ""


def _goles_fiables(p):
    """Completa los goleadores y los da por buenos solo si cuadran con el marcador y no hay goles en propia puerta."""
    try:
        R.completar_goles(p)
    except Exception:
        pass
    gl, gv = p.get("gol_l") or [], p.get("gol_v") or []
    if len(gl) != p["gl"] or len(gv) != p["gv"] or any("(p.p.)" in x for x in gl + gv):
        return [], []
    return gl, gv


def datos_partido(p, txt, logo, hoy, offline=False):
    f = p["f"].astimezone(MADRID)
    celta_local = R.es_celta(p["home"])
    gc, gr = (p["gl"], p["gv"]) if celta_local else (p["gv"], p["gl"])
    gl, gv = ([], []) if offline else _goles_fiables(p)
    n = hoy.year - f.year
    return {"tipo": "efemeride", "logo": logo, "serie": SERIE, "titulo": f"HAI {n} {'ANO' if n == 1 else 'ANOS'}",
            "fecha_texto": f"{DIAS[f.weekday()]} {f.day} de {MESES[f.month - 1]} de {f.year}", "competicion_texto": txt,
            "local": escudo(p["home"]), "visitante": escudo(p["away"]), "local_nombre": nombre(p["home"]), "visitante_nombre": nombre(p["away"]),
            "goles_local": p["gl"], "goles_visitante": p["gv"], "frase": _frase(p, gc, gr),
            "goleadores_local": gl, "goleadores_visitante": gv, "_fecha": f.date().isoformat(), "_gc": gc, "_gr": gr}


def manuales(hoy):
    """Las de efemerides.json marcadas como revisadas que cumplen años esta semana."""
    try:
        lista = json.load(open(os.path.join(BASE, "efemerides.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for e in lista:
        if not e.get("fecha") or not e.get("revisada"):
            continue
        f = datetime.date.fromisoformat(e["fecha"])
        if f.year >= hoy.year or not _cerca(f, hoy):
            continue
        n = hoy.year - f.year
        d = {k: v for k, v in e.items() if k not in ("revisada", "fuentes", "_leeme", "fecha")}
        d.update({"tipo": "efemeride", "serie": SERIE, "titulo": f"HAI {n} {'ANO' if n == 1 else 'ANOS'}",
                  "fecha_texto": f"{DIAS[f.weekday()]} {f.day} de {MESES[f.month - 1]} de {f.year}", "_fecha": f.isoformat()})
        out.append(d)
    return out


def _cerca(f, hoy):
    try:
        este = f.replace(year=hoy.year)
    except ValueError:
        este = f.replace(year=hoy.year, day=28)
    return abs((este - hoy).days) <= VENTANA_DIAS


def elegir(hoy, desde=None, avisos=None, maximo=3):
    """Devuelve (lista de datos de partido, datos de la portada) o ([], None)."""
    elegidos = manuales(hoy)
    fechas = {d["_fecha"] for d in elegidos}
    cand = []
    try:
        todos = partidos(hoy, desde, avisos)
        if PENDIENTES:                                              # historial a medio descargar: mejor esperar a la siguiente ejecución que publicar a medias
            return [], None
        for p, txt, logo, peso in todos:
            f = p["f"].astimezone(MADRID).date()
            if f.year >= hoy.year or not _cerca(f, hoy) or f.isoformat() in fechas:
                continue
            pts = _puntos(p, peso, europa=(logo in ("europa", None)))
            if pts is not None:
                cand.append((pts, f, p, txt, logo))
    except Exception as e:
        if avisos is not None:
            avisos.append(f"Historia: no se pudieron leer los partidos históricos ({str(e)[:100]})")
    cand.sort(key=lambda c: (-c[0], -c[1].toordinal()))
    vistos = set()
    for pts, f, p, txt, logo in cand:
        if len(elegidos) >= maximo:
            break
        if f in vistos:
            continue
        vistos.add(f)
        elegidos.append(datos_partido(p, txt, logo, hoy, offline=bool(desde)))
    elegidos = sorted(elegidos[:maximo], key=lambda d: d["_fecha"])
    if not elegidos:
        return [], None
    return elegidos, portada(elegidos)


def portada(partidos_):
    logos = {d.get("logo") for d in partidos_}
    if logos <= {"europa", None}:
        tema = "NOITES EUROPEAS"
    elif logos <= {"copa"}:
        tema = "NOITES DE COPA"
    elif logos <= {"copa", "europa", None}:
        tema = "NOITES DE COPA E EUROPA"
    else:
        tema = "GRANDES NOITES CELESTES"
    top = partidos_[0]
    return {"tipo": "historia_portada", "competicion": "liga", "serie": SERIE, "titulo_serie": ["ESTA SEMANA", "NA HISTORIA", "CELESTE"], "tema": tema,
            "local": top["local"], "visitante": top["visitante"], "local_nombre": top["local_nombre"], "visitante_nombre": top["visitante_nombre"],
            "fechas": [[int(d["_fecha"][:4]), f"{d['goles_local']}-{d['goles_visitante']}"] for d in partidos_],
            "pie": "DESLIZA PARA VER OS PARTIDOS"}
