#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""¿Moto o coche? Lluvia en el trayecto Cerdanyola → Parc Taulí.

Junta avisos de AEMET, radar, estaciones de Meteocat, modelos y un ensemble,
y da un solo medio para todo el día: quien va en moto vuelve en moto. Los
motivos salen en catalán porque son los que lee la web.

Uso:
  python3 prevision.py               resumen legible
  python3 prevision.py --json FICH   además, guarda los datos para la web
  --anterior URL|FICH                 datos publicados antes, para mantener la
                                      decisión una vez ha salido de casa
"""
import datetime as dt
import html
import io
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request

import config as C

UA = {"User-Agent": "meteo-local/" + C.VERSION}
DIR = os.path.dirname(os.path.abspath(__file__))
TZ = "Europe/Madrid"
AHORA = dt.datetime.now().astimezone()


def leer_calibracion():
    """Lo que sale de la calibración con datos reales (calibracio/)."""
    try:
        with open(os.path.join(DIR, "calibracio", "calibracio.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


CALIBRACION_COMPLETA = leer_calibracion()
# Frecuencia real de lluvia en cada nivel de la regla.
CALIBRACION = CALIBRACION_COMPLETA.get("ventanas", {})


def frase_historico(ventana, nivel):
    """«Des del 2024, quan els models deien això, a l'hora del trajecte ha
    plogut 6 de cada 58 dies (10 %).»"""
    nombre = "anada" if ventana == C.IDA else "tornada"
    dato = CALIBRACION.get(nombre, {}).get("nivells", {}).get(nivel)
    if not dato or not dato["dies"]:
        return ""
    pct = round(100 * dato["pluja"] / dato["dies"])
    desde = CALIBRACION[nombre]["desde"][:4]
    return (f" Des del {desde}, quan els models deien això, a l'hora del trajecte ha "
            f"plogut {dato['pluja']} de cada {dato['dies']} dies ({pct}\u00a0%).")


def get(url, binario=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        datos = r.read()
    return datos if binario else datos.decode("utf-8", "replace")


def momento(dia, hhmm):
    return dt.datetime.fromisoformat(f"{dia}T{hhmm}").astimezone()


def horas_ventana(ventana):
    """Horas en punto cuyo acumulado (la hora anterior) cubre la ventana."""
    ini, fin = (dt.time.fromisoformat(x) for x in ventana)
    return list(range(ini.hour + 1, fin.hour + (2 if fin.minute else 1)))


def coma(x):
    return f"{x:.1f}".replace(".", ",")


def hm(t):
    return t.strftime("%H:%M")


# --- Recogida de datos ---------------------------------------------------------

PORTAL = "https://analisi.transparenciacatalunya.cat/resource/nzvn-apee.json"


def taula_meteocat(codi):
    """Lluvia semihoraria de hoy en la página de meteo.cat: lista de
    (inicio de la media hora en UTC, mm). La tabla va en hora UTC."""
    s = get(f"https://www.meteo.cat/observacions/xema/dades?codi={codi}")
    t = re.search(r"<table[^>]*tblperiode.*?</table>", s, re.S)
    cab, res = None, []
    dia_utc = AHORA.astimezone(dt.timezone.utc).date()
    for f in re.findall(r"<tr.*?</tr>", t.group(0), re.S) if t else []:
        celdas = [html.unescape(re.sub("<[^>]+>", "", c)).strip()
                  for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", f, re.S)]
        if celdas and celdas[0].startswith("Període"):
            cab = celdas
        elif cab and len(celdas) > 1 and "(s/d)" not in celdas[1]:
            fila = dict(zip(cab, celdas))
            col = next(k for k in cab if k.startswith("PPT"))
            ini = fila[cab[0]].split("-")[0].strip()
            res.append((dt.datetime.combine(dia_utc, dt.time.fromisoformat(ini), dt.timezone.utc),
                        float(fila[col])))
    return res


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
    datos = json.loads(get(METEOCERDANYOLA.format(slug)))
    return resumen_minutal(datos.get("rows", []), nom, "meteocerdanyola.com")


def observaciones():
    """Primero la estación de Montflorit (minuto a minuto); después las de
    Meteocat: su web, que va más al día, o si falla el portal de la
    Generalitat."""
    res = []
    for slug, nom in C.ESTACIONES_LOCALES.items():
        try:
            dato = observaciones_meteocerdanyola(slug, nom)
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


def radar():
    """Lluvia apreciable más cercana y si crece, con RainViewer (zoom 7)."""
    import numpy as np
    from PIL import Image
    meta = json.loads(get("https://api.rainviewer.com/public/weather-maps.json"))
    z = 7
    n = 2 ** z
    lat = (C.CASA[0] + C.DESTINO[0]) / 2
    lon = (C.CASA[1] + C.DESTINO[1]) / 2
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    tx, ty = int(x), int(y)
    centro = (256 + int((y - ty) * 256), 256 + int((x - tx) * 256))

    def mosaico(fotograma):
        a = np.zeros((768, 768))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                url = (f"{meta['host']}{fotograma['path']}/256/{z}/"
                       f"{tx + dx}/{ty + dy}/2/0_0.png")
                im = Image.open(io.BytesIO(get(url, True))).convert("RGBA")
                a[(dy + 1) * 256:(dy + 2) * 256, (dx + 1) * 256:(dx + 2) * 256] = \
                    np.array(im)[:, :, 3]
        return a

    fotogramas = meta["radar"]["past"]
    antes, ahora = mosaico(fotogramas[-7]), mosaico(fotogramas[-1])
    km_px = 360 / n / 256 * 111.32 * math.cos(math.radians(lat))
    yy, xx = np.ogrid[:768, :768]
    dist = np.hypot((yy - centro[0]) * km_px, (xx - centro[1]) * km_px)
    # La opacidad del PNG crece con la intensidad: por encima de 100 es
    # lluvia apreciable; por debajo, llovizna o ruido.
    lluvia = ahora > 100
    cerca = dist <= 50
    return {
        "hora": dt.datetime.fromtimestamp(fotogramas[-1]["time"]).astimezone().isoformat(),
        "km_lluvia": round(float(dist[lluvia].min()), 1) if lluvia.any() else None,
        "km2_50km_antes": round(float(((antes > 100) & cerca).sum() * km_px ** 2)),
        "km2_50km_ahora": round(float((lluvia & cerca).sum() * km_px ** 2)),
    }


def modelos(dias):
    q = urllib.parse.urlencode({
        "latitude": f"{C.CASA[0]},{C.DESTINO[0]}",
        "longitude": f"{C.CASA[1]},{C.DESTINO[1]}",
        "hourly": "precipitation,temperature_2m,wind_gusts_10m,cape",
        "models": ",".join(C.MODELOS_FINOS + C.MODELOS_GLOBALES),
        "timezone": TZ, "start_date": dias[0], "end_date": dias[-1]})
    return json.loads(get(f"https://api.open-meteo.com/v1/forecast?{q}"))


def ensemble(dias):
    q = urllib.parse.urlencode({
        "latitude": round((C.CASA[0] + C.DESTINO[0]) / 2, 3),
        "longitude": round((C.CASA[1] + C.DESTINO[1]) / 2, 3),
        "hourly": "precipitation", "models": C.ENSEMBLE, "timezone": TZ,
        "start_date": dias[0], "end_date": dias[-1]})
    return json.loads(get(f"https://ensemble-api.open-meteo.com/v1/ensemble?{q}"))["hourly"]


def avisos():
    """Avisos de lluvia y tormenta de AEMET, del feed de Meteoalarm."""
    s = get("https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-spain")
    res = []
    for ent in re.findall(r"<entry>.*?</entry>", s, re.S):
        def campo(c):
            m = re.search(rf"<cap:{c}>(.*?)<", ent)
            return m.group(1) if m else ""
        zona, evento = campo("areaDesc"), campo("event")
        if zona not in (C.ZONA_TRAYECTO, C.ZONA_CERCANA):
            continue
        tipo = "tempestes" if "thunderstorm" in evento else "pluja" if "rain" in evento else None
        if not tipo:
            continue
        nivel = {"Moderate": "groc", "Severe": "taronja", "Extreme": "vermell"}.get(
            evento.split()[0], evento)
        res.append({"zona": zona, "tipo": tipo, "nivel": nivel,
                    "inicio": dt.datetime.fromisoformat(campo("onset")).astimezone().isoformat(),
                    "fin": dt.datetime.fromisoformat(campo("expires")).astimezone().isoformat()})
    # El feed repite entradas idénticas.
    unicos = {tuple(sorted(a.items())) for a in res}
    return sorted((dict(t) for t in unicos), key=lambda a: (a["inicio"], a["zona"], a["tipo"]))


PLANES_PC_URL = "https://analisi.transparenciacatalunya.cat/resource/wj9c-j6vf.json"


def afecta_al_trayecto(descripcion):
    """Un plan afecta salvo que su descripción nombre solo otras zonas."""
    d = descripcion or ""
    if any(z in d for z in C.ZONAS_PROPIAS_PC):
        return True
    return not any(z in d for z in C.ZONAS_AJENAS_PC)


def planes_proteccion_civil():
    """Planes meteorológicos de Protección Civil activados (datos abiertos de
    la Generalitat, actualizados en tiempo real), uno por plan."""
    res = {}
    for p in json.loads(get(PLANES_PC_URL)):
        acronimo = p.get("plaacronim", "")
        if (p.get("plaactivat") != "SI" or acronimo not in C.PLANES_PC
                or not afecta_al_trayecto(p.get("descripcio"))):
            continue
        if acronimo in res:
            continue
        res[acronimo] = {"pla": acronimo, "nom": C.PLANES_PC[acronimo],
                         "fase": (p.get("plafase") or "").lower(),
                         "des_de": p.get("fasedatahora"),
                         "descripcio": (p.get("descripcio") or "").strip(" -"),
                         "comunicat": (p.get("comunicatpdf") or {}).get("url")}
    return list(res.values())


def texto_plan(p):
    return f"Protecció Civil té activat el pla {p['nom']} ({p['pla']}) en fase d'{p['fase']}."


# --- Decisión ------------------------------------------------------------------

def valores_ventana(serie_horas, serie_valores, dia, ventana):
    hs = horas_ventana(ventana)
    return [v for t, v in zip(serie_horas, serie_valores)
            if t.startswith(dia) and int(t[11:13]) in hs and v is not None]


def tiempo_ventana(dia, ventana, m):
    """Temperatura y rachas de viento en la ventana, en los dos extremos del
    trayecto, del modelo más fino que tenga datos."""
    if not m:
        return None
    ini, fin = (dt.time.fromisoformat(x) for x in ventana)
    horas = set(range(ini.hour, fin.hour + (2 if fin.minute else 1)))
    for mod in C.MODELOS_FINOS:
        temp, ratxa = [], []
        for loc in m:
            h = loc["hourly"]
            for i, t in enumerate(h["time"]):
                if t.startswith(dia) and int(t[11:13]) in horas:
                    v = h.get(f"temperature_2m_{mod}", [None] * (i + 1))[i]
                    w = h.get(f"wind_gusts_10m_{mod}", [None] * (i + 1))[i]
                    if v is not None:
                        temp.append(v)
                    if w is not None:
                        ratxa.append(w)
        if temp:
            return {"temp_min": round(min(temp)), "temp_max": round(max(temp)),
                    "ratxa_max": round(max(ratxa)) if ratxa else None}
    return None


def decidir(dia, ventana, d):
    """Riesgo de lluvia en una ventana: moto (bajo), compte (moderado) o
    cotxe (alto), con los motivos en catalán."""
    ini, fin = momento(dia, ventana[0]), momento(dia, ventana[1])
    motivos = []          # (peso, nivel, texto); el peso ordena la lista
    # Todo lo que se ha mirado, en números, para el registro (registre.py):
    # con él se podrá ajustar un modelo estadístico con todas las fuentes.
    senyals = {}

    # 1. Avisos que tocan la ventana. Lluvia y tormenta con el mismo horario
    # se cuentan juntas; los de la costa solo si no hay ninguno en el Vallès.
    grupos = {}
    for a in d.get("avisos") or []:
        a_ini, a_fin = (dt.datetime.fromisoformat(a[k]) for k in ("inicio", "fin"))
        if a_ini <= fin and a_fin >= ini:
            grupos.setdefault((a["zona"], a["nivel"], a_ini, a_fin), []).append(a["tipo"])
    hay_valles = any(z == C.ZONA_TRAYECTO for z, *_ in grupos)
    if "avisos" in d:
        for zona, clave in ((C.ZONA_TRAYECTO, "avis_valles"), (C.ZONA_CERCANA, "avis_costa")):
            tipos = sorted({t for (z, *_), ts in grupos.items() if z == zona for t in ts})
            senyals[clave] = tipos
    for (zona, nivel, a_ini, a_fin), tipos in sorted(grupos.items(), key=lambda g: g[0][2]):
        que = " i ".join(sorted(set(tipos)))
        horario = f"de {hm(a_ini)} a {hm(a_fin + dt.timedelta(seconds=1))}"
        if zona == C.ZONA_TRAYECTO:
            motivos.append((0, "cotxe", f"L'AEMET té un avís {nivel} per {que} "
                            f"al Vallès, {horario}."))
        elif not hay_valles:
            motivos.append((1, "compte", f"Hi ha un avís {nivel} per {que} a la costa "
                            f"de Barcelona, {horario}."))
    if "avisos" in d and not grupos:
        motivos.append((5, "moto", "L'AEMET no té cap avís de pluja ni de tempesta "
                        "per a aquesta hora."))

    # 1 bis. Planes de Protección Civil: en alerta o emergencia, riesgo alto.
    for p in d.get("planes") or []:
        senyals.setdefault("proteccio_civil", []).append(f"{p['pla']}:{p['fase']}")
        if p["fase"] in ("alerta", "emergència"):
            motivos.append((0, "cotxe", texto_plan(p)))

    # 2. Radar y estaciones: solo valen mientras la ventana no ha terminado y
    # empieza en las próximas horas.
    falta = (ini - AHORA).total_seconds() / 3600
    vigente = AHORA < fin
    r = d.get("radar")
    if r and vigente and falta <= 3:
        km = r["km_lluvia"]
        crece = r["km2_50km_ahora"] > 1.3 * max(r["km2_50km_antes"], 1)
        tendencia = ", i la zona de pluja creix" if crece else ""
        senyals["radar"] = {"km": km, "creix": crece}
        if km is not None and km <= C.RADAR_COCHE_KM:
            on = "damunt del trajecte" if km < 2 else f"a {km:.0f} km del trajecte"
            motivos.append((0, "cotxe" if crece else "compte",
                            f"El radar veu pluja {on}{tendencia}."))
        elif km is not None and km <= C.RADAR_ATENCION_KM:
            motivos.append((2, "compte", f"El radar veu pluja a {km:.0f} km{tendencia}."))
        else:
            motivos.append((4, "moto", "El radar no veu pluja a prop."))
    obs = d.get("observaciones")
    if obs and vigente and falta <= 1.5:
        mullades = [o for o in obs if o["mm_ultima_media_hora"] > 0 or (o.get("intensitat") or 0) > 0]
        senyals["estacions"] = {o["estacion"]: {"mm_30min": o["mm_ultima_media_hora"],
                                                "intensitat": o.get("intensitat")} for o in obs}
        if mullades:
            parts = []
            for o in mullades:
                detall = (f"{coma(o['intensitat'])}\u00a0mm/h" if o.get("intensitat")
                          else f"{coma(o['mm_ultima_media_hora'])}\u00a0mm en mitja hora")
                parts.append(f"{o['estacion']}, {detall} a les "
                             f"{hm(dt.datetime.fromisoformat(o['hasta']))}")
            motivos.append((0, "cotxe", f"Plou a {', i a '.join(parts)}."))
        else:
            noms = ", ".join(o["estacion"] for o in obs)
            hores = sorted({hm(dt.datetime.fromisoformat(o["hasta"])) for o in obs})
            motivos.append((4, "moto", f"Les estacions ({noms}) no registren pluja "
                            f"(dades de les {' i '.join(hores)})."))

    # 3. Modelos finos: lo máximo que dan en cualquiera de los dos extremos.
    m = d.get("modelos")
    if m:
        maximo = 0.0
        por_modelo, cape = {}, []
        for loc in m:
            h = loc["hourly"]
            for mod in C.MODELOS_FINOS + C.MODELOS_GLOBALES:
                vals = valores_ventana(h["time"], h.get(f"precipitation_{mod}", []), dia, ventana)
                if vals:
                    por_modelo[mod] = max([por_modelo.get(mod, 0.0)] + vals)
                if mod in C.MODELOS_FINOS:
                    maximo = max([maximo] + vals)
                cape += valores_ventana(h["time"], h.get(f"cape_{mod}", []), dia, ventana)
        senyals["models_mm"] = por_modelo
        senyals["cape"] = max(cape) if cape else None
        if maximo >= C.UMBRAL_MM_COCHE:
            nivel, peso, texto = "cotxe", 1, ("Els models més detallats preveuen pluja clara "
                                              f"(fins a {coma(maximo)}\u00a0mm en una hora).")
        elif maximo >= C.UMBRAL_MM:
            nivel, peso, texto = "compte", 2, ("Els models més detallats preveuen una mica "
                                               f"de pluja ({coma(maximo)}\u00a0mm en una hora).")
        else:
            nivel, peso, texto = "moto", 3, "Els models més detallats no preveuen pluja."
        motivos.append((peso, nivel, texto + frase_historico(ventana, nivel)))

    # 4. Ensemble: fracción de simulaciones con lluvia.
    e = d.get("ensemble")
    if e:
        claves = [k for k in e if k.startswith("precipitation")]
        mullats = sum(any(v >= C.UMBRAL_MM for v in valores_ventana(e["time"], e[k], dia, ventana))
                      for k in claves)
        prob = mullats / len(claves) if claves else 0
        senyals["simulacions"] = round(prob, 3)
        nivel = "cotxe" if prob >= C.PROB_COCHE else "compte" if prob >= C.PROB_ATENCION else "moto"
        motivos.append(({"cotxe": 1, "compte": 2, "moto": 3}[nivel], nivel,
                        f"{mullats} de cada {len(claves)} simulacions hi posen pluja "
                        f"({round(prob * 100)}\u00a0% de probabilitat)."))

    temps = tiempo_ventana(dia, ventana, d.get("modelos"))

    orden = ORDEN
    if not motivos:
        motivos.append((0, "compte", "No s'han pogut obtenir dades."))
    veredicto = max((n for _, n, _ in motivos), key=orden.index)
    motivos.sort(key=lambda x: (x[0], -orden.index(x[1])))
    return {
        "dia": dia, "inici": ventana[0], "fi": ventana[1],
        "passat": fin < AHORA,
        "nivell": veredicto,
        "temps": temps,
        "senyals": senyals,
        "motius": [{"nivell": n, "text": t} for _, n, t in motivos],
    }


ORDEN = ["moto", "compte", "cotxe"]


def peor(*niveles):
    return max(niveles, key=ORDEN.index)


def leer_comentario(ruta):
    """Comentario del agente diario (agent/), si lo hay."""
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return None


def comentario_vigente(c, dia, anada, tornada):
    """Vale mientras el programa siga dando los mismos niveles que cuando se
    escribió: si cambian, el comentario se ha quedado viejo."""
    if not c or c.get("dia") != dia:
        return False
    antes = c.get("nivells_programa", {})
    if c.get("mode") == "tarda":
        return antes.get("tornada") == tornada["nivell"]
    return antes.get("anada") == anada["nivell"] and antes.get("tornada") == tornada["nivell"]


def decidir_dia(dia, d, anterior=None, comentario=None):
    """Un solo medio para ida y vuelta: el del trayecto más desfavorable.

    Hasta el final de la ventana de ida (7:30) se recalcula en cada ejecución,
    porque puede salir en cualquier momento de la ventana. Desde entonces se
    mantiene la decisión publicada antes (ya ha salido de casa); la web deja
    de mostrar el medio y solo da el tiempo de la vuelta.
    """
    anada, tornada = decidir(dia, C.IDA, d), decidir(dia, C.VUELTA, d)
    # Margen de cinco minutos para que la pasada de las 7:30, que empieza unos
    # segundos después, aún recalcule.
    salida = momento(dia, C.IDA[1]) + dt.timedelta(minutes=5)
    previa = anterior if anterior and anterior.get("dia") == dia and "decisio" in anterior else None
    if AHORA >= salida and previa:
        decision = dict(previa["decisio"], mantinguda=True)
        anada = previa["anada"]
        anada["passat"] = momento(dia, C.IDA[1]) < AHORA
    else:
        decision = {"mitja": peor(anada["nivell"], tornada["nivell"]),
                    "decidit": AHORA.isoformat(timespec="minutes"),
                    "abans_de_sortir": AHORA < salida,
                    "mantinguda": False}
        # El agente puede hacer la recomendación más prudente, nunca menos.
        if (comentario_vigente(comentario, dia, anada, tornada)
                and comentario.get("mode") == "mati"
                and ORDEN.index(comentario["mitja"]) > ORDEN.index(decision["mitja"])):
            decision.update(mitja=comentario["mitja"], per_la_ia=True)
    salida_c = None
    if comentario and comentario.get("dia") == dia:
        salida_c = dict(comentario, vigent=comentario_vigente(comentario, dia, anada, tornada))
    return {"dia": dia, "decisio": decision, "anada": anada, "tornada": tornada,
            "comentari": salida_c}


def llegir_anterior(origen):
    try:
        if origen.startswith("http"):
            return json.loads(get(origen))
        with open(origen, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def recoger(anterior=None, comentario=None):
    dia = AHORA.date().isoformat()
    d, errores = {}, []
    for clave, funcion in (("avisos", avisos), ("planes", planes_proteccion_civil),
                           ("observaciones", observaciones),
                           ("radar", radar), ("modelos", lambda: modelos([dia])),
                           ("ensemble", lambda: ensemble([dia]))):
        try:
            d[clave] = funcion()
        except Exception as ex:
            errores.append(f"{clave}: {ex}")
    return {
        "versio": C.VERSION,
        "generat": AHORA.isoformat(timespec="minutes"),
        "horari": {"trams": C.HORARIO, "cada_min": C.INTERVALO_MIN},
        "errors": errores,
        "avisos": d.get("avisos"),
        "plans": d.get("planes"),
        "radar": d.get("radar"),
        "observacions": d.get("observaciones"),
        **decidir_dia(dia, d, anterior, comentario),
    }


if __name__ == "__main__":
    args = sys.argv
    anterior = llegir_anterior(args[args.index("--anterior") + 1]) if "--anterior" in args else None
    comentario = leer_comentario(args[args.index("--comentari") + 1]) if "--comentari" in args else None
    datos = recoger(anterior, comentario)
    if "--json" in args:
        with open(args[args.index("--json") + 1], "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
    dec = datos["decisio"]
    print(f"Generado {datos['generat']}")
    for error in datos["errors"]:
        print("  fallo:", error)
    print(f"\n{datos['dia']}: {dec['mitja'].upper()} (decidido {dec['decidit']}"
          + (", se mantiene" if dec["mantinguda"] else "") + ")")
    for nombre in ("anada", "tornada"):
        v = datos[nombre]
        print(f"\n{nombre} {v['inici']}-{v['fi']}: riesgo {v['nivell']}"
              + (" (ya pasó)" if v["passat"] else ""))
        for m in v["motius"]:
            print(f"  [{m['nivell']}] {m['text']}")
