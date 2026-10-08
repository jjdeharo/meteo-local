#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""El bot de Telegram de Temps a Montflorit (@TempsMontfloritBot, ADR 0034).

Vive en el hosting de IONOS, no en el NAS: un corte de luz en casa durante una
tormenta no lo para. El cron lo arranca cada minuto y, durante unos 50
segundos, espera mensajes de Telegram (contesta en uno o dos segundos) y
reparte:

- los avisos que el NAS (o la reserva) deja en avisos.json (avisos_bot.py), a
  quien los haya elegido, y los de riera y peligro también al canal
  @TempsMontflorit (solo en catalán);
- el resumen del día, a la hora que elija cada uno, y al canal a las 7.

Cada persona elige en un menú con botones qué avisos quiere (riera, peligro,
lluvia en unos minutos, trenes), la hora del resumen y el idioma. Solo se
guarda su identificador de Telegram y lo que elige; /baixa lo borra. Sin
dependencias: solo la biblioteca estándar.

Uso: bot.py           una vuelta (lo que hace el cron, cada minuto)
     bot.py estat     suscriptores y avisos repartidos
     bot.py informe   el recuento, a Juanjo por Telegram (el cron, los lunes)
"""
import datetime as dt
import fcntl
import html
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# La hora local de Montflorit, pase lo que pase con la del hosting.
os.environ.setdefault("TZ", "Europe/Madrid")
time.tzset()

BASE = os.environ.get("BOT_DIR", os.path.expanduser("~/.temps-bot"))
DADES = os.environ.get("BOT_DADES", os.path.expanduser("~/app/meteo-local"))
REPO = os.environ.get("BOT_REPO", os.path.expanduser("~/.meteo-reserva/repo"))
SUBS = os.path.join(BASE, "subscriptors.json")
ESTAT = os.path.join(BASE, "estat.json")
CANAL = os.environ.get("BOT_CANAL", "@TempsMontflorit")
WEB = "https://meteo-montflorit.github.io/"
DURADA_S = 50
TIPUS = ("riera", "perill", "pluja", "trens")
PER_DEFECTE = ["riera", "perill"]
CANAL_TIPUS = ("riera", "perill")
HORES_RESUM = ("6", "7", "8", "20")
CANAL_RESUM = "7"
# Un aviso que llega tarde ya no sirve: lluvia en 15 minutos, como mucho 20.
VIGENCIA_MIN = {"pluja": 20, "perill": 180, "riera": 180, "trens": 180}
DADES_VELLES_H = 2

T = {
    "ca": {
        "benvinguda": ("<b>Bot Temps a Montflorit</b>\nT'enviaré, només a tu, els avisos del temps a Montflorit "
                       "(Cerdanyola del Vallès) que triïs a continuació. Els calcula un programa amb dades públiques: "
                       "són orientatius, no oficials. Segueix sempre les indicacions de Protecció Civil i de "
                       "l'Ajuntament.\n" + WEB),
        "inici": "Per començar, t'he activat els avisos de la riera i de perill.",
        "menu": ("Toca el que vulguis rebre. ✓ vol dir que sí; si el tornes a tocar, es treu.\n"
                 "La previsió arriba un cop al dia, a l'hora que triïs.\n\n"
                 "Si també ets al canal (@TempsMontflorit), no et repetiré el que ja t'arriba per allà: els avisos "
                 "de la riera i de perill i la previsió de les 7 h.\n\n"
                 "Només es desa el teu identificador de Telegram i el que triïs aquí. Amb /baixa s'esborra tot."),
        "riera": "Desbordament de la riera de Sant Cugat (en proves)", "perill": "Situacions de perill",
        "pluja": "Pluja a punt de començar (15 min abans)", "trens": "Trens de Cerdanyola (si no circulen)",
        "resum": "Previsió, un cop al dia, a les:", "no": "No vull rebre la previsió", "h": "{} h", "dema": "{} h (per a demà)",
        "baixa": "Fet: s'han esborrat les teves dades i ja no rebràs res. Amb /start pots tornar-hi.",
        "ajuda": ("/avisos tria què reps · /resum la previsió d'avui · /dema la de demà · /ara el temps ara · "
                  "/radar el radar ara · /trens els trens · /avisos_actius els avisos oficials · "
                  "/baixa deixa de rebre'n i esborra les teves dades"),
        "velles": "Les dades de Temps a Montflorit no s'actualitzen des de les {}: ara no puc donar la previsió.",
        "velles_ara": "Les dades de Temps a Montflorit no s'actualitzen des de les {}: ara no puc dir el temps que fa.",
        "sense_previsio": "Ara no hi ha previsió disponible: les dades de les {} no en porten.",
        "mesura": " (mesura de les {})",
    },
    "es": {
        "benvinguda": ("<b>Bot Temps a Montflorit</b>\nTe enviaré, solo a ti, los avisos del tiempo en Montflorit "
                       "(Cerdanyola del Vallès) que elijas a continuación. Los calcula un programa con datos públicos: "
                       "son orientativos, no oficiales. Sigue siempre las indicaciones de Protección Civil y del "
                       "Ayuntamiento.\n" + WEB),
        "inici": "Para empezar, te he activado los avisos de la riera y de peligro.",
        "menu": ("Toca lo que quieras recibir. ✓ quiere decir que sí; si lo vuelves a tocar, se quita.\n"
                 "La previsión llega una vez al día, a la hora que elijas.\n\n"
                 "Si también estás en el canal (@TempsMontflorit), no te repetiré lo que ya te llega por allí, en "
                 "catalán: los avisos de la riera y de peligro y la previsión de las 7 h.\n\n"
                 "Solo se guarda tu identificador de Telegram y lo que elijas aquí. Con /baixa se borra todo."),
        "riera": "Desbordamiento de la riera de Sant Cugat (en pruebas)", "perill": "Situaciones de peligro",
        "pluja": "Lluvia a punto de empezar (15 min antes)", "trens": "Trenes de Cerdanyola (si no circulan)",
        "resum": "Previsión, una vez al día, a las:", "no": "No quiero recibir la previsión", "h": "{} h", "dema": "{} h (para mañana)",
        "baixa": "Hecho: se han borrado tus datos y ya no recibirás nada. Con /start puedes volver.",
        "ajuda": ("/avisos elige qué recibes · /resum la previsión de hoy · /dema la de mañana · /ara el tiempo ahora · "
                  "/radar el radar ahora · /trens los trenes · /avisos_actius los avisos oficiales · "
                  "/baixa deja de recibir y borra tus datos"),
        "velles": "Los datos de Temps a Montflorit no se actualizan desde las {}: ahora no puedo dar la previsión.",
        "velles_ara": "Los datos de Temps a Montflorit no se actualizan desde las {}: ahora no puedo decir el tiempo que hace.",
        "sense_previsio": "Ahora no hay previsión disponible: los datos de las {} no la traen.",
        "mesura": " (medida de las {})",
    },
}


def ara():
    return dt.datetime.now().astimezone()


def llegeix(ruta, defecte):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecte


def desa(ruta, dades):
    with open(ruta + ".tmp", "w", encoding="utf-8") as f:
        json.dump(dades, f, ensure_ascii=False)
    os.replace(ruta + ".tmp", ruta)


# Lo que falla queda apuntado (errors.log, junto al estado), sin
# identificadores de nadie: solo el aviso, cuántos chats y el motivo. Hasta la
# auditoría del 07-10-2026 los fallos de Telegram se silenciaban y un aviso
# podía caducar sin dejar rastro (ADR 0038).
REGISTRE_MAX = 500_000


def registra(text):
    ruta = os.path.join(BASE, "errors.log")
    try:
        os.makedirs(BASE, exist_ok=True)
        if os.path.exists(ruta) and os.path.getsize(ruta) > REGISTRE_MAX:
            os.replace(ruta, ruta + ".1")
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(f"{ara():%F %T}  {text}\n")
    except OSError:
        pass


# --- Telegram ------------------------------------------------------------------

class Api:
    def __init__(self, token):
        self.url = f"https://api.telegram.org/bot{token}/"

    def __call__(self, metode, temps=30, **params):
        dades = urllib.parse.urlencode({k: json.dumps(v) if isinstance(v, (dict, list)) else v
                                        for k, v in params.items() if v is not None}).encode()
        try:
            with urllib.request.urlopen(self.url + metode, dades, timeout=temps) as r:
                return json.load(r).get("result")
        except urllib.error.HTTPError as ex:
            resposta = json.load(ex)
            if ex.code == 403:          # la persona ha bloqueado el bot
                raise Bloquejat() from ex
            raise RuntimeError(f"{metode}: {resposta.get('description')}") from ex


class Bloquejat(Exception):
    pass


# Las unidades no se separan de su número al partir la línea.
UNITATS = re.compile(r"(\d) (°C|mm|km/h|cm)\b")


def envia(api, chat, text, teclat=None, html=False):
    return api("sendMessage", chat_id=chat, text=UNITATS.sub("\\1\u00a0\\2", text), disable_web_page_preview=True,
               parse_mode="HTML" if html else None,
               reply_markup={"inline_keyboard": teclat} if teclat else None)


# --- Menú ----------------------------------------------------------------------

def teclat(sub):
    t = T[sub["idioma"]]
    # Una sola marca: ✓ vol dir sí o triat; sense marca, no (Juanjo, 07-10-2026).
    marca = lambda si: "✓ " if si else ""
    files = [[{"text": marca(x in sub["avisos"]) + t[x], "callback_data": f"t:{x}"}] for x in TIPUS]
    files.append([{"text": t["resum"], "callback_data": "-"}])
    files.append([{"text": marca(sub.get("resum") == h) + t["dema" if int(h) >= HORA_DEMA else "h"].format(h),
                   "callback_data": f"r:{h}"} for h in HORES_RESUM])
    files.append([{"text": marca(not sub.get("resum")) + t["no"], "callback_data": "r:no"}])
    files.append([{"text": marca(sub["idioma"] == i) + n, "callback_data": f"i:{i}"}
                  for i, n in (("ca", "Català"), ("es", "Castellano"))])
    return files


def nou_subscriptor(usuari):
    idioma = "es" if (usuari.get("language_code") or "").startswith("es") else "ca"
    return {"idioma": idioma, "avisos": list(PER_DEFECTE), "resum": None,
            "alta": ara().isoformat(timespec="minutes")}


def canvia(sub, dada):
    """Aplica un botón del menú. Devuelve True si cambia algo."""
    tipus, _, valor = dada.partition(":")
    if tipus == "t" and valor in TIPUS:
        sub["avisos"] = [x for x in TIPUS if (x in sub["avisos"]) != (x == valor)]
    elif tipus == "r" and (valor in HORES_RESUM or valor == "no"):
        sub["resum"] = None if valor == "no" else valor
    elif tipus == "i" and valor in T:
        sub["idioma"] = valor
    else:
        return False
    return True


# --- Resumen y tiempo ahora -------------------------------------------------------

def graus(t):
    return f"{round(t)} °C".replace("-", "−")


def franges(hores):
    """[(inici, fi, prob)] de les hores seguides amb risc de pluja."""
    res = []
    for f in hores:
        # Como en la web: decide la probabilidad; sin ella, los milímetros.
        p = f.get("probabilitat")
        if (p >= 0.2) if p is not None else (f.get("pluja_mm") or 0) >= 0.2:
            p = p or 0
            h = dt.datetime.fromisoformat(f["hora"])
            if res and res[-1][1] == h:
                res[-1] = (res[-1][0], h + dt.timedelta(hours=1), max(res[-1][2], p))
            else:
                res.append((h, h + dt.timedelta(hours=1), p))
    return res


def text_ara(dades, idioma, lloc=""):
    """Como la web: la temperatura, de la estación particular (la de Montflorit
    marca de más por la tarde); la lluvia, de cualquiera de las dos."""
    a, c = dades.get("ara") or {}, dades.get("ara_casa") or {}
    t = c["temperatura"] if c.get("temperatura") is not None else a.get("temperatura")
    if t is None:
        return None
    plou = (a.get("intensitat") or 0) > 0 or (a.get("pluja_30min") or 0) > 0 or bool(c.get("plou"))
    # Sense Montflorit, el zero del pluviòmetre de casa no vol dir que no plogui
    # (ADR 0017): només es diu la temperatura (auditoria del 08-10-2026).
    if not a and not plou:
        return f"{'Ahora mismo' if idioma == 'es' else 'Ara mateix'}{lloc and (' en ' if idioma == 'es' else ' a ') + lloc}: {graus(t)}."
    if idioma == "es":
        return f"Ahora mismo{lloc and ' en ' + lloc}: {graus(t)}, {'llueve' if plou else 'no llueve'}."
    return f"Ara mateix{lloc and ' a ' + lloc}: {graus(t)}, {'plou' if plou else 'no plou'}."


def text_ara_bot(dades, idioma, moment):
    """La respuesta a /ara: como text_ara, pero con el mismo límite de edad
    que el resumen, también para la propia medida, y diciendo de qué hora es
    (auditoría del 07-10-2026)."""
    t = T[idioma]
    generat = dades.get("generat") and dt.datetime.fromisoformat(dades["generat"])
    if not generat or moment - generat > dt.timedelta(hours=DADES_VELLES_H):
        return t["velles_ara"].format(generat.strftime("%H:%M") if generat else "?")
    a, c = dades.get("ara") or {}, dades.get("ara_casa") or {}
    hora = (c if c.get("temperatura") is not None else a).get("hora")
    mesura = hora and dt.datetime.fromisoformat(hora)
    if mesura and moment - mesura > dt.timedelta(hours=DADES_VELLES_H):
        return t["velles_ara"].format(mesura.strftime("%H:%M"))
    text = text_ara(dades, idioma, "Montflorit")
    if not text:
        return t["ajuda"]
    return text + (t["mesura"].format(mesura.strftime("%H:%M")) if mesura else "")


DIES = {"ca": ("dilluns", "dimarts", "dimecres", "dijous", "divendres", "dissabte", "diumenge"),
        "es": ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")}
# A partir de esta hora, la previsión es para el día siguiente.
HORA_DEMA = 18


def text_pluja(tram, idioma):
    pluges = franges(tram)
    if idioma == "es":
        return ("Lluvia: " + "; ".join(f"posible de {a.hour} a {b.hour} h (probabilidad hasta el {round(p * 100)} %)"
                                       for a, b, p in pluges) + ".") if pluges else "Sin lluvia prevista."
    return ("Pluja: " + "; ".join(f"possible de {a.hour} a {b.hour} h (probabilitat fins al {round(p * 100)} %)"
                                  for a, b, p in pluges) + ".") if pluges else "Sense pluja prevista."


def text_temperatura(tram, idioma, quan):
    temps = [f["temperatura"] for f in tram if f.get("temperatura") is not None]
    i = " y " if idioma == "es" else " i "
    return f"{quan}: entre {graus(min(temps))}{i}{graus(max(temps))}." if temps else None


# La ropa para ir a pie, con los mismos tramos que «Si surts» (web/sortir.js,
# ADR 0029): temperatura que se nota con el viento previsto, redondeada. Las
# pruebas comprueban que las dos tablas dicen lo mismo.
ROBA = ((0, "Abric, gorro, bufanda i guants", "Abrigo, gorro, bufanda y guantes"),
        (5, "Abric, bufanda i guants", "Abrigo, bufanda y guantes"),
        (10, "Abric", "Abrigo"),
        (14, "Jaqueta", "Chaqueta"),
        (17, "Jaqueta lleugera o jersei", "Chaqueta ligera o jersey"),
        (20, "Màniga llarga o jersei fi", "Manga larga o jersey fino"),
        (24, "Màniga curta o màniga llarga fina", "Manga corta o manga larga fina"),
        (None, "Màniga curta", "Manga corta"))
# Las horas en que se sale de casa: de 7 a 21 h.
HORES_ROBA = range(7, 22)


def es_nota(t, kmh):
    """Índice de Environment Canada: solo con 10 °C o menos y viento."""
    if t > 10 or kmh < 5:
        return t
    v = kmh ** 0.16
    return 13.12 + 0.6215 * t - 11.37 * v + 0.3965 * t * v


def peca(s, idioma):
    for fins, ca, es in ROBA:
        if fins is None or s <= fins:
            return es if idioma == "es" else ca


def text_roba(tram, idioma):
    """La ropa para todo el día: si el momento más frío y el más caluroso
    piden prendas distintas, las dos, por orden de hora."""
    hores = []
    for f in tram:
        h = dt.datetime.fromisoformat(f["hora"])
        if f.get("temperatura") is not None and h.hour in HORES_ROBA:
            # Redondeo como Math.round de la web (round() de Python lleva 14,5 a 14).
            s = math.floor(es_nota(f["temperatura"], f.get("vent") or 0) + 0.5)
            hores.append((h, f["temperatura"], s))
    if not hores:
        return None
    fred, calor = min(hores, key=lambda x: x[2]), max(hores, key=lambda x: x[2])
    cap = "Ropa para ir a pie: " if idioma == "es" else "Roba per anar a peu: "
    if peca(fred[2], idioma) == peca(calor[2], idioma):
        return cap + peca(fred[2], idioma).lower() + "."

    def moment(x):
        h, t, s = x
        nota = (f", se notan como {graus(s)}" if idioma == "es" else f", es noten com {graus(s)}") \
            if s < math.floor(t + 0.5) else ""
        a = "a las" if idioma == "es" else "a les"
        return f"{peca(s, idioma).lower()} {a} {h.hour} h ({graus(t)}{nota})"
    return cap + "; ".join(moment(x) for x in sorted((fred, calor))) + "."


def text_avisos_aemet(dades, idioma, dia, moment):
    """Los avisos de AEMET de un día: hoy, «fins a les 20:00»; mañana, «de 10:00 a 20:00»."""
    # Els que toquen el dia (també els que van començar abans: auditoria del 08-10-2026).
    inici_dia = dt.datetime.combine(dia, dt.time.min, tzinfo=moment.tzinfo)
    avisos = [a for a in dades.get("avisos") or [] if dt.datetime.fromisoformat(a["fin"]) > max(moment, inici_dia)
              and dt.datetime.fromisoformat(a["inicio"]) < inici_dia + dt.timedelta(days=1)]
    res = []
    for nivell in ("vermell", "taronja", "groc"):
        dels = [a for a in avisos if a["nivel"] == nivell]
        if not dels:
            continue
        tipus = sorted({a["tipo"] for a in dels})
        ini = min(dt.datetime.fromisoformat(a["inicio"]) for a in dels).strftime("%H:%M")
        fi = (max(dt.datetime.fromisoformat(a["fin"]) for a in dels) + dt.timedelta(seconds=1)).strftime("%H:%M")
        if idioma == "es":
            nom = {"vermell": "rojo", "taronja": "naranja", "groc": "amarillo"}[nivell]
            que = " y ".join({"pluja": "lluvia", "tempestes": "tormentas"}.get(x, x) for x in tipus)
            quan = f"hasta las {fi}" if dia == moment.date() else f"de {ini} a {fi}"
            res.append(f"Aviso {nom} de la AEMET por {que} {quan}.")
        else:
            quan = f"fins a les {fi}" if dia == moment.date() else f"de {ini} a {fi}"
            res.append(f"Avís {nivell} de l'AEMET per {' i '.join(tipus)} {quan}.")
    return res


def resum(dades, idioma, moment, dema=False, avui=False):
    """La previsión en pocas líneas, con los datos públicos: hasta las 18 h,
    el tiempo ahora y el resto del día; desde las 18 h, la de mañana. Con la
    ropa para ir a pie (text_roba)."""
    t = T[idioma]
    if not dades.get("generat"):
        return t["velles"].format("?")
    generat = dt.datetime.fromisoformat(dades["generat"])
    if moment - generat > dt.timedelta(hours=DADES_VELLES_H):
        return t["velles"].format(generat.strftime("%H:%M"))
    ara_n = moment.replace(tzinfo=None)
    hores = [f for f in dades.get("hores") or [] if dt.datetime.fromisoformat(f["fins"]) > ara_n]
    hora = lambda f: dt.datetime.fromisoformat(f["hora"])
    # /resum demana sempre la d'avui, /dema la de demà; el resum programat
    # canvia a demà a partir de HORA_DEMA (Juanjo, 08-10-2026).
    if dema or (moment.hour >= HORA_DEMA and not avui):
        dema = (moment + dt.timedelta(days=1)).date()
        # La nit comença a les HORA_DEMA d'avui, també si es demana /dema al matí.
        vespre = dt.datetime.combine(moment.date(), dt.time(HORA_DEMA))
        nit = [f for f in hores if vespre <= hora(f) < dt.datetime.combine(dema, dt.time(6))]
        dia = [f for f in hores if hora(f).date() == dema and hora(f).hour >= 6]
        nom_dia = DIES[idioma][dema.weekday()]
        if not dia:     # sense hores de demà, no hi ha previsió, i es diu (auditoria del 08-10-2026)
            return t["sense_previsio"].format(generat.strftime("%H:%M")) + "\n" + WEB
        # Les dades arriben a 24 hores: de nit, demà només fins a la tarda, i es diu.
        fi = dt.datetime.fromisoformat(dia[-1]["fins"]).hour if dia else 0
        fins = (f" (hasta las {fi} h)" if idioma == "es" else f" (fins a les {fi} h)") if 0 < fi < 24 else ""
        linies = [(f"<b>Previsión para mañana, {nom_dia}, en Montflorit</b>" if idioma == "es"
                   else f"<b>Previsió per a demà, {nom_dia}, a Montflorit</b>") + fins]
        if franges(nit):    # la noche, solo si se espera lluvia
            linies.append(("Esta noche: " if idioma == "es" else "Aquesta nit: ")
                          + text_pluja(nit, idioma).split(": ", 1)[1])
        linies.append(text_temperatura(dia, idioma, "Temperatura"))
        linies.append(text_pluja(dia, idioma))
        roba = text_roba(dia, idioma)
        linies += text_avisos_aemet(dades, idioma, dema, moment)
    else:
        fi_dia = ara_n.replace(hour=23, minute=59)
        tram = [f for f in hores if hora(f) < fi_dia]
        nom_dia = DIES[idioma][moment.weekday()]
        if not tram:    # sense hores d'avui, no hi ha previsió, i es diu (auditoria del 08-10-2026)
            return "\n".join(x for x in (text_ara(dades, idioma), t["sense_previsio"].format(generat.strftime("%H:%M")), WEB) if x)
        linies = [f"<b>El tiempo hoy, {nom_dia}, en Montflorit</b>" if idioma == "es"
                  else f"<b>El temps avui, {nom_dia}, a Montflorit</b>",
                  text_ara(dades, idioma),
                  text_temperatura(tram, idioma, "Temperatura de aquí a medianoche" if idioma == "es"
                                   else "Temperatura d'aquí a mitjanit"),
                  text_pluja(tram, idioma)]
        roba = text_roba(tram, idioma)
        # De vespre, si ha de ploure abans de les 6, també la nit.
        if avui and moment.hour >= HORA_DEMA:
            fi_nit = dt.datetime.combine(moment.date() + dt.timedelta(days=1), dt.time(6))
            nit = [f for f in hores if fi_dia <= hora(f) < fi_nit]
            if franges(nit):
                linies.append(("Esta noche: " if idioma == "es" else "Aquesta nit: ")
                              + text_pluja(nit, idioma).split(": ", 1)[1])
        linies += text_avisos_aemet(dades, idioma, moment.date(), moment)
        linies.append(text_trens_resum(dades, idioma))
    # La ropa, al final y aparte (Juanjo, 08-10-2026: «muy desordenado»).
    text = "\n".join(x for x in linies if x)
    return text + (f"\n\n{roba}" if roba else "") + "\n" + WEB


def text_trens_resum(dades, idioma):
    linies = ((dades.get("trens") or {}).get("linies")) or []
    if not linies:
        return None
    no = {"ca": {"sense_trens": "sense trens", "bus": "per carretera", "incidencies": "amb incidències",
                 "sense_dades": "sense dades"},
          "es": {"sense_trens": "sin trenes", "bus": "por carretera", "incidencies": "con incidencias",
                 "sense_dades": "sin datos"}}[idioma]
    # Sense dades de cap línia (Renfe i FGC caiguts), no es pot dir que vagin bé.
    if all(l["estat"] == "sense_dades" for l in linies):
        return ("Trenes de Cerdanyola: ahora mismo no hay datos de Renfe ni de FGC." if idioma == "es"
                else "Trens de Cerdanyola: ara mateix no hi ha dades de Renfe ni d'FGC.")
    mal = [f"{l['linia']} {no[l['estat']]}" for l in linies if l["estat"] in no]
    if not mal:
        return None if all(l["estat"] == "fora_horari" for l in linies) else \
            ("Trenes de Cerdanyola sin incidencias." if idioma == "es" else "Trens de Cerdanyola sense incidències.")
    return ("Trenes de Cerdanyola: " if idioma == "es" else "Trens de Cerdanyola: ") + ", ".join(mal) + "."


# --- Órdenes de consulta (Juanjo, 08-10-2026) ---------------------------------------
# /trens, /radar y /avisos_actius: lo mismo que la web, con el mismo límite de
# edad de los datos que /ara.

def dades_velles(dades, idioma, moment):
    generat = dades.get("generat") and dt.datetime.fromisoformat(dades["generat"])
    if not generat or moment - generat > dt.timedelta(hours=DADES_VELLES_H):
        return T[idioma]["velles_ara"].format(generat.strftime("%H:%M") if generat else "?")
    return None


ESTAT_TREN = {"ca": {"circula": "sense incidències", "incidencies": "amb incidències", "bus": "servei per carretera",
                     "sense_trens": "sense trens", "fora_horari": "fora d'horari", "sense_dades": "sense dades"},
              "es": {"circula": "sin incidencias", "incidencies": "con incidencias", "bus": "servicio por carretera",
                     "sense_trens": "sin trenes", "fora_horari": "fuera de horario", "sense_dades": "sin datos"}}


def text_trens_bot(dades, idioma, moment):
    vell = dades_velles(dades, idioma, moment)
    if vell:
        return vell
    linies = ((dades.get("trens") or {}).get("linies")) or []
    if not linies:
        return "Ahora no hay datos de los trenes." if idioma == "es" else "Ara no hi ha dades dels trens."
    # Cada línia una sola vegada, amb el seu avís més nou al costat, en
    # l'idioma original de l'operador (Juanjo, 07-10-2026 i 08-10-2026).
    files = []
    for l in linies:
        fila = f"<b>{html.escape(l['linia'])}</b> ({html.escape(l.get('estacio', ''))}): {ESTAT_TREN[idioma].get(l['estat'], l['estat'])}"
        if l.get("avisos"):
            a = l["avisos"][0]
            fila += f". «{html.escape(a.get(idioma) or a.get('ca') or a.get('es') or '')}»"
        files.append(fila)
    cap = "Trenes de Cerdanyola" if idioma == "es" else "Trens de Cerdanyola"
    return f"<b>{cap}</b>\n" + "\n".join(files)


DIRECCIO_ES = {"al nord": "el norte", "al nord-est": "el nordeste", "a l'est": "el este", "al sud-est": "el sudeste",
               "al sud": "el sur", "al sud-oest": "el sudoeste", "a l'oest": "el oeste", "al nord-oest": "el noroeste"}
RADAR_EN_DIRECTE = {"rainviewer": "https://www.rainviewer.com/map.html?loc=41.482,2.135,9&layer=radar",
                    "meteocat": "https://www.meteo.cat/observacions/radar"}


def text_radar_bot(dades, idioma, moment):
    vell = dades_velles(dades, idioma, moment)
    if vell:
        return vell
    r = dades.get("radar")
    if not r:
        return "Ahora no hay datos del radar." if idioma == "es" else "Ara no hi ha dades del radar."
    h = lambda t: dt.datetime.fromisoformat(t).strftime("%H:%M")
    if r.get("arriba"):
        que = (f"Llegaría lluvia hacia las {h(r['arriba'])}." if idioma == "es" else f"Arribaria pluja cap a les {h(r['arriba'])}.")
    elif r.get("possible"):
        que = (f"Puede llegar lluvia hacia las {h(r['possible'])}." if idioma == "es" else f"Pot arribar pluja cap a les {h(r['possible'])}.")
    else:
        que = "No se acerca lluvia en 2 horas." if idioma == "es" else "No s'acosta pluja en 2 hores."
    font = "RainViewer" if r.get("imatge") == "rainviewer" else "Meteocat"
    mov = ""
    if r.get("cap_a"):
        mov = (f" · va hacia {DIRECCIO_ES.get(r['cap_a'], r['cap_a'])} a {r['velocitat_kmh']}\u00a0km/h" if idioma == "es"
               else f" · va cap {r['cap_a']} a {r['velocitat_kmh']}\u00a0km/h")
    detall = (f"Radar de {font} de las {h(r['hora'])}{mov}." if idioma == "es" else f"Radar de {font} de les {h(r['hora'])}{mov}.")
    enllac = RADAR_EN_DIRECTE["rainviewer" if font == "RainViewer" else "meteocat"]
    vist = "En directo" if idioma == "es" else "En directe"
    return f"{que}\n{detall}\n{vist}: {enllac}"


FASE_ES = {"prealerta": "prealerta", "alerta": "alerta", "emergència": "emergencia"}
PLA_ES = {"d'inundacions": "de inundaciones", "de vent": "de viento", "de neu": "de nieve"}


def text_avisos_actius(dades, idioma, moment):
    vell = dades_velles(dades, idioma, moment)
    if vell:
        return vell
    linies = []
    for p in dades.get("plans") or []:
        if idioma == "es":
            linies.append(f"Protección Civil: plan {PLA_ES.get(p['nom'], p['nom'])} ({p['pla']}) en fase de "
                          f"{FASE_ES.get(p['fase'], p['fase'])}." + (f" {p['comunicat']}" if p.get("comunicat") else ""))
        else:
            # «d'alerta», «d'emergència», però «de prealerta», com a la web.
            de = "d'" if p["fase"][:1] in "aeiouàèéíòóú" else "de "
            linies.append(f"Protecció Civil: pla {p['nom']} ({p['pla']}) en fase {de}{p['fase']}."
                          + (f" {p['comunicat']}" if p.get("comunicat") else ""))
    avui, dema = moment.date(), (moment + dt.timedelta(days=1)).date()
    linies += text_avisos_aemet(dades, idioma, avui, moment)
    linies += [x for x in text_avisos_aemet(dades, idioma, dema, moment) if x not in linies]
    # Incendis a prop, Pla Alfa des del nivell 3 i accés a Collserola (ADR 0046).
    linies += linies_entorn(dades.get("entorn") or {}, idioma)
    # El temps excepcional que calcula la pàgina amb els llindars de l'AEMET
    # (el mateix de l'avís «perill», ADR 0018), dit que no és oficial.
    propis = linies_riscos(dades.get("riscos") or [], idioma, moment)
    if not linies and not propis:
        return ("No hay avisos de la AEMET ni planes de Protección Civil activos, ni se prevé tiempo excepcional."
                if idioma == "es" else
                "No hi ha avisos de l'AEMET ni plans de Protecció Civil activats, ni es preveu temps excepcional.")
    cap = "Avisos activos" if idioma == "es" else "Avisos actius"
    text = f"<b>{cap}</b>\n" + "\n".join(html.escape(x, quote=False) for x in linies) if linies else ""
    if propis:
        titol = ("Tiempo excepcional (lo calcula Temps a Montflorit con los umbrales de la AEMET, no es oficial)"
                 if idioma == "es" else
                 "Temps excepcional (ho calcula Temps a Montflorit amb els llindars de l'AEMET, no és oficial)")
        text += ("\n\n" if text else "") + f"<b>{titol}</b>\n" + "\n".join(html.escape(x, quote=False) for x in propis)
    return text


# Des del nivell 3 el Pla Alfa restringeix l'accés (config.ALFA_NIVELL_MOSTRAR;
# el bot no carrega config).
ALFA_NIVELL_MOSTRAR = 3
ALFA = {"ca": "Pla Alfa de Cerdanyola: nivell {n} {quan}: accés restringit als espais forestals.",
        "es": "Plan Alfa de Cerdanyola: nivel {n} {quan}: acceso restringido a los espacios forestales."}


def linies_entorn(entorn, idioma):
    es = idioma == "es"
    res = []
    for i in entorn.get("incendis") or []:
        h = dt.datetime.fromisoformat(i["inici"]).strftime("%H:%M") if i.get("inici") else "?"
        dist = f", a {str(i['km']).replace('.', ',')} km" if i.get("km") is not None else ""
        res.append(f"Bombers: incendio forestal en {i['municipi']}{dist} (desde las {h})." if es
                   else f"Bombers: incendi forestal a {i['municipi']}{dist} (des de les {h}).")
    alfa = entorn.get("pla_alfa") or {}
    for dia in ("avui", "dema"):
        n = alfa.get(dia)
        if n is not None and n >= ALFA_NIVELL_MOSTRAR:
            quan = {"avui": ("hoy" if es else "avui"), "dema": ("mañana" if es else "demà")}[dia]
            res.append(ALFA[idioma].format(n=n, quan=quan))
    for t in alfa.get("tancaments") or []:
        res.append(f"Agents Rurals: cerrado {t['espai']}." if es else f"Agents Rurals: tancat {t['espai']}.")
    for a in entorn.get("collserola") or []:
        res.append(f"Collserola: «{a['titol']}» ({a['data'][8:10]}/{a['data'][5:7]}). {a['enllac']}")
    return res


def linies_riscos(riscos, idioma, moment):
    """Una línia per risc, en l'idioma de qui pregunta. Els textos en castellà
    són els de l'avís (avisos_bot.py); si no es pot carregar, el català de les dades."""
    if idioma == "es":
        try:
            sys.path.insert(0, REPO)
            import avisos_bot as AB
            return [AB.linia_risc_es(r, moment) for r in riscos]
        except Exception:
            pass
    return [r.get("text", "") for r in riscos]


