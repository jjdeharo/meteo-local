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

import aprenentatge as A
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


def variables_hora(desde, h, prob, i, ara):
    """Lo que dan los modelos para la hora que acaba en h["time"][i]: lo que
    usa el modelo aprendido y lo que se guarda en el registro."""
    t = h["time"][i]
    fin = dt.datetime.fromisoformat(t).astimezone()
    d = {"fins": t, "antelacio_h": round((fin - desde).total_seconds() / 3600, 2),
         "prob_ens": prob.get(t)}
    for m in C.MODELOS_FINOS:
        d[f"pluja_{m}"] = h.get(f"precipitation_{m}", [None] * (i + 1))[i]
    for campo in ("temperature_2m", "relative_humidity_2m", "cloud_cover",
                  "wind_speed_10m", "wind_gusts_10m", "weather_code"):
        d[campo] = h.get(f"{campo}_meteofrance_seamless", [None] * (i + 1))[i]
    d["pluja_1h_emes"] = (ara or {}).get("pluja_1h")
    return d


def previsio(desde, h, e, ara, avisos, model=None):
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
        d = variables_hora(desde, h, prob, i, ara)
        # Probabilidad aprendida con lo que llovió de verdad; sin modelo, la
        # fracción del ensemble.
        p = A.prob_pluja(model, d)
        if p is None:
            p = prob.get(t)
        mm = round(lluvia_modelos(h, i), 1)
        temp = A.temperatura(model, d)
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
            "temperatura": None if temp is None else round(temp, 1),
            "pluja_mm": round(mm, 1), "probabilitat": round(p, 2) if p is not None else None,
            "plou_ara": plou_ara, "segons_estacio": segun_estacion,
            "avisos": avisos_del_tramo(ini, fin, avisos),
            "nuvols": valor("cloud_cover", i), "codi": valor("weather_code", i),
            "vent": valor("wind_speed_10m", i), "ratxa": valor("wind_gusts_10m", i)})
    return filas


def filas_registro(desde, h, e, ara, mostradas):
    """Todo lo que los modelos daban para cada hora de la tabla, junto a lo que
    mostró la página: lo que hace falta para aprender de los fallos (ADR 0012)."""
    prob = prob_ensemble(e)
    indice = {t: i for i, t in enumerate(h["time"])}
    filas = []
    for f in mostradas:
        d = variables_hora(desde, h, prob, indice[f["fins"]], ara)
        d.pop("pluja_1h_emes")      # ya va en «ara», una vez por línea
        d["mostrat"] = {"pluja_mm": f["pluja_mm"], "probabilitat": f["probabilitat"],
                        "temperatura": f["temperatura"], "segons_estacio": f["segons_estacio"]}
        filas.append(d)
    return filas


def nivel_hora(f, planes):
    """Riesgo de lluvia de una hora de la tabla y su motivo, con los umbrales del
    trayecto: plan de Protección Civil activado, aviso de AEMET, lluvia ahora,
    1 mm o 50 %, coche; 0,2 mm o 20 %, moto con impermeable."""
    p, mm = f.get("probabilitat") or 0, f.get("pluja_mm") or 0
    pluja = f"pluja {round(p * 100)}\u00a0%"
    plan = next((x for x in planes or [] if x["fase"] in ("alerta", "emergència")), None)
    if plan:
        return "cotxe", f"Protecció Civil en {plan['fase']}"
    if f.get("avisos"):
        a = f["avisos"][0]
        return "cotxe", f"avís {a['nivell']} de l\u2019AEMET"
    if f.get("plou_ara"):
        return "cotxe", "plou ara"
    if p >= C.PROB_COCHE or mm >= C.UMBRAL_MM_COCHE:
        return "cotxe", pluja
    if p >= C.PROB_ATENCION or mm >= C.UMBRAL_MM:
        return "compte", pluja
    return "moto", pluja


def canvis(tramo):
    """Cómo cambia el tiempo entre la salida y la vuelta: si empieza o para de
    llover y si la temperatura cambia mucho."""
    res = []
    moja = [f["probabilitat"] is not None and f["probabilitat"] >= C.PROB_ATENCION
            or (f["pluja_mm"] or 0) >= C.UMBRAL_MM or f.get("plou_ara") for f in tramo]
    if not moja[0] and any(moja):
        f = tramo[moja.index(True)]
        res.append(f"A partir de les {int(f['hora'][11:13])}\u00a0h, pluja probable"
                   + (f" ({round(f['probabilitat'] * 100)}\u00a0%)." if f["probabilitat"] is not None else "."))
    elif moja[0] and not all(moja):
        f = tramo[moja.index(False)]
        res.append(f"Cap a les {int(f['hora'][11:13])}\u00a0h deixa de ploure.")
    temps = [(f["temperatura"], f["hora"]) for f in tramo if f["temperatura"] is not None]
    if temps:
        (t_min, h_min), (t_max, h_max) = min(temps), max(temps)
        if t_max - t_min >= C.SALIDA_CAMBIO_TEMPERATURA:
            res.append(f"La temperatura va de {P.graus(round(t_min))} ({int(h_min[11:13])}\u00a0h) "
                       f"a {P.graus(round(t_max))} ({int(h_max[11:13])}\u00a0h).")
    return res


def sortides(hores, planes):
    """Para quien sale ahora, fuera de las franjas del trayecto: medio, ropa y
    cambios para cada hora de vuelta posible (ADR 0014). El medio sale de las
    dos horas en que se circula, la de salir y la de volver. Se calcula con la
    salida en la hora en curso y en la siguiente: la página usa la que coincide
    con su hora, aunque los datos sean de la hora anterior."""
    res = []
    for k in (0, 1):
        if len(hores) < k + 2:
            break
        ida = hores[k]
        tornades = []
        for j in range(k + 1, len(hores)):
            vuelta = hores[j]
            (niv_ida, mot_ida), (niv_vuelta, mot_vuelta) = nivel_hora(ida, planes), nivel_hora(vuelta, planes)
            mitja = P.peor(niv_ida, niv_vuelta)
            temps = [{"temps": {"temp_min": round(f["temperatura"]), "temp_max": round(f["temperatura"])}}
                     if f["temperatura"] is not None else {} for f in (ida, vuelta)]
            tornades.append({
                "hora": vuelta["hora"], "mitja": mitja,
                "anada": {"nivell": niv_ida, "motiu": mot_ida},
                "tornada": {"nivell": niv_vuelta, "motiu": mot_vuelta},
                "roba": P.roba(mitja, *temps), "canvis": canvis(hores[k:j + 1])})
        res.append({"surt": ida["hora"], "tornades": tornades})
    return res


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
        model = A.carrega()
        salida["aprenentatge"] = A.resum_pagina(model)
        salida["hores"] = previsio(P.AHORA, h, e, ara, avisos, model)
        salida["sortides"] = sortides(salida["hores"], planes)
        salida["sortida_per_defecte_h"] = C.SALIDA_VUELTA_POR_DEFECTO_H
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
                R.apunta_casa(P.AHORA, ara, filas_registro(P.AHORA, h, e, ara, salida["hores"]))
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
