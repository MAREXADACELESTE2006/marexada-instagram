"""Lector de noticias de rccelta.es -> datos para generar.py

Entrada: titulo (el H1 de la noticia) y texto (el cuerpo, sin etiquetas HTML).
Salida:  (tipo, datos) o (tipo, None) si no se pudo leer con seguridad.

Uso de prueba:
    python rccelta.py fixtures/cronica_union.txt     (1ª línea = título, resto = texto)
"""
import datetime
import json
import os
import re
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
EQUIPOS = json.load(open(os.path.join(BASE, "assets", "equipos.json"), encoding="utf-8"))

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
         "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
DIAS = {"lunes": "Lun", "martes": "Mar", "miércoles": "Mér", "miercoles": "Mér", "jueves": "Xov",
        "viernes": "Ven", "sábado": "Sáb", "sabado": "Sáb", "domingo": "Dom"}


# ---------------------------------------------------------------- utilidades
def limpiar(t):
    t = t.replace("\u00a0", " ").replace("*", "")
    return re.sub(r"[ \t]+", " ", t).strip()


def norm(t):
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", t)


GENERICAS = {"ud", "cf", "fc", "cd", "rc", "rcd", "sd", "ad", "ce", "uds", "royale", "club", "de", "la", "el", "sk", "sc"}


def slug_equipo(nombre):
    """'Levante UD' -> 'levante-ud'. None si el club no está en los packs de escudos."""
    if not nombre:
        return None
    a = {w for w in norm(nombre).split() if w not in GENERICAS}
    if a == {"celta"}:
        return "celta-vigo"
    mejor, pts = None, 0.0
    for slug, e in EQUIPOS.items():
        b = {w for w in norm(e["nombre"]).split() if w not in GENERICAS}
        if not a or not b or not (a & b):
            continue
        j = len(a & b) / len(a | b)
        if j > pts:
            mejor, pts = slug, j
    return mejor if pts >= 0.5 else None


def top_split(s, sep=","):
    """Divide por sep fuera de paréntesis."""
    partes, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            partes.append(cur)
            cur = ""
        else:
            cur += ch
    partes.append(cur)
    return [p.strip() for p in partes if p.strip()]


def lista_con_y(s):
    """'A, B (x, y) y C' -> ['A', 'B (x, y)', 'C']  (también separa con ' e ' si sigue una mayúscula)"""
    items = top_split(s)
    if items:
        ult, depth, corte = items[-1], 0, None
        for m in re.finditer(r"\(|\)|\s(?:y|e)\s+(?=[A-ZÁÉÍÓÚÑ])", ult):
            if m.group() == "(":
                depth += 1
            elif m.group() == ")":
                depth -= 1
            elif depth == 0:
                corte = m
        if corte is not None:
            items[-1:] = [ult[:corte.start()].strip(), ult[corte.end():].strip()]
    return [i for i in items if i]


# ordinales de jornada ("duodécima" -> 12), de 1 a 42
def _ordinales():
    u = ["", "primera", "segunda", "tercera", "cuarta", "quinta", "sexta", "septima", "octava", "novena"]
    d = {}
    for i in range(1, 10):
        d[u[i]] = i
    d.update({"decima": 10, "undecima": 11, "duodecima": 12})
    for i in range(3, 10):
        d["decimo" + u[i]] = 10 + i
    d["decimoctava"] = 18
    d["vigesima"] = 20
    for i in range(1, 10):
        d["vigesimo" + u[i]] = 20 + i
        d["vigesima" + u[i]] = 20 + i
    d["trigesima"] = 30
    for i in range(1, 10):
        d["trigesima" + u[i]] = 30 + i
    d["cuadragesima"] = 40
    for i in (1, 2):
        d["cuadragesima" + u[i]] = 40 + i
    return d


ORDINALES = _ordinales()


