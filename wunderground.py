#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sube la estación de casa a Weather Underground (ADR 0059).

En cada pasada de la página, con la lectura de Ecowitt que ya se ha hecho,
se manda a la red de estaciones personales de Weather Underground lo que
mide la estación: temperatura, humedad, punto de rocío, presión al nivel
del mar, lluvia de la última hora y del día, radiación y UV. El viento no,
porque el anemómetro no funciona bien (ADR 0017). Así la estación cuenta
como contribuidora y Juanjo tiene la clave de lectura de esa red.

Las claves no están en el repositorio: WU_STATION_ID y WU_STATION_KEY en el
entorno o en ~/.config/meteo-local/wunderground.env. Sin ellas, no se sube.

Uso:
  python3 wunderground.py puja      lee Ecowitt y sube una vez
  python3 wunderground.py mostra    enseña lo que se mandaría, sin subir
"""
import datetime as dt
import os
import sys
import urllib.parse
import urllib.request

import ecowitt as E

URL = "https://weatherstation.wunderground.com/weatherstation/updateweatherstation.php"
PROGRAMA = "meteo-local"


def claves():
    e = {k: os.environ.get(k) for k in ("WU_STATION_ID", "WU_STATION_KEY")}
    if all(e.values()):
        return e
    ruta = os.path.expanduser("~/.config/meteo-local/wunderground.env")
    try:
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                k, _, v = linea.strip().partition("=")
                if k in e and not e[k]:
                    e[k] = v
    except OSError:
        pass
    return e if all(e.values()) else None


def disponible():
    return claves() is not None


def _f(c):
    return None if c is None else round(c * 9 / 5 + 32, 1)


def _polzades(mm):
    return None if mm is None else round(mm / 25.4, 3)


def parametres(casa, ahora=None):
    """Lo que se manda, en las unidades de Weather Underground (°F, inHg,
    pulgadas), a partir de la lectura de ecowitt.resum_ara o ecowitt.ara."""
    hora = dt.datetime.fromisoformat(casa["hora"]) if casa.get("hora") else (ahora or dt.datetime.now().astimezone())
    d = {"dateutc": hora.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
         "tempf": _f(casa.get("temperatura")), "humidity": casa.get("humitat"),
         "dewptf": _f(casa.get("rosada")),
         "baromin": None if casa.get("pressio") is None else round(casa["pressio"] / 33.8639, 3),
         "rainin": _polzades(casa.get("pluja_1h")), "dailyrainin": _polzades(casa.get("pluja_avui")),
         "solarradiation": casa.get("solar"), "UV": casa.get("uv"),
         "softwaretype": PROGRAMA, "action": "updateraw"}
    return {k: v for k, v in d.items() if v is not None}


def puja(casa, ahora=None, lector=None):
    """Sube una lectura. Devuelve la respuesta («success») o None sin claves."""
    k = claves()
    if not k:
        return None
    q = urllib.parse.urlencode({"ID": k["WU_STATION_ID"], "PASSWORD": k["WU_STATION_KEY"],
                                **parametres(casa, ahora)})
    if lector:
        return lector(f"{URL}?{q}")
    req = urllib.request.Request(f"{URL}?{q}", headers={"User-Agent": PROGRAMA})
    with urllib.request.urlopen(req, timeout=20) as r:
        resposta = r.read().decode("utf-8", "replace").strip()
    if resposta != "success":
        raise RuntimeError(f"Weather Underground: {resposta[:80]}")
    return resposta


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else ""
    if orden in ("puja", "mostra"):
        if not E.disponible():
            sys.exit("sense claus d'Ecowitt")
        casa = E.resum_ara()
        print(parametres(casa))
        if orden == "puja":
            print(puja(casa) or "sense claus de Weather Underground: no es puja")
    else:
        print(__doc__)
