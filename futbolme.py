"""Marexada Celeste · AS Celtas Fem desde futbolme.com (v19).

Lee dos páginas públicas de futbolme.com del equipo "RC Celta de Vigo - Senior Femenino"
(en el programa lo llamamos AS Celtas) y escribe en datos_reales/ (o en --salida):
    clasificacion_as_celtas_fem.json   (jueves)
    resultado_as_celtas_fem.json       (último partido jugado)
    proximo_as_celtas_fem.json         (próximo partido)

Uso:
    python futbolme.py                                   (lee internet)
    python futbolme.py --clasif a.html --calendario b.html --hoy 2026-11-10 --salida carpeta   (prueba sin internet)
Si la página cambia y no se entiende, guarda lo recibido en futbolme_*_DEBUG.html para poder ajustarlo.
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
URL_CLASIF = "https://futbolme.com/resultados-directo/equipo/rc-celta-de-vigo/51793/clasificacion/"
URL_CALENDARIO = "https://futbolme.com/resultados-directo/equipo/rc-celta-de-vigo/51793/calendario"
SUBTITULO = "Segunda Federación Femenina · Grupo 1"
DIA = ["Lun", "Mar", "Mér", "Xov", "Ven", "Sáb", "Dom"]

# (palabra clave, nombre que se ve, escudo). El orden importa: la primera que encaje gana.
EQUIPOS = [
    (r"deportivo.*coru", "Deportivo Abanca B", "deportivo-la-coruna"),
    (r"^deportivo b|deportivo b$", "Deportivo Abanca B", "deportivo-la-coruna"),
    (r"oviedo", "Real Oviedo", "real-oviedo"),
    (r"sporting", "Real Sporting", "sporting-gijon"),
    (r"eibar", "Eibar B", "sd-eibar"),
    (r"avil", "Real Avilés", None),
    (r"celta", "AS Celtas", "celta-vigo"),
    (r"burgos", "Burgos CF", "burgos-cf"),
    (r"racing", "Racing", "racing-santander"),
    (r"arratia", "CD Arratia", None),
    (r"osasuna", "Osasuna B", "osasuna"),
    (r"bizkerre", "Club Bizkerre", None),
    (r"victoria", "Victoria CF", None),
    (r"vallecano", "Rayo Vallecano", "rayo-vallecano"),
    (r"madrid cff", "Madrid CFF B", None),
]


class ErrorLector(Exception):
    pass


def leer(fuente):
    if re.match(r"https?://", fuente):
        req = urllib.request.Request(fuente, headers={
            "User-Agent": "Mozilla/5.0 (compatible; MarexadaCeleste/1.0)",
            "Accept": "text/html,application/xhtml+xml", "Accept-Language": "es-ES,es;q=0.9"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", errors="replace")
    with open(fuente, encoding="utf-8") as f:
        return f.read()


def limpio(t):
    return re.sub(r"\s+", " ", t or "").strip()


def equipo(txt):
    """Nombre (corto o largo, como salga en futbolme) -> (nombre que se ve, escudo)."""
    t = limpio(txt).lower()
    for patron, nombre, escudo in EQUIPOS:
        if re.search(patron, t):
            return nombre, escudo
    try:
        import rccelta
        escudo = rccelta.slug_equipo(limpio(txt))
    except Exception:
        escudo = None
    return limpio(txt), escudo


# ---------------------------------------------------------------- clasificación
class Tablas(HTMLParser):
    """Filas de las tablas: lista de celdas con su texto y el atributo title/alt de lo que lleven dentro."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.filas, self._fila, self._celda = [], None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tr":
            self._fila = []
        elif tag in ("td", "th") and self._fila is not None:
            self._celda = {"texto": "", "extra": []}
        elif self._celda is not None:
            for k in ("title", "alt"):
                if a.get(k):
                    self._celda["extra"].append(a[k])

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._celda is not None and self._fila is not None:
            self._celda["texto"] = limpio(self._celda["texto"])
            self._fila.append(self._celda)
            self._celda = None
        elif tag == "tr" and self._fila is not None:
            self.filas.append(self._fila)
            self._fila = None

    def handle_data(self, d):
        if self._celda is not None:
            self._celda["texto"] += d


def entero(t):
    m = re.search(r"-?\d+", (t or "").replace("−", "-"))
    return int(m.group()) if m else None


def leer_clasificacion(html):
    p = Tablas()
    p.feed(html)
    filas = []
    for fila in p.filas:
        if len(fila) < 9:
            continue
        pos, pts, pj, dg = (entero(fila[0]["texto"]), entero(fila[2]["texto"]), entero(fila[3]["texto"]), entero(fila[-1]["texto"]))
        if None in (pos, pts, pj, dg) or not fila[1]["texto"]:
            continue
        txt = " ".join([fila[1]["texto"]] + fila[1]["extra"])
        nombre, escudo = equipo(txt)
        filas.append({"pos": pos, "nombre": nombre, "escudo": escudo, "pts": pts, "pj": pj, "dg": dg})
    if len(filas) < 8:
        raise ErrorLector("No encuentro la tabla de clasificación en futbolme (¿ha cambiado la página?).")
    filas.sort(key=lambda f: f["pos"])
    return filas


