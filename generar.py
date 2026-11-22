"""Marexada Celeste · generador de publicaciones de partido (v2)

Uso:
    python generar.py datos_ejemplo/convocatoria_celta_osasuna.json [salida.png]
    python generar.py            (genera todos los ejemplos en ejemplos/)

Cada JSON lleva "tipo": convocatoria | alineacion | resultado.
"""
import glob
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

import generar_historia as HISTORIA

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")
W, H = 1080, 1350
WHITE = (255, 255, 255)
SOFT = (200, 215, 235)
F = os.path.join(ASSETS, "fuentes", "Poppins-")

THEMES = {
    "liga": dict(top=(10, 31, 60), bot=(18, 58, 115), accent=(138, 198, 240), card=(8, 24, 48),
                 tag="PARTIDO", photo=os.path.join(ASSETS, "fondos", "balaidos_liga.jpeg")),
    "europa": dict(top=(8, 8, 12), bot=(34, 18, 8), accent=(255, 132, 24), card=(14, 12, 14),
                   tag="EUROPA LEAGUE", photo=os.path.join(ASSETS, "fondos", "europa_league.webp")),
}
T = THEMES["liga"]
EQUIPOS = json.load(open(os.path.join(ASSETS, "equipos.json"), encoding="utf-8"))


# ---------------------------------------------------------------- utilidades
def font(weight, size):
    return ImageFont.truetype(F + weight + ".ttf", int(size))


def fit(d, text, weight, size, maxw, minsize=14):
    """Fuente que hace caber el texto en maxw píxeles."""
    size = int(size)
    f = font(weight, size)
    while size > minsize and d.textlength(text, font=f) > maxw:
        size -= 1
        f = font(weight, size)
    return f


def center(d, y, text, f, fill=WHITE, x=W // 2):
    w = d.textlength(text, font=f)
    d.text((x - w / 2, y), text, font=f, fill=fill)


def corto(slug):
    return EQUIPOS.get(slug, {}).get("corto", slug.replace("-", " ").upper())


def jugador(j):
    """Acepta 'Nombre' o {'dorsal': 9, 'nombre': 'Nombre'} -> (dorsal|None, nombre)."""
    if isinstance(j, str):
        return None, j
    d = j.get("dorsal")
    return (f"{d:02d}" if isinstance(d, int) else (str(d) if d else None)), j["nombre"]


# ---------------------------------------------------------------- piezas comunes
def background():
    img = Image.new("RGB", (W, H), T["top"])
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(T["top"][i] + (T["bot"][i] - T["top"][i]) * t) for i in range(3)))
    ph = Image.open(T["photo"]).convert("RGB")
    if T is THEMES["europa"]:
        ph = ph.crop((0, 0, 1400, 830)).resize((W, 640), Image.LANCZOS)  # trofeo a la derecha
        blend = 0.28
    else:
        ph = ph.crop((0, 298, ph.width, 500))  # banderas y bufandas, sin rótulos
        k = 480 / ph.height
        ph = ph.resize((int(ph.width * k), 480), Image.LANCZOS)
        ox = (ph.width - W) // 2
        ph = ph.crop((ox, 0, ox + W, 480))
        blend = 0.42
    ph = Image.blend(ph, Image.new("RGB", ph.size, T["top"]), blend)
    mask = Image.new("L", ph.size, 255)
    md = ImageDraw.Draw(mask)
    for y in range(ph.height):
        md.line([(0, y), (W, y)], fill=int(255 * max(0, 1 - (y / ph.height) ** 1.6)))
    img.paste(ph, (0, 0), mask)
    return img


def header_footer(d, datos):
    A = T["accent"]
    d.rectangle([0, 0, W, 8], fill=A)
    f34 = font("Bold", 34)
    d.text((60, 44), "MAREXADA", font=f34, fill=WHITE)
    d.text((60 + d.textlength("MAREXADA ", font=f34), 44), "CELESTE", font=f34, fill=A)
    d.text((60, 90), "Peña celtista · Dende 2006", font=font("Regular", 22), fill=SOFT)
    tag = datos.get("tag") or T["tag"]
    w = d.textlength(tag, font=font("Bold", 24))
    d.rounded_rectangle([W - 60 - w - 40, 46, W - 60, 100], 27, fill=A)
    d.text((W - 60 - w - 20, 56), tag, font=font("Bold", 24), fill=(10, 10, 14))
    d.line([(60, H - 120), (W - 60, H - 120)], fill=A, width=2)
    d.text((60, H - 95), "@marexadaceleste", font=font("Medium", 28), fill=WHITE)
    t = "Faite socio/a  »"
    d.text((W - 60 - d.textlength(t, font=font("Bold", 28)), H - 95), t, font=font("Bold", 28), fill=A)


