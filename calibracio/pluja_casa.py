#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Modelo de lluvia de la página de casa ajustado con el archivo (ADR 0012).

Regresión logística (aprenentatge.py) con las previsiones archivadas de
Open-Meteo en casa (corto plazo y 24 h antes) y la lluvia medida en Sabadell y
Sant Cugat, cada estación como una muestra. Antes de ajustar con todo, se
comprueba con los últimos meses, que no se usan para ajustar, frente a la
fracción del ensemble ICON-EU-EPS, que era lo que daba la página (su archivo
solo llega a unos tres meses atrás).

Escribe calibracio/pluja_casa.json. Necesita los datos de descarrega.py.
Uso: python3 calibracio/pluja_casa.py
"""
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aprenentatge as A  # noqa: E402
import config as C  # noqa: E402
from calibracio.analitza import leer_obs, leer_prev  # noqa: E402

LOCAL = ZoneInfo("Europe/Madrid")
UTC = dt.timezone.utc
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pluja_casa.json")
DIAS_PRUEBA = 90


def ensemble(inicio, fin):
    q = urllib.parse.urlencode({"latitude": C.CASA[0], "longitude": C.CASA[1],
                                "hourly": "precipitation", "models": C.ENSEMBLE, "timezone": "UTC",
                                "start_date": inicio.isoformat(), "end_date": fin.isoformat()})
    with urllib.request.urlopen(f"https://ensemble-api.open-meteo.com/v1/ensemble?{q}", timeout=120) as r:
        h = json.loads(r.read())["hourly"]
    miembros = [k for k in h if k.startswith("precipitation")]
    return {dt.datetime.fromisoformat(t).replace(tzinfo=UTC):
            sum((h[k][i] or 0) >= C.UMBRAL_MM for k in miembros) / len(miembros)
            for i, t in enumerate(h["time"])}


def muestras():
    obs, prev = leer_obs(), leer_prev()
    res = []
    for t, puntos in prev.items():
        p = puntos.get("casa")
        if not p:
            continue
        fins = t.astimezone(LOCAL).strftime("%Y-%m-%dT%H:%M")
        for serie in obs.values():
            a, b = serie.get(t - dt.timedelta(minutes=60)), serie.get(t - dt.timedelta(minutes=30))
            if a is None or b is None:
                continue
            for plazo, horas in (("", 0), ("_previous_day1", 24)):
                d = {"fins": fins, "antelacio_h": horas}
                d.update({f"pluja_{m}": p.get(f"precipitation{plazo}_{m}") for m in C.MODELOS_FINOS})
                x = A.rasgos(d, A.RASGOS_ARXIU)
                if x is not None:
                    res.append((t, horas, x, float(a + b >= C.UMBRAL_MM)))
    return res


def main():
    ms = muestras()
    final = max(t for t, *_ in ms)
    corte = (final - dt.timedelta(days=DIAS_PRUEBA)).replace(hour=0)
    t = np.array([m[0] for m in ms])
    horas = np.array([m[1] for m in ms])
    x = np.array([m[2] for m in ms])
    y = np.array([m[3] for m in ms])
    ent = t < corte
    w = A.ajustar(x[ent], y[ent])
    ens = ensemble(corte.date(), final.date())
    prueba = (~ent) & (horas == 0) & np.array([ti in ens for ti in t])
    yp = y[prueba]
    p_log = A.predecir(w, x[prueba])
    p_ens = np.array([ens[ti] for ti in t[prueba]])

    def brier(p):
        return round(float(np.mean((p - yp) ** 2)), 5)

    fiabilidad = []
    for a, b in ((0, .05), (.05, .1), (.1, .2), (.2, .3), (.3, .5), (.5, 1.01)):
        s = (p_log >= a) & (p_log < b)
        if s.sum():
            fiabilidad.append({"de": a, "a": min(b, 1), "hores": int(s.sum()),
                               "donada": round(float(p_log[s].mean()), 3),
                               "va_ploure": round(float(yp[s].mean()), 3)})
    w_final = A.ajustar(x, y)
    resultado = {
        "origen": "arxiu", "des_de": t.min().astimezone(LOCAL).date().isoformat(),
        "fins": final.astimezone(LOCAL).date().isoformat(),
        "rasgos": A.RASGOS_ARXIU, "w": [round(v, 5) for v in w_final.tolist()],
        "mostres": int(len(y)), "hores_pluja": int(y.sum()),
        "validacio": {
            "periode": [corte.date().isoformat(), final.date().isoformat()],
            "mostres": int(prueba.sum()), "hores_pluja": int(yp.sum()),
            "error_frequencia": brier(np.full(len(yp), y[ent].mean())),
            "error_ensemble": brier(p_ens), "error_logistica": brier(p_log),
            "fiabilitat": fiabilidad},
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1)
    print(json.dumps(resultado["validacio"], ensure_ascii=False, indent=1))
    print("Coeficientes:", dict(zip(A.RASGOS_ARXIU, resultado["w"])))


if __name__ == "__main__":
    main()
