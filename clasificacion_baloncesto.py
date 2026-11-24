"""Marexada Celeste · clasificación de la Liga Femenina Endesa (la del Celta Femxa Zorka) desde la web de la Federación (v87).

Lee la «pasarela» oficial de la FEB (feb.es/lfendesa/Pasarela/clasificacion.aspx?g=4), una tabla en HTML normal con la jornada y la fecha,
y escribe clasificacion_baloncesto_fem.json en datos_reales/ (o en --salida) con el formato de las demás clasificaciones.
Puntos de la liga: 2 por victoria y 1 por derrota (columna PTs de la FEB). DG = puntos a favor - puntos en contra.

Uso:
    python clasificacion_baloncesto.py                                   (lee internet)
    python clasificacion_baloncesto.py --desde fixtures/feb_clasificacion_RECONSTRUIDO.html --salida carpeta     (prueba sin internet)
Si la página cambia y no se entiende, guarda lo recibido en clasificacion_baloncesto_DEBUG.html.
"""
import argparse
import datetime
import json
import os
import re
import sys

import baloncesto as B

BASE = os.path.dirname(os.path.abspath(__file__))
URL = "https://www.feb.es/lfendesa/Pasarela/clasificacion.aspx?g=4"


def leer_clasificacion(html):
    """(jornada, fecha, filas). Cada fila: {pos, nombre, escudo, pts, pj, dg}. Falla con B.ErrorLector si no se entiende la página."""
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    m = re.search(r"Jornada\s+(\d+)\s+(\d{2})/(\d{2})/(\d{4})", B.limpio(html))
    if not m:
        raise B.ErrorLector("No encuentro «Jornada N dd/mm/aaaa» en la clasificación de la FEB.")
    jornada = int(m.group(1))
    fecha = datetime.date(int(m.group(4)), int(m.group(3)), int(m.group(2)))
    filas = []
    for tr in re.findall(r"(?is)<tr\b.*?</tr>", html):
        celdas = [B.limpio(c) for c in re.findall(r"(?is)<t[dh]\b[^>]*>(.*?)</t[dh]>", tr)]
        if len(celdas) < 8 or not celdas[0].isdigit() or not all(c.lstrip("-").isdigit() for c in celdas[2:8]):
            continue
        pos, nombre = int(celdas[0]), celdas[1]
        pj, pg, pp, pf, pc, pts = (int(c) for c in celdas[2:8])
        escudo, bonito = B.equipo(nombre)
        filas.append({"pos": pos, "nombre": bonito, "escudo": escudo, "pts": pts, "pj": pj, "dg": pf - pc})
    if len(filas) < 8:
        raise B.ErrorLector(f"Solo he entendido {len(filas)} equipos en la clasificación de la FEB (esperaba 16).")
    return jornada, fecha, sorted(filas, key=lambda f: f["pos"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", default=URL, help="dirección o archivo HTML")
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    a = ap.parse_args()
    os.makedirs(a.salida, exist_ok=True)
    html = B.leer(a.desde)
    try:
        jornada, fecha, filas = leer_clasificacion(html)
    except B.ErrorLector as e:
        with open(os.path.join(a.salida, "clasificacion_baloncesto_DEBUG.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"aviso: {e} (guardada clasificacion_baloncesto_DEBUG.html)", file=sys.stderr)
        return
    d = {"tipo": "clasificacion", "competicion": "liga", "tag": B.TAG, "subtitulo": "Liga Femenina Endesa", "jornada": f"Xornada {jornada}",
         "destacado": "Celta Femxa Zorka", "_fecha": fecha.isoformat(), "filas": filas}
    ruta = os.path.join(a.salida, "clasificacion_baloncesto_fem.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print("escrito", ruta)


if __name__ == "__main__":
    main()
