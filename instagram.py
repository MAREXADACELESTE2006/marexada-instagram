"""Marexada Celeste · publicación AUTOMÁTICA de historias en Instagram (v59).

Cómo funciona:
  1. diario.py genera las imágenes y llama a encolar(): la imagen se sube a la rama «imagenes» de este mismo repositorio (público) para que
     Instagram pueda descargarla, y se apunta en estado/cola_instagram.json con la hora a partir de la cual puede salir y hasta cuándo.
  2. Este programa (python instagram.py, un paso del workflow que se ejecuta en cada revisión) publica como historia lo que ya toca
     (API oficial de Instagram, «Content Publishing») y avisa por Telegram de cada publicación o error.
  Una historia solo se publica una vez. Si falla se reintenta (3 veces); si pasa su caducidad sin salir, se descarta y se avisa.

Variables (secretos de GitHub):  IG_USER_ID, IG_TOKEN  (ver INSTAGRAM.md).  GITHUB_TOKEN y GITHUB_REPOSITORY los pone GitHub solo.
Opcionales:  IG_SIMULACRO=1 (sube la imagen y dice qué publicaría, pero NO publica)  ·  IG_PAUSA=1 (no publica nada; lo pendiente caduca)
Uso:
    python instagram.py                 (publica lo pendiente que ya toque)
    python instagram.py --comprobar     (comprueba el token y dice con qué cuenta de Instagram está conectado)
    python instagram.py --prueba        (v58/v59: publica DE VERDAD una historia de prueba, aunque IG_SIMULACRO=1; solo si PRUEBA_CONFIRMADA=SI)
"""
import argparse
import base64
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

BASE = os.path.dirname(os.path.abspath(__file__))
MADRID = ZoneInfo("Europe/Madrid")
COLA = os.path.join(BASE, "estado", "cola_instagram.json")
GRAPH = os.environ.get("IG_GRAPH_URL") or "https://graph.facebook.com/v21.0"      # por si el token fuera de «inicio de sesión de Instagram»: https://graph.instagram.com/v21.0
RAMA = "imagenes"
MAX_INTENTOS = 3
CONSERVAR_DIAS = 1          # las imágenes ya publicadas o caducadas se borran de la rama «imagenes» un día después


def activo():
    return bool(os.environ.get("IG_USER_ID") and os.environ.get("IG_TOKEN")) or os.environ.get("IG_SIMULACRO") == "1"


def ahora():
    return datetime.datetime.now(MADRID)


