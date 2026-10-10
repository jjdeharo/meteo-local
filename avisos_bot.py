#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Los avisos públicos para el bot y el canal de Telegram (ADR 0034).

Tras cada cálculo (en el NAS o en la reserva de IONOS), mira los datos de casa
y decide qué avisos tocan para los vecinos, con su propio estado: el de los
avisos de Juanjo es otro. Los deja en avisos.json, que se sube a IONOS con
montflorit.json; allí el bot (bot/bot.py) los reparte a quien los haya elegido
y publica en el canal los importantes. Cada aviso lleva un identificador:
el bot no manda dos veces el mismo.

Tipos:
- pluja: llueve en Montflorit en unos 15 minutos, según el radar (la lógica
  de pluja_arriba.py, ADR 0022), un aviso por episodio de lluvia.
- perill: lo medido o previsto llega a los umbrales de aviso de AEMET (la de
  riscos.py, ADR 0018), al aparecer o subir de nivel; y, desde el 08-10-2026,
  un incendio forestal en curso a menos de 5 km (Bombers) al empezar y al
  dejar de constar (entorn.py, ADR 0046).
- riera: riesgo de desbordamiento de la riera de Sant Cugat (la de riera.py,
  ADR 0027), atención y peligro, siempre con el aviso de que es orientativo.
- perill, también, desde el 09-10-2026: los avisos oficiales nuevos (ADR 0055).
  Un aviso de AEMET para el Prelitoral de Barcelona al aparecer o subir de
  nivel, y un plan de Protección Civil al pasar a alerta o a emergencia y
  cuando sale de ellas. La prealerta no avisa (ADR 0051).

Los trenes y el tráfico no avisan desde el 09-10-2026: se consultan en «Si
surts» y con /trens y /transit del bot (ADR 0053).

