"""Marexada Celeste · Celta Femxa Zorka (baloncesto femenino, Liga Femenina Endesa) desde la web de la Federación y BetExplorer (v87).

Como con el AS Celtas Fem, solo se publican DOS cosas: el próximo partido y el resultado (nada de directo, alineación ni convocatoria).
Lee la página oficial de resultados de la FEB (feb.es/lfendesa/resultados.aspx: marcador, día y hora de la jornada), el calendario oficial de la FEB
(feb.es/competiciones/calendario.aspx: todas las jornadas con día y hora, v89) y, de reserva, dos páginas públicas de betexplorer.com del equipo. Escribe en datos_reales/ (o en --salida):
    proximo_baloncesto_fem.json      (próximo partido)
    resultado_baloncesto_fem.json    (último partido jugado)

Uso:
    python baloncesto.py                                                  (lee internet)
    python baloncesto.py --calendario a.html --resultados b.html --feb c.html --calendario-feb d.html --hoy 2026-11-23 --salida carpeta     (prueba sin internet)
Si la página cambia y no se entiende, guarda lo recibido en baloncesto_*_DEBUG.html para poder ajustarlo.
HORAS: BetExplorer las da en hora de Madrid (a comprobar con el primer partido). Si salieran desplazadas, se corrige sin tocar código
poniendo la variable BALONCESTO_DESFASE_MIN (minutos, p. ej. 60 o -60) en GitHub → Settings → Variables → Actions.
"""
import argparse
import datetime
import html as _html
import json
import os
import re
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
URL_CALENDARIO = "https://www.betexplorer.com/basketball/team/celta/pMyy6Tm6/fixtures/"
URL_RESULTADOS = "https://www.betexplorer.com/basketball/team/celta/pMyy6Tm6/results/"
URL_FEB = "https://www.feb.es/lfendesa/resultados.aspx"
URL_FEB_CALENDARIO = "https://www.feb.es/competiciones/calendario.aspx?g=4&t={temporada}&nm=lfendesa"      # v89: calendario oficial de toda la liga (t = año en que empieza la temporada)
TAG = "CELTA FEMXA ZORKA"
DIA = ["Lun", "Mar", "Mér", "Xov", "Ven", "Sáb", "Dom"]

# nombre en BetExplorer (sin « W») -> (escudo, nombre que se ve). Los escudos están en assets/escudos/<escudo>-logo-footylogos.png
EQUIPOS = {
    "celta": ("celta-femxa-zorka", "Celta Femxa Zorka"),
    "leganes": ("innova-tsn-leganes", "Innova-TSN Leganés"),
    "mallorca palma": ("azulmarino-mallorca-palma", "Azulmarino Mallorca Palma"),
    "estudiantes": ("movistar-estudiantes", "Movistar Estudiantes"),
    "uni girona": ("spar-girona", "Spar Girona"),
    "girona": ("spar-girona", "Spar Girona"),
    "perfumerias avenida": ("meins-avenida", "Meins Avenida"),
    "ferrol": ("baxi-ferrol", "BAXI Ferrol"),
    "ensino": ("duran-maquinaria-ensino", "Durán Maquinaria Ensino"),
    "araski": ("kutxabank-araski", "Kutxabank Araski"),
    "zaragoza": ("casademont-zaragoza", "Casademont Zaragoza"),
    "estepona": ("impulso-360-estepona", "Impulso 360 Estepona"),
    "cadi la seu": ("cadi-la-seu", "Cadí La Seu"),
    "valencia": ("valencia-basket", "Valencia Basket"),
    "jairis": ("hozono-global-jairis", "Hozono Global Jairis"),
    "idk gipuzkoa": ("mirai-euskotren", "Mirai Euskotren"),
    "gernika bizkaia": ("inversus-gernika-bizkaia", "Inversus Gernika Bizkaia"),
}
# v87: los nombres que usa la web de la Federación (feb.es) para la clasificación
for _n, _e in {"celta femxa zorka": "celta", "innova tsn leganes": "leganes", "azulmarino mallorca palma": "mallorca palma", "movistar estudiantes": "estudiantes",
               "spar girona": "girona", "meins avenida": "perfumerias avenida", "baxi ferrol": "ferrol", "duran maquinaria ensino": "ensino", "kutxabank araski": "araski",
               "casademont zaragoza": "zaragoza", "impulso 360 estepona": "estepona", "valencia b c": "valencia", "valencia basket": "valencia", "hozono global jairis": "jairis",
               "mirai euskotren": "idk gipuzkoa", "inversus gernika bizkaia": "gernika bizkaia"}.items():
    EQUIPOS[_n] = EQUIPOS[_e]


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
    t = re.sub(r"(?s)<[^>]+>", " ", t or "")
    return re.sub(r"\s+", " ", _html.unescape(t)).strip()


