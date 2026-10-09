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
  dejar de constar (entorn.py, ADR 0046); y, desde el 09-10-2026, una calzada
  cortada a 4 km o menos (Servei Català de Trànsit), al empezar y al acabar
  (transit.py, ADR 0052).
- riera: riesgo de desbordamiento de la riera de Sant Cugat (la de riera.py,
  ADR 0027), atención y peligro, siempre con el aviso de que es orientativo.
- trens: una línea de Cerdanyola deja de circular o vuelve (trens.py,
  ADR 0029), cuando el cambio se repite en dos pasadas seguidas.

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
VA = ("circula", "incidencies")
NO_VA = ("sense_trens", "bus")


def coma(x):
    return f"{x:.0f}" if x >= 10 else f"{x:.1f}".replace(".", ",")


# --- Textos ------------------------------------------------------------------

# Cada aviso empieza por lo que pasa, en negrita (HTML de Telegram), y lo explica
# en palabras llanas para quien no conoce la web (Juanjo, 07-10-2026).
def negreta(text):
    return f"<b>{html.escape(text, quote=False)}</b>"


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
    ca = [negreta(f"Avís de perill ({pitjor}): " + " i ".join(QUE_CA[t] for t in tipus))]
    ca += [html.escape(r["text"], quote=False) for r in nous]
    ca.append("Ho calcula Temps a Montflorit amb els llindars de l'AEMET: no és un avís oficial.")
    es = [negreta(f"Aviso de peligro ({NIVELLS_ES[pitjor]}): " + " y ".join(QUE_ES[t] for t in tipus))]
    es += [html.escape(linia_risc_es(r, ahora), quote=False) for r in nous]
    es.append("Lo calcula Temps a Montflorit con los umbrales de la AEMET: no es un aviso oficial.")
    return {"ca": "\n".join(ca), "es": "\n".join(es)}, pitjor


