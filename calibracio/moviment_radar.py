#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprueba cómo acierta el radar llevado hacia delante según de dónde salga
el movimiento (ADR 0023): de todo el cuadro de 300 km o de la lluvia de cerca
del trayecto.

Parte de una tarde de imágenes guardadas (no están en el repositorio):
  radar-FECHA.npz     hores, ims (mm/h), casa (fila, columna), km_px
  adveccio-FECHA.npz  bases, a6 y a60 (las previsiones de Meteocat a 6 y 60 min)
Las del 06-10-2026 se sacaron de la caché del NAS (/estat/radar-cache), que
guarda 3 horas, componiendo los mosaicos con nowcast.mosaic.

Para cada imagen se lleva la lluvia 60 y 120 minutos hacia delante y se
compara con lo que el radar vio después, en puntos cada 10 km a menos de 55
km de casa: probabilidad como en nowcast.serie (fracción del círculo con
lluvia) contra si llovió en el punto (la mitad o más de un círculo de 3 km).

Uso: python3 calibracio/moviment_radar.py calibracio/dades/radar-2026-10-06.npz calibracio/dades/adveccio-2026-10-06.npz
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config as C  # noqa: E402
import nowcast as N  # noqa: E402


def minuts(hora):
    return int(hora[:2]) * 60 + int(hora[3:])


def fraccio(camp, fila, col, radi_km, km_px, salt=(0, 0)):
    """Fracción con lluvia del círculo, con la imagen desplazada salt."""
    r = int(radi_km / km_px) + 1
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    f, c = fila - salt[0], col - salt[1]
    return (camp[f - r:f + r + 1, c - r:c + r + 1][yy ** 2 + xx ** 2 <= (radi_km / km_px) ** 2] >= N.PLOU_MMH).mean()


def main(ruta_radar, ruta_adveccio):
    d, a = np.load(ruta_radar), np.load(ruta_adveccio)
    hores = {minuts(str(h)): i for i, h in enumerate(d["hores"])}
    ims, km_px = d["ims"].astype(float), float(d["km_px"])
    fc, cc = (int(round(float(x))) for x in d["casa"])
    lat, lon = (C.CASA[0] + C.DESTINO[0]) / 2, (C.CASA[1] + C.DESTINO[1]) / 2
    tx, ty = N.geometria(lat, lon)
    r = {"tx": tx, "ty": ty, "km_px": km_px}
    punts = [(fc + int(j * 10 / km_px), cc + int(i * 10 / km_px))
             for j in range(-5, 6) for i in range(-5, 6) if np.hypot(i, j) * 10 <= 55]
    for avanc in (60, 120):
        radi = N.RADI_KM[0] + N.RADI_KM[1] * avanc
        casos = {}
        for k, base in enumerate(a["bases"]):
            m = minuts(str(base))
            if m not in hores or m + avanc not in hores:
                continue
            a6, a60 = a["a6"][k].astype(float), a["a60"][k].astype(float)
            ara, despres = ims[hores[m]], ims[hores[m + avanc]]
            vectors = {"quieta": (0.0, 0.0), "cuadro de 300 km": N.desplacament(a6, a60),
                       "lluvia de cerca": N.desplacament_local(a6, a60, r, 54) or N.desplacament(a6, a60)}
            if None in vectors.values():
                continue
            for nom, v in vectors.items():
                salt = (int(round(v[0] / 54 * avanc)), int(round(v[1] / 54 * avanc)))
                for f, c in punts:
                    casos.setdefault(nom, []).append(
                        (fraccio(ara, f, c, radi, km_px, salt), fraccio(despres, f, c, 3.0, km_px) >= 0.5))
        print(f"A {avanc} minutos:")
        for nom, llista in casos.items():
            p, o = np.array(llista).T
            print(f"  {nom:17s} Brier {((p - o) ** 2).mean():.3f} · con 50 % o más: {int(((p >= .5) & (o == 1)).sum())} aciertos, "
                  f"{int(((p >= .5) & (o == 0)).sum())} falsas alarmas, {int(((p < .5) & (o == 1)).sum())} lluvias sin anunciar "
                  f"(n = {len(p)}, llovió en el {o.mean():.0%})")


if __name__ == "__main__":
    main(*sys.argv[1:3])
