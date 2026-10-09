# Volver a montar meteo-local en otro NAS u otro hosting

Lo que hace falta si se pierde el NAS (primera parte) o IONOS (segunda
parte). Las claves de los dos, cifradas, y el registro del NAS están en el
repositorio privado `meteo-montflorit/meteo-local-registre` (ADR 0044 y
0045).

# Parte 1. El NAS

Mientras tanto, la reserva de IONOS calcula, publica y avisa sola (ADR 0032):
no hay prisa.

## 1. El programa

En el NAS nuevo, con Docker:

```sh
mkdir -p /volume1/docker/meteo-local/{home/.ssh,estat}
cd /volume1/docker/meteo-local
git clone https://github.com/meteo-montflorit/meteo-local.git repo
cp repo/nas/compose.yml repo/nas/Dockerfile repo/nas/reloj.sh .
```

`compose.yml` lee la versión de Claude Code de un `.env` (enlace al archivo
común `/volume1/docker/versiones/versiones.env`); si no existe, usa la del
`Dockerfile`. Ajusta `user:` al usuario del NAS nuevo.

## 2. Las claves

Todas están, cifradas con una contraseña que solo sabe Juanjo, en
`claus/claus-nas.tar.gz.gpg` del repositorio privado `meteo-local-registre`.
Dentro de `/volume1/docker/meteo-local/home`:

```sh
git clone git@github.com:meteo-montflorit/meteo-local-registre.git /tmp/registre
gpg -d /tmp/registre/claus/claus-nas.tar.gz.gpg | tar xzf -
chmod 700 .ssh && chmod 600 .ssh/id_*
```

Con eso las claves siguen autorizadas donde estaban y no hay que hacer nada
más. Si se pierde la contraseña, o si alguna clave se cambia, se generan de
nuevo y se autorizan así:

| Archivo en `home/` | Para qué | Dónde se autoriza o se obtiene |
|---|---|---|
| `.ssh/id_ed25519` | Leer y poner al día `meteo-montflorit/meteo-local` | GitHub, ajustes del repositorio > *Deploy keys*, «NAS meteo-local» |
| `.ssh/id_montflorit` | Publicar la web en `meteo-montflorit.github.io` | Ídem en ese repositorio, con escritura |
| `.ssh/id_registre` | Subir la copia diaria a `meteo-local-registre` | Ídem en ese repositorio, con escritura |
| `.ssh/id_ionos` | Subir `montflorit.json` y `avisos.json` a IONOS | `~/.ssh/authorized_keys` de IONOS, con `command="sh .meteo-reserva/bin/rep-dades",restrict` (ADR 0038) |
| `.config/meteo-local/ionos.env` | `IONOS=` usuario y servidor SSH del hosting | Panel de IONOS |
| `.config/meteo-local/ecowitt.env` | `ECOWITT_APPLICATION_KEY`, `ECOWITT_API_KEY`, `ECOWITT_MAC` | ecowitt.net > usuario > API Keys (ADR 0017) |
| `.config/meteo-local/wunderground.env` | `WU_STATION_ID`, `WU_STATION_KEY`: la estación de casa en Weather Underground (ADR 0059) | wunderground.com > Member Settings > Devices |
| `.config/meteo-local/claude.env` | `CLAUDE_CODE_OAUTH_TOKEN`, solo para el vigía del NAS | `claude setup-token` |
| `.local/bin/avisar-juanjo` y `.config/avisar-juanjo/config.json` | Los avisos a Juanjo por Telegram (`usuario`, `token`, `chat_id`) | El script está en el equipo de Juanjo; el token, en @BotFather |

Las claves SSH nuevas: `ssh-keygen -t ed25519 -N "" -f home/.ssh/<nombre>`,
y `ssh -i … git@github.com` una vez para aceptar la huella de GitHub e IONOS.

## 3. Los datos: el registro y el aprendizaje

Están en el repositorio privado `meteo-montflorit/meteo-local-registre`, un
commit por día:

```sh
git clone git@github.com:meteo-montflorit/meteo-local-registre.git /tmp/registre
cp -a /tmp/registre/registre /tmp/registre/aprenentatge estat/
```

Para un día anterior, `git checkout <commit>` antes de copiar. El resto de
`estat/` (cachés, último cálculo, estado de los avisos) se regenera solo.

## 4. Arrancar

```sh
docker compose up -d --build
docker compose logs -f        # «reloj en marcha» y, a la pasada siguiente, «publicado»
```

Cuando el NAS vuelve a publicar, la reserva de IONOS se aparta sola.

# Parte 2. IONOS (u otro hosting)

## Qué pasa mientras falta

- **La web sigue**: si IONOS no responde, la página lee la copia de los datos
  que el NAS publica en GitHub (cada 30 minutos como mucho; ADR 0038).
- **El NAS sigue** calculando y avisando a Juanjo; la subida a IONOS falla y
  solo queda apuntada.
- **Se paran el bot y los mensajes del canal** (el programa vive en IONOS) y
  **la reserva** (la que releva al NAS). El canal, el bot y sus nombres son
  de Telegram: no se pierden.

## Qué necesita el hosting nuevo

SSH con clave, cron, Python 3 con `venv`, `git` y una carpeta servida por la
web donde se pueda poner un `.htaccess` (o la cabecera CORS equivalente).

## 1. Las claves

En `claus/claus-ionos.tar.gz.gpg` del repositorio privado, con la misma
contraseña:

```sh
gpg -d claus-ionos.tar.gz.gpg | tar xzf -    # en el $HOME del hosting nuevo
```

Deja `.temps-bot/config.json` (el token del bot «Temps a Montflorit») y
`.vigilancia-nas/config.json` (el del bot de avisos a Juanjo, que usa la
reserva). El primero también está en el portátil de Juanjo
(`~/.config/credenciales/temps-montflorit-bot.json`, el que lee
`bot/instalar.sh`).

## 2. Instalar

Desde el portátil, con el alias `ionos-webspace` apuntando al hosting nuevo
(o con `IONOS_HOST=…`):

```sh
reserva/instalar.sh     # carpeta .meteo-reserva, receptor rep-dades, entorno de Python,
                        # app/meteo-local con su .htaccess, prueba y cron
bot/instalar.sh         # carpeta .temps-bot, configuración y cron del bot; avisos en el
                        # navegador: pywebpush, claves VAPID nuevas, subscripcio.php y cron
```

Y en `~/.ssh/authorized_keys` del hosting, la clave del NAS
(`id_ionos.pub`, en `claus-nas.tar.gz.gpg`) con la orden fija:

```
command="sh .meteo-reserva/bin/rep-dades",restrict ssh-ed25519 … meteo-local NAS -> IONOS
```

## 3. La dirección de los datos

Si cambia el dominio, en dos sitios: `DADES_URL` de `web/comu.js` (la web) y
`IONOS=` de `.config/meteo-local/ionos.env` del NAS (adónde sube). Y en
`reserva/htaccess-dades`, el origen permitido si cambia la web.

## 4. Los suscriptores del bot

No tienen copia: son datos personales y no salen del hosting (AGENTS.md;
`/baixa` los borra). En un cambio de hosting voluntario se pasa
`.temps-bot/subscriptors.json` directamente de un servidor al otro. Si el
hosting desaparece de golpe, el bot vuelve con su mismo nombre pero sin la
lista: se anuncia en el canal que quien lo usaba vuelva a escribir `/start`.

Lo mismo con los avisos en el navegador (ADR 0048): `.temps-bot/push.json` y
las claves `.temps-bot/vapid.json` se pasan juntos de un servidor al otro.
Sin ellos, `bot/instalar.sh` crea claves nuevas y cada uno tiene que volver a
tocar «Activa els avisos» en la página «Avisos»: las suscripciones antiguas
iban atadas a la clave perdida y la página, al no encontrarlas en el
servidor, las da por desactivadas.