# --- Mensajes recibidos -------------------------------------------------------------

def avisa_juanjo(text):
    """A Juanjo, con su bot de avisos (el del vigía de IONOS). Sin nombres de
    nadie: el bot promete guardar solo el identificador."""
    propi = llegeix(os.environ.get("AVISAR_CONFIG", os.path.expanduser("~/.vigilancia-nas/config.json")), {})
    if propi.get("token") and propi.get("chat_id"):
        try:
            Api(propi["token"])("sendMessage", chat_id=propi["chat_id"], text=text)
        except Exception as ex:
            registra(f"no se ha podido avisar a Juanjo: {ex}")


def alta(subs, chat, usuari):
    """El suscriptor de este chat; si es nuevo, se le da de alta y se avisa a
    Juanjo con el número total."""
    if chat not in subs:
        subs[chat] = nou_subscriptor(usuari)
        avisa_juanjo(f"Temps a Montflorit: alta nova al bot (ja en són {len(subs)}).")
    return subs[chat]


def esborra(estat, chat):
    """La baja borra el chat de todo el estado: la fecha del último resumen y
    los avisos pendientes de entregarle (auditoría del 07-10-2026)."""
    if estat is None:
        return
    estat.get("resums", {}).pop(chat, None)
    for p in estat.get("pendents", {}).values():
        p["chats"] = [c for c in p["chats"] if c != chat]


