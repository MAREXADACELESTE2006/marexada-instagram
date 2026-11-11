"""Marexada Celeste · noticias de ENTRADAS del Celta y del Celta Fortuna desde rccelta.es (v21).

Las noticias del club están en https://rccelta.es/club/actualidad/<nombre>/ (por ejemplo
https://rccelta.es/club/actualidad/entradas-celta-fortuna-real-valladolid/), pero la LISTA de noticias de esa página
se carga con JavaScript, así que el programa busca la lista de tres maneras, una detrás de otra:
  1. API de WordPress del club:   /wp-json/wp/v2/search?search=entradas   (busca en todas las noticias)
  2. Mapa del sitio (sitemap):    /wp-sitemap.xml  o  /sitemap_index.xml
  3. La propia página de actualidad y los enlaces «Noticias recomendadas» de cada noticia que ya se ha leído.
Se queda con las noticias de entradas (Celta y Celta Fortuna, no As Celtas ni femenino) de los últimos días, lee el
partido, la fecha y los puntos clave (venta, prioridad de carnés, precios) y escribe en la carpeta de salida:
    entradas_<nombre-de-la-noticia>.json      (como mucho las 3 más recientes)
El programa diario saca una historia por cada noticia nueva (la clave es el nombre de la noticia).

Uso:
    python entradas.py --hoy 2026-11-11                 (lee internet)
    python entradas.py --hoy 2026-11-11 --desde fixtures/entradas_RECONSTRUIDO --salida carpeta   (prueba sin internet)
Si no consigue ninguna lista guarda entradas_DEBUG.txt con lo que probó.
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser

import partemedico as pm                                  # reutiliza el conversor HTML -> líneas de texto
import rccelta                                            # nombre de equipo -> escudo

BASE = os.path.dirname(os.path.abspath(__file__))
RAIZ = "https://rccelta.es"
LISTAS = [RAIZ + "/club/actualidad/", RAIZ + "/gl/club/actualidad/"]
MAPAS = [RAIZ + "/wp-sitemap.xml", RAIZ + "/sitemap_index.xml", RAIZ + "/sitemap.xml"]
ENLACE = re.compile(r'(?:https?://rccelta\.es)?/(?:(?:gl|en)/)?club/actualidad/([a-z0-9][a-z0-9-]+)/?', re.I)
ENTRADA = re.compile(r"entrada", re.I)
EXCLUIR = re.compile(r"as-?celtas|femenin|canteira|juvenil|cadete|infantil|alev[ií]n|benjam[ií]n|abono|abonad", re.I)
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9,
         "octubre": 10, "noviembre": 11, "diciembre": 12, "xaneiro": 1, "febreiro": 2, "maio": 5, "xuño": 6, "xullo": 7, "setembro": 9,
         "outubro": 10, "novembro": 11, "decembro": 12, "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7,
         "september": 9, "october": 10, "november": 11, "december": 12}
DIAS = "lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo"
FECHA_HORA = re.compile(rf"\b({DIAS})\s+(\d{{1,2}})\s+de\s+([a-zñáéíóú]+)\s+a\s+las\s+(\d{{1,2}})[:.](\d{{2}})", re.I)
FECHA_NOTICIA = re.compile(r"^RC Celta\s+(\d{1,2})[-/ ]([A-Za-zñáéíóú]+)[-/ ](\d{4})", re.I)
CLAVES = re.compile(r"euros|€|prioridad|canje|carn[eé]|suplemento|a la venta|venta|localidades|entrada gratuita|abonad", re.I)
FIN_TEXTO = re.compile(r"^(etiquetas|noticias recomendadas|tags|s[ií]guenos)", re.I)


class _Bloques(HTMLParser):
    """HTML -> bloques de texto (párrafos, títulos, elementos de lista), con la etiqueta de cada uno."""
    BLOQUE = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "div", "section", "article", "header", "footer", "br", "tr", "td", "figure", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.bloques, self.buf, self.etq, self.saltar = [], [], "p", 0

    def _cerrar(self):
        t = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        if t:
            self.bloques.append((self.etq, t))
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.saltar += 1
        elif tag in self.BLOQUE:
            self._cerrar()
            self.etq = tag

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.saltar:
            self.saltar -= 1
        elif tag in self.BLOQUE:
            self._cerrar()

    def handle_data(self, data):
        if not self.saltar:
            self.buf.append(data)


def bloques_de(html):
    p = _Bloques()
    p.feed(html)
    p._cerrar()
    return p.bloques


DIA_GL = {"lunes": "luns", "martes": "martes", "miércoles": "mércores", "miercoles": "mércores", "jueves": "xoves", "viernes": "venres",
          "sábado": "sábado", "sabado": "sábado", "domingo": "domingo"}
CUANDO = rf"(?:el\s+)?({DIAS})\s+(\d{{1,2}})\s+de\s+([a-zñáéíóú]+)(?:\s+a\s+las\s+(\d{{1,2}}[:.]\d{{2}}))?"


def _cuando(m):
    """Grupo de CUANDO -> «xoves 12/11 ás 14:00 h»."""
    dia, d, mes, hora = m.group(1).lower(), int(m.group(2)), MESES.get(m.group(3).lower()), m.group(4)
    r = f"{DIA_GL.get(dia, dia)} {d}" + (f"/{mes:02d}" if mes else "")
    return r + (f" ás {hora.replace('.', ':')} h" if hora else "")


def descargar(url, desde=None):
    if desde:                                              # prueba sin internet: la URL se convierte en un archivo local
        nombre = re.sub(r"[^A-Za-z0-9_-]+", "_", url.rstrip("/").split("/")[-1]) or "indice"
        for ruta in (os.path.join(desde, nombre + ".html"), os.path.join(desde, nombre)):
            if os.path.exists(ruta):
                return open(ruta, encoding="utf-8").read()
        raise FileNotFoundError(nombre)
    req = urllib.request.Request(url, headers={"user-agent": "Mozilla/5.0 (compatible; MarexadaCeleste/1.0)", "accept-language": "es",
                                               "accept": "text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _nombre(url):
    m = ENLACE.search(url)
    return m.group(1).lower() if m else None


def descubrir(desde, traza):
    """Devuelve ([(nombre, url)], fuentes_que_respondieron). Las más recientes primero cuando la fuente lo permite."""
    vistos, lista, respondieron = set(), [], 0

    def poner(url):
        n = _nombre(url)
        if n and n not in vistos:
            vistos.add(n)
            lista.append((n, RAIZ + "/club/actualidad/" + n + "/"))

    if not desde:
        # 1) API de WordPress: busca «entradas» en todas las noticias (type=post, subtype = lo que sea)
        for termino in ("entradas", "entrada"):
            try:
                url = f"{RAIZ}/wp-json/wp/v2/search?search={termino}&per_page=100&_fields=id,title,url,subtype"
                filas = json.loads(descargar(url))
                respondieron += 1
                traza.append(f"API search '{termino}': {len(filas)} resultados")
                for f in sorted(filas, key=lambda f: -int(f.get("id", 0))):                  # id mayor = más reciente
                    if "/club/actualidad/" in (f.get("url") or ""):
                        poner(f["url"])
            except Exception as e:
                traza.append(f"API search '{termino}': {e}")
        # 2) mapa del sitio
        for mapa in MAPAS:
            try:
                xml = descargar(mapa)
                respondieron += 1
                hijos = [h for h in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml) if h.endswith(".xml")]
                traza.append(f"mapa {mapa}: {len(hijos)} mapas hijos")
                paginas = [(None, mapa, xml)] if not hijos else []
                for h in hijos[:12]:
                    if re.search(r"actualidad|post|noticia|club", h, re.I):
                        try:
                            paginas.append((None, h, descargar(h)))
                        except Exception as e:
                            traza.append(f"  {h}: {e}")
                filas = []
                for _, _, contenido in paginas:
                    for bloque in re.findall(r"<url>(.*?)</url>", contenido, re.S):
                        loc = re.search(r"<loc>\s*([^<\s]+)\s*</loc>", bloque)
                        mod = re.search(r"<lastmod>\s*([^<\s]+)\s*</lastmod>", bloque)
                        if loc and "/club/actualidad/" in loc.group(1):
                            filas.append((mod.group(1) if mod else "", loc.group(1)))
                traza.append(f"  noticias del club en el mapa: {len(filas)}")
                for _, u in sorted(filas, reverse=True):
                    poner(u)
                if filas:
                    break
            except Exception as e:
                traza.append(f"mapa {mapa}: {e}")
    # 3) la página de actualidad (si trae enlaces en el HTML)
    for pagina in (LISTAS if not desde else [RAIZ + "/club/actualidad/"]):
        try:
            html = descargar(pagina, desde)
            enlaces = [m.group(0) for m in ENLACE.finditer(html)]
            traza.append(f"lista {pagina}: {len(enlaces)} enlaces")
            if enlaces:
                respondieron += 1
            for e in enlaces:
                poner(e)
        except Exception as e:
            traza.append(f"lista {pagina}: {e}")
    return lista, respondieron


def _meta(html, prop):
    for rx in (rf'<meta[^>]+(?:property|name)="{prop}"[^>]+content="([^"]*)"', rf'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="{prop}"'):
        m = re.search(rx, html, re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    return None


def _fecha_noticia(lineas):
    for l in lineas:
        m = FECHA_NOTICIA.match(l)
        if m and m.group(2).lower() in MESES:
            return datetime.date(int(m.group(3)), MESES[m.group(2).lower()], int(m.group(1)))
    return None


def _limpia(t):
    return re.sub(r"\s+", " ", t.replace("\xa0", " ")).strip()


def _corta(t, n):
    t = _limpia(t)
    if len(t) <= n:
        return t
    return t[:n].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _lado(nombre_equipo):
    """(nombre para mostrar, escudo) de un lado del partido. El Celta y el Celta Fortuna llevan el escudo del Celta."""
    n = _limpia(nombre_equipo)
    if re.search(r"\bcelta\b", n, re.I) and not re.search(r"as celtas", n, re.I):
        return ("Celta Fortuna" if re.search(r"fortuna", n, re.I) else "Celta"), "celta-vigo"
    return n, rccelta.slug_equipo(n)


def articulo(html, nombre, hoy):
    """Lee una noticia. Devuelve un diccionario o None si no es de entradas de Celta/Fortuna."""
    titulo = _meta(html, "og:title") or ""
    lineas = pm.lineas_de(html)
    if not titulo:
        titulo = next((l for l in lineas if len(l) > 15), "")
    titulo = re.sub(r"\s*\|\s*Celta\s*$", "", titulo).strip()
    if not ENTRADA.search(titulo + " " + nombre) or EXCLUIR.search(nombre + " " + titulo):
        return None
    partes = [p.strip() for p in titulo.split("|")]
    partido = next((p for p in partes if re.search(r"\bcelta\b", p, re.I) and re.search(r"\s[-–—]\s", p)), None)
    if not partido:
        m = re.search(r"((?:Celta Fortuna|Celta|RC Celta)\s*[-–—]\s*[^|.,:;]+|[A-ZÁÉÍÓÚ][^|.,:;]+\s*[-–—]\s*(?:Celta Fortuna|Celta))", titulo)
        partido = m.group(1).strip() if m else None
    fecha = _fecha_noticia(lineas)
    # texto de la noticia: bloques entre la fecha de publicación y «Etiquetas / Noticias recomendadas»
    bl = bloques_de(html)
    ini = next((i for i, (_, t) in enumerate(bl) if re.search(r"RC Celta\s+\d{1,2}[-/ ][A-Za-zñáéíóú]+[-/ ]\d{4}", t)), None)
    cuerpo = []
    for etq, t in bl[(ini + 1) if ini is not None else 0:]:
        if FIN_TEXTO.match(t) or re.search(r"RC Celta\s+\d{1,2}[-/ ][A-Za-zñáéíóú]+[-/ ]\d{4}", t):
            break
        cuerpo.append((etq, t))
    parrafos = [t for e, t in cuerpo if not e.startswith("h") and len(t) > 25]
    texto = _limpia(" ".join(parrafos))
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚ¡¿0-9])", texto) if len(f.strip()) > 25]
    partido_dt, anio = None, (fecha or hoy).year
    for f in frases[:6]:
        m = FECHA_HORA.search(f)
        if m and re.search(r"disput|partido|encuentro|jornada|cita", f, re.I) and m.group(3).lower() in MESES:
            partido_dt = datetime.datetime(anio, MESES[m.group(3).lower()], int(m.group(2)), int(m.group(4)), int(m.group(5)))
            break
    jornada = re.search(r"Jornada\s+(\d{1,2})", texto, re.I)
    competicion = re.search(r"(LaLiga Hypermotion|LaLiga EA Sports|LaLiga|Europa League|Conference League|Copa del Rey|UEFA[^.,;]{0,25})", texto, re.I)
    # datos concretos (en gallego, cortos); si no se encuentran, frases sueltas con palabras clave
    puntos = []
    venta = next((f for f in frases if re.search(r"adquirir|a la venta|venta general|cualquier aficionado|p[uú]blico general", f, re.I) and re.search(r"desde el", f, re.I)), None)
    cu = re.search(r"desde\s+" + CUANDO, venta, re.I) if venta else None
    precio = re.search(r"(?:a partir de|desde)\s+(\d+(?:[.,]\d+)?)\s*(?:euros|€)", texto, re.I)
    if cu or precio:
        puntos.append("Venda xeral" + (f": dende o {_cuando(cu)}" if cu else "") + (f" · entradas dende {precio.group(1)} €" if precio else ""))
    pri = re.search(r"prioridad de\s+(\d+)\s*horas", texto, re.I)
    if re.search(r"carn[eé]s? celtistas?", texto, re.I) and (pri or re.search(r"entrada gratuita", texto, re.I)):
        puntos.append("Carné Celtista: " + ("entrada gratuíta" if re.search(r"entrada gratuita", texto, re.I) else "prioridade")
                      + (f", con prioridade exclusiva de {pri.group(1)} h" if pri else ""))
    canje = re.search(r"canje[^.]{0,80}?hasta\s+" + CUANDO, texto, re.I)
    if canje:
        puntos.append(f"Canxe de entradas ata o {_cuando(canje)}")
    if len(puntos) < 2:
        for f in frases[1:]:
            if CLAVES.search(f) and len(puntos) < 3 and _corta(f, 150) not in puntos:
                puntos.append(_corta(f, 150))
    if not (partido or puntos):
        return None
    lado = {}
    if partido:
        pp = re.split(r"\s+[-–—]\s+", partido, maxsplit=1)
        if len(pp) == 2:
            (ln, ls), (vn, vs) = _lado(pp[0]), _lado(pp[1])
            lado = {"local": ls, "visitante": vs, "local_nombre": ln, "visitante_nombre": vn}
            fuera = bool(re.search(r"celta", vn, re.I)) and not re.search(r"celta", ln, re.I)
            lado["visitantes"] = fuera or bool(re.search(r"visitante|desplazamiento", nombre + " " + titulo, re.I))
    return {"tipo": "entradas", "competicion": "liga", **lado, "tag": "CELTA FORTUNA" if re.search(r"fortuna", nombre + titulo, re.I) else "REAL CLUB CELTA",
            "nombre": nombre, "url": f"{RAIZ}/club/actualidad/{nombre}/", "titulo": titulo, "partido": partido, "publicada": fecha.isoformat() if fecha else None,
            "partido_fecha_hora": partido_dt.strftime("%Y-%m-%dT%H:%M") if partido_dt else None,
            "jornada": int(jornada.group(1)) if jornada else None, "torneo": competicion.group(1) if competicion else None,
            "intro": _corta(frases[0], 220) if frases else "", "puntos": puntos[:3]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hoy", default=datetime.date.today().isoformat())
    ap.add_argument("--desde", default=None, help="carpeta con copias HTML (prueba sin internet)")
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    ap.add_argument("--dias", type=int, default=8, help="solo noticias de los últimos N días")
    ap.add_argument("--max", type=int, default=3, help="como mucho N noticias")
    a = ap.parse_args()
    hoy = datetime.date.fromisoformat(a.hoy)
    os.makedirs(a.salida, exist_ok=True)
    traza = []
    lista, respondieron = descubrir(a.desde, traza)
    candidatas = [(n, u) for n, u in lista if ENTRADA.search(n) and not EXCLUIR.search(n)]
    traza.append(f"candidatas por el nombre: {len(candidatas)} de {len(lista)} enlaces")
    leidas, noticias, revisadas = set(), [], 0
    cola = candidatas[:10]
    while cola and revisadas < 20:
        nombre, url = cola.pop(0)
        if nombre in leidas:
            continue
        leidas.add(nombre)
        revisadas += 1
        try:
            html = descargar(url, a.desde)
        except Exception as e:
            traza.append(f"noticia {nombre}: {e}")
            continue
        for m in ENLACE.finditer(html):                       # «Noticias recomendadas»: puede haber otra noticia de entradas
            n2 = m.group(1).lower()
            if ENTRADA.search(n2) and not EXCLUIR.search(n2) and n2 not in leidas and (n2, RAIZ + "/club/actualidad/" + n2 + "/") not in cola and revisadas < 12:
                cola.append((n2, RAIZ + "/club/actualidad/" + n2 + "/"))
        d = articulo(html, nombre, hoy)
        if not d:
            continue
        if d["publicada"] and (hoy - datetime.date.fromisoformat(d["publicada"])).days > a.dias:
            continue
        if d["partido_fecha_hora"] and datetime.datetime.fromisoformat(d["partido_fecha_hora"]).date() < hoy:
            continue                                          # el partido ya se jugó
        noticias.append(d)
    if not respondieron and not noticias:
        with open(os.path.join(a.salida, "entradas_DEBUG.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(traza) + "\n")
        sys.exit("ERROR entradas: no consigo la lista de noticias del club (" + "; ".join(traza[-4:]) + ")")
    noticias.sort(key=lambda d: d["publicada"] or "", reverse=True)
    for viejo in os.listdir(a.salida):
        if re.fullmatch(r"entradas_.+\.json", viejo):
            os.remove(os.path.join(a.salida, viejo))
    for d in noticias[:a.max]:
        with open(os.path.join(a.salida, f"entradas_{d['nombre'][:60]}.json"), "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
    print(f"entradas: {len(noticias[:a.max])} noticia(s) ({'; '.join(traza[-3:])})")
    for d in noticias[:a.max]:
        print(f"  - {d['publicada']} {d['partido']} ({d['nombre']})")


if __name__ == "__main__":
    main()
