#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Calcula la previsión y publica la web (web/ + dades.json) en la rama
# gh-pages, de la que sirve GitHub Pages. La rama tiene siempre un solo
# commit: se rehace en cada publicación para no llenar el historial.
#
# Lo usa el NAS (con reloj.sh), que es el único que publica; a mano también
# se puede ejecutar desde un ordenador con acceso al repositorio.
# Calcula las dos páginas: la del trayecto (dades.json) y la de casa
# (casa.json). Variables:
#   ANTERIOR    datos del trayecto publicados antes, para mantener la decisión
#               del día: una URL o un archivo (por defecto, la web publicada)
#   DESTINO     adónde se empuja (por defecto, el remoto origin)
#   SOLO_CASA   si vale 1, solo recalcula la página de casa y vuelve a
#               publicar los datos del trayecto tal como estaban (ANTERIOR)
#   COMENTARI   comentario del agente diario (agent/), si lo hay
set -euo pipefail
cd "$(dirname "$0")"

ANTERIOR=${ANTERIOR:-https://jjdeharo.github.io/meteo-local/dades.json}
DESTINO=${DESTINO:-$(git remote get-url origin)}

sitio=$(mktemp -d)
trap 'rm -rf "$sitio"' EXIT
cp -r web/. "$sitio/"
rm -f "$sitio/dades.json"
if [ "${SOLO_CASA:-0}" = 1 ]; then
  case "$ANTERIOR" in
    http*) curl -fsS "$ANTERIOR" -o "$sitio/dades.json" ;;
    *) cp "$ANTERIOR" "$sitio/dades.json" ;;
  esac
else
  python3 prevision.py --anterior "$ANTERIOR" --comentari "${COMENTARI:-/dev/null}" \
    --json "$sitio/dades.json"
fi
# Si Open-Meteo falla, casa.py reutiliza la última previsión buena (ADR 0016).
case "$ANTERIOR" in
  http*) CASA_ANTERIOR=https://jjdeharo.github.io/meteo-local/casa.json ;;
  *) CASA_ANTERIOR="$(dirname "$ANTERIOR")/casa.json" ;;
esac
python3 casa.py --json "$sitio/casa.json" --anterior "$CASA_ANTERIOR" >/dev/null
# Una copia de casa.json para el agente, junto a los datos del trayecto.
if [ "${ANTERIOR#http}" = "$ANTERIOR" ]; then
  cp "$sitio/casa.json" "$(dirname "$ANTERIOR")/casa.json"
fi
# Sin Jekyll: la web es HTML ya hecho.
touch "$sitio/.nojekyll"

git -C "$sitio" init -q -b gh-pages
git -C "$sitio" add -A
git -C "$sitio" -c user.name="Juan Jose de Haro" -c user.email="jjdeharo@gmail.com" \
  commit -q -m "Previsió $(date '+%F %H:%M')"
git -C "$sitio" push -q -f "$DESTINO" gh-pages

# Si ANTERIOR es un archivo, se guarda ahí lo publicado para la próxima vez.
if [ "${SOLO_CASA:-0}" != 1 ] && [ "${ANTERIOR#http}" = "$ANTERIOR" ]; then
  cp "$sitio/dades.json" "$ANTERIOR"
fi
echo "$(date '+%F %T')  publicado"
