#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Aprendizaje de la página de casa con lo que pasó de verdad (ADR 0012).

Dos regresiones, sin IA, ajustadas con numpy:

- Lluvia: regresión logística. Da la probabilidad de que caigan 0,2 mm o
  más en una hora a partir de la lluvia de los tres modelos finos (cuánta, si
  cada uno da alguna y cuántos coinciden), la antelación, la hora y el día
  del año (ADR 0021) y, con datos propios, la fracción del ensemble y la
  lluvia que medía la estación de casa al hacer la previsión.
- Temperatura: regresión lineal (ridge) del error del modelo en la estación
  de casa según la propia temperatura, las nubes, la humedad, la radiación,
  la hora, el día del año, la antelación y el error que tenía el modelo al
  prever (ADR 0017). La temperatura corregida es la del modelo menos ese error.

Mientras no hay bastantes datos propios, la lluvia usa el modelo ajustado con
el archivo de 2024-2026 (calibracio/pluja_casa.json) y la temperatura, la
corrección ajustada con el último año de la estación de casa
(calibracio/temperatura_casa.json). Cada día, a la hora de la verificación, el reloj del
NAS ejecuta «diari»: vuelve a ajustar con todo lo registrado, lo compara con
lo que se usa ahora en semanas que no ha visto y, si mejora, lo propone. Un
cambio de método se avisa por Telegram y se aplica al día siguiente, salvo que
exista el archivo «atura»; un nuevo ajuste del mismo método se aplica directamente.

Uso:
  python3 aprenentatge.py diari     ajusta, compara y propone o aplica
  python3 aprenentatge.py estat     qué se usa ahora y con qué resultados
  python3 aprenentatge.py moto      cómo va la regla de lluvia de la moto de «Si surts»
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
ARXIU_TEMPERATURA = os.path.join(AQUI, "calibracio", "temperatura_casa.json")
REGISTRE = os.environ.get("REGISTRE_DIR", "/estat/registre")
DIR = os.environ.get("APRENENTATGE_DIR", "/estat/aprenentatge")
MODEL = os.path.join(DIR, "model.json")
PROPOSAT = os.path.join(DIR, "proposat.json")
ATURA = os.path.join(DIR, "atura")
HISTORIAL = os.path.join(DIR, "historial.csv")

# Cuándo hay bastantes datos propios y cuánto tiene que mejorar un método
# para sustituir al que se usa (en semanas que no ha visto).
MIN_HORES_PLUJA = 30        # horas con lluvia medida en casa
MIN_DIES_TEMPERATURA = 14
MILLORA_MINIMA = 0.05       # 5 % menos de error
SETMANES_VALIDACIO = 4      # grupos de semanas para la validación cruzada
PERSISTENCIA_H = 4          # horas en que cuenta lo medido al prever (lluvia, sequedad)
# Cuánto dura el error de temperatura que tenía el modelo al prever: una
# parte se pierde en unas horas, otra en un día (ADR 0017).
ERROR_TEMP_H = (3, 24)

# Un modelo «da lluvia» desde su décima de milímetro: que ponga algo ya dice
# mucho más de lo que pesa su cantidad (ADR 0021).
MM_MODEL_PLOU = 0.1
RASGOS_ARXIU = ["constant", "arome_hd", "arome", "icon_eu", "antelacio",
                "hora_sin", "hora_cos", "dia_sin", "dia_cos",
                "plou_arome_hd", "plou_arome", "plou_icon_eu", "dos_models", "tres_models",
                "arome_hd_antelacio", "arome_antelacio", "icon_eu_antelacio",
                "algun_antelacio", "tres_antelacio"]
RASGOS_PROPIS = RASGOS_ARXIU + ["ensemble", "persistencia", "sequedat"]
# Con la lluvia de la última hora en Sant Cugat (Meteocat, a 4,6 km, en la
# cuenca de la riera): se ajusta aparte y solo gana si acierta más (ADR 0042).
RASGOS_PROPIS_XV = RASGOS_PROPIS + ["sant_cugat"]
AVIS_XV = os.path.join(DIR, "avis-sant-cugat")
# Con lo oficial de cada hora: aviso de AEMET por lluvia o tormentas y el
# INUNCAT en alerta o emergencia. Se registran desde el 08-10-2026; la variante
# se ajusta aparte y solo gana si acierta más (ADR 0047).
RASGOS_PROPIS_AVIS = RASGOS_PROPIS + ["avis_aemet", "pla_inuncat"]
# Sin la estación de casa (si falla al prever), la temperatura se corrige con
# los mismos rasgos menos el error al prever.
RASGOS_TEMPERATURA_SENSE_ESTACIO = ["constant", "temperatura", "nuvols", "humitat", "hora_sin",
                                    "hora_cos", "antelacio", "dia_sin", "dia_cos", "radiacio"]