Uso: python3 avisos_bot.py CASA.json AVISOS.json
"""
import datetime as dt
import html
import json
import os
import sys

import config as C
import pluja_arriba as PA
import riera as RI
import riscos as RS

ESTAT = os.path.join(os.path.dirname(os.environ.get("REGISTRE_DIR", "/estat/registre")), "bot-avisos.json")
CONSERVA_H = 24          # avisos que se guardan en avisos.json
WEB = "https://meteo-montflorit.github.io/"
ORIENTATIU = {
    "ca": "Avís en proves, orientatiu i no oficial: segueix les indicacions de Protecció Civil i de l'Ajuntament.",
    "es": "Aviso en pruebas, orientativo y no oficial: sigue las indicaciones de Protección Civil y del Ayuntamiento.",
}
NIVELLS_ES = {"groc": "amarillo", "taronja": "naranja", "vermell": "rojo"}
RISCOS_ES = {
    "pluja_1h": ("Lluvia muy fuerte prevista: hasta {v} mm en una hora, {q}.",
                 "Ahora llueve muy fuerte: {v} mm en la última hora."),
    "pluja_12h": ("Mucha lluvia prevista: {v} mm en 12 horas, {q}.",
                  "Ha llovido mucho: {v} mm en las últimas 12 horas."),
    "ratxa": ("Viento muy fuerte previsto: rachas de hasta {v} km/h, {q}.", None),
    "calor": ("Calor extremo previsto: hasta {v} °C, {q}.", "Ahora hace calor extremo: {v} °C."),
    "fred": ("Frío intenso previsto: hasta {v} °C, {q}.", "Ahora hace frío intenso: {v} °C."),
    "neu_24h": ("Nieve prevista: {v} cm en las próximas 24 horas.", None),
}


def coma(x):
    return f"{x:.0f}" if x >= 10 else f"{x:.1f}".replace(".", ",")


# --- Textos ------------------------------------------------------------------

# Cada aviso empieza por lo que pasa, en negrita (HTML de Telegram), y lo explica
# en palabras llanas para quien no conoce la web (Juanjo, 07-10-2026).
# Delante, el nivel con un círculo de color, la misma escala que el bot
# (bot/bot.py, CERCLE): se ve la gravedad antes de leer, también en la
# notificación del móvil (Juanjo, 10-10-2026; ADR 0065). El final, en verde.
CERCLE = {"groc": "🟡", "taronja": "🟠", "vermell": "🔴", "atencio": "🟠", "perill": "🔴",
          "alerta": "🟠", "emergència": "🔴", "fi": "🟢"}


def negreta(text, nivell=None):
    cercle = CERCLE.get(nivell)
    return (f"{cercle} " if cercle else "") + f"<b>{html.escape(text, quote=False)}</b>"


def text_pluja(salida, ahora):
    r = salida["radar"]
    falta = round(PA.falta_min(salida, ahora))
    mm = r.get("arriba_mm_h")
    forca = {"ca": "", "es": ""}
    if mm is not None:
        forca = ({"ca": " Pot ser forta.", "es": " Puede ser fuerte."} if mm >= 4 else
                 {"ca": " Serà moderada.", "es": " Será moderada."} if mm >= 1 else
                 {"ca": " Serà feble.", "es": " Será débil."})
    if falta <= 2:
        ca = (negreta("Pluja imminent a Montflorit") + "\nEl radar ja veu pluja a sobre del barri: pot "
              "començar en qualsevol moment." + forca["ca"])
        es = (negreta("Lluvia inminente en Montflorit") + "\nEl radar ya ve lluvia encima del barrio: puede "
              "empezar en cualquier momento." + forca["es"])
    else:
        hora = dt.datetime.fromisoformat(r["arriba"]).strftime("%H:%M")
        ca = negreta(f"Pluja d'aquí a uns {falta} minuts") + (f"\nSegons el radar, començarà a ploure a "
                                                              f"Montflorit cap a les {hora}.") + forca["ca"]
        es = negreta(f"Lluvia dentro de unos {falta} minutos") + (f"\nSegún el radar, empezará a llover en "
                                                                 f"Montflorit hacia las {hora}.") + forca["es"]
    return amb_radar(ca, es, r)


def amb_radar(ca, es, r):
    """El radar en directe, el mateix que ha donat l'avís (Juanjo, 08-10-2026):
    a Telegram, un enllaç a l'última línia; a la notificació, que no admet
    enllaços al text, en tocar-la (bot/push.py llegeix «url» i «push»)."""
    font = "rainviewer" if r.get("imatge") == "rainviewer" else "meteocat"
    url = C.RADAR_EN_DIRECTE[font]
    nom = {"rainviewer": "RainViewer", "meteocat": "Meteocat"}[font]
    enllac = f'<a href="{html.escape(url)}">{nom}</a>'
    return {"ca": f"{ca}\nRadar en directe: {enllac}", "es": f"{es}\nRadar en directo: {enllac}", "url": url,
            "push": {"ca": f"{ca} Toca per veure el radar.", "es": f"{es} Toca para ver el radar."}}


def quan_es(r, ahora):
    ini, fin = dt.datetime.fromisoformat(r["des_de"]), dt.datetime.fromisoformat(r["fins"])
    dia = ("hoy" if ini.date() == ahora.date() else
           "mañana" if ini.date() == ahora.date() + dt.timedelta(days=1) else ini.strftime("%d/%m"))
    return f"{dia} de {ini.hour} a {fin.hour} h"


QUE_CA = {"pluja_1h": "pluja molt forta", "pluja_12h": "molta pluja", "ratxa": "vent molt fort",
          "calor": "calor extrema", "fred": "fred intens", "neu_24h": "neu"}
QUE_ES = {"pluja_1h": "lluvia muy fuerte", "pluja_12h": "mucha lluvia", "ratxa": "viento muy fuerte",
          "calor": "calor extremo", "fred": "frío intenso", "neu_24h": "nieve"}


def linia_risc_es(r, ahora):
    """El text d'un risc en castellà (el català ja ve fet a les dades)."""
    previst, mesura = RISCOS_ES[r["tipus"]]
    plantilla = previst if r["origen"] == "previsio" else mesura
    if not plantilla:
        return r["text"]
    return plantilla.format(v=RS.num(r["valor"]), q=quan_es(r, ahora) if r.get("des_de") else "")


