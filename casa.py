#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""El tiempo en casa (Montflorit): lo que mide ahora la estación y la
previsión hora a hora para las próximas 24 horas.

Uso: python3 casa.py --json web/casa.json
"""
import datetime as dt
import json
import sys
import urllib.parse

import config as C
import prevision as P

HORAS = 24


def ahora_montflorit():
    """Últimos valores de la estación de Montflorit (meteocerdanyola.com)."""
    slug = next(iter(C.ESTACIONES_LOCALES))
    filas = json.loads(P.get(P.METEOCERDANYOLA.format(slug))).get("rows", [])
    filas = [f for f in filas if f.get("TEMP") is not None]
    if not filas:
        return None
    u = filas[-1]
    resumen = P.resumen_minutal(filas, C.ESTACIONES_LOCALES[slug], "meteocerdanyola.com")
    return {"hora": dt.datetime.fromisoformat(u["dt_local"]).astimezone().isoformat(),
            "temperatura": u.get("TEMP"), "humitat": u.get("HUM"),
            "vent": u.get("VEL"), "pluja_avui": u.get("PREC"),
            "pluja_30min": resumen["mm_ultima_media_hora"] if resumen else None,
            "intensitat": u.get("PINT")}


def previsio(desde):
    """Una fila por hora, de la hora actual a 24 horas después."""
    dias = [desde.date().isoformat(), (desde + dt.timedelta(days=2)).date().isoformat()]
    q = urllib.parse.urlencode({
        "latitude": C.CASA[0], "longitude": C.CASA[1],
        "hourly": "temperature_2m,precipitation,weather_code,cloud_cover,"
                  "wind_speed_10m,wind_gusts_10m,relative_humidity_2m",
        "models": "meteofrance_seamless," + ",".join(C.MODELOS_FINOS),
        "timezone": P.TZ, "start_date": dias[0], "end_date": dias[1]})
    h = json.loads(P.get(f"https://api.open-meteo.com/v1/forecast?{q}"))["hourly"]
    q = urllib.parse.urlencode({
        "latitude": C.CASA[0], "longitude": C.CASA[1], "hourly": "precipitation",
        "models": C.ENSEMBLE, "timezone": P.TZ, "start_date": dias[0], "end_date": dias[1]})
    e = json.loads(P.get(f"https://ensemble-api.open-meteo.com/v1/ensemble?{q}"))["hourly"]
    miembros = [k for k in e if k.startswith("precipitation")]
    prob = {t: sum((e[k][i] or 0) >= C.UMBRAL_MM for k in miembros) / len(miembros)
            for i, t in enumerate(e["time"])} if miembros else {}

    def valor(campo, i):
        return h.get(f"{campo}_meteofrance_seamless", [None] * (i + 1))[i]

    # Cada fila es un tramo de una hora («de 10 a 11»). Open-Meteo da la lluvia
    # acumulada en la hora anterior, así que el tramo de 10 a 11 se lee en la
    # hora 11:00; los demás valores, también los de esa hora.
    primera = desde.replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1)
    fin_tramo = primera.strftime("%Y-%m-%dT%H:%M")
    filas = []
    for i, t in enumerate(h["time"]):
        if t < fin_tramo or len(filas) >= HORAS:
            continue
        lluvias = [h.get(f"precipitation_{m}", [None] * (i + 1))[i] for m in C.MODELOS_FINOS]
        lluvias = [v for v in lluvias if v is not None] or [valor("precipitation", i) or 0.0]
        inicio_tramo = (dt.datetime.fromisoformat(t) - dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
        filas.append({
            "hora": inicio_tramo, "fins": t, "temperatura": valor("temperature_2m", i),
            "pluja_mm": round(max(lluvias), 1),
            "probabilitat": round(prob[t], 2) if t in prob else None,
            "nuvols": valor("cloud_cover", i), "codi": valor("weather_code", i),
            "vent": valor("wind_speed_10m", i), "ratxa": valor("wind_gusts_10m", i),
            "humitat": valor("relative_humidity_2m", i)})
    return filas


def recoger():
    salida = {"versio": C.VERSION, "generat": P.AHORA.isoformat(timespec="minutes"),
              "horari": {"trams": [C.HORARIO_CASA], "cada_min": C.INTERVALO_CASA_MIN},
              "errors": []}
    for clave, funcion in (("ara", ahora_montflorit), ("hores", lambda: previsio(P.AHORA)),
                           ("avisos", P.avisos)):
        try:
            salida[clave] = funcion()
        except Exception as ex:
            salida[clave] = None
            salida["errors"].append(f"{clave}: {ex}")
    if salida["avisos"]:
        salida["avisos"] = [a for a in salida["avisos"] if a["zona"] == C.ZONA_TRAYECTO
                            and dt.datetime.fromisoformat(a["fin"]) > P.AHORA]
    return salida


if __name__ == "__main__":
    datos = recoger()
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
    print(f"Generado {datos['generat']}", datos["errors"] or "")
    print("Ahora:", datos["ara"])
    for f in datos["hores"] or []:
        print(f["hora"][11:16], f["temperatura"], "°C", f["pluja_mm"], "mm",
              f["probabilitat"], f["codi"], f["vent"], f["ratxa"])