def neteja(subs, estat):
    """Quita del estado los restos de chats que ya no están suscritos."""
    resums = estat.get("resums") or {}
    for chat in [c for c in resums if c not in subs]:
        del resums[chat]
    for p in (estat.get("pendents") or {}).values():
        p["chats"] = [c for c in p["chats"] if c in subs]


def canvi_canal(api, cm):
    """Juanjo quiere saber quién entra y quién sale del canal (08-10-2026).
    Telegram lo cuenta al bot porque es administrador del canal. El nombre va
    solo en el aviso a Juanjo, que lo ve igualmente en la lista del canal: no
    se guarda."""
    if cm.get("chat", {}).get("username", "").lower() != CANAL.lstrip("@").lower():
        return
    dins = lambda m: m.get("status") in DINS_CANAL or bool(m.get("status") == "restricted" and m.get("is_member"))
    abans, despres = cm.get("old_chat_member") or {}, cm.get("new_chat_member") or {}
    if dins(abans) == dins(despres):
        return
    u = despres.get("user") or abans.get("user") or {}
    nom = " ".join(x for x in (u.get("first_name"), u.get("last_name")) if x) or "?"
    if u.get("username"):
        nom += f" (@{u['username']})"
    try:
        total = f" Ja en són {api('getChatMemberCount', chat_id=CANAL)}."
    except Exception:
        total = ""
    que = "alta nova al canal" if dins(despres) else "baixa del canal"
    avisa_juanjo(f"Temps a Montflorit: {que}, {nom}.{total}")