def num_jornada(texto):
    """'jornada número 12', 'duodécima jornada' o 'Jornada 12' -> 12 (o None)."""
    m = re.search(r"jornada\s+(?:n[uú]mero\s+)?(\d+)", texto, re.I)
    if m:
        return int(m.group(1))
    for m in re.finditer(r"((?:[a-záéíóú]+\s+)?[a-záéíóú]+)\s+jornada\b", texto, re.I):
        k = norm(m.group(1)).replace(" ", "")
        for cand in (k, norm(m.group(1)).split()[-1]):
            if cand in ORDINALES:
                return ORDINALES[cand]
    return None


def limpiar_lugar(lugar):
    """'Abanca Balaídos' -> 'Balaídos'; 'el Estadio El Plantío' -> 'El Plantío'."""
    if not lugar:
        return None
    lugar = re.sub(r"^(?:el\s+|la\s+)?Abanca\s+", "", lugar.strip())
    lugar = re.sub(r"^(?:el\s+)?Estadio\s+(?=[A-ZÁÉÍÓÚÑ])", "", lugar)
    lugar = re.sub(r"^(?:el\s+|la\s+)", "", lugar)
    return lugar.strip() or None


def sufijo_filial(rival):
    """'Real Sociedad B' -> 'REAL SOCIEDAD B' (el escudo es el del primer equipo, el nombre no)."""
    if rival and re.search(r"\s(B|C|Atl[eè]tic|Castilla|Promesas)$", rival.strip()):
        return rival.strip().upper()
    return None


def detectar_equipo(titulo):
    if re.search(r"Celta Fortuna", titulo, re.I):
        return "fortuna"
    if re.search(r"As Celtas", titulo, re.I):
        return "as-celtas"
    return "primero"


def fecha_hora(texto):
    m = re.search(r"(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo),?\s*(\d{1,2}) de (\w+).{0,25}?(\d{1,2})[:.](\d{2})", texto, re.I | re.S)
    if m:
        mes = MESES.get(m.group(3).lower())
        if mes:
            return f"{DIAS[m.group(1).lower()]} {int(m.group(2)):02d}/{mes:02d} · {int(m.group(4)):02d}:{m.group(5)}"
    # "esta tarde a las 18:30 horas": el día es el de publicación ("RC Celta 31-octubre-2026")
    mp = re.search(r"RC Celta\s+(\d{1,2})-(\w+)-(\d{4})", texto)
    mh = re.search(r"(\d{1,2})[:.](\d{2})\s*horas", texto)
    if mp and mh and re.search(r"\b(hoy|esta (?:tarde|noche|mañana))\b", texto, re.I):
        mes = MESES.get(mp.group(2).lower())
        if mes:
            f = datetime.date(int(mp.group(3)), mes, int(mp.group(1)))
            dia = ["Lun", "Mar", "Mér", "Xov", "Ven", "Sáb", "Dom"][f.weekday()]
            return f"{dia} {f.day:02d}/{f.month:02d} · {int(mh.group(1)):02d}:{mh.group(2)}"
    return None


def fecha_publicacion(texto):
    mp = re.search(r"RC Celta\s+(\d{1,2})-(\w+)-(\d{4})", texto)
    if not mp or not MESES.get(mp.group(2).lower()):
        return None
    f = datetime.date(int(mp.group(3)), MESES[mp.group(2).lower()], int(mp.group(1)))
    return f"{['Lun', 'Mar', 'Mér', 'Xov', 'Ven', 'Sáb', 'Dom'][f.weekday()]} {f.day:02d}/{f.month:02d}"


def competicion(texto):
    """-> (competicion, tag)"""
    if re.search(r"Europa League|\bUEL\b", texto):
        return "europa", None
    if re.search(r"Copa del Rey", texto):
        return "liga", "COPA DEL REY"
    return "liga", None


def logo_competicion(texto):
    if re.search(r"Hypermotion", texto, re.I):
        return "hypermotion"
    if re.search(r"Copa del Rey", texto):
        return "copa"
    if re.search(r"Europa League|\bUEL\b", texto):
        return "europa"
    return "laliga"


