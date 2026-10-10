#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# ADR 0070. Dades: calibracio/dades/veines (history/all de Weather Underground, 27-07 a 09-10-2026).
"""Les veïnes com a senyal de la probabilitat a curt termini, amb l'arxiu."""
import sys, os, json, datetime as dt, math
sys.path.insert(0, os.path.expanduser("~/Documentos/github/meteo-local"))
import numpy as np
import aprenentatge as A, config as C
from calibracio import regla_moto as R
from calibracio.pluja_casa import creuada
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "dades")
sys.argv = sys.argv[:2]; exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "veines_regles.py")).read().split("tr = collections")[0])
hores = {dt.datetime.fromisoformat(h["fins"]): h for h in json.load(open(os.path.join(S, "hores_veines.json")))}
PLOU = ["ICERDA6", "ICERDA18", "ICERDA28"]; SEC = PLOU
def mediana(h):
    v = sorted(h[k] for k in PLOU if h.get(k) is not None)
    if not v: return None
    n = len(v); return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2
xs = {}
for (t, horas, est, x, mm, y) in R.muestras():
    if horas == 0: xs.setdefault(t, x)
rows = []
for t, x in xs.items():
    tl = t.astimezone()
    h, a = hores.get(tl), hores.get(tl - dt.timedelta(hours=1))
    if not h or not a: continue
    y = local(h)
    if y is None or a["casa"] is None: continue
    v = mediana(a)
    if v is None: continue
    rows.append((t, x, a["casa"], v, y))
print("hores:", len(rows), "amb pluja:", sum(r[4] for r in rows))
t = np.array([r[0] for r in rows]); y = np.array([r[4] for r in rows], dtype=float)
grup = np.array([(ti.isocalendar()[0] * 53 + ti.isocalendar()[1]) % A.SETMANES_VALIDACIO for ti in t])
base = np.array([r[1] for r in rows])
cas = np.log1p(np.array([r[2] for r in rows]))[:, None]
vei = np.log1p(np.array([r[3] for r in rows]))[:, None]
mx = np.log1p(np.maximum(np.array([r[2] for r in rows]), np.array([r[3] for r in rows])))[:, None]
for nom, X in (("models", base), ("+ casa", np.hstack([base, cas])), ("+ casa + veïnes", np.hstack([base, cas, vei])),
               ("+ el màxim de casa i veïnes", np.hstack([base, mx]))):
    p = creuada(X, y, grup)
    brier = np.mean((p - y) ** 2)
    pl = y == 1
    print(f"  {nom:30} Brier {brier:.5f}  prob. mitjana amb pluja {p[pl].mean():.2f}, sense {p[~pl].mean():.3f}")
