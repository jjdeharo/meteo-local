#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regla de lluvia de la moto y la bici en «Si surts», comprobada con el archivo
(ADR 0047).

Compara, hora a hora y con las previsiones archivadas en casa (corto plazo y
24 h antes), dos reglas:

- «abans»: manda la probabilidad o la lluvia del modelo más lluvioso, lo que dé
  más (50 % o 1 mm, «no»; 20 % o 0,2 mm, «compte»);
- «ara»: solo la probabilidad (50 %, «no»; 20 %, «compte»).

La probabilidad es la del modelo del archivo (aprenentatge.py) ajustado sin la
semana que se comprueba (validación cruzada por semanas), así que no ha visto
la hora que juzga. La verdad es la lluvia de Sabadell y Sant Cugat (cada
estación, una muestra). También juzga el viaje de cada día a las 10 y a las
17 h, con un solo veredicto para la ida y la vuelta.

Necesita los datos de descarrega.py. Uso: python3 calibracio/regla_moto.py
"""
import datetime as dt
import os
import sys
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aprenentatge as A  # noqa: E402
import config as C  # noqa: E402
from calibracio.analitza import leer_obs, leer_prev  # noqa: E402
from calibracio.pluja_casa import creuada  # noqa: E402

LOCAL = ZoneInfo("Europe/Madrid")
PROB_RISC, PROB_PLUJA = 0.2, 0.5        # web/sortir.js
MM_RISC, MM_PLUJA = 0.2, 1.0            # los umbrales que se quitan
VIATGE = (11, 18)                        # tramos de 10 a 11 y de 17 a 18 («fins»)
NIVELLS = ("be", "compte", "no")


def muestras():
    obs, prev = leer_obs(), leer_prev()
    res = []
    for t, puntos in prev.items():
        p = puntos.get("casa")
        if not p:
            continue
        fins = t.astimezone(LOCAL).strftime("%Y-%m-%dT%H:%M")
        for est, serie in obs.items():
            a, b = serie.get(t - dt.timedelta(minutes=60)), serie.get(t - dt.timedelta(minutes=30))
            if a is None or b is None:
                continue
            for plazo, horas in (("", 0), ("_previous_day1", 24)):
                d = {"fins": fins, "antelacio_h": horas}
                d.update({f"pluja_{m}": p.get(f"precipitation{plazo}_{m}") for m in C.MODELOS_FINOS})
                x = A.rasgos(d, A.RASGOS_ARXIU)
                if x is None:
                    continue
                mm = max(d[f"pluja_{m}"] for m in C.MODELOS_FINOS)
                res.append((t, horas, est, x, mm, float(a + b >= C.UMBRAL_MM)))
    return res


def nivell(p, mm, amb_mm):
    if p >= PROB_PLUJA or (amb_mm and mm >= MM_PLUJA):
        return 2
    if p >= PROB_RISC or (amb_mm and mm >= MM_RISC):
        return 1
    return 0


def taula(niv, y):
    """Cuántas horas secas y con lluvia caen en cada nivel."""
    return {"seques": [int(((niv == k) & (y == 0)).sum()) for k in range(3)],
            "pluja": [int(((niv == k) & (y == 1)).sum()) for k in range(3)]}


def mostra(nom, t):
    s, p = t["seques"], t["pluja"]
    print(f"  {nom:6} sec: bé {s[0]:6}  compte {s[1]:5}  no {s[2]:4} | "
          f"pluja: bé {p[0]:4}  compte {p[1]:4}  no {p[2]:4}")


def main():
    ms = muestras()
    t = np.array([m[0] for m in ms])
    horas = np.array([m[1] for m in ms])
    est = np.array([m[2] for m in ms])
    x = np.array([m[3] for m in ms])
    mm = np.array([m[4] for m in ms])
    y = np.array([m[5] for m in ms])
    grup = np.array([(ti.isocalendar()[0] * 53 + ti.isocalendar()[1]) % A.SETMANES_VALIDACIO for ti in t])
    p = creuada(x, y, grup)
    abans = np.array([nivell(pi, mi, True) for pi, mi in zip(p, mm)])
    ara = np.array([nivell(pi, mi, False) for pi, mi in zip(p, mm)])
    print(f"Arxiu: {t.min().astimezone(LOCAL).date()} a {t.max().astimezone(LOCAL).date()}")
    for nom, h in (("Curt termini", 0), ("Un dia abans", 24)):
        s = horas == h
        print(f"{nom}: {s.sum()} hores-estació, {int(y[s].sum())} amb pluja")
        mostra("abans", taula(abans[s], y[s]))
        mostra("ara", taula(ara[s], y[s]))
        # El viaje de las 10 y las 17: un veredicto, el peor de las dos horas;
        # llueve si llueve en alguna de las dos en alguna estación.
        dies = {}
        for i in np.where(s)[0]:
            loc = t[i].astimezone(LOCAL)
            if loc.hour in VIATGE:
                d = dies.setdefault(loc.date(), {"h": set(), "abans": 0, "ara": 0, "plou": 0})
                d["h"].add(loc.hour)
                d["abans"] = max(d["abans"], abans[i])
                d["ara"] = max(d["ara"], ara[i])
                d["plou"] = max(d["plou"], y[i])
        dies = [d for d in dies.values() if len(d["h"]) == 2]
        yd = np.array([d["plou"] for d in dies])
        print(f"  Viatge 10-17 h: {len(dies)} dies, {int(yd.sum())} amb pluja")
        mostra("abans", taula(np.array([d["abans"] for d in dies]), yd))
        mostra("ara", taula(np.array([d["ara"] for d in dies]), yd))


if __name__ == "__main__":
    main()