RASGOS_TEMPERATURA = RASGOS_TEMPERATURA_SENSE_ESTACIO + ["error_ara_3h", "error_ara_24h"]


# --- Rasgos ------------------------------------------------------------------------

def rasgos(d, noms):
    """Vector de rasgos de una hora. d lleva lo que se guarda en el registro:
    la lluvia de cada modelo (pluja_<modelo>), «fins» (hora local en que acaba
    el tramo), antelacio_h, prob_ens, temperature_2m… y lo que medía la
    estación al prever: pluja_1h_emes, error_temp_ara (temperatura del modelo
    menos la medida) y deficit_rosada_ara (temperatura menos punto de rocío)."""
    fin = dt.datetime.fromisoformat(d["fins"])
    h = 2 * math.pi * fin.hour / 24
    dia = 2 * math.pi * fin.timetuple().tm_yday / 365.25
    pluja = {m: d.get(f"pluja_{m}") for m in C.MODELOS_FINOS}
    antelacio = max(d.get("antelacio_h", 0), 0)
    corto = d.get("antelacio_h", 99) <= PERSISTENCIA_H
    error_ara, deficit = d.get("error_temp_ara"), d.get("deficit_rosada_ara")
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
        "persistencia": math.log1p(d.get("pluja_1h_emes") or 0) if corto else 0.0,
        # Aire seco al prever, menos lluvia en las horas siguientes.
        "sequedat": (0.0 if not corto else None if deficit is None else min(max(deficit, 0), 15) / 10),
        # Lo que llovía en Sant Cugat al prever, como la persistencia; sin dato, no hay vector.
        "sant_cugat": (0.0 if not corto else None if d.get("pluja_1h_xv") is None else math.log1p(d["pluja_1h_xv"])),
        # Lo oficial de la hora (0 o 1); sin dato, no hay vector.
        "avis_aemet": d.get("avis_pluja"),
        "pla_inuncat": d.get("pla_inuncat"),
        "temperatura": d.get("temperature_2m"),
        "nuvols": None if d.get("cloud_cover") is None else d["cloud_cover"] / 100,
        "vent": None if d.get("wind_speed_10m") is None else d["wind_speed_10m"] / 10,
        "humitat": None if d.get("relative_humidity_2m") is None else d["relative_humidity_2m"] / 100,
        "radiacio": None if d.get("shortwave_radiation") is None else d["shortwave_radiation"] / 1000,
        "error_ara_3h": None if error_ara is None else error_ara * math.exp(-antelacio / ERROR_TEMP_H[0]),
        "error_ara_24h": None if error_ara is None else error_ara * math.exp(-antelacio / ERROR_TEMP_H[1]),
    }
    # Si un modelo da lluvia, cuántos coinciden y cuánto vale todo eso según
    # la antelación: la lluvia prevista para dentro de un día se cumple menos.
    mm = [valors[m] for m in ("arome_hd", "arome", "icon_eu")]
    if None not in mm:
        plou = [float(v >= MM_MODEL_PLOU - 1e-9) for v in mm]
        ant = valors["antelacio"]
        for m, v, p in zip(("arome_hd", "arome", "icon_eu"), mm, plou):
            valors[m] = math.log1p(max(v, 0))
            valors[f"plou_{m}"] = p
            valors[f"{m}_antelacio"] = valors[m] * ant
        valors["dos_models"] = float(sum(plou) >= 2)
        valors["tres_models"] = float(sum(plou) == 3)
        valors["algun_antelacio"] = float(sum(plou) >= 1) * ant
        valors["tres_antelacio"] = valors["tres_models"] * ant
    x = [valors.get(n) for n in noms]
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


def modelo_arxiu_temperatura():
    with open(ARXIU_TEMPERATURA, encoding="utf-8") as f:
        m = json.load(f)
    return {k: v for k, v in m.items() if k != "pluja"}


