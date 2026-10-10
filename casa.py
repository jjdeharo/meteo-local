#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""El tiempo en casa (Montflorit): lo que mide ahora la estación de casa y
la previsión hora a hora para las próximas 24 horas.

Los modelos pueden no ver un episodio (el 05-10-2026 daban 0,3 mm por hora
mientras caían más de 20 mm/h y había alerta de Protección Civil). Por eso:
- las primeras horas parten de la lluvia que mide la estación, con la
  persistencia real de la lluvia en Sabadell y Sant Cugat (calibracio.json);
- si los modelos se han quedado muy cortos en las últimas horas, se dice;
- cada hora lleva los avisos de AEMET y los planes de Protección Civil que la
  cubren.

La estación de casa (ecowitt.py, ADR 0017) da la temperatura de ahora y, con
lo que se equivoca el modelo en este momento, corrige la de las horas
siguientes. Su lluvia solo cuenta cuando marca lluvia.

Si Open-Meteo falla, se reutiliza la última previsión buena (--anterior), con
las horas que aún no han pasado y los avisos y la lluvia de ahora (ADR 0016).

Uso: python3 casa.py --json web/casa.json [--anterior casa.json|URL]
"""
import datetime as dt
import json
import sys
import urllib.parse

import aire as AI
import aprenentatge as A
import config as C
import ecowitt as E
import entorn as EN
import fi_pluja as FP
import nowcast as N
import pollen as PO
import prevision as P
import radar_fonts as RF
import registre as R
import riera as RI
import riscos as RS
import transit as TT
import trens as TR
import wunderground as WU

HORAS = 24
# La tabla llega como mínimo a 24 horas y hasta las 21 h de mañana, para que
# mañana salga entero (la mañana y la tarde), y acaba siempre con un tramo del
# día (matí 7–14, tarda 14–21, nit 21–7: web/casa.js, ADR 0041). «Mañana» es
# el día siguiente al del tramo en curso: de madrugada, la noche aún es de
# ayer. Entre 24 y 38 filas (a las 7 h, hasta las 21 h de mañana). AROME llega
# a unas 40-45 horas; más allá, la lluvia es la de los otros modelos y la
# probabilidad, la del ensemble. Los riesgos y el registro siguen con las 24
# primeras.
FI_TRAMS = (7, 14, 21)
FI_DEMA = 21
HORAS_PERSISTENCIA = 4      # las que tiene la tabla de calibracio.json
# Una lectura de «ahora» con más de estos minutos no vale: un feed congelado
# no puede decir que llueve (o que no) durante horas.
ARA_MAX_MIN = 30
HORAS_COMPROBACION = 3      # últimas horas en que se comparan modelos y estación


def modelos(desde, errors=None):
    """Los modelos deterministas y, aparte, el ensemble: si solo falla el
    ensemble, la previsión sigue (la probabilidad sale del modelo aprendido
    sin él) y queda apuntado en errors."""
    dias = [desde.date().isoformat(), (desde + dt.timedelta(days=2)).date().isoformat()]
    q = urllib.parse.urlencode({
        "latitude": C.CASA[0], "longitude": C.CASA[1],
        "hourly": "temperature_2m,precipitation,weather_code,cloud_cover,"
                  "wind_speed_10m,wind_gusts_10m,relative_humidity_2m,shortwave_radiation,snowfall",
        "models": "meteofrance_seamless," + ",".join(C.MODELOS_FINOS),
        "timezone": P.TZ, "start_date": dias[0], "end_date": dias[1]})
    h = json.loads(P.get(f"https://api.open-meteo.com/v1/forecast?{q}"))["hourly"]
    q = urllib.parse.urlencode({
        "latitude": C.CASA[0], "longitude": C.CASA[1], "hourly": "precipitation",
        "models": C.ENSEMBLE, "timezone": P.TZ, "start_date": dias[0], "end_date": dias[1]})
    try:
        e = json.loads(P.get(f"https://ensemble-api.open-meteo.com/v1/ensemble?{q}"))["hourly"]
    except Exception as ex:
        if errors is None:
            raise
        errors.append(f"ensemble: {ex}")
        e = {}
    return h, e


def indice_uv(desde):
    """Índice UV por hora ({"AAAA-MM-DDTHH:MM": valor}) para la página «Si
    surts» (ADR 0029). Solo lo da el modelo por defecto de Open-Meteo: va en
    una consulta aparte, y si falla la página sigue sin él."""
    dias = [desde.date().isoformat(), (desde + dt.timedelta(days=2)).date().isoformat()]
    q = urllib.parse.urlencode({"latitude": C.CASA[0], "longitude": C.CASA[1], "hourly": "uv_index",
                                "timezone": P.TZ, "start_date": dias[0], "end_date": dias[1]})
    h = json.loads(P.get(f"https://api.open-meteo.com/v1/forecast?{q}"))["hourly"]
    return {t: v for t, v in zip(h["time"], h["uv_index"]) if v is not None}


def sol(desde):
    """Salida y puesta del sol e índice UV máximo de hoy y mañana, para
    «Consultes» y /sol (ADR 0054). Del modelo por defecto de Open-Meteo."""
    q = urllib.parse.urlencode({"latitude": C.CASA[0], "longitude": C.CASA[1], "timezone": P.TZ,
                                "daily": "sunrise,sunset,uv_index_max", "start_date": desde.date().isoformat(),
                                "end_date": (desde + dt.timedelta(days=1)).date().isoformat()})
    d = json.loads(P.get(f"https://api.open-meteo.com/v1/forecast?{q}"))["daily"]
    return [{"dia": t, "sortida": s, "posta": p, "uv_max": uv}
            for t, s, p, uv in zip(d["time"], d["sunrise"], d["sunset"], d["uv_index_max"])]


def estacio_casa():
    """Lo que mide ahora la estación de casa (None sin claves o si falla)."""
    if not E.disponible():
        return None
    casa = E.resum_ara()
    hora = dt.datetime.fromisoformat(casa["hora"])
    if P.AHORA - hora > dt.timedelta(minutes=ARA_MAX_MIN):
        raise RuntimeError(f"l'última lectura és de les {hora:%H:%M}")
    return casa


def llueve_ahora_en(casa, veines=None):
    """Llueve ahora: el pluviómetro de casa ha recogido lluvia en los últimos
    PLOU_ARA_MIN minutos (config.py), o lo ha hecho alguna de las estaciones
    vecinas de Weather Underground que cuentan (config.VEINES, ADR 0060).
    Solo cuenta el sí (ADR 0017)."""
    return bool(casa and casa.get("plou")) or WU.plou_a_les_veines(veines)


def temperatura_model_ara(h, ahora):
    """Temperatura del modelo en este momento, entre las dos horas en punto."""
    serie = h.get("temperature_2m_meteofrance_seamless") or []
    ini = ahora.replace(minute=0, second=0, microsecond=0)
    try:
        i = h["time"].index(ini.strftime("%Y-%m-%dT%H:%M"))
        a, b = serie[i], serie[i + 1]
    except (ValueError, IndexError):
        return None
    if a is None or b is None:
        return None
    return a + (b - a) * (ahora - ini).total_seconds() / 3600


def al_prever(desde, h, casa, riera=None):
    """Lo que medían las estaciones al prever y usa el aprendizaje: la lluvia
    de la última hora en casa, lo que se equivocaba el modelo
    de temperatura en casa, lo seco que estaba el aire y la lluvia de la
    última hora en Sant Cugat (la misma que guarda el registro, ADR 0042;
    hasta la auditoría del 09-10-2026 la variante se entrenaba con ella pero
    al prever no llegaba, y las primeras horas caían al modelo del archivo).
    Sin dato reciente de Sant Cugat (riera None: más de 2 horas), None, y
    esa variante usa el archivo en las primeras horas; el error «riera: …»
    de la pasada lo deja apuntado."""
    d = {"pluja_1h_emes": casa.get("pluja_1h") if casa else None,
         "error_temp_ara": None, "deficit_rosada_ara": None,
         "pluja_1h_xv": (riera or {}).get("mm_1h")}
    if casa and casa.get("temperatura") is not None:
        t_model = temperatura_model_ara(h, dt.datetime.fromisoformat(casa["hora"]))
        if t_model is not None:
            d["error_temp_ara"] = round(t_model - casa["temperatura"], 2)
        if casa.get("rosada") is not None:
            d["deficit_rosada_ara"] = round(casa["temperatura"] - casa["rosada"], 1)
    return d


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
        if a["zona"] == C.ZONA_AVISOS and a_ini < fin and a_fin > ini:
            res.setdefault(a["nivel"], set()).add(a["tipo"])
    return [{"nivell": n, "tipus": sorted(t)} for n, t in res.items()]


def senyals_avis(ini, fin, avisos, planes):
    """Lo que dice lo oficial de la hora, para que el modelo aprenda cuánto
    pesa (ADR 0047): si había aviso de AEMET por lluvia o tormentas y si el
    INUNCAT estaba en alerta o emergencia. None si no se pudieron leer."""
    tipus = {t for a in avisos_del_tramo(ini, fin, avisos) for t in a["tipus"]}
    return {"avis_pluja": None if avisos is None else float(bool(tipus & {"pluja", "tempestes"})),
            "pla_inuncat": None if planes is None else float(any(
                p["pla"] == "INUNCAT" and p["fase"] in ("alerta", "emergència") for p in planes))}


def prob_ensemble(e):
    """Fracción de miembros del ensemble con lluvia, por hora."""
    miembros = [k for k in e if k.startswith("precipitation")]
    if not miembros:
        return {}
    return {t: sum((e[k][i] or 0) >= C.UMBRAL_MM for k in miembros) / len(miembros)
            for i, t in enumerate(e["time"])}


def variables_hora(desde, h, prob, i, prever):
    """Lo que dan los modelos para la hora que acaba en h["time"][i] y lo que
    medían las estaciones al prever (al_prever): lo que usa el modelo
    aprendido y lo que se guarda en el registro."""
    t = h["time"][i]
    fin = dt.datetime.fromisoformat(t).astimezone()
    d = {"fins": t, "antelacio_h": round((fin - desde).total_seconds() / 3600, 2),
         "prob_ens": prob.get(t)}
    for m in C.MODELOS_FINOS:
        d[f"pluja_{m}"] = h.get(f"precipitation_{m}", [None] * (i + 1))[i]
    for campo in ("temperature_2m", "relative_humidity_2m", "cloud_cover",
                  "wind_speed_10m", "wind_gusts_10m", "weather_code", "shortwave_radiation"):
        d[campo] = h.get(f"{campo}_meteofrance_seamless", [None] * (i + 1))[i]
    d.update(prever or {})
    return d


def previsio(desde, h, e, avisos, model=None, casa=None, nc=None, planes=None, riera=None, veines=None):
    """Una fila por tramo de una hora («de 10 a 11»), de la hora actual a 24
    horas después como mínimo, hasta las 21 h de mañana y acabando un tramo
    del día (FI_TRAMS). Open-Meteo da la lluvia acumulada en la hora anterior: el
    tramo de 10 a 11 se lee en la hora 11:00, y los demás valores también."""
    prob = prob_ensemble(e)
    llueve_ahora = llueve_ahora_en(casa, veines)
    prever = al_prever(desde, h, casa, riera)
    ultima_hora = prever["pluja_1h_emes"] or 0.0

    def valor(campo, i):
        return h.get(f"{campo}_meteofrance_seamless", [None] * (i + 1))[i]

    primera = desde.replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1)
    dia = desde.date() - dt.timedelta(days=1 if desde.hour < FI_TRAMS[0] else 0)
    fi_dema = (dt.datetime.combine(dia + dt.timedelta(days=1), dt.time(FI_DEMA))).strftime("%Y-%m-%dT%H:%M")
    filas = []
    for i, t in enumerate(h["time"]):
        if t < primera.strftime("%Y-%m-%dT%H:%M"):
            continue
        if (len(filas) >= HORAS and filas[-1]["fins"] >= fi_dema
                and int(filas[-1]["fins"][11:13]) in FI_TRAMS):
            break
        fin = dt.datetime.fromisoformat(t).astimezone()
        ini = fin - dt.timedelta(hours=1)
        n = len(filas)
        d = variables_hora(desde, h, prob, i, prever)
        d.update(senyals_avis(ini, fin, avisos, planes))
        # Probabilidad aprendida con lo que llovió de verdad; sin modelo, la
        # fracción del ensemble.
        p = A.prob_pluja(model, d)
        if p is None:
            p = prob.get(t)
        mm = round(lluvia_modelos(h, i), 1)
        # La temperatura es la de un instante: la del tramo de 18 a 19, la media
        # de las 18 y las 19, las dos corregidas (la lluvia sí es la acumulada
        # hasta el final del tramo).
        temp = A.temperatura(model, d)
        if i > 0:
            antes = A.temperatura(model, variables_hora(desde, h, prob, i - 1, prever))
            if antes is not None and temp is not None:
                temp = (antes + temp) / 2
        segun_estacion = False
        # Primeras horas: la persistencia de la lluvia que mide ahora la
        # estación, si da más que los modelos.
        dato = persistencia(ultima_hora, n + 1) if n < HORAS_PERSISTENCIA else None
        if dato:
            if p is None or dato["probabilitat"] > p:
                p, segun_estacion = dato["probabilitat"], True
            if dato["mediana_mm"] > mm:
                mm, segun_estacion = dato["mediana_mm"], True
        # Primeras dos horas: la lluvia del radar llevada hacia delante (ADR
        # 0019), si da más. No rebaja nada: la lluvia que aún no ha nacido no
        # se ve en el radar.
        segun_radar = False
        # La probabilidad vale aunque el radar cubra solo una parte de la hora
        # (si llueve en ese rato, llueve en la hora); los mm, solo si cubre
        # media hora o más.
        radar = N.en_tram(nc, "casa", max(ini, desde), fin)
        if radar:
            if radar["prob"] > (p or 0) and radar["prob"] >= C.PROB_ATENCION:
                p, segun_radar = radar["prob"], True
            if radar["minuts"] >= 30 and radar["mm"] > mm and radar["mm"] >= C.UMBRAL_MM:
                mm, segun_radar = radar["mm"], True
        plou_ara = n == 0 and llueve_ahora
        if plou_ara:
            p, segun_estacion = 1.0, True
        filas.append({
            "hora": ini.strftime("%Y-%m-%dT%H:%M"), "fins": t,
            "temperatura": None if temp is None else round(temp, 1),
            "pluja_mm": round(mm, 1), "probabilitat": round(p, 2) if p is not None else None,
            "plou_ara": plou_ara, "segons_estacio": segun_estacion,
            "segons_radar": segun_radar and not plou_ara and not segun_estacion,
            "radar": radar,
            "avisos": avisos_del_tramo(ini, fin, avisos),
            "nuvols": valor("cloud_cover", i), "codi": valor("weather_code", i),
            "vent": valor("wind_speed_10m", i), "ratxa": valor("wind_gusts_10m", i),
            "neu": valor("snowfall", i)})
    return filas


def filas_registro(desde, h, e, mostradas, casa=None, avisos=None, planes=None, riera=None):
    """Todo lo que los modelos daban para cada hora de la tabla, junto a lo que
    mostró la página: lo que hace falta para aprender de los fallos (ADR 0012)."""
    prob = prob_ensemble(e)
    indice = {t: i for i, t in enumerate(h["time"])}
    prever = al_prever(desde, h, casa, riera)
    filas = []
    for f in mostradas:
        d = variables_hora(desde, h, prob, indice[f["fins"]], prever)
        d.pop("pluja_1h_emes")      # ya va en «ara_casa», una vez por línea
        d.pop("pluja_1h_xv", None)  # ya va en «sant_cugat», una vez por línea
        fin = dt.datetime.fromisoformat(f["fins"]).astimezone()
        d.update(senyals_avis(fin - dt.timedelta(hours=1), fin, avisos, planes))
        # «plou_ara», para saber qué veredicto dio «Si surts» (ADR 0047).
        d["mostrat"] = {"pluja_mm": f["pluja_mm"], "probabilitat": f["probabilitat"],
                        "temperatura": f["temperatura"], "segons_estacio": f["segons_estacio"],
                        "segons_radar": f.get("segons_radar", False), "plou_ara": f.get("plou_ara", False)}
        # Lo que daba el radar llevado hacia delante, para aprender (ADR 0019).
        d["radar_mm"] = (f.get("radar") or {}).get("mm")
        d["radar_prob"] = (f.get("radar") or {}).get("prob")
        filas.append(d)
    return filas


def previsio_anterior(origen, avisos, casa=None, veines=None):
    """Las horas que aún no han pasado de la última previsión buena, con los
    avisos y la lluvia de ahora. None si no la hay o tiene más de
    CASA_PREVISION_ANTERIOR_MAX_H horas."""
    if not origen:
        return None
    try:
        if origen.startswith("http"):
            antes = json.loads(P.get(origen))
        else:
            with open(origen, encoding="utf-8") as f:
                antes = json.load(f)
    except Exception:
        return None
    de = antes.get("previsio_de") or antes.get("generat")
    if not antes.get("hores") or not de:
        return None
    if P.AHORA - dt.datetime.fromisoformat(de) > dt.timedelta(hours=C.CASA_PREVISION_ANTERIOR_MAX_H):
        return None
    ara_hora = P.AHORA.strftime("%Y-%m-%dT%H:%M")
    hores = [dict(f) for f in antes["hores"] if f["fins"] > ara_hora]
    if not hores:
        return None
    llueve_ahora = llueve_ahora_en(casa, veines)
    for n, f in enumerate(hores):
        fin = dt.datetime.fromisoformat(f["fins"]).astimezone()
        f["avisos"] = avisos_del_tramo(fin - dt.timedelta(hours=1), fin, avisos)
        f["plou_ara"] = n == 0 and llueve_ahora
        if f["plou_ara"]:
            f["probabilitat"], f["segons_estacio"] = 1.0, True
    return {"hores": hores, "previsio_de": de, "aprenentatge": antes.get("aprenentatge")}


def comprobacion_modelos(desde, h, filas_estacion):
    """Lluvia medida en casa y prevista en las últimas horas completas. Si
    los modelos se han quedado muy cortos, la página lo dice. Solo si las
    lecturas de la estación (ecowitt.resum_ara) cubren esas horas."""
    if not filas_estacion:
        return None
    fin = desde.replace(minute=0, second=0, microsecond=0)
    ini = fin - dt.timedelta(hours=HORAS_COMPROBACION)
    if filas_estacion[0]["t"] > ini or filas_estacion[-1]["t"] < fin:
        return None
    medida = E.pluja_entre(filas_estacion, ini, fin)
    prevista = 0.0
    for i, t in enumerate(h["time"]):
        tt = dt.datetime.fromisoformat(t).astimezone()
        if ini < tt <= fin:
            prevista += lluvia_modelos(h, i)
    fallan = medida >= 3 and medida > 3 * prevista + 1
    return {"hores": HORAS_COMPROBACION, "mesurada_mm": round(medida, 1),
            "prevista_mm": round(prevista, 1), "no_encerten": fallan}


def recoger(anterior=None):
    salida = {"versio": C.VERSION, "generat": P.AHORA.isoformat(timespec="minutes"),
              "errors": []}
    # La estación del barrio es la de casa, en «ara_casa» (ADR 0017 y 0058).
    casa = None
    try:
        casa = estacio_casa()
    except Exception as ex:
        salida["errors"].append(f"estació de casa: {ex}")
    salida["ara_casa"] = casa and {k: v for k, v in casa.items() if k != "files"}
    # La temperatura medida cada hora de las últimas 72, para decir cuántos
    # grados más o menos que ayer (ADR 0061). Solo en el NAS, que tiene el
    # registro; sin él (la reserva de IONOS), no se compara.
    salida["temperatura_mesurada"] = None
    if R.hay_registro():
        try:
            salida["temperatura_mesurada"] = R.temperatures_casa(
                P.AHORA, recents=E.hores(casa["files"]) if casa else None) or None
        except Exception as ex:
            print("No he podido leer la temperatura medida:", ex, file=sys.stderr)
    # La estación de casa, a Weather Underground (ADR 0059). Si falla, no es
    # cosa de la página: solo se apunta.
    if casa and WU.disponible():
        try:
            WU.puja(casa, P.AHORA)
        except Exception as ex:
            print("No he podido subir la estación a Weather Underground:", ex, file=sys.stderr)
    # Las estaciones vecinas de Weather Underground (ADR 0060): si falla una,
    # solo se apunta; si no se puede leer ninguna teniendo clave (caducada,
    # red caída), la página lo dice, porque «plou ara» cuenta con ellas.
    veines = []
    if WU.lectura_disponible():
        veines, fallos = WU.veines_ara(P.AHORA)
        for fallo in fallos:
            print("No he podido leer la estación vecina", fallo, file=sys.stderr)
        if fallos and not veines:
            salida["errors"].append(f"estacions veïnes: {fallos[0]}")
        dies = WU.dies_fins_caducitat(P.AHORA)
        if dies <= C.WU_AVIS_CADUCITAT_DIES:
            print(f"La clau de lectura de Weather Underground caduca d'aquí a {dies} dies "
                  f"({C.WU_CLAU_CADUCA}): cal regenerar-la (RESTAURAR.md).", file=sys.stderr)
    salida["veines"] = [{k: v for k, v in x.items() if k != "files"} for x in veines]
    # Si llueve ahora, en casa o en una vecina que cuenta: lo que miran el
    # bot, los avisos y la web (plou_ara de la primera hora de la tabla).
    salida["plou_ara"] = llueve_ahora_en(casa, veines)
    # El viento de ahora, de la estación de Meteocat más cercana (ADR 0037).
    try:
        salida["vent"] = P.vent_meteocat(C.VENT_ESTACIO)
    except Exception as ex:
        salida["vent"] = None
        salida["errors"].append(f"vent: {ex}")
    avisos = planes = None
    try:
        avisos = [a for a in P.avisos() if a["zona"] == C.ZONA_AVISOS
                  and dt.datetime.fromisoformat(a["fin"]) > P.AHORA]
    except Exception as ex:
        salida["errors"].append(f"avisos: {ex}")
    try:
        planes = P.planes_proteccion_civil()
    except Exception as ex:
        salida["errors"].append(f"plans: {ex}")
    # Los planes sin motivo meteorológico a la vista (la recuperación tras un
    # temporal) no se muestran ni ponen la página en modo aviso; van aparte,
    # para que los avisos del canal no anuncien un final que no ha habido
    # (ADR 0062).
    salida["plans_ocults"] = None
    if planes is not None:
        salida["plans_ocults"] = [p for p in planes if not P.pla_per_temps(p, avisos, P.AHORA)]
        planes = [p for p in planes if P.pla_per_temps(p, avisos, P.AHORA)]
    salida["avisos"], salida["plans"] = avisos, planes
    radar = None
    try:
        radar = P.radar()
    except Exception as ex:
        salida["errors"].append(f"radar: {ex}")
    obs = [o for o in [E.observacio(casa, C.ESTACIO_CASA)] + [WU.observacio(v) for v in veines] if o]
    motivos = P.motivos_modo_aviso(avisos, planes, obs, radar)
    # En modo aviso, todo el día: hasta las 23:50, no solo hasta las 23:00.
    nc = (radar or {}).get("nowcast")
    salida["radar"] = nc and {k: nc[k] for k in ("hora", "imatge", "moviment", "velocitat_kmh", "cap_a")}
    if nc:
        # Cuándo llegaría: probable (50 %) o, si no, posible (20 %).
        for clau, prob in (("arriba", 0.5), ("possible", C.PROB_ATENCION)):
            t = N.arribada(nc, "casa", prob)
            salida["radar"][clau] = t and t.isoformat(timespec="minutes")
        # Cómo sería al llegar, para el aviso de antes de llover (ADR 0022).
        salida["radar"]["arriba_mm_h"] = N.intensitat_arribada(nc, "casa")
        # A qué hora pararía, «en entrenament» en la página (fi_pluja.py, ADR 0049).
        try:
            salida["radar"].update(FP.fi_radar(nc, P.AHORA, salida["radar"]["arriba"]) or {})
        except Exception as ex:
            salida["errors"].append(f"final de la pluja: {ex}")
    # La riera de Sant Cugat: lo que ha llovido en la cuenca y lo que trae el
    # radar, para el aviso por Telegram (ADR 0027).
    try:
        salida["riera"] = RI.calcula(P.AHORA, nc)
        if salida["riera"] is None:
            salida["errors"].append("riera: Sant Cugat (Meteocat) sense dades recents")
        elif salida["riera"].get("incomplet"):
            salida["errors"].append("riera: a Sant Cugat (Meteocat) li falten mitges hores de pluja")
    except Exception as ex:
        salida["riera"] = None
        salida["errors"].append(f"riera: {ex}")
    salida["horari"] = P.horario([C.HORARIO_CASA_AVISO if motivos else C.HORARIO_CASA],
                                 C.INTERVALO_CASA_MIN, motivos)
    try:
        h, e = modelos(P.AHORA, salida["errors"])
        model = A.carrega()
        salida["aprenentatge"] = A.resum_pagina(model)
        salida["hores"] = previsio(P.AHORA, h, e, avisos, model, casa, nc, planes, salida.get("riera"), veines)
        salida["models"] = comprobacion_modelos(P.AHORA, h, (casa or {}).get("files", []))
    except Exception as ex:
        salida["hores"] = salida["models"] = None
        salida["errors"].append(f"previsió: {ex}")
        # Sin modelos: la última previsión buena, si es reciente, avisando.
        antes = previsio_anterior(anterior, avisos, casa, veines)
        if antes:
            salida.update(antes)
    # Para «Si surts» (ADR 0029): el índice UV de cada hora y si circulan los
    # trenes de cerca.
    try:
        uv = indice_uv(P.AHORA)
        for f in salida["hores"] or []:
            valors = [uv[t] for t in (f["hora"], f["fins"]) if t in uv]
            f["uv"] = round(max(valors), 1) if valors else None
    except Exception as ex:
        salida["errors"].append(f"índex UV: {ex}")
    try:
        salida["trens"] = TR.calcula(P.AHORA)
    except Exception as ex:
        salida["trens"] = None
        salida["errors"].append(f"trens: {ex}")
    # Incidencias de tráfico de cerca, para el coche y la moto (ADR 0052).
    try:
        salida["transit"] = TT.calcula(P.AHORA)
    except Exception as ex:
        salida["transit"] = None
        salida["errors"].append(f"trànsit: {ex}")
    # El sol y la calidad del aire, para «Consultes», /sol y /aire (ADR 0054).
    for clau, funcio in (("sol", lambda: sol(P.AHORA)), ("aire", lambda: AI.calcula(P.AHORA))):
        try:
            salida[clau] = funcio()
        except Exception as ex:
            salida[clau] = None
            salida["errors"].append(f"{clau}: {ex}")
    # El polen de la semana en Bellaterra, para «Consultes» y /pollen (ADR 0054).
    try:
        salida["pollen"] = PO.calcula(P.AHORA)
    except Exception as ex:
        salida["pollen"] = None
        salida["errors"].append(f"pol·len: {ex}")
    # Incendios cerca, Pla Alfa y acceso a Collserola (ADR 0046).
    salida["entorn"] = EN.calcula(P.AHORA)
    salida["errors"] += [f"entorn: {e}" for e in salida["entorn"].pop("errors")]
    # Situaciones de peligro según lo medido y lo previsto (ADR 0018).
    salida["riscos"] = RS.detecta(salida, P.AHORA)
    # Registro para aprender (solo en el NAS, que tiene /estat): lo que medía
    # la estación de casa, por horas y cada 5 minutos, la lluvia por horas de
    # las estaciones de Meteocat, lo que medían las vecinas y, una vez por
    # hora, lo que daban los modelos.
    if R.hay_registro():
        try:
            if casa:
                R.apunta_estacio_casa(E.hores(casa["files"]))
                R.apunta_casa_5min(R.cincs_casa(casa["files"]))
            if salida["hores"] and not salida.get("previsio_de"):
                r = salida.get("riera")
                R.apunta_casa(P.AHORA, filas_registro(P.AHORA, h, e, salida["hores"][:HORAS], casa,
                                                      avisos, planes, salida.get("riera")),
                              salida["ara_casa"], {"pluja_1h": r["mm_1h"], "fins": r["fins"]} if r else None)
        except Exception as ex:
            print("No he podido apuntar en el registro:", ex, file=sys.stderr)
        if radar:
            try:
                R.apunta_radar_a_prop(P.AHORA, radar, motivos, obs)
            except Exception as ex:
                print("No he podido apuntar los ecos del radar:", ex, file=sys.stderr)
        for codi in C.ESTACIONES:
            try:
                R.apunta_meteocat(codi, R.hores_meteocat(RI.files(codi, P.AHORA, 6, None)))
            except Exception as ex:
                print(f"No he podido apuntar la estación {codi} de Meteocat:", ex, file=sys.stderr)
        # Las vecinas por horas (ADR 0060): las de hoy en cada pasada y, una
        # vez al día, las de ayer, para cerrar la última hora del día.
        for v in veines:
            try:
                files = v["files"]
                if R.falta_ahir_veina(v["estacio"], P.AHORA):
                    files = WU.hores_ahir(v["estacio"], P.AHORA) + files
                R.apunta_veina(v["estacio"], R.hores_veina(files))
            except Exception as ex:
                print(f"No he podido apuntar la estación vecina {v['estacio']}:", ex, file=sys.stderr)
        # Lo que daba cada radar, para saber cuál acierta más (ADR 0026).
        try:
            RF.apunta(P.AHORA, nc, salida["ara_casa"])
        except Exception as ex:
            print("No he podido apuntar los radares:", ex, file=sys.stderr)
    return salida


if __name__ == "__main__":
    datos = recoger(sys.argv[sys.argv.index("--anterior") + 1] if "--anterior" in sys.argv else None)
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
    print(f"Generado {datos['generat']}", datos["errors"] or "")
    print("Casa:", datos["ara_casa"])
    print("Modelos:", datos["models"])
    print("Planes:", datos["plans"])
    for f in (datos["hores"] or [])[:8]:
        print(f["hora"][11:16], f["temperatura"], "°C", f["pluja_mm"], "mm", f["probabilitat"],
              "estació" if f["segons_estacio"] else "", "PLOU ARA" if f["plou_ara"] else "",
              f["avisos"])