def text_perill_fi():
    """Ja no queda cap risc: el mateix que rebia abans només Juanjo (Juanjo,
    08-10-2026), perquè qui ha rebut l'avís sàpiga que ha passat."""
    h = C.RISC_FI_H
    ca = (negreta("Ja no hi ha cap situació de perill a Montflorit") +
          f"\nFa {h} hores que ni el que mesuren les estacions ni la previsió arriben als llindars d'avís de "
          "l'AEMET. Si hi tornen, hi haurà un avís nou.")
    es = (negreta("Ya no hay ninguna situación de peligro en Montflorit") +
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
        ca = (negreta("Perill de desbordament de la riera de Sant Cugat a Montflorit") +
              f"\nHa plogut molt a Sant Cugat, d'on baixa l'aigua de la riera: {mm3} mm en 3 hores i {mm6} en 6 "
              f"(fins a les {hora}){mes_ca}. Amb aquesta pluja, la riera ja s'ha desbordat altres vegades. "
              "No t'acostis a la riera.")
        es = (negreta("Peligro de desbordamiento de la riera de Sant Cugat en Montflorit") +
              f"\nHa llovido mucho en Sant Cugat, de donde baja el agua de la riera: {mm3} mm en 3 horas y {mm6} "
              f"en 6 (hasta las {hora}){mes_es}. Con esta lluvia, la riera ya se ha desbordado otras veces. "
              "No te acerques a la riera.")
    else:
        ca = (negreta("Atenció: possible desbordament de la riera de Sant Cugat") +
              f"\nPlou fort a Sant Cugat, d'on baixa l'aigua de la riera: {mm3} mm en 3 hores (fins a les {hora})"
              f"{mes_ca}. Si continua, la riera es pot desbordar a Montflorit. No t'acostis a la riera.")
        es = (negreta("Atención: posible desbordamiento de la riera de Sant Cugat") +
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
    ca = (negreta("Riera de Sant Cugat: " + ("ha passat el perill de desbordament" if perill else "ja no hi ha risc de desbordament"))
          + f"\nA Sant Cugat fa {h} hores que no plou amb força ({mm3} mm en les últimes 3 hores) i el radar no hi veu "
          "pluja forta. Si torna a ploure fort, tornarà l'avís.")
    es = (negreta("Riera de Sant Cugat: " + ("ha pasado el peligro de desbordamiento" if perill else "ya no hay riesgo de desbordamiento"))
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
        return {"ca": negreta(f"Incendi a {lloc}: ja no consta com a actiu")
                      + "\nBombers de la Generalitat ja no el tenen entre les actuacions en curs.",
                "es": negreta(f"Incendio en {lloc}: ya no consta como activo")
                      + "\nBombers de la Generalitat ya no lo tienen entre las actuaciones en curso."}
    return {"ca": negreta(f"Incendi forestal a prop de Montflorit: {lloc}")
                  + f"\nBombers de la Generalitat treballen en un incendi de vegetació forestal a {lloc}{dist}, "
                  f"des de les {hhmm(i.get('inici'))}. Segueix les indicacions de Bombers i de Protecció Civil.",
            "es": negreta(f"Incendio forestal cerca de Montflorit: {lloc}")
                  + f"\nBombers de la Generalitat trabajan en un incendio de vegetación forestal en {lloc}{dist_es}, "
                  f"desde las {hhmm(i.get('inici'))}. Sigue las indicaciones de Bombers y de Protección Civil."}


# --- Carreteras cortadas cerca (ADR 0052) -----------------------------------------
# También con los de peligro: afectan a todo el que sale en coche o en moto.
# Qué corte avisa lo decide transit.py («tall»). Los textos del Servei Català
# de Trànsit (causa y sentido) van tal cual, en catalán.

def text_tall(i, acabat=False):
    via = i.get("carretera") or "?"
    lloc_ca = f" a {i['municipi']}" if i.get("municipi") else ""
    lloc_es = f" en {i['municipi']}" if i.get("municipi") else ""
    if acabat:
        return {"ca": negreta(f"Carretera: la {via}{lloc_ca} ja no consta com a tallada")
                      + "\nEl Servei Català de Trànsit ja no hi indica la calçada tallada.",
                "es": negreta(f"Carretera: la {via}{lloc_es} ya no consta como cortada")
                      + "\nEl Servei Català de Trànsit ya no indica allí la calzada cortada."}
    detall = "; ".join(x for x in (i.get("causa"), i.get("sentit"), i.get("pk") and f"km {i['pk']}") if x)
    detall = f" ({html.escape(detall, quote=False)})" if detall else ""
    return {"ca": negreta(f"Carretera tallada a prop de Montflorit: {via}{lloc_ca}")
                  + f"\nEl Servei Català de Trànsit hi indica la calçada tallada{detall}, des de les "
                  f"{hhmm(i.get('des_de'))}. Si havies de passar per allà, busca un altre camí.",
            "es": negreta(f"Carretera cortada cerca de Montflorit: {via}{lloc_es}")
                  + f"\nEl Servei Català de Trànsit indica allí la calzada cortada{detall}, desde las "
                  f"{hhmm(i.get('des_de'))}. Si tenías que pasar por allí, busca otro camino."}


def text_trens(linia, estacio, estat):
    if estat == "bus":
        return {"ca": negreta(f"Trens: l'{linia} no circula a {estacio}") + "\nHi ha servei per carretera.",
                "es": negreta(f"Trenes: la {linia} no circula en {estacio}") + "\nHay servicio por carretera."}
    if estat == "sense_trens":
        return {"ca": negreta(f"Trens: l'{linia} no circula a {estacio}"),
                "es": negreta(f"Trenes: la {linia} no circula en {estacio}")}
    return {"ca": negreta(f"Trens: l'{linia} torna a circular a {estacio}"),
            "es": negreta(f"Trenes: la {linia} vuelve a circular en {estacio}")}


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
    # Carreteras cortadas cerca (ADR 0052), igual que los incendios: la primera
    # vez solo se apunta lo que hay. Si el Servei Català de Trànsit no ha
    # respondido, no se mira: no es que se hayan acabado.
    transit = salida.get("transit")
    if transit and transit.get("incidencies") is not None:
        talls = {i["id"]: i for i in transit["incidencies"] if i.get("tall")}
        e = estat.get("talls")
        if e is not None:
            for tid, i in talls.items():
                if tid not in e:
                    afegeix("perill", f"tall:{tid}", text_tall(i), "tall")
            for tid, i in e.items():
                if tid not in talls:
                    afegeix("perill", f"tall:{tid}:fi", text_tall(i, acabat=True), "fi")
        estat["talls"] = talls
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
    # Trenes: el cambio cuenta si se repite en dos pasadas seguidas.
    trens = estat.setdefault("trens", {})
    for l in ((salida.get("trens") or {}).get("linies") or []):
        if l["estat"] not in VA + NO_VA:
            continue
        ara = "va" if l["estat"] in VA else l["estat"]
        t = trens.setdefault(l["linia"], {"avisat": "va", "candidat": None})
        if ara == t["avisat"]:
            t["candidat"] = None
            continue
        if t["candidat"] == ara:
            t["avisat"], t["candidat"] = ara, None
            afegeix("trens", f"{l['linia']}:{hora}", text_trens(l["linia"], l["estacio"], l["estat"]),
                    "va" if ara == "va" else "no_va")
        else:
            t["candidat"] = ara
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