def carrega():
    """El modelo en uso: el aprendido en el NAS si lo hay; lo que falte, el
    del archivo (lluvia de 2024-2026, temperatura del último año en casa)."""
    model = {"pluja": None, "temperatura": None}
    try:
        with open(MODEL, encoding="utf-8") as f:
            model.update(json.load(f))
    except (OSError, ValueError):
        pass
    for clave, carga in (("pluja", modelo_arxiu), ("temperatura", modelo_arxiu_temperatura)):
        if not model.get(clave):
            try:
                model[clave] = carga()
            except (OSError, ValueError):
                pass
    return model


def prob_pluja(model, d):
    """Probabilidad de lluvia. Si el modelo propio necesita la estación de
    casa y no hay dato, la del archivo."""
    m = (model or {}).get("pluja")
    x = rasgos(d, m["rasgos"]) if m else None
    if x is None and m and m.get("origen") != "arxiu":
        m = modelo_arxiu()
        x = rasgos(d, m["rasgos"])
    return None if x is None else float(predecir(np.array(m["w"]), np.array(x)))


def temperatura(model, d):
    """Temperatura corregida; sin la estación al prever, con los pesos que no
    la necesitan; sin modelo, la del modelo meteorológico."""
    m = (model or {}).get("temperatura")
    if not m or d.get("temperature_2m") is None:
        return d.get("temperature_2m")
    for sufijo in ("", "_sense_estacio"):
        if m.get(f"rasgos{sufijo}"):
            x = rasgos(d, m[f"rasgos{sufijo}"])
            if x is not None:
                return d["temperature_2m"] - float(np.array(m[f"w{sufijo}"]) @ np.array(x))
    return d["temperature_2m"]


def resum_pagina(model):
    """Lo que dice la página sobre cómo se calcula."""
    p, t = (model or {}).get("pluja"), (model or {}).get("temperatura")
    return {"pluja": p and {"origen": p["origen"], "des_de": p["des_de"]},
            "temperatura": t and {"origen": t["origen"], "des_de": t["des_de"]}}


# --- Datos propios ----------------------------------------------------------------------

def _llegeix(nom):
    ruta = os.path.join(REGISTRE, nom)
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding="utf-8") as f:
        return {r["fins"]: r for r in csv.DictReader(f)}


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def pluja_observada(casa, meteocat=()):
    """mm de la hora según la estación de casa. Lo que marca es lluvia; su
    cero solo vale como hora seca si las estaciones de alrededor (meteocat:
    lo que midió cada una, si lo hay: las de Meteocat y la vecina fiable de
    Weather Underground) tampoco recogieron nada: el pluviómetro a veces no
    marca la lluvia débil (ADR 0017, 0058 y 0060). Sin casa, o con casa a
    cero y lluvia cerca, no se sabe."""
    c = _num((casa or {}).get("pluja_mm"))
    if c is None:
        return None
    if c >= C.UMBRAL_MM:
        return c
    prop = [_num((m or {}).get("pluja_mm")) for m in meteocat]
    prop = [x for x in prop if x is not None]
    return 0.0 if prop and all(x < C.UMBRAL_MM for x in prop) else None


def _meteocat():
    """Lo medido por horas en cada estación de Meteocat del registro y en
    las vecinas de Weather Underground cuyo cero confirma una hora seca
    (config.VEINES, ADR 0060)."""
    return ([_llegeix(f"meteocat-{codi}.csv") for codi in C.ESTACIONES]
            + [_llegeix(f"veina-{estacio}.csv") for estacio, v in C.VEINES.items() if v.get("sec")])


def mostres():
    """Una muestra por hora prevista y pasada de cada previsión registrada, con
    lo que pasó: la lluvia y la temperatura de casa (ADR 0017), con las
    estaciones de Meteocat y la vecina fiable para confirmar las horas secas
    (ADR 0058 y 0060)."""
    casa, meteocat = _llegeix("estacio-casa.csv"), _meteocat()
    res = []
    for arxiu in sorted(glob.glob(os.path.join(REGISTRE, "casa-*.jsonl"))):
        with open(arxiu, encoding="utf-8") as f:
            for linea in map(json.loads, f):
                ara_casa = linea.get("ara_casa") or {}
                plujas = [x for x in (ara_casa.get("pluja_1h"),) if x is not None]
                for h in linea["hores"]:
                    obs_pluja = pluja_observada(casa.get(h["fins"]), [m.get(h["fins"]) for m in meteocat])
                    obs_temp = _num((casa.get(h["fins"]) or {}).get("temperatura"))
                    if obs_pluja is None and obs_temp is None:
                        continue
                    res.append({**h, "emes": linea["emes"], "pluja_1h_emes": max(plujas) if plujas else None,
                                "pluja_1h_xv": (linea.get("sant_cugat") or {}).get("pluja_1h"),
                                "obs_pluja": obs_pluja, "obs_temp": obs_temp})
    return res


