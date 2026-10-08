# Volver a montar meteo-local en otro NAS

Lo que hace falta si el NAS se pierde (ADR 0044). Mientras tanto, la reserva
de IONOS calcula, publica y avisa sola (ADR 0032): no hay prisa.

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

Ninguna está en los repositorios. Se generan de nuevo y se autorizan:

| Archivo en `home/` | Para qué | Dónde se autoriza o se obtiene |
|---|---|---|
| `.ssh/id_ed25519` | Leer y poner al día `meteo-montflorit/meteo-local` | GitHub, ajustes del repositorio > *Deploy keys*, «NAS meteo-local» |
| `.ssh/id_montflorit` | Publicar la web en `meteo-montflorit.github.io` | Ídem en ese repositorio, con escritura |
| `.ssh/id_registre` | Subir la copia diaria a `meteo-local-registre` | Ídem en ese repositorio, con escritura |
| `.ssh/id_ionos` | Subir `montflorit.json` y `avisos.json` a IONOS | `~/.ssh/authorized_keys` de IONOS, con `command="sh .meteo-reserva/bin/rep-dades",restrict` (ADR 0038) |
| `.config/meteo-local/ionos.env` | `IONOS=` usuario y servidor SSH del hosting | Panel de IONOS |
| `.config/meteo-local/ecowitt.env` | `ECOWITT_APPLICATION_KEY`, `ECOWITT_API_KEY`, `ECOWITT_MAC` | ecowitt.net > usuario > API Keys (ADR 0017) |
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
