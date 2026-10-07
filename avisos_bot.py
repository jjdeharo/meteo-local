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
  riscos.py, ADR 0018), al aparecer o subir de nivel.
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
        return {"ca": negreta("Pluja imminent a Montflorit") + "\nEl radar ja veu pluja a sobre del barri: pot "
                      "començar en qualsevol moment." + forca["ca"],
                "es": negreta("Lluvia inminente en Montflorit") + "\nEl radar ya ve lluvia encima del barrio: puede "
                      "empezar en cualquier momento." + forca["es"]}
    hora = dt.datetime.fromisoformat(r["arriba"]).strftime("%H:%M")
    return {"ca": negreta(f"Pluja d'aquí a uns {falta} minuts") + f"\nSegons el radar, començarà a ploure a "
                  f"Montflorit cap a les {hora}." + forca["ca"],
            "es": negreta(f"Lluvia dentro de unos {falta} minutos") + f"\nSegún el radar, empezará a llover en "
                  f"Montflorit hacia las {hora}." + forca["es"]}


def quan_es(r, ahora):
    ini, fin = dt.datetime.fromisoformat(r["des_de"]), dt.datetime.fromisoformat(r["fins"])
    dia = ("hoy" if ini.date() == ahora.date() else
           "mañana" if ini.date() == ahora.date() + dt.timedelta(days=1) else ini.strftime("%d/%m"))
    return f"{dia} de {ini.hour} a {fin.hour} h"


QUE_CA = {"pluja_1h": "pluja molt forta", "pluja_12h": "molta pluja", "ratxa": "vent molt fort",
          "calor": "calor extrema", "fred": "fred intens", "neu_24h": "neu"}
QUE_ES = {"pluja_1h": "lluvia muy fuerte", "pluja_12h": "mucha lluvia", "ratxa": "viento muy fuerte",
          "calor": "calor extremo", "fred": "frío intenso", "neu_24h": "nieve"}


def text_perill(nous, ahora):
    pitjor = max(nous, key=lambda r: RS.NIVELLS.index(r["nivell"]))["nivell"]
    tipus = list(dict.fromkeys(r["tipus"] for r in nous))
    ca = [negreta(f"Avís de perill ({pitjor}): " + " i ".join(QUE_CA[t] for t in tipus))]
    ca += [html.escape(r["text"], quote=False) for r in nous]
    ca.append("Ho calcula Temps a Montflorit amb els llindars de l'AEMET: no és un avís oficial.")
    es = [negreta(f"Aviso de peligro ({NIVELLS_ES[pitjor]}): " + " y ".join(QUE_ES[t] for t in tipus))]
    for r in nous:
        previst, mesura = RISCOS_ES[r["tipus"]]
        plantilla = previst if r["origen"] == "previsio" else mesura
        es.append(html.escape(plantilla.format(v=RS.num(r["valor"]),
                                               q=quan_es(r, ahora) if r.get("des_de") else "")
                              if plantilla else r["text"], quote=False))
    es.append("Lo calcula Temps a Montflorit con los umbrales de la AEMET: no es un aviso oficial.")
    return {"ca": "\n".join(ca), "es": "\n".join(es)}, pitjor


def text_riera(riera, nivell):
    hora = dt.datetime.fromisoformat(riera["fins"]).strftime("%H:%M")
    mm3, mm6 = coma(riera["mm_3h"]), coma(riera["mm_6h"])
    radar = riera.get("radar_1h")
    mes_ca = f", i el radar en preveu uns {coma(radar)} mm més en la pròxima hora" if radar and radar >= 1 else ""
    mes_es = f", y el radar prevé unos {coma(radar)} mm más en la próxima hora" if radar and radar >= 1 else ""
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
    return {"ca": f"{ca}\n{ORIENTATIU['ca']}", "es": f"{es}\n{ORIENTATIU['es']}"}


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
    for clau, a in list(actius.items()):
        if ahora - dt.datetime.fromisoformat(a["vist"]) >= dt.timedelta(hours=C.RISC_FI_H):
            del actius[clau]
    if nous_perill:
        text, pitjor = text_perill(nous_perill, ahora)
        afegeix("perill", hora + ":" + ",".join(r["clau"] for r in nous_perill), text, pitjor)
    # Riera: atención y peligro, una vez cada nivel por episodio.
    riera = salida.get("riera")
    if riera:
        e = estat.setdefault("riera", {"episodi": None})
        abans = set((e.get("episodi") or {}).get("avisos", {}))
        RI.compara(e, riera, ahora)
        despres = (e.get("episodi") or {}).get("avisos", {})
        for nivell in ("perill", "atencio"):
            if nivell in despres and nivell not in abans:
                afegeix("riera", f"{e['episodi']['inici']}:{nivell}", text_riera(riera, nivell), nivell)
                break
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
