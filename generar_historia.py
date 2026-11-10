"""Marexada Celeste · diseño «historia» 1080x1920 (LaLiga y Celta Fortuna).

Tipos: proximo | resultado | convocatoria | alineacion.  Europa League sigue con el diseño de generar.py.
Se usa desde generar.py (generar_historia.RENDER).  Fondo: assets/fondos/historia.jpg (si no existe, el provisional).
"""
import glob
import json
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
_TEMAS = {"copa": {"navy": (86, 8, 28), "acento": (255, 178, 178)}}   # Copa del Rey: fondo teñido de rojo


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
def proximo(datos):
    img = fondo(); d = ImageDraw.Draw(img)
    cabecera(img, d, etiqueta_equipo(datos), "PRÓXIMO PARTIDO", datos.get("logo"), ytitulo=205)
    jornada(d, datos)
    encuentro(img, d, datos, "VS")
    dia, hora = fecha_larga(datos.get("fecha_hora"))
    if dia:
        center(d, 1335, dia, fit(d, dia, 62, W - 100))
    if hora:
        center(d, 1425, f"{hora} h", font(124), fill=AZUL)
    if datos.get("lugar"):
        center(d, 1262, datos["lugar"], fit(d, datos["lugar"], 38, W - 120), fill=(200, 218, 240))
    pie(img, d)
    return img


def resultado(datos):
    img = fondo(); d = ImageDraw.Draw(img)
    cabecera(img, d, etiqueta_equipo(datos), "RESULTADO FINAL", datos.get("logo"))
    jornada(d, datos)
    encuentro(img, d, datos, f"{datos['goles_local']} - {datos['goles_visitante']}")
    dia, _ = fecha_larga(datos.get("fecha_hora"))
    if dia:
        center(d, 1310, dia, fit(d, dia, 50, W - 100), fill=AZUL)
    gl, gv = datos.get("goleadores_local", []), datos.get("goleadores_visitante", [])
    if gl or gv:
        y = 1415
        for lado, lista, x in (("local", gl, 215), ("visitante", gv, 865)):
            for i, g in enumerate(lista[:5]):
                center(d, y + i * 38, g, fit(d, g, 30, 420), fill=(214, 228, 246), x=x)
    pie(img, d)
    return img


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


def convocatoria(datos):
    img = fondo(); d = ImageDraw.Draw(img)
    tag = {"CELTA FORTUNA": "CELTA FORTUNA"}.get(datos.get("tag"), "REAL CLUB CELTA DE VIGO")
    center(d, 150, "CONVOCATORIA", font(96))
    center(d, 270, tag, font(44), fill=AZUL)
    rival = nombre(datos, "visitante" if datos["local"] == "celta-vigo" else "local")
    vs = f"vs {rival}" if datos["local"] == "celta-vigo" else f"en {rival}"
    center(d, 340, vs, fit(d, vs, 62, W - 100))
    dia, hora = fecha_larga(datos.get("fecha_hora"))
    linea = " · ".join(x for x in (dia, hora) if x)
    if linea:
        center(d, 425, linea, fit(d, linea, 44, W - 100), fill=AZUL)
    bajas = datos.get("bajas", [])
    fondo_lista = 1530 - (170 if bajas else 0)
    y = lista_pildoras(img, d, datos["convocados"], 520, fondo_lista - 520)
    if bajas:
        d.text((70, y + 22), "BAIXAS", font=font(30), fill=AZUL)
        f = font(32)
        linea, yy = "", y + 68
        for nom in [b["nombre"] for b in bajas]:
            prueba = (linea + ", " if linea else "") + nom
            if d.textlength(prueba, font=f) > W - 140 and linea:
                d.text((70, yy), linea + ",", font=f, fill=(214, 228, 246))
                linea, yy = nom, yy + 42
            else:
                linea = prueba
        d.text((70, yy), linea, font=f, fill=(214, 228, 246))
    pie(img, d)
    return img


def alineacion(datos):
    img = fondo(); d = ImageDraw.Draw(img)
    center(d, 150, "ALIÑACIÓN", font(96))
    center(d, 270, etiqueta_equipo(datos), font(44), fill=AZUL)
    rival = nombre(datos, "visitante" if datos["local"] == "celta-vigo" else "local")
    center(d, 340, f"vs {rival}", fit(d, f"vs {rival}", 62, W - 100))
    dia, hora = fecha_larga(datos.get("fecha_hora"))
    linea = " · ".join(x for x in (dia, hora) if x)
    if linea:
        center(d, 425, linea, fit(d, linea, 44, W - 100), fill=AZUL)
    once = [j if isinstance(j, dict) else {"nombre": j} for j in datos["once"]]
    y = lista_pildoras(img, d, once, 520, 560)
    sup = [j if isinstance(j, dict) else {"nombre": j} for j in datos.get("suplentes", [])]
    if sup:
        d.text((70, y + 20), "SUPLENTES", font=font(30), fill=AZUL)
        lista_pildoras(img, d, sup, y + 64, 1530 - (y + 64))
    pie(img, d)
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


RENDER = {"previa": previa, "clasificacion": clasificacion, "proximo": proximo, "resultado": resultado, "convocatoria": convocatoria, "alineacion": alineacion}
