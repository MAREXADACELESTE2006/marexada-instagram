"""Convierte el Excel del Almanaque Celta (hoja «Publicaciones miércoles» / «Publicacións do mércores», en español o en gallego) en assets/almanaque.json.

Solo hace falta usarlo en tu ordenador cuando cambies el Excel (necesita:  pip install openpyxl).
El programa diario NO lee el Excel: lee assets/almanaque.json.

Uso:  python convertir_almanaque.py RUTA_DEL_EXCEL.xlsx
"""
import datetime
import json
import os
import sys

import openpyxl

COLS = {  # clave del json -> posibles nombres de la columna (español / gallego)
    "fecha": ("Fecha de publicación (miércoles)", "Data de publicación (mércores)"),
    "inicio": ("Inicio de semana",), "fin": ("Fin de semana",),
    "fecha_historica": ("Fecha histórica original", "Data histórica orixinal"),
    "categoria": ("Categoría",), "tipo": ("Tipo de contenido", "Tipo de contido"),
    "titular": ("Titular",), "s1": ("Story 1 · Gancho",), "s2": ("Story 2 · Datos",), "s3": ("Story 3 · Cierre", "Story 3 · Peche"),
    "dato": ("Dato histórico principal",), "protagonistas": ("Protagonistas",),
    "pregunta": ("Pregunta / interacción",), "hashtags": ("Hashtags",),
    "fuente": ("Fuente documental", "Fonte documental"), "precision": ("Precisión / contexto",),
}


def main(ruta):
    wb = openpyxl.load_workbook(ruta, data_only=True)
    hoja = next((n for n in wb.sheetnames if n.lower().startswith("publicaci")), None)      # «Publicaciones miércoles» / «Publicacións do mércores»
    if not hoja:
        sys.exit("No encuentro la hoja de publicaciones (debe empezar por «Publicaci...»).")
    filas = list(wb[hoja].iter_rows(values_only=True))
    cab = {c: i for i, c in enumerate(filas[0])}
    idx = {}
    for clave, nombres in COLS.items():
        col = next((n for n in nombres if n in cab), None)
        if col is None:
            if clave in ("fecha", "fecha_historica", "titular", "s1", "s2", "s3"):
                sys.exit(f"Falta la columna de «{clave}» en el Excel (se buscaba: {' / '.join(nombres)}).")
            continue
        idx[clave] = cab[col]
    salida = []
    for f in filas[1:]:
        if not f[idx["titular"]]:
            continue
        e = {}
        for clave in COLS:
            v = f[idx[clave]] if clave in idx else None
            if isinstance(v, (datetime.datetime, datetime.date)):
                v = v.strftime("%Y-%m-%d")
            e[clave] = (str(v).strip() if v is not None else "")
        salida.append(e)
    salida.sort(key=lambda e: e["fecha"])
    destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "almanaque.json")
    json.dump(salida, open(destino, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{len(salida)} publicaciones -> {destino} ({os.path.getsize(destino) // 1024} KB). Primera: {salida[0]['fecha']}, última: {salida[-1]['fecha']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
