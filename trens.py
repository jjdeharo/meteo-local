#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Si circulen els trens de prop de Montflorit (ADR 0029).

Les línies que paren al terme de Cerdanyola: R4, R7 i R8 de Rodalies i S2
d'FGC (Bellaterra i Universitat Autònoma). Per a cada una:

- **Avisos**: els de Renfe (GTFS-RT en JSON, `gtfsrt.renfe.com`) i els de FGC
  (GTFS-RT en protobuf, al portal de dades obertes). Un avís «propi» només
  parla d'aquella línia; un de «general», de moltes.
- **Trens que es mouen** a TRENS_RADI_KM o menys de l'estació de la línia a
  Cerdanyola. Un tren aturat també envia la seva posició (el 07-10-2026, amb
  tot Rodalies parat, dos de l'R7 apareixien «a l'estació»): per això es
  compara amb la posició de la passada anterior, si és prou recent; sense,
  compten els que no estan aturats. I només els de prop de l'estació: aquell
  dia l'R4 circulava pel tram sud, que no serveix a qui surt de Cerdanyola.
  Amb trens cada 15 o 30 minuts, en una passada pot no haver-n'hi cap a prop:
  la línia circula si se n'ha vist un en els últims TRENS_VIST_MIN minuts.

L'estat: «bus» si l'avís propi més recent que parla del servei diu que va per
carretera (el 07-10-2026 l'R8 tenia alhora un avís vell de «servei per
carretera» i un de nou de «circulació ferroviària»: mana el nou, auditoria
del 07-10-2026); «incidencies» si circula i hi ha algun avís; «circula» si
circula sense avisos; «sense_trens» si dins de l'horari no se n'ha vist cap, i
«fora_horari» abans del primer tren de la línia a Cerdanyola (i mitja hora
més) o després de l'últim (config.TRENS_HORARI_LINIA). Els avisos es mostren
del més nou al més vell.
Els textos dels avisos no es tradueixen mai: es mostren en l'idioma en què
els publica l'operador. Si n'hi ha en català i en castellà, cada versió de la
pàgina mostra el seu (Renfe els marca tots dos com a castellà: es distingeixen
pel contingut); si només n'hi ha un, totes dues mostren aquell.
Llegeix la xarxa a cada passada de la pàgina de casa, sense IA.

Ús:
  python3 trens.py          l'estat ara (amb xarxa)
"""
import datetime as dt
import json
import math
import os
import re
import urllib.request

import config as C

RENFE = "https://gtfsrt.renfe.com/"
FGC = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/"
UA = {"User-Agent": "meteo-local/" + C.VERSION}
ESTAT = os.path.join(os.environ.get("TRENS_DIR", "/estat"), "trens-posicions.json")
# Moure's més que això entre dues passades és circular (el GPS balla uns metres).
MOGUT_M = 300
POSICIONS_MAX_MIN = 40      # posicions més velles: no es comparen


def get(url, binari=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        dades = r.read()
    return dades if binari else json.loads(dades)


# --- Protobuf mínim ------------------------------------------------------------
# Prou per llegir els avisos GTFS-RT sense dependències: el contenidor del NAS
# no té la biblioteca de protobuf.

def _varint(b, i):
    n = desp = 0
    while True:
        c = b[i]
        i += 1
        n |= (c & 0x7F) << desp
        if c < 0x80:
            return n, i
        desp += 7


def camps(b):
    """Els camps d'un missatge: llista de (número, valor). Els de longitud
    variable surten com a bytes; els enters, com a int."""
    res, i = [], 0
    while i < len(b):
        clau, i = _varint(b, i)
        num, tipus = clau >> 3, clau & 7
        if tipus == 0:
            v, i = _varint(b, i)
        elif tipus == 2:
            n, i = _varint(b, i)
            v, i = b[i:i + n], i + n
        elif tipus == 1:
            v, i = b[i:i + 8], i + 8
        elif tipus == 5:
            v, i = b[i:i + 4], i + 4
        else:
            raise ValueError(f"tipus de camp desconegut: {tipus}")
        res.append((num, v))
    return res


def _text(traduit):
    """TranslatedString: {idioma: text}."""
    res = {}
    for num, t in camps(traduit):
        if num == 1:
            c = dict(camps(t))
            res[c.get(2, b"").decode()] = c.get(1, b"").decode()
    return res


def iso(segons):
    """Segons des de 1970 (GTFS-RT) → ISO local amb minuts, o None."""
    try:
        return dt.datetime.fromtimestamp(int(segons), dt.timezone.utc).astimezone().isoformat(timespec="minutes")
    except (TypeError, ValueError, OverflowError):
        return None


def avisos_pb(b):
    """Els avisos d'un FeedMessage GTFS-RT: [{rutes, text, inici}]. inici és
    el començament del primer període actiu de l'avís (ISO), o None."""
    res = []
    for num, entitat in camps(b):
        if num != 2:
            continue
        for n2, alerta in camps(entitat):
            if n2 != 5:
                continue
            rutes, textos, inicis = [], {}, []
            for n3, v in camps(alerta):
                if n3 == 1:
                    inicis += [t for n4, t in camps(v) if n4 == 1]
                elif n3 == 5:
                    rutes += [r.decode() for n4, r in camps(v) if n4 == 2]
                elif n3 in (10, 11):
                    for idioma, t in _text(v).items():
                        textos.setdefault(idioma, "")
                        textos[idioma] = (textos[idioma] + " " + t).strip()
            res.append({"rutes": rutes, "text": textos, "inici": iso(min(inicis)) if inicis else None})
    return res


