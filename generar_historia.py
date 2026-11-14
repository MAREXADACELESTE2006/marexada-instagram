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

from PIL import Image, ImageDraw, ImageFilter, ImageFont

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


def center(d, y, text, f, fill=WHITE, x=W // 2):
    d.text((x - d.textlength(text, font=f) / 2, y), text, font=f, fill=fill)


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
          "europa": {"navy": (34, 16, 6), "acento": (255, 150, 48)}}          # Europa League: fondo oscuro cálido y acento naranja


def usar_tema(logo=None):
    """Cambia los colores de las historias según la competición (Copa del Rey = rojo). Llamar antes de dibujar."""
    global NAVY, AZUL
    t = _TEMAS.get(logo, _TEMA_BASE)
    NAVY, AZUL = t["navy"], t["acento"]


def fondo():
    ruta = os.path.join(ASSETS, "fondos", "historia.jpg")
    if not os.path.exists(ruta):
        ruta = os.path.join(ASSETS, "fondos", "historia_provisional.jpg")
    img = Image.open(ruta).convert("RGB").resize((W, H), Image.LANCZOS)
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
    pegar(img, os.path.join(ASSETS, "marca", "escudo_marexada.png"), 458, 1584, (164, 164))
    center(d, 1762, "MAREXADA CELESTE", font(48))
    center(d, 1826, "marexadaceleste.com", font(34), fill=AZUL)


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


def _bloque_partido(img, d, datos, cy, r=98, centro="VS", cx=(270, 810), tam=36):
    """Los dos escudos con su nombre debajo y el centro (VS o marcador). Devuelve la y donde acaban los nombres."""
    fin = cy
    for lado, x in (("local", cx[0]), ("visitante", cx[1])):
        _escudo_redondo(img, x, cy, datos[lado], siglas(nombre(datos, lado)), r=r)
        lineas = _nombre_lineas(d, nombre(datos, lado), tam, 420)
        for i, l in enumerate(lineas):
            center(d, cy + r + 20 + i * (tam + 8), l, fit(d, l, tam, 420), x=x)
        fin = max(fin, cy + r + 20 + len(lineas) * (tam + 8))
    if centro:
        center(d, cy - 38, centro, font(64), fill=AZUL)
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



FIN_CONTENIDO = 1466        # el pie (escudo de la peña + web) ocupa de 1484 a 1690, dentro de la zona segura


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


