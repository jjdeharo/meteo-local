#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Avisos privados a Juanjo por Telegram (avisar-juanjo) con reintento (ADR
0038).

Los avisos de peligro (riscos.py), de lluvia inminente (pluja_arriba.py) y de
la riera (riera.py) se mandan con avisar-juanjo, y cada programa apunta el
episodio como avisado antes de enviarlo. Hasta la auditoría del 07-10-2026,
si Telegram o la red fallaban en ese momento, el aviso se perdía: el episodio
ya constaba como avisado. Ahora el envío pasa por aquí: si avisar-juanjo no
devuelve 0, el aviso queda en una cola (avisos-pendents.jsonl, junto al
estado) y el reloj del NAS (nas/reloj.sh) y la reserva de IONOS
(reserva/reserva.py) la reintentan en cada pasada mientras el aviso tenga
sentido (su vigencia: 3 horas; el de lluvia en unos minutos, 20). Lo que
caduca sin entregarse se apunta en el registro de la pasada.

Uso:
  python3 avis_privat.py reintenta     reenvía los pendientes (lo hacen el reloj y la reserva)
  python3 avis_privat.py estat         los pendientes
"""
import datetime as dt
import json
import os
import subprocess
import sys

DIR = os.path.dirname(os.environ.get("REGISTRE_DIR", "/estat/registre"))
PENDENTS = os.path.join(DIR, "avisos-pendents.jsonl")
ORDRE = os.environ.get("AVISAR_JUANJO", "avisar-juanjo")
ASSUMPTE = "meteo-local"
VIGENCIA_MIN = 180


def ara_():
    return dt.datetime.now().astimezone()


def _executa(text, assumpte):
    """True si avisar-juanjo lo ha entregado (código 0)."""
    try:
        return subprocess.run([ORDRE, "--asunto", assumpte, text], check=False, timeout=120,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def pendents():
    try:
        with open(PENDENTS, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]
    except (OSError, ValueError):
        return []


def _desa(llista):
    os.makedirs(os.path.dirname(PENDENTS) or ".", exist_ok=True)
    with open(PENDENTS + ".tmp", "w", encoding="utf-8") as f:
        for p in llista:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    os.replace(PENDENTS + ".tmp", PENDENTS)


def envia(text, assumpte=ASSUMPTE, vigencia_min=VIGENCIA_MIN, ara=None):
    """Manda el aviso. True si Telegram lo ha aceptado; si no, queda apuntado
    para reintentarlo hasta que caduque."""
    if _executa(text, assumpte):
        return True
    ara = ara or ara_()
    llista = pendents()
    llista.append({"hora": ara.isoformat(timespec="minutes"),
                   "fins": (ara + dt.timedelta(minutes=vigencia_min)).isoformat(timespec="minutes"),
                   "assumpte": assumpte, "text": text})
    _desa(llista)
    return False


def reintenta(ara=None):
    """Reenvía los pendientes vigentes. Devuelve (entregados, caducados sin
    entregar, aún pendientes)."""
    llista = pendents()
    if not llista:
        return [], [], []
    ara = ara or ara_()
    entregats, caducats, queden = [], [], []
    for p in llista:
        if dt.datetime.fromisoformat(p["fins"]) < ara:
            caducats.append(p)
        elif _executa(p["text"], p["assumpte"]):
            entregats.append(p)
        else:
            queden.append(p)
    _desa(queden)
    return entregats, caducats, queden


if __name__ == "__main__":
    ordre = sys.argv[1] if len(sys.argv) > 1 else ""
    if ordre == "reintenta":
        entregats, caducats, queden = reintenta()
        for p in entregats:
            print(f"aviso privado entregado al reintentar (de las {p['hora'][11:16]}): {p['text'][:80]}")
        for p in caducats:
            print(f"aviso privado caducado sin entregar (de las {p['hora'][11:16]}): {p['text'][:80]}")
        if queden:
            print(f"{len(queden)} aviso(s) privado(s) pendiente(s) de entregar")
    elif ordre == "estat":
        print(json.dumps(pendents(), ensure_ascii=False, indent=1))
    else:
        print(__doc__)
        sys.exit(1)