def datos_clasificacion(filas):
    return {"tipo": "clasificacion", "competicion": "liga", "tag": "AS CELTAS FEM", "subtitulo": SUBTITULO,
            "jornada": f"Xornada {max(f['pj'] for f in filas)}", "destacado": "AS Celtas", "filas": filas}


# ---------------------------------------------------------------- calendario
PATRON = re.compile(
    r"(?P<fecha>(?<!\d)\d{2}/\d{2}/\d{2}(?!\d))"
    r"|(?P<jor>Jornada\s+(?P<njor>\d+))"
    r"|Partido entre (?P<l>[^\"<>]+?) y (?P<v>[^\"<>]+?)[\"<]"
    r"|>\s*(?P<gl>\d{1,2})\s*(?:<[^>]*>\s*)*-\s*(?:<[^>]*>\s*)*(?P<gv>\d{1,2})\s*<"
    r"|>\s*(?P<hora>\d{1,2}:\d{2})\s*<", re.I)


def leer_calendario(html):
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    partidos, cur = [], None
    for m in PATRON.finditer(html):
        if m.group("fecha"):
            d, mo, a = (int(x) for x in m.group("fecha").split("/"))
            cur = {"fecha": datetime.date(2000 + a, mo, d), "jornada": None, "local": None, "visitante": None,
                   "goles": None, "hora": None}
            partidos.append(cur)
        elif cur is None:
            continue
        elif m.group("njor"):
            cur["jornada"] = cur["jornada"] or int(m.group("njor"))
        elif m.group("l"):
            if cur["local"] is None:
                cur["local"], cur["visitante"] = limpio(m.group("l")), limpio(m.group("v"))
        elif m.group("gl") is not None and cur["local"] and cur["goles"] is None and cur["hora"] is None:
            cur["goles"] = (int(m.group("gl")), int(m.group("gv")))
        elif m.group("hora") and cur["local"] and cur["goles"] is None and cur["hora"] is None:
            cur["hora"] = m.group("hora")
    partidos = [p for p in partidos if p["local"] and p["visitante"]]
    if len(partidos) < 5:
        raise ErrorLector("No encuentro el calendario en futbolme (¿ha cambiado la página?).")
    return partidos


def datos_partido(p, tipo):
    ln, le = equipo(p["local"])
    vn, ve = equipo(p["visitante"])
    f = p["fecha"]
    d = {"tipo": tipo, "competicion": "liga", "tag": "AS CELTAS FEM", "local": le, "visitante": ve,
         "local_nombre": ln, "visitante_nombre": vn, "jornada": f"Xornada {p['jornada']}" if p["jornada"] else "",
         "_fecha": f.isoformat(),
         "fecha_hora": f"{DIA[f.weekday()]} {f.day:02d}/{f.month:02d}" + (f" · {p['hora']}" if tipo == "proximo" and p["hora"] else "")}
    if tipo == "resultado":
        d.update(goles_local=p["goles"][0], goles_visitante=p["goles"][1], goleadores_local=[], goleadores_visitante=[])
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clasif", default=URL_CLASIF)
    ap.add_argument("--calendario", default=URL_CALENDARIO)
    ap.add_argument("--hoy", default=None, help="fecha AAAA-MM-DD (por defecto, hoy)")
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    a = ap.parse_args()
    hoy = datetime.date.fromisoformat(a.hoy) if a.hoy else datetime.date.today()
    os.makedirs(a.salida, exist_ok=True)

    def guardar(nombre, datos):
        ruta = os.path.join(a.salida, nombre)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
        print("escrito", ruta)

    def con_debug(nombre, html, funcion):
        try:
            return funcion(html)
        except ErrorLector:
            with open(os.path.join(a.salida, f"futbolme_{nombre}_DEBUG.html"), "w", encoding="utf-8") as f:
                f.write(html)
            print(f"aviso: guardada futbolme_{nombre}_DEBUG.html ({len(html)} caracteres)", file=sys.stderr)
            raise

    filas = con_debug("clasif", leer(a.clasif), leer_clasificacion)
    guardar("clasificacion_as_celtas_fem.json", datos_clasificacion(filas))
    partidos = con_debug("calendario", leer(a.calendario), leer_calendario)
    jugados = [p for p in partidos if p["goles"] and p["fecha"] <= hoy]
    futuros = [p for p in partidos if not p["goles"] and p["fecha"] >= hoy]
    if jugados:
        guardar("resultado_as_celtas_fem.json", datos_partido(jugados[-1], "resultado"))
    else:
        print("aviso: no hay partidos jugados", file=sys.stderr)
    if futuros:
        guardar("proximo_as_celtas_fem.json", datos_partido(futuros[0], "proximo"))
    else:
        print("aviso: no hay próximos partidos", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except ErrorLector as e:
        sys.exit(f"ERROR: {e}")
