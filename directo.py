"""Marexada Celeste · EN DIRECTO (v56).

Mira si el Celta (primer equipo) o el Celta Fortuna están jugando ahora mismo (ESPN: LaLiga, Europa League, Copa del Rey e Hypermotion).
Escribe en datos_reales/ (o en la carpeta --salida):
  Celta y Celta Fortuna:
    directo_<equipo>_inicio.json     «COMIENZA EL PARTIDO» (primeros minutos, marcador 0-0)
    directo_<equipo>_descanso.json   «DESCANSO» con el marcador y los goleadores de la primera parte
  Solo el Celta (primer equipo):
    directo_celta_gol_NN.json        «¡GOOOOOOL!» por cada gol DEL CELTA: goleador, minuto y marcador en ese momento
                                     (NN = número de gol del partido). Los goles del rival no se publican.
  v84, solo el Celta (primer equipo):
    directo_celta_tarjeta_NN.json    «¡ROJA DIRECTA!» o «¡DOBLE AMARILLA!» (expulsión de un jugador del Celta o del rival)
    directo_celta_penalti_NN.json    «¡PENALTI PARADO!» cuando el Celta detiene un penalti del rival
El final lo saca resultados.py como siempre (también el del Fortuna).
Si el equipo no está jugando, no escribe nada. Nunca rompe el programa: si ESPN falla, simplemente no hay directo.
diario.py anota en estado/publicado.json lo ya publicado, así que repetir un gol en la siguiente revisión no lo duplica.

Uso:
    python directo.py                                          (lee internet)
    python directo.py --desde fixtures/espn_directo_EJEMPLO.json    (prueba sin internet)
"""
import argparse
import datetime
import json
import os
import re
import sys

import resultados as R
from calendario import MADRID

BASE = os.path.dirname(os.path.abspath(__file__))
EN_JUEGO = re.compile(r"IN_PROGRESS|FIRST_HALF|SECOND_HALF|HALFTIME|EXTRA_TIME|OVERTIME|SHOOTOUT|PENALT", re.I)
MAX_ANTIGUEDAD = 30        # un gol solo se publica si se marcó hace como mucho 30 min de juego (si el programa estuvo parado, no se sacan goles viejos)

# equipo -> (id en ESPN, [(liga ESPN, clave de competición)])
EQUIPOS = {"celta": (R.CELTA_ESPN, (("esp.1", "liga"), ("uefa.europa", "euro"), ("esp.copa_del_rey", "copa"))),
           "fortuna": (R.FORTUNA_ESPN, (("esp.2", "hm"),))}


def es_del_equipo(eq, p):
    """El partido es del Celta (primer equipo) o del Fortuna según el nombre de los dos clubes."""
    if eq == "fortuna":
        return R.es_fortuna(p["home"]) or R.es_fortuna(p["away"])
    return R.es_celta(p["home"] + p["away"]) and not R.es_fortuna(p["home"]) and not R.es_fortuna(p["away"])