# --- Rodalies i FGC -------------------------------------------------------------

def linia_renfe(ruta):
    """«51T0037R7» → «R7» (les rutes de Rodalies comencen per 51)."""
    m = re.match(r"51T\d+((?:R|RG|RL|RT)\d+[NS]?)$", ruta or "")
    return m and m.group(1)


CATALA = re.compile(r"\b(servei|per causes|no es pot|recorregut|usuaris|demanem|els|amb|estació|línia)\b", re.I)
CASTELLA = re.compile(r"\b(servicio|por causas|no se puede|recorrido|usuarios|pedimos|los|con|estación|línea)\b", re.I)


def idiomes(textos):
    """{"ca": …, "es": …} a partir de textos amb idioma o sense: cada text va
    a l'idioma que diu el seu contingut."""
    res = {}
    for t in textos:
        t = " ".join(t.split())
        if t:
            idioma = "ca" if len(CATALA.findall(t)) > len(CASTELLA.findall(t)) else "es"
            res.setdefault(idioma, t)
    if res:
        res.setdefault("ca", res.get("es"))
        res.setdefault("es", res.get("ca"))
    return res


def avisos_renfe(dades=None):
    """[{linies, text, inici}] dels avisos de Renfe (alerts.json, o dades ja
    llegides)."""
    res = []
    for e in (dades or get(RENFE + "alerts.json")).get("entity", []):
        a = e.get("alert", {})
        linies = {linia_renfe(i.get("routeId")) for i in a.get("informedEntity", [])} - {None}
        textos = idiomes(t.get("text", "") for t in a.get("descriptionText", {}).get("translation", []))
        inicis = [p.get("start") for p in a.get("activePeriod") or [] if p.get("start")]
        if linies and textos:
            res.append({"linies": linies, "text": textos, "inici": iso(min(inicis, key=int)) if inicis else None})
    return res


def trens_renfe():
    res = []
    for e in get(RENFE + "vehicle_positions.json").get("entity", []):
        v = e.get("vehicle", {})
        linia = (v.get("vehicle", {}).get("label") or "").split("-")[0]
        p = v.get("position") or {}
        if linia and "latitude" in p:
            res.append({"id": "renfe-" + str(v.get("vehicle", {}).get("id")), "linia": linia,
                        "lat": p["latitude"], "lon": p["longitude"],
                        "aturat": v.get("currentStatus") == "STOPPED_AT"})
    return res


def avisos_fgc():
    fitxer = get(FGC + "alerts-gtfs_realtime/records?limit=1")["results"][0]["file"]["url"]
    res = []
    for a in avisos_pb(get(fitxer, binari=True)):
        # Els textos, mai traduïts: en català i castellà si n'hi ha; si no, el
        # que hi hagi, tal qual.
        textos = (idiomes(t for idioma, t in a["text"].items() if idioma in ("ca", "es", ""))
                  or idiomes(a["text"].values()))
        if a["rutes"] and textos:
            res.append({"linies": set(a["rutes"]), "text": textos, "inici": a.get("inici")})
    return res


def trens_fgc(linies):
    q = "lin in (" + ",".join(f"'{x}'" for x in linies) + ")"
    url = FGC + "posicionament-dels-trens/records?limit=100&where=" + urllib.request.quote(q)
    return [{"id": "fgc-" + r["id"], "linia": r["lin"], "lat": r["geo_point_2d"]["lat"],
             "lon": r["geo_point_2d"]["lon"], "aturat": bool(r.get("estacionat_a"))}
            for r in get(url)["results"] if r.get("geo_point_2d")]


def km(a, b):
    lat = math.radians((a[0] + b[0]) / 2)
    return 111.2 * math.hypot(a[0] - b[0], (a[1] - b[1]) * math.cos(lat))


def es_mouen(trens, abans, ara):
    """Els trens que es mouen a prop de l'estació de la seva línia: comparats
    amb la passada anterior si és recent; si no, els que no estan aturats."""
    estacions = {linia: coord for linia, coord in C.TRENS_ESTACIONS.items()}
    prop = [t for t in trens if t["linia"] in estacions
            and km((t["lat"], t["lon"]), estacions[t["linia"]]) <= C.TRENS_RADI_KM]
    recent = abans and ara - dt.datetime.fromisoformat(abans["hora"]) <= dt.timedelta(minutes=POSICIONS_MAX_MIN)
    res = []
    for t in prop:
        antiga = recent and abans["posicions"].get(t["id"])
        if antiga:
            if km(antiga, (t["lat"], t["lon"])) * 1000 >= MOGUT_M:
                res.append(t)
        elif not t["aturat"]:
            res.append(t)
    return res


