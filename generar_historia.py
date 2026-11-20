"""Marexada Celeste · diseño «historia» 1080x1920 (LaLiga y Celta Fortuna).

Tipos: proximo | resultado | convocatoria | alineacion.  Europa League sigue con el diseño de generar.py.
Se usa desde generar.py (generar_historia.RENDER).  Fondo: assets/fondos/historia.jpg (si no existe, el provisional).
"""
import datetime
import glob
import json
import math
import os
import re

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")
W, H = 1080, 1920
WHITE = (255, 255, 255)
AZUL = (146, 202, 246)          # azul claro de rótulos y horas
NAVY = (8, 24, 52)
EQUIPOS = json.load(open(os.path.join(ASSETS, "equipos.json"), encoding="utf-8"))
LOGOS = {"laliga": "logo_laliga.png", "hypermotion": "logo_hypermotion.png", "europa": "logo_europa.png", "copa": "logo_copa.png"}

SEGURA_SUP, SEGURA_INF = 240, 1690     # Instagram tapa arriba (perfil) y abajo (barra de mensaje): ahí no va nada importante

DIA = {"Lun": "Luns", "Mar": "Martes", "Mér": "Mércores", "Xov": "Xoves", "Ven": "Venres", "Sáb": "Sábado", "Dom": "Domingo"}
MES = ["xaneiro", "febreiro", "marzo", "abril", "maio", "xuño", "xullo", "agosto", "setembro", "outubro", "novembro", "decembro"]


def font(size):
    return ImageFont.truetype(os.path.join(ASSETS, "fuentes", "Poppins-Bold.ttf"), int(size))


def fit(d, text, size, maxw, minsize=18):
    size = int(size)
    f = font(size)
    while size > minsize and d.textlength(text, font=f) > maxw:
        size -= 1
        f = font(size)
    return f


