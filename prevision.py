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
    """Frecuencia real de lluvia en cada nivel de la regla (calibracio/)."""
    try:
        with open(os.path.join(DIR, "calibracio", "calibracio.json"), encoding="utf-8") as f:
            return json.load(f)["ventanas"]
    except (OSError, KeyError, ValueError):
        return {}


CALIBRACION = leer_calibracion()


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


def observaciones_web(codi, nom):
    """Lluvia de hoy según la página de meteo.cat (la tabla va en UTC)."""
    s = get(f"https://www.meteo.cat/observacions/xema/dades?codi={codi}")
    t = re.search(r"<table[^>]*tblperiode.*?</table>", s, re.S)
    cab, filas = None, []
    for f in re.findall(r"<tr.*?</tr>", t.group(0), re.S) if t else []:
        celdas = [html.unescape(re.sub("<[^>]+>", "", c)).strip()
                  for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", f, re.S)]
        if celdas and celdas[0].startswith("Període"):
            cab = celdas
        elif cab and len(celdas) > 1 and "(s/d)" not in celdas[1]:
            filas.append(dict(zip(cab, celdas)))
    if not filas:
        return None
    col = next(k for k in cab if k.startswith("PPT"))
    fin_utc = filas[-1][cab[0]].split("-")[-1].strip()
    hora = dt.datetime.combine(AHORA.astimezone(dt.timezone.utc).date(),
                               dt.time.fromisoformat(fin_utc), dt.timezone.utc)
    return {"estacion": nom, "font": "meteo.cat",
            "mm_hoy": round(sum(float(x[col]) for x in filas), 1),
            "mm_ultima_media_hora": float(filas[-1][col]),
            "hasta": hora.astimezone().isoformat()}


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
        "hourly": "precipitation",
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


# --- Decisión ------------------------------------------------------------------

def valores_ventana(serie_horas, serie_valores, dia, ventana):
    hs = horas_ventana(ventana)
    return [v for t, v in zip(serie_horas, serie_valores)
            if t.startswith(dia) and int(t[11:13]) in hs and v is not None]


def decidir(dia, ventana, d):
    """Riesgo de lluvia en una ventana: moto (bajo), compte (moderado) o
    cotxe (alto), con los motivos en catalán."""
    ini, fin = momento(dia, ventana[0]), momento(dia, ventana[1])
    motivos = []          # (peso, nivel, texto); el peso ordena la lista

    # 1. Avisos que tocan la ventana. Lluvia y tormenta con el mismo horario
    # se cuentan juntas; los de la costa solo si no hay ninguno en el Vallès.
    grupos = {}
    for a in d.get("avisos") or []:
        a_ini, a_fin = (dt.datetime.fromisoformat(a[k]) for k in ("inicio", "fin"))
        if a_ini <= fin and a_fin >= ini:
            grupos.setdefault((a["zona"], a["nivel"], a_ini, a_fin), []).append(a["tipo"])
    hay_valles = any(z == C.ZONA_TRAYECTO for z, *_ in grupos)
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

    # 2. Radar y estaciones: solo valen mientras la ventana no ha terminado y
    # empieza en las próximas horas.
    falta = (ini - AHORA).total_seconds() / 3600
    vigente = AHORA < fin
    r = d.get("radar")
    if r and vigente and falta <= 3:
        km = r["km_lluvia"]
        crece = r["km2_50km_ahora"] > 1.3 * max(r["km2_50km_antes"], 1)
        tendencia = ", i la zona de pluja creix" if crece else ""
        if km is not None and km <= C.RADAR_COCHE_KM:
            motivos.append((0, "cotxe" if crece else "compte",
                            f"El radar veu pluja a {km:.0f} km del trajecte{tendencia}."))
        elif km is not None and km <= C.RADAR_ATENCION_KM:
            motivos.append((2, "compte", f"El radar veu pluja a {km:.0f} km{tendencia}."))
        else:
            motivos.append((4, "moto", "El radar no veu pluja a prop."))
    obs = d.get("observaciones")
    if obs and vigente and falta <= 1.5:
        mullades = [o for o in obs if o["mm_ultima_media_hora"] > 0 or (o.get("intensitat") or 0) > 0]
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
        for loc in m:
            h = loc["hourly"]
            for mod in C.MODELOS_FINOS:
                vals = valores_ventana(h["time"], h.get(f"precipitation_{mod}", []), dia, ventana)
                maximo = max([maximo] + vals)
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
        nivel = "cotxe" if prob >= C.PROB_COCHE else "compte" if prob >= C.PROB_ATENCION else "moto"
        motivos.append(({"cotxe": 1, "compte": 2, "moto": 3}[nivel], nivel,
                        f"{mullats} de cada {len(claves)} simulacions hi posen pluja "
                        f"({round(prob * 100)}\u00a0% de probabilitat)."))

    orden = ORDEN
    if not motivos:
        motivos.append((0, "compte", "No s'han pogut obtenir dades."))
    veredicto = max((n for _, n, _ in motivos), key=orden.index)
    motivos.sort(key=lambda x: (x[0], -orden.index(x[1])))
    return {
        "dia": dia, "inici": ventana[0], "fi": ventana[1],
        "passat": fin < AHORA,
        "nivell": veredicto,
        "motius": [{"nivell": n, "text": t} for _, n, t in motivos],
    }


ORDEN = ["moto", "compte", "cotxe"]


def peor(*niveles):
    return max(niveles, key=ORDEN.index)


def decidir_dia(dia, d, anterior=None):
    """Un solo medio para ida y vuelta: el del trayecto más desfavorable.

    Hasta el final de la ventana de ida (7:30) se recalcula en cada ejecución,
    porque puede salir en cualquier momento de la ventana. Desde entonces se
    mantiene la decisión publicada antes (ya ha salido de casa) y solo se avisa
    si la vuelta ha empeorado respecto a lo decidido.
    """
    anada, tornada = decidir(dia, C.IDA, d), decidir(dia, C.VUELTA, d)
    salida = momento(dia, C.IDA[1])
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
    avis_tornada = None
    if (decision["mantinguda"] and not tornada["passat"]
            and ORDEN.index(tornada["nivell"]) > ORDEN.index(decision["mitja"])):
        avis_tornada = ("La previsió per a la tornada ha empitjorat des del matí. "
                        if tornada["nivell"] == "cotxe" else
                        "Ara hi ha una mica de risc de pluja a la tornada. ") + \
            "Porta l'impermeable o, si pots, espera que passi el ruixat."
    return {"dia": dia, "decisio": decision, "avis_tornada": avis_tornada,
            "anada": anada, "tornada": tornada}


def llegir_anterior(origen):
    try:
        if origen.startswith("http"):
            return json.loads(get(origen))
        with open(origen, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def recoger(anterior=None):
    dia = AHORA.date().isoformat()
    d, errores = {}, []
    for clave, funcion in (("avisos", avisos), ("observaciones", observaciones),
                           ("radar", radar), ("modelos", lambda: modelos([dia])),
                           ("ensemble", lambda: ensemble([dia]))):
        try:
            d[clave] = funcion()
        except Exception as ex:
            errores.append(f"{clave}: {ex}")
    return {
        "versio": C.VERSION,
        "generat": AHORA.isoformat(timespec="minutes"),
        "errors": errores,
        "avisos": d.get("avisos"),
        "radar": d.get("radar"),
        "observacions": d.get("observaciones"),
        **decidir_dia(dia, d, anterior),
    }


if __name__ == "__main__":
    args = sys.argv
    anterior = llegir_anterior(args[args.index("--anterior") + 1]) if "--anterior" in args else None
    datos = recoger(anterior)
    if "--json" in args:
        with open(args[args.index("--json") + 1], "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
    dec = datos["decisio"]
    print(f"Generado {datos['generat']}")
    for error in datos["errors"]:
        print("  fallo:", error)
    print(f"\n{datos['dia']}: {dec['mitja'].upper()} (decidido {dec['decidit']}"
          + (", se mantiene" if dec["mantinguda"] else "") + ")")
    if datos["avis_tornada"]:
        print("  Aviso vuelta:", datos["avis_tornada"])
    for nombre in ("anada", "tornada"):
        v = datos[nombre]
        print(f"\n{nombre} {v['inici']}-{v['fi']}: riesgo {v['nivell']}"
              + (" (ya pasó)" if v["passat"] else ""))
        for m in v["motius"]:
            print(f"  [{m['nivell']}] {m['text']}")