# Avisos que diuen com va el servei: per carretera o amb trens. Entre els
# propis d'una línia, mana el més recent d'aquests.
SERVEI = re.compile(r"carretera|circulaci[oó]n? ferrovi", re.I)


def mes_nous_primer(avisos):
    """Del més recent al més vell; sense data, els últims."""
    return sorted(avisos, key=lambda a: a.get("inici") or "", reverse=True)


def dins_horari(linia, ara):
    """Si a aquesta hora la línia hauria de circular per Cerdanyola: des de
    TRENS_MARGE_INICI_MIN minuts després del seu primer tren fins a l'últim
    (config.TRENS_HORARI_LINIA). Abans o després, no veure'n cap és normal."""
    ini, fi = getattr(C, "TRENS_HORARI_LINIA", {}).get(linia, C.TRENS_HORARI)
    h, m = map(int, ini.split(":"))
    inici = f"{(h * 60 + m + C.TRENS_MARGE_INICI_MIN) // 60:02d}:{(h * 60 + m + C.TRENS_MARGE_INICI_MIN) % 60:02d}"
    return inici <= ara.strftime("%H:%M") < fi


def estat_linia(linia, mouen, vist, avisos, ara):
    """vist: última vegada que s'ha vist un tren de la línia movent-se a prop
    de l'estació (ISO), o None."""
    nomes = mes_nous_primer([a for a in avisos if a["linies"] == {linia}])
    propis = [a["text"] for a in nomes]
    generals = [a["text"] for a in mes_nous_primer([a for a in avisos if linia in a["linies"] and len(a["linies"]) > 1])]
    n = sum(t["linia"] == linia for t in mouen)
    circula = n > 0 or bool(vist and ara - dt.datetime.fromisoformat(vist)
                            <= dt.timedelta(minutes=C.TRENS_VIST_MIN))
    de_dia = dins_horari(linia, ara)
    # Si l'avís més nou que parla del servei té data, decideix ell; sense
    # dates, qualsevol avís propi de carretera (com fins ara).
    carretera = lambda a: bool(re.search(r"carretera", a["text"]["ca"] + a["text"]["es"], re.I))
    servei = [a for a in nomes if SERVEI.search(a["text"]["ca"] + a["text"]["es"])]
    bus = (carretera(servei[0]) if servei[0].get("inici") else any(carretera(a) for a in servei)) if servei else False
    if bus:
        estat = "bus"
    elif circula:
        estat = "incidencies" if propis or generals else "circula"
    else:
        estat = "sense_trens" if de_dia else "fora_horari"
    # Primer el que és només d'aquesta línia; sense repetir textos.
    textos = []
    for t in propis + generals:
        if t not in textos:
            textos.append(t)
    return {"estat": estat, "trens": n, "vist": vist if not n else ara.isoformat(timespec="minutes"),
            "avisos": textos[:2]}


def calcula(ara=None):
    """L'estat de cada línia de C.TRENS, per a les dades públiques. Al NAS
    (amb /estat) desa les posicions i quan s'ha vist circular cada línia, per
    a la passada següent."""
    ara = ara or dt.datetime.now().astimezone()
    try:
        with open(ESTAT, encoding="utf-8") as f:
            abans = json.load(f)
    except (OSError, ValueError):
        abans = None
    vistos = dict((abans or {}).get("vist") or {})
    res = {"hora": ara.isoformat(timespec="minutes"), "linies": [], "errors": []}
    trens = []
    for operador, llegeix_avisos, llegeix_trens in (
            ("rodalies", avisos_renfe, trens_renfe),
            ("fgc", avisos_fgc, lambda: trens_fgc([l for l, o, _ in C.TRENS if o == "fgc"]))):
        try:
            avisos, tr = llegeix_avisos(), llegeix_trens()
        except Exception as ex:
            res["errors"].append(f"{operador}: {ex}")
            avisos, tr = None, []
        mouen = es_mouen(tr, abans, ara)
        trens += tr
        for linia, op, estacio in C.TRENS:
            if op != operador:
                continue
            fila = {"linia": linia, "operador": op, "estacio": estacio}
            if avisos is None:
                fila.update({"estat": "sense_dades", "trens": 0, "avisos": []})
            else:
                fila.update(estat_linia(linia, mouen, vistos.get(linia), avisos, ara))
                if fila["vist"]:
                    vistos[linia] = fila["vist"]
            fila.pop("vist", None)
            res["linies"].append(fila)
    posicions = {t["id"]: (round(t["lat"], 5), round(t["lon"], 5)) for t in trens}
    if os.path.isdir(os.path.dirname(ESTAT)) and posicions:
        with open(ESTAT + ".tmp", "w", encoding="utf-8") as f:
            json.dump({"hora": res["hora"], "posicions": posicions, "vist": vistos}, f)
        os.replace(ESTAT + ".tmp", ESTAT)
    return res


if __name__ == "__main__":
    print(json.dumps(calcula(), ensure_ascii=False, indent=1))
