#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Registro en el NAS de lo medido, para aprender con datos (ADR 0006 y 0012).

Lo ejecuta el reloj del NAS, sin IA:

  python3 registre.py estacio             rellena las horas que falten de la
                                          estación de casa con su historial
  python3 registre.py rehaz-pluja-casa    vuelve a calcular su lluvia por horas
                                          con el historial (ADR 0017)

Además, casa.py apunta en cada pasada lo que mide Montflorit hora a hora
(montflorit.csv) y la estación de casa (estacio-casa.csv, ADR 0017) y, una vez
por hora, lo que daban los modelos para las 24 horas siguientes
(casa-AAAA-MM.jsonl), para aprender de los fallos (ADR 0012).

Los datos van a REGISTRE_DIR (en el NAS, /estat/registre), no al repositorio.
"""
import csv
import datetime as dt
import json
import os
import sys

import ecowitt as E
import prevision as P

DIR = os.environ.get("REGISTRE_DIR", "/estat/registre")


# --- Página de casa: previsiones y lo que pasó -----------------------------------

MONTFLORIT = os.path.join(DIR, "montflorit.csv")
CAMPOS_MONTFLORIT = ["fins", "pluja_mm", "temperatura", "humitat", "lectures"]
CASA_DARRERA = os.path.join(DIR, "casa-darrera")


def hay_registro():
    """El registro vive en el NAS (/estat); en un ordenador no se apunta nada."""
    return os.path.isdir(os.path.dirname(DIR))


def horas_montflorit(filas):
    """Horas completas de los datos minuto a minuto: la lluvia de la hora que
    acaba en «fins» y la temperatura y la humedad de la lectura más cercana a
    la hora en punto (a 5 minutos como mucho; la estación se salta minutos)."""
    if not filas:
        return {}
    por_hora, cerca = {}, {}
    for antes, despues in zip(filas, filas[1:]):
        t = dt.datetime.fromisoformat(despues["dt_local"])
        fin = t.replace(minute=0, second=0) + (dt.timedelta(hours=1) if t.minute or t.second else dt.timedelta())
        salto = despues["PREC"] - antes["PREC"]
        h = por_hora.setdefault(fin, {"pluja_mm": 0.0, "lectures": 0})
        h["pluja_mm"] += despues["PREC"] if salto < 0 else salto
        h["lectures"] += 1
    for f in filas:
        t = dt.datetime.fromisoformat(f["dt_local"])
        marca = (t + dt.timedelta(minutes=30)).replace(minute=0, second=0)
        dist = abs((t - marca).total_seconds())
        if dist <= 300 and f.get("TEMP") is not None and dist < cerca.get(marca, (999, None))[0]:
            cerca[marca] = (dist, f)
    ultima = dt.datetime.fromisoformat(filas[-1]["dt_local"])
    primera = dt.datetime.fromisoformat(filas[0]["dt_local"])
    res = {}
    # Solo las horas enteras: ni la que está en curso ni la primera, cortada.
    for fin, h in por_hora.items():
        if fin <= ultima and fin - dt.timedelta(hours=1) >= primera:
            f = cerca.get(fin, (None, {}))[1]
            res[fin] = {**h, "temperatura": f.get("TEMP"), "humitat": f.get("HUM")}
    return res


def apunta_montflorit(filas):
    nuevas = horas_montflorit(filas)
    if not nuevas:
        return
    os.makedirs(DIR, exist_ok=True)
    guardadas = {}
    if os.path.exists(MONTFLORIT):
        with open(MONTFLORIT, encoding="utf-8") as f:
            guardadas = {r["fins"]: r for r in csv.DictReader(f)}
    for fin, h in nuevas.items():
        guardadas[fin.strftime("%Y-%m-%dT%H:%M")] = {
            "fins": fin.strftime("%Y-%m-%dT%H:%M"), "pluja_mm": round(h["pluja_mm"], 1),
            "temperatura": h.get("temperatura"), "humitat": h.get("humitat"), "lectures": h["lectures"]}
    with open(MONTFLORIT + ".tmp", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_MONTFLORIT)
        w.writeheader()
        w.writerows(guardadas[k] for k in sorted(guardadas))
    os.replace(MONTFLORIT + ".tmp", MONTFLORIT)


# La lluvia de Montflorit cada 5 minutos, el paso del radar: para comprobar a
# qué hora para la lluvia que se ve encima (fi_pluja.py, ADR 0049). La
# estación solo ofrece las últimas 24 horas; aquí se van quedando.
MONTFLORIT_5MIN = os.path.join(DIR, "montflorit-5min.csv")
CAMPOS_MONTFLORIT_5MIN = ["fins", "pluja_mm"]


def cincs_montflorit(filas):
    """La lluvia de cada tramo completo de 5 minutos ({fin: mm}), de los datos
    minuto a minuto («PREC», acumulada del día)."""
    res = {}
    for antes, despues in zip(filas, filas[1:]):
        t = dt.datetime.fromisoformat(despues["dt_local"])
        # El tramo que acaba en «fin» va de fin - 5 min (sin incluir) a fin.
        base = t.replace(minute=t.minute - t.minute % 5, second=0, microsecond=0)
        fin = base if t == base else base + dt.timedelta(minutes=5)
        salto = despues["PREC"] - antes["PREC"]
        res[fin] = res.get(fin, 0.0) + (despues["PREC"] if salto < 0 else salto)
    if not filas:
        return {}
    primera = dt.datetime.fromisoformat(filas[0]["dt_local"])
    ultima = dt.datetime.fromisoformat(filas[-1]["dt_local"])
    return {fin: mm for fin, mm in res.items() if fin <= ultima and fin - dt.timedelta(minutes=5) >= primera}


def apunta_montflorit_5min(filas):
    nuevas = cincs_montflorit(filas)
    if not nuevas:
        return
    os.makedirs(DIR, exist_ok=True)
    guardadas = {}
    if os.path.exists(MONTFLORIT_5MIN):
        with open(MONTFLORIT_5MIN, encoding="utf-8") as f:
            guardadas = {r["fins"]: r for r in csv.DictReader(f)}
    for fin, mm in nuevas.items():
        clave = fin.strftime("%Y-%m-%dT%H:%M")
        guardadas[clave] = {"fins": clave, "pluja_mm": round(mm, 1)}
    with open(MONTFLORIT_5MIN + ".tmp", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_MONTFLORIT_5MIN)
        w.writeheader()
        w.writerows(guardadas[k] for k in sorted(guardadas))
    os.replace(MONTFLORIT_5MIN + ".tmp", MONTFLORIT_5MIN)


ESTACIO_CASA = os.path.join(DIR, "estacio-casa.csv")
CAMPOS_ESTACIO_CASA = ["fins", "pluja_mm", "temperatura", "humitat", "rosada", "pressio", "solar"]
# Cuánto se rellena hacia atrás como mucho: Ecowitt guarda 90 días cada 5 minutos.
ESTACIO_CASA_DIES_MAX = 89


def apunta_estacio_casa(nuevas):
    """Horas completas de la estación de casa ({fin: valores}, ecowitt.hores)."""
    nuevas = {fin: h for fin, h in nuevas.items() if h.get("temperatura") is not None
              or h.get("pluja_mm") is not None}
    if not nuevas:
        return
    os.makedirs(DIR, exist_ok=True)
    guardadas = {}
    if os.path.exists(ESTACIO_CASA):
        with open(ESTACIO_CASA, encoding="utf-8") as f:
            guardadas = {r["fins"]: r for r in csv.DictReader(f)}
    for fin, h in nuevas.items():
        clave = fin.strftime("%Y-%m-%dT%H:%M")
        guardadas[clave] = {"fins": clave, **{k: h.get(k) for k in CAMPOS_ESTACIO_CASA[1:]}}
    with open(ESTACIO_CASA + ".tmp", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_ESTACIO_CASA)
        w.writeheader()
        w.writerows(guardadas[k] for k in sorted(guardadas))
    os.replace(ESTACIO_CASA + ".tmp", ESTACIO_CASA)


def completa_estacio_casa(ahora=None):
    """Rellena con el historial de Ecowitt las horas que falten desde la
    última guardada (o desde el inicio del registro de casa), por si el NAS
    ha estado apagado. Una consulta por día que falte."""
    if not E.disponible():
        print("Sin claves de Ecowitt: no se rellena la estación de casa.")
        return
    ahora = ahora or P.AHORA
    desde = ahora - dt.timedelta(days=ESTACIO_CASA_DIES_MAX)
    if os.path.exists(ESTACIO_CASA):
        with open(ESTACIO_CASA, encoding="utf-8") as f:
            horas = [r["fins"] for r in csv.DictReader(f) if r["temperatura"]]
        if horas:
            desde = max(desde, dt.datetime.fromisoformat(horas[-1]).astimezone() - dt.timedelta(hours=2))
    else:
        desde = max(desde, ahora - dt.timedelta(days=2))
    apunta_estacio_casa(E.hores(E.historial(desde, ahora, "5min")))
    print("Estació de casa completada des de", desde.isoformat(timespec="minutes"))


def rehaz_pluja_casa(ahora=None):
    """Vuelve a calcular la lluvia de cada hora de estacio-casa.csv con el
    historial de Ecowitt (5 minutos, los últimos ESTACIO_CASA_DIES_MAX días).
    Hasta la 3.27.5 se guardaba la de la primera hora cortada de cada pasada
    encima de la buena (ADR 0017). Deja una copia del archivo de antes y solo
    cambia la lluvia."""
    ahora = ahora or P.AHORA
    if not os.path.exists(ESTACIO_CASA):
        return 0
    with open(ESTACIO_CASA, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    desde = max(ahora - dt.timedelta(days=ESTACIO_CASA_DIES_MAX),
                dt.datetime.fromisoformat(filas[0]["fins"]).astimezone() - dt.timedelta(hours=1))
    buenas = {fin.strftime("%Y-%m-%dT%H:%M"): h["pluja_mm"]
              for fin, h in E.hores(E.historial(desde, ahora, "5min")).items() if h["pluja_mm"] is not None}
    canvis = 0
    for r in filas:
        if r["fins"] in buenas and _num(r["pluja_mm"]) != buenas[r["fins"]]:
            r["pluja_mm"] = buenas[r["fins"]]
            canvis += 1
    if canvis:
        copia = f"{ESTACIO_CASA}.bak-pluja-{ahora:%Y%m%d%H%M}"
        os.replace(ESTACIO_CASA, copia)
        with open(ESTACIO_CASA + ".tmp", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS_ESTACIO_CASA)
            w.writeheader()
            w.writerows(filas)
        os.replace(ESTACIO_CASA + ".tmp", ESTACIO_CASA)
    return canvis


def _num(x):
    try:
        return round(float(x), 1)
    except (TypeError, ValueError):
        return None


def apunta_casa(emes, ara, hores, ara_casa=None, sant_cugat=None):
    """Una línea por hora de reloj: la primera pasada de cada hora. sant_cugat:
    la lluvia de la última hora en la estación de Meteocat de Sant Cugat, por
    si lo que llueve cerca ayuda a prever (ADR 0042)."""
    hora = emes.strftime("%Y-%m-%dT%H")
    if os.path.exists(CASA_DARRERA):
        with open(CASA_DARRERA) as f:
            if f.read().strip() == hora:
                return
    os.makedirs(DIR, exist_ok=True)
    linea = {"emes": emes.isoformat(timespec="minutes"), "ara": ara, "ara_casa": ara_casa, "hores": hores,
             "sant_cugat": sant_cugat}
    with open(os.path.join(DIR, f"casa-{emes.strftime('%Y-%m')}.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(linea, ensure_ascii=False) + "\n")
    with open(CASA_DARRERA, "w") as f:
        f.write(hora)


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else ""
    if orden == "estacio":
        completa_estacio_casa()
    elif orden == "rehaz-pluja-casa":
        print("Horas con la lluvia corregida:", rehaz_pluja_casa())
    else:
        print(__doc__)