def norm(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", t)).strip()


def equipo(txt):
    """«Leganes W» -> (escudo, nombre). Los clubes que no conocemos salen con su nombre y las siglas (sin escudo)."""
    n = norm(re.sub(r"\s+W$", "", txt.strip()))
    if n in EQUIPOS:
        return EQUIPOS[n]
    return None, re.sub(r"\s+W$", "", txt.strip())


RONDA = re.compile(r"^(\d+)\s*\.\s*(Round|Rodada|Turno|Ronda|Jornada|Tour)\b", re.I)
FECHA = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})(?:\s+(\d{1,2}):(\d{2}))?")
MARCADOR = re.compile(r"^(\d{1,3})\s*[:\-]\s*(\d{1,3})\b")


def leer_partidos(html):
    """Todas las filas con jornada de la tabla: [{jornada, local, visitante, fecha, hora, puntos}]. puntos=None si no se ha jugado."""
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    out = []
    for tr in re.findall(r"(?is)<tr\b.*?</tr>", html):
        celdas = [limpio(c) for c in re.findall(r"(?is)<t[dh]\b[^>]*>(.*?)</t[dh]>", tr)]
        i = next((k for k, c in enumerate(celdas) if RONDA.match(c)), None)
        if i is None:
            continue
        resto = [c for c in celdas[i + 1:] if c]
        if len(resto) < 2:
            continue
        local, visitante = resto[0], resto[1]
        puntos, fecha, hora = None, None, None
        for c in resto[2:]:
            m = MARCADOR.match(c)
            if m and puntos is None:
                puntos = (int(m.group(1)), int(m.group(2)))
                continue
            m = FECHA.search(c)
            if m and fecha is None:
                fecha = datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                hora = f"{int(m.group(4)):02d}:{m.group(5)}" if m.group(4) else None
        if fecha is None:
            continue
        out.append({"jornada": int(RONDA.match(celdas[i]).group(1)), "local": local, "visitante": visitante, "fecha": fecha, "hora": hora, "puntos": puntos})
    return out


def leer_feb(html):
    """Página de resultados de la FEB -> partidos de la jornada que enseña: [{jornada, local, visitante, fecha, hora, puntos, origen}].
    Cada partido empieza con «Día: dd/mm/aaaa / Hora: hh:mm», sigue con los dos equipos y el marcador («79 - 74») y termina en «Parciales»."""
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    t = limpio(html)
    rondas = [(datetime.date(int(m.group(4)), int(m.group(3)), int(m.group(2))), int(m.group(1)))
              for m in re.finditer(r"Jornada\s+(\d+)\s*\((\d{2})/(\d{2})/(\d{4})\)", t)]
    out = []
    for m in re.finditer(r"D[ií]a:\s*(\d{2})/(\d{2})/(\d{4})\s*/\s*Hora:\s*(\d{1,2}):(\d{2})\s*(.*?)(?=D[ií]a:\s*\d{2}/|Parciales|$)", t, re.S):
        fecha = datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        cuerpo = m.group(6).strip()
        puntos = None
        ms = re.search(r"(\d{1,3})\s*-\s*(\d{1,3})\s*$", cuerpo)
        if ms:
            puntos = (int(ms.group(1)), int(ms.group(2)))
            cuerpo = cuerpo[:ms.start()].strip()
        palabras = cuerpo.split()
        for k in range(1, len(palabras)):                      # los dos nombres van seguidos: se parte donde ambos son equipos conocidos
            local, visitante = " ".join(palabras[:k]), " ".join(palabras[k:])
            if norm(local) in EQUIPOS and norm(visitante) in EQUIPOS:
                prev = [n for d, n in rondas if d <= fecha]
                out.append({"jornada": max(prev) if prev else 0, "local": local, "visitante": visitante, "fecha": fecha,
                            "hora": f"{int(m.group(4)):02d}:{m.group(5)}", "puntos": puntos, "origen": "feb"})
                break
    return out