def de_espn_directo(ev, k):
    """Partido en juego (no terminado) -> dict como el de resultados.de_espn, más minuto. None si no está en juego."""
    c = (ev.get("competitions") or [{}])[0]
    st = c.get("status") or ev.get("status") or {}
    tipo = st.get("type") or {}
    if tipo.get("completed") or not (tipo.get("state") == "in" or EN_JUEGO.search(tipo.get("name", ""))):
        return None
    h = a = None
    for t in c.get("competitors", []):
        if t.get("homeAway") == "home":
            h = t
        else:
            a = t
    if not h or not a:
        return None
    gl, gv = R.num(h.get("score")), R.num(a.get("score"))
    if gl is None or gv is None:
        return None
    nm = lambda t: (t.get("team") or {}).get("displayName") or (t.get("team") or {}).get("name") or ""
    try:
        f = datetime.datetime.fromisoformat((ev.get("date") or c.get("date")).replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    g1, g2 = R.goles_espn(c, h)
    minuto = st.get("displayClock") or tipo.get("shortDetail") or ""
    if re.search(r"HALFTIME", tipo.get("name", ""), re.I):
        minuto = "Descanso"
    return {"f": f, "k": k, "home": nm(h), "away": nm(a), "gl": gl, "gv": gv, "gol_l": g1, "gol_v": g2,
            "id": ev.get("id") or c.get("id"), "minuto": minuto, "estado": tipo.get("name", ""), "periodo": st.get("period"),
            "detalles": c.get("details") or [], "home_id": str((h.get("team") or {}).get("id", "")), "away_id": str((a.get("team") or {}).get("id", ""))}


def _ids(ev):
    return {str((t.get("team") or {}).get("id", "")) for t in ((ev.get("competitions") or [{}])[0].get("competitors") or [])}


def buscar_en_vivo(registro=None):
    """{'celta': [partidos en juego], 'fortuna': [...]} leyendo ESPN.
    v56: la lista normal de partidos del equipo (/schedule) SOLO trae los ya terminados, así que un partido en juego no salía.
    Se miran tres sitios: /schedule?fixture=true (próximos y en juego), el marcador de la liga (/scoreboard, con los partidos de hoy) y /schedule."""
    registro = registro if registro is not None else []
    out = {eq: [] for eq in EQUIPOS}
    for eq, (id_, ligas) in EQUIPOS.items():
        vistos = {}
        for liga, k in ligas:
            base = R.ESPN.format(liga)
            for etiqueta, url in (("fixture", base + f"teams/{id_}/schedule?fixture=true"), ("scoreboard", base + "scoreboard"), ("schedule", base + f"teams/{id_}/schedule")):
                try:
                    evs = R.get(url).get("events") or []
                except Exception as e:
                    registro.append(f"{eq} {liga} {etiqueta}: ERROR {type(e).__name__}: {e}")
                    print(f"aviso: ESPN {liga} {etiqueta} ({eq}): {e}", file=sys.stderr)
                    continue
                suyos = [e for e in evs if id_ in _ids(e)]
                estados = [((((e.get('competitions') or [{}])[0].get('status') or e.get('status') or {}).get('type') or {}).get('name') or '?') for e in suyos]
                registro.append(f"{eq} {liga} {etiqueta}: {len(evs)} eventos, {len(suyos)} del equipo; estados: {', '.join(sorted(set(estados))) or '-'}")
                for e in suyos:
                    p = de_espn_directo(e, k)
                    if p and es_del_equipo(eq, p):
                        p["liga"] = liga
                        previo = vistos.get(p["id"])
                        if not previo or (len(p["gol_l"]) + len(p["gol_v"]), len(p["detalles"])) > (len(previo["gol_l"]) + len(previo["gol_v"]), len(previo["detalles"])):
                            vistos[p["id"]] = p                 # si sale en varias fuentes, nos quedamos con la que trae más goles detallados
        out[eq] = list(vistos.values())
    return out


def desde_archivo(ruta):
    """Prueba sin internet: {"celta": {"liga": {"events": [...]}}, "fortuna": {"hm": {...}}} con el formato de ESPN."""
    j = json.load(open(ruta, encoding="utf-8"))
    out = {eq: [] for eq in EQUIPOS}
    for eq in EQUIPOS:
        for k, resp in (j.get(eq) or {}).items():
            out[eq] += [p for p in (de_espn_directo(e, k) for e in resp.get("events", [])) if p and es_del_equipo(eq, p)]
    return out


def datos(p, titulo, con_minuto=True, eq="celta"):
    f = p["f"].astimezone(MADRID)
    d = R.datos(p, eq)
    d.update(titulo=titulo, lugar=((f"Minuto {p['minuto']}" if p["minuto"] != "Descanso" else "Descanso") if con_minuto and p.get("minuto") else None),
             _id=str(p.get("id") or ""), _minuto=p.get("minuto") or "")
    return d


def minuto_num(txt):
    m = re.search(r"\d+", txt or "")
    return int(m.group()) if m else None


def al_descanso(p):
    """Marcador y goleadores al descanso a partir de los goles con minuto <= 45. None si la lista no cuadra con el marcador actual."""
    def hasta45(lista):
        return [g for g in lista if (minuto_num(g.split()[-1]) or 99) <= 45]
    if len(p["gol_l"]) + len(p["gol_v"]) != p["gl"] + p["gv"]:
        return None
    gl, gv = hasta45(p["gol_l"]), hasta45(p["gol_v"])
    return dict(p, gl=len(gl), gv=len(gv), gol_l=gl, gol_v=gv)


# ---------------------------------------------------------------- goles (v53, solo el Celta)
def orden_minuto(txt):
    """'Iago Aspas (p.) 45+2'' -> 45.02 (para ordenar los goles de los dos equipos); sin minuto -> 999."""
    m = re.search(r"(\d+)(?:\s*\+\s*(\d+))?'?\s*$", txt.strip())
    if not m:
        return 999.0
    return int(m.group(1)) + (int(m.group(2)) / 100 if m.group(2) else 0)


def corregir_propia_puerta(p):
    """Si el rival marca en propia puerta, ESPN puede apuntarlo en la lista equivocada. Si el total cuadra pero el reparto no,
    se pasan los «(p.p.)» sobrantes al otro lado. Devuelve True si al final las listas cuadran con el marcador."""
    gl, gv = list(p["gol_l"]), list(p["gol_v"])
    if len(gl) + len(gv) != p["gl"] + p["gv"]:
        return False
    for origen, destino, quiere in ((gl, gv, p["gl"]), (gv, gl, p["gv"])):
        while len(origen) > quiere:
            propios = [g for g in origen if "(p.p.)" in g]
            if not propios:
                return False
            origen.remove(propios[-1])
            destino.append(propios[-1])
    p["gol_l"], p["gol_v"] = gl, gv
    return (len(gl), len(gv)) == (p["gl"], p["gv"])


def partir_gol(txt):
    """'Iago Aspas (p.) 67'' -> ('Iago Aspas', "67'", 'penalti')"""
    m = re.match(r"^(.*?)\s*(\((?:p|p\.p)\.\))?\s*(\d+(?:\+\d+)?)'?\s*$", txt.strip())
    if not m:
        return txt.strip(), "", ""
    modo = {"(p.)": "penalti", "(p.p.)": "propia"}.get(m.group(2) or "", "")
    return m.group(1).strip(), m.group(3) + "'", modo


def goles_del_celta(p, actual):
    """Lista de goles DEL CELTA en orden, cada uno con el marcador en ese momento y los datos del goleador.
    Solo los recientes (<= MAX_ANTIGUEDAD min de juego respecto al minuto actual). Lista vacía si el detalle no cuadra con el marcador."""
    celta_local = R.es_celta(p["home"]) and not R.es_fortuna(p["home"])
    if (len(p["gol_l"]), len(p["gol_v"])) != (p["gl"], p["gv"]) and not corregir_propia_puerta(p):
        print("Goles: el detalle de goleadores todavía no cuadra con el marcador; se espera a la próxima revisión.", file=sys.stderr)
        return []
    eventos = sorted([(orden_minuto(g), "l", g) for g in p["gol_l"]] + [(orden_minuto(g), "v", g) for g in p["gol_v"]], key=lambda e: e[0])
    out, cl, cv = [], 0, 0
    for n, (orden, lado, texto) in enumerate(eventos, 1):
        cl, cv = cl + (lado == "l"), cv + (lado == "v")
        if (lado == "l") != celta_local:
            continue                                               # gol del rival: no se publica
        if actual is not None and orden < actual - MAX_ANTIGUEDAD:
            continue                                               # gol viejo
        nombre, minuto, modo = partir_gol(texto)
        if nombre:
            out.append({"n": n, "gl": cl, "gv": cv, "goleador": nombre, "minuto": minuto, "modo": modo, "lado": "local" if celta_local else "visitante"})
    return out


def datos_gol(p, g):
    d = datos(p, "¡GOOOOOOL!", con_minuto=False, eq="celta")
    d.update(tipo="gol", goles_local=g["gl"], goles_visitante=g["gv"], goleador=g["goleador"], minuto=g["minuto"], modo=g["modo"], lado=g["lado"], _n=g["n"])
    d.pop("goleadores_local", None)
    d.pop("goleadores_visitante", None)
    return d


# ---------------------------------------------------------------- tarjetas rojas y penaltis parados (v84, solo el Celta)
def _texto_ev(ev):
    return " ".join(str(x) for x in ((ev.get("type") or {}).get("text"), ev.get("text"), ev.get("shortText")) if x)


def _slug(t):
    import unicodedata
    return re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", (t or "").lower()).encode("ascii", "ignore").decode()).strip("-")


def _nombres_ev(ev):
    out = []
    for a in ev.get("athletesInvolved") or []:                  # formato del marcador (details)
        n = a.get("displayName") or a.get("shortName")
        if n:
            out.append(n)
    for pt in ev.get("participants") or []:                     # formato del detalle del partido (keyEvents)
        n = (pt.get("athlete") or {}).get("displayName")
        if n:
            out.append(n)
    return out


def eventos_disciplina(items):
    """Eventos de ESPN (competitions[0].details del marcador o keyEvents del detalle) -> expulsiones y penaltis parados, en orden:
    [{'tipo': 'roja'|'doble'|'penalti_parado', 'jugador', 'portero', 'minuto', 'orden', 'equipo_id'}].
    ESPN no documenta su formato, así que se mira todo a la vez (banderas redCard/yellowCard y el texto del evento).
    Roja directa o doble amarilla: es doble si el texto lo dice, o si ese jugador ya tenía una amarilla antes en el partido (salvo que el texto diga «straight red»)."""
    previos = []
    for ev in items or []:
        try:
            if ev.get("shootout"):
                continue
            txt = _texto_ev(ev)
            nombres = _nombres_ev(ev)
            base = {"jugador": nombres[0] if nombres else "", "minuto": R._min((ev.get("clock") or {}).get("displayValue") or ""),
                    "equipo_id": str((ev.get("team") or {}).get("id", "")), "portero": None}
            base["orden"] = orden_minuto(base["minuto"]) if base["minuto"] else 999.0
            segunda = bool(re.search(r"second yellow|2nd yellow|second bookable|segunda amarilla|yellow.{0,12}red", txt, re.I))
            directa = bool(re.search(r"straight red|violent conduct|serious foul play|denying an obvious|roja directa", txt, re.I))
            if ev.get("redCard") or re.search(r"\bred card\b|tarjeta roja|sent off|expulsad", txt, re.I):
                previos.append(dict(base, tipo="roja", segunda=segunda, directa=directa))
            elif ev.get("yellowCard") or re.search(r"yellow card|tarjeta amarilla", txt, re.I):
                previos.append(dict(base, tipo="doble" if segunda else "amarilla", segunda=segunda, directa=False))
            elif (re.search(r"penalty.{0,12}saved|saved.{0,25}penalty|penalti parado|penalty save", txt, re.I)
                  or (ev.get("penaltyKick") and not ev.get("scoringPlay") and re.search(r"saved|parad|atajad", txt, re.I))):
                m = re.search(r"(?:saved by|parado por|atajado por)\s+([^.,;()\n]+)", txt, re.I)
                previos.append(dict(base, tipo="penalti_parado", portero=(m.group(1).strip() if m else None), segunda=False, directa=False,
                                    otros=nombres[1:]))
        except Exception:
            continue
    previos.sort(key=lambda e: e["orden"])
    amarillas, out = {}, []
    for e in previos:
        clave = _slug(e["jugador"])
        if e["tipo"] == "amarilla":
            amarillas.setdefault(clave, []).append(e["orden"])
            continue
        if e["tipo"] in ("roja", "doble"):
            if not e["jugador"]:
                continue                                         # sin nombre no se publica (puede llegar en la siguiente revisión)
            doble = e["tipo"] == "doble" or e["segunda"] or (not e["directa"] and any(o <= e["orden"] for o in amarillas.get(clave, [])))
            ya = [x for x in out if x["tipo"] in ("roja", "doble") and _slug(x["jugador"]) == clave]
            if ya:                                               # la misma expulsión contada dos veces (amarilla+roja, marcador+detalle)
                if doble:
                    ya[0]["tipo"] = "doble"
                continue
            out.append({k: e[k] for k in ("jugador", "minuto", "orden", "equipo_id", "portero")} | {"tipo": "doble" if doble else "roja"})
        else:
            if any(x["tipo"] == "penalti_parado" and abs(x["orden"] - e["orden"]) < 1 for x in out):
                continue
            out.append({k: e[k] for k in ("jugador", "minuto", "orden", "equipo_id", "portero")} | {"tipo": "penalti_parado", "otros": e.get("otros", [])})
    return out


def penalti_a_favor(e):
    """Un penalti parado solo se publica si lo para el Celta (lo lanza el rival). Devuelve (a_favor, lanzador, portero)."""
    try:
        import caras
        celta_id = str(R.CELTA_ESPN)
        nombre = e["jugador"]
        pos = (caras.posicion_de(nombre) or "") if nombre else ""
        if pos:                                                   # el nombre es de un jugador del Celta: si es el portero, lo ha parado él; si no, el que lo lanza es del Celta
            if re.search(r"porteir|portero", pos, re.I):
                return True, None, nombre
            return False, nombre, None
        if e["equipo_id"] and e["equipo_id"] != celta_id:         # lo lanza un jugador del rival
            portero = e.get("portero")
            if not portero:
                for o in e.get("otros") or []:
                    if re.search(r"porteir|portero", caras.posicion_de(o) or "", re.I):
                        portero = o
            return True, nombre or None, portero
    except Exception:
        pass
    return False, None, None


def eventos_a_publicar(p, actual, sin_internet):
    """Expulsiones (de cualquier equipo) y penaltis parados por el Celta del partido en juego, solo los recientes."""
    items = list(p.get("detalles") or [])
    if not sin_internet and p.get("liga") and p.get("id"):       # el detalle del partido (keyEvents) suele traer más datos que el marcador
        try:
            items += R.get(R.ESPN.format(p["liga"]) + f"summary?event={p['id']}").get("keyEvents") or []
        except Exception as e:
            print(f"aviso: sin detalle del partido para tarjetas/penaltis: {e}", file=sys.stderr)
    out = []
    for e in eventos_disciplina(items):
        if actual is not None and e["orden"] < actual - MAX_ANTIGUEDAD:
            continue
        if e["tipo"] == "penalti_parado":
            fav, lanzador, portero = penalti_a_favor(e)
            if not fav:
                continue
            e = dict(e, jugador=lanzador or "", portero=portero)
        out.append(e)
    return out


def _nombre_equipo(p, tid):
    return R.nombre(p["home"]) if tid and tid == p.get("home_id") else R.nombre(p["away"]) if tid and tid == p.get("away_id") else ""


def datos_evento(p, e, n):
    celta_local = R.es_celta(p["home"]) and not R.es_fortuna(p["home"])
    lado = "local" if celta_local else "visitante"
    if e["tipo"] == "penalti_parado":
        rival = R.nombre(p["away"] if celta_local else p["home"])
        d = datos(p, "¡PENALTI PARADO!", con_minuto=False, eq="celta")
        d.update(tipo="penalti_parado", goleador=(e.get("portero") or "¡NON PASA!"), minuto=e["minuto"], lado=lado,
                 etiqueta=(f"Penalti de {e['jugador']} · {rival}" if e.get("jugador") else f"Penalti do {rival}"), portero=e.get("portero") or "", lanzador=e.get("jugador") or "", rival=rival)
    else:
        equipo = _nombre_equipo(p, e["equipo_id"])
        del_celta = e["equipo_id"] == str(R.CELTA_ESPN)
        d = datos(p, "¡DOBLE AMARILLA!" if e["tipo"] == "doble" else "¡ROJA DIRECTA!", con_minuto=False, eq="celta")
        d.update(tipo="tarjeta", goleador=e["jugador"], minuto=e["minuto"], lado=lado, icono="doble" if e["tipo"] == "doble" else "roja",
                 etiqueta=("EXPULSADO · " + equipo.upper()) if equipo else "EXPULSADO", equipo=equipo, de="celta" if del_celta else "rival", clase=e["tipo"])
    d.update(goles_local=p["gl"], goles_visitante=p["gv"], _n=n)
    d.pop("goleadores_local", None)
    d.pop("goleadores_visitante", None)
    return d


def escribir(ruta, d):
    json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("escrito", ruta)


def procesar(eq, p, salida, sin_internet):
    """Un partido en juego del Celta o del Fortuna: goles (solo Celta), inicio y descanso."""
    m = minuto_num(p.get("minuto"))
    descanso = bool(re.search(r"HALFTIME", p.get("estado", ""), re.I))
    detallar = (p["gl"] + p["gv"] > 0) and not sin_internet and (len(p["gol_l"]), len(p["gol_v"])) != (p["gl"], p["gv"])
    if eq == "celta" and detallar:                                 # goles: si la lista de goleadores no está completa, se pide el detalle del partido
        previos = (p["gol_l"], p["gol_v"])
        p["gol_l"], p["gol_v"] = [], []
        R.completar_goles(p)
        if not (p["gol_l"] or p["gol_v"]):
            p["gol_l"], p["gol_v"] = previos
    elif eq == "fortuna" and detallar and (descanso or (p.get("periodo") == 2 and m and 46 <= m <= 60)) and not (p["gol_l"] or p["gol_v"]):
        R.completar_goles(p)                                        # el Fortuna solo necesita los goleadores para el descanso
    if eq == "celta" and p["gl"] + p["gv"] > 0:
        for g in goles_del_celta(p, 45 if descanso else m):
            escribir(os.path.join(salida, f"directo_celta_gol_{g['n']:02d}.json"), datos_gol(p, g))
    if eq == "celta":                                              # v84: expulsiones y penaltis parados
        try:
            nt = npp = 0
            for e in eventos_a_publicar(p, 45 if descanso else m, sin_internet):
                if e["tipo"] == "penalti_parado":
                    npp += 1
                    escribir(os.path.join(salida, f"directo_celta_penalti_{npp:02d}.json"), datos_evento(p, e, npp))
                else:
                    nt += 1
                    escribir(os.path.join(salida, f"directo_celta_tarjeta_{nt:02d}.json"), datos_evento(p, e, nt))
        except Exception as e:
            print(f"aviso: tarjetas/penaltis no disponibles ({e})", file=sys.stderr)
    if descanso:
        escribir(os.path.join(salida, f"directo_{eq}_descanso.json"), datos(p, "DESCANSO", con_minuto=False, eq=eq))
    elif p.get("periodo") == 2 and m and 46 <= m <= 60:           # se nos pasó el descanso (la revisión es cada pocos minutos): se reconstruye con los goles de la primera parte
        q = al_descanso(p)
        if not q:
            print(f"{eq}: segunda parte sin goles detallados: no se reconstruye el descanso.")
            return
        escribir(os.path.join(salida, f"directo_{eq}_descanso.json"), datos(q, "DESCANSO", con_minuto=False, eq=eq))
    elif p["gl"] + p["gv"] == 0 and (p.get("periodo") or 1) == 1 and (m is None or m <= 15):
        escribir(os.path.join(salida, f"directo_{eq}_inicio.json"), datos(p, "COMIENZA EL PARTIDO", con_minuto=False, eq=eq))
    else:
        print(f"{eq}: en juego, pero ahora no toca inicio ni descanso.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", default=None)
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    a = ap.parse_args()
    os.makedirs(a.salida, exist_ok=True)
    registro = []
    try:
        vivos = desde_archivo(a.desde) if a.desde else buscar_en_vivo(registro)
    except Exception as e:
        print(f"aviso: directo sin datos ({e})", file=sys.stderr)
        return
    finally:                                                       # v56: lo que ha visto ESPN en esta revisión, para poder comprobarlo en el artifact «historias»
        if registro:
            open(os.path.join(a.salida, "directo_log.txt"), "w", encoding="utf-8").write(
                datetime.datetime.now(MADRID).strftime("%Y-%m-%d %H:%M Madrid") + "\n" + "\n".join(registro) + "\n")
    if not any(vivos.values()):
        print("Ni el Celta ni el Celta Fortuna están jugando ahora mismo.")
        return
    for eq, partidos in vivos.items():
        if partidos:
            procesar(eq, partidos[0], a.salida, bool(a.desde))


if __name__ == "__main__":
    main()
