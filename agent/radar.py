#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Imagen del radar para el agente: tres fotogramas (hace 1 h, hace 30 min y
el último) de RainViewer sobre el mapa de OpenStreetMap, alrededor del
trayecto, con el trayecto marcado en rojo.

Uso: python3 agent/radar.py SALIDA.png
"""
import datetime as dt
import io
import json
import math
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

UA = {"User-Agent": "meteo-local/" + C.VERSION}
Z = 7


def imagen(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGBA")


def main(salida):
    meta = json.load(urllib.request.urlopen(
        urllib.request.Request("https://api.rainviewer.com/public/weather-maps.json", headers=UA),
        timeout=30))
    n = 2 ** Z
    lat = (C.CASA[0] + C.DESTINO[0]) / 2
    lon = (C.CASA[1] + C.DESTINO[1]) / 2
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    tx, ty = int(x), int(y)
    px, py = 256 + int((x - tx) * 256), 256 + int((y - ty) * 256)
    base = Image.new("RGBA", (768, 768))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            base.alpha_composite(imagen(f"https://tile.openstreetmap.org/{Z}/{tx + dx}/{ty + dy}.png"),
                                 ((dx + 1) * 256, (dy + 1) * 256))
    paneles = []
    for f in (meta["radar"]["past"][-7], meta["radar"]["past"][-4], meta["radar"]["past"][-1]):
        im = base.copy()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                im.alpha_composite(imagen(f"{meta['host']}{f['path']}/256/{Z}/{tx + dx}/{ty + dy}/2/1_0.png"),
                                   ((dx + 1) * 256, (dy + 1) * 256))
        # Unos 180 km de lado, centrado en el trayecto.
        recorte = im.crop((px - 100, py - 100, px + 100, py + 100)).resize((400, 400), Image.NEAREST)
        d = ImageDraw.Draw(recorte)
        d.ellipse((194, 194, 206, 206), outline=(255, 0, 0, 255), width=3)
        hora = dt.datetime.fromtimestamp(f["time"]).astimezone().strftime("%H:%M")
        d.rectangle((0, 0, 58, 18), fill=(255, 255, 255, 255))
        d.text((5, 3), hora, fill=(0, 0, 0, 255))
        paneles.append(recorte)
    hoja = Image.new("RGBA", (1220, 400), (255, 255, 255, 255))
    for i, p in enumerate(paneles):
        hoja.paste(p, (i * 410, 0))
    hoja.convert("RGB").save(salida)
    print(salida)


if __name__ == "__main__":
    main(sys.argv[1])