CABECERA_FEB = re.compile(r"Jornada\s*(\d+)\s*(?:<[^>]*>\s*)*(\d{2})/(\d{2})/(\d{4})", re.I)       # «Jornada 9 28/11/2026» (el desplegable lleva «Jornada 9(28/11/2026)» y no vale)
DIA_FEB = r"(?:LUNES|MARTES|MI[ÉE]RCOLES|JUEVES|VIERNES|S[ÁA]BADO|DOMINGO)"
FECHA_FEB = re.compile(rf"(?:{DIA_FEB}\s+)?(\d{{1,2}})/(\d{{1,2}})/(\d{{4}})(?:\s+(\d{{1,2}}):(\d{{2}}))?", re.I)


def leer_calendario_feb(html):
    """v89: calendario oficial de la FEB (feb.es/competiciones/calendario.aspx?g=4&t=AAAA&nm=lfendesa) -> partidos POR JUGAR: [{jornada, local, visitante, fecha, hora, puntos=None, origen}].
    La página tiene una tabla por jornada («Jornada 9 28/11/2026») con tres columnas: Local | Resultado | Visitante. En los partidos por jugar la columna del medio
    trae el día y la hora («SÁBADO 28/11/2026 16:45»); en los jugados, el marcador («80-84»), que aquí se ignora porque no lleva fecha exacta
    (los marcadores salen de la página de resultados). Una hora «0:00» significa «sin hora todavía» y se deja sin hora."""
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    eventos = sorted([(m.start(), "j", m) for m in CABECERA_FEB.finditer(html)] + [(m.start(), "r", m) for m in re.finditer(r"(?is)<tr\b.*?</tr>", html)], key=lambda e: e[0])
    out, jornada = [], None
    for _, tipo, m in eventos:
        if tipo == "j":
            jornada = int(m.group(1))
            continue
        celdas = [limpio(c) for c in re.findall(r"(?is)<t[dh]\b[^>]*>(.*?)</t[dh]>", m.group(0))]
        if jornada is None or len(celdas) < 3 or norm(celdas[0]) == "local" or not celdas[0] or not celdas[2]:
            continue
        mf = FECHA_FEB.search(celdas[1])
        if not mf or MARCADOR.match(celdas[1]):
            continue
        hora = None
        if mf.group(4) and (int(mf.group(4)), int(mf.group(5))) != (0, 0):
            hora = f"{int(mf.group(4)):02d}:{mf.group(5)}"
        try:
            fecha = datetime.date(int(mf.group(3)), int(mf.group(2)), int(mf.group(1)))
        except ValueError:
            continue
        out.append({"jornada": jornada, "local": celdas[0], "visitante": celdas[2], "fecha": fecha, "hora": hora, "puntos": None, "origen": "feb"})
    return out


def con_desfase(p):
    """Aplica BALONCESTO_DESFASE_MIN (si lo hay) a la hora, por si BetExplorer la diera en otra zona."""
    try:
        d = int(os.environ.get("BALONCESTO_DESFASE_MIN", "0") or 0)
    except ValueError:
        d = 0
    if not d or not p["hora"]:
        return p
    t = datetime.datetime.combine(p["fecha"], datetime.time(*map(int, p["hora"].split(":")))) + datetime.timedelta(minutes=d)
    return dict(p, fecha=t.date(), hora=f"{t.hour:02d}:{t.minute:02d}")


def es_del_celta(p):
    return any(norm(re.sub(r"\s+W$", "", n)).startswith("celta") for n in (p["local"], p["visitante"]))