def crest(img, cx, cy, r, slug):
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 250, 252), outline=T["accent"], width=5)
    m = glob.glob(os.path.join(ASSETS, "escudos", f"{slug}-logo-footylogos.png"))
    if m:
        c = Image.open(m[0]).convert("RGBA")
        c = c.crop(c.getbbox())  # quita el margen transparente
        box = int(r * 1.5)
        k = min(box / c.width, box / c.height)
        c = c.resize((max(1, int(c.width * k)), max(1, int(c.height * k))), Image.LANCZOS)
        img.paste(c, (cx - c.width // 2, cy - c.height // 2), c)
    else:  # sin escudo: siglas del club
        t = corto(slug)[:3]
        center(d, cy - r * 0.3, t, font("Bold", r * 0.6), fill=(10, 20, 40), x=cx)


def match_line(img, d, y, datos):
    crest(img, 300, y + 70, 72, datos["local"])
    center(d, y + 30, "VS", font("Bold", 56), fill=T["accent"])
    crest(img, 780, y + 70, 72, datos["visitante"])


def subtitulo(d, y, datos):
    t = " · ".join(str(datos[k]) for k in ("jornada", "lugar", "fecha_hora") if datos.get(k))
    if t:
        center(d, y, t, fit(d, t, "Medium", 30, W - 120), fill=SOFT)


# ---------------------------------------------------------------- publicaciones
def convocatoria(datos):
    img = background(); d = ImageDraw.Draw(img); header_footer(d, datos)
    A = T["accent"]
    center(d, 150, "CONVOCATORIA", font("Bold", 84))
    match_line(img, d, 255, datos)
    subtitulo(d, 415, datos)
    if isinstance(datos["convocados"], list):
        return convocatoria_plana(img, d, datos)
    grupos = {k: v for k, v in datos["convocados"].items() if v}
    top, bottom = 480, 1200

    def alto(rh):
        return sum(40 + math.ceil(len(v) / 2) * rh + 16 for v in grupos.values())

    rh = 36
    while rh > 24 and alto(rh) > bottom - top:
        rh -= 1
    fs = max(18, rh - 9)
    y = top
    for nombre, lista in grupos.items():
        d.text((60, y), nombre.upper(), font=font("Bold", 26), fill=A)
        y += 40
        for i, j in enumerate(lista):
            x = 60 + (i % 2) * 510
            yy = y + (i // 2) * rh
            dorsal, nom = jugador(j)
            if dorsal:
                d.text((x, yy), dorsal, font=font("Bold", fs), fill=A)
                d.text((x + 55, yy), nom, font=fit(d, nom, "Medium", fs, 400), fill=WHITE)
            else:
                d.text((x, yy), nom, font=fit(d, nom, "Medium", fs, 450), fill=WHITE)
        y += math.ceil(len(lista) / 2) * rh + 16
    return img


def convocatoria_plana(img, d, datos):
    """Lista única ordenada como la publica el club (dorsal + nombre) y, si hay, las bajas."""
    A = T["accent"]
    lista, bajas = datos["convocados"], datos.get("bajas", [])
    n = len(lista)
    d.text((60, 478), f"CONVOCADOS · {n}", font=font("Bold", 26), fill=A)
    filas = math.ceil(n / 2)
    fondo = 1200 - (150 if bajas else 0)
    rh = min(54, (fondo - 522) // filas)
    fs = max(20, rh - 17)
    for i, j in enumerate(lista):
        col, fila = divmod(i, filas)  # se lee de arriba abajo, columna a columna
        x = 60 + col * 510
        yy = 522 + fila * rh
        dorsal, nom = jugador(j)
        if dorsal:
            d.text((x, yy), dorsal, font=font("Bold", fs), fill=A)
        d.text((x + (62 if dorsal else 0), yy), nom, font=fit(d, nom, "Medium", fs, 400), fill=WHITE)
    if bajas:
        y0 = 1200 - 128
        d.line([(60, y0 - 12), (W - 60, y0 - 12)], fill=A, width=1)
        d.text((60, y0), "BAIXAS", font=font("Bold", 24), fill=A)
        nombres = ", ".join(jugador(b)[1] for b in bajas)
        f = fit(d, nombres, "Medium", 27, W - 120, minsize=20)
        d.text((60, y0 + 38), nombres, font=f, fill=SOFT)
    return img


def alineacion(datos):
    img = background(); d = ImageDraw.Draw(img); header_footer(d, datos)
    A = T["accent"]
    center(d, 150, "ALIÑACIÓN", font("Bold", 84))
    match_line(img, d, 255, datos)
    subtitulo(d, 415, datos)
    once, sup, ent = datos["once"], datos.get("suplentes", []), datos.get("entrenador")
    ancho = 540 if sup else 960
    d.rounded_rectangle([60, 480, 60 + ancho, 1180], 26, fill=T["card"])
    d.text((95, 505), "ONCE INICIAL", font=font("Bold", 30), fill=A)
    paso = 50 if (not sup and ent) else 53
    for i, j in enumerate(once):
        yy = 565 + i * paso
        dorsal, nom = jugador(j)
        if dorsal:
            d.text((95, yy), dorsal, font=font("Bold", 30), fill=A)
        d.text((165 if dorsal else 95, yy), nom, font=fit(d, nom, "Medium", 31, ancho - 130), fill=WHITE)
    if not sup and ent:
        d.text((95, 1125), "ADESTRADOR", font=font("Bold", 22), fill=A)
        d.text((290, 1120), ent, font=fit(d, ent, "Medium", 27, ancho - 250), fill=WHITE)
    if sup:
        d.rounded_rectangle([620, 480, 1020, 1180], 26, fill=T["card"])
        d.text((655, 505), "SUPLENTES", font=font("Bold", 30), fill=A)
        libre = (985 if ent else 1150) - 565
        rh = min(47, libre // len(sup))
        fs = max(18, rh - 20)
        for i, j in enumerate(sup):
            yy = 565 + i * rh
            dorsal, nom = jugador(j)
            if dorsal:
                d.text((655, yy), dorsal, font=font("Bold", fs - 1), fill=A)
            d.text((715 if dorsal else 655, yy), nom, font=fit(d, nom, "Medium", fs, 285), fill=WHITE)
        if ent:
            ye = min(1000, 565 + len(sup) * rh + 30)
            d.text((655, ye), "ADESTRADOR", font=font("Bold", 24), fill=A)
            d.text((655, ye + 38), ent, font=fit(d, ent, "Medium", 27, 330), fill=WHITE)
    return img


def resultado(datos):
    img = background(); d = ImageDraw.Draw(img); header_footer(d, datos)
    A = T["accent"]
    center(d, 160, "RESULTADO", font("Bold", 84))
    t = " · ".join(str(datos[k]) for k in ("jornada", "lugar") if datos.get(k))
    center(d, 275, t, fit(d, t, "Medium", 30, W - 120), fill=SOFT)
    crest(img, 190, 530, 100, datos["local"])
    crest(img, 890, 530, 100, datos["visitante"])
    marcador = f"{datos['goles_local']} - {datos['goles_visitante']}"
    center(d, 445, marcador, font("Bold", 150))
    nl = datos.get("local_nombre") or corto(datos["local"])
    nv = datos.get("visitante_nombre") or corto(datos["visitante"])
    center(d, 660, nl, fit(d, nl, "Bold", 36, 300), fill=A, x=190)
    center(d, 660, nv, fit(d, nv, "Bold", 36, 300), fill=WHITE, x=890)

    d.rounded_rectangle([60, 790, W - 60, 1170], 28, fill=T["card"])
    d.text((100, 820), "GOLES", font=font("Bold", 28), fill=A)
    cols = [(nl, datos.get("goleadores_local", []), A, 100), (nv, datos.get("goleadores_visitante", []), SOFT, 560)]
    if not any(c[1] for c in cols):
        d.text((100, 890), "Sen goles", font=font("Medium", 32), fill=WHITE)
        return img
    mx = max(len(c[1]) for c in cols)
    rh = min(52, 280 // (mx + 1))
    for nombre, lista, color, x in cols:
        d.text((x, 872), nombre, font=font("Bold", max(20, rh - 14)), fill=color)
        for i, g in enumerate(lista):
            s_ = f"• {g}"
            d.text((x, 872 + rh * (i + 1)), s_, font=fit(d, s_, "Medium", max(20, rh - 14), 400), fill=WHITE)
    return img


RENDER = {"convocatoria": convocatoria, "alineacion": alineacion, "resultado": resultado}


def foto_especial(datos):
    """v64: fotos propias para tres casos (el resto de historias no cambia):
    · partido de Europa League (previa, próximo partido, convocatoria, alineación, inicio, descanso y resultado) -> fondo_europa.jpg
    · inicio de partido del Celta (primer equipo)                                                          -> fondo_inicio.jpg
    · resultado con victoria del Celta (primer equipo)                                                     -> fondo_victoria.jpg
    · alineación del Celta (v85; salvo Europa League, que lleva el suyo)                                   -> fondo_alineacion_balaidos.jpg"""
    tipo, titulo = datos.get("tipo"), (datos.get("titulo") or "").upper()
    if tipo in ("gol", "tarjeta", "penalti_parado"):                                           # v80: el gol en Europa League lleva el fondo y el estilo de Europa; el resto de goles, su fondo de siempre
        return "fondo_europa.jpg" if (datos.get("logo") == "europa" or datos.get("competicion") == "europa") else None
    if tipo not in ("previa", "proximo", "convocatoria", "alineacion", "resultado"):
        return None
    if datos.get("logo") == "europa" or datos.get("competicion") == "europa":
        return "fondo_europa.jpg"
    if tipo == "alineacion" and datos.get("tag") != "CELTA FORTUNA":                            # v85: la alineación del Celta lleva la foto de Balaídos (la del Fortuna, su estilo turquesa)
        return "fondo_alineacion_balaidos.jpg"
    if "celta-vigo" not in (datos.get("local"), datos.get("visitante")) or datos.get("tag") == "CELTA FORTUNA":
        return None
    if tipo == "resultado" and titulo.startswith(("COMEZA", "COMIENZA")):
        return "fondo_inicio.jpg"
    if tipo == "resultado" and "DESCANSO" not in titulo:
        try:
            gc, gr = (datos["goles_local"], datos["goles_visitante"]) if datos["local"] == "celta-vigo" else (datos["goles_visitante"], datos["goles_local"])
            if int(gc) > int(gr):
                return "fondo_victoria.jpg"
        except (KeyError, TypeError, ValueError):
            pass
    return None


def generar(ruta_json, salida=None):
    global T
    datos = json.load(open(ruta_json, encoding="utf-8"))
    T = THEMES[datos.get("competicion", "liga")]
    HISTORIA.usar_tema(datos.get("logo"), datos.get("tag"))
    HISTORIA._TIPO_FONDO = datos.get("tipo")
    HISTORIA._FOTO_ESPECIAL = foto_especial(datos)
    HISTORIA.USO_FOTOS, HISTORIA.ULTIMA_ETIQUETA = False, None     # v80: se ponen a True/valor al dibujar caras (diario.py los lee para el crédito y la etiqueta)
    if datos["tipo"] in HISTORIA.RENDER:
        img = HISTORIA.RENDER[datos["tipo"]](datos)  # TODO sale como historia 1080x1920 (también Europa League)
        img = HISTORIA.acabado(img)                  # v60: halo de color, viñeteado y grano
    else:
        img = RENDER[datos["tipo"]](datos)
    if salida is None:
        salida = os.path.join(BASE, "ejemplos", os.path.splitext(os.path.basename(ruta_json))[0] + ".jpg")
    os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
    if salida.lower().endswith((".jpg", ".jpeg")):     # JPEG: pesa ~10 veces menos y Instagram lo acepta igual
        img.convert("RGB").save(salida, quality=86, optimize=True, subsampling=0)
    else:
        img.save(salida, optimize=True)
    return salida


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(generar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
    else:
        for p in sorted(glob.glob(os.path.join(BASE, "datos_ejemplo", "*.json"))):
            print(generar(p))