# ---------------------------------------------------------------- convocatoria
def _jugadores(cadena, motivo=None):
    """'Nombre (7), Otro (20) y Tercero (3)' -> lista de dicts; el dorsal es opcional."""
    out = []
    for it in lista_con_y(cadena):
        mm = re.match(r"^(.+?)\s*\((\d+)\)$", it)
        j = {"nombre": (mm.group(1) if mm else it).strip()}
        if mm:
            j["dorsal"] = int(mm.group(2))
        if motivo:
            j["motivo"] = motivo
        out.append(j)
    return out


def parse_convocatoria(titulo, texto):
    titulo, texto = limpiar(titulo), limpiar(texto)
    titulo = re.sub(r"\s*\|\s*Celta\s*$", "", titulo)
    equipo = detectar_equipo(titulo)
    m = re.search(r"formar[aá]n\s+(.+?)\.(?:\s|$)", texto, re.S)
    if not m:
        return None
    convocados = _jugadores(m.group(1))
    if len(convocados) < 11:
        return None

    bajas = []
    for mb in re.finditer(r"Ser[aá]n?\s+baja[s]?(?:\s+por\s+(lesi[oó]n|sanci[oó]n))?\s+(.+?\))\s*\.(?:\s|$)", texto, re.S):
        motivo = "lesion" if (mb.group(1) or "").lower().startswith("lesi") else "sancion"
        bajas += _jugadores(mb.group(2), motivo)
    # "Pablo Meixús (6) se perderá el encuentro por sanción" / "X (6) y Y (20) se perderán el encuentro por ..."
    for ms in re.finditer(r"([^.]*?\))\s+se perder[aá]n?\s+el encuentro", texto):
        cad = re.sub(r"^\s*(?:Mientras,|Además,)\s*", "", ms.group(1))
        bajas += _jugadores(cad, "sancion")
    # (quien sigue con su selección no es baja: no se lista)

    rival = None
    for pat in (r"(?:recibir|visitar)\s+(?:al|a la|a los|a las|a|el|la)\s+(.+)$", r"\bante\s+(?:el|la|los|las)\s+(.+)$", r"\bante\s+(.+)$"):
        mr = re.search(pat, titulo)
        if mr:
            rival = mr.group(1).strip()
            break
    if not rival:  # "Convocatoria ... para su visita al estadio «El Molinón»": el rival va en el cuerpo
        mr = re.search(r"horas,?\s*(?:al|a la|a los|a las|a)\s+(.+?)\.\s", texto)
        if mr:
            rival = mr.group(1).strip()
    if not rival:
        return None

    cabeza = texto[:450]
    if re.search(r"\bvisitar[aá]\b", cabeza):
        celta_local = False
    elif re.search(r"\brecibir[aá]\b", cabeza):
        celta_local = True
    elif re.search(r"\bvisitar\b", titulo):
        celta_local = False
    elif re.search(r"\brecibir\b", titulo):
        celta_local = True
    else:
        celta_local = "Balaídos" in texto

    comp, tag = competicion(titulo + " " + texto)
    mj = num_jornada(texto)
    rival_slug = slug_equipo(rival)
    ml = re.search(r"disputar[aá]\s+en\s+(.+?)(?:,|\.\s)", texto)
    lugar = limpiar_lugar(ml.group(1)) if ml else ("Balaídos" if celta_local and "Balaídos" in texto else None)
    hyper = "Hypermotion" in texto
    jornada = (f"{'Hypermotion · ' if hyper else ''}Xornada {mj}") if mj else ("Hypermotion" if hyper else None)
    datos = {
        "tipo": "convocatoria", "competicion": comp,
        "local": "celta-vigo" if celta_local else (rival_slug or rival),
        "visitante": (rival_slug or rival) if celta_local else "celta-vigo",
        "jornada": jornada, "lugar": lugar, "fecha_hora": fecha_hora(texto),
        "convocados": convocados, "bajas": bajas, "_rival_texto": rival,
        "logo": logo_competicion(titulo + " " + texto),
    }
    _nombres(datos, equipo, celta_local, rival)
    if tag:
        datos["tag"] = tag
    return {k: v for k, v in datos.items() if v is not None}


