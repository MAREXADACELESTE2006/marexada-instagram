"""Marexada Celeste · caras de los jugadores (v79).

buscar(nombre) devuelve la ruta de la cara recortada (assets/caras/<nombre>.webp) del jugador cuyo nombre se parece a `nombre`
(p. ej. «Iago Aspas», «I. Aspas» o «Aspas»), o None si no hay foto o hay duda. Con la duda NO se adivina: más vale sin foto que con la foto de otro.
Solo usa a los jugadores de cumpleanos.json que tienen foto.
"""
import json
import os
import re
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))


def _slug(t):
    t = unicodedata.normalize("NFKD", (t or "").lower().replace("ı", "i")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def _candidatos():
    try:
        personas = json.load(open(os.path.join(BASE, "cumpleanos.json"), encoding="utf-8"))["personas"]
    except Exception:
        return []
    out = []
    for p in personas:
        ruta = os.path.join(BASE, "assets", "caras", _slug(p["nombre"]) + ".webp")
        if os.path.exists(ruta):
            out.append((_slug(p["nombre"]).split("-"), ruta))
    return out


def buscar(nombre):
    s = _slug(nombre)
    if not s:
        return None
    cands = _candidatos()
    for toks, ruta in cands:                                       # nombre completo
        if "-".join(toks) == s:
            return ruta
    partes = s.split("-")
    iniciales = [p for p in partes if len(p) == 1]                 # «I. Aspas» → inicial i + apellido aspas
    resto = [p for p in partes if len(p) > 1]
    if not resto:
        return None
    ok = [(t, r) for t, r in cands if all(x in t for x in resto) and all(t[0].startswith(i) for i in iniciales)]
    if len(ok) == 1 and (iniciales or len(resto) >= 2 or resto[0] != ok[0][0][0]):      # un nombre de pila suelto («Hugo», «Javi») nunca vale
        return ok[0][1]
    return None


if __name__ == "__main__":
    import sys
    for n in sys.argv[1:] or ["Iago Aspas", "I. Aspas", "Aspas", "Hugo", "Javi", "Hugo Álvarez", "Álvarez", "Moriba", "Borja Iglesias", "Jutglà", "Pepe"]:
        print(f"{n!r:18} -> {os.path.basename(buscar(n) or '') or None}")
