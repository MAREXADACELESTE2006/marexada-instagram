"""Marexada Celeste · clasificaciones de LaLiga, Europa League y Hypermotion (v10).

Usa las MISMAS fuentes que la página https://marexadaceleste.com/clasificacion (js/clasificacion.js):
  1) ESPN   https://site.api.espn.com/apis/v2/sports/soccer/<liga>/standings
  2) TheSportsDB (clave gratuita 3)  .../lookuptable.php?l=<id>&s=<temporada>   (si ESPN falla)
y valida la tabla igual que la web (número de equipos, Celta dentro, partidos jugados que no bajan).

Crea en datos_reales/: clasificacion_celta_laliga.json, clasificacion_celta_europa.json, clasificacion_celta_fortuna.json

Uso:
    python clasificaciones.py                       (lee internet)
    python clasificaciones.py --desde fixtures/web_respaldo_jornada8_LL_EL_HM.json   (prueba sin internet)
"""
import argparse
import json
import os
import re
import sys
import urllib.request

import rccelta

BASE = os.path.dirname(os.path.abspath(__file__))
ESPN = "https://site.api.espn.com/apis/v2/sports/soccer/{}/standings"
SDB = "https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?l={}&s={}"
TEMPORADA = "2026-2027"

COMPETICIONES = {
    "laliga": dict(espn="esp.1", sdb="4335", equipos=20, re=r"la liga", nombre="LaLiga EA Sports", logo="laliga",
                   tag="REAL CLUB CELTA", destacado=r"celta", respaldo="LL"),
    "europa": dict(espn="uefa.europa", sdb="4481", equipos=36, re=r"europa league", nombre="UEFA Europa League · Fase liga", logo="europa",
                   tag="REAL CLUB CELTA", destacado=r"celta", respaldo="EL"),
    "fortuna": dict(espn="esp.2", sdb="4400", equipos=22, re=r"la liga 2|segunda|hypermotion", nombre="LaLiga Hypermotion", logo="hypermotion",
                    tag="CELTA FORTUNA", destacado=r"celta", respaldo="HM"),
}


def get(url):
    req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "Mozilla/5.0 (compatible; MarexadaCeleste/1.0)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def de_espn(j):
    filas = []
    for c in (j or {}).get("children", []):
        for i, e in enumerate((c.get("standings") or {}).get("entries", [])):
            st = {s.get("name"): s.get("value") for s in e.get("stats", [])}
            t = e.get("team") or {}
            filas.append({"p": int(st.get("rank") or i + 1), "t": t.get("displayName") or t.get("name"),
                          "pj": st.get("gamesPlayed"), "dg": st.get("pointDifferential"), "pts": st.get("points")})
    return filas


def de_sdb(j, patron):
    filas = [{"p": x.get("intRank"), "t": x.get("strTeam"), "pj": x.get("intPlayed"), "dg": x.get("intGoalDifference"),
              "pts": x.get("intPoints"), "lg": x.get("strLeague")} for x in (j or {}).get("table") or []]
    return filas if filas and re.search(patron, filas[0].get("lg") or "", re.I) else []


def valida(filas, n, patron_celta="celta"):
    """Mismas comprobaciones que la web: n equipos, números válidos y el Celta dentro."""
    try:
        if len(filas) != n:
            return None
        out = [{"p": int(f["p"]), "t": str(f["t"]), "pj": int(float(f["pj"])), "dg": int(float(f["dg"])), "pts": int(float(f["pts"]))} for f in filas]
    except (TypeError, ValueError, KeyError):
        return None
    if not any(re.search(patron_celta, f["t"], re.I) for f in out):
        return None
    return sorted(out, key=lambda f: f["p"])


def leer_tabla(c, minimo_pj=0):
    errores = []
    fuentes = [("ESPN", lambda: de_espn(get(ESPN.format(c["espn"])))),
               ("TheSportsDB", lambda: de_sdb(get(SDB.format(c["sdb"], TEMPORADA)), c["re"]))]
    for nombre, f in fuentes:
        try:
            filas = valida(f(), c["equipos"])
            if filas and sum(x["pj"] for x in filas) >= minimo_pj:
                return filas, nombre
            errores.append(f"{nombre}: tabla no válida")
        except Exception as e:  # red, 403, JSON raro...
            errores.append(f"{nombre}: {e}")
    raise RuntimeError("; ".join(errores))


def escudo(nombre):
    if re.search(r"celta", nombre, re.I):
        return "celta-vigo"
    return rccelta.slug_equipo(nombre)


def datos(c, filas):
    dest = next(f["t"] for f in filas if re.search(c["destacado"], f["t"], re.I))
    return {
        "tipo": "clasificacion", "competicion": "liga", "tag": c["tag"], "logo": c["logo"],
        "subtitulo": c["nombre"], "jornada": f"Xornada {max(f['pj'] for f in filas)}", "destacado": dest,
        "filas": [{"pos": f["p"], "nombre": f["t"], "escudo": escudo(f["t"]), "pts": f["pts"], "pj": f["pj"], "dg": f["dg"]} for f in filas],
    }


def desde_respaldo(c, snap):
    """Convierte las listas de respaldo de la web ([equipo, PX, DG, Pts] o [pos, equipo, PX, DG, Pts])."""
    lista = snap[c["respaldo"]]
    filas = []
    for i, r in enumerate(lista):
        if isinstance(r[0], int):
            filas.append({"p": r[0], "t": r[1], "pj": r[2], "dg": r[3], "pts": r[4]})
        else:
            filas.append({"p": i + 1, "t": r[0], "pj": r[1], "dg": r[2], "pts": r[3]})
    return filas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", default=None, help="JSON con las listas de respaldo de la web (prueba sin internet)")
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    a = ap.parse_args()
    os.makedirs(a.salida, exist_ok=True)
    snap = json.load(open(a.desde, encoding="utf-8")) if a.desde else None
    fallos = 0
    for clave, c in COMPETICIONES.items():
        try:
            if snap:
                filas, fuente = valida(desde_respaldo(c, snap), c["equipos"]), "respaldo"
            else:
                filas, fuente = leer_tabla(c)
            ruta = os.path.join(a.salida, f"clasificacion_celta_{clave}.json")
            json.dump(datos(c, filas), open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"escrito {ruta} ({fuente})")
        except Exception as e:
            fallos += 1
            print(f"ERROR en {clave}: {e}", file=sys.stderr)
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