def datos_partido(p, tipo):
    ls, ln = equipo(p["local"])
    vs, vn = equipo(p["visitante"])
    f = p["fecha"]
    d = {"tipo": tipo, "competicion": "liga", "tag": TAG, "deporte": "baloncesto", "local": ls, "visitante": vs,
         "local_nombre": ln, "visitante_nombre": vn, "jornada": f"LF Endesa · Xornada {p['jornada']}" if p["jornada"] else "LF Endesa",
         "_fecha": f.isoformat(),
         "fecha_hora": f"{DIA[f.weekday()]} {f.day:02d}/{f.month:02d}" + (f" · {p['hora']}" if tipo == "proximo" and p["hora"] else "")}
    if tipo == "resultado":
        d.update(goles_local=p["puntos"][0], goles_visitante=p["puntos"][1], goleadores_local=[], goleadores_visitante=[])
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--calendario", default=URL_CALENDARIO)
    ap.add_argument("--resultados", default=URL_RESULTADOS)
    ap.add_argument("--feb", default=URL_FEB)
    ap.add_argument("--calendario-feb", dest="calendario_feb", default=None, help="calendario oficial de la FEB (por defecto, la web de la temporada en curso)")
    ap.add_argument("--hoy", default=None, help="fecha AAAA-MM-DD (por defecto, hoy)")
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    a = ap.parse_args()
    hoy = datetime.date.fromisoformat(a.hoy) if a.hoy else datetime.date.today()
    os.makedirs(a.salida, exist_ok=True)
    if not a.calendario_feb:
        a.calendario_feb = URL_FEB_CALENDARIO.format(temporada=hoy.year if hoy.month >= 8 else hoy.year - 1)

    def guardar(nombre, datos):
        ruta = os.path.join(a.salida, nombre)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
        print("escrito", ruta)

    def partidos_de(nombre, fuente, lector):
        html = leer(fuente)
        ps = [con_desfase(p) if p.get("origen") != "feb" else p for p in lector(html) if es_del_celta(p)]
        if not ps:                                           # ni una fila reconocible: la página habrá cambiado (o el Celta no juega en la jornada que enseña)
            with open(os.path.join(a.salida, f"baloncesto_{nombre}_DEBUG.html"), "w", encoding="utf-8") as f:
                f.write(html)
            print(f"aviso: guardada baloncesto_{nombre}_DEBUG.html ({len(html)} caracteres)", file=sys.stderr)
            raise ErrorLector(f"No encuentro los partidos del Celta Femxa Zorka en {nombre}; ¿ha cambiado la página?")
        return ps

    todos = []
    for nombre, fuente, lector, origen in (("feb", a.feb, leer_feb, "feb"), ("calendario_feb", a.calendario_feb, leer_calendario_feb, "feb"),
                                           ("calendario", a.calendario, leer_partidos, "bet"), ("resultados", a.resultados, leer_partidos, "bet")):
        try:
            todos += [dict(p, origen=origen) for p in partidos_de(nombre, fuente, lector)]
        except ErrorLector as e:
            print(f"aviso: {e}", file=sys.stderr)
        except OSError as e:                                 # sin conexión o web caída: se sigue con la otra fuente
            print(f"aviso: no se pudo leer {nombre}: {e}", file=sys.stderr)
    if not todos:
        raise ErrorLector("Ninguna fuente del baloncesto ha dado datos.")
    prefiere_feb = lambda p: 0 if p["origen"] == "feb" else 1         # a igualdad de día, manda la web oficial (hora y marcador)
    jugados_clave = {(p["fecha"], norm(re.sub(r"\s+W$", "", p["local"])), norm(re.sub(r"\s+W$", "", p["visitante"]))) for p in todos if p["puntos"] is not None}
    futuros = [p for p in todos if p["puntos"] is None and p["fecha"] >= hoy      # v89: un partido que ya tiene marcador en otra fuente no es «el próximo» (el calendario de la FEB tarda días en poner los marcadores)
               and (p["fecha"], norm(re.sub(r"\s+W$", "", p["local"])), norm(re.sub(r"\s+W$", "", p["visitante"]))) not in jugados_clave]
    futuros = [p for p in futuros if p["origen"] == "feb"] or futuros               # v89: si la web oficial da calendario, solo se mira ella (BetExplorer queda de reserva)
    if futuros:
        guardar("proximo_baloncesto_fem.json", datos_partido(min(futuros, key=lambda p: (p["fecha"], prefiere_feb(p), p["hora"] or "")), "proximo"))
    else:
        print("Sin próximo partido del Celta Femxa Zorka en el calendario.")
    jugados = [p for p in todos if p["puntos"] is not None and p["fecha"] <= hoy]
    if jugados:
        guardar("resultado_baloncesto_fem.json", datos_partido(max(jugados, key=lambda p: (p["fecha"], -prefiere_feb(p))), "resultado"))
    else:
        print("Sin resultados del Celta Femxa Zorka todavía.")


if __name__ == "__main__":
    main()