def text_perill(nous, ahora):
    pitjor = max(nous, key=lambda r: RS.NIVELLS.index(r["nivell"]))["nivell"]
    tipus = list(dict.fromkeys(r["tipus"] for r in nous))
    ca = [negreta(f"Avís de perill a Montflorit ({pitjor}): " + " i ".join(QUE_CA[t] for t in tipus), pitjor)]
    ca += [html.escape(r["text"], quote=False) for r in nous]
    ca.append("Ho calcula Temps a Montflorit amb els llindars de l'AEMET: no és un avís oficial.")
    es = [negreta(f"Aviso de peligro en Montflorit ({NIVELLS_ES[pitjor]}): " + " y ".join(QUE_ES[t] for t in tipus), pitjor)]
    es += [html.escape(linia_risc_es(r, ahora), quote=False) for r in nous]
    es.append("Lo calcula Temps a Montflorit con los umbrales de la AEMET: no es un aviso oficial.")
    return {"ca": "\n".join(ca), "es": "\n".join(es)}, pitjor


def text_perill_fi():
    """Ja no queda cap risc: el mateix que rebia abans només Juanjo (Juanjo,
    08-10-2026), perquè qui ha rebut l'avís sàpiga que ha passat."""
    h = C.RISC_FI_H
    ca = (negreta("Ja no hi ha cap situació de perill a Montflorit", "fi") +
          f"\nFa {h} hores que ni el que mesuren les estacions ni la previsió arriben als llindars d'avís de "
          "l'AEMET. Si hi tornen, hi haurà un avís nou.")
    es = (negreta("Ya no hay ninguna situación de peligro en Montflorit", "fi") +
          f"\nHace {h} horas que ni lo que miden las estaciones ni la previsión llegan a los umbrales de aviso de "
          "la AEMET. Si vuelven, habrá un aviso nuevo.")
    return {"ca": ca, "es": es}


def text_riera(riera, nivell):
    hora = dt.datetime.fromisoformat(riera["fins"]).strftime("%H:%M")
    mm3, mm6 = coma(riera["mm_3h"]), coma(riera["mm_6h"])
    radar = riera.get("radar_1h")
    mes_ca = f", i el radar en preveu uns {coma(radar)} mm més des de llavors fins d'aquí a una hora" if radar and radar >= 1 else ""
    mes_es = f", y el radar prevé unos {coma(radar)} mm más desde entonces hasta dentro de una hora" if radar and radar >= 1 else ""
    if nivell == "perill":
        ca = (negreta("Perill de desbordament de la riera de Sant Cugat a Montflorit", nivell) +
              f"\nHa plogut molt a Sant Cugat, d'on baixa l'aigua de la riera: {mm3} mm en 3 hores i {mm6} en 6 "
              f"(fins a les {hora}){mes_ca}. Amb aquesta pluja, la riera ja s'ha desbordat altres vegades. "
              "No t'acostis a la riera.")
        es = (negreta("Peligro de desbordamiento de la riera de Sant Cugat en Montflorit", nivell) +
              f"\nHa llovido mucho en Sant Cugat, de donde baja el agua de la riera: {mm3} mm en 3 horas y {mm6} "
              f"en 6 (hasta las {hora}){mes_es}. Con esta lluvia, la riera ya se ha desbordado otras veces. "
              "No te acerques a la riera.")
    else:
        ca = (negreta("Atenció: possible desbordament de la riera de Sant Cugat", nivell) +
              f"\nPlou fort a Sant Cugat, d'on baixa l'aigua de la riera: {mm3} mm en 3 hores (fins a les {hora})"
              f"{mes_ca}. Si continua, la riera es pot desbordar a Montflorit. No t'acostis a la riera.")
        es = (negreta("Atención: posible desbordamiento de la riera de Sant Cugat", nivell) +
              f"\nLlueve fuerte en Sant Cugat, de donde baja el agua de la riera: {mm3} mm en 3 horas (hasta las "
              f"{hora}){mes_es}. Si continúa, la riera se puede desbordar en Montflorit. No te acerques a la riera.")
    if riera.get("incomplet"):
        ca += " A l'estació li falten mesures: la pluja real pot ser més alta."
        es += " A la estación le faltan medidas: la lluvia real puede ser más alta."
    return {"ca": f"{ca}\n{ORIENTATIU['ca']}", "es": f"{es}\n{ORIENTATIU['es']}"}


