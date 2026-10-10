#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# ADR 0070. Dades: calibracio/dades/veines (history/all de Weather Underground, 27-07 a 09-10-2026).
"""Model de l'arxiu: ajustat amb Sabadell i Sant Cugat o amb la pluja de Montflorit, jutjat a Montflorit."""
import sys, os, json, csv, datetime as dt
sys.path.insert(0, os.path.expanduser("~/Documentos/github/meteo-local"))
import numpy as np
import aprenentatge as A, config as C
from calibracio import regla_moto as R
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "dades"); U = 0.2
D = os.path.expanduser("~/Documentos/github/meteo-local/calibracio/dades")
acum = {}
for f in ("casa_30min.csv", "casa_5min.csv"):
    for r in csv.DictReader(open(os.path.join(D, f))):
        acum[dt.datetime.fromisoformat(r["t"])] = float(r["pluja_avui"]) if r["pluja_avui"] else None
def casa_hora(t):
    a, b = acum.get(t - dt.timedelta(hours=1)), acum.get(t)
    if a is None or b is None: return None
    return b if b - a < 0 else b - a
vh = {dt.datetime.fromisoformat(h["fins"]): h for h in json.load(open(os.path.join(S, "hores_veines.json")))}
VE = ["ICERDA6", "ICERDA18", "ICERDA28"]
ms = R.muestras()
per = {}
for (t, horas, est, x, mm, y) in ms:
    per.setdefault((t, horas), {"x": x, "obs": {}})["obs"][est] = y
X, Yxs, Yloc, T = [], [], [], []
for (t, horas), v in per.items():
    tl = t.astimezone()
    c = casa_hora(tl)
    h = vh.get(tl)
    # veritat local (ADR 0070)
    y = None
    vs = [h[k] for k in VE if h and h.get(k) is not None]
    mullen = [x for x in vs if x >= U]
    if (c is not None and c >= U) or len(mullen) >= 2: y = 1.0
    elif c is not None and not mullen:
        if vs: y = 0.0 if all(x < U for x in vs) else None
        elif len(v["obs"]) == 2 and max(v["obs"].values()) == 0: y = 0.0
    for est, yo in v["obs"].items():
        X.append(v["x"]); Yxs.append(yo); Yloc.append(np.nan if y is None else y); T.append((t, horas, est))
X = np.array(X); Yxs = np.array(Yxs, dtype=float); Yloc = np.array(Yloc)
t = [r[0] for r in T]; horas = np.array([r[1] for r in T]); est = np.array([r[2] for r in T])
grup = np.array([(ti.isocalendar()[0] * 53 + ti.isocalendar()[1]) % A.SETMANES_VALIDACIO for ti in t])
loc_ok = ~np.isnan(Yloc)
# una mostra per hora per a la veritat local (la primera estació)
primera = np.array([e == "XF" for e in est])
pA = np.zeros(len(Yxs)); pB = np.zeros(len(Yxs))
for g in np.unique(grup):
    tr, te = grup != g, grup == g
    wA = A.ajustar(X[tr], Yxs[tr])
    m = tr & loc_ok & primera
    wB = A.ajustar(X[m], Yloc[m])
    pA[te] = A.predecir(wA, X[te]); pB[te] = A.predecir(wB, X[te])
for nom, hh in (("curt termini", 0), ("un dia abans", 24)):
    s = loc_ok & primera & (horas == hh)
    y = Yloc[s]
    for n, p in (("ajustat amb Sabadell i Sant Cugat", pA[s]), ("ajustat amb Montflorit", pB[s])):
        print(f"{nom}, {n}: Brier {np.mean((p - y) ** 2):.5f}  ({s.sum()} hores, {int(y.sum())} amb pluja)")
