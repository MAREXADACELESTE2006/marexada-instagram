"""Convierte el Excel del Almanaque Celta (hoja «Publicaciones miércoles») en assets/almanaque.json.

Solo hace falta usarlo en tu ordenador cuando cambies el Excel (necesita:  pip install openpyxl).
El programa diario NO lee el Excel: lee assets/almanaque.json.

Uso:  python convertir_almanaque.py RUTA_DEL_EXCEL.xlsx
"""
import datetime
import json
import os
import sys

import openpyxl

COLS = {  # columna del Excel -> clave del json
    "Fecha de publicación (miércoles)": "fecha", "Inicio de semana": "inicio", "Fin de semana": "fin",
    "Fecha histórica original": "fecha_historica", "Categoría": "categoria", "Tipo de contenido": "tipo",
    "Titular": "titular", "Story 1 · Gancho": "s1", "Story 2 · Datos": "s2", "Story 3 · Cierre": "s3",
    "Dato histórico principal": "dato", "Protagonistas": "protagonistas", "Pregunta / interacción": "pregunta",
    "Hashtags": "hashtags", "Fuente documental": "fuente", "Precisión / contexto": "precision",
}


def main(ruta):
    ws = openpyxl.load_workbook(ruta, data_only=True)["Publicaciones miércoles"]
    filas = list(ws.iter_rows(values_only=True))
    cab = {c: i for i, c in enumerate(filas[0])}
    salida = []
    for f in filas[1:]:
        if not f[cab["Titular"]]:
            continue
        e = {}
        for col, clave in COLS.items():
            v = f[cab[col]]
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
