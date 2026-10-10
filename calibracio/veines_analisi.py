#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# ADR 0070. Dades: calibracio/dades/veines (history/all de Weather Underground, 27-07 a 09-10-2026).
"""Les veïnes contra l'estació de casa, hora a hora (27-07 a 04-10-2026)."""
import sys, os, csv, json, glob, datetime as dt, collections
sys.path.insert(0, os.path.expanduser("~/Documentos/github/meteo-local"))
import numpy as np
import config as C, ecowitt as E, wunderground as WU
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "dades")
D = os.path.expanduser("~/Documentos/github/meteo-local/calibracio/dades")
U = 0.2
# casa: comptador del dia cada 5 min
casa_f = []
for r in csv.DictReader(open(os.path.join(D, "casa_5min.csv"))):
    if r["pluja_avui"] != "":
        casa_f.append({"t": dt.datetime.fromisoformat(r["t"]), "pluja_avui": float(r["pluja_avui"])})
veines = {}
for est in C.VEINES:
    files = []
    for f in sorted(glob.glob(os.path.join(S, "veines", f"{est}-*.json"))):
        files += WU.files(json.load(open(f)))
    veines[est] = sorted(files, key=lambda x: x["t"])
def obs_meteocat(codi):
    o = {}
    for r in csv.reader(open(os.path.join(D, f"obs_{codi}.csv"))):
        if r[0] == "t" or r[0].startswith("fins"): continue
        try: o[dt.datetime.fromisoformat(r[0])] = float(r[1])
        except ValueError: pass
    return o
xf, xv = obs_meteocat("XF"), obs_meteocat("XV")
loc = dt.datetime(2026, 7, 27, 1).astimezone()
fi = dt.datetime(2026, 10, 4, 23).astimezone()
def mm(files, ini, fin):
    dins = [f for f in files if ini - dt.timedelta(minutes=10) <= f["t"] <= fin + dt.timedelta(minutes=10)]
    if len(dins) < 6: return None
    return E.pluja_entre(files, ini, fin)
def met(o, fin):
    # obs_ en UTC naïf? provem les dues mitges hores que acaben a fin
    # obs_*.csv: inici de cada mitja hora, en UTC
    k1 = (fin - dt.timedelta(minutes=60)).astimezone(dt.timezone.utc).replace(tzinfo=None)
    k2 = (fin - dt.timedelta(minutes=30)).astimezone(dt.timezone.utc).replace(tzinfo=None)
    a, b = o.get(k1), o.get(k2)
    return None if a is None or b is None else a + b
hores = []
t = loc
while t <= fi:
    ini = t - dt.timedelta(hours=1)
    h = {"fins": t, "casa": mm(casa_f, ini, t), "XF": met(xf, t), "XV": met(xv, t)}
    for est, fs in veines.items(): h[est] = mm(fs, ini, t)
    hores.append(h)
    t += dt.timedelta(hours=1)
json.dump([{**h, "fins": h["fins"].isoformat()} for h in hores], open(os.path.join(S, "hores_veines.json"), "w"))
V = list(C.VEINES)
print("hores:", len(hores), " amb casa:", sum(h["casa"] is not None for h in hores),
      " Meteocat:", sum(h["XF"] is not None for h in hores))
for est in V: print(f"  {est}: {sum(h[est] is not None for h in hores)} hores amb dades")
pluja_casa = [h for h in hores if h["casa"] is not None and h["casa"] >= U]
print(f"\nHores de pluja a casa: {len(pluja_casa)}")
for est in V:
    d = [h for h in pluja_casa if h[est] is not None]
    print(f"  {est}: no la veu en {sum(h[est] < U for h in d)} de {len(d)}")
for m in ("XF", "XV"):
    d = [h for h in pluja_casa if h[m] is not None]
    print(f"  {m}: no la veu en {sum(h[m] < U for h in d)} de {len(d)}")
print("\nHores amb casa a zero:")
seques = [h for h in hores if h["casa"] is not None and h["casa"] < U]
for est in V:
    d = [h for h in seques if h[est] is not None]
    altres = [h for h in d if all((h[o] or 0) < U for o in V if o != est)]
    print(f"  {est}: marca pluja en {sum(h[est] >= U for h in d)} de {len(d)}; quan cap altra veïna no en marca: {sum(h[est] >= U for h in altres)} de {len(altres)}")
