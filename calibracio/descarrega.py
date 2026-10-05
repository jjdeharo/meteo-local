#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Descarga lo necesario para calibrar la regla con lo que pasó de verdad.

- Lluvia semihoraria medida en las estaciones (portal de datos abiertos de la
  Generalitat, variable 35 de la XEMA).
- Previsiones archivadas de Open-Meteo para casa y destino:
  · «day0»: primeras horas de cada pasada, unidas (corto plazo);
  · «day1»: la previsión hecha un día antes (24 h de antelación).

Los datos van a calibracio/dades/, que no se sube al repositorio.

Uso: python3 calibracio/descarrega.py [inicio] [fin] [--forzar]
(--forzar vuelve a bajar las observaciones ya descargadas)
"""
import csv
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dades")
PORTAL = "https://analisi.transparenciacatalunya.cat/resource/nzvn-apee.json"
PREVIAS = "https://previous-runs-api.open-meteo.com/v1/forecast"
MODELOS = C.MODELOS_FINOS
UA = {"User-Agent": "meteo-local/" + C.VERSION}


def get_json(url, intentos=4):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except (TimeoutError, OSError):
            if i == intentos - 1:
                raise
            print("  reintento", i + 1)


def observaciones(inicio, fin):
    """Ordenado de más reciente a más antiguo y filtrado aquí: con filtro de
    fechas el portal tarda minutos y corta la conexión; ordenado por fecha
    responde, aunque de forma irregular, así que va en tandas y con reintentos."""
    for codi in C.ESTACIONES:
        ruta = os.path.join(DIR, f"obs_{codi}.csv")
        if os.path.exists(ruta) and "--forzar" not in sys.argv:
            print(f"{codi}: ya descargado ({ruta})")
            continue
        filas, offset = [], 0
        while True:
            q = urllib.parse.urlencode({
                "$select": "data_lectura,valor_lectura",
                "$where": f"codi_estacio='{codi}' AND codi_variable='35'",
                "$order": "data_lectura DESC", "$limit": 20000, "$offset": offset})
            lote = get_json(f"{PORTAL}?{q}")
            filas += [x for x in lote if inicio <= x["data_lectura"][:10] < fin]
            if len(lote) < 20000 or lote[-1]["data_lectura"][:10] < inicio:
                break
            offset += 20000
        filas.sort(key=lambda x: x["data_lectura"])
        with open(ruta, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["inicio_utc", "mm"])
            for x in filas:
                w.writerow([x["data_lectura"][:16], x["valor_lectura"]])
        print(f"{codi}: {len(filas)} medias horas -> {ruta}")


def previsiones(inicio, fin):
    variables = ["precipitation", "precipitation_previous_day1", "cape", "cape_previous_day1"]
    for nombre, (lat, lon) in (("casa", C.CASA), ("desti", C.DESTINO)):
        tramos = []
        a = dt.date.fromisoformat(inicio)
        final = dt.date.fromisoformat(fin)
        while a < final:
            b = min(a + dt.timedelta(days=180), final - dt.timedelta(days=1))
            q = urllib.parse.urlencode({
                "latitude": lat, "longitude": lon, "hourly": ",".join(variables),
                "models": ",".join(MODELOS), "timezone": "UTC",
                "start_date": a.isoformat(), "end_date": b.isoformat()})
            tramos.append(get_json(f"{PREVIAS}?{q}")["hourly"])
            a = b + dt.timedelta(days=1)
        claves = [k for k in tramos[0] if k != "time"]
        ruta = os.path.join(DIR, f"prev_{nombre}.csv")
        with open(ruta, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["hora_utc"] + claves)
            for t in tramos:
                for i, hora in enumerate(t["time"]):
                    w.writerow([hora] + [t[k][i] for k in claves])
        print(f"{nombre}: {sum(len(t['time']) for t in tramos)} horas -> {ruta}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    inicio = args[0] if args else "2024-01-01"
    fin = args[1] if len(args) > 1 else dt.date.today().isoformat()
    os.makedirs(DIR, exist_ok=True)
    observaciones(inicio, fin)
    previsiones(inicio, fin)
