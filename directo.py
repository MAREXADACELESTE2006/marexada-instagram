"""Marexada Celeste · Celta (primer equipo) EN DIRECTO (v50).

Mira si el Celta está jugando ahora mismo (ESPN: LaLiga, Europa League, Copa del Rey). Si es así, escribe en datos_reales/:
    directo_celta_inicio.json    «COMIENZA EL PARTIDO» (primeros minutos, marcador 0-0)
    directo_celta_descanso.json  «DESCANSO» con el marcador y los goleadores de la primera parte
El final lo saca resultados.py como siempre. No hay publicación por gol (decisión de la peña, v51).
Si el Celta no está jugando, no escribe nada. Nunca rompe el programa: si ESPN falla, simplemente no hay directo.

Uso:
    python directo.py                              (lee internet)
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
    out = []
    for liga, k in (("esp.1", "liga"), ("uefa.europa", "euro"), ("esp.copa_del_rey", "copa")):
        try:
            evs = R.get(R.ESPN.format(liga) + f"teams/{R.CELTA_ESPN}/schedule").get("events") or []
        except Exception as e:
            print(f"aviso: ESPN {liga}: {e}", file=sys.stderr)
            continue
        for e in evs:
            p = de_espn_directo(e, k)
            if p and R.es_celta(p["home"] + p["away"]) and not R.es_fortuna(p["home"]) and not R.es_fortuna(p["away"]):
                p["liga"] = liga
                out.append(p)
    return out


def desde_archivo(ruta):
    j = json.load(open(ruta, encoding="utf-8"))
    return [p for k, resp in (j.get("celta") or {}).items() for p in (de_espn_directo(e, k) for e in resp.get("events", [])) if p]


def datos(p, titulo, con_minuto=True):
    f = p["f"].astimezone(MADRID)
    d = R.datos(p, "celta")
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
    if not vivos:
        print("El Celta no está jugando ahora mismo.")
        return
    p = vivos[0]
    m = minuto_num(p.get("minuto"))
    descanso = bool(re.search(r"HALFTIME", p.get("estado", ""), re.I))
    if (p["gl"] + p["gv"] > 0) and not (p["gol_l"] or p["gol_v"]) and not a.desde and (descanso or (p.get("periodo") == 2 and m and 46 <= m <= 60)):
        R.completar_goles(p)
    if descanso:
        salida, titulo = os.path.join(a.salida, "directo_celta_descanso.json"), "DESCANSO"
        d = datos(p, titulo, con_minuto=False)
    elif p.get("periodo") == 2 and m and 46 <= m <= 60:       # se nos pasó el descanso (la revisión es cada pocos minutos): se reconstruye con los goles de la primera parte
        q = al_descanso(p)
        if not q:
            print("Segunda parte sin goles detallados: no se reconstruye el descanso.")
            return
        salida, d = os.path.join(a.salida, "directo_celta_descanso.json"), datos(q, "DESCANSO", con_minuto=False)
    elif p["gl"] + p["gv"] == 0 and (p.get("periodo") or 1) == 1 and (m is None or m <= 15):
        salida, d = os.path.join(a.salida, "directo_celta_inicio.json"), datos(p, "COMIENZA EL PARTIDO", con_minuto=False)
    else:
        print("En juego, pero ahora no toca inicio ni descanso.")
        return
    json.dump(d, open(salida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("escrito", salida)


if __name__ == "__main__":
    main()
