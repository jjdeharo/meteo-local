#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-or-later
# Recibe por SSH, desde el NAS, el tar.gz con los datos públicos de Temps a
# Montflorit y lo deja en app/meteo-local (ADR 0020). Es la orden fija de la
# clave del NAS en ~/.ssh/authorized_keys de IONOS:
#
#   command="sh .meteo-reserva/bin/rep-dades",restrict ssh-ed25519 …
#
# Solo acepta montflorit.json y avisos.json, como archivos normales (nada de
# enlaces, carpetas ni rutas), con JSON válido y de menos de MAX bytes. Si
# algo no cuadra, se rechaza el envío entero y no se toca nada: hasta la
# auditoría del 07-10-2026 la orden extraía el tar tal cual, y un enlace
# simbólico llamado *.json habría acabado en la carpeta pública (ADR 0038).
# Lo instala reserva/instalar.sh; se puede probar con REP_DIR=carpeta.
set -eu
d=${REP_DIR:-app/meteo-local}
t=$d/.rep
MAX=2000000
rebutja() { echo "rep-dades: rebutjat: $*" >&2; exit 1; }
rm -rf "$t"
mkdir "$t"
trap 'rm -rf "$t"' EXIT
head -c $((MAX + 1)) > "$t/in.tgz"
[ "$(wc -c < "$t/in.tgz")" -le "$MAX" ] || rebutja "més de $MAX bytes"
# Cada entrada del tar: un archivo normal («-») con uno de los dos nombres.
tar -tzvf "$t/in.tgz" | awk '
  { tipus = substr($1, 1, 1); nom = $NF }
  tipus != "-" || (nom != "montflorit.json" && nom != "avisos.json") { print "rep-dades: rebutjat: " $0 > "/dev/stderr"; mal = 1 }
  END { exit mal }' || exit 1
noms=$(tar -tzf "$t/in.tgz")
[ -n "$noms" ] || rebutja "buit"
tar -xzf "$t/in.tgz" -C "$t" --no-same-owner --no-same-permissions $noms
for n in $noms; do
  [ -f "$t/$n" ] && [ ! -L "$t/$n" ] || rebutja "$n no és un fitxer normal"
  python3 -c 'import json, sys; json.load(open(sys.argv[1], encoding="utf-8"))' "$t/$n" 2>/dev/null \
    || rebutja "$n no és JSON"
  chmod 604 "$t/$n"
done
for n in $noms; do
  mv -f "$t/$n" "$d/$n"
done
