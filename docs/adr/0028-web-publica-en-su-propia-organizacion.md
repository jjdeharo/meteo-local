# 28. Web pública en su propia organización

Fecha: 2026-10-07 · Estado: aceptado

## Contexto

«Temps a Montflorit» se publicaba en `jjdeharo/meteo-montflorit`, en
<https://jjdeharo.github.io/meteo-montflorit/> (ADR 0024). Juanjo quiso
cambiarla a la organización que había preparado, `meteo-montflorit`, para que
se lea en <https://meteo-montflorit.github.io/>, como sus demás aplicaciones,
que tienen casa propia. La dirección antigua ya se había dado a conocer, así
que tenía que seguir llevando a la web.

## Decisión

- **Dónde**: repositorio `meteo-montflorit/meteo-montflorit.github.io`, rama
  `gh-pages` (la que empuja `publica.sh`, ahora también la principal),
  publicada en <https://meteo-montflorit.github.io/>. `montflorit.py` (`REPO`),
  `publica.sh` (`DESTINO_MONTFLORIT`), `i18n/es.json` y los README apuntan ahí.
- **Clave del NAS**: la misma de antes (`~/.ssh/id_montflorit`), como clave de
  despliegue del repositorio nuevo, quitada del antiguo: GitHub no deja la
  misma en dos repositorios. La organización tenía las claves de despliegue
  desactivadas y se activaron.
- **Datos**: el `.htaccess` de `bilateria.org/app/meteo-local/` devuelve
  `Access-Control-Allow-Origin` con el origen que pide si es
  `jjdeharo.github.io` o `meteo-montflorit.github.io` (la cabecera solo admite
  uno), con `Vary: Origin`. No está en el repositorio: vive en IONOS.
- **La dirección antigua redirige**: `jjdeharo/meteo-montflorit` queda con
  páginas que llevan a la misma página de la web nueva (`index.html`,
  `fonts.html`, `es/` y, para cualquier otra ruta, `404.html`), con
  `meta refresh`, `location.replace` y `link rel="canonical"`, que los
  buscadores toman como traslado. Quitan el service worker antiguo y su
  magatzem, solo los de esta web: el origen `jjdeharo.github.io` lo comparten
  otras webs de Juanjo. `sw.js` se sustituye por uno que hace lo mismo y se da
  de baja. El repositorio se archiva.

## Alternativas descartadas

- **Dominio propio con CNAME**: no se pidió, y `github.io` no cuesta nada.
- **Redirección del servidor (301)**: GitHub Pages no la permite.
- **Una clave de despliegue nueva**: la antigua ya no tenía otro uso.

## Consecuencias

- Quien instaló la web como aplicación desde la dirección antigua la abre y
  pasa a la nueva; para tenerla instalada con la dirección nueva, hay que
  volver a instalarla.
- El NAS publica en el repositorio nuevo sin cambios en el contenedor:
  `publica.sh` se lee del repositorio en cada pasada.

## Evidencia

- `curl -H "Origin: …" https://bilateria.org/app/meteo-local/montflorit.json`:
  devuelve el origen para los dos dominios y nada para otro (07-10-2026).
- Desde el contenedor del NAS, `git ls-remote` al repositorio nuevo con
  `id_montflorit` responde (07-10-2026).

## Riesgos y limitaciones

- Si el `.htaccess` de IONOS se pierde o se reescribe con un solo origen, una
  de las dos webs se queda sin datos (recurre a la copia de su repositorio,
  que se actualiza cada media hora como mucho).
- Los enlaces antiguos dependen de que el repositorio archivado siga con
  Pages activado.

## Validación

Web nueva cargada con datos de IONOS en Chromium, Firefox y WebKit;
redirecciones de la portada, de `fonts.html`, de `es/` y de una ruta
inexistente comprobadas en el navegador (07-10-2026).
