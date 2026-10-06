#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Qué radar acierta más en casa: Meteocat, mejor pero unos 15 minutos tarde,
o RainViewer, más nuevo pero que marca más lluvia de la que hay (ADR 0026).

En cada pasada de la página de casa se apunta lo que daba cada fuente para
casa en las dos horas siguientes (nowcast.fonts, con el mismo movimiento) y
si llovía en ese momento en Montflorit o en casa. Cada día, con lo apuntado
en los últimos DIES días, se compara lo que daba cada una con lo que pasó
después y se elige la que acierta más (Brier, docs/estadistica.md). La
elección decide cuánto más nueva tiene que ser la imagen de RainViewer para
usarla en lugar de la de Meteocat (nowcast.MARGES).

Como el resto del aprendizaje de la página de casa (docs/estadistica.md,
apartado 4): solo cambia con bastantes casos de lluvia (MIN_PLUJA y
MIN_DIES), si la otra fuente tiene al menos un 5 % menos de error y si no
existe el archivo de parada (aprenentatge/atura). Al cambiar, avisa.

Uso:
  python3 radar_fonts.py verifica   compara y, si toca, cambia
  python3 radar_fonts.py estat      la elegida y la última comparación
"""
import datetime as dt
import glob
import json
import os
import subprocess
import sys

import nowcast as N

DIR = os.environ.get("REGISTRE_DIR", "/estat/registre")
DIES = 30
DE_MIN, FINS_MIN = 10, 60       # antelaciones que se comparan (desde la pasada)
TOLERANCIA_MIN = 4              # observación a menos de esto de la hora prevista
MIN_PLUJA = 30                  # casos con lluvia medida, como mínimo
MIN_DIES = 3                    # en días distintos
MILLORA = 0.95                  # error de la otra, como mucho este factor del actual


def plou(ara, ara_casa):
    """Llueve en este momento en Montflorit o en casa (en casa, solo cuenta
    el sí: su pluviómetro no marca la lluvia débil)."""
    return bool((ara and (ara.get("intensitat") or 0) > 0) or (ara_casa and ara_casa.get("plou")))


def apunta(ahora, nc, ara, ara_casa):
    """Una línea por pasada en radar-fonts-AAAA-MM.jsonl."""
    linia = {"t": ahora.isoformat(timespec="minutes"), "plou": plou(ara, ara_casa),
             "triada": nc and nc.get("imatge"), "fonts": (nc or {}).get("fonts") or {}}
    with open(os.path.join(DIR, f"radar-fonts-{ahora:%Y-%m}.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(linia, ensure_ascii=False) + "\n")


def llegeix(avui):
    files = []
    for ruta in sorted(glob.glob(os.path.join(DIR, "radar-fonts-*.jsonl"))):
        with open(ruta, encoding="utf-8") as f:
            files += [json.loads(l) for l in f if l.strip()]
    des_de = avui - dt.timedelta(days=DIES)
    return [l for l in files if dt.datetime.fromisoformat(l["t"]).date() >= des_de]


def parelles(files):
    """(prob Meteocat, prob RainViewer, llovió) para cada hora prevista por
    las dos fuentes en la misma pasada, con una observación cerca."""
    obs = sorted((dt.datetime.fromisoformat(l["t"]), l["plou"]) for l in files)
    res = []
    for l in files:
        fs = l["fonts"]
        if "meteocat" not in fs or "rainviewer" not in fs:
            continue
        t = dt.datetime.fromisoformat(l["t"])
        prev = {}
        for nom in ("meteocat", "rainviewer"):
            hora = dt.datetime.fromisoformat(fs[nom]["hora"])
            for k, p in enumerate(fs[nom]["prob"]):
                v = hora + dt.timedelta(minutes=k * N.PAS_MIN)
                if dt.timedelta(minutes=DE_MIN) <= v - t <= dt.timedelta(minutes=FINS_MIN):
                    prev.setdefault(v, {})[nom] = p
        for v, ps in prev.items():
            if len(ps) < 2:
                continue
            prop = min(obs, key=lambda o: abs(o[0] - v))
            if abs(prop[0] - v) <= dt.timedelta(minutes=TOLERANCIA_MIN):
                res.append((ps["meteocat"], ps["rainviewer"], prop[1], v.date()))
    return res


def compara(files):
    ps = parelles(files)
    pluja = [p for p in ps if p[2]]
    res = {"parelles": len(ps), "amb_pluja": len(pluja), "dies_pluja": len({p[3] for p in pluja})}
    if ps:
        for i, nom in ((0, "meteocat"), (1, "rainviewer")):
            res[f"brier_{nom}"] = round(sum((p[i] - p[2]) ** 2 for p in ps) / len(ps), 4)
    return res


def decideix(c, actual):
    """La fuente que toca: la otra, si hay bastantes casos de lluvia y
    tiene al menos un 5 % menos de error; si no, la de ahora."""
    if c["amb_pluja"] < MIN_PLUJA or c["dies_pluja"] < MIN_DIES:
        return actual
    altra = "meteocat" if actual == "rainviewer" else "rainviewer"
    return altra if c[f"brier_{altra}"] < MILLORA * c[f"brier_{actual}"] else actual


def verifica(avui=None, avisa=True):
    avui = avui or dt.date.today()
    actual = N.font_preferida()
    c = compara(llegeix(avui))
    nova = decideix(c, actual)
    if nova != actual and os.path.exists(os.path.join(os.path.dirname(N.FONT_PREFERIDA), "atura")):
        print("Canvi de radar aturat (existeix «atura»).")
        nova = actual
    os.makedirs(os.path.dirname(N.FONT_PREFERIDA), exist_ok=True)
    estat = {"preferida": nova, "dia": avui.isoformat(), "comparacio": c}
    if nova == actual and os.path.exists(N.FONT_PREFERIDA):
        with open(N.FONT_PREFERIDA, encoding="utf-8") as f:
            estat["des_de"] = json.load(f).get("des_de", avui.isoformat())
    else:
        estat["des_de"] = avui.isoformat()
    with open(N.FONT_PREFERIDA + ".tmp", "w", encoding="utf-8") as f:
        json.dump(estat, f, ensure_ascii=False, indent=1)
    os.replace(N.FONT_PREFERIDA + ".tmp", N.FONT_PREFERIDA)
    noms = {"meteocat": "Meteocat", "rainviewer": "RainViewer"}
    if nova != actual:
        text = (f"Radar de la pàgina de casa: ara mana {noms[nova]} en lloc de {noms[actual]}. "
                f"En els últims {DIES} dies ha encertat més ({c['amb_pluja']} casos amb pluja en "
                f"{c['dies_pluja']} dies; Brier {c['brier_' + nova]} contra {c['brier_' + actual]}).")
        print(text)
        if avisa:
            subprocess.run(["avisar-juanjo", "--asunto", "meteo-local", text], check=False)
    else:
        print(f"Radar: es queda {noms[actual]}.", json.dumps(c, ensure_ascii=False))
    return estat


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else ""
    if orden == "verifica":
        verifica()
    elif orden == "estat":
        print(N.font_preferida())
        print(json.dumps(compara(llegeix(dt.date.today())), ensure_ascii=False))
    else:
        print(__doc__)