def grupo_semana(m):
    """Grupo de validación por la semana de la hora observada: así todas las
    previsiones de una misma hora caen en el mismo grupo (auditoría del
    08-10-2026; antes iba por la fecha de emisión)."""
    d = dt.date.fromisoformat(m["fins"][:10])
    return (d.isocalendar()[0] * 53 + d.isocalendar()[1]) % SETMANES_VALIDACIO


def valida_pluja(ms, arxiu, noms=RASGOS_PROPIS):
    """Error (Brier) en validación cruzada por semanas del modelo propio (con
    los rasgos noms) y del archivo, con las mismas muestras."""
    ms = [m for m in ms if m["obs_pluja"] is not None and rasgos(m, noms) is not None]
    if not ms:
        return None
    x = np.array([rasgos(m, noms) for m in ms])
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
    # Horas observadas distintas con lluvia: cada hora se prevé muchas veces y
    # no cuenta más por eso (auditoría del 08-10-2026).
    hores_pluja = len({m["fins"] for m, plou in zip(ms, y) if plou})
    return {"mostres": len(y), "hores_pluja": hores_pluja, "rasgos": noms,
            "error": float(np.mean((p - y) ** 2)),
            "error_abans": float(np.mean((predecir(np.array(arxiu["w"]), xa) - y) ** 2)),
            "w": ajustar(x, y).tolist() if y.sum() else None}


def valida_temperatura(ms, arxiu_t):
    """Error medio absoluto en validación cruzada por semanas: la corrección
    ajustada con el registro propio frente a la del archivo (o, sin ella, la
    temperatura sin corregir), con las mismas horas."""
    ms = [m for m in ms if m["obs_temp"] is not None and rasgos(m, RASGOS_TEMPERATURA) is not None]
    if not ms:
        return None
    x = np.array([rasgos(m, RASGOS_TEMPERATURA) for m in ms])
    modelo = np.array([m["temperature_2m"] for m in ms])
    obs = np.array([m["obs_temp"] for m in ms])
    error = modelo - obs
    grupo = np.array([grupo_semana(m) for m in ms])
    if len(set(grupo)) < 2:
        return None
    pred = np.zeros(len(error))
    for g in set(grupo):
        ent = grupo != g
        pred[~ent] = x[~ent] @ ajustar_ridge(x[ent], error[ent])
    abans = np.array([temperatura({"temperatura": arxiu_t}, m) for m in ms])
    xs = np.array([rasgos(m, RASGOS_TEMPERATURA_SENSE_ESTACIO) for m in ms])
    dies = len({m["emes"][:10] for m in ms})
    return {"mostres": len(ms), "dies": dies,
            "error": float(np.mean(np.abs(error - pred))),
            "error_abans": float(np.mean(np.abs(abans - obs))),
            "w": ajustar_ridge(x, error).tolist(), "w_sense_estacio": ajustar_ridge(xs, error).tolist()}


def valida_variant(ms, arxiu, noms):
    """Una variante (Sant Cugat, los avisos), solo con las muestras que llevan
    su dato, y el modelo base ajustado y comprobado con esas mismas muestras
    (error_base): un error medido en horas distintas no se puede comparar.
    Hasta la auditoría del 09-10-2026 la variante se elegía por tener menos
    error que el base, aunque el suyo saliera de la mitad de las horas."""
    sub = [m for m in ms if m["obs_pluja"] is not None and rasgos(m, noms) is not None]
    v = valida_pluja(sub, arxiu, noms)
    if v:
        base = valida_pluja(sub, arxiu)
        v["error_base"] = base["error"] if base else None
        v["mostres_base"] = base["mostres"] if base else None
    return v


# --- Decisión diaria -------------------------------------------------------------------

def millora(v):
    return v["error"] < (1 - MILLORA_MINIMA) * v["error_abans"]


