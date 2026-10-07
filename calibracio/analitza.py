#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Compara la regla con lo que pasó de verdad y ajusta una probabilidad.

Lee lo que baja descarrega.py y escribe:
- calibracio/informe.md: aciertos de la regla actual y del modelo calibrado;
- calibracio/calibracio.json: frecuencia real de lluvia en cada nivel de la
  regla del trayecto retirado (ADR 0030; queda como histórico) y la
  persistencia de la lluvia, que usa casa.py.

La regresión logística y el CAPE se calculan solo para compararlos con la
regla: con estos datos no la mejoran (ver informe.md y el ADR 0003).

Qué se cuenta como lluvia en el trayecto: 0,2 mm o más en alguna media hora
de la ventana en Sabadell (XF) o en Sant Cugat (XV).
"""
import csv
import datetime as dt
import json
import math
import os
import sys
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402
from aprenentatge import ajustar, predecir  # noqa: E402,F401

AQUI = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(AQUI, "dades")
LOCAL = ZoneInfo("Europe/Madrid")
UTC = dt.timezone.utc
UMBRAL_LLUVIA = 0.2
# La regla del trayecto retirado (ADR 0030), que aquí se sigue comparando con
# el histórico: sus ventanas en moto (hora local) y el umbral de lluvia clara
# (mm en una hora). Estaban en config.py.
ANADA = ("06:30", "07:30")
TORNADA = ("15:00", "15:30")
UMBRAL_MM_COCHE = 1.0


# --- Lectura -------------------------------------------------------------------

def leer_obs():
    obs = {}
    for codi in C.ESTACIONES:
        serie = {}
        with open(os.path.join(DIR, f"obs_{codi}.csv")) as f:
            for fila in csv.DictReader(f):
                t = dt.datetime.fromisoformat(fila["inicio_utc"]).replace(tzinfo=UTC)
                serie[t] = float(fila["mm"])
        obs[codi] = serie
    return obs


def leer_prev():
    prev = {}
    for punto in ("casa", "desti"):
        with open(os.path.join(DIR, f"prev_{punto}.csv")) as f:
            for fila in csv.DictReader(f):
                t = dt.datetime.fromisoformat(fila["hora_utc"]).replace(tzinfo=UTC)
                prev.setdefault(t, {})[punto] = {
                    k: (float(v) if v not in ("", "None") else None)
                    for k, v in fila.items() if k != "hora_utc"}
    return prev


# --- Ventanas ------------------------------------------------------------------

def medias_horas(dia, ventana):
    """Inicios (UTC) de las medias horas que cubren la ventana local."""
    ini, fin = (dt.datetime.combine(dia, dt.time.fromisoformat(x), LOCAL) for x in ventana)
    t, res = ini, []
    while t < fin:
        res.append(t.astimezone(UTC))
        t += dt.timedelta(minutes=30)
    return res


def horas_prevision(dia, ventana):
    """Horas (UTC) en que acaban los acumulados horarios que cubren la ventana."""
    ini, fin = (dt.datetime.combine(dia, dt.time.fromisoformat(x), LOCAL) for x in ventana)
    primera = ini.replace(minute=0) + dt.timedelta(hours=1)
    res, t = [], primera
    while t - dt.timedelta(hours=1) < fin:
        res.append(t.astimezone(UTC))
        t += dt.timedelta(hours=1)
    return res


def lluvia_observada(obs, dia, ventana):
    """mm máximos de una media hora en la ventana, o None si faltan datos."""
    valores = []
    for serie in obs.values():
        vs = [serie.get(t) for t in medias_horas(dia, ventana)]
        if all(v is not None for v in vs):
            valores.append(max(vs))
    return max(valores) if valores else None


def rasgos(prev, dia, ventana, plazo):
    """Previsión para la ventana: máximo en los dos extremos del trayecto.
    plazo: "" (corto plazo, day0) o "_previous_day1" (24 h antes)."""
    horas = horas_prevision(dia, ventana)
    r = {}
    for m in C.MODELOS_FINOS:
        clave = f"precipitation{plazo}_{m}"
        vs = [prev.get(h, {}).get(p, {}).get(clave) for h in horas for p in ("casa", "desti")]
        vs = [v for v in vs if v is not None]
        r[m] = max(vs) if vs else None
    cape = []
    for m in ("meteofrance_arome_france_hd", "icon_eu"):
        clave = f"cape{plazo}_{m}"
        cape += [prev.get(h, {}).get(p, {}).get(clave) for h in horas for p in ("casa", "desti")]
    cape = [v for v in cape if v is not None]
    r["cape"] = max(cape) if cape else None
    finos = [r[m] for m in C.MODELOS_FINOS if r[m] is not None]
    r["fino_max"] = max(finos) if finos else None
    return r


def tabla(obs, prev, ventana, plazo):
    filas = []
    dias = sorted({t.astimezone(LOCAL).date() for t in prev})
    for dia in dias:
        lluvia = lluvia_observada(obs, dia, ventana)
        r = rasgos(prev, dia, ventana, plazo)
        if lluvia is None or r["fino_max"] is None or r["cape"] is None:
            continue
        filas.append({"dia": dia, "lluvia": lluvia, "llueve": lluvia >= UMBRAL_LLUVIA, **r})
    return filas


# --- Regla actual ----------------------------------------------------------------

def nivel_regla(fino_max):
    if fino_max >= UMBRAL_MM_COCHE:
        return "cotxe"
    if fino_max >= C.UMBRAL_MM:
        return "compte"
    return "moto"


def contingencia(avisa, ocurre):
    avisa, ocurre = np.asarray(avisa), np.asarray(ocurre)
    aciertos = int((avisa & ocurre).sum())
    fallos = int((~avisa & ocurre).sum())
    falsas = int((avisa & ~ocurre).sum())
    return {
        "dias": len(avisa), "con_lluvia": int(ocurre.sum()),
        "avisa": int(avisa.sum()), "aciertos": aciertos, "fallos": fallos,
        "falsas_alarmas": falsas,
        "detecta": aciertos / max(aciertos + fallos, 1),
        "falsa_alarma": falsas / max(aciertos + falsas, 1),
    }


# --- Modelo calibrado ------------------------------------------------------------

def matriz(filas):
    x = []
    for f in filas:
        doy = f["dia"].timetuple().tm_yday
        x.append([1.0,
                  math.log1p(f["fino_max"]),
                  math.log1p(f["meteofrance_arome_france_hd"] or 0.0),
                  math.log1p(f["icon_eu"] or 0.0),
                  math.sqrt(f["cape"]) / 30,
                  math.sin(2 * math.pi * doy / 365.25),
                  math.cos(2 * math.pi * doy / 365.25)])
    return np.array(x)


NOMBRES = ["constante", "log1p(máximo modelos finos)", "log1p(AROME HD)",
           "log1p(ICON-EU)", "raíz(CAPE)/30", "sen(día del año)", "cos(día del año)"]


def validacion_cruzada(filas, pliegues=5):
    """Pliegues por meses enteros (mes % 5) para que días vecinos, muy
    parecidos entre sí, no caigan a la vez en ajuste y comprobación."""
    x = matriz(filas)
    y = np.array([f["llueve"] for f in filas], dtype=float)
    grupo = np.array([(f["dia"].year * 12 + f["dia"].month) % pliegues for f in filas])
    p_log = np.zeros(len(y))
    p_regla = np.zeros(len(y))
    p_clima = np.zeros(len(y))
    niveles = np.array([nivel_regla(f["fino_max"]) for f in filas])
    for g in range(pliegues):
        ent, prueba = grupo != g, grupo == g
        w = ajustar(x[ent], y[ent])
        p_log[prueba] = predecir(w, x[prueba])
        p_clima[prueba] = y[ent].mean()
        # La regla, convertida en probabilidad con la frecuencia de lluvia
        # observada en cada uno de sus tres niveles.
        for n in ("moto", "compte", "cotxe"):
            sel = ent & (niveles == n)
            frec = y[sel].mean() if sel.any() else y[ent].mean()
            p_regla[prueba & (niveles == n)] = frec
    return y, p_log, p_regla, p_clima, niveles


def brier(p, y):
    return float(np.mean((p - y) ** 2))


def fiabilidad(p, y, cortes=(0, .05, .1, .2, .3, .5, 1.01)):
    res = []
    for a, b in zip(cortes[:-1], cortes[1:]):
        sel = (p >= a) & (p < b)
        if sel.any():
            res.append((a, b, int(sel.sum()), float(p[sel].mean()), float(y[sel].mean())))
    return res


# --- Informe ---------------------------------------------------------------------

def pct(x):
    return f"{100 * x:.0f} %"


CLASES_PERSISTENCIA = [4.0, 1.0, 0.2]   # mm en la última hora, de más a menos


def persistencia(obs, horas=4):
    """Si ha llovido en una hora, probabilidad de que siga lloviendo (0,2 mm o
    más) 1, 2, 3 y 4 horas después, y lluvia mediana. Juntando las dos
    estaciones: lo usa la página de casa para las primeras horas, que los
    modelos pueden no ver."""
    res = {}
    for clase in CLASES_PERSISTENCIA:
        filas = {k: [] for k in range(1, horas + 1)}
        for serie in obs.values():
            por_hora = {}
            for t, mm in serie.items():
                h = t.replace(minute=0)
                por_hora[h] = por_hora.get(h, 0.0) + mm
            for h, mm in por_hora.items():
                if mm < clase:
                    continue
                for k in filas:
                    despues = por_hora.get(h + dt.timedelta(hours=k))
                    if despues is not None:
                        filas[k].append(despues)
        res[str(clase)] = {str(k): {"casos": len(v),
                                    "probabilitat": round(sum(x >= UMBRAL_LLUVIA for x in v) / len(v), 3),
                                    "mediana_mm": round(sorted(v)[len(v) // 2], 1)}
                           for k, v in filas.items() if v}
    return res


def analizar():
    obs, prev = leer_obs(), leer_prev()
    salida = {"version": 2, "generat": dt.date.today().isoformat(),
              "umbral_lluvia_mm": UMBRAL_LLUVIA, "ventanas": {}}
    lineas = ["# Calibración de la regla con datos reales", "",
              f"Generado el {dt.date.today().isoformat()} con `calibracio/analitza.py`.", "",
              "Lluvia en el trayecto: 0,2 mm o más en alguna media hora de la ventana en "
              "Sabadell (XF) o Sant Cugat (XV), del portal de datos abiertos de la Generalitat. "
              "Previsiones archivadas de Open-Meteo: «corto plazo» une las primeras horas de cada "
              "pasada del modelo; «24 h antes» es la previsión hecha un día antes.", ""]
    resumen_dia = {}
    for nombre, ventana in (("anada", ANADA), ("tornada", TORNADA)):
        for plazo, rotulo in (("", "corto plazo"), ("_previous_day1", "24 h antes")):
            filas = tabla(obs, prev, ventana, plazo)
            if not filas:
                continue
            y, p_log, p_regla, p_clima, niveles = validacion_cruzada(filas)
            ocurre = y.astype(bool)
            b_clima, b_regla, b_log = brier(p_clima, y), brier(p_regla, y), brier(p_log, y)
            lineas += [f"## {nombre.capitalize()} {ventana[0]}-{ventana[1]}, previsión a {rotulo}", "",
                       f"{len(filas)} días, del {filas[0]['dia']} al {filas[-1]['dia']}. "
                       f"Llovió en {int(y.sum())} ({pct(y.mean())}).", "",
                       "| | Días que avisa | Lluvias detectadas | Lluvias no avisadas | Avisos sin lluvia |",
                       "|---|---|---|---|---|"]
            for rot, avisa in (("Regla: cotxe (≥ 1 mm)", niveles == "cotxe"),
                               ("Regla: cotxe o compte (≥ 0,2 mm)", niveles != "moto"),
                               ("Calibrado: probabilidad ≥ 20 %", p_log >= .2),
                               ("Calibrado: probabilidad ≥ 30 %", p_log >= .3)):
                c = contingencia(avisa, ocurre)
                lineas.append(f"| {rot} | {c['avisa']} | {c['aciertos']} de {c['con_lluvia']} "
                              f"({pct(c['detecta'])}) | {c['fallos']} | {c['falsas_alarmas']} "
                              f"({pct(c['falsa_alarma'])} de los avisos) |")
            lineas += ["", "Error cuadrático de la probabilidad (Brier; menos es mejor), "
                       "comprobado en meses que no se usaron para ajustar:", "",
                       f"- Solo la frecuencia habitual de lluvia: {b_clima:.4f}",
                       f"- Regla actual: {b_regla:.4f} (mejora del {pct(1 - b_regla / b_clima)})",
                       f"- Calibrado: {b_log:.4f} (mejora del {pct(1 - b_log / b_clima)})", "",
                       "Fiabilidad del calibrado (si dice 30 %, ¿llueve el 30 % de las veces?):", "",
                       "| Probabilidad dada | Días | Media dada | Llovió |", "|---|---|---|---|"]
            for a, b, n, pm, fo in fiabilidad(p_log, y):
                lineas.append(f"| {pct(a)}–{pct(min(b, 1))} | {n} | {pct(pm)} | {pct(fo)} |")
            lineas.append("")
            lineas += ["Frecuencia real de lluvia según el nivel de la regla:", "",
                       "| Nivel | Días | Llovió |", "|---|---|---|"]
            for n in ("moto", "compte", "cotxe"):
                sel = niveles == n
                lineas.append(f"| {n} | {int(sel.sum())} | {int(y[sel].sum())} ({pct(y[sel].mean())}) |")
            lineas.append("")
            if plazo == "":
                salida["ventanas"][nombre] = {
                    "desde": filas[0]["dia"].isoformat(), "fins": filas[-1]["dia"].isoformat(),
                    "nivells": {n: {"dies": int((niveles == n).sum()),
                                    "pluja": int(y[niveles == n].sum())}
                                for n in ("moto", "compte", "cotxe")}}
                resumen_dia[nombre] = {f["dia"]: (f["llueve"], niveles[i], p_log[i])
                                       for i, f in enumerate(filas)}
    # Un solo medio para el día: manda el peor de los dos trayectos.
    comunes = sorted(set(resumen_dia.get("anada", {})) & set(resumen_dia.get("tornada", {})))
    if comunes:
        orden = ["moto", "compte", "cotxe"]
        llueve = np.array([resumen_dia["anada"][d][0] or resumen_dia["tornada"][d][0] for d in comunes])
        regla = np.array([max(resumen_dia["anada"][d][1], resumen_dia["tornada"][d][1],
                              key=orden.index) for d in comunes])
        p_ida = np.array([resumen_dia["anada"][d][2] for d in comunes])
        p_vta = np.array([resumen_dia["tornada"][d][2] for d in comunes])
        lineas += ["## El día entero (un solo medio), previsión a corto plazo", "",
                   f"{len(comunes)} días. Llovió en algún trayecto en {int(llueve.sum())} "
                   f"({pct(llueve.mean())}).", "",
                   "| | Días de coche | Días de lluvia con coche | Días de lluvia en moto | Coche sin lluvia |",
                   "|---|---|---|---|---|"]
        for rot, coche in (("Regla actual (cotxe)", regla == "cotxe"),
                           ("Regla actual (cotxe o compte)", regla != "moto"),
                           ("Calibrado ≥ 20 % en algún trayecto", np.maximum(p_ida, p_vta) >= .2),
                           ("Calibrado ≥ 30 % en algún trayecto", np.maximum(p_ida, p_vta) >= .3)):
            c = contingencia(coche, llueve)
            lineas.append(f"| {rot} | {c['avisa']} | {c['aciertos']} | {c['fallos']} | "
                          f"{c['falsas_alarmas']} |")
        lineas.append("")
    salida["persistencia"] = persistencia(obs)
    lineas += ["## Persistencia de la lluvia", "",
               "Si en una hora ha llovido al menos lo que dice la fila, cuántas veces siguió "
               "lloviendo (0,2 mm o más) en las horas siguientes, en Sabadell y Sant Cugat juntas:", "",
               "| Última hora | +1 h | +2 h | +3 h | +4 h |", "|---|---|---|---|---|"]
    for clase, dato in salida["persistencia"].items():
        lineas.append(f"| ≥ {clase.replace('.', ',')} mm | " + " | ".join(
            f"{pct(dato[k]['probabilitat'])} ({dato[k]['casos']})" for k in sorted(dato)) + " |")
    lineas.append("")
    with open(os.path.join(AQUI, "informe.md"), "w") as f:
        f.write("\n".join(lineas))
    with open(os.path.join(AQUI, "calibracio.json"), "w") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    print("\n".join(lineas))


if __name__ == "__main__":
    analizar()