CONSULTES = ("/dema", "/trens", "/radar", "/avisos_actius")


def atén(api, subs, update, estat=None):
    if "chat_member" in update:
        canvi_canal(api, update["chat_member"])
        return
    if "callback_query" in update:
        q = update["callback_query"]
        chat = str(q["message"]["chat"]["id"])
        sub = alta(subs, chat, q.get("from", {}))
        if canvia(sub, q.get("data", "")):
            api("editMessageText", chat_id=chat, message_id=q["message"]["message_id"],
                text=T[sub["idioma"]]["menu"], reply_markup={"inline_keyboard": teclat(sub)})
        api("answerCallbackQuery", callback_query_id=q["id"])
        return
    m = update.get("message") or {}
    if m.get("chat", {}).get("type") != "private" or "text" not in m:
        return
    chat = str(m["chat"]["id"])
    ordre = m["text"].split()[0].split("@")[0].lower()
    if ordre == "/baixa":
        idioma = (subs.pop(chat, None) or nou_subscriptor(m.get("from", {})))["idioma"]
        esborra(estat, chat)
        envia(api, chat, T[idioma]["baixa"])
        return
    nou = chat not in subs
    if nou and ordre not in ("/start", "/avisos", "/menu", "/resum", "/ara") + CONSULTES:
        # Quien escribe cualquier cosa sin haber empezado solo recibe la ayuda.
        envia(api, chat, T[nou_subscriptor(m.get("from", {}))["idioma"]]["ajuda"])
        return
    sub = alta(subs, chat, m.get("from", {}))
    t = T[sub["idioma"]]
    if ordre == "/start":
        envia(api, chat, t["benvinguda"], html=True)
        # A quien llega de nuevo se le dice qué se le ha marcado ya (Juanjo, 07-10-2026).
        envia(api, chat, (t["inici"] + " " if nou else "") + t["menu"], teclat(sub))
    elif ordre in ("/avisos", "/menu"):
        envia(api, chat, t["menu"], teclat(sub))
    elif ordre == "/resum":
        envia(api, chat, resum(llegeix(os.path.join(DADES, "montflorit.json"), {}), sub["idioma"], ara(), avui=True), html=True)
    elif ordre == "/ara":
        dades = llegeix(os.path.join(DADES, "montflorit.json"), {})
        envia(api, chat, text_ara_bot(dades, sub["idioma"], ara()) + "\n" + WEB)
    elif ordre == "/dema":
        envia(api, chat, resum(llegeix(os.path.join(DADES, "montflorit.json"), {}), sub["idioma"], ara(), dema=True), html=True)
    elif ordre in CONSULTES:
        dades = llegeix(os.path.join(DADES, "montflorit.json"), {})
        funcio = {"/trens": text_trens_bot, "/radar": text_radar_bot, "/avisos_actius": text_avisos_actius}[ordre]
        envia(api, chat, funcio(dades, sub["idioma"], ara()) + "\n" + WEB, html=True)
    else:
        envia(api, chat, t["ajuda"])


