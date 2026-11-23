"""Marexada Celeste · Celta Femxa Zorka (baloncesto femenino, Liga Femenina Endesa) desde BetExplorer (v87).

Como con el AS Celtas Fem, solo se publican DOS cosas: el próximo partido y el resultado (nada de directo, alineación ni convocatoria).
Lee dos páginas públicas de betexplorer.com del equipo (calendario y resultados) y escribe en datos_reales/ (o en --salida):
    proximo_baloncesto_fem.json      (próximo partido)
    resultado_baloncesto_fem.json    (último partido jugado)

Uso:
    python baloncesto.py                                                  (lee internet)
    python baloncesto.py --calendario a.html --resultados b.html --hoy 2026-11-23 --salida carpeta     (prueba sin internet)
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
    return "celta" in (norm(re.sub(r"\s+W$", "", p["local"])), norm(re.sub(r"\s+W$", "", p["visitante"])))


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

    def partidos_de(nombre, fuente):
        html = leer(fuente)
        ps = [con_desfase(p) for p in leer_partidos(html) if es_del_celta(p)]
        if not ps:                                           # ni una fila reconocible: la página habrá cambiado
            with open(os.path.join(a.salida, f"baloncesto_{nombre}_DEBUG.html"), "w", encoding="utf-8") as f:
                f.write(html)
            print(f"aviso: guardada baloncesto_{nombre}_DEBUG.html ({len(html)} caracteres)", file=sys.stderr)
            raise ErrorLector(f"No encuentro los partidos del Celta Femxa Zorka en BetExplorer ({nombre}); ¿ha cambiado la página?")
        return ps

    try:
        futuros = [p for p in partidos_de("calendario", a.calendario) if p["puntos"] is None and p["fecha"] >= hoy]
        if futuros:
            guardar("proximo_baloncesto_fem.json", datos_partido(min(futuros, key=lambda p: (p["fecha"], p["hora"] or "")), "proximo"))
        else:
            print("Sin próximo partido del Celta Femxa Zorka en el calendario.")
    except ErrorLector as e:
        print(f"aviso: {e}", file=sys.stderr)
    try:
        jugados = [p for p in partidos_de("resultados", a.resultados) if p["puntos"] is not None and p["fecha"] <= hoy]
        if jugados:
            guardar("resultado_baloncesto_fem.json", datos_partido(max(jugados, key=lambda p: p["fecha"]), "resultado"))
        else:
            print("Sin resultados del Celta Femxa Zorka todavía.")
    except ErrorLector as e:
        print(f"aviso: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
