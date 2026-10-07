#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""El bot de Telegram de Temps a Montflorit (@TempsMontfloritBot, ADR 0034).

Vive en el hosting de IONOS, no en el NAS: un corte de luz en casa durante una
tormenta no lo para. El cron lo arranca cada minuto y, durante unos 50
segundos, espera mensajes de Telegram (contesta en uno o dos segundos) y
reparte:

- los avisos que el NAS (o la reserva) deja en avisos.json (avisos_bot.py), a
  quien los haya elegido, y los de riera y peligro también al canal
  @TempsMontflorit;
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
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

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
        "benvinguda": ("Aquest bot envia avisos del temps a Montflorit (Cerdanyola del Vallès), calculats "
                       "automàticament amb dades de Meteocat, l'AEMET, el radar, les estacions del barri, "
                       "Renfe i FGC. Els de desbordament de la riera estan en proves i són orientatius, no "
                       "oficials: segueix sempre les indicacions de Protecció Civil i de l'Ajuntament.\n" + WEB),
        "menu": ("Tria què vols rebre: toca un botó per activar-ho o desactivar-ho. La previsió és un sol "
                 "missatge cada dia, a l'hora que triïs; la de les 20 h és per a l'endemà.\n\nNomés es desa el teu "
                 "identificador de Telegram i el que triïs aquí. Amb /baixa s'esborra tot."),
        "riera": "Desbordament de la riera de Sant Cugat (en proves)", "perill": "Perill (pluja forta, vent, calor…)",
        "pluja": "Pluja d'aquí a 15 minuts", "trens": "Trens de Cerdanyola",
        "resum": "Previsió, un cop al dia, a les:", "no": "No vull rebre la previsió", "h": "{} h", "dema": "{} h (per a demà)",
        "baixa": "Fet: s'han esborrat les teves dades i ja no rebràs res. Amb /start pots tornar-hi.",
        "ajuda": ("/avisos tria què reps · /resum la previsió · /ara el temps ara · "
                  "/baixa deixa de rebre'n i esborra les teves dades"),
        "velles": "Les dades de Temps a Montflorit no s'actualitzen des de les {}: ara no puc donar la previsió.",
    },
    "es": {
        "benvinguda": ("Este bot envía avisos del tiempo en Montflorit (Cerdanyola del Vallès), calculados "
                       "automáticamente con datos de Meteocat, la AEMET, el radar, las estaciones del barrio, "
                       "Renfe y FGC. Los de desbordamiento de la riera están en pruebas y son orientativos, "
                       "no oficiales: sigue siempre las indicaciones de Protección Civil y del Ayuntamiento.\n" + WEB),
        "menu": ("Elige qué quieres recibir: toca un botón para activarlo o desactivarlo. La previsión es un solo "
                 "mensaje cada día, a la hora que elijas; la de las 20 h es para el día siguiente.\n\nSolo se guarda "
                 "tu identificador de Telegram y lo que elijas aquí. Con /baixa se borra todo."),
        "riera": "Desbordamiento de la riera de Sant Cugat (en pruebas)", "perill": "Peligro (lluvia fuerte, viento, calor…)",
        "pluja": "Lluvia dentro de 15 minutos", "trens": "Trenes de Cerdanyola",
        "resum": "Previsión, una vez al día, a las:", "no": "No quiero recibir la previsión", "h": "{} h", "dema": "{} h (para mañana)",
        "baixa": "Hecho: se han borrado tus datos y ya no recibirás nada. Con /start puedes volver.",
        "ajuda": ("/avisos elige qué recibes · /resum la previsión · /ara el tiempo ahora · "
                  "/baixa deja de recibir y borra tus datos"),
        "velles": "Los datos de Temps a Montflorit no se actualizan desde las {}: ahora no puedo dar la previsión.",
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


def envia(api, chat, text, teclat=None):
    return api("sendMessage", chat_id=chat, text=text, disable_web_page_preview=True,
               reply_markup={"inline_keyboard": teclat} if teclat else None)


# --- Menú ----------------------------------------------------------------------

def teclat(sub):
    t = T[sub["idioma"]]
    marca = lambda actiu: "✓ " if actiu else "· "
    files = [[{"text": marca(x in sub["avisos"]) + t[x], "callback_data": f"t:{x}"}] for x in TIPUS]
    files.append([{"text": t["resum"], "callback_data": "-"}])
    files.append([{"text": ("• " if sub.get("resum") == h else "")
                   + t["dema" if int(h) >= HORA_DEMA else "h"].format(h), "callback_data": f"r:{h}"}
                  for h in HORES_RESUM])
    files.append([{"text": ("• " if not sub.get("resum") else "") + t["no"], "callback_data": "r:no"}])
    files.append([{"text": ("• " if sub["idioma"] == i else "") + n, "callback_data": f"i:{i}"}
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


def text_ara(dades, idioma):
    a = dades.get("ara") or {}
    if a.get("temperatura") is None:
        return None
    plou = (a.get("intensitat") or 0) > 0 or (a.get("pluja_30min") or 0) > 0
    if idioma == "es":
        return f"Ahora en Montflorit: {graus(a['temperatura'])}, {'llueve' if plou else 'no llueve'}."
    return f"Ara a Montflorit: {graus(a['temperatura'])}, {'plou' if plou else 'no plou'}."


DIES = {"ca": ("dilluns", "dimarts", "dimecres", "dijous", "divendres", "dissabte", "diumenge"),
        "es": ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")}
# A partir de esta hora, la previsión es para el día siguiente.
HORA_DEMA = 18


def text_pluja(tram, idioma):
    pluges = franges(tram)
    if idioma == "es":
        return ("Lluvia: " + "; ".join(f"posible de {a.hour} a {b.hour} h (hasta {round(p * 100)} %)"
                                       for a, b, p in pluges) + ".") if pluges else "Sin lluvia prevista."
    return ("Pluja: " + "; ".join(f"possible de {a.hour} a {b.hour} h (fins al {round(p * 100)} %)"
                                  for a, b, p in pluges) + ".") if pluges else "Sense pluja prevista."


def text_temperatura(tram, idioma, quan):
    temps = [f["temperatura"] for f in tram if f.get("temperatura") is not None]
    return f"{quan}: de {graus(min(temps))} a {graus(max(temps))}." if temps else None


def text_avisos_aemet(dades, idioma, dia, moment):
    """Los avisos de AEMET de un día: hoy, «fins a les 20:00»; mañana, «de 10:00 a 20:00»."""
    avisos = [a for a in dades.get("avisos") or [] if dt.datetime.fromisoformat(a["fin"]) > moment
              and dt.datetime.fromisoformat(a["inicio"]).date() == dia]
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


def resum(dades, idioma, moment):
    """La previsión en pocas líneas, con los datos públicos: hasta las 18 h,
    el tiempo ahora y el resto del día; desde las 18 h, la de mañana."""
    t = T[idioma]
    if not dades.get("generat"):
        return t["velles"].format("?")
    generat = dt.datetime.fromisoformat(dades["generat"])
    if moment - generat > dt.timedelta(hours=DADES_VELLES_H):
        return t["velles"].format(generat.strftime("%H:%M"))
    ara_n = moment.replace(tzinfo=None)
    hores = [f for f in dades.get("hores") or [] if dt.datetime.fromisoformat(f["fins"]) > ara_n]
    hora = lambda f: dt.datetime.fromisoformat(f["hora"])
    if moment.hour >= HORA_DEMA:
        dema = (moment + dt.timedelta(days=1)).date()
        nit = [f for f in hores if hora(f) < dt.datetime.combine(dema, dt.time(6))]
        dia = [f for f in hores if hora(f).date() == dema and hora(f).hour >= 6]
        nom_dia = DIES[idioma][dema.weekday()]
        linies = [f"Previsión para mañana, {nom_dia}:" if idioma == "es" else f"Previsió per a demà, {nom_dia}:"]
        if franges(nit):    # la noche, solo si se espera lluvia
            linies.append(("Esta noche: " if idioma == "es" else "Aquesta nit: ")
                          + text_pluja(nit, idioma).split(": ", 1)[1])
        linies.append(text_temperatura(dia, idioma, "Mañana" if idioma == "es" else "Demà"))
        linies.append(text_pluja(dia, idioma))
        linies += text_avisos_aemet(dades, idioma, dema, moment)
    else:
        fi_dia = ara_n.replace(hour=23, minute=59)
        tram = [f for f in hores if hora(f) < fi_dia]
        linies = [text_ara(dades, idioma),
                  text_temperatura(tram, idioma, "Hoy" if idioma == "es" else "Avui"),
                  text_pluja(tram, idioma)]
        linies += text_avisos_aemet(dades, idioma, moment.date(), moment)
        linies.append(text_trens_resum(dades, idioma))
    linies.append(WEB)
    return "\n".join(x for x in linies if x)


def text_trens_resum(dades, idioma):
    linies = ((dades.get("trens") or {}).get("linies")) or []
    if not linies:
        return None
    no = {"ca": {"sense_trens": "sense trens", "bus": "per carretera", "incidencies": "amb incidències"},
          "es": {"sense_trens": "sin trenes", "bus": "por carretera", "incidencies": "con incidencias"}}[idioma]
    mal = [f"{l['linia']} {no[l['estat']]}" for l in linies if l["estat"] in no]
    if not mal:
        return None if all(l["estat"] == "fora_horari" for l in linies) else \
            ("Trenes de Cerdanyola sin incidencias." if idioma == "es" else "Trens de Cerdanyola sense incidències.")
    return ("Trenes: " if idioma == "es" else "Trens: ") + ", ".join(mal) + "."


# --- Mensajes recibidos -------------------------------------------------------------

def avisa_juanjo(text):
    """A Juanjo, con su bot de avisos (el del vigía de IONOS). Sin nombres de
    nadie: el bot promete guardar solo el identificador."""
    propi = llegeix(os.environ.get("AVISAR_CONFIG", os.path.expanduser("~/.vigilancia-nas/config.json")), {})
    if propi.get("token") and propi.get("chat_id"):
        try:
            Api(propi["token"])("sendMessage", chat_id=propi["chat_id"], text=text)
        except Exception:
            pass


def alta(subs, chat, usuari):
    """El suscriptor de este chat; si es nuevo, se le da de alta y se avisa a
    Juanjo con el número total."""
    if chat not in subs:
        subs[chat] = nou_subscriptor(usuari)
        avisa_juanjo(f"Temps a Montflorit: alta nova al bot (ja en són {len(subs)}).")
    return subs[chat]


def atén(api, subs, update):
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
        envia(api, chat, T[idioma]["baixa"])
        return
    sub = alta(subs, chat, m.get("from", {}))
    t = T[sub["idioma"]]
    if ordre == "/start":
        envia(api, chat, t["benvinguda"])
        envia(api, chat, t["menu"], teclat(sub))
    elif ordre in ("/avisos", "/menu"):
        envia(api, chat, t["menu"], teclat(sub))
    elif ordre == "/resum":
        envia(api, chat, resum(llegeix(os.path.join(DADES, "montflorit.json"), {}), sub["idioma"], ara()))
    elif ordre == "/ara":
        dades = llegeix(os.path.join(DADES, "montflorit.json"), {})
        envia(api, chat, (text_ara(dades, sub["idioma"]) or t["ajuda"]) + "\n" + WEB)
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


def reparteix(api, subs, estat, moment):
    enviats = estat.setdefault("enviats", {})
    avisos = llegeix(os.path.join(DADES, "avisos.json"), {}).get("avisos", [])
    for a in a_repartir(avisos, enviats, moment):
        enviats[a["id"]] = moment.isoformat(timespec="minutes")
        for chat, sub in list(subs.items()):
            if a["tipus"] in sub["avisos"]:
                try:
                    envia(api, chat, a[sub["idioma"]])
                except Bloquejat:
                    subs.pop(chat, None)
                except Exception:
                    pass
                time.sleep(0.05)
        if a["tipus"] in CANAL_TIPUS:
            try:
                envia(api, CANAL, f"{a['ca']}\n\n{a['es']}")
            except Exception:
                pass
    # Lo repartido hace más de 3 días ya no hace falta recordarlo.
    limit = moment - dt.timedelta(days=3)
    for k in [k for k, v in enviats.items() if dt.datetime.fromisoformat(v) < limit]:
        del enviats[k]
    # El resumen diario, a la hora de cada uno (una vez al día).
    hora, avui = str(moment.hour), moment.date().isoformat()
    resums = estat.setdefault("resums", {})
    dades = None
    for chat, sub in list(subs.items()):
        if sub.get("resum") == hora and resums.get(chat) != avui:
            dades = dades or llegeix(os.path.join(DADES, "montflorit.json"), {})
            resums[chat] = avui
            try:
                envia(api, chat, resum(dades, sub["idioma"], moment))
            except Bloquejat:
                subs.pop(chat, None)
            except Exception:
                pass
    if hora == CANAL_RESUM and estat.get("canal_resum") != avui:
        dades = dades or llegeix(os.path.join(DADES, "montflorit.json"), {})
        estat["canal_resum"] = avui
        try:
            # En el canal, en catalán y en castellano; el enlace, una vez al final.
            envia(api, CANAL, resum(dades, "ca", moment).removesuffix("\n" + WEB) + "\n\n" + resum(dades, "es", moment))
        except Exception:
            pass


def actualitza_repo(estat):
    """git pull, com a molt un cop per hora: el bot es posa al dia sol."""
    if time.time() - estat.get("pull", 0) < 3600:
        return
    estat["pull"] = time.time()
    subprocess.run(["git", "-C", REPO, "pull", "-q", "--ff-only"], check=False, timeout=120,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


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
                          timeout=min(queda, 25), allowed_updates=["message", "callback_query"]) or []
        except Exception:
            time.sleep(5)
            continue
        for u in updates:
            estat["offset"] = u["update_id"] + 1
            try:
                atén(api, subs, u)
            except Exception:
                pass
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