# --- Repartir ----------------------------------------------------------------------

def a_repartir(avisos, enviats, moment):
    """Los avisos aún no repartidos y vigentes."""
    res = []
    for a in avisos:
        if a["id"] in enviats:
            continue
        edat = (moment - dt.datetime.fromisoformat(a["hora"])).total_seconds() / 60
        if edat <= VIGENCIA_MIN.get(a["tipus"], 60):
            res.append(a)
    return res


# Quien sigue el canal no recibe por el bot lo que el canal ya le da: avisos de
# riera y peligro y la previsión de las 7 (Juanjo, 07-10-2026). El bot, como
# administrador del canal, puede preguntar quién está; ante la duda o si el
# canal no lo ha recibido, se manda: mejor un aviso repetido que uno perdido.
# El canal va solo en catalán, y aun así no se repite a nadie: quien está en
# el canal ya lo recibe allí (Juanjo, 08-10-2026). El menú del bot lo explica.
DINS_CANAL = ("creator", "administrator", "member")


def al_canal(api, chat, memoria):
    if chat not in memoria:
        try:
            r = api("getChatMember", chat_id=CANAL, user_id=chat) or {}
            memoria[chat] = r.get("status") in DINS_CANAL or bool(r.get("status") == "restricted" and r.get("is_member"))
        except Exception:
            memoria[chat] = False
    return memoria[chat]


