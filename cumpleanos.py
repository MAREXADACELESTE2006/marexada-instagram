"""Marexada Celeste · cumpleaños de la plantilla (v22; v72: con la cara del jugador si hay foto).

Lee cumpleanos.json (jugadores y cuerpo técnico del Celta y del Celta Fortuna, con su fecha de nacimiento) y, si hoy cumple años
alguien, escribe en la carpeta de salida:
    cumpleanos_<nombre>.json     (uno por persona; el programa diario saca una historia «Feliz aniversario»)
No necesita internet. Para añadir o corregir a alguien, edita cumpleanos.json en GitHub (lápiz de «Edit this file»).

Uso:
    python cumpleanos.py --hoy 2026-11-19 --salida carpeta
"""
import argparse
import datetime
import json
import os
import re
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
MESES_GL = ["xaneiro", "febreiro", "marzo", "abril", "maio", "xuño", "xullo", "agosto", "setembro", "outubro", "novembro", "decembro"]
TAG = {"celta": "REAL CLUB CELTA", "fortuna": "CELTA FORTUNA"}


def slug(t):
    t = unicodedata.normalize("NFKD", t.lower().replace("ı", "i")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hoy", default=datetime.date.today().isoformat())
    ap.add_argument("--archivo", default=os.path.join(BASE, "cumpleanos.json"))
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    a = ap.parse_args()
    hoy = datetime.date.fromisoformat(a.hoy)
    os.makedirs(a.salida, exist_ok=True)
    try:
        personas = json.load(open(a.archivo, encoding="utf-8"))["personas"]
    except Exception as e:
        sys.exit(f"ERROR cumpleaños: no puedo leer {os.path.basename(a.archivo)}: {e}")
    for viejo in os.listdir(a.salida):
        if re.fullmatch(r"cumpleanos_.+\.json", viejo):
            os.remove(os.path.join(a.salida, viejo))
    hechos, errores = [], []
    for p in personas:
        if p.get("pendiente"):
            continue
        try:
            n = datetime.date.fromisoformat(p["nacimiento"])
        except Exception:
            errores.append(f"{p.get('nombre')}: fecha {p.get('nacimiento')!r}")
            continue
        dia = (n.month, n.day)
        if dia == (2, 29) and not (hoy.year % 4 == 0 and (hoy.year % 100 != 0 or hoy.year % 400 == 0)):
            dia = (2, 28)                                       # los nacidos el 29/02 celebran el 28 en años no bisiestos
        if (hoy.month, hoy.day) != dia:
            continue
        d = {"tipo": "cumpleanos", "competicion": "liga", "tag": TAG.get(p.get("equipo"), "REAL CLUB CELTA"), "nombre": p["nombre"],
             "posicion": p.get("posicion", ""), "edad": hoy.year - n.year, "fecha": f"{hoy.day} de {MESES_GL[hoy.month - 1]}",
             "equipo": p.get("equipo", "celta"), "año": hoy.year}
        if p.get("instagram"):                                                   # v76: cuenta de Instagram del jugador (se pone en la imagen y en el texto)
            d["instagram"] = p["instagram"].lstrip("@")
        foto = os.path.join("assets", "caras", slug(p["nombre"]) + ".webp")       # v72: cara de la web del club, si la hay (assets/caras/<nombre>.webp)
        if os.path.exists(os.path.join(BASE, foto)):
            d["foto"] = foto.replace(os.sep, "/")
        with open(os.path.join(a.salida, f"cumpleanos_{slug(p['nombre'])}.json"), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        hechos.append(f"{p['nombre']} ({d['edad']})")
    print("cumpleaños de hoy: " + (", ".join(hechos) if hechos else "nadie"))
    if errores:
        sys.exit("Cumpleaños con fecha mal escrita: " + "; ".join(errores))


if __name__ == "__main__":
    main()
