"""Marexada Celeste · alineación del Celta (primer equipo) y del Celta Fortuna (v86) antes del partido (v85).

Lee el once inicial en ESPN (la misma fuente que directo.py), lo ordena por posiciones (portero, defensas, mediocentros, delanteros)
y escribe datos_reales/alineacion_celta.json (y alineacion_fortuna.json con el estilo turquesa del Fortuna). El dibujo (con las caras) está en generar_historia.py (`_alineacion_posiciones`).

Si ESPN no da el once (o lo da incompleto), se intenta besoccer. OJO: el lector de besoccer todavía NO interpreta la página (no tengo
una copia real); solo guarda el HTML en datos_reales/alineacion_besoccer_RAW.html para poder escribirlo con datos reales.
Nunca se publica un once incompleto: tiene que haber 11 titulares, 1 portero y las posiciones claras. Nunca rompe el programa.

Uso:
    python alineacion.py                                          (lee internet)
    python alineacion.py --desde fixtures/espn_alineacion_EJEMPLO.json   (prueba sin internet)
"""
import argparse
import datetime
import json
import os
import re
import sys

import resultados as R
from calendario import MADRID

BASE = os.path.dirname(os.path.abspath(__file__))
LIGAS = {"celta": (("esp.1", "liga"), ("uefa.europa", "euro"), ("esp.copa_del_rey", "copa")), "fortuna": (("esp.2", "hm"),)}
ANTES_MIN = 150                      # se busca la alineación desde 2 h 30 min antes del partido...
DESPUES_MIN = 10                     # ...hasta 10 min después de empezar (después ya no tiene sentido)
GRUPOS = ("POR", "DEF", "MED", "DEL")
TITULO_GRUPO = {"POR": "PORTEIRO", "DEF": "DEFENSAS", "MED": "CENTROCAMPISTAS", "DEL": "DIANTEIROS"}


# ---------------------------------------------------------------- posiciones
def grupo_de_abreviatura(ab):
    """Abreviatura de posición de ESPN (G, CD-L, LB, DM, CM-R, AM, LF, F, ST...) -> POR | DEF | MED | DEL | None."""
    ab = (ab or "").upper().strip()
    if not ab or ab in ("SUB", "S"):
        return None
    if ab in ("G", "GK") or ab.startswith("GK"):
        return "POR"
    if re.match(r"^(CD|SW|D$|D-|LWB|RWB|WB|CB|LB|RB)", ab):
        return "DEF"
    if re.match(r"^(DM|CM|AM|CAM|CDM|LM|RM|M$|M-)", ab):
        return "MED"
    if re.match(r"^(F$|F-|CF|ST|SS|LF|RF|LW|RW|W$|W-|FW)", ab):
        return "DEL"
    return None


def grupo_de_gallego(pos):
    """Posición de cumpleanos.json (en gallego) -> grupo. Extremo cuenta como delantero y pivote como mediocentro."""
    p = (pos or "").lower()
    if "porteiro" in p:
        return "POR"
    if "dianteiro" in p or "extremo" in p:
        return "DEL" if "centrocampista" not in p else "MED"
    if "centrocampista" in p or "pivote" in p:
        return "MED"
    if "defensa" in p:
        return "DEF"
    return None


def grupos_por_formacion(formacion, n_lugares):
    """'4-2-3-1' y los 11 titulares ordenados por su lugar en la formación -> lista de 11 grupos (portero, 4 defensas, 5 medios, 1 delantero)."""
    try:
        lineas = [int(x) for x in re.split(r"[-\s]+", formacion.strip()) if x]
    except (AttributeError, ValueError):
        return None
    if n_lugares != 11 or sum(lineas) != 10 or len(lineas) < 3:
        return None
    return ["POR"] + ["DEF"] * lineas[0] + ["MED"] * sum(lineas[1:-1]) + ["DEL"] * lineas[-1]


