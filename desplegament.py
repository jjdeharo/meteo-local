#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pone al día una copia del repositorio solo hasta el último commit de main
cuyas pruebas de GitHub han pasado (ADR 0038).

Hasta la auditoría del 07-10-2026, el reloj del NAS (nas/reloj.sh), la
reserva de IONOS (reserva/reserva.py) y el bot (bot/bot.py) desplegaban
cualquier commit nuevo de main sin mirar si la acción de pruebas
(.github/workflows/previsio.yml) había acabado o fallado. Ahora, antes de
mover la copia, se consulta la API pública de GitHub
(/commits/<sha>/check-runs, sin credenciales: 60 consultas por hora bastan,
porque solo se pregunta cuando main ha cambiado):

- pruebas en verde: se despliega;
- pendientes: se espera, como mucho ESPERA_MAX_MIN minutos (si la acción no
  arranca, no puede bloquear la publicación para siempre);
- fallidas: no se despliega y se apunta una vez; se queda el commit anterior
  y no se vuelve a preguntar por ese commit hasta pasados REPREGUNTA_MIN
  minutos (por si se repiten las pruebas), para no agotar las consultas;
- la API no responde: se despliega como hasta ahora, y se dice. Si lo que
  contesta es que se han agotado las consultas, se espera como con las
  pruebas pendientes.

El estado (desde cuándo se espera, qué fallo se ha apuntado ya) lo guarda
quien llama, en su propio archivo de estado.

Uso:
  python3 desplegament.py actualitza REPO ESTAT.json   pone al día REPO (lo que hace el reloj del NAS)
  python3 desplegament.py proves SHA                   ok | pendent | fallit | desconegut
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = os.environ.get("GITHUB_API", "https://api.github.com/repos/meteo-montflorit/meteo-local")
ESPERA_MAX_MIN = 20
REPREGUNTA_MIN = 15
BONES = ("success", "neutral", "skipped")


def estat_proves(sha):
    """ok | pendent | fallit | desconegut, según las comprobaciones de GitHub
    del commit."""
    req = urllib.request.Request(f"{API}/commits/{sha}/check-runs",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "meteo-local"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            dades = json.load(r)
    except urllib.error.HTTPError as ex:
        # Consultas agotadas (403 o 429): se espera, como con las pruebas pendientes.
        return "pendent" if ex.code in (403, 429) else "desconegut"
    except Exception:
        return "desconegut"
    runs = dades.get("check_runs") or []
    if not runs or any(r.get("status") != "completed" for r in runs):
        return "pendent"
    return "ok" if all(r.get("conclusion") in BONES for r in runs) else "fallit"


def git(repo, *args, **kw):
    return subprocess.run(["git", "-C", repo, *args], check=True, timeout=120, text=True,
                          capture_output=True, **kw).stdout.strip()


def actualitza(repo, estat, registra=print, proves=estat_proves):
    """Trae main y, si hay un commit nuevo, mueve la copia a él solo cuando se
    puede. Devuelve «igual» (nada nuevo), «pendent», «fallit», o «ok» o
    «desconegut» cuando se ha movido (con las pruebas en verde o sin poder
    comprobarlas)."""
    git(repo, "fetch", "-q", "origin", "main")
    remot, actual = git(repo, "rev-parse", "origin/main"), git(repo, "rev-parse", "HEAD")
    if remot == actual:
        estat.pop("proves_pendents", None)
        return "igual"
    fallides = estat.get("proves_fallides") or {}
    if fallides.get("sha") == remot and time.time() - fallides.get("hora", 0) < REPREGUNTA_MIN * 60:
        return "fallit"
    resultat = proves(remot)
    if resultat == "pendent":
        pendent = estat.get("proves_pendents")
        if not pendent or pendent.get("sha") != remot:
            pendent = estat["proves_pendents"] = {"sha": remot, "des_de": time.time()}
            registra(f"hay código nuevo en main ({remot[:7]}): se espera a que acaben las pruebas")
        if time.time() - pendent["des_de"] < ESPERA_MAX_MIN * 60:
            return "pendent"
        registra(f"las pruebas de {remot[:7]} llevan {ESPERA_MAX_MIN} min sin acabar: se despliega sin esperar más")
        resultat = "desconegut"
    elif resultat == "fallit":
        if fallides.get("sha") != remot:
            registra(f"las pruebas de {remot[:7]} han fallado: no se despliega; se queda {actual[:7]}")
        estat["proves_fallides"] = {"sha": remot, "hora": time.time()}
        return "fallit"
    git(repo, "reset", "-q", "--hard", remot)
    estat.pop("proves_pendents", None)
    estat.pop("proves_fallides", None)
    registra(f"repositorio en {remot[:7]} ("
             + ("pruebas en verde" if resultat == "ok" else "GitHub no responde: sin comprobar las pruebas") + ")")
    return resultat


def llegeix(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def desa(ruta, estat):
    with open(ruta + ".tmp", "w", encoding="utf-8") as f:
        json.dump(estat, f)
    os.replace(ruta + ".tmp", ruta)


if __name__ == "__main__":
    ordre = sys.argv[1] if len(sys.argv) > 1 else ""
    if ordre == "actualitza" and len(sys.argv) > 3:
        estat = llegeix(sys.argv[3])
        try:
            resultat = actualitza(sys.argv[2], estat, registra=lambda t: print(t, file=sys.stderr))
        finally:
            desa(sys.argv[3], estat)
        print(resultat)
    elif ordre == "proves" and len(sys.argv) > 2:
        print(estat_proves(sys.argv[2]))
    else:
        print(__doc__)
        sys.exit(1)
