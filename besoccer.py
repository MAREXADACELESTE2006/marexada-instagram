"""Marexada Celeste · lector de besoccer para el AS Celtas Fem (v7).

Lee dos páginas de besoccer (se ven como texto, sin JavaScript) y crea los JSON que entiende generar.py:
    clasificacion_as_celtas_fem.json   tabla completa del grupo
    resultado_as_celtas_fem.json       último partido jugado
    proximo_as_celtas_fem.json         próximo partido

Uso:
    python besoccer.py                                   (lee las dos páginas de internet, escribe en datos_reales/)
    python besoccer.py --clasif archivo.html --partidos archivo.html --hoy 2026-11-10 --salida datos_reales

Cada fuente puede ser una URL o un archivo local. Si la web cambia y no se encuentra algo, el programa
lo dice con un error claro en vez de inventar datos.
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser

BASE = os.path.dirname(os.path.abspath(__file__))
URL_CLASIF = "https://es.besoccer.com/equipo/clasificacion/ud-mos"
URL_PARTIDOS = "https://es.besoccer.com/equipo/partidos/ud-mos"
NUESTRO = "ud-mos"  # nombre interno en besoccer del AS Celtas Fem (era el equipo anterior)

# escudo del pack (assets/escudos/<slug>-logo-footylogos.png) para cada equipo de besoccer; los que no están salen con siglas
ESCUDO = {
    "ud-mos": "celta-vigo",                      # AS Celtas lleva el escudo del Celta
    "deportivo-abanca-femenino-b": "deportivo-la-coruna",
    "oviedo-moderno-femenino": "real-oviedo",
    "sporting-gijon-femenino": "sporting-gijon",
    "sd-eibar-femenino-b": "sd-eibar",
    "nuestra-senora-belen-femenino": "burgos-cf",
    "real-racing-femenino": "racing-santander",
    "cdf-osasuna-b-femenino": "osasuna",
    "rayo-vallecano-femenino": "rayo-vallecano",
}
MESES = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12}
DIA = ["Lun", "Mar", "Mér", "Xov", "Ven", "Sáb", "Dom"]  # lunes = 0


class ErrorLector(Exception):
    pass


# ---------------------------------------------------------------- lectura de la fuente
def leer(fuente):
    if re.match(r"https?://", fuente):
        req = urllib.request.Request(fuente, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "es-ES,es;q=0.9"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", errors="replace")
    with open(fuente, encoding="utf-8") as f:
        return f.read()


def limpio(t):
    return re.sub(r"\s+", " ", t or "").strip()


# ---------------------------------------------------------------- tablas y enlaces
class Lector(HTMLParser):
    """Recoge las filas de todas las tablas (texto y enlaces de cada celda) y los enlaces a partidos."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tablas, self.partidos = [], []
        self._tabla = self._fila = self._celda = self._enlace = None
        self._enlace_partido = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._tabla = []
        elif tag == "tr" and self._tabla is not None:
            self._fila = []
        elif tag in ("td", "th") and self._fila is not None:
            self._celda = {"texto": [], "enlaces": []}
        elif tag == "a" and a.get("href"):
            href = a["href"]
            if self._celda is not None and "/equipo/" in href:
                self._enlace = {"href": href, "texto": []}
            if "/partido/" in href:
                self._enlace_partido = {"href": href, "texto": []}
        elif tag == "img" and a.get("alt") is None:
            pass

    def handle_endtag(self, tag):
        if tag == "a":
            if self._enlace is not None and self._celda is not None:
                self._enlace["texto"] = limpio(" ".join(self._enlace["texto"]))
                self._celda["enlaces"].append(self._enlace)
            self._enlace = None
            if self._enlace_partido is not None:
                self.partidos.append({"href": self._enlace_partido["href"], "texto": limpio(" ".join(self._enlace_partido["texto"]))})
                self._enlace_partido = None
        elif tag in ("td", "th") and self._celda is not None:
            self._celda["texto"] = limpio(" ".join(self._celda["texto"]))
            self._fila.append(self._celda)
            self._celda = None
        elif tag == "tr" and self._fila is not None:
            if self._tabla is not None:
                self._tabla.append(self._fila)
            self._fila = None
        elif tag == "table" and self._tabla is not None:
            self.tablas.append(self._tabla)
            self._tabla = None

    def handle_data(self, data):
        if self._celda is not None:
            self._celda["texto"].append(data)
        if self._enlace is not None:
            self._enlace["texto"].append(data)
        if self._enlace_partido is not None:
            self._enlace_partido["texto"].append(data)


