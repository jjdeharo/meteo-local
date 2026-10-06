#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Aprendizaje de la página de casa con lo que pasó de verdad (ADR 0012).

Dos regresiones, sin IA, ajustadas con numpy:

- Lluvia: regresión logística. Da la probabilidad de que caigan 0,2 mm o
  más en una hora a partir de la lluvia de los tres modelos finos (cuánta, si
  cada uno da alguna y cuántos coinciden), la antelación, la hora y el día
  del año (ADR 0021) y, con datos propios, la fracción del ensemble y la
  lluvia que medía Montflorit al hacer la previsión.
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
MIN_HORES_PLUJA = 30        # horas con lluvia en Montflorit
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


def pluja_observada(mont, casa):
    """mm de la hora: Montflorit y, si marca lluvia, la estación de casa (su
    cero no es fiable). Sin Montflorit y sin lluvia en casa, no se sabe."""
    m, c = _num((mont or {}).get("pluja_mm")), _num((casa or {}).get("pluja_mm"))
    if m is None:
        return c if c is not None and c >= C.UMBRAL_MM else None
    return max(m, c or 0)


def mostres():
    """Una muestra por hora prevista y pasada de cada previsión registrada, con
    lo que pasó: la lluvia de Montflorit y de casa y la temperatura de casa
    (ADR 0017)."""
    mont, casa = _llegeix("montflorit.csv"), _llegeix("estacio-casa.csv")
    res = []
    for arxiu in sorted(glob.glob(os.path.join(REGISTRE, "casa-*.jsonl"))):
        with open(arxiu, encoding="utf-8") as f:
            for linea in map(json.loads, f):
                ara, ara_casa = linea.get("ara") or {}, linea.get("ara_casa") or {}
                plujas = [x for x in (ara.get("pluja_1h"), ara_casa.get("pluja_1h")) if x is not None]
                for h in linea["hores"]:
                    obs_pluja = pluja_observada(mont.get(h["fins"]), casa.get(h["fins"]))
                    obs_temp = _num((casa.get(h["fins"]) or {}).get("temperatura"))
                    if obs_pluja is None and obs_temp is None:
                        continue
                    res.append({**h, "emes": linea["emes"], "pluja_1h_emes": max(plujas) if plujas else None,
                                "obs_pluja": obs_pluja, "obs_temp": obs_temp})
    return res


def grupo_semana(m):
    d = dt.date.fromisoformat(m["emes"][:10])
    return (d.isocalendar()[0] * 53 + d.isocalendar()[1]) % SETMANES_VALIDACIO


def valida_pluja(ms, arxiu):
    """Error (Brier) en validación cruzada por semanas del modelo propio y del
    archivo, con las mismas muestras."""
    ms = [m for m in ms if m["obs_pluja"] is not None and rasgos(m, RASGOS_PROPIS) is not None]
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


# --- Decisión diaria -------------------------------------------------------------------

def millora(v):
    return v["error"] < (1 - MILLORA_MINIMA) * v["error_abans"]


def candidat(ms, arxiu, arxiu_t, avui):
    """El modelo que tocaría usar con los datos de hoy, y los números."""
    vp, vt = valida_pluja(ms, arxiu), valida_temperatura(ms, arxiu_t)
    model = {"pluja": arxiu, "temperatura": arxiu_t}
    if vp and vp["hores_pluja"] >= MIN_HORES_PLUJA and vp["w"] and millora(vp):
        model["pluja"] = {"origen": "local", "des_de": ms[0]["emes"][:10], "fins": avui,
                          "rasgos": RASGOS_PROPIS, "w": vp["w"], "error": vp["error"],
                          "error_abans": vp["error_abans"], "mostres": vp["mostres"]}
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
            linies.append(f"Pluja: passa a aprendre de Montflorit i de l'estació de casa "
                          f"({vp['hores_pluja']} hores amb pluja). "
                          f"Error {vp['error']:.4f} en setmanes no vistes, abans {vp['error_abans']:.4f}.")
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
                        "error_pluja_arxiu", "dies_temperatura", "error_temp", "error_temp_model"])
        w.writerow([avui, *metode(model),
                    vp and vp["mostres"], vp and vp["hores_pluja"], vp and round(vp["error"], 5),
                    vp and round(vp["error_abans"], 5), vt and vt["dies"],
                    vt and round(vt["error"], 2), vt and round(vt["error_abans"], 2)])


def diari(avui=None, avisa=True):
    avui = avui or dt.date.today().isoformat()
    os.makedirs(DIR, exist_ok=True)
    # Qué radar acierta más en casa (radar_fonts.py, ADR 0026).
    try:
        import radar_fonts
        radar_fonts.verifica(dt.date.fromisoformat(avui), avisa)
    except Exception as ex:
        print("No he pogut comparar els radars:", ex)
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
