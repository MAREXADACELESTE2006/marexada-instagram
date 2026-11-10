"""Marexada Celeste · parte médico del Celta y del Celta Fortuna desde rccelta.es (v20).

Lee las páginas del parte médico del club (cada lesionado con su diagnóstico, fecha de lesión y observaciones):
    primer equipo  https://rccelta.es/equipos/primer-equipo/parte-medico/
    Celta Fortuna  https://rccelta.es/equipos/celta-fortuna/parte-medico/
y escribe en la carpeta de salida:
    partemedico_celta.json, partemedico_celta_2.json ...      (7 lesionados por imagen; si hay más, otra imagen)
    partemedico_fortuna.json, partemedico_fortuna_2.json ...
Cada JSON lleva una "firma": cambia cuando entra o sale alguien del parte o cambia un diagnóstico.
El programa diario la usa para sacar la historia solo cuando el parte cambia.

Uso:
    python partemedico.py                                   (lee internet)
    python partemedico.py --desde fixtures/partemedico_RECONSTRUIDO --salida carpeta   (prueba sin internet)
Si la página cambia y no se entiende, guarda lo recibido en partemedico_*_DEBUG.html para poder ajustarlo.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser

BASE = os.path.dirname(os.path.abspath(__file__))
EQUIPOS = {
    "celta": {"tag": "REAL CLUB CELTA", "urls": ["https://rccelta.es/equipos/primer-equipo/parte-medico/",
                                                   "https://rccelta.es/gl/equipos/primer-equipo/parte-medico/",
                                                   "https://rccelta.es/en/equipos/primer-equipo/parte-medico/"]},
    "fortuna": {"tag": "CELTA FORTUNA", "urls": ["https://rccelta.es/equipos/celta-fortuna/parte-medico/",
                                                   "https://rccelta.es/gl/equipos/celta-fortuna/parte-medico/",
                                                   "https://rccelta.es/en/equipos/celta-fortuna/parte-medico/"]},
}
POR_IMAGEN = 7
SALTAR = {"script", "style", "noscript", "svg", "button"}
ETIQUETAS = (("diagnostico", re.compile(r"^(diagn[oó]stic[oa]?|diagnosis)\W*$", re.I)), ("lugar", re.compile(r"^(lugar|place|location)\W*$", re.I)),
             ("tratamiento", re.compile(r"^(tratamiento|tratamento|treatment)\W*$", re.I)),
             ("observaciones", re.compile(r"^(observaciones|observaci[oó]ns|observacions|observations|remarks|notes)\W*$", re.I)))
INICIO = re.compile(r"^(lesionad[oa]s?|injured)\b", re.I)
FECHA = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{2,4})\b")
FINAL = re.compile(r"^(s[ií]guenos|follow us|first team|firts team|primer equipo|copyright|©)", re.I)
ACTUALIZADO = re.compile(r"[úu]ltima vez actualizad[oa]:?\s*(.*)", re.I)


class ErrorLector(Exception):
    pass


class _Texto(HTMLParser):
    """HTML -> lista de líneas de texto (un nodo de texto por línea)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lineas, self.saltar = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in SALTAR:
            self.saltar += 1

    def handle_endtag(self, tag):
        if tag in SALTAR and self.saltar:
            self.saltar -= 1

    def handle_data(self, data):
        if not self.saltar:
            t = re.sub(r"\s+", " ", data).strip()
            if t:
                self.lineas.append(t)


def lineas_de(html):
    p = _Texto()
    p.feed(html)
    return p.lineas


def _etiqueta(linea):
    for clave, rx in ETIQUETAS:
        if rx.match(linea):
            return clave
    return None