def entero(t):
    t = limpio(t).replace("+", "").replace("−", "-").replace("–", "-")
    return int(t) if re.fullmatch(r"-?\d+", t) else None


def nombre_corto(n):
    n = re.sub(r"(\s+[VED]){3,}$", "", limpio(n))     # por si la racha (V V E D) viniera dentro del enlace
    n = re.sub(r"\s+Fem$", "", n)
    return n


# ---------------------------------------------------------------- clasificación
def leer_clasificacion(html):
    p = Lector()
    p.feed(html)
    for tabla in p.tablas:                             # la primera tabla válida es la de «Total»
        filas = []
        for fila in tabla:
            if len(fila) < 10:
                continue
            nums = [entero(c["texto"]) for c in fila[-8:]]       # pts pj pg pe pp gf gc dg
            pos = entero(fila[0]["texto"])
            enlaces = [e for c in fila for e in c["enlaces"]]
            if pos is None or None in nums or not enlaces:
                continue
            pts, pj, pg, pe, pp, gf, gc, dg = nums
            slug = enlaces[0]["href"].rstrip("/").split("/")[-1]
            filas.append({"pos": pos, "slug": slug, "nombre": nombre_corto(enlaces[0]["texto"]),
                          "pts": pts, "pj": pj, "pg": pg, "pe": pe, "pp": pp, "gf": gf, "gc": gc, "dg": dg})
        if len(filas) >= 8:
            return filas
    raise ErrorLector("No encuentro la tabla de clasificación en la página (¿ha cambiado besoccer?).")


def datos_clasificacion(filas, subtitulo="Segunda Federación Femenina · Grupo 1"):
    return {
        "tipo": "clasificacion", "competicion": "liga", "tag": "AS CELTAS FEM",
        "subtitulo": subtitulo, "jornada": f"Xornada {max(f['pj'] for f in filas)}", "destacado": "AS Celtas",
        "filas": [{"pos": f["pos"], "nombre": f["nombre"], "escudo": ESCUDO.get(f["slug"]),
                   "pts": f["pts"], "pj": f["pj"], "dg": f["dg"]} for f in filas],
    }


# ---------------------------------------------------------------- partidos
def leer_partidos(html, hoy, nombres):
    p = Lector()
    p.feed(html)
    vistos, salida = set(), []
    for e in p.partidos:
        m = re.search(r"/partido/([^/]+)/([^/]+)/(\d+)", e["href"])
        if not m or m.group(3) in vistos or NUESTRO not in (m.group(1), m.group(2)):
            continue
        vistos.add(m.group(3))
        t = e["texto"]
        fecha = None
        for d in re.finditer(r"\b(\d{1,2})\s+(ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)\b\.?(?:\s+(\d{4}))?", t, re.I):
            fecha = d                                  # la fecha es lo último que aparece
        if not fecha:
            continue
        dia, mes, anio = int(fecha.group(1)), MESES[fecha.group(2).upper()], fecha.group(3)
        if anio:
            f = datetime.date(int(anio), mes, dia)
        else:                                          # sin año: el más cercano a hoy
            f = min((datetime.date(y, mes, dia) for y in (hoy.year - 1, hoy.year, hoy.year + 1)), key=lambda x: abs((x - hoy).days))
        resto = (t[:fecha.start()] + " " + t[fecha.end():])
        comp = re.match(r"\s*(?:FIN\s*)?([^.]+?)\.\s*", resto)
        competicion = comp.group(1).strip() if comp else ""
        ronda = re.search(r"Jornada\s*(\d+)|\b(\d+/\d+)\b", resto)
        etapa = (f"Xornada {ronda.group(1)}" if ronda and ronda.group(1) else (ronda.group(2) if ronda else ""))
        sin_ronda = re.sub(r"Jornada\s*\d+|\b\d+/\d+\b", " ", resto[comp.end():] if comp else resto)
        hora = re.search(r"\b(\d{1,2}:\d{2})\b", sin_ronda)
        gl = gv = pen = None
        mp = re.search(r"(\d+)\s*\((\d+)\s*-\s*(\d+)\)\s*(\d+)", sin_ronda)
        ms = re.search(r"(?<![\d/:])(\d+)\s*-\s*(\d+)(?![\d/:])", sin_ronda)
        if mp:
            gl, gv, pen = int(mp.group(1)), int(mp.group(4)), f"{mp.group(2)}-{mp.group(3)}"
        elif ms:
            gl, gv = int(ms.group(1)), int(ms.group(2))
        salida.append({"id": m.group(3), "local": m.group(1), "visitante": m.group(2), "fecha": f,
                       "hora": hora.group(1) if hora else None, "competicion": competicion, "etapa": etapa,
                       "goles_local": gl, "goles_visitante": gv, "penaltis": pen, "jugado": gl is not None})
    if not salida:
        raise ErrorLector("No encuentro ningún partido del AS Celtas Fem en la página (¿ha cambiado besoccer?).")
    return sorted(salida, key=lambda x: x["fecha"])


