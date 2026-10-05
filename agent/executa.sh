#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Ejecuta el agente diario: prepara la imagen del radar, le pasa los datos ya
# calculados a Claude (solo puede leer archivos) y guarda su comentario.
#
#   agent/executa.sh mati|tarda
#
# Variables (con los valores del NAS por defecto):
#   DADES, CASA        datos publicados del trayecto y de casa
#   COMENTARI          dónde se guarda el comentario
#   CLAUDE_ENV         archivo con CLAUDE_CODE_OAUTH_TOKEN (claude setup-token)
set -euo pipefail
cd "$(dirname "$0")/.."

MODO=${1:?mati o tarda}
DADES=${DADES:-/estat/dades.json}
CASA=${CASA:-/estat/casa.json}
COMENTARI=${COMENTARI:-/estat/comentari.json}
CLAUDE_ENV=${CLAUDE_ENV:-$HOME/.config/meteo-local/claude.env}
MODELO=$(python3 -c 'import config; print(config.AGENTE_MODELO)')

if [ -f "$CLAUDE_ENV" ]; then
  set -a; . "$CLAUDE_ENV"; set +a
fi

trabajo=$(mktemp -d)
trap 'rm -rf "$trabajo"' EXIT
cp "$DADES" "$trabajo/dades.json"
cp "$CASA" "$trabajo/casa.json"
python3 agent/radar.py "$trabajo/radar.png" >/dev/null

prompt="$(cat agent/instruccions.md)

---
Modo: $MODO. Hora: $(date '+%H:%M') del $(date '+%d-%m-%Y').
Archivos: $trabajo/dades.json, $trabajo/casa.json y la imagen $trabajo/radar.png."

(cd "$trabajo" && claude -p "$prompt" --model "$MODELO" --output-format json \
  --max-turns 6 --allowedTools "Read" < /dev/null > "$trabajo/sortida.json")
python3 agent/desa.py "$MODO" "$trabajo/sortida.json" "$DADES" "$COMENTARI"
