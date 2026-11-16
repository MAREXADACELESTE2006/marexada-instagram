"""Marexada Celeste · EN DIRECTO (v53).

Mira si el Celta (primer equipo) o el Celta Fortuna están jugando ahora mismo (ESPN: LaLiga, Europa League, Copa del Rey e Hypermotion).
Escribe en datos_reales/ (o en la carpeta --salida):
  Celta y Celta Fortuna:
    directo_<equipo>_inicio.json     «COMIENZA EL PARTIDO» (primeros minutos, marcador 0-0)
    directo_<equipo>_descanso.json   «DESCANSO» con el marcador y los goleadores de la primera parte
  Solo el Celta (primer equipo):
    directo_celta_gol_NN.json        «¡GOOOOOOL!» por cada gol DEL CELTA: goleador, minuto y marcador en ese momento
                                     (NN = número de gol del partido). Los goles del rival no se publican.
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
            "id": ev.get("id") or c.get("id"), "minuto": minuto, "estado": tipo.get("name", ""), "periodo": st.get("period")}


def buscar_en_vivo():
    """{'celta': [partidos en juego], 'fortuna': [...]} leyendo ESPN."""
    out = {eq: [] for eq in EQUIPOS}
    for eq, (id_, ligas) in EQUIPOS.items():
        for liga, k in ligas:
            try:
                evs = R.get(R.ESPN.format(liga) + f"teams/{id_}/schedule").get("events") or []
            except Exception as e:
                print(f"aviso: ESPN {liga} ({eq}): {e}", file=sys.stderr)
                continue
            for e in evs:
                p = de_espn_directo(e, k)
                if p and es_del_equipo(eq, p):
                    p["liga"] = liga
                    out[eq].append(p)
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
    try:
        vivos = desde_archivo(a.desde) if a.desde else buscar_en_vivo()
    except Exception as e:
        print(f"aviso: directo sin datos ({e})", file=sys.stderr)
        return
    if not any(vivos.values()):
        print("Ni el Celta ni el Celta Fortuna están jugando ahora mismo.")
        return
    for eq, partidos in vivos.items():
        if partidos:
            procesar(eq, partidos[0], a.salida, bool(a.desde))


if __name__ == "__main__":
    main()
