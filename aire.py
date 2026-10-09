#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""La calidad del aire en Montflorit, ahora y lo que queda de día (ADR 0054).

**Es una estimación, no una medida de Montflorit.** Sale del modelo CAMS
Europa del Copernicus Atmosphere Monitoring Service, que sirve Open-Meteo, en
celdas de 0,1° (unos 11 × 8 km aquí): la de Montflorit tiene el centro en
Bellaterra y da un solo valor para la zona de Sant Cugat a Ripollet. El
09-10-2026, comparado con las estaciones de la Generalitat, daba de noche
alrededor del doble de NO₂ que el medido y menos partículas.

Por eso:
- **Se corrige con lo medido.** Una vez al día se comparan las horas del último
  mes en que hay a la vez modelo (Open-Meteo guarda los días pasados) y medida
  de las estaciones de la red de la Generalitat (XVPCA, datos abiertos
  `tasf-thgu`) de Barberà, Sant Cugat y Montcada, y para cada contaminante se
  calcula cuánto se desvía el modelo: el cociente entre la suma de lo medido y
  la de lo previsto. Solo si lo miden al menos dos estaciones
  (`AIRE_ESTACIONS_MIN`): hoy, el NO₂ y el ozono. Las concentraciones del modelo se multiplican por ese
  factor y el índice se recalcula con la tabla del índice europeo (EAQI) de
  Open-Meteo: para cada contaminante, interpolado dentro de su tramo, y el
  total, el del peor. Sin bastantes horas (`AIRE_HORES_MIN`), no se corrige.
- **Se da la última medida de cada estación**, con su hora: la red publica sus
  datos abiertos con unas 7 u 8 horas de retraso, así que no sirven para decir
  cómo está el aire ahora, pero sí para ver si la estimación exagera.

Categorías (de 0-20 a más de 100), con los nombres del índice español, que
sigue al europeo: bona, raonablement bona, regular, desfavorable, molt
desfavorable y extremadament desfavorable.

En el NAS (con AIRE_DIR) se guarda la corrección del día.

    python3 aire.py        lo de ahora, en JSON
