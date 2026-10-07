#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Situaciones de peligro en casa según lo que mide y prevé la propia página
(ADR 0018).

Se comparan las estaciones (ahora) y la previsión de la página de casa (24
horas) con los umbrales de aviso de AEMET para el Prelitoral de Barcelona
(config.RISC_LLINDARS): lluvia en 1 y en 12 horas, rachas de viento, calor,
frío y nieve. Los avisos de AEMET y los planes de Protección Civil no cuentan
aquí: ya salen en la página, y Juanjo solo quiere el aviso cuando la previsión
propia ve el peligro.

El NAS, tras publicar la página de casa, avisa por Telegram cuando aparece un
riesgo o sube de nivel, y una vez cuando ya no queda ninguno (un riesgo se da
por acabado tras RISC_FI_H horas sin verlo, para que el vaivén de los modelos
no repita mensajes).

Uso:
  python3 riscos.py avisa CASA.json   compara con lo ya avisado y, si toca, avisa
  python3 riscos.py estat             lo que se tiene por activo
"""
import datetime as dt
import json
import os
import subprocess
import sys

import config as C

NIVELLS = ("groc", "taronja", "vermell")
DIR = os.environ.get("REGISTRE_DIR", "/estat/registre")
ESTADO = os.path.join(os.path.dirname(DIR), "riscos.json")
WEB = "https://meteo-montflorit.github.io/"

UNITATS = {"pluja_1h": "mm", "pluja_12h": "mm", "ratxa": "km/h", "calor": "°C", "fred": "°C",
           "neu_24h": "cm"}


def nivell(tipus, valor):
    """Nivel de AEMET que alcanza el valor, o None."""
    if valor is None:
        return None
    res = None
    for n, llindar in zip(NIVELLS, C.RISC_LLINDARS[tipus]):
        if (valor <= llindar) if tipus == "fred" else (valor >= llindar):
            res = n
    return res


def num(x):
    return f"{x:.0f}".replace("-", "−")


def quan(ini, fin, ahora):
    """«avui de 15 a 18 h», «demà de 2 a 5 h»."""
    dia = "avui" if ini.date() == ahora.date() else "demà" if ini.date() == ahora.date() + dt.timedelta(days=1) \
        else ini.strftime("%d/%m")
    return f"{dia} de {ini.hour} a {fin.hour} h"


TEXTOS = {
    "pluja_1h": ("Pluja molt forta prevista: fins a {v} mm en una hora, {q}.",
                 "Ara plou molt fort: {v} mm en l'última hora."),
    "pluja_12h": ("Molta pluja prevista: {v} mm en 12 hores, {q}.",
                  "Ha plogut molt: {v} mm en les últimes 12 hores."),
    "ratxa": ("Vent molt fort previst: ratxes de fins a {v} km/h, {q}.", None),
    "calor": ("Calor extrema prevista: fins a {v} °C, {q}.", "Ara fa calor extrema: {v} °C."),
    "fred": ("Fred intens previst: fins a {v} °C, {q}.", "Ara fa fred intens: {v} °C."),
    "neu_24h": ("Neu prevista: {v} cm en les pròximes 24 hores.", None),
}


def risc(tipus, origen, valor, ini=None, fin=None, ahora=None):
    n = nivell(tipus, valor)
    if not n:
        return None
    previst, mesura = TEXTOS[tipus]
    plantilla = previst if origen == "previsio" else mesura
    text = plantilla.format(v=num(valor), q=quan(ini, fin, ahora) if ini else "")
    llindar = C.RISC_LLINDARS[tipus][NIVELLS.index(n)]
    return {"clau": f"{origen}:{tipus}", "tipus": tipus, "origen": origen, "nivell": n,
            "valor": round(valor, 1), "llindar": llindar, "unitat": UNITATS[tipus],
            "des_de": ini and ini.isoformat(timespec="minutes"),
            "fins": fin and fin.isoformat(timespec="minutes"), "text": text}


TRAM_PAUSA_H = 2


def pitjor_tram(hores, tipus, valor_de):
    """De las horas que pasan el umbral amarillo, el peor valor y el tramo
    de horas seguidas que lo contiene."""
    dins = [(f, valor_de(f)) for f in hores if nivell(tipus, valor_de(f))]
    if not dins:
        return None
    cmp = min if tipus == "fred" else max
    valor = cmp(v for _, v in dins)
    # Tramos de horas seguidas (una pausa de hasta TRAM_PAUSA_H horas no los
    # separa): el que tiene el peor valor. Antes se unían la primera y la
    # última hora aunque hubiera media noche sin riesgo en medio («avui de
    # 15 a 4 h»).
    trams, tram = [], [dins[0]]
    for ant, act in zip(dins, dins[1:]):
        pausa = dt.datetime.fromisoformat(act[0]["hora"]) - dt.datetime.fromisoformat(ant[0]["fins"])
        if pausa <= dt.timedelta(hours=TRAM_PAUSA_H):
            tram.append(act)
        else:
            trams.append(tram)
            tram = [act]
    trams.append(tram)
    tram = next(t for t in trams if any(v == valor for _, v in t))
    ini = dt.datetime.fromisoformat(tram[0][0]["hora"])
    fin = dt.datetime.fromisoformat(tram[-1][0]["fins"])
    return valor, ini, fin


def de_la_previsio(hores, ahora):
    res = []
    if not hores:
        return res
    for tipus, valor_de in (("pluja_1h", lambda f: f.get("pluja_mm")),
                            ("ratxa", lambda f: f.get("ratxa")),
                            ("calor", lambda f: f.get("temperatura")),
                            ("fred", lambda f: f.get("temperatura"))):
        t = pitjor_tram(hores, tipus, valor_de)
        if t:
            res.append(risc(tipus, "previsio", t[0], t[1], t[2], ahora))
    # Lluvia en 12 horas seguidas: la ventana que más acumula.
    millor = None
    for i in range(max(0, len(hores) - 11)):
        tram = hores[i:i + 12]
        mm = sum(f.get("pluja_mm") or 0 for f in tram)
        if millor is None or mm > millor[0]:
            millor = (mm, tram)
    if millor and nivell("pluja_12h", millor[0]):
        tram = millor[1]
        res.append(risc("pluja_12h", "previsio", millor[0], dt.datetime.fromisoformat(tram[0]["hora"]),
                        dt.datetime.fromisoformat(tram[-1]["fins"]), ahora))
    neu = sum(f.get("neu") or 0 for f in hores)
    r = risc("neu_24h", "previsio", neu)
    if r:
        res.append(r)
    return res


def de_les_estacions(ara, casa):
    """Lo que miden ahora: la lluvia de Montflorit y, si marca, la de casa; la
    temperatura de casa (o la de Montflorit). El viento de las estaciones no
    sirve aquí: Montflorit da la media y el anemómetro de casa no va bien."""
    res = []
    plujas = [x.get("pluja_1h") for x in (ara, casa if casa and casa.get("plou") else None)
              if x and x.get("pluja_1h") is not None]
    for r in (risc("pluja_1h", "ara", max(plujas)) if plujas else None,
              risc("pluja_12h", "ara", ara.get("pluja_12h")) if ara else None):
        if r:
            res.append(r)
    base = casa if casa and casa.get("temperatura") is not None else ara
    if base and base.get("temperatura") is not None:
        for tipus in ("calor", "fred"):
            r = risc(tipus, "ara", base["temperatura"])
            if r:
                res.append(r)
    return res


def detecta(salida, ahora):
    """Riesgos de ahora y de las próximas 24 horas, el peor nivel primero."""
    res = de_les_estacions(salida.get("ara"), salida.get("ara_casa")) + de_la_previsio(salida.get("hores"), ahora)
    return sorted(res, key=lambda r: -NIVELLS.index(r["nivell"]))


# --- Aviso por Telegram (solo en el NAS) ---------------------------------

def llegeix_estat():
    try:
        with open(ESTADO, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {"actius": {}}


def desa_estat(estat):
    with open(ESTADO + ".tmp", "w", encoding="utf-8") as f:
        json.dump(estat, f, ensure_ascii=False, indent=1)
    os.replace(ESTADO + ".tmp", ESTADO)


def compara(estat, salida, ahora):
    """Pone al día el estado y devuelve el mensaje que toca, o None."""
    actius = estat.setdefault("actius", {})
    riscos = salida.get("riscos") or []
    # Si falta una fuente, lo suyo no se da por acabado.
    sense = set()
    if not salida.get("hores"):
        sense.add("previsio")
    if not salida.get("ara") and not salida.get("ara_casa"):
        sense.add("ara")
    nous = []
    for r in riscos:
        abans = actius.get(r["clau"])
        if not abans or NIVELLS.index(r["nivell"]) > NIVELLS.index(abans["nivell"]):
            nous.append(r)
            actius[r["clau"]] = {"nivell": r["nivell"]}
        actius[r["clau"]]["vist"] = ahora.isoformat(timespec="minutes")
    acabats = []
    for clau, a in list(actius.items()):
        if clau.split(":")[0] in sense:
            continue
        if ahora - dt.datetime.fromisoformat(a["vist"]) >= dt.timedelta(hours=C.RISC_FI_H):
            acabats.append(clau)
            del actius[clau]
    if nous:
        pitjor = max(nous, key=lambda r: NIVELLS.index(r["nivell"]))["nivell"]
        linies = [f"Temps a casa: risc {pitjor}."]
        linies += [f"{r['text']} (llindar {r['nivell']} d'AEMET: {num(r['llindar'])} {r['unitat']})"
                   for r in nous]
        linies.append(WEB)
        return "\n".join(linies)
    if acabats and not actius:
        return "Temps a casa: ja no es preveu ni es mesura cap situació de perill."
    return None


def avisa(ruta, ahora=None, envia=True):
    ahora = ahora or dt.datetime.now().astimezone()
    with open(ruta, encoding="utf-8") as f:
        salida = json.load(f)
    estat = llegeix_estat()
    text = compara(estat, salida, ahora)
    desa_estat(estat)
    if text:
        print(text)
        if envia:
            subprocess.run(["avisar-juanjo", "--asunto", "meteo-local", text], check=False)
    return text


if __name__ == "__main__":
    ordre = sys.argv[1] if len(sys.argv) > 1 else ""
    if ordre == "avisa" and len(sys.argv) > 2:
        avisa(sys.argv[2])
    elif ordre == "estat":
        print(json.dumps(llegeix_estat(), ensure_ascii=False, indent=1))
    else:
        print(__doc__)
        sys.exit(1)