def candidat(ms, arxiu, arxiu_t, avui):
    """El modelo que tocaría usar con los datos de hoy, y los números."""
    vp, vt = valida_pluja(ms, arxiu), valida_temperatura(ms, arxiu_t)
    # Las variantes con Sant Cugat y con los avisos, aparte: solo con las
    # muestras que llevan el dato, y el base con esas mismas (valida_variant).
    if vp:
        vp["xv"] = valida_variant(ms, arxiu, RASGOS_PROPIS_XV)
        vp["avis"] = valida_variant(ms, arxiu, RASGOS_PROPIS_AVIS)
    model = {"pluja": arxiu, "temperatura": arxiu_t}

    def val(v):
        return bool(v and v["hores_pluja"] >= MIN_HORES_PLUJA and v["w"] and millora(v))
    # Una variante, solo si en sus mismas horas mejora también al base en
    # MILLORA_MINIMA; entre varias, la que más lo mejora en proporción. Si
    # ninguna, el base, si mejora al archivo.
    variants = [v for v in ((vp or {}).get("xv"), (vp or {}).get("avis"))
                if val(v) and v.get("error_base") and v["error"] < (1 - MILLORA_MINIMA) * v["error_base"]]
    v = max(variants, key=lambda v: 1 - v["error"] / v["error_base"]) if variants else vp if val(vp) else None
    if v:
        model["pluja"] = {"origen": "local", "des_de": ms[0]["emes"][:10], "fins": avui,
                          "rasgos": v["rasgos"], "w": v["w"], "error": v["error"],
                          "error_abans": v["error_abans"], "mostres": v["mostres"],
                          "error_base": v.get("error_base")}
    if vt and vt["dies"] >= MIN_DIES_TEMPERATURA and millora(vt):
        model["temperatura"] = {"origen": "casa", "des_de": ms[0]["emes"][:10], "fins": avui,
                                "rasgos": RASGOS_TEMPERATURA, "w": vt["w"],
                                "rasgos_sense_estacio": RASGOS_TEMPERATURA_SENSE_ESTACIO,
                                "w_sense_estacio": vt["w_sense_estacio"], "error": vt["error"],
                                "error_abans": vt["error_abans"], "mostres": vt["mostres"]}
    return model, vp, vt


def metode(model):
    p, t = model.get("pluja"), model.get("temperatura")
    return ((p or {}).get("origen"), (t or {}).get("origen"))


def explica(abans, nou, vp, vt):
    """Mensaje de Telegram: qué cambia y con qué números."""
    linies = ["Temps a casa: canvi de mètode d'aprenentatge, s'aplicarà demà."]
    if metode(abans)[0] != metode(nou)[0]:
        if nou["pluja"]["origen"] != "arxiu":
            p = nou["pluja"]
            amb_xv = (" i la pluja de Sant Cugat" if "sant_cugat" in p["rasgos"]
                      else " i els avisos oficials" if "avis_aemet" in p["rasgos"] else "")
            linies.append(f"Pluja: passa a aprendre de l'estació de casa{amb_xv} "
                          f"({p['mostres']} mostres). "
                          f"Error {p['error']:.4f} en setmanes no vistes, abans {p['error_abans']:.4f}."
                          + (f" Sense aquest rasgo, a les mateixes hores: {p['error_base']:.4f}."
                             if p.get("error_base") else ""))
        else:
            linies.append("Pluja: torna al model de l'arxiu; el propi ja no millora.")
    if metode(abans)[1] != metode(nou)[1]:
        if nou["temperatura"] and nou["temperatura"]["origen"] != "arxiu":
            linies.append(f"Temperatura: es corregeix amb el registre propi ({vt['dies']} dies). "
                          f"Error mitjà {vt['error']:.2f} °C, amb la correcció de l'arxiu {vt['error_abans']:.2f} °C.")
        else:
            linies.append("Temperatura: torna a la correcció de l'arxiu; la del registre propi ja no millora.")
    linies.append("Per aturar-ho, demana-ho a Claude abans de demà.")
    return "\n".join(linies)