"""
import datetime as dt
import json
import math
import os
import urllib.parse
import urllib.request

import config as C
import prevision as P

API = "https://air-quality-api.open-meteo.com/v1/air-quality"
XVPCA = "https://analisi.transparenciacatalunya.cat/resource/tasf-thgu.json"
CONTAMINANTS = ("pm2_5", "pm10", "nitrogen_dioxide", "ozone", "sulphur_dioxide")
# Límite superior de cada categoría del índice (Open-Meteo).
LIMITS = (20, 40, 60, 80, 100)
CATEGORIES = ("bona", "raonablement_bona", "regular", "desfavorable", "molt_desfavorable", "extremadament_desfavorable")
# Tramos de concentración horaria (µg/m³) de cada categoría, de la tabla del
# índice europeo de la documentación de Open-Meteo (consultada el 09-10-2026).
TRAMS = {"pm2_5": (5, 15, 50, 90, 140), "pm10": (15, 45, 120, 195, 270),
         "nitrogen_dioxide": (10, 25, 60, 100, 150), "ozone": (60, 100, 120, 160, 180),
         "sulphur_dioxide": (20, 40, 125, 190, 275)}
# Las estaciones de la red de la Generalitat más cercanas y cómo llama cada
# contaminante.
ESTACIONS = {"Barberà del Vallès": (41.513, 2.125), "Sant Cugat del Vallès": (41.477, 2.089),
             "Montcada i Reixac": (41.482, 2.188)}
NOM_XVPCA = {"NO2": "nitrogen_dioxide", "O3": "ozone", "PM10": "pm10", "PM2.5": "pm2_5", "SO2": "sulphur_dioxide"}
DIES_CORRECCIO = 30
AIRE_HORES_MIN = 72          # horas emparejadas por contaminante para corregir
# Solo se corrige con al menos dos estaciones: las partículas (PM10) solo las
# mide Montcada, junto a la cementera, y su factor (2,5 el 09-10-2026) diría
# más de Montcada que de Montflorit.
AIRE_ESTACIONS_MIN = 2
CACHE = os.path.join(os.environ.get("AIRE_DIR", "/estat"), "aire-correccio.json")
UA = {"User-Agent": "Temps a Montflorit (https://meteo-montflorit.github.io/)"}


def categoria(index):
    return CATEGORIES[sum(index > l for l in LIMITS)] if index is not None else None


def index_de(contaminant, conc):
    """El índice europeo (0-100 y más) de una concentración, interpolado
    dentro de su tramo."""
    if conc is None:
        return None
    trams = (0,) + TRAMS[contaminant]
    for n in range(len(trams) - 1):
        if conc <= trams[n + 1]:
            return round(20 * n + 20 * (conc - trams[n]) / (trams[n + 1] - trams[n]))
    return round(100 + 20 * (conc - trams[-1]) / (trams[-1] - trams[-2]))


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    return 6371 * math.hypot((lo2 - lo1) * math.cos((la1 + la2) / 2), la2 - la1)


def get_json(url, params):
    req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def model(ara, dies_passats=0):
    return get_json(API, {"latitude": C.CASA[0], "longitude": C.CASA[1], "timezone": P.TZ, "domains": "cams_europe",
                          "hourly": ",".join(CONTAMINANTS), "past_days": dies_passats, "forecast_days": 1})


def mesures_xvpca(desde):
    """Las filas diarias de las estaciones cercanas desde la fecha dada
    (h01…h24: la hora que acaba a la 1, …, a las 24)."""
    noms = ",".join(f"'{n}'" for n in ESTACIONS)
    contaminants = ",".join(f"'{c}'" for c in NOM_XVPCA)
    return get_json(XVPCA, {"$where": f"data >= '{desde}T00:00:00.000' AND nom_estacio in ({noms}) "
                                      f"AND contaminant in ({contaminants})", "$limit": 5000})


def per_hora(files):
    """{(estació, contaminant, 'AAAA-MM-DDTHH:00'): µg/m³}; la hora, la del
    final del període (h04 → 04:00)."""
    res = {}
    for f in files:
        c = NOM_XVPCA.get(f.get("contaminant"))
        if not c:
            continue
        dia = dt.date.fromisoformat(f["data"][:10])
        for h in range(1, 25):
            v = f.get(f"h{h:02d}")
            if v in (None, ""):
                continue
            moment = dt.datetime.combine(dia, dt.time()) + dt.timedelta(hours=h)
            res[(f["nom_estacio"], c, moment.strftime("%Y-%m-%dT%H:00"))] = float(v)
    return res


def factors(model_hores, mesures):
    """Para cada contaminante, la suma de lo medido (media de las estaciones
    de cada hora) entre la del modelo, en las horas que tienen las dos cosas."""
    res = {}
    for c in CONTAMINANTS:
        mesurat, previst, n = 0.0, 0.0, 0
        for t, m in zip(model_hores["time"], model_hores.get(c) or []):
            vals = [v for (e, cc, tt), v in mesures.items() if cc == c and tt == t]
            if m is None or not vals:
                continue
            mesurat += sum(vals) / len(vals)
            previst += m
            n += 1
        estacions = {e for (e, cc, t) in mesures if cc == c}
        if n >= AIRE_HORES_MIN and previst > 0 and len(estacions) >= AIRE_ESTACIONS_MIN:
            res[c] = {"factor": round(mesurat / previst, 2), "hores": n}
    return res


def ultimes(mesures):
    """La última medida de cada estación: la hora más reciente con algún valor
    y los valores de esa hora."""
    res = []
    for nom, lloc in ESTACIONS.items():
        hores = sorted({t for (e, c, t) in mesures if e == nom})
        if not hores:
            continue
        t = hores[-1]
        valors = {c: v for (e, c, tt), v in mesures.items() if e == nom and tt == t}
        res.append({"estacio": nom, "km": round(km(C.CASA, lloc), 1), "hora": t, "valors": valors,
                    "index": max(index_de(c, v) for c, v in valors.items())})
    return sorted(res, key=lambda e: e["km"])


def correccio(ara):
    """Los factores y las últimas medidas, guardados un día en el NAS."""
    try:
        with open(CACHE, encoding="utf-8") as f:
            desat = json.load(f)
        if desat.get("dia") == ara.date().isoformat() and \
                ara - dt.datetime.fromisoformat(desat["hora"]) < dt.timedelta(hours=3):
            return desat
    except (OSError, ValueError, KeyError):
        pass
    desde = (ara - dt.timedelta(days=DIES_CORRECCIO + 1)).date().isoformat()
    mesures = per_hora(mesures_xvpca(desde))
    passat = model(ara, DIES_CORRECCIO)["hourly"]
    res = {"dia": ara.date().isoformat(), "hora": ara.isoformat(timespec="minutes"),
           "factors": factors(passat, mesures), "mesures": ultimes(mesures)}
    if os.path.isdir(os.path.dirname(CACHE)):
        with open(CACHE + ".tmp", "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False)
        os.replace(CACHE + ".tmp", CACHE)
    return res


def llegeix(d, ara, corr=None):
    """De la respuesta del modelo (hora a hora de hoy), lo de ahora, cada hora
    de lo que queda de hoy y el peor momento, corregidos si hay factores."""
    fs = {c: v["factor"] for c, v in ((corr or {}).get("factors") or {}).items()}
    h = d["hourly"]
    ara_h = ara.strftime("%Y-%m-%dT%H:00")
    hores = []
    for n, t in enumerate(h["time"]):
        if t[:10] != ara.date().isoformat() or t < ara_h:
            continue
        per = {c: index_de(c, h[c][n] * fs.get(c, 1)) for c in CONTAMINANTS if h.get(c) and h[c][n] is not None}
        if per:
            hores.append({"hora": t, "index": max(per.values()), "per": per})
    if not hores:
        return None
    ara_ = hores[0]
    pitjor = max(hores, key=lambda x: x["index"])
    return {"hora": ara_["hora"], "index": ara_["index"], "categoria": categoria(ara_["index"]),
            "contaminant": max(ara_["per"], key=ara_["per"].get), "contaminants": ara_["per"],
            "hores": [{"hora": x["hora"], "index": x["index"]} for x in hores],
            "pitjor": {"hora": pitjor["hora"], "index": pitjor["index"], "categoria": categoria(pitjor["index"])},
            "corregit": bool(fs), "factors": (corr or {}).get("factors") or {},
            "mesures": (corr or {}).get("mesures") or []}


def calcula(ara=None):
    ara = ara or dt.datetime.now().astimezone()
    try:
        corr = correccio(ara)
    except Exception:          # sin la red de la Generalitat, el modelo tal cual
        corr = None
    return llegeix(model(ara), ara, corr)


if __name__ == "__main__":
    print(json.dumps(calcula(), ensure_ascii=False, indent=1))