def text_riera_fi(riera, episodi):
    """Final d'un episodi amb avís (Juanjo, 08-10-2026): un sol missatge, i
    només després de RIERA_FI_H hores per sota del registre."""
    mm3, h = coma(riera["mm_3h"]), C.RIERA_FI_H
    perill = bool(episodi["avisos"].get("perill"))
    ca = (negreta("Riera de Sant Cugat: " + ("ha passat el perill de desbordament" if perill else "ja no hi ha risc de desbordament"), "fi")
          + f"\nA Sant Cugat fa {h} hores que no plou amb força ({mm3} mm en les últimes 3 hores) i el radar no hi veu "
          "pluja forta. Si torna a ploure fort, tornarà l'avís.")
    es = (negreta("Riera de Sant Cugat: " + ("ha pasado el peligro de desbordamiento" if perill else "ya no hay riesgo de desbordamiento"), "fi")
          + f"\nEn Sant Cugat lleva {h} horas sin llover con fuerza ({mm3} mm en las últimas 3 horas) y el radar no ve "
          "lluvia fuerte. Si vuelve a llover fuerte, volverá el aviso.")
    return {"ca": f"{ca}\n{ORIENTATIU['ca']}", "es": f"{es}\n{ORIENTATIU['es']}"}


# --- Incendios cerca (ADR 0046) ---------------------------------------------------
# Van con los de peligro («Situacions de perill»): son datos oficiales de
# Bombers, y se dice de dónde salen.

def hhmm(iso):
    return dt.datetime.fromisoformat(iso).strftime("%H:%M") if iso else "?"


def text_incendi(i, acabat=False):
    lloc = i.get("municipi") or "?"
    dist = f", a uns {coma(i['km'])} km" if i.get("km") is not None else ""
    dist_es = f", a unos {coma(i['km'])} km" if i.get("km") is not None else ""
    if acabat:
        return {"ca": negreta(f"Incendi a {lloc}: ja no consta com a actiu", "fi")
                      + "\nBombers de la Generalitat ja no el tenen entre les actuacions en curs.",
                "es": negreta(f"Incendio en {lloc}: ya no consta como activo", "fi")
                      + "\nBombers de la Generalitat ya no lo tienen entre las actuaciones en curso."}
    return {"ca": negreta(f"Incendi forestal a prop de Montflorit: {lloc}")
                  + f"\nBombers de la Generalitat treballen en un incendi de vegetació forestal a {lloc}{dist}, "
                  f"des de les {hhmm(i.get('inici'))}. Segueix les indicacions de Bombers i de Protecció Civil.",
            "es": negreta(f"Incendio forestal cerca de Montflorit: {lloc}")
                  + f"\nBombers de la Generalitat trabajan en un incendio de vegetación forestal en {lloc}{dist_es}, "
                  f"desde las {hhmm(i.get('inici'))}. Sigue las indicaciones de Bombers y de Protección Civil."}


# --- Avisos oficiales nuevos (ADR 0055) -------------------------------------------
# Van con los de peligro: llegan al canal y a quien tiene «Situacions de perill».