def per_desar(model):
    """Lo que se guarda en el NAS: solo los modelos propios. Los del archivo
    se leen siempre del repositorio, para que un ajuste nuevo llegue solo."""
    return {k: (v if v and v.get("origen") != "arxiu" else None) for k, v in model.items()}


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
                        "error_pluja_arxiu", "dies_temperatura", "error_temp", "error_temp_model",
                        "hores_pluja_sant_cugat", "error_pluja_sant_cugat",
                        "hores_pluja_avisos", "error_pluja_avisos"])
        xv, av = (vp or {}).get("xv"), (vp or {}).get("avis")
        w.writerow([avui, *metode(model),
                    vp and vp["mostres"], vp and vp["hores_pluja"], vp and round(vp["error"], 5),
                    vp and round(vp["error_abans"], 5), vt and vt["dies"],
                    vt and round(vt["error"], 2), vt and round(vt["error_abans"], 2),
                    xv and xv["hores_pluja"], xv and round(xv["error"], 5),
                    av and av["hores_pluja"], av and round(av["error"], 5)])


def diari(avui=None, avisa=True):
    avui = avui or dt.date.today().isoformat()
    os.makedirs(DIR, exist_ok=True)
    # Qué radar acierta más en casa (radar_fonts.py, ADR 0026).
    try:
        import radar_fonts
        radar_fonts.verifica(dt.date.fromisoformat(avui), avisa)
    except Exception as ex:
        print("No he pogut comparar els radars:", ex)
    # A qué hora para la lluvia, según el radar: con 5 episodios, el resultado
    # a Juanjo, una vez (ADR 0049).
    try:
        import fi_pluja
        text_fi = fi_pluja.verifica(avisa)
        if text_fi:
            print(text_fi)
    except Exception as ex:
        print("No he pogut comprovar el final de la pluja:", ex)
    # Qué dijo la regla de la moto de «Si surts» y si llovió (ADR 0047).
    try:
        print("Moto: hores noves verificades:", verifica_moto())
        text_moto = avis_moto(avisa)
        if text_moto:
            print(text_moto)
    except Exception as ex:
        print("No he pogut verificar la moto:", ex)
    # El viento con las vecinas: factores, comprobación y, una vez, el
    # resultado a Juanjo para que decida (ADR 0064).
    try:
        import vent_veines
        vent_veines.apren(avisa=avisa, registre=REGISTRE, directori=DIR)
    except Exception as ex:
        print("No he pogut aprendre el vent de les veïnes:", ex)
    arxiu, arxiu_t = modelo_arxiu(), modelo_arxiu_temperatura()
    en_us = carrega()
    # 1. Una propuesta de ayer que nadie ha parado: se aplica.
    if os.path.exists(PROPOSAT):
        with open(PROPOSAT, encoding="utf-8") as f:
            proposat = json.load(f)
        if os.path.exists(ATURA):
            print("Proposta aturada: no s'aplica.")
            os.remove(PROPOSAT)
        elif proposat["dia"] < avui:
            guarda(MODEL, per_desar(proposat["model"]))
            en_us = carrega()
            os.remove(PROPOSAT)
            print("Aplicada la proposta d'ahir:", metode(en_us))
    # 2. Lo que tocaría hoy.
    nou, vp, vt = candidat(mostres(), arxiu, arxiu_t, avui)
    apunta_historial(avui, nou, vp, vt)
    # Una sola vez: cuando haya bastante lluvia con el dato de Sant Cugat, el
    # resultado medido, para decidir si se pide la clave de AEMET (ADR 0042).
    text_xv = avis_sant_cugat(vp)
    if text_xv:
        print(text_xv)
        if avisa:
            subprocess.run(["avisar-juanjo", "--asunto", "meteo-local", text_xv], check=False)
    if metode(nou) == metode(en_us):
        # Mismo método, más datos: se pone al día sin avisar.
        if per_desar(nou) != per_desar(en_us) and not os.path.exists(ATURA):
            guarda(MODEL, per_desar(nou))
        print("Mateix mètode:", metode(nou))
        return
    if os.path.exists(ATURA):
        print("Canvi de mètode aturat (existeix «atura»).")
        return
    guarda(PROPOSAT, {"dia": avui, "model": per_desar(nou)})
    text = explica(en_us, nou, vp, vt)
    print(text)
    if avisa:
        subprocess.run(["avisar-juanjo", "--asunto", "meteo-local", text], check=False)