def reparteix(api, subs, estat, moment):
    """Reparte los avisos nuevos y vuelve a intentar, cada minuto mientras el
    aviso esté vigente, lo que Telegram no aceptó (el canal o algún chat):
    un fallo pasajero no puede perder un aviso de riera o de peligro (ADR
    0034). Si el canal falla, los suscriptores lo reciben igualmente por el
    bot; cuando el canal lo acepte, quien está en él lo verá repetido."""
    enviats = estat.setdefault("enviats", {})
    pendents = estat.setdefault("pendents", {})     # id: {"avis", "canal", "chats"}
    memoria = {}        # quién está en el canal, preguntado una vez por pasada
    avisos = llegeix(os.path.join(DADES, "avisos.json"), {}).get("avisos", [])
    for a in a_repartir(avisos, enviats, moment):
        enviats[a["id"]] = moment.isoformat(timespec="minutes")
        pendents[a["id"]] = {"avis": a, "canal": a["tipus"] in CANAL_TIPUS,
                             "chats": [c for c, s in subs.items() if a["tipus"] in s["avisos"]]}
    for clau, p in list(pendents.items()):
        a = p["avis"]
        if not a_repartir([a], {}, moment):
            # Ya no está vigente: se deja estar, pero con rastro, y si era de
            # riera o de peligro, Juanjo se entera (auditoría del 07-10-2026).
            if p["canal"] or p["chats"]:
                on = (["el canal"] if p["canal"] else []) + ([f"{len(p['chats'])} chat(s)"] if p["chats"] else [])
                registra(f"aviso {clau} caducado sin entregar a {' y '.join(on)}")
                if a["tipus"] in CANAL_TIPUS:
                    avisa_juanjo(f"Temps a Montflorit: el aviso {clau} ha caducado sin llegar a {' y '.join(on)}. "
                                 "Telegram lo ha rechazado durante toda su vigencia: mira errors.log del bot.")
            del pendents[clau]
            continue
        if p["canal"]:
            try:
                envia(api, CANAL, a["ca"], html=True)
                p["canal"] = False
            except Exception as ex:
                registra(f"aviso {clau}: el canal no lo acepta: {ex}")
        al_canal_ok = a["tipus"] in CANAL_TIPUS and not p["canal"]
        queden, motius = [], []
        for chat in p["chats"]:
            sub = subs.get(chat)
            if not sub or (al_canal_ok and al_canal(api, chat, memoria)):
                continue
            try:
                envia(api, chat, a[sub["idioma"]], html=True)
            except Bloquejat:
                subs.pop(chat, None)
                esborra(estat, chat)
            except Exception as ex:
                queden.append(chat)
                motius.append(str(ex))
            time.sleep(0.05)
        p["chats"] = queden
        if queden:
            registra(f"aviso {clau}: {len(queden)} chat(s) sin entregar: {'; '.join(sorted(set(motius)))}")
        if not p["canal"] and not queden:
            del pendents[clau]
    # Lo repartido hace más de 3 días ya no hace falta recordarlo.
    limit = moment - dt.timedelta(days=3)
    for k in [k for k, v in enviats.items() if dt.datetime.fromisoformat(v) < limit]:
        del enviats[k]
    # El resumen diario: primero el del canal, a las 7; luego el de cada uno, a su hora
    # (una vez al día), salvo a quien ya le ha llegado por el canal. Se apunta
    # como hecho solo cuando Telegram lo acepta: si falla, se reintenta al
    # minuto siguiente mientras dure esa hora.
    hora, avui = str(moment.hour), moment.date().isoformat()
    dades = None
    if hora == CANAL_RESUM and estat.get("canal_resum") != avui:
        dades = llegeix(os.path.join(DADES, "montflorit.json"), {})
        try:
            # El canal, solo en catalán (Juanjo, 08-10-2026).
            envia(api, CANAL, resum(dades, "ca", moment), html=True)
            estat["canal_resum"] = avui
        except Exception as ex:
            registra(f"el resumen del canal no ha entrado: {ex}")
    canal_resum_ok = hora == CANAL_RESUM and estat.get("canal_resum") == avui
    resums = estat.setdefault("resums", {})
    for chat, sub in list(subs.items()):
        if sub.get("resum") == hora and resums.get(chat) != avui:
            if canal_resum_ok and al_canal(api, chat, memoria):
                resums[chat] = avui
                continue
            dades = dades or llegeix(os.path.join(DADES, "montflorit.json"), {})
            try:
                envia(api, chat, resum(dades, sub["idioma"], moment), html=True)
                resums[chat] = avui
            except Bloquejat:
                subs.pop(chat, None)
                esborra(estat, chat)
            except Exception as ex:
                registra(f"un resumen de las {hora} h no ha entrado: {ex}")