def _nombres(datos, equipo, celta_local, rival):
    """Etiquetas de equipo: Fortuna / filiales (el escudo es el del club grande, el nombre no)."""
    celta_nombre = {"fortuna": "CELTA FORTUNA", "as-celtas": "AS CELTAS"}.get(equipo)
    if celta_nombre:
        datos["tag"] = celta_nombre
        datos["local_nombre" if celta_local else "visitante_nombre"] = celta_nombre
    fil = sufijo_filial(rival)
    if fil:
        datos["visitante_nombre" if celta_local else "local_nombre"] = fil


# ---------------------------------------------------------------- resultado (crónica)
def goles_de(texto, g1, g2):
    """Línea 'Goles: 1-0, min. 11: Nombre; 1-1, min. 35: Otro' (o separada por '. ') -> (locales, visitantes)."""
    gl, gv = [], []
    mg = re.search(r"Goles:\s*(.+?)(?:\n|$)", texto)
    if mg:
        prev_l = 0
        patron = r"(\d+)\s*-\s*(\d+),\s*min\.\s*([\d+]+):\s*(.+?)(?=\s*[;.]\s*\d+\s*-\s*\d+,\s*min\.|\s*\.?\s*$)"
        for ms in re.finditer(patron, mg.group(1)):
            a = int(ms.group(1))
            etiqueta = f"{ms.group(4).strip()} {ms.group(3)}'"
            (gl if a > prev_l else gv).append(etiqueta)
            prev_l = a
    if (g1 + g2) > 0 and (len(gl) != g1 or len(gv) != g2):
        gl = gl if len(gl) == g1 else []
        gv = gv if len(gv) == g2 else []
    return gl, gv


def parse_resultado(titulo, texto):
    titulo, texto = limpiar(titulo), limpiar(texto)
    titulo = re.sub(r"\s*\|\s*Celta\s*$", "", titulo)
    m = re.search(r"\|\s*(.+?)\s+(\d+)\s*[-–]\s*(\d+)\s+(.+?)\s*$", titulo)
    if not m:
        return None
    n1, g1, g2, n2 = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
    celta_local = norm(n1).split()[-1] == "celta" and slug_equipo(n1) == "celta-vigo"
    if not celta_local and slug_equipo(n2) != "celta-vigo":
        return None
    rival = n2 if celta_local else n1
    rival_slug = slug_equipo(rival)
    local_s = "celta-vigo" if celta_local else (rival_slug or rival)
    visit_s = (rival_slug or rival) if celta_local else "celta-vigo"

    gl, gv = goles_de(texto, g1, g2)

    inc = re.search(r"Incidencias:\s*(.+)", texto)
    inc = inc.group(1) if inc else ""
    mj = num_jornada(inc)
    ml = re.search(r"disputado en\s+(.+?)(?:\s+ante\b|\.|,|$)", inc)
    lugar = limpiar_lugar(ml.group(1)) if ml else None
    comp, tag = competicion(inc or titulo)

    datos = {
        "tipo": "resultado", "competicion": comp, "local": local_s, "visitante": visit_s,
        "jornada": f"Xornada {mj}" if mj else None, "lugar": lugar,
        "goles_local": g1, "goles_visitante": g2,
        "goleadores_local": gl, "goleadores_visitante": gv,
        "logo": logo_competicion(inc or titulo), "fecha_hora": fecha_publicacion(texto),
    }
    if tag:
        datos["tag"] = tag
    return {k: v for k, v in datos.items() if v is not None}


# ---------------------------------------------------------------- ficha técnica (por si se quiere la alineación tras el partido)
def parse_ficha(texto):
    """-> {'celta': {'once': [...], 'cambios': [(entra, minuto)]}, 'rival': ...}"""
    texto = limpiar(texto)
    out = []
    for m in re.finditer(r"^(\d+)\s*[–-]\s*([^:\n]+):\s*(.+?)\.?\s*$", texto, re.M):
        once, cambios = [], []
        for it in lista_con_y(m.group(3).replace(";", ",")):
            mm = re.match(r"^(.+?)\s*\((.+?),\s*min\.\s*([\d+]+)\)$", it)
            if mm:
                once.append(mm.group(1).strip())
                cambios.append({"nombre": mm.group(2).strip(), "min": mm.group(3), "por": mm.group(1).strip()})
            else:
                once.append(it)
        out.append({"equipo": m.group(2).strip(), "goles": int(m.group(1)), "once": once, "cambios": cambios})
    return out