# ---------------------------------------------------------------- nombres
def corto(nombre):
    """«Iago Aspas» -> «Aspas»; si otro jugador de la plantilla comparte el apellido -> «H. Álvarez». Una sola palabra se deja igual."""
    partes = (nombre or "").split()
    if len(partes) < 2:
        return nombre or ""
    apellido = " ".join(partes[1:])
    try:
        import caras
        ap = caras._slug(apellido)
        plantilla = json.load(open(os.path.join(BASE, "cumpleanos.json"), encoding="utf-8"))["personas"]
        mismos = [p for p in plantilla if caras._slug(p["nombre"]).split("-", 1)[-1] == ap]
        if len(mismos) > 1:
            return f"{partes[0][0]}. {apellido}"
    except Exception:
        pass
    return apellido


def _persona(j):
    a = j.get("athlete") or {}
    return a.get("displayName") or a.get("fullName") or a.get("shortName") or j.get("displayName") or ""


def _dorsal(j):
    d = j.get("jersey") or (j.get("athlete") or {}).get("jersey")
    try:
        return int(str(d).strip())
    except (TypeError, ValueError):
        return None


def _abreviatura(j):
    p = j.get("position") or (j.get("athlete") or {}).get("position") or {}
    return p.get("abbreviation") or p.get("name") or ""


# ---------------------------------------------------------------- lectura del resumen de ESPN
def once_de_resumen(resumen, celta_id):
    """Resumen de un partido de ESPN (summary?event=ID) -> {'once': [...], 'suplentes': [...], 'formacion': '4-2-3-1'} del Celta, o None si
    el once no está (todavía) o no es fiable. Cada jugador: {'dorsal', 'nombre', 'completo', 'grupo'}. ESPN no documenta su formato: se miran
    varios sitios (rosters/roster, starter, position.abbreviation, formationPlace) y, si algo no cuadra, NO se inventa nada."""
    rosters = resumen.get("rosters") or []
    mio = None
    for r in rosters:
        if str((r.get("team") or {}).get("id", "")) == str(celta_id):
            mio = r
            break
    if not mio:
        return None
    jugadores = mio.get("roster") or []
    titulares = [j for j in jugadores if j.get("starter") is True]
    if len(titulares) != 11:
        return None
    if any(j.get("formationPlace") not in (None, "") for j in titulares):          # ordenados por su lugar en el campo si ESPN lo da
        titulares.sort(key=lambda j: int(str(j.get("formationPlace") or 99)) if str(j.get("formationPlace") or "99").isdigit() else 99)
    suplentes = [j for j in jugadores if j.get("starter") is not True]
    formacion = mio.get("formation") or ""

    grupos = [grupo_de_abreviatura(_abreviatura(j)) for j in titulares]
    if None in grupos or grupos.count("POR") != 1:                                   # 1.º: por la abreviatura; 2.º: por la formación; 3.º: por cumpleanos.json
        g2 = grupos_por_formacion(formacion, 11) if all(j.get("formationPlace") not in (None, "") for j in titulares) else None
        if g2:
            grupos = g2
        else:
            try:
                import caras
                grupos = [grupo_de_abreviatura(_abreviatura(j)) or grupo_de_gallego(caras.posicion_de(_persona(j))) for j in titulares]
            except Exception:
                return None
    if None in grupos or not _valida(grupos):
        return None

    def ficha(j, g):
        n = _persona(j)
        return {"dorsal": _dorsal(j), "nombre": corto(n), "completo": n, "grupo": g}
    once = [ficha(j, g) for j, g in zip(titulares, grupos)]
    sup = [ficha(j, grupo_de_abreviatura(_abreviatura(j)) or "MED") for j in suplentes if _persona(j)]
    return {"once": once, "suplentes": sup, "formacion": formacion}


def _valida(grupos):
    return len(grupos) == 11 and grupos.count("POR") == 1 and grupos.count("DEF") >= 3 and grupos.count("DEL") >= 1 and grupos.count("MED") >= 1