def nombre_de(slug, nombres):
    if slug == NUESTRO:
        return "AS Celtas"
    if slug in nombres:
        return nombres[slug]
    return re.sub(r"-(femenino|b)?$", "", slug).replace("-", " ").title()


def etiqueta_ronda(pt):
    if pt["competicion"].startswith("Segunda Federación"):
        return pt["etapa"]
    if pt["competicion"].startswith("Copa de la Reina"):
        return f"Copa da Raíña · {pt['etapa']}".strip(" ·")
    return f"{pt['competicion']} · {pt['etapa']}".strip(" ·")


def datos_partido(pt, tipo, nombres):
    d = {
        "tipo": tipo, "competicion": "liga", "tag": "AS CELTAS FEM",
        "local": ESCUDO.get(pt["local"], pt["local"]), "visitante": ESCUDO.get(pt["visitante"], pt["visitante"]),
        "local_nombre": nombre_de(pt["local"], nombres), "visitante_nombre": nombre_de(pt["visitante"], nombres),
        "jornada": etiqueta_ronda(pt), "_fecha": pt["fecha"].isoformat(),
        "fecha_hora": f"{DIA[pt['fecha'].weekday()]} {pt['fecha'].day:02d}/{pt['fecha'].month:02d}" + (f" · {pt['hora']}" if pt["hora"] and tipo == "proximo" else ""),
    }
    if tipo == "resultado":
        d.update(goles_local=pt["goles_local"], goles_visitante=pt["goles_visitante"],
                 goleadores_local=[f"Penaltis {pt['penaltis']}"] if pt["penaltis"] else [], goleadores_visitante=[])
    return d


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clasif", default=URL_CLASIF)
    ap.add_argument("--partidos", default=URL_PARTIDOS)
    ap.add_argument("--hoy", default=None, help="fecha AAAA-MM-DD (por defecto, hoy)")
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    a = ap.parse_args()
    hoy = datetime.date.fromisoformat(a.hoy) if a.hoy else datetime.date.today()
    os.makedirs(a.salida, exist_ok=True)

    filas = leer_clasificacion(leer(a.clasif))
    nombres = {f["slug"]: f["nombre"] for f in filas}
    partidos = leer_partidos(leer(a.partidos), hoy, nombres)

    def guardar(nombre, datos):
        ruta = os.path.join(a.salida, nombre)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
        print("escrito", ruta)

    guardar("clasificacion_as_celtas_fem.json", datos_clasificacion(filas))
    jugados = [p for p in partidos if p["jugado"] and p["fecha"] <= hoy]
    futuros = [p for p in partidos if not p["jugado"] and p["fecha"] >= hoy]
    if jugados:
        guardar("resultado_as_celtas_fem.json", datos_partido(jugados[-1], "resultado", nombres))
    else:
        print("aviso: no hay partidos jugados", file=sys.stderr)
    if futuros:
        guardar("proximo_as_celtas_fem.json", datos_partido(futuros[0], "proximo", nombres))
    else:
        print("aviso: no hay próximos partidos", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except ErrorLector as e:
        sys.exit(f"ERROR: {e}")
