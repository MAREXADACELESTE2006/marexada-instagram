"""Marexada Celeste · calendario del Celta y del Celta Fortuna (v10).

Lee el calendario público de la propia web de la peña, https://marexadaceleste.com/api/partidos
(la función de Netlify netlify/functions/partidos.mjs: junta ESPN y TheSportsDB desde el servidor),
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
URL = "https://marexadaceleste.com/api/partidos"
MADRID = ZoneInfo("Europe/Madrid")
DIA = ["Lun", "Mar", "Mér", "Xov", "Ven", "Sáb", "Dom"]
LOGO = {"liga": "laliga", "euro": "europa", "hm": "hypermotion", "copa": "copa"}
LUGAR = "Balaídos"


def leer(fuente):
    if re.match(r"https?://", fuente):
        req = urllib.request.Request(fuente, headers={"accept": "application/json", "user-agent": "Mozilla/5.0 (Marexada Celeste bot)"})
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
    ap.add_argument("--desde", default=URL, help="URL o archivo JSON con {partidos: [...]}")
    ap.add_argument("--ahora", default=None, help="fecha y hora UTC AAAA-MM-DDTHH:MM:SS (por defecto, ahora)")
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    a = ap.parse_args()
    ahora = datetime.datetime.fromisoformat(a.ahora).replace(tzinfo=datetime.timezone.utc) if a.ahora else datetime.datetime.now(datetime.timezone.utc)
    hoy = ahora.astimezone(MADRID).date()
    os.makedirs(a.salida, exist_ok=True)
    partidos = leer(a.desde).get("partidos") or []
    if not partidos:
        sys.exit("ERROR: el calendario no trae partidos (¿la función /api/partidos no está funcionando?).")
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
