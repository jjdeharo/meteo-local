#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""La calidad del aire en Montflorit, ahora y lo que queda de día (ADR 0054).

Es el índice europeo de calidad del aire (EAQI) del modelo CAMS Europa del
Copernicus Atmosphere Monitoring Service, en celdas de unos 11 km, que sirve
Open-Meteo: es un modelo, no una medida. Lo medido por la red de la
Generalitat (XVPCA) en Barberà, Sant Cugat y Montcada sale en sus datos
abiertos con 7 u 8 horas de retraso (comprobado el 09-10-2026: a las 11:40,
hasta las 4 h), así que no sirve para decir cómo está el aire ahora; la página
enlaza su mapa en tiempo real.

Categorías de Open-Meteo para el EAQI (0-20, 20-40, 40-60, 60-80, 80-100, más de
100), con los nombres del índice de calidad del aire de España, que sigue al
europeo: bona, raonablement bona, regular, desfavorable, molt desfavorable y
extremadament desfavorable. Manda el contaminante con el índice más alto.

    python3 aire.py        lo de ahora, en JSON
"""
import datetime as dt
import json
import urllib.parse

import config as C
import prevision as P

API = "https://air-quality-api.open-meteo.com/v1/air-quality"
CONTAMINANTS = ("pm2_5", "pm10", "nitrogen_dioxide", "ozone", "sulphur_dioxide")
# Límite superior de cada categoría del EAQI (Open-Meteo).
LIMITS = (20, 40, 60, 80, 100)
CATEGORIES = ("bona", "raonablement_bona", "regular", "desfavorable", "molt_desfavorable", "extremadament_desfavorable")


def categoria(index):
    return CATEGORIES[sum(index > l for l in LIMITS)] if index is not None else None


def llegeix(d, ara):
    """De la respuesta de Open-Meteo, lo de ahora y el peor momento de lo que
    queda de hoy."""
    cur = d["current"]
    per = {c: cur.get(f"european_aqi_{c}") for c in CONTAMINANTS}
    per = {c: v for c, v in per.items() if v is not None}
    hores = [{"hora": t, "index": v} for t, v in zip(d["hourly"]["time"], d["hourly"]["european_aqi"])
             if v is not None and t[:10] == ara.date().isoformat() and t >= cur["time"]]
    pitjor = max(hores, key=lambda h: h["index"]) if hores else None
    index = cur.get("european_aqi")
    return {"hora": cur["time"], "index": index, "categoria": categoria(index),
            "contaminant": max(per, key=per.get) if per else None,
            "pitjor": pitjor and {**pitjor, "categoria": categoria(pitjor["index"])}}


def calcula(ara=None):
    ara = ara or dt.datetime.now().astimezone()
    q = urllib.parse.urlencode({"latitude": C.CASA[0], "longitude": C.CASA[1], "timezone": P.TZ,
                                "current": ",".join(["european_aqi"] + [f"european_aqi_{c}" for c in CONTAMINANTS]),
                                "hourly": "european_aqi", "forecast_days": 1})
    return llegeix(json.loads(P.get(f"{API}?{q}")), ara)


if __name__ == "__main__":
    print(json.dumps(calcula(), ensure_ascii=False, indent=1))
