#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# ADR 0070. Dades: calibracio/dades/veines (history/all de Weather Underground, 27-07 a 09-10-2026).
"""Regles de veritat i les veïnes com a senyal (sobre hores_veines.json)."""
import sys, os, json, datetime as dt, collections
sys.path.insert(0, os.path.expanduser("~/Documentos/github/meteo-local"))
import numpy as np
import aprenentatge as A
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "dades"); U = 0.2
PLOU = sys.argv[2].split(",") if len(sys.argv) > 2 else ["ICERDA6", "ICERDA18", "ICERDA28"]
SEC = sys.argv[3].split(",") if len(sys.argv) > 3 else ["ICERDA6", "ICERDA18", "ICERDA28"]
hores = json.load(open(os.path.join(S, "hores_veines.json")))
def actual(h):
    if h["casa"] is None: return None
    if h["casa"] >= U: return 1
    prop = [h[k] for k in ("XF", "XV", "ICERDA6") if h.get(k) is not None]
    return 0 if prop and all(x < U for x in prop) else None
def local(h):
    c = h["casa"]
    plouen = sum(1 for k in PLOU if h.get(k) is not None and h[k] >= U)
    if (c is not None and c >= U) or plouen >= 2: return 1
    if c is None: return None
    if plouen: return None                     # una veïna sola hi veu pluja: no se sap
    secs = [h[k] for k in SEC if h.get(k) is not None]
    if secs: return 0 if all(x < U for x in secs) else None
    prop = [h[k] for k in ("XF", "XV") if h.get(k) is not None]
    return 0 if prop and all(x < U for x in prop) else None
tr = collections.Counter((actual(h), local(h)) for h in hores)
nom = {1: "pluja", 0: "seca", None: "no se sap"}
print(f"PLOU={PLOU} SEC={SEC}")
for (a, l), n in sorted(tr.items(), key=lambda x: -x[1]):
    print(f"  ara {nom[a]:10} -> local {nom[l]:10}: {n}")
# hores noves de pluja (casa a zero i dues veïnes amb pluja): què deien la resta
noves = [h for h in hores if actual(h) != 1 and local(h) == 1]
for h in noves[:12]:
    print("   ", h["fins"][:16], {k: h.get(k) for k in ("casa", "ICERDA6", "ICERDA18", "ICERDA28", "ICERDA48", "XF", "XV")})
