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

TRANSITORIOS = {408, 429, 500, 502, 503, 504}
PAUSAS = (3, 8)                      # segundos de espera antes del 2.º y 3.º intento
_caidos = {}                         # host -> motivo (solo vale durante esta ejecución)


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
        raise SitioCaido(f"{host} no responde ({_caidos[host]})")
    ultimo = None
    for intento in range(len(pausas) + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            if not _transitorio(e):
                raise                                  # 404, 403...: error definitivo, se cuenta tal cual
            ultimo = e
            if intento < len(pausas):
                time.sleep(pausas[intento])
    _caidos[host] = str(ultimo)
    raise SitioCaido(f"{host} no responde ({ultimo})")
