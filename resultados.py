"""Marexada Celeste · resultados del Celta y del Celta Fortuna por marcador (v12).

Mira el último partido ya jugado del Celta (LaLiga, Europa League, Copa del Rey) y del Celta Fortuna (Hypermotion) con las
mismas fuentes que tu web (netlify/functions/partidos.mjs): ESPN primero y TheSportsDB de respaldo.
Da marcador y fecha, SIN goleadores (esos vendrían de la crónica de rccelta.es).

Crea en datos_reales/:  resultado_celta.json  y  resultado_fortuna.json

Uso:
    python resultados.py                          (lee internet)
    python resultados.py --desde fixtures/espn_resultados_EJEMPLO.json    (prueba sin internet)
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.request

from calendario import DIA, MADRID, escudo, nombre

BASE = os.path.dirname(os.path.abspath(__file__))
ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/{}/"
SDB = "https://www.thesportsdb.com/api/v1/json/3/"
CELTA_ESPN, FORTUNA_ESPN, CELTA_SDB = "85", "131858", "133937"
LOGO = {"liga": "laliga", "euro": "europa", "hm": "hypermotion", "copa": "copa"}
JORNADA = {"copa": "Copa do Rei"}

es_celta = lambda n: bool(re.search(r"celta", n or "", re.I))
es_fortuna = lambda n: bool(re.search(r"celta.*(fortuna|\bb\b)|(fortuna|\bb\b).*celta", n or "", re.I))


def get(url):
    req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "Mozilla/5.0 (compatible; MarexadaCeleste/1.0)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def num(x):
    if isinstance(x, dict):
        x = x.get("value", x.get("displayValue"))
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def _min(m):
    """"45'+2'" -> "45+2'" """
    return re.sub(r"'\s*\+\s*(\d+)'?", r"+\1'", (m or "").strip())


def goles_espn(c, h):
    """Goleadores del propio ESPN (competitions[0].details) si vienen; si no, listas vacías. Nunca rompe."""
    gl, gv = [], []
    try:
        hid = str((h.get("team") or {}).get("id", ""))
        for dt in c.get("details") or []:
            if not dt.get("scoringPlay"):
                continue
            ath = (dt.get("athletesInvolved") or [{}])[0]
            nom = ath.get("displayName") or ath.get("shortName") or ""
            if not nom:
                continue
            extra = " (p.p.)" if dt.get("ownGoal") else " (p.)" if dt.get("penaltyKick") else ""
            txt = f"{nom}{extra} {_min((dt.get('clock') or {}).get('displayValue'))}".strip()
            (gl if str((dt.get("team") or {}).get("id", "")) == hid else gv).append(txt)
    except Exception:
        return [], []
    return gl, gv


def goles_sdb(texto):
    """TheSportsDB: "16':Ferran Jutglà;24':Ferran Jutglà;" -> ["Ferran Jutglà 16'", ...]"""
    out = []
    for parte in (texto or "").split(";"):
        m = re.match(r"\s*(\d+(?:\+\d+)?)'?\s*:?\s*(.+?)\s*$", parte)
        if m:
            out.append(f"{m.group(2)} {m.group(1)}'")
    return out


def de_espn(ev, k):
    c = (ev.get("competitions") or [{}])[0]
    h = a = None
    for t in c.get("competitors", []):
        if t.get("homeAway") == "home":
            h = t
        else:
            a = t
    st = (c.get("status") or ev.get("status") or {}).get("type") or {}
    if not h or not a or not (st.get("completed") or re.search(r"FULL_TIME|FINAL", st.get("name", ""))):
        return None
    gl, gv = num(h.get("score")), num(a.get("score"))
    if gl is None or gv is None:
        return None
    nm = lambda t: (t.get("team") or {}).get("displayName") or (t.get("team") or {}).get("name") or ""
    try:
        f = datetime.datetime.fromisoformat((ev.get("date") or c.get("date")).replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    g1, g2 = goles_espn(c, h)
    return {"f": f, "k": k, "home": nm(h), "away": nm(a), "gl": gl, "gv": gv, "gol_l": g1, "gol_v": g2, "id": ev.get("id") or c.get("id")}


def de_sdb(ev, k):
    iso = ev.get("strTimestamp") or (ev.get("dateEvent") + "T" + (ev.get("strTime") or "00:00:00") if ev.get("dateEvent") else None)
    gl, gv = num(ev.get("intHomeScore")), num(ev.get("intAwayScore"))
    if not iso or gl is None or gv is None:
        return None
    if not re.search(r"[zZ]|[+-]\d\d:?\d\d$", iso):
        iso += "Z"
    try:
        f = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return {"f": f, "k": k, "home": ev.get("strHomeTeam") or "", "away": ev.get("strAwayTeam") or "", "gl": gl, "gv": gv,
            "gol_l": goles_sdb(ev.get("strHomeGoalDetails")), "gol_v": goles_sdb(ev.get("strAwayGoalDetails")), "sid": ev.get("idEvent")}


def temporada_espn():
    n = datetime.date.today()
    return n.year if n.month >= 7 else n.year - 1


def fuentes_en_vivo():
    """Para cada equipo devuelve [(k, [partidos jugados])] probando ESPN y luego TheSportsDB."""
    y = temporada_espn()
    s = f"{y}-{y + 1}"
    out = {"celta": [], "fortuna": []}
    errores = []
    for eq, id_, ligas, filtro in (("celta", CELTA_ESPN, (("esp.1", "liga"), ("uefa.europa", "euro"), ("esp.copa_del_rey", "copa")), lambda p: es_celta(p["home"] + p["away"]) and not es_fortuna(p["home"]) and not es_fortuna(p["away"])),
                                   ("fortuna", FORTUNA_ESPN, (("esp.2", "hm"),), lambda p: es_fortuna(p["home"]) or es_fortuna(p["away"]))):
        for liga, k in ligas:
            for sufijo in (f"teams/{id_}/schedule?season={y}", f"teams/{id_}/schedule"):
                try:
                    evs = get(ESPN.format(liga) + sufijo).get("events") or []
                    out[eq] += [dict(p, liga=liga) for p in (de_espn(e, k) for e in evs) if p and filtro(p)]
                    break
                except Exception as e:
                    errores.append(f"ESPN {liga} {eq}: {e}")
    sdb = (("celta", "liga", "4335"), ("celta", "euro", "4481"), ("fortuna", "hm", "4400"))
    for eq, k, lid in sdb:
        if out[eq] and any(p["k"] == k for p in out[eq]):
            continue                                   # ESPN ya dio partidos de esta competición
        try:
            evs = get(SDB + f"eventsseason.php?id={lid}&s={s}").get("events") or []
            for e in evs:
                p = de_sdb(e, k)
                if p and ((eq == "fortuna" and (es_fortuna(p["home"]) or es_fortuna(p["away"]))) or
                          (eq == "celta" and es_celta(p["home"] + p["away"]) and not es_fortuna(p["home"]) and not es_fortuna(p["away"]))):
                    out[eq].append(p)
        except Exception as e:
            errores.append(f"TheSportsDB {k}: {e}")
    try:                                               # v38 respaldo: últimos partidos del Celta, de cualquier competición (Copa incluida)
        for e in get(SDB + f"eventslast.php?id={CELTA_SDB}").get("results") or []:
            lg = e.get("strLeague") or ""
            k = "copa" if re.search(r"copa", lg, re.I) else "euro" if re.search(r"europa|uefa", lg, re.I) else "liga"
            p = de_sdb(e, k)
            if p and es_celta(p["home"] + p["away"]) and not es_fortuna(p["home"]) and not es_fortuna(p["away"]):
                if not any(q["f"].date() == p["f"].date() and q["gl"] == p["gl"] and q["gv"] == p["gv"] for q in out["celta"]):
                    out["celta"].append(p)
    except Exception as e:
        errores.append(f"TheSportsDB últimos del Celta: {e}")
    return out, errores


def goles_resumen_espn(j, home_nombre):
    """ESPN summary?event=ID -> keyEvents con los goles (nombre, minuto, equipo). Nunca rompe."""
    gl, gv = [], []
    try:
        hid = ""
        for t in (((j.get("header") or {}).get("competitions") or [{}])[0].get("competitors") or []):
            if t.get("homeAway") == "home":
                hid = str((t.get("team") or {}).get("id", ""))
        for ev in j.get("keyEvents") or []:
            tipo = ((ev.get("type") or {}).get("text") or "")
            if not (ev.get("scoringPlay") or re.search(r"goal|penalty - scored", tipo, re.I)):
                continue
            nom = ""
            for pt in ev.get("participants") or []:
                nom = (pt.get("athlete") or {}).get("displayName") or ""
                if nom:
                    break
            if not nom:
                nom = re.sub(r"\s+(Goal|Penalty.*)$", "", ev.get("shortText") or "").strip()
            if not nom:
                continue
            extra = " (p.p.)" if re.search(r"own", tipo, re.I) else " (p.)" if re.search(r"penalty", tipo, re.I) else ""
            tid = str((ev.get("team") or {}).get("id", ""))
            es_local = (tid == hid) if (tid and hid) else ((ev.get("team") or {}).get("displayName") == home_nombre)
            (gl if es_local else gv).append(f"{nom}{extra} {_min((ev.get('clock') or {}).get('displayValue'))}".strip())
    except Exception:
        return [], []
    return gl, gv


def completar_goles(p):
    """Si el partido no trae goleadores, los busca en el detalle del partido (ESPN) y, si no, en TheSportsDB."""
    if p.get("gol_l") or p.get("gol_v") or (p["gl"] + p["gv"]) == 0:
        return
    try:
        if p.get("liga") and p.get("id"):
            gl, gv = goles_resumen_espn(get(ESPN.format(p["liga"]) + f"summary?event={p['id']}"), p["home"])
            if gl or gv:
                p["gol_l"], p["gol_v"] = gl, gv
                return
    except Exception as e:
        print("aviso: detalle ESPN sin goleadores:", e, file=sys.stderr)
    try:
        if p.get("sid"):
            ev = (get(SDB + f"lookupevent.php?id={p['sid']}").get("events") or [{}])[0]
            gl, gv = goles_sdb(ev.get("strHomeGoalDetails")), goles_sdb(ev.get("strAwayGoalDetails"))
            if gl or gv:
                p["gol_l"], p["gol_v"] = gl, gv
    except Exception as e:
        print("aviso: detalle TheSportsDB sin goleadores:", e, file=sys.stderr)


def desde_archivo(ruta):
    j = json.load(open(ruta, encoding="utf-8"))
    out = {"celta": [], "fortuna": []}
    for eq, por_k in ((e, v) for e, v in j.items() if isinstance(v, dict)):
        for k, resp in por_k.items():
            out[eq] += [p for p in (de_espn(e, k) for e in resp.get("events", [])) if p]
    return out, []


def datos(p, eq):
    f = p["f"].astimezone(MADRID)
    return {"tipo": "resultado", "competicion": "liga", "logo": LOGO.get(p["k"]), "tag": "CELTA FORTUNA" if eq == "fortuna" else "REAL CLUB CELTA",
            "local": escudo(p["home"]), "visitante": escudo(p["away"]),
            "local_nombre": nombre(p["home"]), "visitante_nombre": nombre(p["away"]),
            "jornada": JORNADA.get(p["k"], ""), "goles_local": p["gl"], "goles_visitante": p["gv"],
            "goleadores_local": p.get("gol_l", []), "goleadores_visitante": p.get("gol_v", []),
            "fecha_hora": f"{DIA[f.weekday()]} {f.day:02d}/{f.month:02d}", "_fecha": f.date().isoformat()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", default=None)
    ap.add_argument("--ahora", default=None, help="UTC AAAA-MM-DDTHH:MM:SS (por defecto, ahora): ignora partidos posteriores")
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    a = ap.parse_args()
    ahora = datetime.datetime.fromisoformat(a.ahora).replace(tzinfo=datetime.timezone.utc) if a.ahora else datetime.datetime.now(datetime.timezone.utc)
    os.makedirs(a.salida, exist_ok=True)
    listas, errores = desde_archivo(a.desde) if a.desde else fuentes_en_vivo()
    escritos = 0
    for eq, partidos in listas.items():
        jugados = sorted((p for p in partidos if p["f"] <= ahora), key=lambda p: p["f"])
        if not jugados:
            print(f"aviso: sin partidos jugados del {eq}", file=sys.stderr)
            continue
        if not a.desde:
            completar_goles(jugados[-1])
        ruta = os.path.join(a.salida, f"resultado_{eq}.json")
        json.dump(datos(jugados[-1], eq), open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("escrito", ruta)
        escritos += 1
    for e in errores:
        print("aviso:", e, file=sys.stderr)
    if not escritos:
        sys.exit("ERROR: no se pudo leer ningún resultado (" + "; ".join(errores[-2:]) + ")")


if __name__ == "__main__":
    main()
