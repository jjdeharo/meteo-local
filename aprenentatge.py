#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Aprendizaje de la página de casa con lo que pasó de verdad (ADR 0012).

Dos regresiones, sin IA, ajustadas con numpy:

- Lluvia: regresión logística. Da la probabilidad de que caigan 0,2 mm o
  más en una hora a partir de la lluvia de los tres modelos finos, la
  antelación, la hora y el día del año y, con datos propios, la fracción del
  ensemble y la lluvia que medía Montflorit al hacer la previsión.
- Temperatura: regresión lineal (ridge) del error del modelo en Montflorit
  según la propia temperatura, las nubes, el viento, la humedad, la hora y la
  antelación. La temperatura corregida es la del modelo menos ese error.

Mientras no hay bastantes datos propios, la lluvia usa el modelo ajustado con
el archivo de 2024-2026 (calibracio/pluja_casa.json) y la temperatura es la
del modelo, sin corregir. Cada día, a la hora de la verificación, el reloj del
NAS ejecuta «diari»: vuelve a ajustar con todo lo registrado, lo compara con
lo que se usa ahora en semanas que no ha visto y, si mejora, lo propone. Un
cambio de método se avisa por Telegram y se aplica al día siguiente, salvo que
exista el archivo «atura»; un nuevo ajuste del mismo método se aplica directamente.

Uso:
  python3 aprenentatge.py diari     ajusta, compara y propone o aplica
  python3 aprenentatge.py estat     qué se usa ahora y con qué resultados