def _sombra_texto(d, x, y, text, f, alpha=135, desenfoque=6, dy=4):
    """v60: sombra suave bajo un texto claro (se lee mejor sobre la foto). Si no se puede, no hace nada."""
    im = getattr(d, "_image", None)
    if im is None or im.mode != "RGB" or not text.strip():
        return
    m = desenfoque * 3 + 4
    bb = d.textbbox((x, y), text, font=f)
    x0, y0, x1, y1 = int(bb[0] - m), int(bb[1] - m + dy), int(bb[2] + m), int(bb[3] + m + dy)
    capa = Image.new("L", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(capa).text((x - x0, y - y0 + dy), text, font=f, fill=alpha)
    capa = capa.filter(ImageFilter.GaussianBlur(desenfoque))
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(im.width, x1), min(im.height, y1)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    capa = capa.crop((cx0 - x0, cy0 - y0, cx1 - x0, cy1 - y0))
    im.paste((2, 8, 20), (cx0, cy0, cx1, cy1), capa)


def center(d, y, text, f, fill=WHITE, x=W // 2):
    px = x - d.textlength(text, font=f) / 2
    if isinstance(fill, tuple) and sum(fill[:3]) > 450:                  # solo los textos claros llevan sombra
        _sombra_texto(d, px, y, text, f)
    d.text((px, y), text, font=f, fill=fill)


# ---------------------------------------------------------------- datos -> textos
def fecha_larga(fecha_hora):
    """'Sáb 31/10 · 18:30' -> ('Sábado 31 de outubro', '18:30')"""
    if not fecha_hora:
        return None, None
    m = re.match(r"(\w+)\s+(\d{1,2})/(\d{1,2})(?:\s*·\s*(\d{1,2}:\d{2}))?", fecha_hora)
    if not m:
        return fecha_hora, None
    return f"{DIA.get(m.group(1), m.group(1))} {int(m.group(2))} de {MES[int(m.group(3)) - 1]}", m.group(4)


def nombre(datos, lado):
    n = datos.get(lado + "_nombre")
    if n:
        return n.title() if n.isupper() and len(n) > 4 else n
    return EQUIPOS.get(datos[lado], {}).get("nombre", datos[lado].replace("-", " ").title())


def etiqueta_equipo(datos):
    return datos.get("tag") or "REAL CLUB CELTA"


# ---------------------------------------------------------------- piezas
_TEMA_BASE = {"navy": NAVY, "acento": AZUL}
_TEMAS = {"copa": {"navy": (86, 8, 28), "acento": (255, 178, 178)},            # Copa del Rey: fondo teñido de rojo
          "europa": {"navy": (34, 16, 6), "acento": (255, 150, 48)},          # Europa League: fondo oscuro cálido y acento naranja
          "hypermotion": {"navy": (3, 38, 42), "acento": (72, 226, 214)}}     # v60: LaLiga Hypermotion (Celta Fortuna): fondo verde petróleo y acento turquesa
_TEMAS_TAG = {"AS CELTAS FEM": {"navy": (32, 14, 58), "acento": (206, 172, 255)},      # v60: AS Celtas (femenino): fondo violeta oscuro y acento lila
              "CELTA FORTUNA": {"navy": (3, 38, 42), "acento": (72, 226, 214)}}         # v61: el Celta Fortuna siempre en turquesa (parte médico, etc.), aunque no lleve logo de competición   # v60: AS Celtas (femenino): fondo violeta oscuro y acento lila


def usar_tema(logo=None, tag=None):
    """Cambia los colores de las historias según la competición (Copa = rojo, Europa = naranja, Hypermotion = turquesa, femenino = lila, LaLiga = celeste)."""
    global NAVY, AZUL
    t = _TEMAS.get(logo) or _TEMAS_TAG.get(tag) or _TEMA_BASE
    NAVY, AZUL = t["navy"], t["acento"]


# v52: un fondo distinto según el tipo de historia (la misma capa azul y el mismo pie, solo cambia la foto). Sin foto, se usa la grada de siempre.
FONDO_POR_TIPO = {"convocatoria": "fondo_vestuario.jpg", "alineacion": "fondo_vestuario.jpg",
                  "partemedico": "fondo_ciudad_deportiva.jpg", "clasificacion": "fondo_mural_balaidos.jpg",
                  "gol": "fondo_gol.jpg"}          # v53: el gol dibuja su propio fondo (fondo_gol(), sin deformar la foto)
_TIPO_FONDO = None
_FOTO_ESPECIAL = None        # v64: foto concreta para esta historia (victoria del Celta, inicio de partido, partidos de Europa League); la pone generar.py


def fondo():
    if _FOTO_ESPECIAL and os.path.isfile(os.path.join(ASSETS, "fondos", _FOTO_ESPECIAL)):
        return fondo_foto(_FOTO_ESPECIAL)
    ruta = os.path.join(ASSETS, "fondos", FONDO_POR_TIPO.get(_TIPO_FONDO, ""))
    if not os.path.isfile(ruta):
        ruta = os.path.join(ASSETS, "fondos", "historia.jpg")
    if not os.path.exists(ruta):
        ruta = os.path.join(ASSETS, "fondos", "historia_provisional.jpg")
    img = Image.open(ruta).convert("RGB").resize((W, H), Image.LANCZOS)
    if NAVY != _TEMA_BASE["navy"]:                      # v61: en los equipos/competiciones con otro color la foto se desatura para que el tinte se note de verdad
        from PIL import ImageOps
        img = Image.blend(img, ImageOps.grayscale(img).convert("RGB"), 0.7)
    img = Image.blend(img, Image.new("RGB", (W, H), NAVY), 0.66)
    # oscurece arriba y abajo para que se lea el texto
    sombra = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sombra)
    for y in range(H):
        a = max(0, 1 - y / 520) * 90 + max(0, (y - 1450) / 470) * 110
        sd.line([(0, y), (W, y)], fill=int(a))
    img.paste(Image.new("RGB", (W, H), (4, 12, 30)), (0, 0), sombra)
    return img


def pegar(img, ruta, x, y, tam=None):
    im = Image.open(ruta).convert("RGBA")
    if tam:
        im = im.resize(tam, Image.LANCZOS)
    img.paste(im, (x, y), im)


def cabecera(img, d, tag, titulo, logo=None, ytitulo=205, ytag=150):
    center(d, ytag, tag, font(44), fill=AZUL)
    center(d, ytitulo, titulo, fit(d, titulo, 86, W - 100), fill=WHITE)
    if logo and logo in LOGOS:
        pegar(img, os.path.join(ASSETS, "marca", LOGOS[logo]), 400, 340)


def pie(img, d):
    _pie_marca(img, d, 1590)


def escudo(img, cx, cy, slug, siglas):
    """Círculo blanco de 310 px con sombra y el escudo dentro (o las siglas si no hay)."""
    r = 155
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).ellipse([cx - r + 4, cy - r + 14, cx + r + 4, cy + r + 14], fill=(0, 0, 0, 90))
    sombra = sombra.crop((cx - 200, cy - 200, cx + 220, cy + 220)).filter(ImageFilter.GaussianBlur(10))
    img.paste(sombra, (cx - 200, cy - 200), sombra)
    d = ImageDraw.Draw(img)
    m = glob.glob(os.path.join(ASSETS, "escudos", f"{slug}-logo-footylogos.png"))
    if m:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE)
        c = Image.open(m[0]).convert("RGBA")
        c = c.crop(c.getbbox())
        box = 214
        k = min(box / c.width, box / c.height)
        c = c.resize((max(1, int(c.width * k)), max(1, int(c.height * k))), Image.LANCZOS)
        img.paste(c, (cx - c.width // 2, cy - c.height // 2), c)
    else:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AZUL)
        center(d, cy - 50, siglas, font(100), fill=(14, 40, 84), x=cx)


def siglas(txt):
    p = [w for w in re.split(r"\W+", txt) if w and w.lower() not in ("de", "la", "el", "ud", "cd", "cf", "fc", "rcd", "sd", "ad", "real", "club")]
    return (p[0][0] + (p[1][0] if len(p) > 1 else p[0][1:2])).upper() if p else txt[:2].upper()


def nombres_bajo_escudos(d, datos, y=1105):
    for lado, cx in (("local", 215), ("visitante", 865)):
        n = nombre(datos, lado)
        f = font(46)
        lineas = [n]
        if d.textlength(n, font=f) > 400 and " " in n:
            pal = n.split()
            mejor = min(range(1, len(pal)), key=lambda i: abs(len(" ".join(pal[:i])) - len(" ".join(pal[i:]))))
            lineas = [" ".join(pal[:mejor]), " ".join(pal[mejor:])]
        for i, l in enumerate(lineas):
            center(d, y + i * 56, l, fit(d, l, 46, 420), x=cx)


def jornada(d, datos, y=668):
    j = (datos.get("jornada") or "").strip()
    if j and not re.search(r"\bX$", j):
        center(d, y, j, fit(d, j, 40, W - 120), fill=(200, 218, 240))


def encuentro(img, d, datos, centro):
    escudo(img, 215, 905, datos["local"], siglas(nombre(datos, "local")))
    escudo(img, 865, 905, datos["visitante"], siglas(nombre(datos, "visitante")))
    center(d, 862, centro, font(80 if centro == "VS" else 100), fill=AZUL if centro == "VS" else WHITE)
    nombres_bajo_escudos(d, datos)


# ---------------------------------------------------------------- publicaciones
def pildora(img, x, y, w, h):
    cap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(cap).rounded_rectangle([x, y, x + w, y + h], 14, fill=(255, 255, 255, 36))
    img.paste(cap, (0, 0), cap)


def lista_pildoras(img, d, jugadores, y0, filas_max, titulo=None):
    n = len(jugadores)
    filas = (n + 1) // 2
    ph = min(68, (filas_max) // max(filas, 1))
    fs = max(26, ph - 28)
    for i, j in enumerate(jugadores):
        col, fila = divmod(i, filas)
        x = 70 + col * 480
        y = y0 + fila * (ph + 10)
        pildora(img, x, y, 460, ph)
        dorsal, nom = (j.get("dorsal"), j["nombre"]) if isinstance(j, dict) else (None, j)
        pos = j.get("pos") if isinstance(j, dict) else None
        txt = f"{nom} ({pos})" if pos else nom
        if dorsal:
            d.text((x + 16, y + (ph - fs) / 2 - 6), f"{dorsal}", font=font(fs), fill=AZUL)
            d.text((x + 16 + 68, y + (ph - fs) / 2 - 6), txt, font=fit(d, txt, fs, 460 - 100), fill=WHITE)
        else:
            d.text((x + 20, y + (ph - fs) / 2 - 6), txt, font=fit(d, txt, fs, 420), fill=WHITE)
    return y0 + filas * (ph + 10)


def _rgba(img, caja, radio, relleno, borde=None, grosor=2):
    """Rectángulo redondeado translúcido."""
    cap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(cap).rounded_rectangle(caja, radio, fill=relleno, outline=borde, width=grosor)
    img.paste(cap, (0, 0), cap)


def _escudo_redondo(img, cx, cy, slug, siglas_txt, r=118):
    """Escudo en círculo blanco con aro de color y sombra (versión v33, más pequeña que escudo())."""
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).ellipse([cx - r + 3, cy - r + 12, cx + r + 3, cy + r + 12], fill=(0, 0, 0, 120))
    caja = (cx - r - 40, cy - r - 40, cx + r + 40, cy + r + 40)
    sombra = sombra.crop(caja).filter(ImageFilter.GaussianBlur(11))
    img.paste(sombra, caja[:2], sombra)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r - 7, cy - r - 7, cx + r + 7, cy + r + 7], fill=AZUL)          # aro de color
    m = glob.glob(os.path.join(ASSETS, "escudos", f"{slug}-logo-footylogos.png"))
    if m:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE)
        c = Image.open(m[0]).convert("RGBA")
        c = c.crop(c.getbbox())
        k = min(r * 1.45 / c.width, r * 1.45 / c.height)
        c = c.resize((max(1, int(c.width * k)), max(1, int(c.height * k))), Image.LANCZOS)
        img.paste(c, (cx - c.width // 2, cy - c.height // 2), c)
    else:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(20, 52, 104))
        center(d, cy - 40, siglas_txt, font(84), fill=WHITE, x=cx)


def _tag_v33(datos):
    t = datos.get("tag")
    return t if t in ("CELTA FORTUNA", "AS CELTAS FEM") else "REAL CLUB CELTA DE VIGO"


def _logo_competicion(img, logo, cx, y, lado=144):
    """Logo de la competición bien visible: baldosa con sombra y borde blanco fino para que no se pierda sobre el fondo (el de la Copa es rojo)."""
    x = cx - lado // 2
    caja = (x - 40, y - 30, x + lado + 40, y + lado + 60)
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle([x, y + 10, x + lado, y + lado + 10], int(lado * 0.22), fill=(0, 0, 0, 150))
    sombra = sombra.crop(caja).filter(ImageFilter.GaussianBlur(12))
    img.paste(sombra, caja[:2], sombra)
    borde = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(borde).rounded_rectangle([x - 5, y - 5, x + lado + 5, y + lado + 5], int(lado * 0.24), fill=(255, 255, 255, 235))
    img.paste(borde, (0, 0), borde)
    pegar(img, os.path.join(ASSETS, "marca", LOGOS[logo]), x, y, (lado, lado))


def _escudo_pena(img, cx, y, lado=168):
    """Escudo de la peña (original de 1024 px reducido con LANCZOS) con sombra suave."""
    caja = (cx - lado // 2 - 40, y - 30, cx + lado // 2 + 40, y + lado + 60)
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).ellipse([cx - lado // 2, y + 8, cx + lado // 2, y + lado + 8], fill=(0, 0, 0, 140))
    sombra = sombra.crop(caja).filter(ImageFilter.GaussianBlur(10))
    img.paste(sombra, caja[:2], sombra)
    pegar(img, os.path.join(ASSETS, "marca", "escudo_marexada.png"), cx - lado // 2, y, (lado, lado))


def _nombre_lineas(d, n, tam, maxw):
    pal = n.split()
    if d.textlength(n, font=font(tam)) > maxw and len(pal) > 1:
        k = min(range(1, len(pal)), key=lambda i: abs(len(" ".join(pal[:i])) - len(" ".join(pal[i:]))))
        return [" ".join(pal[:k]), " ".join(pal[k:])]
    return [n]


def _bloque_partido(img, d, datos, cy, r=98, centro="VS", cx=(270, 810), tam=36, brillo=()):
    """Los dos escudos con su nombre debajo y el centro (VS o marcador). Devuelve la y donde acaban los nombres.
    brillo: lados que llevan un resplandor del color de la competición detrás del escudo (v60)."""
    fin = cy
    for lado, x in (("local", cx[0]), ("visitante", cx[1])):
        if lado in brillo:
            _brillo(img, (x - r - 30, cy - r - 30, x + r + 30, cy + r + 30), AZUL, alpha=48, desenfoque=20)
            d = ImageDraw.Draw(img)
        _escudo_redondo(img, x, cy, datos[lado], siglas(nombre(datos, lado)), r=r)
        lineas = _nombre_lineas(d, nombre(datos, lado), tam, 420)
        for i, l in enumerate(lineas):
            center(d, cy + r + 20 + i * (tam + 8), l, fit(d, l, tam, 420), x=x)
        fin = max(fin, cy + r + 20 + len(lineas) * (tam + 8))
    if centro:
        center(d, cy - 52, centro, font(92), fill=AZUL)
    return fin


def _pildora_fecha(img, d, y, texto, tam=44, alto=78, sub=None):
    """Píldora con la fecha/hora y, opcionalmente, el estadio dentro (una línea más pequeña debajo)."""
    f = fit(d, texto, tam, W - 220)
    tw = d.textlength(texto, font=f)
    fs = font(28)
    sw = d.textlength(sub, font=fs) if sub else 0
    ancho = max(tw, sw)
    total = alto + (34 if sub else 0)
    _rgba(img, [W // 2 - ancho / 2 - 40, y, W // 2 + ancho / 2 + 40, y + total], 39 if sub else alto // 2, (255, 255, 255, 34), borde=AZUL, grosor=3)
    center(d, y + (alto - f.size) / 2 - 8 - (2 if sub else 0), texto, f, fill=WHITE)
    if sub:
        center(d, y + alto - 14, sub, fs, fill=(200, 218, 240))
    return y + total


def _tarjeta_jugador(img, d, x, y, w, h, dorsal, nom, pos=None):
    _rgba(img, [x, y, x + w, y + h], h // 2, (255, 255, 255, 30), borde=(255, 255, 255, 46), grosor=1)
    r = h // 2 - 4
    cx, cy = x + h // 2, y + h // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AZUL)
    if dorsal:
        fd = fit(d, str(dorsal), h * 0.44, r * 1.7, 14)
        tw = d.textlength(str(dorsal), font=fd)
        d.text((cx - tw / 2, cy - fd.size * 0.70), str(dorsal), font=fd, fill=NAVY)
    extra = 0
    if pos:
        fp = font(max(16, h * 0.30))
        extra = d.textlength(pos, font=fp) + 22
        d.text((x + w - extra + 6, cy - fp.size * 0.70), pos, font=fp, fill=AZUL)
    fn = fit(d, nom, max(24, h * 0.50), w - h - 24 - extra, 18)
    d.text((x + h + 8, cy - fn.size * 0.70), nom, font=fn, fill=WHITE)


# ---------------------------------------------------------------- resultado (cartel)
def _balon(d, cx, cy, r=15):
    """Pequeño icono de balón."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE, outline=(20, 30, 50), width=2)
    pent = [(cx + r * 0.42 * math.cos(math.radians(a)), cy + r * 0.42 * math.sin(math.radians(a))) for a in range(-90, 270, 72)]
    d.polygon(pent, fill=(20, 30, 50))
    for (px, py) in pent:
        k = r / (r * 0.42)
        d.line([(px, py), (cx + (px - cx) * k * 0.92, cy + (py - cy) * k * 0.92)], fill=(20, 30, 50), width=2)


def _agrupar_goles(lista):
    """["Besfort Zeneli 35'", "Besfort Zeneli 49'"] -> [("Besfort Zeneli", ["35'", "49'"])] (mismo jugador junto, en orden)."""
    out = []
    for g in lista:
        m = re.match(r"^(.*?)\s+([\d+]+'?)\s*$", g.strip())
        nom, mi = (m.group(1), m.group(2) if m.group(2).endswith("'") else m.group(2) + "'") if m else (g.strip(), "")
        for e in out:
            if e[0] == nom:
                if mi:
                    e[1].append(mi)
                break
        else:
            out.append((nom, [mi] if mi else []))
    return out



CARAS_EN_GOL = False        # v82: ponerlo a False para que la historia de gol salga sin la cara del goleador (la etiqueta de Instagram se mantiene, con una píldora «@cuenta»)
CARAS_EN_RESULTADO = True   # v82: ídem para las caras en la lista de goleadores del resultado final
USO_FOTOS = False           # v80: la historia que se acaba de dibujar lleva caras de jugadores (generar.py lo pone a False antes; diario.py añade el crédito al texto)
ULTIMA_ETIQUETA = None      # v80: (x, y) en proporción de la imagen donde colocar la mención al goleador en Instagram


PIE_Y = 1466                # el pie (escudos de la peña + web) ocupa de 1466 a 1690, dentro de la zona segura
FIN_CONTENIDO = PIE_Y - 18


def _filete(d, yl, color=None):
    d.line([(150, yl), (W // 2 - 26, yl)], fill=AZUL, width=3)
    d.line([(W // 2 + 26, yl), (W - 150, yl)], fill=AZUL, width=3)
    _rombo(d, W // 2, yl, 9, AZUL)


def _cab_texto(img, d, titulo, tag):
    """Cabecera sin logo (el de la competición va entre los escudos): título, equipo y filete. Devuelve la y del filete."""
    yt = SEGURA_SUP
    center(d, yt, titulo, fit(d, titulo, 100, W - 90))
    center(d, yt + 114, tag, font(36), fill=AZUL)
    yl = yt + 172
    _filete(d, yl)
    return yl


def _cab_logo(img, d, titulo, tag, logo, s):
    """Cabecera con el logo de la competición grande arriba (resultado y próximo partido)."""
    y = SEGURA_SUP
    if logo in LOGOS:
        L = int(150 * s)
        _logo_competicion(img, logo, W // 2, y, L)
        yt = y + L + 14
    else:
        yt = y
    center(d, yt, titulo, fit(d, titulo, 96, W - 90))
    center(d, yt + 110, tag, font(34), fill=AZUL)
    yl = yt + 166
    _filete(d, yl)
    return yl


def _logo_texto(img, x, y, ancho):
    """Segundo logo de la peña (MAREXADA CELESTE con el escudo rojo), con una sombra suave para que se lea sobre la foto."""
    wm = Image.open(os.path.join(ASSETS, "marca", "logo_marexada_texto.png")).convert("RGBA")
    alto = int(wm.height * ancho / wm.width)
    wm = wm.resize((ancho, alto), Image.LANCZOS)
    sombra = Image.new("RGBA", (ancho + 60, alto + 60), (0, 0, 0, 0))
    sombra.paste((0, 0, 0, 170), (30, 36), wm.getchannel("A"))
    sombra = sombra.filter(ImageFilter.GaussianBlur(9))
    img.paste(sombra, (x - 30, y - 30), sombra)
    img.paste(wm, (x, y), wm)
    return alto


# Pie de marca: escudo azul + letras (más pequeñas) + escudo rojo centrado con las letras.
# Todos se reducen UNA sola vez desde el original grande (sin pasos intermedios) para no perder calidad.
LOGO_PIE = "alternar"       # "alternar" = cada historia cambia: escudo azul + letras / letras + escudo rojo (nunca los dos) | "azul" | "rojo" | "ambos"
_PIE_N = 0                  # cuenta las historias generadas para ir alternando


def _sombra_logo(img, im, x, y, desenfoque=9, alpha=170):
    sombra = Image.new("RGBA", (im.width + 60, im.height + 60), (0, 0, 0, 0))
    sombra.paste((0, 0, 0, alpha), (30, 34), im.getchannel("A"))
    sombra = sombra.filter(ImageFilter.GaussianBlur(desenfoque))
    img.paste(sombra, (x - 30, y - 30), sombra)
    img.paste(im, (x, y), im)


def _cargar_marca(nombre, alto=None, ancho=None):
    im = Image.open(os.path.join(ASSETS, "marca", nombre)).convert("RGBA")
    if alto:
        ancho = round(im.width * alto / im.height)
    else:
        alto = round(im.height * ancho / im.width)
    return im.resize((ancho, alto), Image.LANCZOS)


def _pie_marca(img, d, y):
    """Escudo azul de la peña | MAREXADA CELESTE | escudo rojo, todo en la misma fila y centrado
    verticalmente. La web va debajo. Devuelve la y donde termina."""
    global _PIE_N
    modo = LOGO_PIE
    if modo == "alternar":
        modo = "azul" if (datetime.date.today().toordinal() + _PIE_N) % 2 == 0 else "rojo"
        _PIE_N += 1
    azul = _cargar_marca("escudo_marexada.png", alto=192) if modo in ("ambos", "azul") else None
    rojo = _cargar_marca("logo_marexada_rojo.png", alto=178) if modo in ("ambos", "rojo") else None
    letras = _cargar_marca("logo_marexada_letras.png", ancho=430)
    gap = 26
    piezas = [p for p in (azul, letras, rojo) if p is not None]
    total = sum(p.width for p in piezas) + gap * (len(piezas) - 1)
    fila = max(192, max(p.height for p in piezas))     # misma altura de fila en las dos versiones
    cy = y + fila // 2                      # eje horizontal común: el rojo queda centrado con las letras
    x = (W - total) // 2
    for p in piezas:
        py = cy - p.height // 2
        if p is azul:
            _sombra_logo(img, p, x, py, 10, 140)
        else:
            _sombra_logo(img, p, x, py)
        x += p.width + gap
    center(d, y + fila + 8, "marexadaceleste.com", font(30), fill=AZUL)
    return y + fila + 8 + 40


def _pie_v39(img, d):
    """Pie de las historias de partido, dentro de la zona segura."""
    _pie_marca(img, d, PIE_Y)


def _bloque_centro_logo(img, d, datos, cy, r, tam, s):
    """Escudos de los dos equipos, grandes, y entre ellos el logo de la competición (si no hay, un VS)."""
    cx = (205, 875)
    fin = cy
    for lado, x in (("local", cx[0]), ("visitante", cx[1])):
        _escudo_redondo(img, x, cy, datos[lado], siglas(nombre(datos, lado)), r=r)
        lineas = _nombre_lineas(d, nombre(datos, lado), tam, 380)
        for i, l in enumerate(lineas):
            center(d, cy + r + 16 + i * (tam + 8), l, fit(d, l, tam, 380), x=x)
        fin = max(fin, cy + r + 16 + len(lineas) * (tam + 8))
    logo = datos.get("logo")
    if logo in LOGOS:
        L = min(int(170 * s), 2 * (W // 2 - (cx[0] + r)) - 30)
        _logo_competicion(img, logo, W // 2, cy - L // 2, L)
    else:
        center(d, cy - 38, "VS", font(64), fill=AZUL)
    return fin


def _ajustar(fn, datos):
    """Prueba tamaños de mayor a menor hasta que todo el contenido cabe en la zona segura; luego pone el pie."""
    for s in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6):
        img, fin = fn(datos, s)
        if fin <= FIN_CONTENIDO:
            break
    _pie_v39(img, ImageDraw.Draw(img))
    return img


def _fecha_linea(datos):
    dia, hora = fecha_larga(datos.get("fecha_hora"))
    return " · ".join(x for x in (dia, f"{hora} h" if hora else None) if x)


def _convocatoria(datos, s):
    img = fondo(); d = ImageDraw.Draw(img)
    yl = _cab_texto(img, d, "CONVOCATORIA", _tag_v33(datos))
    r = int(98 * s)
    yp = _bloque_centro_logo(img, d, datos, yl + r + 34, r, int(36 * s), s) + int(22 * s)
    linea = _fecha_linea(datos)
    if linea:
        yp = _pildora_fecha(img, d, yp, linea, sub=datos.get("lugar"))
    bajas = [b if isinstance(b, dict) else {"nombre": b} for b in datos.get("bajas", [])]
    lineas_b, alto_b = [], 0
    if bajas:
        f = font(30)
        act = ""
        for pal in ", ".join(b["nombre"] for b in bajas).split(" "):
            prueba = (act + " " + pal).strip()
            if d.textlength(prueba, font=f) > W - 200 and act:
                lineas_b.append(act); act = pal
            else:
                act = prueba
        lineas_b.append(act)
        alto_b = 58 + 38 * len(lineas_b)
    y0 = yp + 26
    fin = FIN_CONTENIDO - (alto_b + 16 if bajas else 0)
    conv = [j if isinstance(j, dict) else {"nombre": j} for j in datos["convocados"]]
    filas = (len(conv) + 1) // 2
    ph = max(34, min(72, (fin - y0 - 22) // max(filas, 1) - 10))
    alto = filas * (ph + 10) + 22
    _rgba(img, [40, y0 - 12, W - 40, y0 - 12 + alto], 30, (4, 12, 30, 105))
    for i, j in enumerate(conv):
        col, fila = divmod(i, filas)
        _tarjeta_jugador(img, d, 62 + col * 489, y0 + fila * (ph + 10), 467, ph, j.get("dorsal"), j["nombre"])
    y = y0 - 12 + alto + 16
    if bajas:
        _rgba(img, [40, y, W - 40, y + alto_b], 24, (190, 40, 60, 70), borde=(255, 150, 160, 150), grosor=2)
        d.text((70, y + 12), "BAIXAS", font=font(26), fill=(255, 190, 196))
        for i, l in enumerate(lineas_b):
            d.text((70, y + 52 + i * 38), l, font=font(30), fill=(255, 232, 234))
        y += alto_b
    return img, y


def convocatoria(datos):
    return _ajustar(_convocatoria, datos)


def _alineacion(datos, s):
    img = fondo(); d = ImageDraw.Draw(img)
    yl = _cab_texto(img, d, "ALIÑACIÓN", _tag_v33(datos))
    r = int(98 * s)
    yp = _bloque_centro_logo(img, d, datos, yl + r + 34, r, int(36 * s), s) + int(22 * s)
    linea = _fecha_linea(datos)
    if linea:
        yp = _pildora_fecha(img, d, yp, linea, sub=datos.get("lugar"))
    once = [j if isinstance(j, dict) else {"nombre": j} for j in datos["once"]]
    sup = [j if isinstance(j, dict) else {"nombre": j} for j in datos.get("suplentes", [])]
    f1, f2 = (len(once) + 1) // 2, (len(sup) + 1) // 2
    y0 = yp + 26
    libre = FIN_CONTENIDO - y0 - 22 - (60 + 22 if sup else 0)
    ph = max(34, min(74, libre // max(f1 + f2, 1) - 10))
    alto1 = f1 * (ph + 10) + 22
    _rgba(img, [40, y0 - 12, W - 40, y0 - 12 + alto1], 30, (4, 12, 30, 105))
    for i, j in enumerate(once):
        col, fila = divmod(i, f1)
        _tarjeta_jugador(img, d, 62 + col * 489, y0 + fila * (ph + 10), 467, ph, j.get("dorsal"), j["nombre"], j.get("pos"))
    fin = y0 - 12 + alto1
    if sup:
        ys = fin + 14
        d.text((70, ys + 8), "SUPLENTES", font=font(28), fill=AZUL)
        ys += 56
        alto2 = f2 * (ph + 10) + 22
        _rgba(img, [40, ys - 12, W - 40, ys - 12 + alto2], 30, (4, 12, 30, 80))
        for i, j in enumerate(sup):
            col, fila = divmod(i, f2)
            _tarjeta_jugador(img, d, 62 + col * 489, ys + fila * (ph + 10), 467, ph, j.get("dorsal"), j["nombre"], j.get("pos"))
        fin = ys - 12 + alto2
    return img, fin


def alineacion(datos):
    return _ajustar(_alineacion, datos)


def _hoy():
    v = os.environ.get("MAREXADA_HOY")                      # solo para pruebas: MAREXADA_HOY=2026-11-06
    if v:
        return datetime.date.fromisoformat(v)
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Europe/Madrid")).date()
    except Exception:
        return datetime.date.today()


def cuenta_atras(datos):
    """'HOXE', 'MAÑÁ' o 'FALTAN 3 DÍAS' (hasta 14 días); None si no hay fecha o el partido ya pasó."""
    m = re.search(r"(\d{1,2})/(\d{1,2})", datos.get("fecha_hora") or "")
    if not m:
        return None
    hoy = _hoy()
    try:
        f = datetime.date(hoy.year, int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None
    if (f - hoy).days < -200:                                # partido ya del año que viene
        f = f.replace(year=hoy.year + 1)
    n = (f - hoy).days
    if n < 0 or n > 14:
        return None
    return "HOXE" if n == 0 else "MAÑÁ" if n == 1 else f"FALTAN {n} DÍAS"


def _proximo(datos, s, hg=0):
    img = fondo(); d = ImageDraw.Draw(img)
    yl = _cab_logo(img, d, "PRÓXIMO PARTIDO", _tag_v33(datos), datos.get("logo"), s)
    r = int(112 * s)
    cy = yl + r + 30
    fin = _bloque_partido(img, d, datos, cy, r=r, tam=int(38 * s), brillo=("local", "visitante"))
    d = ImageDraw.Draw(img)
    dia, hora = fecha_larga(datos.get("fecha_hora"))
    j = (datos.get("jornada") or "").strip()
    j = "" if re.search(r"\bX$", j) else j
    lugar = datos.get("lugar")
    cd = cuenta_atras(datos)
    ta, th = int(58 * s), int(190 * s)
    alto = 30 + (int(64 * s) + 22 if cd else 0) + (ta + 26 if dia else 0) + (th + 22 if hora else 0) + (58 if lugar else 0) + (66 if j else 0) + 24
    y0 = fin + 44 + hg
    _rgba(img, [60, y0, W - 60, y0 + alto], 36, (4, 12, 30, 105), borde=AZUL + (95,), grosor=3)
    y = y0 + 30
    if cd:                                                    # v60: cuenta atrás en píldora del color de la competición
        fc = font(int(38 * s))
        wc = d.textlength(cd, font=fc)
        hc = int(64 * s)
        d.rounded_rectangle([W / 2 - wc / 2 - 36, y, W / 2 + wc / 2 + 36, y + hc], hc // 2, fill=AZUL)
        bc = d.textbbox((0, 0), "A", font=fc)
        d.text((W / 2 - wc / 2, y + hc / 2 - (bc[1] + bc[3]) / 2), cd, font=fc, fill=NAVY)
        y += hc + 22
    if dia:
        center(d, y, dia, fit(d, dia, ta, W - 160))
        y += ta + 26
    if hora:
        center(d, y, f"{hora} h", fit(d, f"{hora} h", th, W - 160), fill=AZUL)
        y += th + 22
    if lugar:
        center(d, y, lugar, fit(d, lugar, 38, W - 160), fill=(200, 218, 240))
        y += 58
    if j:
        _pildora_fecha(img, d, y + 2, j, tam=32, alto=54)
    return img, y0 + alto


def proximo(datos):
    s_ok = 0.6
    for s in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6):
        img, fin = _proximo(datos, s)
        if fin <= FIN_CONTENIDO:
            s_ok = s
            break
    hg = max(0, min(90, (FIN_CONTENIDO - fin) // 2))
    img, fin = _proximo(datos, s_ok, hg)
    _pie_v39(img, ImageDraw.Draw(img))
    return img


def _fotos_resultado(datos):
    """v80: {nombre: ruta de la cara} de los goleadores del Celta (primer equipo) en un resultado. Sin foto para el Fortuna, el femenino ni los goles en propia puerta."""
    if not CARAS_EN_RESULTADO or (datos.get("tag") or "REAL CLUB CELTA") != "REAL CLUB CELTA":
        return {}
    lado = "local" if datos.get("local") == "celta-vigo" else "visitante" if datos.get("visitante") == "celta-vigo" else None
    if not lado:
        return {}
    try:
        import caras
    except Exception:
        return {}
    out = {}
    for nom, _m in _agrupar_goles(datos.get("goleadores_" + lado, [])):
        if re.search(r"\(|p\.?\s?p\b|propia", nom.lower()):
            continue
        ruta = caras.buscar(nom)
        if ruta:
            out[nom] = ruta
    return out


def _avatar(img, ruta, cx, cy, r):
    """Cara pequeña en círculo (aro blanco) para la lista de goleadores."""
    cx, cy, r = int(round(cx)), int(round(cy)), int(round(r))
    cara = Image.open(ruta).convert("RGBA")
    ancho = int(2.4 * r)                                        # v83: la cabeza entera (de la coronilla a la barbilla) cabe en el círculo
    cara = cara.resize((ancho, int(cara.height * ancho / cara.width)), Image.LANCZOS)
    arriba = cara.getchannel("A").getbbox()[1]
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=WHITE)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AZUL)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    capa.paste(cara, (cx - ancho // 2, cy - r + 2 - arriba), cara)
    mascara = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mascara).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    from PIL import ImageChops
    capa.putalpha(ImageChops.multiply(capa.getchannel("A"), mascara))
    img.paste(capa, (0, 0), capa)


def _resultado(datos, s, hg=0, rh_min=40):
    img = fondo(); d = ImageDraw.Draw(img)
    yl = _cab_logo(img, d, datos.get("titulo") or "RESULTADO FINAL", _tag_v33(datos), datos.get("logo"), s)
    gl = _agrupar_goles(datos.get("goleadores_local", []))
    gv = _agrupar_goles(datos.get("goleadores_visitante", []))
    hay = bool(gl or gv)
    fotos = _fotos_resultado(datos) if hay else {}                # v80: caras de los goleadores del Celta
    if fotos:
        globals()["USO_FOTOS"] = True
    r = int((124 if hay else 150) * s)                             # v84: escudos más grandes en el resultado final
    cy = yl + r + 28
    try:
        ga, gb = int(datos["goles_local"]), int(datos["goles_visitante"])
    except (TypeError, ValueError):
        ga = gb = 0
    ganador = ("local",) if ga > gb else ("visitante",) if gb > ga else ()      # v60: el escudo del que gana lleva resplandor
    fin = _bloque_partido(img, d, datos, cy, r=r, centro=None, cx=(270, 810), tam=int(36 * s), brillo=ganador)
    d = ImageDraw.Draw(img)
    a, b = str(datos["goles_local"]), str(datos["goles_visitante"])
    tam = int((276 if hay else 430) * s)                           # v84: con goleadores, el marcador algo más pequeño para dar sitio a escudos y caras más grandes
    hueco = 52
    while tam > 100:
        f = font(tam)
        total = d.textlength(a, font=f) + d.textlength(b, font=f) + 2 * hueco + 70
        if total <= W - 120:
            break
        tam -= 6
    f = font(tam)
    bb = d.textbbox((0, 0), "8", font=f)
    alto_num = bb[3] - bb[1]
    cs = fin + 36 + hg + alto_num / 2
    ytxt = cs - (bb[1] + alto_num / 2)
    wa = d.textlength(a, font=f)
    x0 = W / 2 - total / 2
    _brillo(img, (x0 - 70, cs - alto_num * 0.62, x0 + total + 70, cs + alto_num * 0.62), AZUL, alpha=70, desenfoque=40)
    d = ImageDraw.Draw(img)
    borde = (4, 14, 34)
    d.text((x0, ytxt), a, font=f, fill=AZUL if ga > gb else WHITE, stroke_width=7, stroke_fill=borde)
    d.rounded_rectangle([x0 + wa + hueco, cs - 9, x0 + wa + hueco + 70, cs + 9], 9, fill=AZUL)
    d.text((x0 + wa + 2 * hueco + 70, ytxt), b, font=f, fill=AZUL if gb > ga else WHITE, stroke_width=7, stroke_fill=borde)
    yp = cs + alto_num / 2 + 6 + 40 + hg
    dia, _ = fecha_larga(datos.get("fecha_hora"))
    j = (datos.get("jornada") or "").strip()
    j = "" if re.search(r"\bX$", j) else j
    linea = " · ".join(x for x in (j, dia) if x)
    if linea:
        yp = _pildora_fecha(img, d, yp, linea, tam=38, alto=70, sub=datos.get("lugar"))
    if hay:
        filas = max(len(gl), len(gv))
        y0 = yp + 30 + hg
        rh = max(rh_min, min(112 if fotos else 66, (FIN_CONTENIDO - y0 - (150 if fotos else 100)) // max(filas, 1)))     # v83: con caras, filas más altas (caras más grandes)
        alto = 78 + filas * rh + 16
        _rgba(img, [40, y0, W - 40, y0 + alto], 30, (4, 12, 30, 115), borde=AZUL + (75,), grosor=3)
        center(d, y0 + 16, "GOLEADORES", font(28), fill=AZUL)
        d.line([(W // 2, y0 + 70), (W // 2, y0 + alto - 20)], fill=(255, 255, 255, 60), width=2)
        dd = min(96, rh - 14) if fotos else min(52, rh - 4)         # v83: diámetro de la cara (hasta 100 px con pocas filas)
        grande = bool(fotos) and rh > 70
        col_celta = gl if datos.get("local") == "celta-vigo" else gv
        for lista, x in ((gl, 70), (gv, 570)):   # columnas de 440 px
            xn = max(48, dd + 16) if (fotos and lista is col_celta) else 48          # los nombres se alinean tras la cara solo en la columna del Celta
            for i, (nom, mins) in enumerate(lista[:7]):
                yy = y0 + 78 + i * rh + rh // 2
                if fotos and lista is col_celta and nom in fotos:
                    _avatar(img, fotos[nom], x + 4 + dd // 2, yy, dd // 2)
                    d = ImageDraw.Draw(img)
                elif fotos and lista is col_celta:
                    _balon(d, x + 4 + dd // 2, yy, 16)                               # sin cara: el balón, centrado en el hueco de la cara
                else:
                    _balon(d, x + 18, yy, 16)
                txt_m = " · ".join(mins)
                fm = font(34 if grande else 30)
                wm = d.textlength(txt_m, font=fm)
                d.text((x + 440 - wm, yy - fm.size * 0.70), txt_m, font=fm, fill=AZUL)
                fn = fit(d, nom, 38 if grande else 34, 440 - xn - wm - 20, 20)
                d.text((x + xn, yy - fn.size * 0.70), nom, font=fn, fill=WHITE)
        yp = y0 + alto
        if fotos:
            _credito_fotos(img, yp + 10)
            yp += 50
    return img, yp


def resultado(datos):
    fotos = _fotos_resultado(datos)
    if fotos:                                                    # v84: con caras, los escudos tienen prioridad (nunca por debajo de 0,8) y las caras se adaptan al hueco
        filas = max(len(_agrupar_goles(datos.get("goleadores_local", []))), len(_agrupar_goles(datos.get("goleadores_visitante", []))), 1)
        deseada = 84 if filas <= 3 else 72 if filas == 4 else 62 if filas == 5 else 52
        elegido = None
        d85, d72 = int(deseada * 0.85), int(deseada * 0.72)
        for s, rh_min in ((1.0, deseada), (0.95, deseada), (0.9, deseada), (0.85, deseada), (0.9, d85), (0.8, deseada), (0.85, d85), (0.8, d85), (0.75, deseada),
                          (0.8, d72), (0.7, deseada), (0.7, d85), (0.65, d85), (0.6, d72), (0.6, 40)):          # de más a menos preferido: escudo grande y cara grande
            img, fin = _resultado(datos, s, 0, rh_min)
            if fin <= FIN_CONTENIDO:
                elegido = (s, rh_min, fin)
                break
        s, rh_min, fin = elegido or (0.6, 40, fin)
        hg = max(0, min(50, (FIN_CONTENIDO - fin) / 3))
        img, fin = _resultado(datos, s, hg, rh_min)
        _pie_v39(img, ImageDraw.Draw(img))
        return img
    s_ok = 0.6
    for s in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6):
        img, fin = _resultado(datos, s)
        if fin <= FIN_CONTENIDO:
            s_ok = s
            break
    hg = max(0, min(50, (FIN_CONTENIDO - fin) / 3))
    img, fin = _resultado(datos, s_ok, hg)
    _pie_v39(img, ImageDraw.Draw(img))
    return img


def escudo_mini(img, cx, cy, slug, siglas_txt, r=30):
    d = ImageDraw.Draw(img)
    m = glob.glob(os.path.join(ASSETS, "escudos", f"{slug}-logo-footylogos.png")) if slug else []
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE if m else AZUL)
    if m:
        c = Image.open(m[0]).convert("RGBA")
        c = c.crop(c.getbbox())
        k = min((2 * r - 12) / c.width, (2 * r - 12) / c.height)
        c = c.resize((max(1, int(c.width * k)), max(1, int(c.height * k))), Image.LANCZOS)
        img.paste(c, (cx - c.width // 2, cy - c.height // 2), c)
    else:
        f = font(26)
        w = d.textlength(siglas_txt, font=f)
        d.text((cx - w / 2, cy - 22), siglas_txt, font=f, fill=(14, 40, 84))


def clasificacion(datos):
    img = fondo(); d = ImageDraw.Draw(img)
    filas = list(datos["filas"])
    dest = next((k for k, f in enumerate(filas) if f["nombre"] == datos.get("destacado")), 0)
    ventana = ""
    if len(filas) > 22:                              # tablas largas (Europa League, 36): ventana de 18 equipos alrededor del destacado
        ini = max(0, min(dest - 9, len(filas) - 18))
        ventana = f"postos {filas[ini]['pos']}-{filas[ini + 17]['pos']} de {len(filas)}"
        filas = filas[ini:ini + 18]
    logo = datos.get("logo")
    if logo in LOGOS:
        pegar(img, os.path.join(ASSETS, "marca", LOGOS[logo]), 56, 56, (150, 150))
    center(d, 110, datos.get("tag", ""), font(44), fill=AZUL)
    center(d, 165, "CLASIFICACIÓN", fit(d, "CLASIFICACIÓN", 86, W - 100 if not logo else 700))
    sub = " · ".join(x for x in (datos.get("subtitulo"), datos.get("jornada"), ventana) if x)
    center(d, 285, sub, fit(d, sub, 34, W - 80), fill=(200, 218, 240))
    n = len(filas)
    y0, ph = 400, min(82, 1150 // n)                 # alto de fila: 82 px hasta 14 equipos, menos si hay más
    esc = ph / 82.0
    cab = y0 - 38
    for x, t in ((690, "PJ"), (810, "DG"), (950, "PTS")):
        center(d, cab, t, font(26), fill=AZUL, x=x)
    for i, f in enumerate(filas):
        y = y0 + i * ph
        destacado = f["nombre"] == datos.get("destacado")
        cap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(cap).rounded_rectangle([40, y, W - 40, y + ph - 6], 12, fill=AZUL + (105,) if destacado else (255, 255, 255, 30))
        img.paste(cap, (0, 0), cap)
        d = ImageDraw.Draw(img)
        cy = y + (ph - 6) // 2
        r = max(14, int((ph - 6) * 0.38))
        tf = max(20, int(34 * esc ** 0.8))
        center(d, cy - tf // 2 - 4, str(f["pos"]), font(tf), fill=AZUL, x=88)
        escudo_mini(img, 160, cy, f.get("escudo"), siglas(f["nombre"]), r=r)
        d = ImageDraw.Draw(img)
        ft = fit(d, f["nombre"], max(20, int(34 * esc ** 0.8)), 400)
        d.text((160 + r + 22, cy - tf // 2 - 4), f["nombre"], font=ft, fill=WHITE)
        dg = f"+{f['dg']}" if f["dg"] > 0 else str(f["dg"]).replace("-", "\u2212")
        center(d, cy - tf // 2 - 3, str(f["pj"]), font(max(18, tf - 2)), fill=(214, 228, 246), x=690)
        center(d, cy - tf // 2 - 3, dg, font(max(18, tf - 2)), fill=(214, 228, 246), x=810)
        center(d, cy - tf // 2 - 5, str(f["pts"]), font(tf + 4), fill=WHITE, x=950)
    pie(img, d)
    return img



# ---------------------------------------------------------------- parte médico
def font_m(size):
    return ImageFont.truetype(os.path.join(ASSETS, "fuentes", "Poppins-Medium.ttf"), int(size))


def _lineas(d, texto, f, maxw, maximo=2):
    """Parte un texto en como mucho `maximo` líneas; si sobra, la última acaba en «…»."""
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if d.textlength(prueba, font=f) <= maxw or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    if len(lineas) > maximo:
        lineas = lineas[:maximo]
        while d.textlength(lineas[-1] + "…", font=f) > maxw and " " in lineas[-1]:
            lineas[-1] = lineas[-1].rsplit(" ", 1)[0]
        lineas[-1] += "…"
    return lineas


def _fecha_corta(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)[2:]}" if m else (iso or "")


_MES_GL = {"enero": "xaneiro", "febrero": "febreiro", "marzo": "marzo", "abril": "abril", "mayo": "maio", "junio": "xuño", "julio": "xullo",
           "agosto": "agosto", "septiembre": "setembro", "octubre": "outubro", "noviembre": "novembro", "diciembre": "decembro"}


def _gl(txt):
    return re.sub(r"[A-Za-zñáéíóú]+", lambda m: _MES_GL.get(m.group(0).lower(), m.group(0)), txt or "")


def _dias_baixa(iso, hoy_iso):
    try:
        a, b = datetime.date.fromisoformat(iso), datetime.date.fromisoformat(hoy_iso)
        n = (b - a).days
        return f"{n} día{'s' if n != 1 else ''}" if n >= 0 else ""
    except Exception:
        return ""


def partemedico(datos):
    img = fondo(); d = ImageDraw.Draw(img)
    escudo_mini(img, W // 2, 140, "celta-vigo", "RC", r=74)          # escudo del Celta arriba
    d = ImageDraw.Draw(img)
    center(d, 232, datos.get("tag", ""), font(40), fill=AZUL)
    center(d, 268, "PARTE MÉDICO", fit(d, "PARTE MÉDICO", 92, W - 100))
    d.line([(W // 2 - 190, 408), (W // 2 - 40, 408)], fill=AZUL, width=4)         # filete con cruz médica en el centro
    d.line([(W // 2 + 40, 408), (W // 2 + 190, 408)], fill=AZUL, width=4)
    d.rectangle([W // 2 - 4, 394, W // 2 + 4, 422], fill=(214, 48, 49))
    d.rectangle([W // 2 - 14, 404, W // 2 + 14, 412], fill=(214, 48, 49))
    sub = " · ".join(x for x in (("Actualizado: " + _gl(datos["actualizado"])) if datos.get("actualizado") else None, datos.get("pagina")) if x)
    if sub:
        center(d, 436, sub, fit(d, sub, 32, W - 80), fill=(200, 218, 240))
    les = datos.get("lesionados", [])
    if not les:
        center(d, 800, "Sen baixas", font(84))
        center(d, 920, "por lesión", font(84))
        center(d, 1050, "no parte médico", font(40), fill=AZUL)
    y0, ph = 506, 168
    for i, x in enumerate(les):
        y = y0 + i * ph
        cap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cd = ImageDraw.Draw(cap)
        cd.rounded_rectangle([40, y, W - 40, y + ph - 10], 14, fill=(255, 255, 255, 30))
        cd.rounded_rectangle([40, y, 50, y + ph - 10], 5, fill=AZUL + (255,))        # barra de acento a la izquierda
        img.paste(cap, (0, 0), cap)
        d = ImageDraw.Draw(img)
        cx, cy = 108, y + (ph - 10) // 2          # cruz médica en un círculo blanco
        d.ellipse([cx - 36, cy - 36, cx + 36, cy + 36], fill=WHITE)
        d.rectangle([cx - 8, cy - 24, cx + 8, cy + 24], fill=(208, 40, 52))
        d.rectangle([cx - 24, cy - 8, cx + 24, cy + 8], fill=(208, 40, 52))
        d.text((175, y + 8), x["nombre"], font=fit(d, x["nombre"], 38, 600), fill=WHITE)
        fd = font_m(27)
        yy = y + 58
        for l in _lineas(d, x.get("diagnostico", ""), fd, 640):
            d.text((175, yy), l, font=fd, fill=(214, 228, 246))
            yy += 31
        if x.get("observaciones") and yy + 28 < y + ph - 10:
            d.text((175, yy + 2), x["observaciones"], font=fit(d, x["observaciones"], 22, 640, 18), fill=AZUL)
        center(d, y + 26, "DENDE", font(22), fill=AZUL, x=915)
        center(d, y + 54, _fecha_corta(x.get("fecha")), font(30), fill=WHITE, x=915)
        baixa = _dias_baixa(x.get("fecha"), datos.get("hoy") or "")
        if baixa:
            center(d, y + 100, baixa, font_m(24), fill=(200, 218, 240), x=915)
    pie(img, d)
    return img


# ---------------------------------------------------------------- pronóstico da peña (diseño verde propio, distinto del resto)
VERDE = (150, 232, 190)            # menta claro: acento del pronóstico
VERDE_OSCURO = (6, 40, 28)


def fondo_verde():
    img = Image.open(os.path.join(ASSETS, "fondos", "pronostico_verde.jpg")).convert("RGB").resize((W, H), Image.LANCZOS)
    img = Image.blend(img, Image.new("RGB", (W, H), VERDE_OSCURO), 0.08)
    sombra = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sombra)
    for y in range(H):                                          # más oscuro arriba (título) y abajo (pie)
        sd.line([(0, y), (W, y)], fill=int(max(0, 1 - y / 560) * 105 + max(0, (y - 1400) / 520) * 120))
    img.paste(Image.new("RGB", (W, H), (2, 18, 12)), (0, 0), sombra)
    return img


def _corto(datos, lado):
    return nombre(datos, lado)


def pronostico(datos):
    global AZUL, NAVY
    AZUL, NAVY = VERDE, VERDE_OSCURO                              # acento menta en todo el diseño (escudos sin imagen, pie...)
    img = fondo_verde(); d = ImageDraw.Draw(img)
    center(d, 125, etiqueta_equipo(datos), font(42), fill=VERDE)
    center(d, 175, "PRONÓSTICO", fit(d, "PRONÓSTICO", 128, W - 90))
    center(d, 322, "DA PEÑA", font(76), fill=VERDE)
    comp = {"copa": "Copa do Rei", "europa": "UEFA Europa League", "laliga": "LaLiga EA Sports", "hypermotion": "LaLiga Hypermotion"}.get(datos.get("logo"))
    j = (datos.get("jornada") or "").strip()
    texto_comp = j if (j and not re.search(r"\bX$", j)) else comp
    if texto_comp:
        center(d, 432, texto_comp, fit(d, texto_comp, 40, W - 120), fill=(214, 240, 226))
    cy = 705
    escudo(img, 215, cy, datos.get("local"), siglas(nombre(datos, "local")))
    escudo(img, 865, cy, datos.get("visitante"), siglas(nombre(datos, "visitante")))
    center(d, cy - 43, "VS", font(80), fill=VERDE)
    nombres_bajo_escudos(d, datos, y=cy + 190)
    dia, hora = fecha_larga(datos.get("fecha_hora"))
    if dia:                                                       # píldora menta con el día y la hora
        cad = f"{dia} · {hora} h" if hora else dia
        f = fit(d, cad, 46, W - 200, 28)
        tw = d.textlength(cad, font=f)
        d.rounded_rectangle([W // 2 - tw / 2 - 40, 1038, W // 2 + tw / 2 + 40, 1112], 37, fill=VERDE)
        d.text((W // 2 - tw / 2, 1046), cad, font=f, fill=VERDE_OSCURO)
    center(d, 1158, "Cal será o resultado?", fit(d, "Cal será o resultado?", 62, W - 100, 36))
    etiquetas_1x2 = (("1", _corto(datos, "local")), ("X", "Empate"), ("2", _corto(datos, "visitante")))
    for (letra, txt), cx in zip(etiquetas_1x2, (215, 540, 865)):
        cap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(cap).ellipse([cx - 62, 1290, cx + 62, 1414], fill=(4, 30, 20, 190))
        img.paste(cap, (0, 0), cap)
        d = ImageDraw.Draw(img)
        d.ellipse([cx - 62, 1290, cx + 62, 1414], outline=VERDE, width=6)
        center(d, 1318, letra, font(70), x=cx)
        center(d, 1424, txt, fit(d, txt, 28, 300, 18), fill=(214, 240, 226), x=cx)
    center(d, 1488, "Responde co teu pronóstico!", fit(d, "Responde co teu pronóstico!", 40, W - 120, 26), fill=VERDE)
    pie(img, d)
    return img


# ---------------------------------------------------------------- esta semana na historia celeste: portada
def fondo_historico():
    """Fondo en blanco y negro teñido de celeste (aspecto de foto antigua), con viñeta y grano."""
    import random
    from PIL import ImageOps
    ruta = os.path.join(ASSETS, "fondos", "historia.jpg")
    if not os.path.exists(ruta):
        ruta = os.path.join(ASSETS, "fondos", "historia_provisional.jpg")
    gris = ImageOps.autocontrast(Image.open(ruta).convert("L").resize((W, H), Image.LANCZOS), cutoff=2)
    img = ImageOps.colorize(gris, black=(3, 10, 26), white=(120, 176, 226)).convert("RGB")
    img = Image.blend(img, Image.new("RGB", (W, H), (6, 22, 50)), 0.45)
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    for i in range(60):                                          # viñeta: oscurece los bordes
        vd.rectangle([i * 9, i * 16, W - i * 9, H - i * 16], outline=int(150 * (1 - i / 60) ** 2), width=18)
    img.paste(Image.new("RGB", (W, H), (2, 8, 20)), (0, 0), vig.filter(ImageFilter.GaussianBlur(40)))
    rnd = random.Random(7)                                       # grano de película
    grano = Image.new("L", (W // 2, H // 2))
    grano.putdata([rnd.randint(110, 146) for _ in range(W // 2 * H // 2)])
    grano = grano.resize((W, H), Image.NEAREST)
    return Image.blend(img, Image.merge("RGB", (grano, grano, grano)), 0.07)


def _texto_borde(d, y, txt, f, fill, borde=(4, 14, 34), grosor=7, x=W // 2):
    d.text((x - d.textlength(txt, font=f) / 2, y), txt, font=f, fill=fill, stroke_width=grosor, stroke_fill=borde)


def _rombo(d, cx, cy, r, fill):
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


def historia_portada(datos):
    global AZUL
    img = fondo_historico(); d = ImageDraw.Draw(img)
    CEL = (150, 208, 255)
    # marco fino de «cartel antiguo»
    d.rectangle([34, 34, W - 34, H - 34], outline=CEL, width=3)
    d.rectangle([48, 48, W - 48, H - 48], outline=(CEL[0] // 2, CEL[1] // 2, CEL[2] // 2), width=2)
    # título: la serie es lo principal
    l1, l2, l3 = datos.get("titulo_serie", ["ESTA SEMANA", "NA HISTORIA", "CELESTE"])
    _texto_borde(d, 130, l1, fit(d, l1, 150, W - 120), WHITE)
    _texto_borde(d, 285, l2, fit(d, l2, 150, W - 120), WHITE)
    f3 = fit(d, l3, 235, W - 100)
    _texto_borde(d, 440, l3, f3, CEL, grosor=9)
    # banda con el tema de la semana
    tema = datos.get("tema", "DERBIS GALEGOS DE NOVEMBRO")
    ft = fit(d, tema, 46, W - 230, 28)
    tw = d.textlength(tema, font=ft)
    d.rounded_rectangle([W // 2 - tw / 2 - 60, 735, W // 2 + tw / 2 + 60, 825], 45, fill=CEL)
    d.text((W // 2 - tw / 2, 750), tema, font=ft, fill=(5, 22, 52))
    _rombo(d, int(W // 2 - tw / 2 - 100), 780, 14, CEL)
    _rombo(d, int(W // 2 + tw / 2 + 100), 780, 14, CEL)
    # escudos
    cy = 1000
    escudo_mini(img, 300, cy, datos["local"], siglas(nombre(datos, "local")), r=105)
    escudo_mini(img, 780, cy, datos["visitante"], siglas(nombre(datos, "visitante")), r=105)
    d = ImageDraw.Draw(img)
    _texto_borde(d, cy - 40, "VS", font(76), CEL, grosor=5, x=540)
    # tres fechas
    y0 = 1190
    n = len(datos["fechas"])
    paso = 310
    x0 = W // 2 - (n - 1) * paso / 2
    for i, (anio, etiqueta) in enumerate(datos["fechas"]):
        cx = int(x0 + i * paso)
        cap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(cap).rounded_rectangle([cx - 140, y0, cx + 140, y0 + 150], 20, fill=(5, 20, 48, 215), outline=CEL + (255,), width=3)
        img.paste(cap, (0, 0), cap)
        d = ImageDraw.Draw(img)
        center(d, y0 + 10, str(anio), font(76), x=cx)
        center(d, y0 + 108, etiqueta, fit(d, etiqueta, 28, 260, 18), fill=CEL, x=cx)
    # invitación a pasar
    txt = datos.get("pie", "DESLIZA PARA VER OS PARTIDOS")
    fp = fit(d, txt, 40, W - 220, 26)
    _texto_borde(d, 1400, txt, fp, CEL, grosor=4)
    xm = W // 2
    for dx in (-24, 6):
        d.line([(xm + dx - 14, 1478), (xm + dx + 8, 1498), (xm + dx - 14, 1518)], fill=CEL, width=8, joint="curve")
    AZUL = (146, 202, 246)
    pie(img, d)
    return img


# ---------------------------------------------------------------- tal semana coma esta (partido histórico)
def efemeride(datos):
    img = fondo(); d = ImageDraw.Draw(img)
    serie = datos.get("serie", "ESTA SEMANA NA HISTORIA CELESTE")
    center(d, 140, serie, fit(d, serie, 44, W - 80, 28), fill=AZUL)
    center(d, 205, datos["titulo"], fit(d, datos["titulo"], 86, W - 100), fill=WHITE)
    y = 430
    for txt, tam, col in ((datos.get("fecha_texto"), 52, WHITE), (datos.get("competicion_texto"), 38, AZUL)):
        if txt:
            center(d, y, txt, fit(d, txt, tam, W - 100, 26), fill=col); y += 70
    encuentro(img, d, datos, f"{datos['goles_local']} - {datos['goles_visitante']}")
    if datos.get("frase"):
        for i, l in enumerate(_lineas(d, datos["frase"], font(46), W - 160, 2)):
            center(d, 1300 + i * 58, l, font(46), fill=AZUL)
    gl, gv = datos.get("goleadores_local", []), datos.get("goleadores_visitante", [])
    if gl or gv:
        y = 1415
        for lista, x in ((gl, 215), (gv, 865)):
            for i, g in enumerate(lista[:5]):
                center(d, y + i * 38, g, fit(d, g, 30, 420), fill=(214, 228, 246), x=x)
    pie(img, d)
    return img


# ---------------------------------------------------------------- entradas a la venta
def entradas(datos):
    img = fondo(); d = ImageDraw.Draw(img)
    titulo = "ENTRADAS VISITANTES" if datos.get("visitantes") else "ENTRADAS"
    cabecera(img, d, datos.get("tag", ""), titulo, None, ytitulo=205)
    logo = datos.get("logo")
    if logo in LOGOS and os.path.exists(os.path.join(ASSETS, "marca", LOGOS[logo])):
        pegar(img, os.path.join(ASSETS, "marca", LOGOS[logo]), 445, 322, (190, 190))
    cy = 705
    if datos.get("local_nombre") and datos.get("visitante_nombre"):
        escudo(img, 215, cy, datos.get("local"), siglas(datos["local_nombre"]))
        escudo(img, 865, cy, datos.get("visitante"), siglas(datos["visitante_nombre"]))
        center(d, cy - 43, "VS", font(80), fill=AZUL)
        nombres_bajo_escudos(d, datos, y=cy + 190)
    else:
        for l in _lineas(d, datos.get("partido") or datos.get("titulo", ""), font(60), W - 120, 3):
            center(d, 600, l, font(60))
    y = cy + 190 + 56 * 2 + 14
    sub = f"Xornada {datos['jornada']}" if datos.get("jornada") else (datos.get("torneo") if not logo else None)
    if sub:
        center(d, y, sub, fit(d, sub, 36, W - 100, 24), fill=(200, 218, 240)); y += 52
    ph = datos.get("partido_fecha_hora")
    if ph:
        dt = datetime.datetime.fromisoformat(ph)
        dias = ["luns", "martes", "mércores", "xoves", "venres", "sábado", "domingo"]
        cad = f"{dias[dt.weekday()].capitalize()} {dt.day:02d}/{dt.month:02d} · {dt:%H:%M} h"
        center(d, y, cad, fit(d, cad, 52, W - 100, 30), fill=AZUL); y += 80
    y = max(y + 10, 1150)
    fd = font_m(31)
    for i, texto in enumerate(datos.get("puntos", [])[:3], 1):
        cap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(cap).rounded_rectangle([40, y, W - 40, y + 118], 14, fill=(255, 255, 255, 30))
        img.paste(cap, (0, 0), cap)
        d = ImageDraw.Draw(img)
        cx, cyp = 98, y + 59
        d.ellipse([cx - 30, cyp - 30, cx + 30, cyp + 30], fill=AZUL)
        center(d, cyp - 25, str(i), font(38), fill=(10, 35, 57), x=cx)
        lineas = _lineas(d, texto, fd, 830, 2)
        yy = cyp - (len(lineas) * 38) // 2
        for l in lineas:
            d.text((155, yy), l, font=fd, fill=WHITE)
            yy += 38
        y += 134
    pie(img, d)
    return img


# ---------------------------------------------------------------- cumpleaños
def _cara(datos):
    """Cara del jugador (recorte con fondo transparente, de la web del club) o None si no hay foto."""
    ruta = datos.get("foto")
    if not ruta:
        return None
    ruta = ruta if os.path.isabs(ruta) else os.path.join(os.path.dirname(ASSETS), ruta)
    try:
        return Image.open(ruta).convert("RGBA")
    except Exception:
        return None


def _credito_fotos(img, y):
    """«📸 Fotos: Web oficial del RC Celta (@rccelta)», con la cámara dibujada (la tipografía no tiene emojis)."""
    d = ImageDraw.Draw(img)
    txt = "Fotos: Web oficial del RC Celta (@rccelta)"
    f = fit(d, txt, 34, W - 200, 22)
    tw = d.textlength(txt, font=f)
    x0 = (W - (tw + 54)) / 2
    c = (200, 220, 242)
    d.rounded_rectangle([x0, y + 8, x0 + 36, y + 32], 6, outline=c, width=3)
    d.rectangle([x0 + 9, y + 3, x0 + 20, y + 9], fill=c)
    d.ellipse([x0 + 11, y + 14, x0 + 25, y + 28], outline=c, width=3)
    d.text((x0 + 54, y + 20 - f.size * 0.7), txt, font=f, fill=c)


def _arroba(d, y, datos):
    """v76: @ de Instagram del jugador, como texto en la imagen (Instagram no permite etiquetas pulsables en historias publicadas por API).
    Devuelve la y siguiente (sin cambios si el jugador no tiene cuenta)."""
    if not datos.get("instagram"):
        return y
    arroba = "@" + datos["instagram"].lstrip("@")
    center(d, y + 14, arroba, fit(d, arroba, 46, W - 120, 28), fill=WHITE)
    return y + 74


def cumpleanos(datos):
    cara = _cara(datos)
    img = fondo(); d = ImageDraw.Draw(img)
    cabecera(img, d, datos.get("tag", ""), "FELIZ ANIVERSARIO", None, ytitulo=205)
    edad = str(datos.get("edad", ""))
    if cara is None:                                                      # sin foto: el diseño de siempre (círculo grande con la edad)
        cx, cy, r = W // 2, 640, 230
        sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sombra).ellipse([cx - r + 6, cy - r + 16, cx + r + 6, cy + r + 16], fill=(0, 0, 0, 90))
        sombra = sombra.filter(ImageFilter.GaussianBlur(12))
        img.paste(sombra, (0, 0), sombra)
        d = ImageDraw.Draw(img)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AZUL)
        d.ellipse([cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14], outline=WHITE, width=6)
        fe = font(250 if len(edad) < 3 else 190)
        bb = d.textbbox((0, 0), edad, font=fe)
        d.text((cx - (bb[0] + bb[2]) / 2, cy - 45 - (bb[1] + bb[3]) / 2), edad, font=fe, fill=(10, 35, 57))
        center(d, cy + 105, "ANOS", font(62), fill=(10, 35, 57), x=cx)
        y = 960
    else:                                                                 # con foto: el jugador «sale» del círculo y la edad va en una insignia
        cx, cy, r = W // 2, 745, 240
        sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sombra).ellipse([cx - r + 6, cy - r + 16, cx + r + 6, cy + r + 16], fill=(0, 0, 0, 100))
        sombra = sombra.filter(ImageFilter.GaussianBlur(14))
        img.paste(sombra, (0, 0), sombra)
        d = ImageDraw.Draw(img)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AZUL)
        d.ellipse([cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14], outline=WHITE, width=6)
        alto = 670
        cara = cara.resize((round(cara.width * alto / cara.height), alto), Image.LANCZOS)
        masc = Image.new("L", (W, H), 0)                                  # visible: el círculo y todo lo que queda por encima de su centro (la cabeza sobresale)
        md = ImageDraw.Draw(masc)
        md.ellipse([cx - r + 7, cy - r + 7, cx + r - 7, cy + r - 7], fill=255)
        md.rectangle([0, 0, W, cy], fill=255)
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        capa.paste(cara, (cx - cara.width // 2, cy + r - 16 - alto), cara)
        capa.putalpha(ImageChops.multiply(capa.getchannel("A"), masc))
        img.paste(capa, (0, 0), capa)
        d = ImageDraw.Draw(img)
        bx, by, br = cx + 200, cy + 182, 100                              # insignia con la edad
        d.ellipse([bx - br - 6, by - br - 6, bx + br + 6, by + br + 6], fill=WHITE)
        d.ellipse([bx - br, by - br, bx + br, by + br], fill=(10, 35, 57))
        fe = font(124 if len(edad) < 3 else 90)
        bb = d.textbbox((0, 0), edad, font=fe)
        d.text((bx - (bb[0] + bb[2]) / 2, by - 22 - (bb[1] + bb[3]) / 2), edad, font=fe, fill=WHITE)
        center(d, by + 34, "ANOS", font(34), fill=AZUL, x=bx)
        y = 1050
    lineas = _lineas(d, datos.get("nombre", ""), font(96), W - 100, 2)
    tam = 96 if len(lineas) == 1 else 84
    for l in lineas:
        center(d, y, l, fit(d, l, tam, W - 100, 50)); y += int(tam * 1.17)
    if cara is None:
        if datos.get("posicion"):
            center(d, y + 10, datos["posicion"], fit(d, datos["posicion"], 46, W - 120, 28), fill=AZUL); y += 80
        if datos.get("fecha"):
            center(d, y + 30, f"{datos['fecha']}", font(50), fill=(200, 218, 240)); y += 90
        y = _arroba(d, y + 15, datos)
        center(d, max(y + 60, 1380), "Parabéns da Marexada Celeste!", fit(d, "Parabéns da Marexada Celeste!", 52, W - 100, 30))
    else:                                                                 # con foto: posición y fecha en una sola línea, para que quepa también con nombres largos
        meta = " · ".join(x for x in (datos.get("posicion"), datos.get("fecha")) if x)
        if meta:
            center(d, y + 4, meta, fit(d, meta, 44, W - 120, 26), fill=AZUL); y += 64
        y = _arroba(d, y - 10, datos)
        yp = max(y + 34, 1325)
        center(d, yp, "Parabéns da Marexada Celeste!", fit(d, "Parabéns da Marexada Celeste!", 52, W - 100, 30))
        _credito_fotos(img, max(1408, yp + 83))
    pie(img, d)
    return img


# ---------------------------------------------------------------- previa en la sede
def _jarra():
    """Jarra de cerveza con asa a la derecha (cristal grueso, cerveza ámbar y espuma), dibujada al doble de tamaño."""
    k = 2
    pad, top, bot, alt, asa = 40, 250, 224, 330, 96
    w, h = (pad + top + asa + pad) * k, (alt + 100 + 50) * k
    x0, y0 = pad * k, 100 * k
    T, B, A = top * k, bot * k, alt * k
    off = (T - B) // 2
    cuerpo = [(x0, y0), (x0 + T, y0), (x0 + T - off, y0 + A), (x0 + off, y0 + A)]
    # asa: anillo de cristal pegado al lado derecho
    asa_l = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ad = ImageDraw.Draw(asa_l)
    ax0, ax1 = x0 + T - 30 * k, x0 + T + asa * k
    ay0, ay1 = y0 + int(A * 0.13), y0 + int(A * 0.78)
    ad.ellipse([ax0, ay0, ax1, ay1], fill=(255, 255, 255, 120), outline=(255, 255, 255, 215), width=5 * k)
    ad.ellipse([ax0 + 30 * k, ay0 + 30 * k, ax1 - 30 * k, ay1 - 30 * k], fill=(0, 0, 0, 0), outline=(255, 255, 255, 215), width=5 * k)
    im = asa_l
    # cerveza (degradado ámbar) recortada con la forma interior del vaso
    cerv = Image.new("RGBA", (w, h), (0, 0, 0, 0)); cd = ImageDraw.Draw(cerv)
    nivel, fondo_c = y0 + int(A * 0.12), y0 + A - 36 * k
    for y in range(nivel, fondo_c):
        t = (y - nivel) / (fondo_c - nivel)
        cd.line([(0, y), (w, y)], fill=(int(255 - 28 * t), int(203 - 84 * t), int(56 - 34 * t), 255))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon([(x0 + 14 * k, nivel), (x0 + T - 14 * k, nivel),
                                  (x0 + T - off - 12 * k, fondo_c), (x0 + off + 12 * k, fondo_c)], fill=255)
    im.paste(cerv, (0, 0), mask)
    # burbujas
    cb = Image.new("RGBA", (w, h), (0, 0, 0, 0)); bd = ImageDraw.Draw(cb)
    for bx, by, br in ((0.22, 0.88, 6), (0.40, 0.74, 5), (0.58, 0.82, 7), (0.76, 0.66, 5), (0.30, 0.55, 4), (0.62, 0.50, 6),
                       (0.48, 0.36, 4), (0.80, 0.34, 5), (0.20, 0.30, 5)):
        cx, cy = x0 + int(T * bx), y0 + int(A * by)
        bd.ellipse([cx - br * k, cy - br * k, cx + br * k, cy + br * k], fill=(255, 236, 160, 150))
    im = Image.alpha_composite(im, cb)
    d = ImageDraw.Draw(im)
    # espuma abundante que rebosa el borde y chorrea un poco
    crema = (255, 251, 238, 255)
    for fx, fy, fr in ((0.06, 0.03, 30), (0.22, -0.04, 40), (0.40, -0.10, 46), (0.58, -0.11, 46), (0.76, -0.05, 42), (0.94, 0.03, 30),
                       (0.14, 0.07, 34), (0.32, 0.05, 38), (0.50, 0.03, 40), (0.68, 0.05, 38), (0.86, 0.07, 34)):
        cx, cy = x0 + int(T * fx), y0 + int(A * fy)
        d.ellipse([cx - fr * k, cy - fr * k, cx + fr * k, cy + fr * k], fill=crema)
    d.polygon([(x0 + 2 * k, y0 + 6 * k), (x0 + T - 2 * k, y0 + 6 * k), (x0 + T - 12 * k, nivel + 14 * k), (x0 + 12 * k, nivel + 14 * k)], fill=crema)
    d.rounded_rectangle([x0 + 14 * k, nivel, x0 + 14 * k + 26 * k, nivel + 62 * k], 13 * k, fill=crema)       # chorreón
    d.rounded_rectangle([x0 + T - 14 * k - 20 * k, nivel, x0 + T - 14 * k, nivel + 34 * k], 10 * k, fill=crema)
    # cristal: relleno, base gruesa, costillas, contorno y brillo
    cg = Image.new("RGBA", (w, h), (0, 0, 0, 0)); g = ImageDraw.Draw(cg)
    g.polygon(cuerpo, fill=(255, 255, 255, 26))
    g.polygon([(x0 + off, y0 + A - 36 * k), (x0 + T - off, y0 + A - 36 * k), (x0 + T - off - 4 * k, y0 + A), (x0 + off + 4 * k, y0 + A)], fill=(255, 255, 255, 90))
    for f in (0.2, 0.4, 0.6, 0.8):
        xa, xb = x0 + int(T * f), x0 + off + int(B * f)
        g.line([(xa, nivel + 20 * k), (xb, y0 + A - 40 * k)], fill=(255, 255, 255, 46), width=4 * k)
    g.line(cuerpo + [cuerpo[0]], fill=(255, 255, 255, 205), width=7 * k, joint="curve")
    g.polygon([(x0 + 26 * k, nivel + 28 * k), (x0 + 50 * k, nivel + 28 * k), (x0 + off + 52 * k, y0 + A - 50 * k), (x0 + off + 30 * k, y0 + A - 50 * k)], fill=(255, 255, 255, 85))
    return Image.alpha_composite(im, cg)


def cervezas(img, cy=330, alto=480):
    """Dos jarras brindando, centradas en la imagen (cy = arriba de la escena)."""
    from PIL import ImageOps
    capa = Image.new("RGBA", (W * 2, alto * 2), (0, 0, 0, 0))
    der = _jarra().rotate(12, resample=Image.BICUBIC, expand=True)
    izq = ImageOps.mirror(_jarra()).rotate(-12, resample=Image.BICUBIC, expand=True)
    cx, base = W, alto * 2
    capa.paste(izq, (cx - izq.width + 150, base - izq.height - 10), izq)
    capa.paste(der, (cx - 150, base - der.height - 10), der)
    d = ImageDraw.Draw(capa)
    for px, py, pr in ((cx, 120, 12), (cx + 50, 60, 9), (cx - 55, 55, 8), (cx + 8, 190, 7), (cx - 110, 120, 6), (cx + 110, 110, 6)):
        d.ellipse([px - pr * 2, py - pr * 2, px + pr * 2, py + pr * 2], fill=(255, 226, 120, 235))
    capa = capa.resize((W, alto), Image.LANCZOS)
    img.paste(capa, (0, cy), capa)


def previa(datos):
    img = fondo(); d = ImageDraw.Draw(img)
    dia, hora = fecha_larga(datos.get("fecha_hora"))
    if not hora:
        raise ValueError("La previa necesita la hora del partido en fecha_hora (por ejemplo 'Dom 08/11 · 18:30').")
    h, m = map(int, hora.split(":"))
    desde = datos.get("horas_antes", 2)
    h_prev = f"{(h - desde) % 24:02d}:{m:02d}"
    center(d, 130, "REAL CLUB CELTA", font(44), fill=AZUL)
    center(d, 185, "PREVIA", font(120))
    cervezas(img, cy=352)
    d = ImageDraw.Draw(img)
    center(d, 825, "NA NOSA SEDE", font(40), fill=AZUL)
    center(d, 880, "CAFETERÍA KIEV", fit(d, "CAFETERÍA KIEV", 92, W - 100))
    center(d, 1020, f"{h_prev} h", font(150), fill=AZUL)
    # el partido
    ycard = 1260
    cap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(cap).rounded_rectangle([70, ycard, W - 70, ycard + 230], 24, fill=(255, 255, 255, 34))
    img.paste(cap, (0, 0), cap)
    escudo_mini(img, 190, ycard + 90, datos["local"], siglas(nombre(datos, "local")), r=62)
    escudo_mini(img, W - 190, ycard + 90, datos["visitante"], siglas(nombre(datos, "visitante")), r=62)
    d = ImageDraw.Draw(img)
    center(d, ycard + 28, "VS", font(56), fill=AZUL)
    center(d, ycard + 108, f"{hora} h", font(64))
    linea = " · ".join(x for x in (datos.get("lugar"), dia) if x)
    if linea:
        center(d, ycard + 178, linea, fit(d, linea, 30, 520), fill=(200, 218, 240))
    pie(img, d)
    return img


# ---------------------------------------------------------------- gol en directo (v53)
def fondo_gol():
    """Foto de la grada celebrando (assets/fondos/fondo_gol.jpg) SIN deformarla: una capa de fondo desenfocada y teñida de azul,
    y encima la foto nítida arriba, que se funde con el azul hacia abajo."""
    nombre = _FOTO_ESPECIAL if _FOTO_ESPECIAL and os.path.isfile(os.path.join(ASSETS, "fondos", _FOTO_ESPECIAL)) else "fondo_gol.jpg"   # v80: en Europa League, el fondo de Europa
    foto = Image.open(os.path.join(ASSETS, "fondos", nombre)).convert("RGB")

    def cubrir(w, h, cx=0.46):
        k = max(w / foto.width, h / foto.height)
        im = foto.resize((math.ceil(foto.width * k), math.ceil(foto.height * k)), Image.LANCZOS)
        x = int((im.width - w) * cx)
        return im.crop((x, 0, x + w, h))

    base = Image.blend(cubrir(W, H).filter(ImageFilter.GaussianBlur(9)), Image.new("RGB", (W, H), NAVY), 0.74)
    alto = 1240
    arriba = Image.blend(cubrir(W, alto), Image.new("RGB", (W, alto), NAVY), 0.34)
    mascara = Image.new("L", (W, alto), 255)
    md = ImageDraw.Draw(mascara)
    for y in range(alto):
        md.line([(0, y), (W, y)], fill=int(255 * min(1, max(0, 1 - (y - 640) / 560)) ** 1.2))
    base.paste(arriba, (0, 0), mascara)
    sombra = Image.new("L", (W, H), 0)                           # oscurece arriba (perfil de Instagram) y abajo (pie)
    sd = ImageDraw.Draw(sombra)
    for y in range(H):
        sd.line([(0, y), (W, y)], fill=int(max(0, 1 - y / 360) * 110 + max(0, (y - 1380) / 540) * 130))
    base.paste(Image.new("RGB", (W, H), (4, 12, 30)), (0, 0), sombra)
    return base


def fondo_foto(nombre, tinte=0.5, cx=0.5):
    """v64: igual que fondo_gol() pero con cualquier foto de assets/fondos, SIN deformarla (la foto nítida arriba, que se funde con el color de la
    competición hacia abajo, y una capa desenfocada detrás). El tinte oscurece algo más la foto para que el texto se lea bien."""
    foto = Image.open(os.path.join(ASSETS, "fondos", nombre)).convert("RGB")

    def cubrir(w, h):
        k = max(w / foto.width, h / foto.height)
        im = foto.resize((math.ceil(foto.width * k), math.ceil(foto.height * k)), Image.LANCZOS)
        x = int((im.width - w) * cx)
        return im.crop((x, 0, x + w, h))

    base = Image.blend(cubrir(W, H).filter(ImageFilter.GaussianBlur(9)), Image.new("RGB", (W, H), NAVY), 0.78)
    alto = 1240
    arriba = Image.blend(cubrir(W, alto), Image.new("RGB", (W, alto), NAVY), tinte)
    mascara = Image.new("L", (W, alto), 255)
    md = ImageDraw.Draw(mascara)
    for y in range(alto):
        md.line([(0, y), (W, y)], fill=int(255 * min(1, max(0, 1 - (y - 640) / 560)) ** 1.2))
    base.paste(arriba, (0, 0), mascara)
    sombra = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sombra)
    for y in range(H):
        sd.line([(0, y), (W, y)], fill=int(max(0, 1 - y / 520) * 100 + max(0, (y - 1380) / 540) * 130))
    base.paste(Image.new("RGB", (W, H), (4, 12, 30)), (0, 0), sombra)
    return base


def _brillo(img, caja, color, alpha=210, desenfoque=24):
    cap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(cap).ellipse(caja, fill=color + (alpha,))
    cap = cap.filter(ImageFilter.GaussianBlur(desenfoque))
    img.paste(cap, (0, 0), cap)


def _tarjeta_icono(d, cx, cy, alto, doble=False):
    """v84: tarjeta roja; con doble=True, una amarilla detrás y la roja delante (doble amarilla = expulsión)."""
    w = int(alto * 0.70)
    def carta(x, y, color):
        d.rounded_rectangle([x - w // 2, y - alto // 2, x + w // 2, y + alto // 2], max(4, int(w * 0.14)), fill=color, outline=(255, 255, 255), width=3)
    if doble:
        carta(int(cx - w * 0.36), int(cy - alto * 0.05), (250, 204, 38))
        carta(int(cx + w * 0.36), int(cy + alto * 0.05), (226, 28, 36))
    else:
        carta(cx, cy, (226, 28, 36))


def _foto_goleador(datos):
    """v79: cara del goleador (assets/caras) o None. En un gol en propia puerta el goleador es del rival: nunca se pone foto."""
    if not CARAS_EN_GOL or (datos.get("modo") or "").lower() == "propia" or datos.get("tipo") not in (None, "gol"):
        return None
    try:
        import caras
        ruta = caras.buscar(datos.get("goleador") or "")
        return Image.open(ruta).convert("RGBA") if ruta else None
    except Exception:
        return None


def _cara_gol(img, cara, cx, cy, r):
    """Cara recortada dentro de un círculo azul con aro blanco y un resplandor detrás."""
    _brillo(img, (cx - r - 40, cy - r - 40, cx + r + 40, cy + r + 40), AZUL, alpha=120, desenfoque=26)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6], fill=WHITE)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AZUL)
    ancho = int(2 * r * 1.12)
    k = ancho / cara.width
    cara = cara.resize((ancho, int(cara.height * k)), Image.LANCZOS)
    arriba = cara.getchannel("A").getbbox()[1]
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    capa.paste(cara, (cx - ancho // 2, cy - r + 8 - arriba), cara)
    mascara = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mascara).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    from PIL import ImageChops
    capa.putalpha(ImageChops.multiply(capa.getchannel("A"), mascara))
    img.paste(capa, (0, 0), capa)


def _cara_grande(img, cara, cx, ytop, ancho, alto, fundido):
    """v82: el jugador recortado, grande, con un resplandor detrás y el borde de abajo difuminado (el nombre se monta encima)."""
    from PIL import ImageChops
    k = ancho / cara.width
    c = cara.resize((ancho, int(cara.height * k)), Image.LANCZOS)
    t = c.getchannel("A").getbbox()[1]
    c = c.crop((0, t, ancho, min(c.height, t + alto)))
    _brillo(img, (cx - ancho * 0.62, ytop + alto * 0.05, cx + ancho * 0.62, ytop + alto * 0.95), AZUL, alpha=150, desenfoque=46)
    m = Image.new("L", c.size, 255)
    dm = ImageDraw.Draw(m)
    for i in range(fundido):                                     # degradado de opacidad en el borde inferior
        dm.line([(0, c.height - 1 - i), (c.width, c.height - 1 - i)], fill=int(255 * i / fundido))
    c.putalpha(ImageChops.multiply(c.getchannel("A"), m))
    img.paste(c, (cx - ancho // 2, int(ytop)), c)
    return c.height


def gol(datos):
    """«¡GOOOOOOL!» con quién marcó, el minuto y el marcador en ese momento. Solo para goles del Celta."""
    img = fondo_gol(); d = ImageDraw.Draw(img)
    foto = _foto_goleador(datos)                                  # v79: con foto del goleador, cabecera más compacta
    y = SEGURA_SUP if foto is not None else SEGURA_SUP - 40        # v84: sin foto, el logo de la competición es más grande y sube para no dejar hueco encima
    logo = datos.get("logo")
    if logo in LOGOS:
        tl = 60 if foto is not None else 190
        _logo_competicion(img, logo, W // 2, y, tl)
        y += tl + (12 if foto is not None else 14)
    # --- título
    titulo = datos.get("titulo") or "¡GOOOOOOL!"
    f = fit(d, titulo, 146 if foto is not None else 200, W - 130, 90)
    bb = d.textbbox((0, 0), titulo, font=f, stroke_width=10)
    cap = Image.new("RGBA", (W, H), (0, 0, 0, 0))                  # resplandor azul detrás de las letras
    ImageDraw.Draw(cap).text((W / 2 - d.textlength(titulo, font=f) / 2, y - bb[1]), titulo, font=f, fill=AZUL + (255,), stroke_width=22, stroke_fill=AZUL + (255,))
    cap = cap.filter(ImageFilter.GaussianBlur(20))
    img.paste(cap, (0, 0), cap)
    d = ImageDraw.Draw(img)
    _texto_borde(d, y - bb[1], titulo, f, WHITE, borde=(4, 14, 34), grosor=10)
    y += bb[3] - bb[1] + 22
    _texto_borde(d, y, _tag_v33(datos), font(36), AZUL, grosor=5)
    yl = y + 66
    _filete(d, yl)
    # --- quién y cuándo
    nom = (datos.get("goleador") or "").upper()
    apretado = foto is not None and (len(_nombre_lineas(d, nom, 104, W - 110)) > 1 or (datos.get("modo") or "").lower() in ("penalti", "propia"))
    try:                                                          # v83: cuenta de Instagram del goleador (con o sin foto); no en propia puerta ni en tarjetas/penaltis parados
        import caras
        cuenta = None if ((datos.get("modo") or "").lower() == "propia" or datos.get("tipo") not in (None, "gol")) else caras.instagram_de(datos.get("goleador") or "")
    except Exception:
        cuenta = None
    if foto is not None:                                          # v79: con foto, el diseño se compacta (sin «en directo» y escudos más pequeños)
        dos = len(_nombre_lineas(d, nom, 104, W - 110)) > 1           # v82: el tamaño de la cara se calcula con el hueco que queda (nombre en dos líneas, «de penalti»...)
        B = 336 - (52 if (datos.get("modo") or "").lower() in ("penalti", "propia") else 0) - (80 if dos else 0)
        k = max(0.70, min(1.30, (B - (44 if cuenta else 4)) / 280))
        AN, FH, barbilla = int(356 * k), int(340 * k), int(282 * k)
        y = yl + 14
        _cara_grande(img, foto, W // 2, y, AN, FH, max(30, FH - barbilla))
        globals()["USO_FOTOS"] = True
        d = ImageDraw.Draw(img)
        if cuenta:                                                # «@cuenta» en una píldora oscura bajo la barbilla; Instagram pone encima la mención pulsable
            arroba = "@" + cuenta
            fa = fit(d, arroba, 38, W - 260, 24)
            wa = d.textlength(arroba, font=fa)
            yp = y + barbilla - 14
            d.rounded_rectangle([W / 2 - wa / 2 - 26, yp, W / 2 + wa / 2 + 26, yp + 52], 26, fill=(4, 14, 34, 235), outline=AZUL, width=2)
            ba = d.textbbox((0, 0), "@Ag", font=fa)
            d.text((W / 2 - wa / 2, yp + 26 - (ba[1] + ba[3]) / 2), arroba, font=fa, fill=WHITE)
            globals()["ULTIMA_ETIQUETA"] = (0.5, round((yp + 26) / H, 3))
            y = yp + 52 + 8
        else:
            y = y + barbilla + 4
    else:
        y = yl + 40
    nom = (datos.get("goleador") or "").upper()
    tam = 104
    lineas = _nombre_lineas(d, nom, tam, W - 110)
    if len(lineas) > 1:
        tam = 76 if apretado else 92
    for l in lineas:
        fl = fit(d, l, tam, W - 90, 44)
        bl = d.textbbox((0, 0), l, font=fl, stroke_width=7)
        _texto_borde(d, y - bl[1], l, fl, WHITE, borde=(4, 14, 34), grosor=7)
        y += int(tam * 1.06)
    modo = datos.get("etiqueta") or {"penalti": "DE PENALTI", "propia": "EN PROPIA PUERTA"}.get((datos.get("modo") or "").lower())     # v84: «etiqueta» para tarjetas y penaltis parados
    if modo:
        grande = bool(datos.get("etiqueta"))                      # v84: en tarjetas y penaltis parados la etiqueta es más grande
        center(d, y + 2, modo, fit(d, modo, 46 if grande else 36, W - 100, 22), fill=AZUL)
        y += 62 if grande else 52
    if cuenta and foto is None:                                   # v83: sin foto, «@cuenta» en una píldora bajo el nombre; Instagram pone encima la mención pulsable
        arroba = "@" + cuenta
        fa = fit(d, arroba, 38, W - 260, 24)
        wa = d.textlength(arroba, font=fa)
        yp = y + 4
        d.rounded_rectangle([W / 2 - wa / 2 - 26, yp, W / 2 + wa / 2 + 26, yp + 52], 26, fill=(4, 14, 34, 235), outline=AZUL, width=2)
        ba = d.textbbox((0, 0), "@Ag", font=fa)
        d.text((W / 2 - wa / 2, yp + 26 - (ba[1] + ba[3]) / 2), arroba, font=fa, fill=WHITE)
        globals()["ULTIMA_ETIQUETA"] = (0.5, round((yp + 26) / H, 3))
        y = yp + 52
    y += 22
    mi = str(datos.get("minuto") or "").strip()
    if mi:
        fm = font(84)
        wm = d.textlength(mi, font=fm)
        icono = datos.get("icono")                                # v84: tarjeta roja (una) o doble amarilla (amarilla + roja) en vez del balón
        iw = 92 if icono == "doble" else 62
        ancho = wm + iw + 56 + 50
        x0 = W / 2 - ancho / 2
        d.rounded_rectangle([x0, y, x0 + ancho, y + 112], 56, fill=AZUL)
        if icono in ("roja", "doble"):
            _tarjeta_icono(d, int(x0 + 30 + iw / 2), y + 56, 76, icono == "doble")
        else:
            _balon(d, int(x0 + 30 + 31), y + 56, 31)
        bm = d.textbbox((0, 0), "8", font=fm)
        d.text((x0 + 30 + iw + 22, y + 56 - (bm[1] + bm[3]) / 2), mi, font=fm, fill=NAVY)
        y += 112
    # --- marcador con los dos escudos
    r = (58 if apretado else 68) if foto is not None else 98
    cy = y + (30 if apretado else 38 if foto is not None else 70) + r
    local_marca = datos.get("lado") == "local"
    nlins = 1                                                     # líneas máximas de los nombres bajo los escudos (para colocar el crédito)
    for lado, x in (("local", 190), ("visitante", 890)):
        if (lado == "local") == local_marca:
            _brillo(img, (x - r - 30, cy - r - 30, x + r + 30, cy + r + 30), AZUL, alpha=105, desenfoque=22)
        d = ImageDraw.Draw(img)
        _escudo_redondo(img, x, cy, datos[lado], siglas(nombre(datos, lado)), r=r)
        lins = _nombre_lineas(d, nombre(datos, lado), 34, 330)
        nlins = max(nlins, len(lins))
        for i, l in enumerate(lins):
            _texto_borde(d, cy + r + 22 + i * 42, l, fit(d, l, 34, 330), WHITE, grosor=4, x=x)
    a, b = str(datos["goles_local"]), str(datos["goles_visitante"])
    tam, hueco, barra = 230, 30, 56
    while tam > 90:
        fs = font(tam)
        total = d.textlength(a, font=fs) + d.textlength(b, font=fs) + 2 * hueco + barra
        if total <= 440:
            break
        tam -= 6
    fs = font(tam)
    bn = d.textbbox((0, 0), "8", font=fs)
    ty = cy - (bn[1] + bn[3]) / 2
    x0 = W / 2 - total / 2
    wa = d.textlength(a, font=fs)
    _texto_borde(d, ty, a, fs, AZUL if local_marca else WHITE, grosor=8, x=x0 + wa / 2)
    d.rounded_rectangle([x0 + wa + hueco, cy - 8, x0 + wa + hueco + barra, cy + 8], 8, fill=AZUL)
    _texto_borde(d, ty, b, fs, WHITE if local_marca else AZUL, grosor=8, x=x0 + wa + 2 * hueco + barra + d.textlength(b, font=fs) / 2)
    if foto is None:
        # --- «en directo»
        yp = min(FIN_CONTENIDO - 76, cy + r + 22 + 2 * 42 + 40)
        texto = "EN DIRECTO"
        fd = font(36)
        ancho = d.textlength(texto, font=fd) + 40 + 56
        x0 = W / 2 - ancho / 2
        _rgba(img, [x0, yp, x0 + ancho, yp + 76], 38, (4, 12, 30, 150), borde=(255, 255, 255, 90), grosor=2)
        d = ImageDraw.Draw(img)
        d.ellipse([x0 + 26, yp + 26, x0 + 50, yp + 50], fill=(238, 52, 52))
        d.text((x0 + 70, yp + 38 - fd.size * 0.70), texto, font=fd, fill=WHITE)
    else:                                                         # v79: crédito obligatorio de la foto
        _credito_fotos(img, min(FIN_CONTENIDO - 40, cy + r + 22 + nlins * 42 + 12))
    _pie_v39(img, d)
    return img


def acabado(img):
    """v60: toque final de todas las historias: halo del color de la competición arriba, viñeteado en los bordes y un grano muy fino."""
    from PIL import ImageChops
    img = img.convert("RGB")
    halo = Image.new("L", img.size, 0)
    hd = ImageDraw.Draw(halo)
    for y in range(430):
        hd.line([(0, y), (img.width, y)], fill=int(72 * (1 - y / 430) ** 1.7))
    img.paste(Image.new("RGB", img.size, AZUL), (0, 0), halo)
    grad = Image.radial_gradient("L").point(lambda v: int(max(0, v - 120) * 0.42)).resize(img.size, Image.BICUBIC)
    img.paste(Image.new("RGB", img.size, (2, 8, 20)), (0, 0), grad)
    ruido = Image.effect_noise(img.size, 26).convert("RGB")
    return Image.blend(img, ImageChops.overlay(img, ruido), 0.16)



# ---------------------------------------------------------------- Tesouros Celestes (v71): 3 historias por miércoles (portada, datos, peche)
CEL = (150, 208, 255)
PLATA = (196, 214, 232)
OSCURO = (5, 22, 52)


def _ft(nombre, tam):
    return ImageFont.truetype(os.path.join(ASSETS, "fuentes", nombre), int(tam))


def f_disp(t):
    return _ft("BigShoulders-Bold.ttf", t)          # números y titulares: condensada de marcador de estadio


def f_serif(t):
    return _ft("Lora-Regular.ttf", t)               # textos largos: serif editorial


def f_serif_b(t):
    return _ft("Lora-Bold.ttf", t)


def f_serif_i(t):
    return _ft("Lora-Italic.ttf", t)


def _parrafo(d, texto, ancho, alto_max, tam_max, tam_min, fuente=None, interlineado=1.36):
    """Parte `texto` en líneas con la letra más grande que quepa en `alto_max`; si aun así sobra, corta con «…». -> (líneas, fuente, paso)."""
    fuente = fuente or font_m
    for tam in range(int(tam_max), int(tam_min) - 1, -2):
        f = fuente(tam)
        lineas, actual = [], ""
        for p in texto.split():
            prueba = (actual + " " + p).strip()
            if d.textlength(prueba, font=f) <= ancho or not actual:
                actual = prueba
            else:
                lineas.append(actual)
                actual = p
        if actual:
            lineas.append(actual)
        paso = int(tam * interlineado)
        if len(lineas) * paso <= alto_max:
            return lineas, f, paso
    lineas = lineas[:max(1, int(alto_max // paso))]
    lineas[-1] = lineas[-1].rstrip(" .,;:") + "…"
    return lineas, f, paso


def _componer(img, cap):
    img.paste(cap, (0, 0), cap)


def _brillo_suave(img, cx, cy, radio, alfa=170, color=CEL):
    """Resplandor suave y circular (se desvanece del todo antes de llegar al borde: sin cortes rectos)."""
    lado = 2 * radio
    m = Image.new("L", (lado, lado), 0)
    ImageDraw.Draw(m).ellipse([radio * 0.5, radio * 0.5, radio * 1.5, radio * 1.5], fill=alfa)
    m = m.filter(ImageFilter.GaussianBlur(radio * 0.2))
    cap = Image.new("RGBA", (W, H), color + (0,))
    masc = Image.new("L", (W, H), 0)
    masc.paste(m, (cx - radio, cy - radio))
    cap.putalpha(masc)
    _componer(img, cap)


def _esp(d, cx, y, txt, f, fill, esp=6, sombra=False):
    """Texto con espaciado entre letras, centrado en cx. Devuelve el ancho."""
    ancho = sum(d.textlength(c, font=f) for c in txt) + esp * (len(txt) - 1)
    x = cx - ancho / 2
    for c in txt:
        if sombra:
            d.text((x + 2, y + 3), c, font=f, fill=(2, 8, 22))
        d.text((x, y), c, font=f, fill=fill)
        x += d.textlength(c, font=f) + esp
    return ancho


def _regla(d, x0, x1, y, color=CEL, grosor=2):
    d.line([(x0, y), (x1, y)], fill=color, width=grosor)


def _foto_tesouros(datos):
    """Foto de fondo de la edición: las noites europeas usan los recortes `europa_*`; el resto, las demás fotos de assets/fondos_tesouros
    (si hay varias, van rotando según el número de edición). Para añadir fotos basta con dejarlas en esa carpeta."""
    carpeta = os.path.join(ASSETS, "fondos_tesouros")
    if not os.path.isdir(carpeta):
        return None
    fotos = sorted(f for f in os.listdir(carpeta) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
    europea = bool(datos.get("europea")) or "europ" in (datos.get("categoria") or "").lower()
    cand = [f for f in fotos if f.startswith("europa_") == europea] or fotos
    return os.path.join(carpeta, cand[int(datos.get("num") or 0) % len(cand)]) if cand else None


def _fondo_foto(datos, yband):
    """Fondo con la foto de la peña teñida de azul noche: si es apaisada va a todo el ancho (nítida, con los bordes difuminados) sobre una
    versión borrosa de sí misma; si es vertical (recorte de periódico) ocupa toda la historia."""
    import random
    from PIL import ImageOps
    ruta = _foto_tesouros(datos)
    if not ruta:
        return fondo_historico()
    foto = Image.open(ruta).convert("L")
    w, h = foto.size
    if w > h:
        base = ImageOps.fit(foto, (W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(22))
        bh = round(W * h / w)
        banda = foto.resize((W, bh), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2.2, percent=130, threshold=2))
        masc = Image.new("L", (W, bh), 255)
        md = ImageDraw.Draw(masc)
        borde = int(bh * 0.24)
        for i in range(borde):
            v = int(255 * (i / borde) ** 1.4)
            md.line([(0, i), (W, i)], fill=v)
            md.line([(0, bh - 1 - i), (W, bh - 1 - i)], fill=v)
        base.paste(banda, (0, int(yband - bh / 2)), masc)
    else:
        base = ImageOps.fit(foto, (W, H), Image.LANCZOS)
    gris = ImageOps.autocontrast(base, cutoff=1).point(lambda v: int(255 * (v / 255) ** 1.25))
    img = ImageOps.colorize(gris, black=(3, 10, 26), white=(168, 212, 246)).convert("RGB")
    img = Image.blend(img, Image.new("RGB", (W, H), (6, 22, 50)), 0.16)
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    for i in range(60):
        vd.rectangle([i * 9, i * 16, W - i * 9, H - i * 16], outline=int(150 * (1 - i / 60) ** 2), width=18)
    img.paste(Image.new("RGB", (W, H), (2, 8, 20)), (0, 0), vig.filter(ImageFilter.GaussianBlur(40)))
    rnd = random.Random(7)
    grano = Image.new("L", (W // 2, H // 2))
    grano.putdata([rnd.randint(110, 146) for _ in range(W // 2 * H // 2)])
    grano = grano.resize((W, H), Image.NEAREST)
    return Image.blend(img, Image.merge("RGB", (grano, grano, grano)), 0.07)


ANCLAS = {   # (y, oscuridad 0-255): claro donde se ve la foto, oscuro donde hay texto
    1: [(0, 215), (300, 190), (400, 55), (930, 60), (1020, 175), (1200, 205), (1466, 215), (1920, 230)],
    2: [(0, 215), (170, 195), (235, 55), (780, 70), (850, 185), (1100, 205), (1920, 230)],
    3: [(0, 215), (160, 195), (230, 60), (760, 70), (860, 185), (1100, 205), (1920, 230)],
}


def _fondo_almanaque(datos, yband=640, foco=(540, 760), radio=620, alfa=95):
    """Fondo de foto antigua, sobrio: la foto se ve en el centro y se oscurece arriba y abajo para que el texto se lea; marco fino con esquinas."""
    img = _fondo_foto(datos, yband)
    cap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(cap)
    anclas = ANCLAS.get(datos.get("pantalla", 1), ANCLAS[1])
    for y in range(H):
        for (y0, a0), (y1, a1) in zip(anclas, anclas[1:]):
            if y0 <= y <= y1:
                a = a0 + (a1 - a0) * (y - y0) / (y1 - y0)
                break
        dd.line([(0, y), (W, y)], fill=(3, 10, 28, int(a)))
    _componer(img, cap)
    if foco:
        _brillo_suave(img, foco[0], foco[1], radio, max(40, alfa - 40))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, W - 40, H - 40], outline=CEL, width=2)
    L = 54                                                                # esquinas dobles
    for sx, sy in ((40, 40), (W - 40, 40), (40, H - 40), (W - 40, H - 40)):
        dx = 1 if sx < W / 2 else -1
        dy = 1 if sy < H / 2 else -1
        d.line([(sx + dx * 14, sy + dy * 14), (sx + dx * (14 + L), sy + dy * 14)], fill=CEL, width=4)
        d.line([(sx + dx * 14, sy + dy * 14), (sx + dx * 14, sy + dy * (14 + L))], fill=CEL, width=4)
    return img


def _cabecera(img, grande=True):
    """Cabecera de publicación: «TESOUROS CELESTES» entre filetes."""
    d = ImageDraw.Draw(img)
    if grande:
        y = 124
        ancho = _esp(d, W // 2, y, "TESOUROS CELESTES", f_disp(100), WHITE, 10, sombra=True)
        yl = y + 60
        _regla(d, 96, W // 2 - ancho / 2 - 34, yl, CEL, 3); _regla(d, W // 2 + ancho / 2 + 34, W - 96, yl, CEL, 3)
        _esp(d, W // 2, y + 122, "ESTA SEMANA NA HISTORIA CELESTE", font_m(26), PLATA, 6)
        _regla(d, 96, W - 96, y + 174, (CEL[0] // 2, CEL[1] // 2, CEL[2] // 2), 2)
    else:
        y = 112
        ancho = _esp(d, W // 2, y, "TESOUROS CELESTES", f_disp(58), WHITE, 9, sombra=True)
        yl = y + 35
        _regla(d, 96, W // 2 - ancho / 2 - 30, yl, CEL, 2); _regla(d, W // 2 + ancho / 2 + 30, W - 96, yl, CEL, 2)


def _sello_anos(img, y, anos):
    """«HAI 27 ANOS» como sello tipográfico: número enorme entre HAI y ANOS, flanqueado por filetes con rombos."""
    d = ImageDraw.Draw(img)
    num = str(anos)
    palabra = "ANO" if anos == 1 else "ANOS"
    fn, ft = f_disp(215), f_disp(80)
    esp = 9
    ww = lambda t: sum(d.textlength(c, font=ft) for c in t) + esp * (len(t) - 1)
    w_hai, w_anos, w_n = ww("HAI"), ww(palabra), d.textlength(num, font=fn)
    gap = 30
    total = w_hai + gap + w_n + gap + w_anos
    x0 = (W - total) / 2
    bn = d.textbbox((0, 0), num, font=fn)
    h_n = bn[3] - bn[1]
    cy = y + h_n / 2
    _brillo_suave(img, W // 2, int(cy), 330, 120)
    d = ImageDraw.Draw(img)
    d.text((x0 + w_hai + gap + 3, y - bn[1] + 5), num, font=fn, fill=(2, 8, 22))               # sombra
    d.text((x0 + w_hai + gap, y - bn[1]), num, font=fn, fill=WHITE)
    bt = d.textbbox((0, 0), "HAI", font=ft)
    ys = y + h_n - bt[3]
    x = x0
    for c in "HAI":
        d.text((x, ys), c, font=ft, fill=CEL)
        x += d.textlength(c, font=ft) + esp
    x = x0 + w_hai + gap + w_n + gap
    for c in palabra:
        d.text((x, ys), c, font=ft, fill=CEL)
        x += d.textlength(c, font=ft) + esp
    xi, xd = x0 - 40, x0 + total + 40
    _regla(d, 96, xi - 22, cy, CEL, 3); _regla(d, xd + 22, W - 96, cy, CEL, 3)
    _rombo(d, int(xi), int(cy), 9, CEL); _rombo(d, int(xd), int(cy), 9, CEL)


def _invitacion(img, y):
    """Invitación a deslizar: pastilla oscura con el texto bien legible y tres flechas que se van apagando."""
    d = ImageDraw.Draw(img)
    txt = "DESLIZA PARA VER A HISTORIA"
    f = font(32)
    esp = 3
    w = sum(d.textlength(c, font=f) for c in txt) + esp * (len(txt) - 1)
    ancho_fl = 74
    total = 44 + w + 24 + ancho_fl + 38
    x0 = W / 2 - total / 2
    _rgba(img, [x0, y, x0 + total, y + 66], 33, (3, 14, 36, 240), borde=CEL + (255,), grosor=3)
    d = ImageDraw.Draw(img)
    x = x0 + 44
    for c in txt:
        d.text((x, y + 33 - 26), c, font=f, fill=WHITE)
        x += d.textlength(c, font=f) + esp
    xa = x0 + 44 + w + 24
    for i, alfa in enumerate((1.0, 0.62, 0.32)):
        col = tuple(int(CEL[k] * alfa + (3, 14, 36)[k] * (1 - alfa)) for k in range(3))
        xx = xa + i * 22
        d.line([(xx, y + 20), (xx + 12, y + 33), (xx, y + 46)], fill=col, width=6, joint="curve")


def _barras(img, actual, total, y=1432):
    d = ImageDraw.Draw(img)
    ancho, hueco = 74, 14
    x0 = W // 2 - (total * ancho + (total - 1) * hueco) / 2
    for i in range(total):
        x = x0 + i * (ancho + hueco)
        d.rounded_rectangle([x, y - 4, x + ancho, y + 4], 4, fill=CEL if i + 1 == actual else (CEL[0] // 3, CEL[1] // 3, CEL[2] // 3))


def _escudo_aro(img, cx, cy, slug, sig, r):
    _brillo_suave(img, cx, cy, int(r * 2.1), 150)
    escudo_mini(img, cx, cy, slug, sig, r=r)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r - 11, cy - r - 11, cx + r + 11, cy + r + 11], outline=CEL, width=4)
    d.ellipse([cx - r - 24, cy - r - 24, cx + r + 24, cy + r + 24], outline=(CEL[0] // 2, CEL[1] // 2, CEL[2] // 2), width=2)


def _marco_texto(img, y, texto, alto_max, tam_max, tam_min, fuente, x0=84, rotulo=None):
    """Panel oscuro con filete fino y texto de lectura cómoda (serif). Devuelve la y del final."""
    d = ImageDraw.Draw(img)
    y_txt = y + (74 if rotulo else 40)
    lineas, f, paso = _parrafo(d, texto, W - 2 * x0 - 2 * 52, alto_max - (y_txt - y) - 44, tam_max, tam_min, fuente, 1.38)
    alto = (y_txt - y) + len(lineas) * paso + 40
    _rgba(img, [x0, y, W - x0, y + alto], 8, (3, 14, 36, 214), borde=CEL + (150,), grosor=2)
    dd = ImageDraw.Draw(img)
    dd.rectangle([x0, y, x0 + 8, y + alto], fill=CEL)                       # barra celeste a la izquierda
    if rotulo:
        _esp(dd, W // 2 + 4, y + 26, rotulo, font_m(24), CEL, 6)
    for i, ln in enumerate(lineas):
        dd.text((x0 + 52, y_txt + i * paso), ln, font=f, fill=WHITE)
    return y + alto


def almanaque(datos):
    global AZUL
    p, total = datos.get("pantalla", 1), datos.get("total", 3)
    anos = datos.get("anos") or 0
    hai = f"HAI {anos} {'ANO' if anos == 1 else 'ANOS'}"
    loc, vis = datos.get("local"), datos.get("visitante")
    nl, nv = datos.get("local_nombre") or "Celta", datos.get("visitante_nombre") or ""
    if p == 1:
        img = _fondo_almanaque(datos, 640, (540, 760), 640, 100)
        _cabecera(img, True)
        d = ImageDraw.Draw(img)
        # placa de fecha: día enorme | mes y año
        dia, mes, anio = str(datos.get("dia", "")), datos.get("mes_largo", ""), str(datos.get("anio", ""))
        fd, fm, fa = f_disp(262), f_disp(84), f_disp(156)
        wd = d.textlength(dia, font=fd)
        wm = sum(d.textlength(c, font=fm) for c in mes) + 12 * (len(mes) - 1)
        wa = d.textlength(anio, font=fa)
        wr = max(wm, wa)
        gap = 44
        x0 = (W - (wd + 2 * gap + 4 + wr)) / 2
        y0 = 338
        bb = d.textbbox((0, 0), dia, font=fd)
        d.text((x0 + 3, y0 - bb[1] + 4), dia, font=fd, fill=(2, 8, 22))
        d.text((x0, y0 - bb[1]), dia, font=fd, fill=WHITE)
        alto_dia = bb[3] - bb[1]
        xr = x0 + wd + 2 * gap + 4
        d.rectangle([x0 + wd + gap, y0 + 8, x0 + wd + gap + 3, y0 + alto_dia - 8], fill=CEL)
        ba = d.textbbox((0, 0), anio, font=fa)
        bm = d.textbbox((0, 0), "A", font=fm)
        h_blq = (bm[3] - bm[1]) + 28 + (ba[3] - ba[1])
        yb = y0 + (alto_dia - h_blq) / 2
        _esp(d, xr + wr / 2, yb - bm[1], mes, fm, CEL, 12, sombra=True)
        d.text((xr + (wr - wa) / 2 + 2, yb + (bm[3] - bm[1]) + 28 - ba[1] + 3), anio, font=fa, fill=(2, 8, 22))
        d.text((xr + (wr - wa) / 2, yb + (bm[3] - bm[1]) + 28 - ba[1]), anio, font=fa, fill=WHITE)
        # protagonistas del cartel
        cy = 742
        if vis:
            _escudo_aro(img, 280, cy, loc, siglas(nl), 112)
            _escudo_aro(img, 800, cy, vis, siglas(nv), 112)
            d = ImageDraw.Draw(img)
            fv = f_disp(92)
            d.text((540 - d.textlength("VS", font=fv) / 2 + 2, cy - 58 + 3), "VS", font=fv, fill=(2, 8, 22))
            d.text((540 - d.textlength("VS", font=fv) / 2, cy - 58), "VS", font=fv, fill=CEL)
            for x, n in ((280, nl), (800, nv)):
                fn = fit(d, n.upper(), 30, 330, 18)
                _esp(d, x, cy + 112 + 50, n.upper(), fn, WHITE, 4, sombra=True)
        else:
            _escudo_aro(img, 540, cy - 8, loc or "celta-vigo", "RC", 122)
            d = ImageDraw.Draw(img)
            _esp(d, 540, cy - 8 + 122 + 50, "REAL CLUB CELTA", font_m(30), WHITE, 6, sombra=True)
        # «HAI N ANOS»: sello tipográfico
        _sello_anos(img, 968, anos)
        d = ImageDraw.Draw(img)
        # titular editorial
        d.line([(W // 2 - 70, 1176), (W // 2 + 70, 1176)], fill=CEL, width=3)
        tit, ft, paso = _parrafo(d, datos.get("titular_cartel") or datos["titular"], W - 190, 178, 56, 32, f_serif_b, 1.2)
        y = 1198
        for ln in tit:
            center(d, y, ln, ft, WHITE)
            y += paso
        _invitacion(img, 1388)
    elif p == 2:
        img = _fondo_almanaque(datos, 500, (540, 480), 520, 90)
        _cabecera(img, False)
        d = ImageDraw.Draw(img)
        _esp(d, 540, 178, f"{datos.get('fecha_texto', '')}   ·   {hai}", font_m(28), PLATA, 5)
        if vis and datos.get("goles_local") is not None:
            cy = 495
            _escudo_aro(img, 170, cy, loc, siglas(nl), 100)
            _escudo_aro(img, 910, cy, vis, siglas(nv), 100)
            d = ImageDraw.Draw(img)
            a, b = str(datos["goles_local"]), str(datos["goles_visitante"])
            fs = f_disp(430)
            wa_, wb_ = d.textlength(a, font=fs), d.textlength(b, font=fs)
            barra, hueco = 54, 34
            x0 = W / 2 - (wa_ + wb_ + 2 * hueco + barra) / 2
            bb = d.textbbox((0, 0), "8", font=fs)
            ty = cy - (bb[1] + bb[3]) / 2
            d.text((x0, ty), a, font=fs, fill=WHITE)
            d.rectangle([x0 + wa_ + hueco, cy - 6, x0 + wa_ + hueco + barra, cy + 6], fill=CEL)
            d.text((x0 + wa_ + 2 * hueco + barra, ty), b, font=fs, fill=WHITE)
            for x, n in ((170, nl), (910, nv)):
                fn = fit(d, n.upper(), 26, 250, 16)
                _esp(d, x, cy + 100 + 44, n.upper(), fn, PLATA, 3)
            y_card = 745
        else:
            _escudo_aro(img, 540, 440, loc or "celta-vigo", "RC", 120)
            y_card = 650
        fin = _marco_texto(img, y_card, datos["texto"], 1230 - y_card, 58, 32, f_serif, rotulo="A HISTORIA EN DATOS")
        prot = (datos.get("protagonistas") or "").strip()
        d = ImageDraw.Draw(img)
        if prot:
            y = fin + 48
            _esp(d, 540, y, "PROTAGONISTAS", font_m(24), CEL, 6)
            lineas, f, paso = _parrafo(d, prot, W - 200, 1405 - (y + 42), 36, 24, f_serif_i, 1.3)
            for i, ln in enumerate(lineas):
                center(d, y + 42 + i * paso, ln, f, fill=PLATA)
        _barras(img, 2, total)
    else:
        img = _fondo_almanaque(datos, 520, (540, 430), 520, 90)
        _cabecera(img, False)
        d = ImageDraw.Draw(img)
        fe = f_disp(430)
        bb = d.textbbox((0, 0), "E TI?", font=fe)
        d.text(((W - d.textlength("E TI?", font=fe)) / 2, 200 - bb[1]), "E TI?", font=fe, fill=WHITE)
        yq = 200 + (bb[3] - bb[1]) + 38
        _escudo_aro(img, 540, yq + 100, "celta-vigo", "RC", 92)
        fin = _marco_texto(img, yq + 250, datos["texto"], 1085 - (yq + 250) + 70, 58, 32, f_serif_i)
        preg = (datos.get("pregunta") or "").strip()
        d = ImageDraw.Draw(img)
        if preg:
            y0 = max(fin + 36, 1090)
            lineas, f, paso = _parrafo(d, preg, W - 2 * (116 + 40), 1380 - y0 - 60, 50, 30, f_serif_b, 1.24)
            alto = len(lineas) * paso + 58
            _rgba(img, [110, y0, W - 110, y0 + alto], 4, CEL + (255,), borde=(236, 247, 255, 255), grosor=3)
            d = ImageDraw.Draw(img)
            d.rectangle([98, y0 - 12, W - 98, y0 + alto + 12], outline=(236, 247, 255), width=2)
            for i, ln in enumerate(lineas):
                center(d, y0 + 27 + i * paso, ln, f, fill=OSCURO)
            yc = y0 + alto + 42
            if yc < 1400:
                _esp(d, 540, yc, "CÓNTANOLO POR MENSAXE", font_m(24), CEL, 5)
        _barras(img, 3, total)
    AZUL = (146, 202, 246)
    pie(img, ImageDraw.Draw(img))
    return img


RENDER = {"gol": gol, "tarjeta": gol, "penalti_parado": gol, "historia_portada": historia_portada, "almanaque": almanaque, "pronostico": pronostico, "efemeride": efemeride, "cumpleanos": cumpleanos, "entradas": entradas, "partemedico": partemedico, "previa": previa, "clasificacion": clasificacion, "proximo": proximo, "resultado": resultado, "convocatoria": convocatoria, "alineacion": alineacion}
