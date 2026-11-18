"""Descargas de internet con reintentos y «cortacircuitos» (v62).

Problema que resuelve: cuando una web (rccelta.es) devuelve 502/503/504 o no responde, antes cada lector probaba
decenas de direcciones y la ejecución se cortaba a los 4 minutos con un ERROR. Ahora:
  * un fallo pasajero (502, 503, 504, 429, tiempo agotado, conexión cortada) se reintenta 3 veces con pausas de 3 y 8 s;
  * si aun así no responde, la web se marca como «caída» durante esa ejecución y el resto de peticiones fallan al instante
    (sin esperar), con un mensaje claro: «rccelta.es no responde (HTTP Error 502...)»;
  * un error definitivo (404, 403...) NO se reintenta ni marca la web como caída.
"""
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

# v65: cabeceras de navegador real. rccelta.es empezó a devolver 403 Forbidden al identificarnos como «compatible; MarexadaCeleste/1.0».
NAVEGADOR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,gl;q=0.8,en;q=0.7",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}
TRANSITORIOS = {408, 429, 500, 502, 503, 504}
PAUSAS = (3, 8)                      # segundos de espera antes del 2.º y 3.º intento
_caidos = {}                         # host -> motivo (solo vale durante esta ejecución)
_bloqueos = {}                       # host -> nº de 403 seguidos; al 2.º se deja de insistir (no martillear una web que nos bloquea)


class SitioCaido(Exception):
    """La web no responde de forma temporal (reintentos agotados o ya marcada como caída)."""


def _transitorio(e):
    if isinstance(e, urllib.error.HTTPError):
        return e.code in TRANSITORIOS
    return isinstance(e, (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError))


def abrir(req, timeout=20, pausas=PAUSAS):
    """Como urllib.request.urlopen(...).read(), pero con reintentos. Devuelve bytes."""
    url = req.full_url if isinstance(req, urllib.request.Request) else req
    host = urllib.parse.urlparse(url).netloc
    if host in _caidos:
        raise SitioCaido(_caidos[host])
    if isinstance(req, urllib.request.Request):
        for k, v in NAVEGADOR.items():                 # mismas cabeceras que un Chrome normal, sin importar lo que pida cada lector
            req.headers.pop(k.capitalize(), None)
            req.add_header(k, v)
    ultimo = None
    for intento in range(len(pausas) + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            if isinstance(e, urllib.error.HTTPError) and e.code == 403:
                _bloqueos[host] = _bloqueos.get(host, 0) + 1
                if _bloqueos[host] >= 2:               # la web nos bloquea: no seguir llamando
                    _caidos[host] = f"{host} bloquea las peticiones ({e})"
                raise
            if not _transitorio(e):
                raise                                  # 404...: error definitivo, se cuenta tal cual
            ultimo = e
            if intento < len(pausas):
                time.sleep(pausas[intento])
    _caidos[host] = f"{host} no responde ({ultimo})"
    raise SitioCaido(_caidos[host])