# ---------------------------------------------------------------- partido
def _estado(ev):
    c = (ev.get("competitions") or [{}])[0]
    return ((c.get("status") or ev.get("status") or {}).get("type") or {})


def partidos_proximos(registro, eq="celta"):
    """Partidos del Celta (primer equipo) o del Fortuna que no han terminado, de sus competiciones: [(evento, clave_competicion, liga)]."""
    vistos, out = set(), []
    id_eq = R.FORTUNA_ESPN if eq == "fortuna" else R.CELTA_ESPN
    for liga, k in LIGAS[eq]:
        base = R.ESPN.format(liga)
        for url in (base + f"teams/{id_eq}/schedule?fixture=true", base + "scoreboard"):
            try:
                evs = R.get(url).get("events") or []
            except Exception as e:
                registro.append(f"alineacion {liga}: ERROR {type(e).__name__}: {e}")
                continue
            for ev in evs:
                ids = {str((t.get("team") or {}).get("id", "")) for t in ((ev.get("competitions") or [{}])[0].get("competitors") or [])}
                nombres = " ".join(((t.get("team") or {}).get("displayName") or "") for t in ((ev.get("competitions") or [{}])[0].get("competitors") or []))
                if str(id_eq) not in ids or (eq == "celta" and R.es_fortuna(nombres)) or ev.get("id") in vistos:
                    continue
                if _estado(ev).get("completed"):
                    continue
                vistos.add(ev.get("id"))
                out.append((ev, k, liga))
    return out