def leer_parte(html):
    """Devuelve (actualizado, [lesionados]). Lista vacía = el parte está vacío (la página se ve pero sin nadie).
    Si no parece la página del parte médico, lanza ErrorLector."""
    lineas = lineas_de(html)
    texto = "\n".join(lineas)
    actualizado = None
    for i, l in enumerate(lineas):
        m = ACTUALIZADO.search(l)
        if m:
            actualizado = m.group(1).strip() or (lineas[i + 1] if i + 1 < len(lineas) else None)
            if actualizado and not re.search(r"\d{4}", actualizado) and i + 1 < len(lineas):
                actualizado = f"{actualizado} {lineas[i + 1]}".strip()
            break
    inicios = []
    for i, l in enumerate(lineas):
        if INICIO.match(l) and i > 0:
            ventana = " ".join(lineas[i:i + 3])
            m = FECHA.search(ventana)
            if m and not _etiqueta(lineas[i - 1]) and not FECHA.search(lineas[i - 1]):
                inicios.append((i, m))
    if not inicios and actualizado is None and not re.search(r"parte m[eé]dico|medical (sheet|report)", texto, re.I):
        raise ErrorLector("no encuentro el parte médico en la página")
    if not inicios and actualizado is None:
        raise ErrorLector("la página no trae el parte médico (¿se carga con JavaScript?)")
    lesionados = []
    for k, (i, m) in enumerate(inicios):
        fin = (inicios[k + 1][0] - 1) if k + 1 < len(inicios) else len(lineas)
        campos, actual = {}, None
        for l in lineas[i + 1:fin]:
            if FINAL.match(l):
                break
            e = _etiqueta(l)
            if e:
                actual = e
                continue
            if re.match(r"^ver info", l, re.I) or FECHA.fullmatch(l) or INICIO.match(l):
                continue
            if actual and actual not in campos:
                campos[actual] = l                       # solo la primera línea de cada campo (evita arrastrar el pie de página)
        d, mes, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a += 2000 if a < 100 else 0
        lesionados.append({"nombre": lineas[i - 1], "fecha": f"{a:04d}-{mes:02d}-{d:02d}", "diagnostico": campos.get("diagnostico", ""),
                           "lugar": campos.get("lugar", ""), "tratamiento": campos.get("tratamiento", ""),
                           "observaciones": campos.get("observaciones", "")})
    return actualizado, lesionados


def firma(lesionados):
    base = "|".join(f"{x['nombre']}~{x['fecha']}~{x['diagnostico']}" for x in lesionados)
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]


def descargar(url, desde=None):
    if desde:
        nombre = re.sub(r"[^A-Za-z0-9_-]+", "_", "/".join(url.rstrip("/").split("/")[-2:]))
        for ruta in (os.path.join(desde, nombre + ".html"), os.path.join(desde, nombre)):
            if os.path.exists(ruta):
                return open(ruta, encoding="utf-8").read()
        raise FileNotFoundError(f"{nombre}.html (en {desde})")
    req = urllib.request.Request(url, headers={"user-agent": "Mozilla/5.0 (compatible; MarexadaCeleste/1.0)", "accept-language": "es"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", default=None, help="carpeta con copias HTML (prueba sin internet)")
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    a = ap.parse_args()
    os.makedirs(a.salida, exist_ok=True)
    fallos, hechos = [], 0
    for equipo, cfg in EQUIPOS.items():
        resultado, ultimo_html, motivo = None, None, None
        for url in cfg["urls"]:
            try:
                html = descargar(url, a.desde)
            except Exception as e:                       # sin conexión, 403, archivo que no existe...
                motivo = f"{url.split('rccelta.es')[-1]}: {e}"
                continue
            ultimo_html = html
            try:
                resultado = leer_parte(html)
                break
            except ErrorLector as e:
                motivo = f"{url.split('rccelta.es')[-1]}: {e}"
        if resultado is None:
            if ultimo_html:
                with open(os.path.join(a.salida, f"partemedico_{equipo}_DEBUG.html"), "w", encoding="utf-8") as f:
                    f.write(ultimo_html)
            fallos.append(f"{equipo}: {motivo}")
            continue
        actualizado, lesionados = resultado
        f = firma(lesionados)
        trozos = [lesionados[i:i + POR_IMAGEN] for i in range(0, len(lesionados), POR_IMAGEN)] or [[]]
        for viejo in os.listdir(a.salida):               # limpia páginas de una ejecución anterior
            if re.fullmatch(rf"partemedico_{equipo}(_\d+)?\.json", viejo):
                os.remove(os.path.join(a.salida, viejo))
        for n, trozo in enumerate(trozos, 1):
            datos = {"tipo": "partemedico", "competicion": "liga", "tag": cfg["tag"], "equipo": equipo, "actualizado": actualizado,
                     "pagina": f"{n}/{len(trozos)}" if len(trozos) > 1 else None, "n_total": len(lesionados), "firma": f, "lesionados": trozo}
            nombre = f"partemedico_{equipo}.json" if n == 1 else f"partemedico_{equipo}_{n}.json"
            with open(os.path.join(a.salida, nombre), "w", encoding="utf-8") as fh:
                json.dump(datos, fh, ensure_ascii=False, indent=1)
        hechos += 1
        print(f"{equipo}: {len(lesionados)} lesionados (actualizado: {actualizado}) -> {len(trozos)} imagen(es)")
    if fallos:
        print("; ".join(fallos), file=sys.stderr)
    if not hechos:
        sys.exit("ERROR parte médico: " + "; ".join(fallos))
    if fallos:
        sys.exit("Parte médico (parcial): " + "; ".join(fallos))


if __name__ == "__main__":
    main()
