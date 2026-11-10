"""Marexada Celeste · calendario del Celta y del Celta Fortuna (v10).

Lee el calendario DIRECTAMENTE de las mismas fuentes públicas que usa la web de la peña (v14):
  - Celta (LaLiga, Europa League, Copa): TheSportsDB
  - Celta Fortuna (Hypermotion): ESPN
y crea en datos_reales/:
    proximo_celta.json       próximo partido del Celta (LaLiga, Europa League o Copa)
    proximo_fortuna.json     próximo partido del Celta Fortuna (Hypermotion)
    previa_hoy.json          SOLO si hoy el Celta juega en casa: la previa en la Cafetería Kiev (2 h antes)
Si hoy no hay previa, borra previa_hoy.json para no publicar una vieja.

Uso:
    python calendario.py                                   (lee internet)
    python calendario.py --desde fixtures/partidos_api_EJEMPLO.json --ahora 2026-11-08T08:00:00
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.request
from zoneinfo import ZoneInfo

import rccelta

BASE = os.path.dirname(os.path.abspath(__file__))
URL = "directo"
SDB = "https://www.thesportsdb.com/api/v1/json/3/eventsnext.php?id=133937"
ESPN_FORTUNA = "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.2/teams/131858/schedule"
CELTA_ID = "133937"
MADRID = ZoneInfo("Europe/Madrid")
DIA = ["Lun", "Mar", "Mér", "Xov", "Ven", "Sáb", "Dom"]
LOGO = {"liga": "laliga", "euro": "europa", "hm": "hypermotion", "copa": "copa"}
LUGAR = "Balaídos"


def _get(url):
    req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "Mozilla/5.0 (compatible; MarexadaCeleste/1.0)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _tipo_competicion(liga):
    liga = liga or ""
    if re.search(r"europa league", liga, re.I):
        return "euro"
    if re.search(r"copa del rey|copa de s", liga, re.I):
        return "copa"
    if re.search(r"la ?liga|primera", liga, re.I) and not re.search(r"la ?liga 2|segunda|hypermotion", liga, re.I):
        return "liga"
    return None


def partidos_celta(j):
    """TheSportsDB eventsnext.php -> lista de partidos en el formato de la web."""
    out = []
    for ev in (j or {}).get("events") or []:
        iso = ev.get("strTimestamp")
        if not iso and ev.get("dateEvent"):
            iso = ev["dateEvent"] + "T" + (ev.get("strTime") or "00:00:00")
        if not iso:
            continue
        if not re.search(r"[zZ]|[+-]\d\d:?\d\d$", iso):
            iso += "Z"
        k = _tipo_competicion(ev.get("strLeague"))
        if not k:
            continue
        casa = str(ev.get("idHomeTeam")) == CELTA_ID or bool(re.search(r"celta", ev.get("strHomeTeam") or "", re.I))
        out.append({"date": iso, "home": ev.get("strHomeTeam"), "away": ev.get("strAwayTeam"), "k": k,
                    "celtaHome": casa, "tbc": not ev.get("strTime") and not ev.get("strTimestamp")})
    return out


def partidos_fortuna(j):
    """ESPN schedule del Celta Fortuna -> lista de partidos en el formato de la web."""
    out = []
    for ev in (j or {}).get("events") or []:
        comp = (ev.get("competitions") or [None])[0]
        if not comp:
            continue
        st = (comp.get("status") or {}).get("type") or {}
        if st.get("completed"):
            continue
        h = a = None
        for t in comp.get("competitors") or []:
            if t.get("homeAway") == "home":
                h = t
            else:
                a = t
        if not h or not a or not ev.get("date"):
            continue
        nm = lambda t: (t.get("team") or {}).get("displayName") or (t.get("team") or {}).get("name") or ""
        out.append({"date": ev["date"], "home": nm(h), "away": nm(a), "k": "hm",
                    "celtaHome": bool(re.search(r"celta", nm(h), re.I)), "tbc": False})
    return out


def leer_directo():
    partidos, avisos = [], []
    for nombre_, url, fn in (("Celta (TheSportsDB)", SDB, partidos_celta), ("Celta Fortuna (ESPN)", ESPN_FORTUNA, partidos_fortuna)):
        try:
            crudo = _get(url)
            lista = fn(crudo)
            partidos += lista
            if not lista:
                n = len((crudo or {}).get("events") or [])
                avisos.append(f"{nombre_}: respondió pero sin partidos utilizables ({n} eventos en bruto)")
        except Exception as e:  # una fuente caída no debe tumbar la otra
            avisos.append(f"{nombre_}: {type(e).__name__}: {e}")
    for av in avisos:
        print("aviso:", av, file=sys.stderr)
    if not partidos:
        sys.exit("ERROR: sin partidos. " + " | ".join(avisos))
    return {"partidos": partidos}


def leer(fuente):
    if fuente == "directo":
        return leer_directo()
    if re.match(r"https?://", fuente):
        req = urllib.request.Request(fuente, headers={"accept": "application/json", "user-agent": "Mozilla/5.0 (compatible; MarexadaCeleste/1.0)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    return json.load(open(fuente, encoding="utf-8"))


def nombre(n):
    n = re.sub(r"\s+", " ", n or "").strip()
    return "Celta" if re.fullmatch(r"(RC |Real Club )?Celta( de)?( Vigo)?", n, re.I) else n


def escudo(n):
    return "celta-vigo" if re.search(r"celta", n or "", re.I) else rccelta.slug_equipo(n)


def datos(p, tipo):
    f = datetime.datetime.fromisoformat(p["date"].replace("Z", "+00:00")).astimezone(MADRID)
    fecha = f"{DIA[f.weekday()]} {f.day:02d}/{f.month:02d}" + ("" if p.get("tbc") else f" · {f:%H:%M}")
    fortuna = p["k"] == "hm"
    return {"tipo": tipo, "competicion": "liga", "logo": LOGO.get(p["k"]), "tag": "CELTA FORTUNA" if fortuna else "REAL CLUB CELTA",
            "local": escudo(p["home"]), "visitante": escudo(p["away"]),
            "local_nombre": nombre(p["home"]), "visitante_nombre": nombre(p["away"]),
            "fecha_hora": fecha, "_fecha": f.date().isoformat(), **({"lugar": LUGAR} if p.get("celtaHome") else {})}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", default=URL, help="\"directo\" (por defecto: TheSportsDB + ESPN), una URL o un archivo JSON con {partidos: [...]}")
    ap.add_argument("--ahora", default=None, help="fecha y hora UTC AAAA-MM-DDTHH:MM:SS (por defecto, ahora)")
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    a = ap.parse_args()
    ahora = datetime.datetime.fromisoformat(a.ahora).replace(tzinfo=datetime.timezone.utc) if a.ahora else datetime.datetime.now(datetime.timezone.utc)
    hoy = ahora.astimezone(MADRID).date()
    os.makedirs(a.salida, exist_ok=True)
    partidos = leer(a.desde).get("partidos") or []
    if not partidos:
        sys.exit("ERROR: el calendario no trae partidos (las fuentes TheSportsDB/ESPN no han respondido).")
    for p in partidos:
        p["_f"] = datetime.datetime.fromisoformat(p["date"].replace("Z", "+00:00"))

    def guardar(nombre_, d):
        ruta = os.path.join(a.salida, nombre_)
        json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("escrito", ruta)

    futuros = sorted((p for p in partidos if p["_f"] >= ahora - datetime.timedelta(hours=2)), key=lambda p: p["_f"])
    for clave, filtro in (("celta", lambda p: p["k"] != "hm"), ("fortuna", lambda p: p["k"] == "hm")):
        sig = next((p for p in futuros if filtro(p)), None)
        if sig:
            guardar(f"proximo_{clave}.json", datos(sig, "proximo"))
        else:
            print(f"aviso: no hay próximo partido del {clave}", file=sys.stderr)

    ruta_previa = os.path.join(a.salida, "previa_hoy.json")
    casa_hoy = next((p for p in futuros if p["k"] != "hm" and p.get("celtaHome") and p["_f"].astimezone(MADRID).date() == hoy), None)
    if casa_hoy and not casa_hoy.get("tbc"):
        guardar("previa_hoy.json", datos(casa_hoy, "previa"))
    else:
        if casa_hoy:
            print("aviso: hoy hay partido en casa pero la hora no está confirmada; sin previa", file=sys.stderr)
        else:
            print("hoy no hay partido del Celta en casa: sin previa")
        if os.path.exists(ruta_previa):
            os.remove(ruta_previa)


if __name__ == "__main__":
    main()
