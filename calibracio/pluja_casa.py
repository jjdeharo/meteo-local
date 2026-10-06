#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Modelo de lluvia de la página de casa ajustado con el archivo (ADR 0012 y 0021).

Regresión logística (aprenentatge.py) con las previsiones archivadas de
Open-Meteo en casa (corto plazo y 24 h antes) y la lluvia medida en Sabadell y
Sant Cugat, cada estación como una muestra.

Antes de ajustar con todo, se comprueba con **todo el archivo** en semanas
que el modelo no ha visto (validación cruzada por semanas, como hace
aprenentatge.py): el error y, sobre todo, la fiabilidad, es decir, si cuando
da un 10 % llueve el 10 % de las veces, en cada antelación. Se compara con la
frecuencia habitual y con la fórmula anterior (solo la cantidad de lluvia de
cada modelo), que se quedaba corta entre el 5 y el 50 %.

Escribe calibracio/pluja_casa.json. Necesita los datos de descarrega.py.
Uso: python3 calibracio/pluja_casa.py
"""
import datetime as dt
import json
import os
import sys
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aprenentatge as A  # noqa: E402
import config as C  # noqa: E402
from calibracio.analitza import leer_obs, leer_prev  # noqa: E402

LOCAL = ZoneInfo("Europe/Madrid")
UTC = dt.timezone.utc
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pluja_casa.json")
# La fórmula anterior, para comparar: sin «el modelo da lluvia», sin cuántos
# coinciden y sin su relación con la antelación.
RASGOS_ABANS = ["constant", "arome_hd", "arome", "icon_eu", "antelacio",
                "hora_sin", "hora_cos", "dia_sin", "dia_cos"]
TRAMS = ((0, .05), (.05, .1), (.1, .2), (.2, .3), (.3, .5), (.5, .7), (.7, 1.01))


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


def creuada(x, y, grup):
    """Probabilidad de cada muestra dada por un modelo ajustado sin su grupo
    de semanas."""
    p = np.zeros(len(y))
    for g in set(grup):
        ent = grup != g
        p[~ent] = A.predecir(A.ajustar(x[ent], y[ent]), x[~ent])
    return p


def fiabilitat(p, y):
    """Por tramos de probabilidad: cuántas horas, la media dada, lo que llovió
    y qué parte de toda la lluvia cayó en el tramo."""
    res = []
    for a, b in TRAMS:
        s = (p >= a) & (p < b)
        if s.sum():
            res.append({"de": a, "a": min(b, 1), "hores": int(s.sum()),
                        "donada": round(float(p[s].mean()), 3),
                        "va_ploure": round(float(y[s].mean()), 3),
                        "part_pluja": round(float(y[s].sum() / y.sum()), 3)})
    return res


def main():
    ms = muestras()
    t = np.array([m[0] for m in ms])
    horas = np.array([m[1] for m in ms])
    x = np.array([m[2] for m in ms])
    y = np.array([m[3] for m in ms])
    columnes = [A.RASGOS_ARXIU.index(n) for n in RASGOS_ABANS]
    grup = np.array([(ti.isocalendar()[0] * 53 + ti.isocalendar()[1]) % A.SETMANES_VALIDACIO for ti in t])
    p_nou, p_abans = creuada(x, y, grup), creuada(x[:, columnes], y, grup)

    def brier(p, s):
        return round(float(np.mean((p[s] - y[s]) ** 2)), 5)

    validacio = {"metode": f"validació creuada en {A.SETMANES_VALIDACIO} grups de setmanes, tot l'arxiu"}
    for nom, h in (("curt_termini", 0), ("un_dia_abans", 24)):
        s = horas == h
        validacio[nom] = {
            "mostres": int(s.sum()), "hores_pluja": int(y[s].sum()),
            "error_frequencia": brier(np.full(len(y), y[s].mean()), s),
            "error_abans": brier(p_abans, s), "error": brier(p_nou, s),
            "fiabilitat": fiabilitat(p_nou[s], y[s]),
            "fiabilitat_abans": fiabilitat(p_abans[s], y[s])}
    resultado = {
        "origen": "arxiu", "des_de": t.min().astimezone(LOCAL).date().isoformat(),
        "fins": t.max().astimezone(LOCAL).date().isoformat(),
        "rasgos": A.RASGOS_ARXIU, "w": [round(v, 5) for v in A.ajustar(x, y).tolist()],
        "mostres": int(len(y)), "hores_pluja": int(y.sum()),
        "validacio": validacio,
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1)
    for nom in ("curt_termini", "un_dia_abans"):
        v = validacio[nom]
        print(f"{nom}: {v['mostres']} mostres, {v['hores_pluja']} amb pluja. Error: freqüència "
              f"{v['error_frequencia']}, abans {v['error_abans']}, ara {v['error']}")
        for clau in ("fiabilitat_abans", "fiabilitat"):
            print(" ", clau, " ".join(f"{100 * f['donada']:.0f}→{100 * f['va_ploure']:.0f} ({f['hores']})"
                                      for f in v[clau]))
    print("Coeficientes:", dict(zip(A.RASGOS_ARXIU, resultado["w"])))


if __name__ == "__main__":
    main()
