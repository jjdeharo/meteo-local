#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Los avisos de Temps a Montflorit como notificaciones del navegador, sin
Telegram (ADR 0048).

Vive en IONOS junto al bot (bot.py) y reparte lo mismo, a quien lo ha pedido
en la página «Avisos» de la web: los avisos de avisos.json (riera, peligro,
lluvia en unos minutos, trenes) y la previsión diaria a la hora elegida. Las
suscripciones las guarda subscripcio.php en push.json; aquí solo se leen, se
borran las que el servicio de notificaciones da por muertas y se marca la
prueba como hecha.

El cron lo arranca cada minuto con el entorno de Python de la reserva, que
tiene pywebpush (bot/instalar.sh). Lo que no entra se reintenta cada minuto
mientras el aviso esté vigente, como en el bot.

Uso: push.py            una vuelta (lo que hace el cron)
     push.py estat      suscripciones y pendientes
     push.py claus      crea las claves VAPID si no las hay (bot/instalar.sh)
"""
import base64
import contextlib
import datetime as dt
import fcntl
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot as B  # noqa: E402

SUBS = os.path.join(B.BASE, "push.json")
ESTAT = os.path.join(B.BASE, "push-estat.json")
CLAUS = os.path.join(B.BASE, "vapid.json")
CADENAT_SUBS = os.path.join(B.BASE, "push.lock")       # el mismo que usa subscripcio.php
CONTACTE = "mailto:avisos@bilateria.org"
# Lo que tarda en dejar de valer una notificación que no ha podido entregarse
# (el móvil apagado): la vigencia del aviso, como en el bot.
TTL_RESUM_S = 3 * 3600
TTL_PROVA_S = 15 * 60
PROVA_MIN = 10          # una prueba pedida hace más de esto ya no se manda
COS_MAX = 1500          # el cuerpo de la notificación, en caracteres
URL = {"pluja": "./", "riera": "./", "perill": "./", "trens": "sortir.html#trens"}


def url(pagina, idioma):
    """La página en el idioma de quien la recibe: la de castellano, en es/."""
    if idioma != "es":
        return pagina
    return "es/" if pagina == "./" else "es/" + pagina
PROVA = {"ca": ("Prova de Temps a Montflorit", "Els avisos funcionen en aquest dispositiu."),
         "es": ("Prueba de Temps a Montflorit", "Los avisos funcionan en este dispositivo.")}


# --- Texto -------------------------------------------------------------------------------

def notificacio(text, url="./", etiqueta=None):
    """Título y cuerpo a partir de un mensaje del bot (HTML de Telegram): el
    título, la primera línea en negrita; el cuerpo, el resto sin etiquetas ni
    el enlace a la web, que ya abre la notificación."""
    linies = text.strip().split("\n")
    titol = re.sub(r"<[^>]+>", "", linies[0])
    cos = "\n".join(l for l in linies[1:] if l.strip() != B.WEB.rstrip("/") and l.strip() != B.WEB)
    cos = re.sub(r"<[^>]+>", "", cos)
    cos = re.sub(r"\n{3,}", "\n\n", cos).strip()
    if len(cos) > COS_MAX:
        cos = cos[:COS_MAX - 1].rstrip() + "…"
    res = {"title": html.unescape(titol).strip(), "body": html.unescape(cos), "url": url}
    if etiqueta:
        res["tag"] = etiqueta
    return res


# --- Archivos ----------------------------------------------------------------------------

@contextlib.contextmanager
def subscripcions():
    """push.json con el candado que comparte con subscripcio.php: lo que se
    cambie dentro se guarda al salir."""
    with open(CADENAT_SUBS, "a") as cadenat:
        fcntl.flock(cadenat, fcntl.LOCK_EX)
        subs = B.llegeix(SUBS, {})
        abans = json.dumps(subs, sort_keys=True)
        yield subs
        if json.dumps(subs, sort_keys=True) != abans:
            B.desa(SUBS, subs)


def claus():
    """Las claves VAPID: se crean una vez y no se copian a ningún sitio; si se
    pierden, cada uno vuelve a activar los avisos (RESTAURAR.md)."""
    dades = B.llegeix(CLAUS, {})
    if dades.get("privada") and dades.get("publica"):
        return dades
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    privada = ec.generate_private_key(ec.SECP256R1())
    pem = privada.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode()
    punt = privada.public_key().public_bytes(serialization.Encoding.X962,
                                             serialization.PublicFormat.UncompressedPoint)
    dades = {"privada": pem, "publica": base64.urlsafe_b64encode(punt).rstrip(b"=").decode()}
    B.desa(CLAUS, dades)
    os.chmod(CLAUS, 0o600)
    return dades


# --- Enviar ------------------------------------------------------------------------------

class Morta(Exception):
    """El servicio de notificaciones dice que la suscripción ya no existe."""


_vapid = None


def envia_push(sub, dades, ttl, urgent=False):
    global _vapid
    from py_vapid import Vapid
    from pywebpush import WebPushException, webpush
    # La clave, ya cargada: pywebpush no acepta el PEM como texto.
    _vapid = _vapid or Vapid.from_pem(claus()["privada"].encode())
    try:
        webpush({"endpoint": sub["endpoint"], "keys": sub["keys"]}, json.dumps(dades, ensure_ascii=False),
                vapid_private_key=_vapid, vapid_claims={"sub": CONTACTE}, ttl=ttl,
                headers={"Urgency": "high" if urgent else "normal"}, timeout=15)
    except WebPushException as ex:
        estat = getattr(ex.response, "status_code", None)
        if estat in (404, 410):
            raise Morta() from ex
        raise RuntimeError(f"{estat}: {str(ex)[:120]}") from ex


def reparteix(estat, moment, envia=envia_push):
    """Una vuelta: avisos nuevos, reintentos, la previsión y las pruebas.
    Devuelve las suscripciones muertas, para borrarlas."""
    with subscripcions() as s:
        subs = {e: dict(v, endpoint=e) for e, v in s.items()}
    mortes = set()
    enviats = estat.setdefault("enviats", {})
    pendents = estat.setdefault("pendents", {})
    avisos = B.llegeix(os.path.join(B.DADES, "avisos.json"), {}).get("avisos", [])
    for a in B.a_repartir(avisos, enviats, moment):
        enviats[a["id"]] = moment.isoformat(timespec="minutes")
        pendents[a["id"]] = {"avis": a, "subs": [e for e, v in subs.items() if a["tipus"] in v.get("avisos", [])]}

    def prova(e, crida):
        try:
            crida()
            return True
        except Morta:
            mortes.add(e)
            return True
        except Exception as ex:
            return str(ex)

    for clau, p in list(pendents.items()):
        a = p["avis"]
        if not B.a_repartir([a], {}, moment):
            if p["subs"]:
                B.registra(f"push: aviso {clau} caducado sin entregar a {len(p['subs'])} suscripción(es)")
            del pendents[clau]
            continue
        queden, motius = [], []
        ttl = B.VIGENCIA_MIN.get(a["tipus"], 60) * 60
        for e in p["subs"]:
            sub = subs.get(e)
            if not sub or e in mortes:
                continue
            idioma = sub.get("idioma", "ca")
            dades = notificacio(a[idioma], url(URL.get(a["tipus"], "./"), idioma), clau)
            r = prova(e, lambda: envia(sub, dades, ttl, a["tipus"] in ("riera", "perill", "pluja")))
            if r is not True:
                queden.append(e)
                motius.append(r)
        p["subs"] = queden
        if queden:
            B.registra(f"push: aviso {clau}: {len(queden)} sin entregar: {'; '.join(sorted(set(motius)))[:300]}")
        else:
            del pendents[clau]
    limit = moment - dt.timedelta(days=3)
    for k in [k for k, v in enviats.items() if dt.datetime.fromisoformat(v) < limit]:
        del enviats[k]
    # La previsión del día, a la hora elegida, una vez: se apunta cuando entra.
    hora, avui = str(moment.hour), moment.date().isoformat()
    resums = estat.setdefault("resums", {})
    dades_web = None
    for e, sub in subs.items():
        if sub.get("resum") == hora and resums.get(e) != avui and e not in mortes:
            dades_web = dades_web or B.llegeix(os.path.join(B.DADES, "montflorit.json"), {})
            idioma = sub.get("idioma", "ca")
            n = notificacio(B.resum(dades_web, idioma, moment), url("./", idioma), "resum")
            r = prova(e, lambda: envia(sub, n, TTL_RESUM_S))
            if r is True:
                resums[e] = avui
            else:
                B.registra(f"push: una previsión de las {hora} h no ha entrado: {r[:200]}")
    # La prueba que pide la página: una notificación en el minuto siguiente.
    fetes = []
    for e, sub in subs.items():
        demanada = sub.get("prova")
        if not demanada or e in mortes:
            continue
        if (moment - dt.datetime.fromisoformat(demanada)).total_seconds() <= PROVA_MIN * 60:
            idioma = sub.get("idioma", "ca")
            titol, cos = PROVA[idioma]
            r = prova(e, lambda: envia(sub, {"title": titol, "body": cos, "url": url("avisos.html", idioma),
                                             "tag": "prova"},
                                       TTL_PROVA_S, True))
            if r is not True:
                B.registra(f"push: la prueba no ha entrado: {r[:200]}")
        fetes.append(e)
    # Lo que cambia en las suscripciones: las muertas fuera y las pruebas
    # hechas (o caducadas), sin pisar lo que la página haya cambiado mientras.
    with subscripcions() as s:
        for e in mortes:
            s.pop(e, None)
        for e in fetes:
            if e in s and s[e].get("prova") == subs[e].get("prova"):
                s[e].pop("prova", None)
    for e in mortes:
        resums.pop(e, None)
        for p in pendents.values():
            if e in p["subs"]:
                p["subs"].remove(e)
    return mortes


def altes(estat):
    """A Juanjo, cada alta nueva con el total, como en el bot (sin nada de quién)."""
    with subscripcions() as s:
        n = len(s)
        nous = [e for e in s if e not in set(estat.get("coneguts", []))]
        estat["coneguts"] = list(s)
    if nous and estat.get("coneguts_inici"):
        B.avisa_juanjo(f"Temps a Montflorit: {'alta nova' if len(nous) == 1 else f'{len(nous)} altes noves'} "
                       f"als avisos de la web (ja en són {n}).")
    estat["coneguts_inici"] = True


def volta():
    os.makedirs(B.BASE, exist_ok=True)
    cadenat = open(os.path.join(B.BASE, "push-volta.lock"), "w")
    try:
        fcntl.flock(cadenat, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return
    estat = B.llegeix(ESTAT, {})
    try:
        reparteix(estat, B.ara())
        altes(estat)
    finally:
        B.desa(ESTAT, estat)


def mostra_estat():
    subs = B.llegeix(SUBS, {})
    estat = B.llegeix(ESTAT, {})
    print(f"Subscripcions: {len(subs)}")
    for x in B.TIPUS:
        print(f"  {x}: {sum(x in s.get('avisos', []) for s in subs.values())}")
    print(f"  resum: {sum(bool(s.get('resum')) for s in subs.values())}")
    print(f"  ca: {sum(s.get('idioma') == 'ca' for s in subs.values())}, "
          f"es: {sum(s.get('idioma') == 'es' for s in subs.values())}")
    pendents = estat.get("pendents") or {}
    if pendents:
        print(f"Pendents d'entregar: {', '.join(pendents)}")


if __name__ == "__main__":
    orden = sys.argv[1] if sys.argv[1:] else ""
    if orden == "estat":
        mostra_estat()
    elif orden == "claus":
        print(claus()["publica"])
    else:
        volta()
