# 24. Web pública Temps a Montflorit

Fecha: 2026-10-06 · Estado: aceptado

## Contexto

Juanjo quiere dar a conocer la página «Temps a casa» como web del tiempo del
barrio, pero sin que salga la recomendación de moto o coche, que es de uso
familiar, y sin cambiar la web actual ni su portada. Preguntó si convenía un
clon con otro nombre y si se verían datos suyos o de su NAS.

## Decisión

- **Una sola pasada de cálculo y dos webs.** La pública es la página de casa
  publicada aparte, en el repositorio `jjdeharo/meteo-montflorit`
  (<https://jjdeharo.github.io/meteo-montflorit/>). No se mantiene a mano:
  `montflorit.py` la genera a partir de `web/` en cada publicación.
- **Qué cambia en la pública** (`CANVIS_INDEX` y `CANVIS_FONTS`): se llama
  «Temps a Montflorit»; no tiene el menú de páginas ni nada del trayecto;
  donde la de casa dice «casa» dice «Montflorit», y la estación propia es
  «una estació particular del barri», sin la distancia a la de Montflorit;
  manifiesto, icono (solo la nube) y caché de instalación propios; el pie
  enlaza su repositorio, no este. `casa.js` y `comu.js` son los mismos: leen
  del `<html>` el nombre del lugar, el archivo de datos y el enlace de la
  versión.
- **Datos aparte**: `montflorit.json`, los de `casa.json` sin `sortides` ni
  `sortida_per_defecte_h`, que llevan la recomendación del trayecto. Va a
  IONOS con los demás en cada pasada y, de reserva, junto a la web.
- **Publicación** (`publica.sh`): tras publicar esta web, se empuja la
  pública a la rama `gh-pages` de su repositorio (un solo commit, que se
  rehace), con una clave de despliegue del NAS que solo vale para él
  (`~/.ssh/id_montflorit`) y con la dirección anónima de GitHub en los
  commits. Si falla, esta web se publica igual y se reintenta en la
  siguiente.
- **Si la página de casa cambia** y un cambio deja de encajar, o queda una
  palabra del trayecto o «casa» en lo que se lee, `montflorit.py` falla: en
  las pruebas antes de publicar y, en el NAS, sin tocar la web pública.
- **Los buscadores**: de momento la pública conserva el `noindex`
  (`INDEXABLE = False`), hasta que el responsable de meteocerdanyola.com
  responda sobre el uso de su estación (ADR 0004).
- **En catalán y, aparte, en castellano** (ADR 0025).

## Alternativas descartadas

- **Un clon del programa en otro repositorio**: dos cálculos y dos códigos
  que se separarían con el tiempo.
- **Una segunda página escrita a mano**: el texto «D'on surt» cambia con el
  método y habría que acordarse de cambiarlo en dos sitios.
- **Hacer privado este repositorio y mover la web del trayecto**: oculta del
  todo el trayecto, pero GitHub Pages pide repositorio público en el plan
  gratuito y habría que cambiar de sitio la web actual. Juanjo eligió que la
  pública no lo enseñe ni lo enlace.
- **Quitar el trayecto de la web actual**: no quiere cambiarla.

## Consecuencias

- Este repositorio sigue siendo público y describe el trayecto y sus horas:
  quien llegue a él lo ve. La web pública no lo enlaza.
- Los datos públicos están en la misma carpeta de IONOS que los del trayecto
  (`bilateria.org/app/meteo-local/`), y el nombre de la carpeta se ve en el
  programa de la página.
- `estil.css` se comparte y conserva los estilos de la página del trayecto,
  que la pública no usa.
- Una publicación más en GitHub cada 30 minutos como mucho, en otro
  repositorio, con su propio límite.
- La versión es la de este programa; en la pública enlaza su repositorio.

## Evidencia

- La clave de IONOS del NAS acepta cualquier `.json` en su carpeta (orden
  fija en `authorized_keys`, comprobada el 06-10-2026): `montflorit.json` no
  ha pedido cambios allí. La carpeta ya permite leer los datos desde
  `jjdeharo.github.io`, que es también el origen de la web pública.
- En el repositorio y su historial no hay direcciones del NAS, claves ni
  tokens (búsqueda del 06-10-2026). Quien visita la web habla con GitHub y
  con bilateria.org, no con el NAS.
- Las coordenadas de `config.py` tienen tres decimales (unos 100 m) y ya
  eran públicas.

## Riesgos y limitaciones

- El uso de la estación de Montflorit de meteocerdanyola.com no tiene
  permiso expreso (ADR 0004). Si su responsable no lo quiere, la página
  tendrá que funcionar sin ella.
- El nombre puede hacer pensar que la web es de esa estación: la página dice
  de quién es cada dato en «D'on surt» y en «Fonts i crèdits».
- Los cambios de texto dependen de frases exactas de `casa.html`: tocar una
  de ellas obliga a tocar `montflorit.py`, y las pruebas lo avisan.

## Validación

`tests/test_montflorit.py` (la web se genera entera, sin archivos del
trayecto; lo que se lee no dice «casa», «cotxe», «moto», «trajecte» ni
«meteo-local»; la comprobación detecta esas palabras; si la página cambia,
falla; caché propia; los datos salen sin el trayecto). `probar-web` en
Chromium, Firefox y WebKit, en escritorio, móvil y tableta, con tema claro y
oscuro, y axe-core.
