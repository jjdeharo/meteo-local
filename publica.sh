#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Calcula el tiempo en Montflorit (casa.py) y publica «Temps a Montflorit»
# (ADR 0024 y 0029): los datos en IONOS y la web en su repositorio. La web
# antigua de este repositorio (rama gh-pages, jjdeharo.github.io/meteo-local)
# solo tiene páginas que llevan a la pública (redireccions/, ADR 0030). Las
# ramas gh-pages tienen siempre un solo commit: se rehacen en cada publicación.
#
# Lo usa el NAS (con reloj.sh), que es el único que publica; a mano también
# se puede ejecutar desde un ordenador con acceso a los repositorios.
# Variables:
#   ESTAT_DIR   carpeta del estado (en el NAS, /estat): ahí se deja casa.json
#               para los avisos y se lee el de la pasada anterior, por si
#               Open-Meteo falla (ADR 0016). Sin ella, el publicado.
#   DESTINO     adónde se empuja la web antigua (por defecto, el remoto origin)
#   DESTINO_MONTFLORIT  adónde se empuja la web pública; vacío, no se publica
#
# En el NAS, los datos de la web pública (montflorit.json: los de casa sin lo
# privado) se suben en cada pasada a IONOS (bilateria.org/app/meteo-local/),
# de donde los lee la página, y las webs a GitHub solo si ha cambiado el
# código, si hace GH_CADA_MIN minutos de la última vez o si IONOS falla:
# GitHub Pages admite unas 10 publicaciones por hora (ADR 0020). La copia de
# los datos en el repositorio de la web pública es la reserva si IONOS no
# responde. Fuera del NAS, sin la clave de IONOS, todo va a GitHub.
set -euo pipefail
cd "$(dirname "$0")"

ESTAT_DIR=${ESTAT_DIR:-}
DESTINO=${DESTINO:-$(git remote get-url origin)}
DESTINO_MONTFLORIT=${DESTINO_MONTFLORIT-git@github.com:meteo-montflorit/meteo-montflorit.github.io.git}

sitio=$(mktemp -d)
publica=$(mktemp -d)
dades=$(mktemp -d)
trap 'rm -rf "$sitio" "$publica" "$dades"' EXIT

# Si Open-Meteo falla, casa.py reutiliza la última previsión buena (ADR 0016).
if [ -n "$ESTAT_DIR" ]; then
  CASA_ANTERIOR="$ESTAT_DIR/casa.json"
else
  CASA_ANTERIOR=https://bilateria.org/app/meteo-local/montflorit.json
fi
python3 casa.py --json "$dades/casa.json" --anterior "$CASA_ANTERIOR" >/dev/null
# Una copia para los avisos por Telegram (riscos.py, pluja_arriba.py, riera.py).
[ -z "$ESTAT_DIR" ] || cp "$dades/casa.json" "$ESTAT_DIR/casa.json"
# Los datos de la web pública: los de casa sin lo privado.
python3 montflorit.py dades "$dades/casa.json" "$publica/montflorit.json"

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
  if tar -czf - -C "$publica" montflorit.json \
      | ssh -i "$CLAU_IONOS" -o BatchMode=yes -o ConnectTimeout=20 "$IONOS" 2>/dev/null; then
    a_ionos=1
    echo "$(date '+%F %T')  dades a IONOS"
  else
    echo "$(date '+%F %T')  IONOS ha fallat: es publica a GitHub" >&2
  fi
fi

# A GitHub: siempre sin IONOS; con IONOS, si cambia el código o toca.
estat_gh="${ESTAT_GH:-${ESTAT_DIR:-$dades}/gh-darrer}"
codi=$(git rev-parse HEAD 2>/dev/null || echo "?")
if [ "$a_ionos" = 1 ] && [ -f "$estat_gh" ]; then
  read -r darrer_t darrer_codi < "$estat_gh" || true
  if [ "$darrer_codi" = "$codi" ] && [ $(( $(date +%s) - ${darrer_t:-0} )) -lt $(( GH_CADA_MIN * 60 )) ]; then
    exit 0
  fi
fi

# La web antigua: solo redirecciones a la pública (ADR 0030).
cp -r redireccions/. "$sitio/"
touch "$sitio/.nojekyll"
git -C "$sitio" init -q -b gh-pages
git -C "$sitio" add -A
git -C "$sitio" -c user.name="Juan Jose de Haro" -c user.email="jjdeharo@gmail.com" \
  commit -q -m "Redirecció a Temps a Montflorit"
git -C "$sitio" push -q -f "$DESTINO" gh-pages
[ -z "$ESTAT_DIR" ] || echo "$(date +%s) $codi" > "$estat_gh"
echo "$(date '+%F %T')  publicado a GitHub"

# La web pública, a su repositorio, con su propia clave de despliegue si la
# hay (en el NAS). Un fallo aquí no detiene nada: se reintenta en la próxima.
if [ -n "$DESTINO_MONTFLORIT" ]; then
  CLAU_MONTFLORIT=${CLAU_MONTFLORIT:-$HOME/.ssh/id_montflorit}
  if (
    python3 montflorit.py web "$publica"
    [ ! -f "$CLAU_MONTFLORIT" ] || export GIT_SSH_COMMAND="ssh -i $CLAU_MONTFLORIT -o IdentitiesOnly=yes"
    git -C "$publica" init -q -b gh-pages
    git -C "$publica" add -A
    git -C "$publica" -c user.name="Juan José de Haro" -c user.email="8707929+jjdeharo@users.noreply.github.com" \
      commit -q -m "Previsió $(date '+%F %H:%M')"
    git -C "$publica" push -q -f "$DESTINO_MONTFLORIT" gh-pages
  ); then
    echo "$(date '+%F %T')  publicada la web de Montflorit"
  else
    echo "$(date '+%F %T')  no s'ha pogut publicar la web de Montflorit" >&2
  fi
fi
