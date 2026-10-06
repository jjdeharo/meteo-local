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
#
# En el NAS, los datos (dades.json y casa.json) se suben en cada pasada a
# IONOS (bilateria.org/app/meteo-local/), de donde los lee la página, y la
# web entera a GitHub solo si ha cambiado el código, si hace GH_CADA_MIN
# minutos de la última vez o si IONOS falla: GitHub Pages admite unas 10
# publicaciones por hora (ADR 0020). Fuera del NAS, sin la clave de IONOS,
# todo va a GitHub como siempre.
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

# Si ANTERIOR es un archivo, se guarda ahí lo publicado para la próxima vez.
if [ "${SOLO_CASA:-0}" != 1 ] && [ "${ANTERIOR#http}" = "$ANTERIOR" ]; then
  cp "$sitio/dades.json" "$ANTERIOR"
fi

# Los datos, a IONOS: una conexión con una clave que solo puede dejar .json
# en su carpeta (la orden la fija IONOS en authorized_keys).
# El usuario y el servidor están en el NAS, fuera del repositorio, que es
# público: ~/.config/meteo-local/ionos.env (IONOS=usuario@servidor).
CLAU_IONOS=${CLAU_IONOS:-$HOME/.ssh/id_ionos}
CONF_IONOS=${CONF_IONOS:-$HOME/.config/meteo-local/ionos.env}
[ -f "$CONF_IONOS" ] && . "$CONF_IONOS"
GH_CADA_MIN=${GH_CADA_MIN:-30}
a_ionos=0
if [ -f "$CLAU_IONOS" ] && [ -n "${IONOS:-}" ]; then
  if tar -czf - -C "$sitio" dades.json casa.json \
      | ssh -i "$CLAU_IONOS" -o BatchMode=yes -o ConnectTimeout=20 "$IONOS" 2>/dev/null; then
    a_ionos=1
    echo "$(date '+%F %T')  dades a IONOS"
  else
    echo "$(date '+%F %T')  IONOS ha fallat: es publica a GitHub" >&2
  fi
fi

# A GitHub: siempre sin IONOS; con IONOS, si cambia el código o toca.
estat_gh="${ESTAT_GH:-$(dirname "${ANTERIOR#http*}")/gh-darrer}"
codi=$(git rev-parse HEAD 2>/dev/null || echo "?")
if [ "$a_ionos" = 1 ] && [ -f "$estat_gh" ]; then
  read -r darrer_t darrer_codi < "$estat_gh" || true
  if [ "$darrer_codi" = "$codi" ] && [ $(( $(date +%s) - ${darrer_t:-0} )) -lt $(( GH_CADA_MIN * 60 )) ]; then
    exit 0
  fi
fi

git -C "$sitio" init -q -b gh-pages
git -C "$sitio" add -A
git -C "$sitio" -c user.name="Juan Jose de Haro" -c user.email="jjdeharo@gmail.com" \
  commit -q -m "Previsió $(date '+%F %H:%M')"
git -C "$sitio" push -q -f "$DESTINO" gh-pages
if [ "${ANTERIOR#http}" = "$ANTERIOR" ]; then
  echo "$(date +%s) $codi" > "$estat_gh"
fi
echo "$(date '+%F %T')  publicado a GitHub"