"""
import csv
import datetime as dt
import glob
import json
import math
import os
import subprocess
import sys

import numpy as np

import config as C

AQUI = os.path.dirname(os.path.abspath(__file__))
ARXIU = os.path.join(AQUI, "calibracio", "pluja_casa.json")
REGISTRE = os.environ.get("REGISTRE_DIR", "/estat/registre")
DIR = os.environ.get("APRENENTATGE_DIR", "/estat/aprenentatge")
MODEL = os.path.join(DIR, "model.json")
PROPOSAT = os.path.join(DIR, "proposat.json")
ATURA = os.path.join(DIR, "atura")
HISTORIAL = os.path.join(DIR, "historial.csv")

# Cuándo hay bastantes datos propios y cuánto tiene que mejorar un método
# para sustituir al que se usa (en semanas que no ha visto).
MIN_HORES_PLUJA = 30        # horas con lluvia en Montflorit
MIN_DIES_TEMPERATURA = 14
MILLORA_MINIMA = 0.05       # 5 % menos de error
SETMANES_VALIDACIO = 4      # grupos de semanas para la validación cruzada
PERSISTENCIA_H = 4          # horas en que cuenta la lluvia medida al prever

RASGOS_ARXIU = ["constant", "arome_hd", "arome", "icon_eu", "antelacio",
                "hora_sin", "hora_cos", "dia_sin", "dia_cos"]
RASGOS_PROPIS = RASGOS_ARXIU + ["ensemble", "persistencia"]
RASGOS_TEMPERATURA = ["constant", "temperatura", "nuvols", "vent", "humitat",
                      "hora_sin", "hora_cos", "antelacio"]


# --- Rasgos ------------------------------------------------------------------------

def rasgos(d, noms):
    """Vector de rasgos de una hora. d lleva lo que se guarda en el registro:
    la lluvia de cada modelo (pluja_<modelo>), «fins» (hora local en que acaba
    el tramo), antelacio_h, prob_ens, temperature_2m… y pluja_1h_emes."""
    fin = dt.datetime.fromisoformat(d["fins"])
    h = 2 * math.pi * fin.hour / 24
    dia = 2 * math.pi * fin.timetuple().tm_yday / 365.25
    pluja = {m: d.get(f"pluja_{m}") for m in C.MODELOS_FINOS}
    valors = {
        "constant": 1.0,
        "arome_hd": pluja["meteofrance_arome_france_hd"],
        "arome": pluja["meteofrance_arome_france"],
        "icon_eu": pluja["icon_eu"],
        # El archivo solo tiene el corto plazo (0) y la previsión de un día
        # antes (1): la antelación va en días, hasta 1.
        "antelacio": min(max(d.get("antelacio_h", 0), 0) / 24, 1.0),
        "hora_sin": math.sin(h), "hora_cos": math.cos(h),
        "dia_sin": math.sin(dia), "dia_cos": math.cos(dia),
        "ensemble": d.get("prob_ens"),
        "persistencia": (math.log1p(d.get("pluja_1h_emes") or 0)
                         if d.get("antelacio_h", 99) <= PERSISTENCIA_H else 0.0),
        "temperatura": d.get("temperature_2m"),
        "nuvols": None if d.get("cloud_cover") is None else d["cloud_cover"] / 100,
        "vent": None if d.get("wind_speed_10m") is None else d["wind_speed_10m"] / 10,
        "humitat": None if d.get("relative_humidity_2m") is None else d["relative_humidity_2m"] / 100,
    }
    for m in ("arome_hd", "arome", "icon_eu"):
        if valors[m] is not None:
            valors[m] = math.log1p(max(valors[m], 0))
    x = [valors[n] for n in noms]
    return None if any(v is None for v in x) else x


# --- Regresiones ---------------------------------------------------------------------

def ajustar(x, y, l2=1.0, iteraciones=50):
    """Regresión logística por Newton-Raphson con regularización L2 (sin
    penalizar la constante)."""
    w = np.zeros(x.shape[1])
    pen = np.full(x.shape[1], l2)
    pen[0] = 0
    for _ in range(iteraciones):
        p = 1 / (1 + np.exp(-x @ w))
        g = x.T @ (p - y) + pen * w
        h = x.T @ (x * (p * (1 - p))[:, None]) + np.diag(pen)
        paso = np.linalg.solve(h, g)
        w -= paso
        if np.abs(paso).max() < 1e-8:
            break
    return w


def predecir(w, x):
    return 1 / (1 + np.exp(-x @ w))


def ajustar_ridge(x, y, l2=1.0):
    """Regresión lineal con regularización L2 (sin penalizar la constante)."""
    pen = np.full(x.shape[1], l2)
    pen[0] = 0
    return np.linalg.solve(x.T @ x + np.diag(pen), x.T @ y)


# --- Modelo en uso --------------------------------------------------------------------

def modelo_arxiu():
    with open(ARXIU, encoding="utf-8") as f:
        return json.load(f)


def carrega():
    """El modelo en uso: el aprendido en el NAS si lo hay; si no, el del
    archivo para la lluvia y la temperatura del modelo sin corregir."""
    try:
        with open(MODEL, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        pass
    try:
        return {"pluja": modelo_arxiu(), "temperatura": None}
    except (OSError, ValueError):
        return {"pluja": None, "temperatura": None}


def prob_pluja(model, d):
    m = (model or {}).get("pluja")
    x = rasgos(d, m["rasgos"]) if m else None
    return None if x is None else float(predecir(np.array(m["w"]), np.array(x)))


def temperatura(model, d):
    m = (model or {}).get("temperatura")
    x = rasgos(d, m["rasgos"]) if m else None
    return d.get("temperature_2m") if x is None else d["temperature_2m"] - float(np.array(m["w"]) @ np.array(x))


def resum_pagina(model):
    """Lo que dice la página sobre cómo se calcula."""
    p, t = (model or {}).get("pluja"), (model or {}).get("temperatura")
    return {"pluja": p and {"origen": p["origen"], "des_de": p["des_de"]},
            "temperatura": t and {"origen": t["origen"], "des_de": t["des_de"]}}


# --- Datos propios ----------------------------------------------------------------------

def mostres():
    """Una muestra por hora prevista y pasada de cada previsión registrada, con
    lo que midió Montflorit en esa hora."""
    obs = {}
    ruta = os.path.join(REGISTRE, "montflorit.csv")
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            obs = {r["fins"]: r for r in csv.DictReader(f)}
    res = []
    for arxiu in sorted(glob.glob(os.path.join(REGISTRE, "casa-*.jsonl"))):
        with open(arxiu, encoding="utf-8") as f:
            for linea in map(json.loads, f):
                ara = linea.get("ara") or {}
                for h in linea["hores"]:
                    o = obs.get(h["fins"])
                    if not o:
                        continue
                    res.append({**h, "emes": linea["emes"], "pluja_1h_emes": ara.get("pluja_1h"),
                                "obs_pluja": float(o["pluja_mm"]),
                                "obs_temp": float(o["temperatura"]) if o["temperatura"] else None})
    return res


def grupo_semana(m):
    d = dt.date.fromisoformat(m["emes"][:10])
    return (d.isocalendar()[0] * 53 + d.isocalendar()[1]) % SETMANES_VALIDACIO


def valida_pluja(ms, arxiu):
    """Error (Brier) en validación cruzada por semanas del modelo propio y del
    archivo, con las mismas muestras."""
    ms = [m for m in ms if rasgos(m, RASGOS_PROPIS) is not None]
    if not ms:
        return None
    x = np.array([rasgos(m, RASGOS_PROPIS) for m in ms])
    y = np.array([m["obs_pluja"] >= C.UMBRAL_MM for m in ms], dtype=float)
    xa = np.array([rasgos(m, arxiu["rasgos"]) for m in ms])
    grupo = np.array([grupo_semana(m) for m in ms])
    if len(set(grupo)) < 2:         # sin semanas aparte, no se puede comprobar
        return None
    p = np.zeros(len(y))
    for g in set(grupo):
        ent = grupo != g
        if y[ent].sum() == 0:
            p[~ent] = y[ent].mean()
        else:
            p[~ent] = predecir(ajustar(x[ent], y[ent]), x[~ent])
    return {"mostres": len(y), "hores_pluja": int(y.sum()),
            "error": float(np.mean((p - y) ** 2)),
            "error_abans": float(np.mean((predecir(np.array(arxiu["w"]), xa) - y) ** 2)),
            "w": ajustar(x, y).tolist() if y.sum() else None}


def valida_temperatura(ms):
    """Error medio absoluto en validación cruzada por semanas: corregida y sin
    corregir."""
    ms = [m for m in ms if m["obs_temp"] is not None and rasgos(m, RASGOS_TEMPERATURA) is not None]
    if not ms:
        return None
    x = np.array([rasgos(m, RASGOS_TEMPERATURA) for m in ms])
    modelo = np.array([m["temperature_2m"] for m in ms])
    error = modelo - np.array([m["obs_temp"] for m in ms])
    grupo = np.array([grupo_semana(m) for m in ms])
    if len(set(grupo)) < 2:
        return None
    pred = np.zeros(len(error))
    for g in set(grupo):
        ent = grupo != g
        pred[~ent] = x[~ent] @ ajustar_ridge(x[ent], error[ent])
    dies = len({m["emes"][:10] for m in ms})
    return {"mostres": len(ms), "dies": dies,
            "error": float(np.mean(np.abs(error - pred))),
            "error_abans": float(np.mean(np.abs(error))),
            "w": ajustar_ridge(x, error).tolist()}


# --- Decisión diaria -------------------------------------------------------------------

def millora(v):
    return v["error"] < (1 - MILLORA_MINIMA) * v["error_abans"]


def candidat(ms, arxiu, avui):
    """El modelo que tocaría usar con los datos de hoy, y los números."""
    vp, vt = valida_pluja(ms, arxiu), valida_temperatura(ms)
    model = {"pluja": arxiu, "temperatura": None}
    if vp and vp["hores_pluja"] >= MIN_HORES_PLUJA and vp["w"] and millora(vp):
        model["pluja"] = {"origen": "montflorit", "des_de": ms[0]["emes"][:10], "fins": avui,
                          "rasgos": RASGOS_PROPIS, "w": vp["w"], "error": vp["error"],
                          "error_abans": vp["error_abans"], "mostres": vp["mostres"]}
    if vt and vt["dies"] >= MIN_DIES_TEMPERATURA and millora(vt):
        model["temperatura"] = {"origen": "montflorit", "des_de": ms[0]["emes"][:10], "fins": avui,
                                "rasgos": RASGOS_TEMPERATURA, "w": vt["w"], "error": vt["error"],
                                "error_abans": vt["error_abans"], "mostres": vt["mostres"]}
    return model, vp, vt


def metode(model):
    p, t = model.get("pluja"), model.get("temperatura")
    return ((p or {}).get("origen"), (t or {}).get("origen"))


def explica(abans, nou, vp, vt):
    """Mensaje de Telegram: qué cambia y con qué números."""
    linies = ["Temps a casa: canvi de mètode d'aprenentatge, s'aplicarà demà."]
    if metode(abans)[0] != metode(nou)[0]:
        if nou["pluja"]["origen"] == "montflorit":
            linies.append(f"Pluja: passa a aprendre de Montflorit ({vp['hores_pluja']} hores amb pluja). "
                          f"Error {vp['error']:.4f} en setmanes no vistes, abans {vp['error_abans']:.4f}.")
        else:
            linies.append("Pluja: torna al model de l'arxiu; el de Montflorit ja no millora.")
    if metode(abans)[1] != metode(nou)[1]:
        if nou["temperatura"]:
            linies.append(f"Temperatura: es corregeix amb Montflorit ({vt['dies']} dies). "
                          f"Error mitjà {vt['error']:.1f} °C, sense corregir {vt['error_abans']:.1f} °C.")
        else:
            linies.append("Temperatura: deixa de corregir-se; la correcció ja no millora.")
    linies.append("Per aturar-ho, demana-ho a Claude abans de demà.")
    return "\n".join(linies)


def guarda(ruta, dades):
    with open(ruta + ".tmp", "w", encoding="utf-8") as f:
        json.dump(dades, f, ensure_ascii=False, indent=1)
    os.replace(ruta + ".tmp", ruta)


def apunta_historial(avui, model, vp, vt):
    nou = not os.path.exists(HISTORIAL)
    with open(HISTORIAL, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nou:
            w.writerow(["dia", "pluja", "temperatura", "mostres_pluja", "hores_pluja", "error_pluja",
                        "error_pluja_arxiu", "dies_temperatura", "error_temp", "error_temp_model"])
        w.writerow([avui, *metode(model),
                    vp and vp["mostres"], vp and vp["hores_pluja"], vp and round(vp["error"], 5),
                    vp and round(vp["error_abans"], 5), vt and vt["dies"],
                    vt and round(vt["error"], 2), vt and round(vt["error_abans"], 2)])


def diari(avui=None, avisa=True):
    avui = avui or dt.date.today().isoformat()
    os.makedirs(DIR, exist_ok=True)
    arxiu = modelo_arxiu()
    en_us = carrega()
    # 1. Una propuesta de ayer que nadie ha parado: se aplica.
    if os.path.exists(PROPOSAT):
        with open(PROPOSAT, encoding="utf-8") as f:
            proposat = json.load(f)
        if os.path.exists(ATURA):
            print("Proposta aturada: no s'aplica.")
            os.remove(PROPOSAT)
        elif proposat["dia"] < avui:
            en_us = proposat["model"]
            guarda(MODEL, en_us)
            os.remove(PROPOSAT)
            print("Aplicada la proposta d'ahir:", metode(en_us))
    # 2. Lo que tocaría hoy.
    nou, vp, vt = candidat(mostres(), arxiu, avui)
    apunta_historial(avui, nou, vp, vt)
    if metode(nou) == metode(en_us):
        # Mismo método, más datos: se pone al día sin avisar.
        if nou != en_us and not os.path.exists(ATURA):
            guarda(MODEL, nou)
        print("Mateix mètode:", metode(nou))
        return
    if os.path.exists(ATURA):
        print("Canvi de mètode aturat (existeix «atura»).")
        return
    guarda(PROPOSAT, {"dia": avui, "model": nou})
    text = explica(en_us, nou, vp, vt)
    print(text)
    if avisa:
        subprocess.run(["avisar-juanjo", "--asunto", "meteo-local", text], check=False)


def estat():
    model = carrega()
    print(json.dumps(resum_pagina(model), ensure_ascii=False))
    if os.path.exists(HISTORIAL):
        with open(HISTORIAL, encoding="utf-8") as f:
            print("".join(f.readlines()[-5:]), end="")


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else ""
    if orden == "diari":
        diari()
    elif orden == "estat":
        estat()
    else:
        print(__doc__)