def actualitza_repo(estat):
    """Pone al día la copia del repositorio, como mucho una vez por hora, y
    solo hasta el último commit con las pruebas de GitHub en verde
    (desplegament.py, ADR 0038); mientras se espera a unas pruebas, cada
    vuelta. Si la copia es tan vieja que no trae desplegament.py, git pull."""
    pendent = estat.get("desplegament", {}).get("proves_pendents")
    if not pendent and time.time() - estat.get("pull", 0) < 3600:
        return
    estat["pull"] = time.time()
    try:
        sys.path.insert(0, REPO)
        import desplegament
        desplegament.actualitza(REPO, estat.setdefault("desplegament", {}), registra)
    except ImportError:
        subprocess.run(["git", "-C", REPO, "pull", "-q", "--ff-only"], check=False, timeout=120,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as ex:
        registra(f"no se ha podido poner al día el repositorio: {ex}")


def volta():
    os.makedirs(BASE, exist_ok=True)
    cadenat = open(os.path.join(BASE, "bot.lock"), "w")
    try:
        fcntl.flock(cadenat, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return          # la vuelta anterior aún no ha acabado
    api = Api(llegeix(os.path.join(BASE, "config.json"), {})["token"])
    subs = llegeix(SUBS, {})
    estat = llegeix(ESTAT, {})
    neteja(subs, estat)
    actualitza_repo(estat)
    fi = time.time() + DURADA_S
    while True:
        reparteix(api, subs, estat, ara())
        desa(SUBS, subs)
        desa(ESTAT, estat)
        queda = int(fi - time.time())
        if queda < 3:
            break
        try:
            updates = api("getUpdates", temps=queda + 10, offset=estat.get("offset"),
                          timeout=min(queda, 25), allowed_updates=["message", "callback_query", "chat_member"]) or []
        except Exception as ex:
            registra(f"getUpdates: {ex}")
            time.sleep(5)
            continue
        for u in updates:
            estat["offset"] = u["update_id"] + 1
            try:
                atén(api, subs, u, estat)
            except Exception as ex:
                registra(f"al atender un mensaje: {ex}")
        desa(SUBS, subs)
        desa(ESTAT, estat)


def mostra_estat():
    subs = llegeix(SUBS, {})
    estat = llegeix(ESTAT, {})
    print(f"Subscriptors: {len(subs)}")
    for x in TIPUS:
        print(f"  {x}: {sum(x in s['avisos'] for s in subs.values())}")
    print(f"  resum: {sum(bool(s.get('resum')) for s in subs.values())}")
    print(f"Avisos repartits (3 dies): {len(estat.get('enviats', {}))}")
    pendents = estat.get("pendents") or {}
    if pendents:
        print(f"Pendents d'entregar: {', '.join(pendents)}")
    try:
        with open(os.path.join(BASE, "errors.log"), encoding="utf-8") as f:
            darrers = f.readlines()[-5:]
        print("Últims errors:\n" + "".join(darrers), end="")
    except OSError:
        pass


def informe():
    """Los lunes, a Juanjo, con su bot de avisos (el del vigía de IONOS):
    cuántos suscriptores hay y qué eligen, y cuántos miembros tiene el canal."""
    subs = llegeix(SUBS, {})
    n = lambda x: sum(x in s["avisos"] for s in subs.values())
    try:
        canal = Api(llegeix(os.path.join(BASE, "config.json"), {})["token"])("getChatMemberCount", chat_id=CANAL)
    except Exception:
        canal = "?"
    text = (f"Temps a Montflorit: {len(subs)} suscriptores en el bot (riera {n('riera')}, peligro {n('perill')}, "
            f"lluvia {n('pluja')}, trenes {n('trens')}, previsión diaria "
            f"{sum(bool(s.get('resum')) for s in subs.values())}) y {canal} miembros en el canal.")
    propi = llegeix(os.environ.get("AVISAR_CONFIG", os.path.expanduser("~/.vigilancia-nas/config.json")), {})
    if propi.get("token") and propi.get("chat_id"):
        Api(propi["token"])("sendMessage", chat_id=propi["chat_id"], text=text)
    print(text)


if __name__ == "__main__":
    {"estat": mostra_estat, "informe": informe}.get(sys.argv[1] if sys.argv[1:] else "", volta)()
