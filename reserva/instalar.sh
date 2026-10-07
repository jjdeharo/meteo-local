#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Monta el servidor de reserva de Temps a Montflorit en IONOS (ADR 0032). Se
# ejecuta EN EL PORTÁTIL; se puede repetir: pone al día lo que haya.
#
#   reserva/instalar.sh            instala, prueba y programa el cron
#   reserva/instalar.sh --sin-cron sin tocar el cron
#
# En IONOS la sesión aterriza dentro de htdocs ($HOME es htdocs): la carpeta
# empieza por punto y lleva un .htaccess para que la web no la sirva. Usa las
# credenciales del bot que el vigía ya tiene en .vigilancia-nas/config.json.
set -euo pipefail

IONOS="${IONOS_HOST:-ionos-webspace}"
DIR=.meteo-reserva
URL_REPO=https://github.com/jjdeharo/meteo-local.git
BASE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"

echo "Carpeta, candado y aviso…"
ssh "$IONOS" "mkdir -p $DIR/bin $DIR/estat && chmod 700 $DIR"
cat "$BASE/htaccess" | ssh "$IONOS" "cat > $DIR/.htaccess"
cat "$BASE/avisar-juanjo" | ssh "$IONOS" "cat > $DIR/bin/avisar-juanjo && chmod 700 $DIR/bin/avisar-juanjo"

echo "Repositorio…"
ssh "$IONOS" "[ -d $DIR/repo/.git ] && git -C $DIR/repo pull -q --ff-only || git clone -q $URL_REPO $DIR/repo"

echo "Entorno de Python (numpy y Pillow)…"
ssh "$IONOS" "[ -x $DIR/v/bin/python ] || python3 -m venv $DIR/v; \
  OPENBLAS_NUM_THREADS=1 $DIR/v/bin/python -c 'import numpy, PIL' 2>/dev/null \
  || $DIR/v/bin/pip install -q --disable-pip-version-check numpy pillow"

echo "Prueba (calcula sin publicar ni avisar)…"
ssh "$IONOS" "RESERVA_SENSE_AVISOS=1 \$HOME/$DIR/v/bin/python \$HOME/$DIR/repo/reserva/reserva.py prova; tail -1 $DIR/registre.log"

if [ "${1:-}" != "--sin-cron" ]; then
  echo "Cron: vigila cada 5 minutos y prueba cada día a las 4:30…"
  ssh "$IONOS" "
    ( crontab -l 2>/dev/null | grep -v 'meteo-reserva' ;
      echo '*/5 * * * * \$HOME/$DIR/v/bin/python \$HOME/$DIR/repo/reserva/reserva.py vigila >>\$HOME/$DIR/cron.log 2>&1' ;
      echo '30 4 * * * \$HOME/$DIR/v/bin/python \$HOME/$DIR/repo/reserva/reserva.py prova >>\$HOME/$DIR/cron.log 2>&1' ) | crontab -
    crontab -l | grep meteo-reserva"
fi
echo "Hecho. Estado: ssh $IONOS '$DIR/v/bin/python $DIR/repo/reserva/reserva.py estat'"
