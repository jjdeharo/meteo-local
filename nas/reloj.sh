#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# El reloj de meteo-local dentro del contenedor del NAS.
#
# Cada minuto pregunta a que_toca.py si es hora de actualizar: lo decide con el
# horario de los últimos datos publicados, el mismo que muestra la web (en
# modo aviso, cada 10 minutos), así que lo que dice la página y lo que se hace
# no pueden separarse. Si toca, pone
# al día el repositorio, publica con publica.sh y apunta lo publicado en el
# registro. Las demás horas en punto (HORARIO_CASA) solo rehace la página de
# casa. A HORA_VERIFICACION comprueba la lluvia que cayó (registre.py) y la
# página de casa aprende de sus aciertos (aprenentatge.py). En
# AGENTE_HORAS ejecuta el agente diario y vuelve a publicar con su comentario.
# Además, cada minuto mira si main tiene commits nuevos y, si los tiene,
# publica enseguida: es el único que publica la web (ADR 0005).
#
#   reloj.sh         bucle (lo que arranca el contenedor)
#   reloj.sh --ara   una sola pasada, ya
set -u

REPO=/proyecto
URL_REPO=git@github.com:jjdeharo/meteo-local.git
ESTAT=/estat/dades.json
COMENTARI=/estat/comentari.json
WEB=https://jjdeharo.github.io/meteo-local/dades.json

registro() { printf '%s  %s\n' "$(date '+%F %T')" "$*"; }

prepara() {
  if [ ! -d "$REPO/.git" ]; then
    git clone -q "$URL_REPO" "$REPO" || { registro "no he podido clonar"; return 1; }
  fi
  git -C "$REPO" fetch -q origin main && git -C "$REPO" reset -q --hard origin/main \
    || { registro "no he podido poner al día el repositorio"; return 1; }
  # Sin datos guardados (primera vez o tras borrar estat/), los de la web.
  [ -s "$ESTAT" ] || curl -fsS "$WEB" -o "$ESTAT" || true
}

pasada() {
  prepara || return
  if ANTERIOR="$ESTAT" COMENTARI="$COMENTARI" DESTINO="$URL_REPO" bash "$REPO/publica.sh" >/dev/null; then
    registro "publicado"
    (cd "$REPO" && python3 registre.py apunta "$ESTAT") || registro "no he podido apuntar en el registro"
  else
    registro "ha fallado la publicación"
  fi
}

pasada_casa() {
  prepara || return
  SOLO_CASA=1 ANTERIOR="$ESTAT" DESTINO="$URL_REPO" bash "$REPO/publica.sh" >/dev/null \
    && registro "publicada la página de casa" || registro "ha fallado la página de casa"
}

verificacion() {
  prepara || return
  (cd "$REPO" && python3 registre.py verifica && python3 registre.py resum --avisa >/dev/null) \
    || registro "ha fallado la verificación del día"
  # La página de casa aprende de lo que pasó (ADR 0012).
  (cd "$REPO" && python3 aprenentatge.py diari >/dev/null) \
    && registro "aprendizaje de casa hecho" || registro "ha fallado el aprendizaje de casa"
}


hay_cambios() {
  remoto=$(git -C "$REPO" ls-remote -q origin refs/heads/main 2>/dev/null | cut -f1)
  [ -n "$remoto" ] && [ "$remoto" != "$(git -C "$REPO" rev-parse HEAD)" ]
}

agente() {
  prepara || return
  if (cd "$REPO" && agent/executa.sh "$1" >/dev/null); then
    registro "agente ($1): comentario escrito"
    pasada
  else
    registro "agente ($1): ha fallado; la página sigue sin comentario"
  fi
}

modo_agente() {
  python3 -c 'import sys; sys.path.insert(0, "/proyecto"); import config; print(config.AGENTE_HORAS.get(sys.argv[1], ""))' "$1"
}

hora_verificacion() {
  python3 -c 'import sys; sys.path.insert(0, "/proyecto"); import config; print(config.HORA_VERIFICACION)'
}


if [ "${1:-}" = "--ara" ]; then pasada; exit; fi

registro "reloj en marcha"
while true; do
  # Espera al principio del minuto siguiente.
  sleep $(( 60 - 10#$(date +%S) ))
  ahora=$(date +%H:%M)
  if [ ! -d "$REPO/.git" ]; then
    prepara
  else
    case "$(cd "$REPO" && python3 que_toca.py "$ahora" "$ESTAT" /estat/casa.json)" in
      completa) pasada ;;
      casa) pasada_casa ;;
    esac
  fi
  # Código nuevo en main: se publica ya, sin esperar a la próxima hora.
  if [ -d "$REPO/.git" ] && hay_cambios; then
    registro "hay código nuevo en main"
    pasada
  fi
  modo=$([ -d "$REPO/.git" ] && modo_agente "$ahora" || true)
  if [ -n "$modo" ]; then
    agente "$modo"
  fi
  if [ -d "$REPO/.git" ] && [ "$ahora" = "$(hora_verificacion)" ]; then
    verificacion
  fi
done
