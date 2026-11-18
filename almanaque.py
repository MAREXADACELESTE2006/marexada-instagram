"""Almanaque Celta · historias de los miércoles (v67).

Lee assets/almanaque.json (hecho con convertir_almanaque.py a partir del Excel) y, si hoy es el miércoles de una publicación,
prepara sus 3 historias: 1 gancho, 2 datos, 3 cierre. Los textos son los del Excel, tal cual.

Uso de prueba:  python almanaque.py 2026-11-18
"""
import datetime
import json
import os
import re
import sys

import rccelta

BASE = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(BASE, "assets", "almanaque.json")
MESES = ["XAN", "FEB", "MAR", "ABR", "MAI", "XUÑ", "XUL", "AGO", "SET", "OUT", "NOV", "DEC"]
SERIE = "ESTA SEMANA NA HISTORIA CELESTE"

# Nombres que el buscador automático confundiría o no encontraría (clave: nombre normalizado).
ALIAS = {
    "deportivo": "deportivo-la-coruna", "depor": "deportivo-la-coruna", "barcelona": "fc-barcelona", "espanol": "rcd-espanyol-barcelona",
    "atletico de bilbao": "athletic-club-bilbao", "athletic": "athletic-club-bilbao", "olympique lyon": "olympique-lyonnais",
    "lyon": "olympique-lyonnais", "atletico de madrid": "atletico-madrid", "atletico": "atletico-madrid", "milan": "ac-milan",
    "oporto": "fc-porto", "benfica": "sl-benfica", "marsella": "olympique-de-marseille-om", "olympique marsella": "olympique-de-marseille-om",
}

_CON_MARCADOR = re.compile(r"^(?P<a>[^0-9;:(]+?)\s+(?P<ga>\d+)\s*[-–]\s*(?P<gb>\d+)\s+(?P<b>[^;:(.,]+?)\s*(?:[;:(.,]|$)")
_SIN_MARCADOR = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}:\s*(?P<a>[^-–.;]+?)\s+[-–]\s+(?P<b>[^.;(]+)")


def cargar():
    return json.load(open(RUTA, encoding="utf-8"))


def entrada(hoy, desde=None):
    """La publicación de ese miércoles (fecha ISO) o None."""
    for e in (desde if desde is not None else cargar()):
        if e["fecha"] == hoy.isoformat():
            return e
    return None


def slug(nombre):
    if not nombre:
        return None
    n = re.sub(r"\s+", " ", rccelta.norm(nombre)).strip()
    return ALIAS.get(n) or rccelta.slug_equipo(nombre)


def _celta(nombre):
    return slug(nombre) == "celta-vigo" or rccelta.norm(nombre).strip() in ("celta", "celta de vigo")


def equipos(dato):
    """(local, visitante, goles_local, goles_visitante) a partir de «Deportivo 0-1 Celta; …» o «30/11/1947: Celta de Vigo - Sevilla. …»."""
    m = _CON_MARCADOR.match(dato or "")
    if m:
        return m["a"].strip(), m["b"].strip(), int(m["ga"]), int(m["gb"])
    m = _SIN_MARCADOR.match(dato or "")
    if m:
        return m["a"].strip(), m["b"].strip(), None, None
    return None, None, None, None


def limpiar(t):
    """Quita emojis (la tipografía de las historias no los tiene y saldrían como un cuadrado) y espacios sobrantes."""
    t = "".join(c for c in (t or "") if not (ord(c) >= 0x1F000 or 0x2600 <= ord(c) <= 0x27BF or ord(c) in (0xFE0F, 0x200D, 0x20E3)))
    return re.sub(r"\s+", " ", t).strip()


def fecha_texto(iso):
    y, m, d = iso.split("-")
    return f"{int(d)} {MESES[int(m) - 1]} {y}"


def historias(e):
    """Lista de 3 dicts (uno por historia) listos para generar_historia.almanaque()."""
    a, b, ga, gb = equipos(e.get("dato"))
    # Solo se enseñan los dos equipos si uno es el Celta y el otro tiene nombre claro.
    local = visitante = None
    if a and b and (_celta(a) or _celta(b)):
        local, visitante = a, b
    anos = int(e["fecha"][:4]) - int(e["fecha_historica"][:4])
    base = {"tipo": "almanaque", "serie": SERIE, "anos": anos, "fecha_texto": fecha_texto(e["fecha_historica"]), "titular": e["titular"],
            "local": slug(local) if local else "celta-vigo", "visitante": slug(visitante) if visitante else None,
            "local_nombre": local, "visitante_nombre": visitante, "goles_local": ga, "goles_visitante": gb,
            "es_partido": bool(local), "_fecha": e["fecha"], "_hashtags": e.get("hashtags", ""), "total": 3}
    if not local:                                                  # sin rival claro: solo el escudo del Celta
        base.update({"local": "celta-vigo", "visitante": None})
    textos = [limpiar(e["s1"]), limpiar(e["s2"]), limpiar(e["s3"])]
    pregunta = limpiar(e.get("pregunta", ""))
    if pregunta and pregunta in textos[2]:                          # si el cierre ya termina con la misma pregunta, no se repite en el recuadro
        resto = textos[2].replace(pregunta, "").strip()
        if len(resto) >= 20:
            textos[2] = resto
    base["titular"] = limpiar(base["titular"])
    out = []
    for i, t in enumerate(textos, 1):
        d = dict(base, pantalla=i, texto=t)
        if i == 2:
            d["protagonistas"] = limpiar(e.get("protagonistas", ""))
        if i == 3:
            d["pregunta"] = pregunta
        out.append(d)
    return out


if __name__ == "__main__":
    f = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today()
    e = entrada(f)
    if not e:
        sys.exit(f"No hay publicación del almanaque para el {f}.")
    for h in historias(e):
        print(json.dumps(h, ensure_ascii=False, indent=1))