def _pie_v39(img, d):
    """Escudo de la peña grande con la web debajo, abajo del todo pero dentro de la zona segura."""
    lado, y = 150, 1484
    _escudo_pena(img, W // 2, y, lado)
    center(d, y + lado + 4, "marexadaceleste.com", font(34), fill=AZUL)


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


def _proximo(datos, s, hg=0):
    img = fondo(); d = ImageDraw.Draw(img)
    yl = _cab_logo(img, d, "PRÓXIMO PARTIDO", _tag_v33(datos), datos.get("logo"), s)
    r = int(112 * s)
    cy = yl + r + 30
    fin = _bloque_partido(img, d, datos, cy, r=r, tam=int(38 * s))
    dia, hora = fecha_larga(datos.get("fecha_hora"))
    j = (datos.get("jornada") or "").strip()
    j = "" if re.search(r"\bX$", j) else j
    lugar = datos.get("lugar")
    ta, th = int(58 * s), int(190 * s)
    alto = 30 + (ta + 26 if dia else 0) + (th + 22 if hora else 0) + (58 if lugar else 0) + (66 if j else 0) + 24
    y0 = fin + 44 + hg
    _rgba(img, [60, y0, W - 60, y0 + alto], 36, (4, 12, 30, 105), borde=(255, 255, 255, 40), grosor=2)
    y = y0 + 30
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


def _resultado(datos, s, hg=0):
    img = fondo(); d = ImageDraw.Draw(img)
    yl = _cab_logo(img, d, "RESULTADO FINAL", _tag_v33(datos), datos.get("logo"), s)
    gl = _agrupar_goles(datos.get("goleadores_local", []))
    gv = _agrupar_goles(datos.get("goleadores_visitante", []))
    hay = bool(gl or gv)
    r = int((96 if hay else 118) * s)
    cy = yl + r + 28
    fin = _bloque_partido(img, d, datos, cy, r=r, centro=None, cx=(270, 810), tam=int(36 * s))
    a, b = str(datos["goles_local"]), str(datos["goles_visitante"])
    tam = int((290 if hay else 380) * s)
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
    d.text((x0, ytxt), a, font=f, fill=WHITE)
    d.rounded_rectangle([x0 + wa + hueco, cs - 9, x0 + wa + hueco + 70, cs + 9], 9, fill=AZUL)
    d.text((x0 + wa + 2 * hueco + 70, ytxt), b, font=f, fill=WHITE)
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
        rh = max(40, min(66, (FIN_CONTENIDO - y0 - 100) // max(filas, 1)))
        alto = 78 + filas * rh + 16
        _rgba(img, [40, y0, W - 40, y0 + alto], 30, (4, 12, 30, 115))
        center(d, y0 + 16, "GOLEADORES", font(28), fill=AZUL)
        d.line([(W // 2, y0 + 70), (W // 2, y0 + alto - 20)], fill=(255, 255, 255, 60), width=2)
        for lista, x in ((gl, 70), (gv, 570)):   # columnas de 440 px
            for i, (nom, mins) in enumerate(lista[:7]):
                yy = y0 + 78 + i * rh + rh // 2
                _balon(d, x + 18, yy, 16)
                txt_m = " · ".join(mins)
                fm = font(30)
                wm = d.textlength(txt_m, font=fm)
                d.text((x + 440 - wm, yy - fm.size * 0.70), txt_m, font=fm, fill=AZUL)
                fn = fit(d, nom, 34, 440 - 48 - wm - 24, 20)
                d.text((x + 48, yy - fn.size * 0.70), nom, font=fn, fill=WHITE)
        yp = y0 + alto
    return img, yp


def resultado(datos):
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
        ImageDraw.Draw(cap).rounded_rectangle([40, y, W - 40, y + ph - 6], 12, fill=(146, 202, 246, 110) if destacado else (255, 255, 255, 30))
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
    serie = datos.get("serie", "TAL SEMANA COMA ESTA")
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
def cumpleanos(datos):
    img = fondo(); d = ImageDraw.Draw(img)
    cabecera(img, d, datos.get("tag", ""), "FELIZ ANIVERSARIO", None, ytitulo=205)
    cx, cy, r = W // 2, 640, 230
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).ellipse([cx - r + 6, cy - r + 16, cx + r + 6, cy + r + 16], fill=(0, 0, 0, 90))
    sombra = sombra.filter(ImageFilter.GaussianBlur(12))
    img.paste(sombra, (0, 0), sombra)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AZUL)
    d.ellipse([cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14], outline=WHITE, width=6)
    edad = str(datos.get("edad", ""))
    fe = font(250 if len(edad) < 3 else 190)
    bb = d.textbbox((0, 0), edad, font=fe)
    d.text((cx - (bb[0] + bb[2]) / 2, cy - 45 - (bb[1] + bb[3]) / 2), edad, font=fe, fill=(10, 35, 57))
    center(d, cy + 105, "ANOS", font(62), fill=(10, 35, 57), x=cx)
    y = 960
    for l in _lineas(d, datos.get("nombre", ""), font(96), W - 100, 2):
        center(d, y, l, fit(d, l, 96, W - 100, 50)); y += 112
    if datos.get("posicion"):
        center(d, y + 10, datos["posicion"], fit(d, datos["posicion"], 46, W - 120, 28), fill=AZUL); y += 80
    if datos.get("fecha"):
        center(d, y + 30, f"{datos['fecha']}", font(50), fill=(200, 218, 240)); y += 90
    center(d, max(y + 60, 1380), "Parabéns da Marexada Celeste!", fit(d, "Parabéns da Marexada Celeste!", 52, W - 100, 30))
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


RENDER = {"historia_portada": historia_portada, "pronostico": pronostico, "efemeride": efemeride, "cumpleanos": cumpleanos, "entradas": entradas, "partemedico": partemedico, "previa": previa, "clasificacion": clasificacion, "proximo": proximo, "resultado": resultado, "convocatoria": convocatoria, "alineacion": alineacion}
