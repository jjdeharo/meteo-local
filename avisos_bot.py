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
    "ca": "Avís orientatiu, no oficial: segueix les indicacions de Protecció Civil i de l'Ajuntament.",
    "es": "Aviso orientativo, no oficial: sigue las indicaciones de Protección Civil y del Ayuntamiento.",
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

def text_pluja(salida, ahora):
    r = salida["radar"]
    falta = round(PA.falta_min(salida, ahora))
    mm = r.get("arriba_mm_h")
    forca = {"ca": "", "es": ""}
    if mm is not None:
        forca = ({"ca": " Seria forta.", "es": " Sería fuerte."} if mm >= 4 else
                 {"ca": " Seria moderada.", "es": " Sería moderada."} if mm >= 1 else
                 {"ca": " Seria feble.", "es": " Sería débil."})
    if falta <= 2:
        return {"ca": "El radar ja veu pluja a sobre de Montflorit: pot començar en qualsevol moment." + forca["ca"],
                "es": "El radar ya ve lluvia encima de Montflorit: puede empezar en cualquier momento." + forca["es"]}
    hora = dt.datetime.fromisoformat(r["arriba"]).strftime("%H:%M")
    return {"ca": f"Plourà a Montflorit d'aquí a uns {falta} minuts, cap a les {hora}." + forca["ca"],
            "es": f"Lloverá en Montflorit dentro de unos {falta} minutos, hacia las {hora}." + forca["es"]}


def quan_es(r, ahora):
    ini, fin = dt.datetime.fromisoformat(r["des_de"]), dt.datetime.fromisoformat(r["fins"])
    dia = ("hoy" if ini.date() == ahora.date() else
           "mañana" if ini.date() == ahora.date() + dt.timedelta(days=1) else ini.strftime("%d/%m"))
    return f"{dia} de {ini.hour} a {fin.hour} h"


def text_perill(nous, ahora):
    pitjor = max(nous, key=lambda r: RS.NIVELLS.index(r["nivell"]))["nivell"]
    ca = [f"Temps a Montflorit: risc {pitjor}."] + [r["text"] for r in nous]
    es = [f"Tiempo en Montflorit: riesgo {NIVELLS_ES[pitjor]}."]
    for r in nous:
        previst, mesura = RISCOS_ES[r["tipus"]]
        plantilla = previst if r["origen"] == "previsio" else mesura
        es.append(plantilla.format(v=RS.num(r["valor"]),
                                   q=quan_es(r, ahora) if r.get("des_de") else "") if plantilla else r["text"])
    return {"ca": "\n".join(ca), "es": "\n".join(es)}, pitjor


def text_riera(riera, nivell):
    hora = dt.datetime.fromisoformat(riera["fins"]).strftime("%H:%M")
    mm3, mm6 = coma(riera["mm_3h"]), coma(riera["mm_6h"])
    if nivell == "perill":
        ca = (f"Riera de Sant Cugat: perill de desbordament a Montflorit. A Sant Cugat han caigut {mm3} mm "
              f"en 3 hores i {mm6} en 6 (fins a les {hora}).")
        es = (f"Riera de Sant Cugat: peligro de desbordamiento en Montflorit. En Sant Cugat han caído {mm3} mm "
              f"en 3 horas y {mm6} en 6 (hasta las {hora}).")
    else:
        ca = (f"Riera de Sant Cugat: atenció, plou fort a la conca. A Sant Cugat han caigut {mm3} mm "
              f"en 3 hores (fins a les {hora}).")
        es = (f"Riera de Sant Cugat: atención, llueve fuerte en la cuenca. En Sant Cugat han caído {mm3} mm "
              f"en 3 horas (hasta las {hora}).")
    radar = riera.get("radar_1h")
    if radar and radar >= 1:
        ca += f" El radar en preveu uns {coma(radar)} més en la pròxima hora."
        es += f" El radar prevé unos {coma(radar)} más en la próxima hora."
    return {"ca": f"{ca}\n{ORIENTATIU['ca']}", "es": f"{es}\n{ORIENTATIU['es']}"}


def text_trens(linia, estacio, estat):
    if estat == "bus":
        return {"ca": f"{linia} ({estacio}): servei per carretera, sense trens.",
                "es": f"{linia} ({estacio}): servicio por carretera, sin trenes."}
    if estat == "sense_trens":
        return {"ca": f"{linia} ({estacio}): sense trens.", "es": f"{linia} ({estacio}): sin trenes."}
    return {"ca": f"{linia} ({estacio}): torna a circular.", "es": f"{linia} ({estacio}): vuelve a circular."}


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