def parse_resultado_ficha(titulo, texto):
    """Crónicas cuyo título no lleva 'Celta 1-0 Rival' (p. ej. 'Un empate con sabor a poco ... (2-2)'):
    el marcador y los dos equipos se leen de la FICHA TÉCNICA (el primero que aparece es el local)."""
    titulo, texto = limpiar(titulo), limpiar(texto)
    fichas = parse_ficha(texto)
    if len(fichas) < 2:
        return None
    f1, f2 = fichas[0], fichas[1]
    c1 = "celta" in norm(f1["equipo"]).split()
    c2 = "celta" in norm(f2["equipo"]).split()
    if c1 == c2:
        return None
    celta_local = c1
    fc, fr = (f1, f2) if celta_local else (f2, f1)
    equipo = "fortuna" if "fortuna" in norm(fc["equipo"]).split() else ("as-celtas" if "celtas" in norm(fc["equipo"]).split() else "primero")
    rival_slug = slug_equipo(fr["equipo"])
    g1, g2 = f1["goles"], f2["goles"]
    gl, gv = goles_de(texto, g1, g2)
    inc = re.search(r"Incidencias:\s*(.+)", texto)
    inc = inc.group(1) if inc else ""
    mj = num_jornada(inc)
    ml = re.search(r"disputado en\s+(.+?)(?:\s+ante\b|\.|,|$)", inc)
    comp, tag = competicion(inc or titulo)
    hyper = "Hypermotion" in inc
    amistoso = bool(re.search(r"amistoso", inc, re.I)) and not mj
    jornada = (f"{'Hypermotion · ' if hyper else ''}Xornada {mj}") if mj else ("Amigable" if amistoso else None)
    local_s = "celta-vigo" if celta_local else (rival_slug or fr["equipo"])
    visit_s = (rival_slug or fr["equipo"]) if celta_local else "celta-vigo"
    datos = {
        "tipo": "resultado", "competicion": comp, "local": local_s, "visitante": visit_s,
        "jornada": jornada, "lugar": limpiar_lugar(ml.group(1)) if ml else None,
        "goles_local": g1, "goles_visitante": g2, "goleadores_local": gl, "goleadores_visitante": gv,
        "logo": logo_competicion(inc or titulo), "fecha_hora": fecha_publicacion(texto),
    }
    _nombres(datos, equipo, celta_local, fr["equipo"])
    if tag:
        datos["tag"] = tag
    return {k: v for k, v in datos.items() if v is not None}


# ---------------------------------------------------------------- clasificación
def clasificar(titulo, texto=""):
    t = limpiar(titulo)
    if re.match(r"Convocatoria del Celta", t, re.I):
        return "convocatoria"
    if re.search(r"\|\s*.+?\s+\d+\s*[-–]\s*\d+\s+.+$", t):
        return "resultado"
    if texto and re.search(r"FICHA T[ÉE]CNICA", texto, re.I) and re.search(r"Incidencias", texto):
        return "resultado"  # crónica con título libre
    return "otra"


def articulo_a_datos(titulo, texto):
    tipo = clasificar(titulo, texto)
    if tipo == "convocatoria":
        return tipo, parse_convocatoria(titulo, texto)
    if tipo == "resultado":
        return tipo, parse_resultado(titulo, texto) or parse_resultado_ficha(titulo, texto)
    return tipo, None


if __name__ == "__main__":
    ruta = sys.argv[1]
    lineas = open(ruta, encoding="utf-8").read().split("\n")
    tipo, datos = articulo_a_datos(lineas[0], "\n".join(lineas[1:]))
    print(tipo)
    print(json.dumps(datos, ensure_ascii=False, indent=1))
