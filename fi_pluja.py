#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""¿A qué hora para la lluvia que está cayendo? Comprobación antes de
enseñarlo en la página (ADR 0049).

El radar llevado hacia delante (nowcast.py) da, cada 5 minutos y hasta 2
horas, la probabilidad de lluvia en casa. El final previsto sería el primer
momento, desde la pasada, en que baja de LLINDAR durante PASSOS pasos
seguidos (15 minutos); si no lo hace en el horizonte, «no s'acaba en 2 hores».

Aquí se compara con la lluvia de Montflorit cada 5 minutos
(montflorit-5min.csv, registre.py): episodios con lluvia separados por
menos de BUIT_MIN minutos; su final, el último tramo con lluvia. Se juzgan
las pasadas registradas mientras llovía (radar-fonts-*.jsonl, con el radar
que usaba la página). El día en que hay MIN_EPISODIS episodios, el NAS manda
el resultado a Juanjo una vez, para decidir si se muestra.

Uso:
  python3 fi_pluja.py resum     el resultado con lo que hay ahora
"""
import csv
import datetime as dt
import glob
import json
import os
import subprocess
import sys

DIR = os.environ.get("REGISTRE_DIR", "/estat/registre")
APRENENTATGE = os.environ.get("APRENENTATGE_DIR", "/estat/aprenentatge")
AVIS = os.path.join(APRENENTATGE, "avis-fi-pluja")
LLINDAR = 0.2
PASSOS = 3              # 15 minutos
PAS_MIN = 5
BUIT_MIN = 30           # una pausa más corta no acaba el episodio
MIN_EPISODIS = 5
ENCERT_MIN = 15         # acierto: a 15 minutos o menos del final real


def pluja_5min():
    """{fin del tramo: mm} de Montflorit."""
    ruta = os.path.join(DIR, "montflorit-5min.csv")
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding="utf-8") as f:
        return {dt.datetime.fromisoformat(r["fins"]).astimezone(): float(r["pluja_mm"]) for r in csv.DictReader(f)}


def episodis(pluja):
    """[[inicio, final]] con los tramos con lluvia; una pausa de menos de
    BUIT_MIN minutos no corta el episodio. El último, si aún podría seguir
    (sin BUIT_MIN minutos registrados después), no cuenta."""
    res = []
    for t in sorted(t for t, mm in pluja.items() if mm > 0):
        if res and t - res[-1][1] <= dt.timedelta(minutes=BUIT_MIN):
            res[-1][1] = t
        else:
            res.append([t - dt.timedelta(minutes=PAS_MIN), t])
    if res and (not pluja or max(pluja) - res[-1][1] < dt.timedelta(minutes=BUIT_MIN)):
        res.pop()
    return res


def fi_previst(t0, prob, des_de):
    """Primer momento desde des_de en que la probabilidad baja de LLINDAR
    durante PASSOS pasos seguidos; None si no pasa en el horizonte."""
    for k in range(len(prob)):
        tk = t0 + dt.timedelta(minutes=PAS_MIN * k)
        tram = prob[k:k + PASSOS]
        if tk >= des_de and len(tram) == PASSOS and all(p < LLINDAR for p in tram):
            return tk
    return None


def passades():
    res = []
    for ruta in sorted(glob.glob(os.path.join(DIR, "radar-fonts-*.jsonl"))):
        with open(ruta, encoding="utf-8") as f:
            res += [json.loads(l) for l in f if l.strip()]
    return res


def compara(pluja, regs):
    """Para cada pasada durante un episodio: el final real, el previsto (o
    None) y el horizonte del radar."""
    eps = episodis(pluja)
    res = []
    for r in regs:
        t = dt.datetime.fromisoformat(r["t"])
        ep = next((e for e in eps if e[0] <= t <= e[1]), None)
        f = (r.get("fonts") or {}).get(r.get("triada"))
        if not ep or not f:
            continue
        t0 = dt.datetime.fromisoformat(f["hora"])
        res.append({"t": t, "episodi": ep[0], "real": ep[1], "previst": fi_previst(t0, f["prob"], t),
                    "horitzo": t0 + dt.timedelta(minutes=PAS_MIN * (len(f["prob"]) - 1))})
    return res, len(eps)


def resultat(casos, n_episodis):
    """Las cifras para decidir."""
    amb = [c for c in casos if c["previst"]]
    errors = [(c["previst"] - c["real"]).total_seconds() / 60 for c in amb]
    sense = [c for c in casos if not c["previst"]]
    return {"episodis": n_episodis, "passades": len(casos), "amb_final": len(amb),
            "encerts": sum(abs(e) <= ENCERT_MIN for e in errors),
            "massa_aviat": sum(e < -ENCERT_MIN for e in errors), "massa_tard": sum(e > ENCERT_MIN for e in errors),
            "error_mitja": round(sum(abs(e) for e in errors) / len(errors)) if errors else None,
            "sense_final": len(sense), "sense_final_be": sum(c["real"] > c["horitzo"] for c in sense)}


def text(r):
    return (f"Temps a Montflorit, final de la pluja segons el radar: ja hi ha {r['episodis']} episodis de pluja "
            f"amb dades cada 5 minuts ({r['passades']} passades mentre plovia). "
            f"Quan donava una hora de final ({r['amb_final']} vegades): {r['encerts']} a {ENCERT_MIN} minuts o menys, "
            f"{r['massa_aviat']} massa aviat i {r['massa_tard']} massa tard; error mitjà de {r['error_mitja']} minuts. "
            f"Quan deia que no s'acabava en 2 hores ({r['sense_final']}), ho encertava {r['sense_final_be']}. "
            "Digues a Claude si es mostra a la pàgina (ADR 0049).")


def verifica(avisa=True):
    """Cada día (aprenentatge.py diari): con MIN_EPISODIS episodios, el
    resultado a Juanjo, una sola vez."""
    if os.path.exists(AVIS):
        return None
    casos, n = compara(pluja_5min(), passades())
    if n < MIN_EPISODIS:
        return None
    t = text(resultat(casos, n))
    if avisa:
        subprocess.run(["avisar-juanjo", "--asunto", "meteo-local", t], check=False)
    os.makedirs(APRENENTATGE, exist_ok=True)
    open(AVIS, "w").close()
    return t


if __name__ == "__main__":
    if sys.argv[1:] == ["resum"]:
        casos, n = compara(pluja_5min(), passades())
        print(text(resultat(casos, n)) if casos else f"Encara no hi ha cap passada mentre plovia ({n} episodis).")
    else:
        print(__doc__)
