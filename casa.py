#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""El tiempo en casa (Montflorit): lo que mide ahora la estación y la
previsión hora a hora para las próximas 24 horas.

Los modelos pueden no ver un episodio (el 05-10-2026 daban 0,3 mm por hora
mientras caían más de 20 mm/h y había alerta de Protección Civil). Por eso:
- las primeras horas parten de la lluvia que mide la estación, con la
  persistencia real de la lluvia en Sabadell y Sant Cugat (calibracio.json);
- si los modelos se han quedado muy cortos en las últimas horas, se dice;
- cada hora lleva los avisos de AEMET y los planes de Protección Civil que la
  cubren.

Uso: python3 casa.py --json web/casa.json
"""
import datetime as dt
import json
import sys
import urllib.parse

import config as C
import prevision as P
import registre as R

HORAS = 24
HORAS_PERSISTENCIA = 4      # las que tiene la tabla de calibracio.json
HORAS_COMPROBACION = 3      # últimas horas en que se comparan modelos y estación


def lluvia_entre(filas, ini, fin):
    """mm medidos entre ini y fin con el acumulado diario minuto a minuto."""
    mm = 0.0
    for antes, despues in zip(filas, filas[1:]):
        t = dt.datetime.fromisoformat(despues["dt_local"]).astimezone()
        if ini < t <= fin:
            salto = despues["PREC"] - antes["PREC"]
            mm += despues["PREC"] if salto < 0 else salto
    return round(mm, 1)


def montflorit():
    """Filas minuto a minuto de la estación y el resumen de ahora."""
    slug = next(iter(C.ESTACIONES_LOCALES))
    filas = json.loads(P.get(P.METEOCERDANYOLA.format(slug))).get("rows", [])
    filas = [f for f in filas if f.get("PREC") is not None]
    if not filas:
        return [], None
    u = filas[-1]
    hora = dt.datetime.fromisoformat(u["dt_local"]).astimezone()
    ara = {"hora": hora.isoformat(), "temperatura": u.get("TEMP"), "humitat": u.get("HUM"),
           "vent": u.get("VEL"), "pluja_avui": u.get("PREC"),
           "pluja_30min": lluvia_entre(filas, hora - dt.timedelta(minutes=30), hora),
           "pluja_1h": lluvia_entre(filas, hora - dt.timedelta(hours=1), hora),
           "intensitat": u.get("PINT")}
    return filas, ara


def modelos(desde):
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
    return h, e


def lluvia_modelos(h, i):
    """Lluvia de la hora i: la mayor de los modelos finos."""
    v = [h.get(f"precipitation_{m}", [None] * (i + 1))[i] for m in C.MODELOS_FINOS]
    v = [x for x in v if x is not None]
    return max(v) if v else (h.get("precipitation_meteofrance_seamless", [0] * (i + 1))[i] or 0.0)


def persistencia(mm_ultima_hora, k):
    """Probabilidad y lluvia mediana k horas después de una hora con esa
    lluvia, según el histórico (None si no ha llovido)."""
    tabla = P.CALIBRACION_COMPLETA.get("persistencia", {})
    for clase in sorted(tabla, key=float, reverse=True):
        if mm_ultima_hora >= float(clase):
            return tabla[clase].get(str(k))
    return None


def avisos_del_tramo(ini, fin, avisos):
    """Avisos de AEMET que cubren el tramo. Los planes de Protección Civil no
    tienen hora de fin: van en un aviso aparte, encima de la tabla."""
    res = {}
    for a in avisos or []:
        a_ini, a_fin = (dt.datetime.fromisoformat(a[k]) for k in ("inicio", "fin"))
        if a["zona"] == C.ZONA_TRAYECTO and a_ini < fin and a_fin > ini:
            res.setdefault(a["nivel"], set()).add(a["tipo"])
    return [{"nivell": n, "tipus": sorted(t)} for n, t in res.items()]


def prob_ensemble(e):
    """Fracción de miembros del ensemble con lluvia, por hora."""
    miembros = [k for k in e if k.startswith("precipitation")]
    if not miembros:
        return {}
    return {t: sum((e[k][i] or 0) >= C.UMBRAL_MM for k in miembros) / len(miembros)
            for i, t in enumerate(e["time"])}


def previsio(desde, h, e, ara, avisos):
    """Una fila por tramo de una hora («de 10 a 11»), de la hora actual a 24
    horas después. Open-Meteo da la lluvia acumulada en la hora anterior: el
    tramo de 10 a 11 se lee en la hora 11:00, y los demás valores también."""
    prob = prob_ensemble(e)
    llueve_ahora = bool(ara) and ((ara.get("intensitat") or 0) > 0 or (ara.get("pluja_30min") or 0) > 0)
    ultima_hora = (ara or {}).get("pluja_1h") or 0.0

    def valor(campo, i):
        return h.get(f"{campo}_meteofrance_seamless", [None] * (i + 1))[i]

    primera = desde.replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1)
    filas = []
    for i, t in enumerate(h["time"]):
        if t < primera.strftime("%Y-%m-%dT%H:%M") or len(filas) >= HORAS:
            continue
        fin = dt.datetime.fromisoformat(t).astimezone()
        ini = fin - dt.timedelta(hours=1)
        n = len(filas)
        mm, p = round(lluvia_modelos(h, i), 1), prob.get(t)
        segun_estacion = False
        # Primeras horas: la persistencia de la lluvia que mide ahora la
        # estación, si da más que los modelos.
        dato = persistencia(ultima_hora, n + 1) if n < HORAS_PERSISTENCIA else None
        if dato:
            if p is None or dato["probabilitat"] > p:
                p, segun_estacion = dato["probabilitat"], True
            if dato["mediana_mm"] > mm:
                mm, segun_estacion = dato["mediana_mm"], True
        plou_ara = n == 0 and llueve_ahora
        if plou_ara:
            p, segun_estacion = 1.0, True
        filas.append({
            "hora": ini.strftime("%Y-%m-%dT%H:%M"), "fins": t,
            "temperatura": valor("temperature_2m", i),
            "pluja_mm": round(mm, 1), "probabilitat": round(p, 2) if p is not None else None,
            "plou_ara": plou_ara, "segons_estacio": segun_estacion,
            "avisos": avisos_del_tramo(ini, fin, avisos),
            "nuvols": valor("cloud_cover", i), "codi": valor("weather_code", i),
            "vent": valor("wind_speed_10m", i), "ratxa": valor("wind_gusts_10m", i)})
    return filas


def filas_registro(desde, h, e, mostradas):
    """Todo lo que los modelos daban para cada hora de la tabla, junto a lo que
    mostró la página: lo que hace falta para aprender de los fallos (ADR 0012)."""
    prob = prob_ensemble(e)
    indice = {t: i for i, t in enumerate(h["time"])}
    filas = []
    for f in mostradas:
        i = indice[f["fins"]]
        fin = dt.datetime.fromisoformat(f["fins"]).astimezone()
        fila = {"fins": f["fins"], "antelacio_h": round((fin - desde).total_seconds() / 3600, 2),
                "prob_ens": prob.get(f["fins"])}
        for m in C.MODELOS_FINOS:
            fila[f"pluja_{m}"] = h.get(f"precipitation_{m}", [None] * (i + 1))[i]
        for campo in ("temperature_2m", "relative_humidity_2m", "cloud_cover",
                      "wind_speed_10m", "wind_gusts_10m", "weather_code"):
            fila[campo] = h.get(f"{campo}_meteofrance_seamless", [None] * (i + 1))[i]
        fila["mostrat"] = {"pluja_mm": f["pluja_mm"], "probabilitat": f["probabilitat"],
                           "temperatura": f["temperatura"], "segons_estacio": f["segons_estacio"]}
        filas.append(fila)
    return filas


def comprobacion_modelos(desde, h, filas_estacion):
    """Lluvia medida y prevista en las últimas horas completas. Si los modelos
    se han quedado muy cortos, la página lo dice."""
    if not filas_estacion:
        return None
    fin = desde.replace(minute=0, second=0, microsecond=0)
    ini = fin - dt.timedelta(hours=HORAS_COMPROBACION)
    medida = lluvia_entre(filas_estacion, ini, fin)
    prevista = 0.0
    for i, t in enumerate(h["time"]):
        tt = dt.datetime.fromisoformat(t).astimezone()
        if ini < tt <= fin:
            prevista += lluvia_modelos(h, i)
    fallan = medida >= 3 and medida > 3 * prevista + 1
    return {"hores": HORAS_COMPROBACION, "mesurada_mm": round(medida, 1),
            "prevista_mm": round(prevista, 1), "no_encerten": fallan}


def recoger():
    salida = {"versio": C.VERSION, "generat": P.AHORA.isoformat(timespec="minutes"),
              "errors": []}
    filas_estacion, ara = [], None
    try:
        filas_estacion, ara = montflorit()
    except Exception as ex:
        salida["errors"].append(f"estació: {ex}")
    salida["ara"] = ara
    avisos = planes = None
    try:
        avisos = [a for a in P.avisos() if a["zona"] == C.ZONA_TRAYECTO
                  and dt.datetime.fromisoformat(a["fin"]) > P.AHORA]
    except Exception as ex:
        salida["errors"].append(f"avisos: {ex}")
    try:
        planes = P.planes_proteccion_civil()
    except Exception as ex:
        salida["errors"].append(f"plans: {ex}")
    salida["avisos"], salida["plans"] = avisos, planes
    radar = None
    try:
        radar = P.radar()
    except Exception as ex:
        salida["errors"].append(f"radar: {ex}")
    obs = [{"intensitat": ara.get("intensitat"), "mm_ultima_media_hora": ara.get("pluja_30min")}] if ara else []
    motivos = P.motivos_modo_aviso(avisos, planes, obs, radar)
    # En modo aviso, todo el día: hasta las 23:50, no solo hasta las 23:00.
    salida["horari"] = P.horario([C.HORARIO_CASA_AVISO if motivos else C.HORARIO_CASA],
                                 C.INTERVALO_CASA_MIN, motivos)
    try:
        h, e = modelos(P.AHORA)
        salida["hores"] = previsio(P.AHORA, h, e, ara, avisos)
        salida["models"] = comprobacion_modelos(P.AHORA, h, filas_estacion)
    except Exception as ex:
        salida["hores"] = salida["models"] = None
        salida["errors"].append(f"previsió: {ex}")
    # Registro para aprender (solo en el NAS, que tiene /estat): lo que medía
    # Montflorit y, una vez por hora, lo que daban los modelos.
    if R.hay_registro():
        try:
            R.apunta_montflorit(filas_estacion)
            if salida["hores"]:
                R.apunta_casa(P.AHORA, ara, filas_registro(P.AHORA, h, e, salida["hores"]))
        except Exception as ex:
            print("No he podido apuntar en el registro:", ex, file=sys.stderr)
    return salida


if __name__ == "__main__":
    datos = recoger()
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
    print(f"Generado {datos['generat']}", datos["errors"] or "")
    print("Ahora:", datos["ara"])
    print("Modelos:", datos["models"])
    print("Planes:", datos["plans"])
    for f in (datos["hores"] or [])[:8]:
        print(f["hora"][11:16], f["temperatura"], "°C", f["pluja_mm"], "mm", f["probabilitat"],
              "estació" if f["segons_estacio"] else "", "PLOU ARA" if f["plou_ara"] else "",
              f["avisos"])
