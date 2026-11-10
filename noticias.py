"""Marexada Celeste · convocatorias y crónicas desde rccelta.es (v13).

1. Abre las páginas de categoría de noticias de rccelta.es (se ven como HTML normal, la lista de noticias viene dentro):
     primer equipo  https://rccelta.es/categorias-actualidad-equipo/primer-equipo/
     Celta Fortuna  https://rccelta.es/categorias-actualidad-fundacion/celta-fortuna/      (sin comprobar)
2. De cada lista toma las noticias candidatas (título de convocatoria o de crónica con marcador) y descarga solo esas.
3. rccelta.py las convierte en datos (convocados y bajas / marcador, goles y alineaciones) y se guardan en datos_reales/:
     convocatoria_celta.json  cronica_celta.json  convocatoria_fortuna.json  cronica_fortuna.json   (la más reciente de cada tipo)

Uso:
    python noticias.py                              (lee internet)
    python noticias.py --desde fixtures/rccelta_web_RECONSTRUIDO     (prueba sin internet)
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser

import rccelta

BASE = os.path.dirname(os.path.abspath(__file__))
CATEGORIAS = {
    "celta": ["https://rccelta.es/categorias-actualidad-equipo/primer-equipo/"],
    "fortuna": ["https://rccelta.es/categorias-actualidad-fundacion/celta-fortuna/", "https://rccelta.es/fundacion/actualidad/"],
}
MAX_NOTICIAS = 12                       # cuántas noticias de cada lista se miran
CANDIDATA = re.compile(r"^Convocatoria del Celta|\d+\s*[-–]\s*\d+", re.I)   # título de convocatoria o con marcador
BASURA = re.compile(r"^(continued|seguir leyendo|ler m[aá]is|leer m[aá]s|read more|m[aá]s|ver m[aá]s)\W*$", re.I)
ENLACE = re.compile(r'<a\b[^>]*?href="([^"]*?/(?:equipo|fundacion)/actualidad/[^"/]+/?)"[^>]*>(.*?)</a>', re.I | re.S)
SALTAR = {"script", "style", "nav", "header", "footer", "aside", "noscript", "form", "button", "svg"}


def descargar(url, desde=None):
    if desde:                                          # prueba sin internet: la URL se convierte en un archivo local
        nombre = re.sub(r"[^A-Za-z0-9_-]+", "_", url.rstrip("/").split("/")[-1]) or "indice"
        for ruta in (os.path.join(desde, nombre + ".html"), os.path.join(desde, nombre)):
            if os.path.exists(ruta):
                return open(ruta, encoding="utf-8").read()
        raise FileNotFoundError(f"{nombre}.html (en {desde})")
    req = urllib.request.Request(url, headers={"user-agent": "Mozilla/5.0 (compatible; MarexadaCeleste/1.0)", "accept-language": "es"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def sin_etiquetas(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()


def listar(html):
    """Noticias de una página de categoría: [(url, título)] en el orden de la página, sin repetir."""
    vistas, out = set(), []
    for url, interior in ENLACE.findall(html):
        titulo = sin_etiquetas(interior)
        if not titulo or BASURA.match(titulo) or url in vistas:
            continue
        vistas.add(url)
        out.append((url, titulo))
    return out


class Cuerpo(HTMLParser):
    """Saca el título (h1) y el texto de una noticia, línea por línea, sin menús ni pie."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titulo, self.lineas = "", []
        self._h1 = False
        self._saltar = 0
        self._buf = []
        self._tras_h1 = False

    def _cortar(self):
        t = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        if t and self._tras_h1:
            self.lineas.append(t)
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag in SALTAR:
            self._saltar += 1
        elif tag == "h1" and not self.titulo:
            self._h1 = True
        elif tag in ("p", "div", "li", "h2", "h3", "h4", "br", "tr", "section", "article"):
            self._cortar()

    def handle_endtag(self, tag):
        if tag in SALTAR:
            self._saltar = max(0, self._saltar - 1)
        elif tag == "h1" and self._h1:
            self._h1 = False
            self._tras_h1 = True
        elif tag in ("p", "div", "li", "h2", "h3", "h4", "tr", "section", "article"):
            self._cortar()

    def handle_data(self, data):
        if self._saltar:
            return
        if self._h1:
            self.titulo += data
        else:
            self._buf.append(data)


def articulo(html):
    p = Cuerpo()
    p.feed(html)
    p._cortar()
    titulo = re.sub(r"\s+", " ", p.titulo).strip()
    return titulo, "\n".join(p.lineas)


def fecha_iso(texto):
    m = re.search(r"RC Celta\s+(\d{1,2})-(\w+)-(\d{4})", texto)
    if m and rccelta.MESES.get(m.group(2).lower()):
        return datetime.date(int(m.group(3)), rccelta.MESES[m.group(2).lower()], int(m.group(1))).isoformat()
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", default=None, help="carpeta con copias HTML (prueba sin internet)")
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    a = ap.parse_args()
    os.makedirs(a.salida, exist_ok=True)
    avisos, escritos = [], 0
    for equipo, urls in CATEGORIAS.items():
        lista = []
        for u in urls:
            try:
                lista = listar(descargar(u, a.desde))
            except Exception as e:
                avisos.append(f"{equipo}: no se pudo abrir {u} ({e})")
                continue
            if lista:
                break
        if not lista:
            avisos.append(f"{equipo}: no se encontraron noticias en la lista (¿ha cambiado la web?)")
            continue
        hecho = set()
        for url, titulo_lista in lista[:MAX_NOTICIAS]:
            if not CANDIDATA.search(titulo_lista):
                continue
            try:
                titulo, texto = articulo(descargar(url, a.desde))
                tipo, datos = rccelta.articulo_a_datos(titulo or titulo_lista, texto)
            except Exception as e:
                avisos.append(f"{equipo}: error leyendo «{titulo_lista}»: {e}")
                continue
            clave = "cronica" if tipo == "resultado" else tipo
            if tipo not in ("convocatoria", "resultado") or clave in hecho:
                continue
            if not datos:
                avisos.append(f"{equipo}: no se pudo interpretar «{titulo_lista}» (formato nuevo)")
                continue
            hecho.add(clave)
            datos["_url"] = url
            datos["_fecha"] = fecha_iso(texto)
            ruta = os.path.join(a.salida, f"{clave}_{equipo}.json")
            json.dump(datos, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("escrito", ruta, "<-", titulo_lista)
            escritos += 1
    for x in avisos:
        print("aviso:", x, file=sys.stderr)
    if not escritos and avisos:
        sys.exit("ERROR: " + avisos[0])


if __name__ == "__main__":
    main()
