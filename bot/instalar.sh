#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Monta el bot de Telegram de Temps a Montflorit en IONOS (ADR 0034). Se
# ejecuta EN EL PORTÁTIL; se puede repetir. Usa el clon del repositorio de la
# reserva (.meteo-reserva/repo, reserva/instalar.sh) y la clave del bot de
# ~/.config/credenciales/temps-montflorit-bot.json, que va directa a IONOS.
#
#   bot/instalar.sh            instala, registra las órdenes y programa el cron
#   bot/instalar.sh --sin-cron sin tocar el cron
set -euo pipefail

IONOS="${IONOS_HOST:-ionos-webspace}"
DIR=.temps-bot
BASE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
CLAU="$HOME/.config/credenciales/temps-montflorit-bot.json"

echo "Carpeta, candado y clave…"
ssh "$IONOS" "mkdir -p $DIR && chmod 700 $DIR && git -C .meteo-reserva/repo pull -q --ff-only"
cat "$BASE/htaccess" | ssh "$IONOS" "cat > $DIR/.htaccess"
cat "$CLAU" | ssh "$IONOS" "cat > $DIR/config.json && chmod 600 $DIR/config.json"

echo "Órdenes y descripción en Telegram…"
TOKEN=$(python3 -c "import json; print(json.load(open('$CLAU'))['token'])")
python3 - "$TOKEN" <<'PY'
import json, sys, urllib.parse, urllib.request
api = f"https://api.telegram.org/bot{sys.argv[1]}/"
def crida(metode, **p):
    dades = urllib.parse.urlencode({k: json.dumps(v) if isinstance(v, list) else v for k, v in p.items()}).encode()
    with urllib.request.urlopen(api + metode, dades, timeout=30) as r:
        assert json.load(r)["ok"], metode
TEXTOS = {
    "ca": ([("avisos", "Tria quins avisos reps"), ("resum", "El temps d'avui"), ("ara", "El temps ara"),
            ("baixa", "Deixa de rebre avisos i esborra les teves dades")],
           "Avisos del temps a Montflorit (Cerdanyola del Vallès): riera de Sant Cugat, perill per pluja o vent, "
           "pluja d'aquí a 15 minuts, trens i resum del dia. Tu tries què reps. Orientatiu, no oficial; la riera, en proves.",
           "Avisos del temps a Montflorit: riera, perill, pluja, trens i resum del dia."),
    "es": ([("avisos", "Elige qué avisos recibes"), ("resum", "El tiempo de hoy"), ("ara", "El tiempo ahora"),
            ("baixa", "Deja de recibir avisos y borra tus datos")],
           "Avisos del tiempo en Montflorit (Cerdanyola del Vallès): riera de Sant Cugat, peligro por lluvia o "
           "viento, lluvia dentro de 15 minutos, trenes y resumen del día. Tú eliges qué recibes. Orientativo, no oficial; la riera, en pruebas.",
           "Avisos del tiempo en Montflorit: riera, peligro, lluvia, trenes y resumen del día."),
}
for idioma, (ordres, descripcio, curta) in TEXTOS.items():
    for codi in ([idioma, ""] if idioma == "ca" else [idioma]):
        extra = {"language_code": codi} if codi else {}
        crida("setMyCommands", commands=[{"command": c, "description": d} for c, d in ordres], **extra)
        crida("setMyDescription", description=descripcio, **extra)
        crida("setMyShortDescription", short_description=curta, **extra)
print("fet")
PY

if [ "${1:-}" != "--sin-cron" ]; then
  echo "Cron: cada minuto…"
  ssh "$IONOS" "
    ( crontab -l 2>/dev/null | grep -v 'repo/bot/bot.py' ;
      echo '* * * * * python3 \$HOME/.meteo-reserva/repo/bot/bot.py >>\$HOME/$DIR/cron.log 2>&1' ) | crontab -
    crontab -l | grep bot.py"
fi
echo "Hecho. Estado: ssh $IONOS 'python3 .meteo-reserva/repo/bot/bot.py estat'"
