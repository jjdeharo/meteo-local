#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprueba la respuesta del agente y la guarda como comentario del día.

Uso: python3 agent/desa.py MODE SORTIDA_CLAUDE.json DADES.json COMENTARI.json

Añade la hora, el modo y los niveles de riesgo que daba el programa cuando se
escribió: si después cambian, el comentario caduca (prevision.py).
"""
import datetime as dt
import json
import re
import sys

NIVELES = ("moto", "compte", "cotxe")


def extraer(sortida):
    """La respuesta de `claude -p --output-format json` lleva el texto del
    modelo en `result`; dentro tiene que haber un objeto JSON."""
    texto = json.loads(sortida)["result"]
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        raise ValueError("la respuesta no contiene un objeto JSON")
    return json.loads(m.group(0))


def main(modo, ruta_sortida, ruta_dades, ruta_comentari):
    with open(ruta_sortida, encoding="utf-8") as f:
        r = extraer(f.read())
    with open(ruta_dades, encoding="utf-8") as f:
        dades = json.load(f)
    texto = " ".join(str(r.get("text", "")).split())
    if not texto or len(texto) > 320:
        raise ValueError(f"texto vacío o demasiado largo ({len(texto)} caracteres)")
    if r.get("mitja") not in NIVELES:
        raise ValueError(f"nivel desconocido: {r.get('mitja')}")
    comentari = {
        "dia": dades["dia"], "mode": modo,
        "generat": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
        "text": texto, "mitja": r["mitja"], "confianca": r.get("confianca"),
        "nivells_programa": {"anada": dades["anada"]["nivell"],
                             "tornada": dades["tornada"]["nivell"]},
    }
    with open(ruta_comentari, "w", encoding="utf-8") as f:
        json.dump(comentari, f, ensure_ascii=False, indent=1)
    print(json.dumps(comentari, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:5])