def a_partido(ev, k):
    c = (ev.get("competitions") or [{}])[0]
    h = a = None
    for t in c.get("competitors", []):
        if t.get("homeAway") == "home":
            h = t
        else:
            a = t
    if not h or not a:
        return None
    nm = lambda t: (t.get("team") or {}).get("displayName") or (t.get("team") or {}).get("name") or ""
    try:
        f = datetime.datetime.fromisoformat((ev.get("date") or c.get("date")).replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return {"f": f, "k": k, "home": nm(h), "away": nm(a), "gl": 0, "gv": 0, "id": ev.get("id") or c.get("id"),
            "home_id": str((h.get("team") or {}).get("id", "")), "away_id": str((a.get("team") or {}).get("id", ""))}


def en_ventana(f, ahora):
    m = (f - ahora).total_seconds() / 60
    return -DESPUES_MIN <= m <= ANTES_MIN


def datos(p, once, eq="celta"):
    """JSON que entiende generar.py: lo de siempre (tipo alineacion) más `grupos` (lo que dibuja el diseño con caras)."""
    d = R.datos(p, eq)
    f = p["f"].astimezone(MADRID)
    hora = f"{f.hour:02d}:{f.minute:02d}"
    d.update(tipo="alineacion", fecha_hora=f"{d['fecha_hora']} · {hora}", _id=str(p.get("id") or ""), formacion=once.get("formacion") or "")
    for k in ("goles_local", "goles_visitante", "goleadores_local", "goleadores_visitante"):
        d.pop(k, None)
    d["once"] = [{"dorsal": j["dorsal"], "nombre": j["nombre"], "completo": j["completo"]} for j in once["once"]]
    d["suplentes"] = [{"dorsal": j["dorsal"], "nombre": j["nombre"]} for j in once["suplentes"]]
    d["grupos"] = [{"clave": g, "titulo": TITULO_GRUPO[g], "jugadores": [{"dorsal": j["dorsal"], "nombre": j["nombre"], "completo": j["completo"]}
                                                                          for j in once["once"] if j["grupo"] == g]} for g in GRUPOS]
    local_celta = R.es_celta(p["home"]) and eq == "celta"
    d["lugar"] = "Balaídos" if local_celta else None                     # (del Fortuna no se sabe el campo: no se pone)
    d["entrenador"] = once.get("entrenador") or None
    return {k: v for k, v in d.items() if v is not None}


# ---------------------------------------------------------------- besoccer (de reserva)
def desde_besoccer(url, salida, registro):
    """TODAVÍA NO interpreta la página: guarda el HTML para poder escribir el lector con datos reales. Devuelve None."""
    try:
        import red
        import urllib.request
        html = red.abrir(urllib.request.Request(url)).decode("utf-8", "replace")
        open(os.path.join(salida, "alineacion_besoccer_RAW.html"), "w", encoding="utf-8").write(html)
        registro.append(f"besoccer: página guardada ({len(html)} caracteres), sin interpretar todavía")
    except Exception as e:
        registro.append(f"besoccer: ERROR {type(e).__name__}: {e}")
    return None


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", default=None, help="prueba sin internet: archivo con {'events': [...], 'resumen': {...}}")
    ap.add_argument("--equipo", default="celta", choices=("celta", "fortuna"), help="solo con --desde: de qué equipo es el archivo")
    ap.add_argument("--ahora", default=None, help="UTC AAAA-MM-DDTHH:MM:SS (por defecto, ahora)")
    ap.add_argument("--salida", default=os.path.join(BASE, "datos_reales"))
    a = ap.parse_args()
    os.makedirs(a.salida, exist_ok=True)
    ahora = datetime.datetime.fromisoformat(a.ahora).replace(tzinfo=datetime.timezone.utc) if a.ahora else datetime.datetime.now(datetime.timezone.utc)
    registro = []
    for eq in ([a.equipo] if a.desde else ["celta", "fortuna"]):
        try:
            id_eq = R.FORTUNA_ESPN if eq == "fortuna" else R.CELTA_ESPN
            if a.desde:
                j = json.load(open(a.desde, encoding="utf-8"))
                cand = [(ev, "hm" if eq == "fortuna" else "liga", "esp.2" if eq == "fortuna" else "esp.1") for ev in j.get("events", [])]
                resumenes = {str(j.get("resumen_id")): j.get("resumen") or {}}
            else:
                cand, resumenes = partidos_proximos(registro, eq), {}
            hechos = 0
            for ev, k, liga in cand:
                p = a_partido(ev, k)
                if not p or not en_ventana(p["f"], ahora):
                    continue
                try:
                    resumen = resumenes.get(str(p["id"])) if a.desde else R.get(R.ESPN.format(liga) + f"summary?event={p['id']}")
                except Exception as e:
                    registro.append(f"ESPN {eq} {liga} {p['id']}: ERROR {type(e).__name__}: {e}")
                    continue
                once = once_de_resumen(resumen or {}, id_eq)
                if not once:
                    registro.append(f"ESPN {eq} {liga} {p['id']}: todavía sin once fiable")
                    if eq == "celta" and not a.desde and 40 <= (p["f"] - ahora).total_seconds() / 60 <= 60:        # reserva (sin interpretar aún): solo 1 o 2 veces por partido, para no martillear la web
                        desde_besoccer("https://es.besoccer.com/equipo/partidos/rc-celta", a.salida, registro)
                    continue
                ruta = os.path.join(a.salida, f"alineacion_{eq}.json")
                json.dump(datos(p, once, eq), open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print("escrito", ruta)
                hechos += 1
                break
            if not hechos:
                print(f"Sin alineación del {'Celta Fortuna' if eq == 'fortuna' else 'Celta'} que publicar ahora.")
        except Exception as e:                                   # la alineación es un extra: si algo falla, no se para nada
            print(f"aviso: alineación del {eq} sin datos ({e})", file=sys.stderr)
    if registro:
        open(os.path.join(a.salida, "alineacion_log.txt"), "w", encoding="utf-8").write(
            datetime.datetime.now(MADRID).strftime("%Y-%m-%d %H:%M Madrid") + "\n" + "\n".join(registro) + "\n")


if __name__ == "__main__":
    main()