# ---------------------------------------------------------------- HTTP
def _peticion(url, datos=None, cabeceras=None, metodo=None):
    """Devuelve (código, json). Nunca incluye la URL ni el token en el error."""
    req = urllib.request.Request(url, data=datos, headers=cabeceras or {}, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            cuerpo = r.read().decode("utf-8") or "{}"
            return r.status, json.loads(cuerpo)
    except urllib.error.HTTPError as e:
        try:
            cuerpo = json.loads(e.read().decode("utf-8") or "{}")
        except ValueError:
            cuerpo = {}
        return e.code, cuerpo
    except urllib.error.URLError as e:
        raise RuntimeError(f"sin conexión ({e.reason})") from None


def _error_meta(cuerpo):
    e = (cuerpo or {}).get("error") or {}
    return f"{e.get('message', 'error desconocido')} (código {e.get('code', '?')}/{e.get('error_subcode', '-')})"


def _graph(ruta, campos=None, post=False):
    token = os.environ["IG_TOKEN"]
    if post:
        datos = urllib.parse.urlencode({**(campos or {}), "access_token": token}).encode()
        codigo, j = _peticion(f"{GRAPH}/{ruta}", datos=datos, metodo="POST")
    else:
        q = urllib.parse.urlencode({**(campos or {}), "access_token": token})
        codigo, j = _peticion(f"{GRAPH}/{ruta}?{q}")
    if codigo >= 400 or "error" in j:
        raise RuntimeError(f"Instagram: {_error_meta(j)}")
    return j


# ---------------------------------------------------------------- GitHub: alojar la imagen
def _gh(metodo, ruta, cuerpo=None):
    token, repo = os.environ["GITHUB_TOKEN"], os.environ["GITHUB_REPOSITORY"]
    cab = {"authorization": f"Bearer {token}", "accept": "application/vnd.github+json", "user-agent": "marexada-bot", "x-github-api-version": "2022-11-28"}
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    url = f"https://api.github.com/repos/{repo}" + (f"/{ruta}" if ruta else "")
    return _peticion(url, datos=datos, cabeceras=cab, metodo=metodo)


def asegurar_rama():
    """Crea la rama «imagenes» (a partir de la versión que se está ejecutando) si todavía no existe."""
    codigo, _ = _gh("GET", f"git/ref/heads/{RAMA}")
    if codigo == 200:
        return
    sha = os.environ.get("GITHUB_SHA")                               # el commit que ejecuta el workflow: no hace falta preguntar por la rama principal
    if not sha:
        c, repo = _gh("GET", "")
        c2, ref = _gh("GET", f"git/ref/heads/{repo.get('default_branch', 'main')}")
        if c >= 300 or c2 >= 300 or "object" not in ref:
            raise RuntimeError(f"no se pudo leer la rama principal del repositorio ({c}/{c2})")
        sha = ref["object"]["sha"]
    codigo, j = _gh("POST", "git/refs", {"ref": f"refs/heads/{RAMA}", "sha": sha})
    if codigo >= 300 and codigo != 422:                              # 422 = ya existe (otra ejecución la acaba de crear)
        raise RuntimeError(f"no se pudo crear la rama «{RAMA}» ({codigo}: {j.get('message', '')})")


def subir_imagen(ruta_local, nombre):
    """Sube el JPEG a la rama «imagenes» y devuelve (url pública, sha)."""
    asegurar_rama()
    contenido = base64.b64encode(open(ruta_local, "rb").read()).decode()
    codigo, j = _gh("PUT", f"contents/historias/{nombre}", {"message": f"Imagen {nombre}", "content": contenido, "branch": RAMA})
    if codigo >= 300:
        raise RuntimeError(f"no se pudo subir la imagen ({codigo}: {j.get('message', '')})")
    return f"https://raw.githubusercontent.com/{os.environ['GITHUB_REPOSITORY']}/{RAMA}/historias/{nombre}", j["content"]["sha"]


def borrar_imagen(nombre, sha):
    try:
        _gh("DELETE", f"contents/historias/{nombre}", {"message": f"Borrar {nombre}", "sha": sha, "branch": RAMA})
    except Exception as e:
        print(f"aviso: no se pudo borrar {nombre}: {e}", file=sys.stderr)


# ---------------------------------------------------------------- cola
def cargar_cola():
    try:
        return json.load(open(COLA, encoding="utf-8"))
    except (OSError, ValueError):
        return []


def guardar_cola(cola):
    os.makedirs(os.path.dirname(COLA), exist_ok=True)
    json.dump(cola, open(COLA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def encolar(clave, ruta_imagen, texto, desde, hasta):
    """Sube la imagen y la apunta en la cola. desde/hasta: datetime con zona horaria. No hace nada si ya estaba en la cola."""
    cola = cargar_cola()
    if any(i["clave"] == clave for i in cola):
        return False
    nombre = re.sub(r"[^a-z0-9]+", "-", clave.lower()).strip("-")[:60] + f"-{int(time.time())}.jpg"
    try:
        url, sha = subir_imagen(ruta_imagen, nombre)
    except Exception:                                                # un reintento por si GitHub falló un momento
        time.sleep(5)
        url, sha = subir_imagen(ruta_imagen, nombre)
    cola.append({"clave": clave, "nombre": nombre, "sha": sha, "url": url, "texto": texto, "desde": desde.isoformat(), "hasta": hasta.isoformat(),
                 "estado": "pendiente", "intentos": 0, "id": None, "creada": ahora().isoformat()})
    guardar_cola(cola)
    return True


# ---------------------------------------------------------------- Telegram (avisos)
def avisar(texto):
    token, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return
    try:
        datos = urllib.parse.urlencode({"chat_id": chat, "text": texto[:3500]}).encode()
        _peticion(f"https://api.telegram.org/bot{token}/sendMessage", datos=datos, metodo="POST")
    except Exception as e:
        print(f"aviso: Telegram: {e}", file=sys.stderr)


# ---------------------------------------------------------------- Instagram
def publicar_historia(url):
    """Crea el contenedor de la historia con la imagen, espera a que Instagram la procese y la publica. Devuelve el id."""
    uid = os.environ["IG_USER_ID"]
    cid = _graph(f"{uid}/media", {"image_url": url, "media_type": "STORIES"}, post=True)["id"]
    for _ in range(30):
        s = _graph(cid, {"fields": "status_code"})
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram no pudo procesar la imagen ({s.get('status_code')})")
        time.sleep(3)
    else:
        raise RuntimeError("Instagram tardó demasiado en procesar la imagen")
    return _graph(f"{uid}/media_publish", {"creation_id": cid}, post=True)["id"]


def imagen_prueba(ruta):
    """Crea una historia de prueba (1080x1920) con el fondo del mural, el escudo y un texto claro de que es una prueba."""
    from PIL import Image, ImageDraw, ImageFont
    assets = os.path.join(BASE, "assets")
    fondo = Image.open(os.path.join(assets, "fondos", "fondo_mural_balaidos.jpg")).convert("RGB").resize((1080, 1920))
    velo = Image.new("RGB", fondo.size, (0, 20, 60))
    img = Image.blend(fondo, velo, 0.55)
    d = ImageDraw.Draw(img)
    fuente = lambda n, t: ImageFont.truetype(os.path.join(assets, "fuentes", n), t)
    escudo = Image.open(os.path.join(assets, "marca", "escudo_marexada.png")).convert("RGBA").resize((520, 520))
    img.paste(escudo, ((1080 - 520) // 2, 430), escudo)
    textos = [("PRUEBA", "Poppins-Bold.ttf", 150, 1010), ("DE PUBLICACIÓN", "Poppins-Bold.ttf", 78, 1190),
              ("Marexada Celeste", "Poppins-Medium.ttf", 64, 1330), ("Historia de prueba del sistema", "Poppins-Regular.ttf", 46, 1450)]
    for t, f, tam, y in textos:
        fu = fuente(f, tam)
        d.text(((1080 - d.textlength(t, font=fu)) / 2, y), t, font=fu, fill=(255, 255, 255))
    img.save(ruta, "JPEG", quality=88)


def prueba():
    """Publica DE VERDAD una historia de prueba en la cuenta (no usa la cola ni el diario, y no le afecta IG_SIMULACRO)."""
    if os.environ.get("PRUEBA_CONFIRMADA") != "SI":
        sys.exit("No se publica nada: en «Run workflow» hay que escribir SI en la casilla de confirmación.")
    for v in ("IG_USER_ID", "IG_TOKEN", "GITHUB_TOKEN", "GITHUB_REPOSITORY"):
        if not os.environ.get(v):
            sys.exit(f"ERROR: falta {v}")
    ruta = os.path.join(BASE, "prueba_instagram.jpg")
    imagen_prueba(ruta)
    nombre = f"prueba-{int(time.time())}.jpg"
    url, sha = subir_imagen(ruta, nombre)
    try:
        id_historia = publicar_historia(url)
    finally:
        borrar_imagen(nombre, sha)                                   # ya procesada por Instagram (o fallida): la imagen no hace falta
    print(f"Historia de prueba publicada en Instagram (id {id_historia}). Bórrala a mano desde la app si no quieres que dure 24 horas.")
    avisar("✅ Prueba de Instagram: historia de prueba PUBLICADA en la cuenta. Puedes borrarla desde la app.")


def comprobar():
    j = _graph(os.environ["IG_USER_ID"], {"fields": "username"})
    print(f"Conectado con @{j.get('username')} (id {j.get('id')}). Todo listo para publicar.")


def procesar():
    cola = cargar_cola()
    if not cola:
        print("Instagram: cola vacía.")
        return 0
    simulacro = os.environ.get("IG_SIMULACRO") == "1"
    pausa = os.environ.get("IG_PAUSA") == "1"
    t = ahora()
    publicadas = 0
    for it in sorted((i for i in cola if i["estado"] == "pendiente"), key=lambda i: i["desde"]):
        desde, hasta = datetime.datetime.fromisoformat(it["desde"]), datetime.datetime.fromisoformat(it["hasta"])
        if t < desde:
            continue
        if t > hasta:
            it["estado"] = "caducada"
            avisar(f"⏱️ Instagram: no se publicó a tiempo y se descarta: {it['texto']}")
            continue
        if pausa:
            print("Instagram: IG_PAUSA=1, no se publica nada.")
            break
        try:
            if simulacro:
                it["estado"] = "simulada"
                avisar(f"🧪 SIMULACRO (no publicado). Imagen: {it['url']}\n{it['texto']}")
            else:
                it["id"] = publicar_historia(it["url"])
                it["estado"] = "publicada"
                it["publicada"] = ahora().isoformat()
                publicadas += 1
                avisar(f"✅ Publicada en Instagram (historia): {it['texto']}")
        except Exception as e:
            it["intentos"] += 1
            it["ultimo_error"] = str(e)[:300]
            print(f"aviso: {it['clave']}: {e}", file=sys.stderr)
            if it["intentos"] >= MAX_INTENTOS:
                it["estado"] = "fallida"
                avisar(f"❌ Instagram: no se pudo publicar tras {MAX_INTENTOS} intentos: {it['texto']}\nMotivo: {it['ultimo_error']}")
        guardar_cola(cola)                                           # tras cada historia: si el trabajo se corta, no se repite
    # limpieza: las ya resueltas se borran de la rama y de la cola al pasar CONSERVAR_DIAS
    limite = t - datetime.timedelta(days=CONSERVAR_DIAS)
    resto = []
    for it in cola:
        if it["estado"] != "pendiente" and datetime.datetime.fromisoformat(it["hasta"]) < limite:
            if it.get("sha") and "GITHUB_TOKEN" in os.environ:
                borrar_imagen(it["nombre"], it["sha"])
        else:
            resto.append(it)
    guardar_cola(resto)
    print(f"Instagram: {publicadas} publicada(s); pendientes: {sum(1 for i in resto if i['estado'] == 'pendiente')}.")
    return publicadas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--comprobar", action="store_true")
    ap.add_argument("--prueba", action="store_true")
    a = ap.parse_args()
    if a.comprobar:
        try:
            comprobar()
        except Exception as e:
            sys.exit(f"ERROR: {e}")
        return
    if a.prueba:
        try:
            prueba()
        except Exception as e:
            avisar(f"❌ Prueba de Instagram: {str(e)[:300]}")
            sys.exit(f"ERROR: {e}")
        return
    if not activo():
        print("Instagram: sin IG_USER_ID / IG_TOKEN, no se publica (solo Telegram).")
        return
    try:
        procesar()
    except Exception as e:
        avisar(f"❌ Instagram: error inesperado: {str(e)[:300]}")
        sys.exit(f"ERROR: {e}")


if __name__ == "__main__":
    main()
