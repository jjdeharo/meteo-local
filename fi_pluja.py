#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""¿A qué hora para la lluvia que está cayendo? (ADR 0049)

El radar llevado hacia delante (nowcast.py) da, cada 5 minutos y hasta 2
horas, la probabilidad de lluvia en casa. El final previsto es el primer
momento, desde la pasada, en que baja de un umbral durante unos minutos
seguidos (al principio, del 20 % durante 15 minutos); si no lo hace en el
horizonte, «no s'acaba en 2 hores». La página lo enseña «en entrenament».

Aprende sola: cada día prueba las VARIANTS con lo registrado y, si una se
equivoca al menos un 5 % menos que la que se usa (con MIN_EPISODIS_CANVI
episodios o más), pasa a usarla y lo dice a Juanjo. Se guarda en
aprenentatge/fi-pluja.json; el archivo «atura» lo para.

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
REGLA = os.path.join(APRENENTATGE, "fi-pluja.json")
ATURA = os.path.join(APRENENTATGE, "atura")
PER_DEFECTE = {"llindar": 0.2, "passos": 3}       # 20 %, 15 minutos
VARIANTS = [{"llindar": l, "passos": p} for l in (0.1, 0.2, 0.3) for p in (2, 3, 4)]
MIN_EPISODIS_CANVI = 3
MILLORA = 0.95
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


def regla():
    try:
        with open(REGLA, encoding="utf-8") as f:
            r = json.load(f)
        return {"llindar": r["llindar"], "passos": r["passos"]}
    except (OSError, ValueError, KeyError):
        return dict(PER_DEFECTE)


def fi_previst(t0, prob, des_de, r=None):
    """Primer momento desde des_de en que la probabilidad baja del umbral
    durante los pasos seguidos de la regla r; None si no pasa en el horizonte."""
    r = r or regla()
    for k in range(len(prob)):
        tk = t0 + dt.timedelta(minutes=PAS_MIN * k)
        tram = prob[k:k + r["passos"]]
        if tk >= des_de and len(tram) == r["passos"] and all(p < r["llindar"] for p in tram):
            return tk
    return None


def fi_radar(nc, ahora, arriba=None):
    """Para la página: {fi: hora o None, sense_fi: si no se ve el final en el
    horizonte}, desde ahora o desde que llegue la lluvia. None sin radar."""
    serie = ((nc or {}).get("llocs") or {}).get("casa")
    if not serie:
        return None
    t0 = dt.datetime.fromisoformat(nc["hora"])
    des_de = max(ahora, dt.datetime.fromisoformat(arriba)) if arriba else ahora
    fi = fi_previst(t0, [p["prob"] for p in serie], des_de)
    return {"fi": fi and fi.isoformat(timespec="minutes"), "sense_fi": fi is None}


def passades():
    res = []
    for ruta in sorted(glob.glob(os.path.join(DIR, "radar-fonts-*.jsonl"))):
        with open(ruta, encoding="utf-8") as f:
            res += [json.loads(l) for l in f if l.strip()]
    return res


def compara(pluja, regs, r=None):
    """Para cada pasada durante un episodio: el final real, el previsto con
    la regla r (o None) y el horizonte del radar."""
    eps = episodis(pluja)
    res = []
    for reg in regs:
        t = dt.datetime.fromisoformat(reg["t"])
        ep = next((e for e in eps if e[0] <= t <= e[1]), None)
        f = (reg.get("fonts") or {}).get(reg.get("triada"))
        if not ep or not f:
            continue
        t0 = dt.datetime.fromisoformat(f["hora"])
        res.append({"t": t, "episodi": ep[0], "real": ep[1], "previst": fi_previst(t0, f["prob"], t, r),
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


def error(casos):
    """Error medio en minutos de una regla: con hora de final, la distancia al
    final real; sin ella, nada si de verdad acababa más allá del radar y, si
    no, lo que faltaba hasta el horizonte."""
    if not casos:
        return None
    e = [abs((c["previst"] - c["real"]).total_seconds()) / 60 if c["previst"]
         else max(0.0, (c["horitzo"] - c["real"]).total_seconds() / 60) for c in casos]
    return sum(e) / len(e)


def aprèn(pluja, regs, avisa=True):
    """Prueba las variantes y, si una mejora bastante, pasa a usarla."""
    eps = episodis(pluja)
    if len(eps) < MIN_EPISODIS_CANVI or os.path.exists(ATURA):
        return None
    actual = regla()
    err_actual = error(compara(pluja, regs, actual)[0])
    millor = min(VARIANTS, key=lambda v: error(compara(pluja, regs, v)[0]) or 0)
    err_millor = error(compara(pluja, regs, millor)[0])
    if millor == actual or err_actual is None or err_millor >= MILLORA * err_actual:
        return None
    os.makedirs(APRENENTATGE, exist_ok=True)
    with open(REGLA + ".tmp", "w", encoding="utf-8") as f:
        json.dump({**millor, "error_min": round(err_millor, 1), "episodis": len(eps),
                   "des_de": dt.date.today().isoformat()}, f)
    os.replace(REGLA + ".tmp", REGLA)
    t = (f"Temps a Montflorit, final de la pluja segons el radar: passa a donar-la per acabada amb menys del "
         f"{round(millor['llindar'] * 100)} % durant {millor['passos'] * PAS_MIN} minuts (abans, "
         f"{round(actual['llindar'] * 100)} % i {actual['passos'] * PAS_MIN}). Error mitjà amb {len(eps)} episodis: "
         f"{err_millor:.0f} minuts, abans {err_actual:.0f}.")
    if avisa:
        subprocess.run(["avisar-juanjo", "--asunto", "meteo-local", t], check=False)
    return t


def text(r):
    return (f"Temps a Montflorit, final de la pluja segons el radar: ja hi ha {r['episodis']} episodis de pluja "
            f"amb dades cada 5 minuts ({r['passades']} passades mentre plovia). "
            f"Quan donava una hora de final ({r['amb_final']} vegades): {r['encerts']} a {ENCERT_MIN} minuts o menys, "
            f"{r['massa_aviat']} massa aviat i {r['massa_tard']} massa tard; error mitjà de {r['error_mitja']} minuts. "
            f"Quan deia que no s'acabava en 2 hores ({r['sense_final']}), ho encertava {r['sense_final_be']}. "
            "Es mostra a la pàgina «en entrenament»: digues a Claude si cal treure-ho o si ja no cal dir-ho (ADR 0049).")


def verifica(avisa=True):
    """Cada día (aprenentatge.py diari): aprende y, con MIN_EPISODIS
    episodios, manda el resultado a Juanjo, una sola vez."""
    pluja, regs = pluja_5min(), passades()
    canvi = aprèn(pluja, regs, avisa)
    if os.path.exists(AVIS):
        return canvi
    casos, n = compara(pluja, regs)
    if n < MIN_EPISODIS:
        return canvi
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