FASES_PLA = ("prealerta", "alerta", "emergència")
DIES = {"ca": ("dilluns", "dimarts", "dimecres", "dijous", "divendres", "dissabte", "diumenge"),
        "es": ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")}
TIPUS_AEMET = {"ca": {"pluja": "pluja", "tempestes": "tempestes"}, "es": {"pluja": "lluvia", "tempestes": "tormentas"}}
NOM_PLA_ES = {"d'inundacions": "de inundaciones", "de vent": "de viento", "de neu": "de nieve",
              "per onada de calor": "por ola de calor", "per onada de fred": "por ola de frío",
              "per contaminació": "por contaminación", "per vent": "por viento"}
SENTIT_FASE = {
    "ca": {"alerta": "El pla està activat: es preveu un risc important a curt termini, o hi ha afectacions que no són greus.",
           "emergència": "El pla està activat per un risc greu per a la població: segueix les indicacions de Protecció Civil."},
    "es": {"alerta": "El plan está activado: se prevé un riesgo importante a corto plazo, o hay afectaciones que no son graves.",
           "emergència": "El plan está activado por un riesgo grave para la población: sigue las indicaciones de Protección Civil."}}


def moment(iso, ahora):
    """(dia, hora) d'un instant; les 23:59:59 compten com la mitjanit següent."""
    t = dt.datetime.fromisoformat(iso).astimezone(ahora.tzinfo)
    if t.second == 59:
        t += dt.timedelta(seconds=1)
    return t, (t.date() - ahora.date()).days


def nom_dia(t, dies, idioma):
    es = idioma == "es"
    return (("hoy" if es else "avui") if dies == 0 else ("mañana" if es else "demà") if dies == 1
            else DIES[idioma][t.weekday()])


def franja(inici, fi, ahora, idioma):
    """«Des d'avui a les 15 h fins a mitjanit.», «Desde mañana a las 6 h hasta el
    sábado a las 3 h.»"""
    es = idioma == "es"
    t0, d0 = moment(inici, ahora)
    t1, d1 = moment(fi, ahora)
    dia0 = nom_dia(t0, d0, idioma)
    if d1 == d0:                                     # el mateix dia
        return (f"{dia0.capitalize()}, de las {t0.hour} h a las {t1.hour} h." if es
                else f"{dia0.capitalize()}, de les {t0.hour} h a les {t1.hour} h.")
    if t1.hour == 0 and t1.minute == 0 and d1 == d0 + 1:
        fins = "hasta medianoche" if es else "fins a mitjanit"
    else:
        dia1 = nom_dia(t1, d1, idioma)
        fins = (f"hasta {'el ' if d1 > 1 else ''}{dia1} a las {t1.hour} h" if es
                else f"fins {dia1} a les {t1.hour} h")
    if es:
        return f"Desde {'el ' if d0 > 1 else ''}{dia0} a las {t0.hour} h {fins}."
    de = "d'" if dia0[:1] in "aeiouàèéíòóú" else "de "
    return f"Des {de}{dia0} a les {t0.hour} h {fins}."


def text_aemet(a, ahora):
    """Un aviso de AEMET: nivel, de qué, de cuándo a cuándo y su texto (en
    castellano, como lo publica AEMET: ADR 0033)."""
    nivell = a["nivel"]
    desc = f"\n«{html.escape(a['descripcio'], quote=False)}»" if a.get("descripcio") else ""
    ca = (negreta(f"Avís {nivell} de l'AEMET per {TIPUS_AEMET['ca'].get(a['tipo'], a['tipo'])} al Vallès", nivell)
          + "\n" + franja(a["inicio"], a["fin"], ahora, "ca") + desc
          + "\nÉs un avís oficial: segueix les indicacions de Protecció Civil.")
    es = (negreta(f"Aviso {NIVELLS_ES.get(nivell, nivell)} de la AEMET por {TIPUS_AEMET['es'].get(a['tipo'], a['tipo'])} "
                  f"en el Vallès", nivell)
          + "\n" + franja(a["inicio"], a["fin"], ahora, "es") + desc
          + "\nEs un aviso oficial: sigue las indicaciones de Protección Civil.")
    return {"ca": ca, "es": es}


def text_pla(p, acabat=False):
    nom_ca, nom_es = p["nom"], NOM_PLA_ES.get(p["nom"], p["nom"])
    if acabat:
        return {"ca": negreta(f"Protecció Civil: el pla {nom_ca} ({p['pla']}) ja no està en alerta", "fi")
                      + "\nJa no consta en alerta ni en emergència.",
                "es": negreta(f"Protección Civil: el plan {nom_es} ({p['pla']}) ya no está en alerta", "fi")
                      + "\nYa no consta en alerta ni en emergencia."}
    de = "d'" if p["fase"][:1] in "aeiouàèéíòóú" else "de "
    fase_es = {"emergència": "emergencia"}.get(p["fase"], p["fase"])
    enllac_ca = f"\n<a href=\"{html.escape(p['comunicat'])}\">Comunicat (PDF)</a>" if p.get("comunicat") else ""
    enllac_es = enllac_ca.replace("Comunicat (PDF)", "Comunicado (PDF)")
    return {"ca": negreta(f"Protecció Civil: pla {nom_ca} ({p['pla']}) en fase {de}{p['fase']}", p["fase"])
                  + "\n" + SENTIT_FASE["ca"][p["fase"]] + enllac_ca,
            "es": negreta(f"Protección Civil: plan {nom_es} ({p['pla']}) en fase de {fase_es}", p["fase"])
                  + "\n" + SENTIT_FASE["es"][p["fase"]] + enllac_es}


# --- Decidir -----------------------------------------------------------------

def decideix(estat, salida, ahora):
    """Pone al día el estado y devuelve los avisos nuevos:
    [{id, tipus, nivell, ca, es, hora}]."""
    nous = []
    hora = ahora.isoformat(timespec="minutes")

    def afegeix(tipus, clau, text, nivell=None):
        nous.append({"id": f"{tipus}:{clau}", "tipus": tipus, "nivell": nivell, "hora": hora, **text})

    # Lluvia en unos minutos: la lógica del aviso de Juanjo, con estado propio.
    try:
        avis, _ = PA.compara(estat.setdefault("pluja", {"episodi": None}), salida, ahora)
        if avis:
            afegeix("pluja", estat["pluja"]["episodi"]["inici"], text_pluja(salida, ahora))
    except Exception:
        pass
    # Peligro: al aparecer o subir de nivel.
    actius = estat.setdefault("perill", {})
    nous_perill = []
    for r in salida.get("riscos") or []:
        abans = actius.get(r["clau"])
        if not abans or RS.NIVELLS.index(r["nivell"]) > RS.NIVELLS.index(abans["nivell"]):
            nous_perill.append(r)
            actius[r["clau"]] = {"nivell": r["nivell"]}
        actius[r["clau"]]["vist"] = hora
    # Sin previsión o sin estación no se ha podido mirar: el riesgo no caduca,
    # para no repetirlo al canal cuando vuelvan los datos.
    sense = not salida.get("hores") or not salida.get("ara")
    acabats = []
    for clau, a in list(actius.items()):
        if not sense and ahora - dt.datetime.fromisoformat(a["vist"]) >= dt.timedelta(hours=C.RISC_FI_H):
            acabats.append(clau)
            del actius[clau]
    if nous_perill:
        text, pitjor = text_perill(nous_perill, ahora)
        afegeix("perill", hora + ":" + ",".join(r["clau"] for r in nous_perill), text, pitjor)
    elif acabats and not actius:
        # Quan ja no en queda cap, es diu (abans, només a Juanjo).
        afegeix("perill", hora + ":fi", text_perill_fi(), "fi")
    # Incendios forestales cerca (ADR 0046). La primera vez solo se apunta lo
    # que hay: lo que ya estaba no es una novedad.
    entorn = salida.get("entorn") or {}
    e = estat.get("entorn")
    if entorn.get("incendis") is not None:
        ara_ids = {i["id"]: i for i in entorn["incendis"]}
        if e is not None:
            for i in entorn["incendis"]:
                if i["id"] not in e["incendis"]:
                    afegeix("perill", f"incendi:{i['id']}", text_incendi(i), "incendi")
            for iid, i in e["incendis"].items():
                if iid not in ara_ids:
                    afegeix("perill", f"incendi:{iid}:fi", text_incendi(i, acabat=True), "fi")
        estat.setdefault("entorn", {"incendis": {}})["incendis"] = ara_ids
    # Avisos oficiales nuevos (ADR 0055). La primera vez solo se apunta lo que
    # hay; si una fuente ha fallado (None), no se toca: no es que se acabe.
    of = estat.get("oficials")
    nou_of = {"aemet": dict((of or {}).get("aemet") or {}), "plans": dict((of or {}).get("plans") or {})}
    if salida.get("avisos") is not None:
        aemet = {f"{a['tipo']}:{a['inicio']}": a for a in salida["avisos"]
                 if a.get("zona", C.ZONA_AVISOS) == C.ZONA_AVISOS and a["nivel"] in RS.NIVELLS}
        if of is not None:
            for k, a in aemet.items():
                abans = of["aemet"].get(k)
                if abans is None or RS.NIVELLS.index(a["nivel"]) > RS.NIVELLS.index(abans):
                    afegeix("perill", f"aemet:{k}:{a['nivel']}", text_aemet(a, ahora), a["nivel"])
        nou_of["aemet"] = {k: a["nivel"] for k, a in aemet.items()}
    if salida.get("plans") is not None:
        actius = ("alerta", "emergència")
        plans = {p["pla"]: p for p in salida["plans"] if p.get("fase") in actius}
        # Los ocultos por no tener motivo meteorológico (ADR 0062) siguen
        # activos: ocultarlos no es un final, y si vuelven a mostrarse en la
        # misma fase no son nuevos. Al desactivarse uno oculto no se avisa:
        # ya no se estaba mostrando.
        ocults = {p["pla"]: p for p in salida.get("plans_ocults") or [] if p.get("fase") in actius}
        if of is not None:
            for k, p in plans.items():
                abans = (of["plans"].get(k) or {}).get("fase")
                if abans is None or FASES_PLA.index(p["fase"]) > FASES_PLA.index(abans):
                    afegeix("perill", f"pla:{k}:{p['fase']}:{hora}", text_pla(p), "pc")
            for k, p in of["plans"].items():
                if k not in plans and k not in ocults and not p.get("ocult"):
                    afegeix("perill", f"pla:{k}:fi:{hora}", text_pla({**p, "pla": k}, acabat=True), "fi")
        nou_of["plans"] = {k: {"fase": p["fase"], "nom": p["nom"], **({"ocult": True} if k in ocults else {})}
                           for k, p in {**ocults, **plans}.items()}
    estat["oficials"] = nou_of
    # Riera: atención y peligro, una vez cada nivel por episodio.
    riera = salida.get("riera")
    if riera:
        e = estat.setdefault("riera", {"episodi": None})
        episodi_abans = e.get("episodi")
        abans = set((episodi_abans or {}).get("avisos", {}))
        RI.compara(e, riera, ahora)
        despres = (e.get("episodi") or {}).get("avisos", {})
        for nivell in ("perill", "atencio"):
            if nivell in despres and nivell not in abans:
                afegeix("riera", f"{e['episodi']['inici']}:{nivell}", text_riera(riera, nivell), nivell)
                break
        # L'episodi s'ha tancat (3 hores de calma) després d'un avís: es diu que ha passat.
        if episodi_abans and not e.get("episodi") and abans:
            afegeix("riera", f"{episodi_abans['inici']}:fi", text_riera_fi(riera, episodi_abans), "fi")
    # Los avisos de trenes y de cortes ya no existen (ADR 0053): fuera su estado.
    estat.pop("trens", None)
    estat.pop("talls", None)
    return nous


def actualitza(casa_json, sortida, ahora=None):
    ahora = ahora or dt.datetime.now().astimezone()
    with open(casa_json, encoding="utf-8") as f:
        salida = json.load(f)
    try:
        with open(ESTAT, encoding="utf-8") as f:
            estat = json.load(f)
    except (OSError, ValueError):
        estat = {}
    nous = decideix(estat, salida, ahora)
    # Los avisos de las últimas CONSERVA_H horas: el bot reparte los que no ha
    # mandado aún.
    limit = ahora - dt.timedelta(hours=CONSERVA_H)
    llista = [a for a in estat.get("llista", []) if dt.datetime.fromisoformat(a["hora"]) > limit] + nous
    estat["llista"] = llista
    with open(ESTAT + ".tmp", "w", encoding="utf-8") as f:
        json.dump(estat, f, ensure_ascii=False)
    os.replace(ESTAT + ".tmp", ESTAT)
    with open(sortida, "w", encoding="utf-8") as f:
        json.dump({"generat": ahora.isoformat(timespec="minutes"), "avisos": llista}, f, ensure_ascii=False)
    return nous


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    for a in actualitza(sys.argv[1], sys.argv[2]):
        print(a["id"], a["ca"].splitlines()[0])