def avis_sant_cugat(vp):
    """El día en que el registro tiene MIN_HORES_PLUJA horas de lluvia con la
    lluvia de Sant Cugat, una vez: si ese rasgo acierta más o no, con las
    cifras (Juanjo, 08-10-2026: «¿quién se acordará de mirarlo?»)."""
    xv = (vp or {}).get("xv")
    if not xv or xv["hores_pluja"] < MIN_HORES_PLUJA or xv.get("error_base") is None or os.path.exists(AVIS_XV):
        return None
    # Contra el base a las mismas horas, no contra el base de todas (auditoría del 09-10-2026).
    sense = xv["error_base"]
    ajuda = xv["error"] < sense
    text = (f"Temps a casa: el registre ja té {xv['hores_pluja']} hores de pluja amb la dada de Sant Cugat. "
            f"Error en setmanes no vistes, a les mateixes hores: amb la pluja de Sant Cugat {xv['error']:.4f}, "
            f"sense {sense:.4f} (model de l'arxiu {xv['error_abans']:.4f}). "
            + ("Ajuda: si vols, demana la clau d'OpenData de l'AEMET i afegim l'aeroport de Sabadell."
               if ajuda else "No ajuda: no val la pena afegir l'aeroport de Sabadell."))
    os.makedirs(DIR, exist_ok=True)
    open(AVIS_XV, "w").close()
    return text


# --- «Si surts»: el veredicto de la moto y lo que pasó (ADR 0047) ------------------------

MOTO = os.path.join(REGISTRE, "moto.csv")
CAMPS_MOTO = ["fins", "termini", "emes", "antelacio_h", "probabilitat", "pluja_mm", "plou_ara",
              "avis", "nivell", "nivell_abans", "pluja_obs"]
# Con qué antelación se juzga: al salir (la previsión de 1 a 3 horas antes) y
# la vuelta, decidida por la mañana (de 6 a 10 horas antes); de cada hora, la
# previsión más reciente dentro de ese margen.
TERMINIS_MOTO = {"sortida": (1, 3), "tornada": (6, 10)}
# Solo las horas en que se circula: tramos que acaban de las 7 a las 22 h.
HORES_MOTO = range(7, 23)
DIES_RESUM_MOTO = 28            # resumen por Telegram, una vez
AVIS_MOTO = os.path.join(DIR, "avis-moto")
# La regla de antes del 08-10-2026, para comparar: 50 % o 1 mm, «no»; 20 % o
# 0,2 mm, «compte»; un aviso de AEMET solo, «no».
ABANS_MOTO = (0.2, 0.5, 0.2, 1.0)


def nivell_moto(m, avis, abans=False):
    """Veredicto de lluvia de la moto en una hora, como web/sortir.js: «be»,
    «compte» o «no». m: lo que mostró la página («mostrat»)."""
    p, mm, plou = m.get("probabilitat"), m.get("pluja_mm") or 0, m.get("plou_ara")
    if abans:
        risc, pluja, mm_risc, mm_pluja = ABANS_MOTO
        if plou or avis or (p or 0) >= pluja or mm >= mm_pluja:
            return "no"
        return "compte" if (p or 0) >= risc or mm >= mm_risc else "be"

    def sobre(prob, llindar_mm):
        return mm >= llindar_mm if p is None else p >= prob
    if plou or sobre(C.MOTO_PROB_PLUJA, C.MOTO_MM_PLUJA):
        return "no"
    return "compte" if avis or sobre(C.MOTO_PROB_RISC, C.MOTO_MM_RISC) else "be"


