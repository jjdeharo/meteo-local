#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lo que aporta la estación de casa a la previsión, con su historial (ADR 0017).

Ecowitt guarda un año de lecturas cada 30 minutos y 90 días cada 5. Con eso y
las previsiones archivadas de Open-Meteo para casa:

- Temperatura: ajusta la corrección del modelo (regresión ridge,
  aprenentatge.py) con la temperatura medida en casa y la comprueba en semanas
  que no ha visto. Escribe calibracio/temperatura_casa.json, que la página usa
  desde el primer día.
- Lluvia: comprueba si las señales de casa al prever (la lluvia que cae y la
  sequedad del aire) mejoran el modelo del archivo (pluja_casa.json), con la
  lluvia de casa como verdad mientras el pluviómetro iba bien. Solo informa:
  el modelo de lluvia no cambia aquí.

Las descargas van a calibracio/dades/, que no se sube al repositorio.
Uso: python3 calibracio/estacio_casa.py [--descarrega]
"""
import datetime as dt
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aprenentatge as A  # noqa: E402
import config as C  # noqa: E402
import ecowitt as E  # noqa: E402
from calibracio.analitza import leer_prev  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(AQUI, "dades")
SALIDA = os.path.join(AQUI, "temperatura_casa.json")
ECOWITT_30 = os.path.join(DIR, "casa_30min.csv")
ECOWITT_5 = os.path.join(DIR, "casa_5min.csv")
PREV_TEMP = os.path.join(DIR, "prev_temp_casa.json")
LOCAL = ZoneInfo("Europe/Madrid")
UTC = dt.timezone.utc
VARIABLES = ["temperature_2m", "relative_humidity_2m", "cloud_cover", "shortwave_radiation"]
# Antelaciones con que se comprueba: las primeras horas salen de la pasada
# más reciente del modelo («day0»); 24 h, de la del día antes.
ANTELACIONES = ((1, ""), (2, ""), (3, ""), (6, ""), (24, "_previous_day1"))


def descarga():
    os.makedirs(DIR, exist_ok=True)
    ahora = dt.datetime.now().astimezone()
    corte = (ahora - dt.timedelta(days=E.TRAMOS["5min"][1] - 2)).replace(hour=0, minute=0, second=0, microsecond=0)
    inicio = (ahora - dt.timedelta(days=E.TRAMOS["30min"][1] - 2)).replace(hour=0, minute=0, second=0, microsecond=0)
    E.guarda_csv(E.historial(inicio, corte, "30min"), ECOWITT_30)
    E.guarda_csv(E.historial(corte, ahora, "5min"), ECOWITT_5)
    hv = ",".join(VARIABLES + [v + "_previous_day1" for v in VARIABLES])
    q = urllib.parse.urlencode({"latitude": C.CASA[0], "longitude": C.CASA[1], "hourly": hv,
                                "models": "meteofrance_seamless", "timezone": "UTC",
                                "start_date": inicio.date().isoformat(), "end_date": ahora.date().isoformat()})
    with urllib.request.urlopen(f"https://previous-runs-api.open-meteo.com/v1/forecast?{q}", timeout=300) as r:
        with open(PREV_TEMP, "w", encoding="utf-8") as f:
            json.dump(json.loads(r.read())["hourly"], f)


def estacion():
    """Lluvia por hora y lecturas en punto, en UTC."""
    filas = sorted(E.lee_csv(ECOWITT_30) + E.lee_csv(ECOWITT_5), key=lambda f: f["t"])
    lluvia, lect = {}, {}
    for a, b in zip(filas, filas[1:]):
        t = b["t"].astimezone(UTC)
        fin = t.replace(minute=0, second=0) + (dt.timedelta(hours=1) if t.minute else dt.timedelta())
        if None not in (a["pluja_avui"], b["pluja_avui"]) and b["t"] - a["t"] <= dt.timedelta(minutes=35):
            salto = b["pluja_avui"] - a["pluja_avui"]
            lluvia[fin] = lluvia.get(fin, 0) + (b["pluja_avui"] if salto < 0 else salto)
    for f in filas:
        t = f["t"].astimezone(UTC)
        if t.minute == 0 and f["temperatura"] is not None:
            lect[t] = f
    return lluvia, lect


def grupo(t):
    iso = t.astimezone(LOCAL).isocalendar()
    return (iso[0] * 53 + iso[1]) % A.SETMANES_VALIDACIO


def muestras_temperatura(lect, prev):
    idx = {dt.datetime.fromisoformat(t).replace(tzinfo=UTC): i for i, t in enumerate(prev["time"])}
    res = []
    for t, i in idx.items():
        f = lect.get(t)
        if not f:
            continue
        for horas, plazo in ANTELACIONES:
            emes = t - dt.timedelta(hours=horas)
            fe, ie = lect.get(emes), idx.get(emes)
            d = {"fins": t.astimezone(LOCAL).strftime("%Y-%m-%dT%H:%M"), "antelacio_h": horas,
                 **{v: prev[f"{v}{plazo}"][i] for v in VARIABLES}}
            if fe and ie is not None and prev["temperature_2m"][ie] is not None:
                d["error_temp_ara"] = prev["temperature_2m"][ie] - fe["temperatura"]
            if d["temperature_2m"] is None:
                continue
            res.append({**d, "t": t, "obs": f["temperatura"]})
    return res


def ajusta_temperatura(ms):
    """Pesos con y sin las señales de la estación al prever, y su
    comprobación en semanas no vistas (error medio absoluto, °C)."""
    resultado = {}
    for clave, noms in (("", A.RASGOS_TEMPERATURA), ("_sense_estacio", A.RASGOS_TEMPERATURA_SENSE_ESTACIO)):
        sel = [m for m in ms if A.rasgos(m, noms) is not None]
        x = np.array([A.rasgos(m, noms) for m in sel])
        err = np.array([m["temperature_2m"] - m["obs"] for m in sel])
        g = np.array([grupo(m["t"]) for m in sel])
        h = np.array([m["antelacio_h"] for m in sel])
        pred = np.zeros(len(err))
        for k in set(g):
            ent = g != k
            pred[~ent] = x[~ent] @ A.ajustar_ridge(x[ent], err[ent])
        resultado[f"rasgos{clave}"] = noms
        resultado[f"w{clave}"] = [round(v, 5) for v in A.ajustar_ridge(x, err).tolist()]
        resultado[f"validacio{clave}"] = {
            "mostres": int(len(err)), "dies": len({m["t"].date() for m in sel}),
            "biaix_model": round(float(err.mean()), 2),
            "error_model": round(float(np.abs(err).mean()), 3),
            "error_corregit": round(float(np.abs(err - pred).mean()), 3),
            "per_antelacio": {str(a): {"model": round(float(np.abs(err[h == a]).mean()), 2),
                                       "corregit": round(float(np.abs(err - pred)[h == a].mean()), 2)}
                              for a, _ in ANTELACIONES}}
    return resultado


def comprueba_lluvia(lluvia, lect):
    """¿Mejoran las señales de casa el modelo del archivo? Validación cruzada
    por semanas de un ajuste apilado: el logit del archivo más las señales."""
    arxiu = A.modelo_arxiu()
    fiable = dt.datetime.fromisoformat(C.PLUVIOMETRE_CASA_FIABLE_FINS).replace(tzinfo=LOCAL) + dt.timedelta(days=1)
    filas = []
    for t, p in leer_prev().items():
        p = p.get("casa")
        if not p or t not in lluvia or t.astimezone(LOCAL) >= fiable:
            continue
        for horas, plazo in ((1, ""), (2, ""), (3, ""), (4, ""), (24, "_previous_day1")):
            emes = t - dt.timedelta(hours=horas)
            fe = lect.get(emes)
            d = {"fins": t.astimezone(LOCAL).strftime("%Y-%m-%dT%H:%M"), "antelacio_h": horas,
                 **{f"pluja_{m}": p.get(f"precipitation{plazo}_{m}") for m in C.MODELOS_FINOS}}
            if fe and fe["rosada"] is not None and lluvia.get(emes) is not None:
                d["pluja_1h_emes"] = lluvia[emes]
                d["deficit_rosada_ara"] = fe["temperatura"] - fe["rosada"]
            xa = A.rasgos(d, arxiu["rasgos"])
            xs = A.rasgos(d, ["persistencia", "sequedat"])
            if xa is not None and xs is not None:
                filas.append((t, horas, float(np.array(arxiu["w"]) @ np.array(xa)), xs,
                              float(lluvia[t] >= C.UMBRAL_MM)))
    t = [f[0] for f in filas]
    h = np.array([f[1] for f in filas])
    y = np.array([f[4] for f in filas])
    g = np.array([grupo(x) for x in t])
    base = np.column_stack([np.ones(len(y)), [f[2] for f in filas]])
    con = np.column_stack([base, [f[3] for f in filas]])

    def cv(x):
        p = np.zeros(len(y))
        for k in set(g):
            ent = g != k
            p[~ent] = A.predecir(A.ajustar(x[ent], y[ent]), x[~ent])
        return p

    p_arxiu = 1 / (1 + np.exp(-base[:, 1]))
    res = {"periode": [min(t).astimezone(LOCAL).date().isoformat(), C.PLUVIOMETRE_CASA_FIABLE_FINS],
           "mostres": int(len(y)), "hores_pluja": int(len({x for x, *_, yy in filas if yy}))}
    for nombre, p in (("arxiu", p_arxiu), ("arxiu_i_casa", cv(con))):
        res[f"error_{nombre}"] = {str(a): round(float(np.mean((p[h == a] - y[h == a]) ** 2)), 5)
                                  for a in (1, 2, 3, 4, 24)}
        res[f"error_{nombre}"]["total"] = round(float(np.mean((p - y) ** 2)), 5)
    return res


def main():
    if "--descarrega" in sys.argv or not os.path.exists(ECOWITT_30):
        descarga()
    lluvia, lect = estacion()
    with open(PREV_TEMP, encoding="utf-8") as f:
        prev = json.load(f)
    ms = muestras_temperatura(lect, prev)
    resultado = {"origen": "arxiu",
                 "des_de": min(m["t"] for m in ms).astimezone(LOCAL).date().isoformat(),
                 "fins": max(m["t"] for m in ms).astimezone(LOCAL).date().isoformat(),
                 **ajusta_temperatura(ms), "pluja": comprueba_lluvia(lluvia, lect)}
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in resultado.items() if k.startswith("validacio") or k == "pluja"},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
