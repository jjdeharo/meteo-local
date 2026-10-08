#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copia del registro y del aprendizaje del NAS en un repositorio privado de
# GitHub (meteo-montflorit/meteo-local-registre), una vez al día (ADR 0044).
# Es lo único de meteo-local que solo está en el NAS y no se puede volver a
# pedir: lo que preveía la página cada hora junto a lo que pasó, los
# episodios de la riera y el estado del aprendizaje. Cada día queda un
# commit, así que se puede volver a cualquier día anterior. Los datos son
# del tiempo, sin nada personal; las claves no se copian.
#
# Lo llama el reloj (nas/reloj.sh). Escribe el resultado en
# $ESTAT_DIR/copia.json y, si lleva más de COPIA_DIES_AVIS días sin poder
# copiar, avisa a Juanjo una vez (avis_privat.py).
#
#   copia-registre.sh            copia ahora
set -u

ESTAT_DIR=${ESTAT_DIR:-/estat}
REPO=${REPO:-/proyecto}
DESTI=${COPIA_DESTI:-git@github.com:meteo-montflorit/meteo-local-registre.git}
CLAU=${COPIA_CLAU:-$HOME/.ssh/id_registre}
DIR=$ESTAT_DIR/copia-git
COPIA_DIES_AVIS=${COPIA_DIES_AVIS:-2}
avui=$(date +%F)

export GIT_SSH_COMMAND="ssh -i $CLAU -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=20"

desa_estat() {   # ok|fallada, text
  python3 - "$ESTAT_DIR/copia.json" "$1" "$avui" "$2" <<'PY'
import json, sys
ruta, res, avui, text = sys.argv[1:]
try:
    e = json.load(open(ruta))
except Exception:
    e = {}
e["darrer_intent"] = avui
e.setdefault("primer_intent", avui)
e["resultat"] = text
if res == "ok":
    e["darrera_ok"] = avui
    e.pop("avisat", None)
json.dump(e, open(ruta + ".tmp", "w"), ensure_ascii=False)
import os; os.replace(ruta + ".tmp", ruta)
PY
}

avisa_si_cal() {
  python3 - "$ESTAT_DIR/copia.json" "$avui" "$COPIA_DIES_AVIS" "$REPO" <<'PY'
import datetime as dt, json, os, sys
ruta, avui, dies, repo = sys.argv[1], dt.date.fromisoformat(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
e = json.load(open(ruta))
# Sense cap còpia bona encara, es compta des del primer intent.
ok = dt.date.fromisoformat(e.get("darrera_ok") or e.get("primer_intent") or sys.argv[2])
if (avui - ok).days > dies and not e.get("avisat"):
    sys.path.insert(0, repo)
    import avis_privat as AP
    AP.envia(f"Fa {(avui - ok).days} dies que el NAS no pot copiar el registre a GitHub "
             f"(meteo-local-registre). Darrer error: {e.get('resultat', '?')}", vigencia_min=24 * 60)
    e["avisat"] = sys.argv[2]
    json.dump(e, open(ruta, "w"), ensure_ascii=False)
PY
}

falla() { desa_estat fallada "$1"; avisa_si_cal; echo "copia del registro: $1"; exit 1; }

if [ ! -d "$DIR/.git" ]; then
  rm -rf "$DIR"
  git clone -q "$DESTI" "$DIR" 2>/dev/null || falla "no he podido clonar el repositorio de la copia"
fi
git -C "$DIR" config user.name "meteo-local (NAS)"
git -C "$DIR" config user.email "meteo-local@users.noreply.github.com"
git -C "$DIR" pull -q --ff-only origin main 2>/dev/null || true

# Lo que se copia: registre/ y aprenentatge/, enteros (sin las copias .bak).
for d in registre aprenentatge; do
  [ -d "$ESTAT_DIR/$d" ] || continue
  rm -rf "${DIR:?}/$d"
  cp -a "$ESTAT_DIR/$d" "$DIR/$d"
  find "$DIR/$d" -name '*.bak*' -delete
done
[ -f "$DIR/README.md" ] || printf '%s\n' "# Registre de meteo-local" "" \
  "Còpia diària, des del NAS, de \`/estat/registre\` i \`/estat/aprenentatge\` de" \
  "[meteo-local](https://github.com/meteo-montflorit/meteo-local). Privat." \
  "Com es recupera: \`nas/RESTAURAR.md\` del repositori del programa (ADR 0044)." > "$DIR/README.md"

git -C "$DIR" add -A
if git -C "$DIR" diff --cached --quiet; then
  desa_estat ok "sense canvis"
  exit 0
fi
git -C "$DIR" commit -q -m "Registre del $avui" || falla "no he podido hacer el commit"
git -C "$DIR" branch -M main
git -C "$DIR" push -q -u origin main 2>/dev/null || falla "no he podido subir a GitHub"
desa_estat ok "copiat"
echo "copia del registro hecha"