def verifica_moto(ahora=None):
    """Apunta en moto.csv, de cada hora pasada que tenga lluvia medida y que
    aún no esté, qué decía la regla de la moto (la de ahora y la de antes) y
    si llovió. Devuelve cuántas horas ha añadido."""
    ahora = ahora or dt.datetime.now().astimezone()
    fetes = set()
    if os.path.exists(MOTO):
        with open(MOTO, encoding="utf-8") as f:
            fetes = {(r["fins"], r["termini"]) for r in csv.DictReader(f)}
    casa, meteocat = _llegeix("estacio-casa.csv"), _meteocat()
    millor = {}
    for arxiu in sorted(glob.glob(os.path.join(REGISTRE, "casa-*.jsonl"))):
        with open(arxiu, encoding="utf-8") as f:
            for linea in map(json.loads, f):
                for h in linea["hores"]:
                    # Sin el aviso registrado (antes del 08-10-2026) no se sabe qué dijo.
                    if not h.get("mostrat") or h.get("avis_pluja") is None or int(h["fins"][11:13]) not in HORES_MOTO:
                        continue
                    for termini, (a, b) in TERMINIS_MOTO.items():
                        clau = (h["fins"], termini)
                        if a <= h["antelacio_h"] < b and (clau not in millor
                                                          or h["antelacio_h"] < millor[clau][1]["antelacio_h"]):
                            millor[clau] = (linea["emes"], h)
    noves = []
    for (fins, termini), (emes, h) in sorted(millor.items()):
        if (fins, termini) in fetes or dt.datetime.fromisoformat(fins).astimezone() > ahora:
            continue
        obs = pluja_observada(casa.get(fins), [m.get(fins) for m in meteocat])
        if obs is None:
            continue
        m, avis = h["mostrat"], bool(h["avis_pluja"])
        noves.append({"fins": fins, "termini": termini, "emes": emes, "antelacio_h": h["antelacio_h"],
                      "probabilitat": m.get("probabilitat"), "pluja_mm": m.get("pluja_mm"),
                      "plou_ara": int(bool(m.get("plou_ara"))), "avis": int(avis),
                      "nivell": nivell_moto(m, avis), "nivell_abans": nivell_moto(m, avis, abans=True),
                      "pluja_obs": obs})
    if noves:
        os.makedirs(os.path.dirname(MOTO), exist_ok=True)
        nou = not os.path.exists(MOTO)
        with open(MOTO, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CAMPS_MOTO)
            if nou:
                w.writeheader()
            w.writerows(noves)
    return len(noves)


def resum_moto():
    """Qué ha pasado con la regla de la moto desde que se registra, frente a la
    de antes. None si aún no hay nada."""
    if not os.path.exists(MOTO):
        return None
    with open(MOTO, encoding="utf-8") as f:
        files = list(csv.DictReader(f))
    if not files:
        return None
    dies = sorted({r["fins"][:10] for r in files})
    res = {"dies": len(dies), "des_de": dies[0], "fins": dies[-1]}
    for termini in TERMINIS_MOTO:
        fs = [r for r in files if r["termini"] == termini]
        plou = [float(r["pluja_obs"]) >= C.UMBRAL_MM for r in fs]
        res[termini] = {"hores": len(fs), "hores_pluja": sum(plou)}
        for clau in ("nivell", "nivell_abans"):
            res[termini][clau] = {
                "sec": {n: sum(1 for r, p in zip(fs, plou) if not p and r[clau] == n) for n in ("compte", "no")},
                "pluja": {n: sum(1 for r, p in zip(fs, plou) if p and r[clau] == n) for n in ("be", "compte", "no")}}
    return res


def text_resum_moto(r):
    """El resumen para Juanjo: falsas alarmas y lluvia con «bé», con la regla
    de ahora y la de antes."""
    noms = {"sortida": "Al sortir (previsió d'1 a 3 h abans)",
            "tornada": "Tornada decidida al matí (de 6 a 10 h abans)"}
    linies = [f"Si surts, pluja en moto: {r['dies']} dies registrats ({r['des_de']} a {r['fins']}), "
              "hores de 6 a 22 h. Entre parèntesis, la regla d'abans del 08-10-2026."]
    for termini, nom in noms.items():
        t = r[termini]
        a, b = t["nivell"], t["nivell_abans"]
        linies.append(f"{nom}: {t['hores']} hores, {t['hores_pluja']} amb pluja. "
                      f"Sense pluja, «no» {a['sec']['no']} ({b['sec']['no']}) i «compte» "
                      f"{a['sec']['compte']} ({b['sec']['compte']}). "
                      f"Amb pluja, «bé» {a['pluja']['be']} ({b['pluja']['be']}).")
    if sum(r[t]["hores_pluja"] for t in TERMINIS_MOTO) < 5:
        linies.append("Encara hi ha massa poca pluja per jutjar-ho.")
    return "\n".join(linies)


def avis_moto(avisa=True):
    """El resumen, una sola vez, cuando hay DIES_RESUM_MOTO días."""
    r = resum_moto()
    if not r or r["dies"] < DIES_RESUM_MOTO or os.path.exists(AVIS_MOTO):
        return None
    text = text_resum_moto(r)
    if avisa:
        subprocess.run(["avisar-juanjo", "--asunto", "meteo-local", text], check=False)
    os.makedirs(DIR, exist_ok=True)
    open(AVIS_MOTO, "w").close()
    return text


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
    elif orden == "moto":
        r = resum_moto()
        print(text_resum_moto(r) if r else "Encara no hi ha cap hora verificada.")
    else:
        print(__doc__)
