#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Recogida de datos del tiempo en el barrio, para casa.py y la riera.

Junta los avisos de AEMET, los planes de Protección Civil, la lluvia y el
viento de las estaciones y el radar (con la lluvia llevada hacia delante,
nowcast.py), y decide cuándo toca el modo aviso. Los textos salen en catalán
porque son los que lee la web.

Uso:
  python3 prevision.py               resumen legible de lo que recoge
"""
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

import config as C
import nowcast as N
import ecowitt

UA = {"User-Agent": "meteo-local/" + C.VERSION}
DIR = os.path.dirname(os.path.abspath(__file__))
TZ = "Europe/Madrid"
AHORA = dt.datetime.now().astimezone()


def leer_calibracion():
    """Lo que sale de la calibración con datos reales (calibracio/): la
    persistencia de la lluvia que usa casa.py."""
    try:
        with open(os.path.join(DIR, "calibracio", "calibracio.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


CALIBRACION_COMPLETA = leer_calibracion()


def get(url, binario=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        datos = r.read()
    return datos if binario else datos.decode("utf-8", "replace")


CACHE_WEB = os.environ.get("CACHE_WEB", "/estat/cache-web")


def get_recent(url, segons=120):
    """get() que reutiliza la respuesta si tiene menos de segons: las
    distintas lecturas de una misma pasada (la lluvia, el viento, la riera)
    leen cada página una sola vez (ADR 0020). Fuera del NAS, sin /estat,
    siempre de la red."""
    import hashlib
    import time
    if not os.path.isdir(os.path.dirname(CACHE_WEB)):
        return get(url)
    os.makedirs(CACHE_WEB, exist_ok=True)
    ruta = os.path.join(CACHE_WEB, hashlib.sha1(url.encode()).hexdigest())
    try:
        if time.time() - os.path.getmtime(ruta) < segons:
            with open(ruta, encoding="utf-8") as f:
                return f.read()
    except OSError:
        pass
    datos = get(url)
    with open(ruta + ".tmp", "w", encoding="utf-8") as f:
        f.write(datos)
    os.replace(ruta + ".tmp", ruta)
    return datos


# --- Estaciones -----------------------------------------------------------------

PORTAL = "https://analisi.transparenciacatalunya.cat/resource/nzvn-apee.json"


def files_meteocat(codi, dia_utc=None, lector=None):
    """Filas semihorarias de un día (por defecto, hoy) en la página de
    meteo.cat: lista de (inicio de la media hora en UTC, {columna: texto}).
    La tabla va en hora UTC y el día también es el de UTC. Las columnas se
    llaman como en la cabecera: «PPTmm», «VVM (10 m)km/h», «VVX (10 m)km/h»…
    La misma página la leen la lluvia, el viento y la riera: se guarda dos
    minutos."""
    url = f"https://www.meteo.cat/observacions/xema/dades?codi={codi}"
    if dia_utc:
        url += f"&dia={dia_utc.isoformat()}T00:00Z"
    s = (lector or get_recent)(url)
    t = re.search(r"<table[^>]*tblperiode.*?</table>", s, re.S)
    cab, res = None, []
    dia_utc = dia_utc or AHORA.astimezone(dt.timezone.utc).date()
    for f in re.findall(r"<tr.*?</tr>", t.group(0), re.S) if t else []:
        celdas = [html.unescape(re.sub("<[^>]+>", "", c)).strip()
                  for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", f, re.S)]
        if celdas and celdas[0].startswith("Període"):
            cab = celdas
        elif cab and len(celdas) > 1:
            fila = dict(zip(cab, celdas))
            ini = fila[cab[0]].split("-")[0].strip()
            res.append((dt.datetime.combine(dia_utc, dt.time.fromisoformat(ini), dt.timezone.utc), fila))
    return res


def _columna(fila, prefix):
    """El valor numérico de la columna que empieza por prefix, o None si
    falta o es «(s/d)»."""
    for k, v in fila.items():
        if k.startswith(prefix):
            try:
                return float(v)
            except ValueError:
                return None
    return None


def taula_meteocat(codi, dia_utc=None, lector=None):
    """Lluvia semihoraria de un día: lista de (inicio de la media hora en
    UTC, mm), sin las medias horas sin dato."""
    res = []
    for ini, fila in files_meteocat(codi, dia_utc, lector):
        mm = _columna(fila, "PPT")
        if mm is not None:
            res.append((ini, mm))
    return res


def vent_meteocat(codi, lector=None):
    """El viento de la última media hora con dato en una estación de
    Meteocat: media y racha en km/h y hasta cuándo vale (ADR 0037)."""
    for ini, fila in reversed(files_meteocat(codi, lector=lector)):
        mitja, ratxa = _columna(fila, "VVM"), _columna(fila, "VVX")
        if mitja is not None:
            nom = C.ESTACIONES.get(codi, codi)
            return {"estacio": nom.split(" (")[0], "mitja": mitja, "ratxa": ratxa,
                    "fins": (ini + dt.timedelta(minutes=30)).astimezone().isoformat(timespec="minutes")}
    return None


def observaciones_web(codi, nom):
    """Lluvia de hoy según la página de meteo.cat."""
    filas = taula_meteocat(codi)
    if not filas:
        return None
    hasta = filas[-1][0] + dt.timedelta(minutes=30)
    return {"estacion": nom, "font": "meteo.cat",
            "mm_hoy": round(sum(mm for _, mm in filas), 1),
            "mm_ultima_media_hora": filas[-1][1],
            "hasta": hasta.astimezone().isoformat()}


def observaciones_portal(codi, nom):
    """Lo mismo desde el portal de datos abiertos de la Generalitat. Va
    aproximadamente una hora por detrás, pero es una API estable. Cada lectura
    marca el inicio de su media hora, en UTC (comprobado con la tabla de
    meteo.cat del 04-10-2026)."""
    inicio = AHORA.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT00:00:00")
    q = urllib.parse.urlencode({
        "$where": f"codi_estacio='{codi}' AND codi_variable='35' AND data_lectura>='{inicio}'",
        "$order": "data_lectura", "$limit": 100})
    filas = json.loads(get(f"{PORTAL}?{q}"))
    if not filas:
        return None
    ultima = dt.datetime.fromisoformat(filas[-1]["data_lectura"]).replace(tzinfo=dt.timezone.utc)
    return {"estacion": nom, "font": "portal de dades obertes",
            "mm_hoy": round(sum(float(f["valor_lectura"]) for f in filas), 1),
            "mm_ultima_media_hora": float(filas[-1]["valor_lectura"]),
            "hasta": (ultima + dt.timedelta(minutes=30)).astimezone().isoformat()}


METEOCERDANYOLA = "https://meteocerdanyola.com/2026/api/graphs-series.php?slug={}"


def resumen_minutal(filas, nom, font):
    """Lluvia de la última media hora a partir de filas minuto a minuto con el
    acumulado del día (PREC, se pone a cero a medianoche) y la intensidad
    (PINT, mm/h)."""
    filas = [f for f in filas if f.get("PREC") is not None]
    if not filas:
        return None
    ultima = dt.datetime.fromisoformat(filas[-1]["dt_local"]).astimezone()
    desde = ultima - dt.timedelta(minutes=30)
    recientes = [f for f in filas if dt.datetime.fromisoformat(f["dt_local"]).astimezone() >= desde]
    mm = 0.0
    for antes, despues in zip(recientes, recientes[1:]):
        salto = despues["PREC"] - antes["PREC"]
        mm += despues["PREC"] if salto < 0 else salto
    return {"estacion": nom, "font": font,
            "mm_hoy": round(filas[-1]["PREC"], 1),
            "mm_ultima_media_hora": round(mm, 1),
            "intensitat": filas[-1].get("PINT"),
            "hasta": ultima.isoformat()}


def observaciones_meteocerdanyola(slug, nom):
    """Estaciones de meteocerdanyola.com, minuto a minuto. Se lee la API de
    sus gráficas una vez por actualización (unos 380 KB, últimas 24 h): la
    carpeta /2026/data/ está cerrada a programas en su robots.txt, la API no.
    Juanjo decidió usarla (05-10-2026); ver el ADR 0004."""
    datos = json.loads(get_recent(METEOCERDANYOLA.format(slug)))
    return resumen_minutal(datos.get("rows", []), nom, "meteocerdanyola.com")


def observaciones():
    """Primero la estación de Montflorit (minuto a minuto) y la de casa si
    marca lluvia; después las de Meteocat: su web, que va más al día, o si falla el portal de la
    Generalitat."""
    res = []
    for slug, nom in C.ESTACIONES_LOCALES.items():
        try:
            dato = observaciones_meteocerdanyola(slug, nom)
        except Exception:
            dato = None
        if dato:
            res.append(dato)
    # La estación de casa, solo si marca lluvia: su cero no es fiable (ADR 0017).
    try:
        dato = ecowitt.observacio(ecowitt.resum_ara(), C.ESTACIO_CASA) if ecowitt.disponible() else None
    except Exception:
        dato = None
    if dato:
        res.append(dato)
    for codi, nom in C.ESTACIONES.items():
        dato = None
        for fuente in (observaciones_web, observaciones_portal):
            try:
                dato = fuente(codi, nom)
            except Exception:
                dato = None
            if dato:
                break
        if dato:
            res.append(dato)
    return res


# --- Radar ----------------------------------------------------------------------

def radar():
    """Lluvia apreciable más cercana a casa, si crece, y la lluvia llevada
    hacia delante hasta 2 horas (nowcast.py, ADR 0019): imagen de Meteocat
    o, si se ha quedado atrás, de RainViewer."""
    import numpy as np
    r = N.carrega(get, get_pagina=get_recent)
    im = N.imatge(r)
    if im is None:
        raise RuntimeError("; ".join(r["errors"]) or "sense imatges de radar")
    hora, ara, origen = im
    fila, col = N.pixel(C.CASA[0], C.CASA[1], r["tx"], r["ty"])
    yy, xx = np.ogrid[:N.MIDA, :N.MIDA]
    dist = np.hypot((yy - fila) * r["km_px"], (xx - col) * r["km_px"])
    cerca = dist <= 50
    lluvia = ara >= RADAR_APRECIABLE_MMH
    res = {"hora": hora.isoformat(), "imatge": origen,
           "km_lluvia": round(float(dist[lluvia].min()), 1) if lluvia.any() else None,
           "km2_50km_ahora": round(float((lluvia & cerca).sum() * r["km_px"] ** 2)),
           "km2_50km_antes": None, "nowcast": N.resum(r)}
    # Si crece: la misma comparación de siempre, con RainViewer (una hora antes).
    rv = r.get("rainviewer")
    if rv and len(rv["mm_h"]) >= 7:
        res["km2_50km_antes"] = round(float(((rv["mm_h"][0] >= RADAR_APRECIABLE_MMH) & cerca).sum() * r["km_px"] ** 2))
        res["km2_50km_ahora"] = round(float(((rv["mm_h"][-1] >= RADAR_APRECIABLE_MMH) & cerca).sum() * r["km_px"] ** 2))
    return res


# Lluvia apreciable en el radar: unos 6 dBZ, el umbral que se usaba con la
# opacidad de RainViewer (por debajo, llovizna o ruido).
RADAR_APRECIABLE_MMH = 0.08


# --- Avisos y planes ------------------------------------------------------------

def descripcion_aviso(url):
    """El texto de un aviso de AEMET, tal como lo publica (en castellano; la
    versión inglesa de la ficha repite el mismo texto). Cada ficha tiene su
    dirección: si el aviso cambia, cambia la dirección, así que se puede
    guardar horas. None si no hay texto."""
    s = get_recent(url, segons=6 * 3600)
    textos = {}
    for info in re.findall(r"<info>.*?</info>", s, re.S):
        idioma = re.search(r"<language>(.*?)<", info)
        texto = re.search(r"<description>(.*?)</description>", info, re.S)
        if texto and texto.group(1).strip():
            textos[idioma.group(1) if idioma else ""] = html.unescape(" ".join(texto.group(1).split()))
    return textos.get("es-ES") or next(iter(textos.values()), None)


def avisos():
    """Avisos de lluvia y tormenta de AEMET, del feed de Meteoalarm."""
    s = get("https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-spain")
    res = []
    for ent in re.findall(r"<entry>.*?</entry>", s, re.S):
        def campo(c):
            m = re.search(rf"<cap:{c}>(.*?)<", ent)
            return m.group(1) if m else ""
        zona, evento = campo("areaDesc"), campo("event")
        if zona not in (C.ZONA_AVISOS, C.ZONA_CERCANA):
            continue
        tipo = "tempestes" if "thunderstorm" in evento else "pluja" if "rain" in evento else None
        if not tipo:
            continue
        nivel = {"Moderate": "groc", "Severe": "taronja", "Extreme": "vermell"}.get(
            evento.split()[0], evento)
        aviso = {"zona": zona, "tipo": tipo, "nivel": nivel,
                 "inicio": dt.datetime.fromisoformat(campo("onset")).astimezone().isoformat(),
                 "fin": dt.datetime.fromisoformat(campo("expires")).astimezone().isoformat()}
        # El texto del aviso («Pueden ir acompañadas de granizo…») está en su
        # ficha, no en el resumen (ADR 0033).
        ficha = re.search(r'href="(https://feeds\.meteoalarm\.org/api/v1/warnings/[^"]+)"', ent)
        if ficha and zona == C.ZONA_AVISOS and aviso["fin"] > AHORA.isoformat():
            try:
                aviso["descripcio"] = descripcion_aviso(ficha.group(1))
            except Exception:
                pass
        res.append(aviso)
    # El feed repite entradas idénticas.
    unicos = {tuple(sorted(a.items())) for a in res}
    return sorted((dict(t) for t in unicos), key=lambda a: (a["inicio"], a["zona"], a["tipo"]))


PLANES_PC_URL = "https://analisi.transparenciacatalunya.cat/resource/wj9c-j6vf.json"


def afecta_la_zona(descripcion):
    """Un plan afecta salvo que su descripción nombre solo otras zonas."""
    d = descripcion or ""
    if any(z in d for z in C.ZONAS_PROPIAS_PC):
        return True
    return not any(z in d for z in C.ZONAS_AJENAS_PC)


ORDRE_FASES = {"prealerta": 0, "alerta": 1, "emergència": 2}


def nom_pla(p):
    """El nombre que ve el lector de un plan que interesa, o None. Del PROCICAT
    solo interesan algunos riesgos, y el de cada registro lo dice su icono."""
    acronimo = p.get("plaacronim", "")
    if acronimo in C.PLANES_PC:
        return C.PLANES_PC[acronimo]
    if acronimo == "PROCICAT":
        icona = urllib.parse.unquote((p.get("plaicona") or {}).get("url") or "")
        m = re.search(r"ico_PROCICAT_([^/]+)\.png$", icona, re.I)
        return C.PROCICAT_PC.get(m.group(1).upper()) if m else None
    return None


def planes_proteccion_civil():
    """Planes de Protección Civil que dependen del tiempo, activados o en
    prealerta (datos abiertos de la Generalitat, actualizados en tiempo real),
    uno por plan y riesgo, con la fase más alta. La prealerta no activa el plan
    pero se muestra (ADR 0051)."""
    res = {}
    for p in json.loads(get(PLANES_PC_URL)):
        nom = nom_pla(p)
        fase = (p.get("plafase") or "").lower()
        if (nom is None or fase not in ORDRE_FASES or (p.get("plaactivat") != "SI" and fase != "prealerta")
                or not afecta_la_zona(p.get("descripcio"))):
            continue
        clau = (p["plaacronim"], nom)
        if clau in res and ORDRE_FASES[res[clau]["fase"]] >= ORDRE_FASES[fase]:
            continue
        res[clau] = {"pla": p["plaacronim"], "nom": nom, "fase": fase,
                     "des_de": p.get("fasedatahora"),
                     "descripcio": (p.get("descripcio") or "").strip(" -"),
                     "comunicat": (p.get("comunicatpdf") or {}).get("url")}
    return list(res.values())


# --- Horario y modo aviso -------------------------------------------------------

def motivos_modo_aviso(avisos_, planes, obs, radar_):
    """Por qué conviene actualizar cada 6 minutos (lista vacía si no): aviso
    de AEMET vigente, plan de Protección Civil en alerta o emergencia, lluvia
    en las estaciones o lluvia en el radar a menos de RADAR_AVISO_KM de casa
    (o que llegará a casa en la próxima hora)."""
    res = []
    if any(a["zona"] == C.ZONA_AVISOS
           and dt.datetime.fromisoformat(a["inicio"]) <= AHORA < dt.datetime.fromisoformat(a["fin"])
           for a in avisos_ or []):
        res.append("avís de l'AEMET")
    if any(p["fase"] in ("alerta", "emergència") for p in planes or []):
        res.append("pla de Protecció Civil")
    if any((o.get("mm_ultima_media_hora") or 0) > 0 or (o.get("intensitat") or 0) > 0 for o in obs or []):
        res.append("pluja a les estacions")
    nc = (radar_ or {}).get("nowcast")
    propera = nc and N.en_tram(nc, "casa", AHORA, AHORA + dt.timedelta(hours=1))
    if (radar_ and radar_.get("km_lluvia") is not None and radar_["km_lluvia"] <= C.RADAR_AVISO_KM
            or propera and propera["prob"] >= C.PROB_ATENCION):
        res.append("pluja al radar")
    return res


def horario(trams, cada_min, motivos_aviso):
    """El horario que muestra la página y que sigue el reloj del NAS."""
    if motivos_aviso:
        return {"trams": trams, "cada_min": C.MODO_AVISO_INTERVALO_MIN,
                "desfase_min": C.MODO_AVISO_DESFASE_MIN, "mode_avis": motivos_aviso}
    return {"trams": trams, "cada_min": cada_min, "desfase_min": 0, "mode_avis": []}


if __name__ == "__main__":
    d, errores = {}, []
    for clave, funcion in (("avisos", avisos), ("plans", planes_proteccion_civil),
                           ("estacions", observaciones), ("radar", radar)):
        try:
            d[clave] = funcion()
        except Exception as ex:
            errores.append(f"{clave}: {ex}")
    print(f"Recollit {AHORA.isoformat(timespec='minutes')}")
    for error in errores:
        print("  fallo:", error)
    for a in d.get("avisos") or []:
        print(f"Avís {a['nivel']} per {a['tipo']} a {a['zona']}: {a['inicio'][11:16]}-{a['fin'][11:16]}")
    for p in d.get("plans") or []:
        print(f"Pla {p['pla']} en fase d'{p['fase']}")
    for o in d.get("estacions") or []:
        print(f"{o['estacion']}: {o['mm_ultima_media_hora']} mm en mitja hora, {o['mm_hoy']} mm avui ({o['font']})")
    r = d.get("radar")
    if r:
        nc = r["nowcast"] or {}
        print(f"Radar ({r['imatge']}, {r['hora'][11:16]}): pluja a {r['km_lluvia']} km de casa; "
              f"moviment cap {nc.get('cap_a')} a {nc.get('velocitat_kmh')} km/h")
    motius = motivos_modo_aviso(d.get("avisos"), d.get("plans"), d.get("estacions"), r)
    print("Mode avís:", ", ".join(motius) if motius else "no")
    sys.exit(1 if errores and not d else 0)
