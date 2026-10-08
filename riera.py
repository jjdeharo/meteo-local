#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Riesgo de desbordamiento de la riera de Sant Cugat en Montflorit (ADR 0027).

La riera nace en Collserola, cruza Sant Cugat y pasa por Montflorit. Su
cuenca es pequeña (unos 50 km²) y responde enseguida: las tres veces
conocidas se desbordó justo al acabar las 3 horas más lluviosas, con 53 mm en
esas 3 horas en la estación de Meteocat de Sant Cugat (29-04-2024) y con 67
(29-09-2026 y 04-10-2026). Por eso se mira:

- **Lo medido**: la lluvia semihoraria de Sant Cugat en la página de meteo.cat
  (va unos 30 minutos por detrás). La del Observatori Fabra, en la cresta de
  Collserola, junto a Les Planes, donde nace la riera, y la de Montflorit, en
  la parte baja, se guardan y se dicen en el aviso, pero no deciden.
- **Lo que viene**: la lluvia que el radar ve y lleva hacia delante sobre el
  centro de la cuenca (nowcast.py, ADR 0019), que cubre también la media hora
  que la estación va por detrás.
- **El índice**: la lluvia de 3 horas más alta que se alcanzará en la hora
  siguiente, juntando las dos: lo medido en las últimas 3 horas, en las
  últimas 2,5 más la media hora prevista o en las últimas 2 más la hora
  prevista. Lo mismo con 6 horas.

Con RIERA_ATENCIO_MM en 3 horas hay aviso (a los suscriptores, al canal y en
las notificaciones, avisos_bot.py; hasta el 08-10-2026, también a Juanjo
aparte), y con RIERA_PERILL_MM en
3 horas y RIERA_PERILL_6H_MM en 6, otra vez: el 13-09-2025 cayeron 52 mm en
3 horas sobre suelo seco, sin más lluvia antes, y no se desbordó. Una sola vez
cada nivel por episodio. Un episodio empieza con RIERA_REGISTRE_MM
y acaba tras RIERA_FI_H horas por debajo; al acabar se apunta en el registro
(riera.csv) con sus máximos, para ajustar los umbrales con lo que pase.

Uso:
  python3 riera.py ara                  el índice ahora (con red)
  python3 riera.py avisa CASA.json      mira los datos y apunta el episodio
  python3 riera.py estat                el episodio en curso
  python3 riera.py resum                los episodios apuntados
"""
import csv
import datetime as dt
import json
import math
import os
import sys

import config as C
import nowcast as N

DIR = os.environ.get("REGISTRE_DIR", "/estat/registre")
ESTADO = os.path.join(os.path.dirname(DIR), "riera.json")
REGISTRO = os.path.join(DIR, "riera.csv")
CAMPOS = ["inici", "fi", "hora_max", "index_max", "mm_3h_max", "mm_6h_max", "capcalera_3h_max",
          "montflorit_3h_max", "avis_atencio", "avis_perill", "desbordament"]
MITJA_HORA = dt.timedelta(minutes=30)
# Con la estación más atrasada que esto, lo medido ya no sirve para avisar.
RETARD_MAX = dt.timedelta(hours=2)


def files(codi, ahora, hores, lector):
    """Lluvia semihoraria de la estación que cubre las últimas hores: la de
    hoy y, si hace falta, la de ayer (días UTC)."""
    import prevision as P
    hoy = ahora.astimezone(dt.timezone.utc).date()
    dies = [hoy]
    if (ahora - dt.timedelta(hours=hores + 1)).astimezone(dt.timezone.utc).date() < hoy:
        dies.insert(0, hoy - dt.timedelta(days=1))
    res = []
    for dia in dies:
        res += P.taula_meteocat(codi, dia, lector)
    return res


def acumulat(filas, fins, hores):
    """mm de las medias horas que caen enteras entre fins - hores y fins."""
    desde = fins - dt.timedelta(hours=hores)
    return round(sum(mm for t, mm in filas if t >= desde and t + MITJA_HORA <= fins), 1)


# Medias horas que pueden faltar en una ventana sin que el cálculo se dé por
# incompleto: una en 3 horas (5 de 6) y dos en 6 (10 de 12). Una media hora
# ausente cuenta como cero y rebaja el índice: con más huecos no se puede
# decir que el riesgo haya bajado (auditoría del 07-10-2026, ADR 0038).
FORATS_MAX = {3: 1, 6: 2}


def cobertura(filas, fins, hores):
    """Medias horas presentes entre fins - hores y fins, de las hores * 2 que
    debería haber."""
    desde = fins - dt.timedelta(hours=hores)
    return sum(1 for t, _ in filas if t >= desde and t + MITJA_HORA <= fins)


def incomplet(filas, fins):
    """True si a alguna de las dos ventanas (3 y 6 horas) le faltan más
    medias horas de las admitidas."""
    return any(hores * 2 - cobertura(filas, fins, hores) > forats for hores, forats in FORATS_MAX.items())


def previst(nc, desde, minuts):
    """mm que el radar da sobre la cuenca entre desde (el final de lo medido)
    y desde + minuts. La imagen del radar suele ser más nueva que la última
    media hora de la estación: el hueco entre las dos se cuenta con la lluvia
    que ve la imagen."""
    passos = ((nc or {}).get("llocs") or {}).get("conca")
    if not minuts or not passos:
        return 0.0
    fin = desde + dt.timedelta(minutes=minuts)
    t0 = dt.datetime.fromisoformat(nc["hora"])
    mm = 0.0
    if t0 > desde:
        mm += passos[0]["mm_h"] * (min(t0, fin) - desde).total_seconds() / 3600
    tram = N.en_tram(nc, "conca", max(desde, t0), fin) if fin > t0 else None
    return round(mm + (tram["mm"] if tram else 0.0), 1)


def nivell(index, index_6h):
    """Peligro con la lluvia de 3 y de 6 horas; atención y registro, con la
    de 3."""
    if index >= C.RIERA_PERILL_MM and index_6h >= C.RIERA_PERILL_6H_MM:
        return "perill"
    for nom, llindar in (("atencio", C.RIERA_ATENCIO_MM), ("registre", C.RIERA_REGISTRE_MM)):
        if index >= llindar:
            return nom
    return None


def horitzo(fins, ahora):
    """Minutos desde el final de lo medido hasta una hora después de ahora,
    en medias horas enteras hacia arriba. La estación llega con retraso (unos
    30 minutos; se admiten hasta 2 horas): la «hora siguiente» se cuenta
    desde ahora, no desde la última medida (auditoría del 08-10-2026)."""
    return int(math.ceil(((ahora - fins).total_seconds() / 60 + 60) / 30) * 30)


def maxim_amb_radar(filas, fins, hores, nc, ahora):
    """La lluvia de hores horas más alta que se alcanzará de aquí a una hora,
    y dentro de cuántos minutos (desde ahora)."""
    opcions = []
    for minuts in range(0, horitzo(fins, ahora) + 1, 30):
        mm = acumulat(filas, fins, max(hores - minuts / 60, 0)) + previst(nc, fins, minuts)
        opcions.append((round(mm, 1), max(0, int(minuts - (ahora - fins).total_seconds() / 60))))
    return max(opcions)


def calcula(ahora, nc, lector=None, montflorit_3h=None):
    """Estado de la riera ahora, para casa.json. None si Sant Cugat no da
    datos recientes. La lluvia de 3 horas de Montflorit (minuto a minuto, en
    la parte baja de la cuenca) se guarda y se dice, pero no decide: aún no
    hay historial para saber qué umbral le corresponde."""
    filas = files(C.RIERA_ESTACIO, ahora, 6, lector)
    if not filas:
        return None
    fins = filas[-1][0] + MITJA_HORA
    if ahora - fins > RETARD_MAX:
        return None
    h = C.RIERA_HORES
    res = {"estacio": C.ESTACIONES.get(C.RIERA_ESTACIO, C.RIERA_ESTACIO),
           "fins": fins.astimezone().isoformat(timespec="minutes"),
           "mm_3h": acumulat(filas, fins, h), "mm_6h": acumulat(filas, fins, 6),
           "mm_1h": acumulat(filas, fins, 1),     # per al registre de l'aprenentatge (ADR 0042)
           "incomplet": incomplet(filas, fins),
           "radar_1h": previst(nc, fins, (ahora - fins).total_seconds() / 60 + 60) if nc else None,
           "capcalera": None, "montflorit_3h": montflorit_3h}
    res["index"], res["index_d_aqui_a_min"] = maxim_amb_radar(filas, fins, h, nc, ahora)
    res["index_6h"] = maxim_amb_radar(filas, fins, 6, nc, ahora)[0]
    res["nivell"] = nivell(res["index"], res["index_6h"])
    try:
        codi, nom = C.RIERA_CAPCALERA
        cap = files(codi, ahora, 6, lector)
        if cap:
            fc = cap[-1][0] + MITJA_HORA
            res["capcalera"] = {"estacio": nom, "fins": fc.astimezone().isoformat(timespec="minutes"),
                                "mm_3h": acumulat(cap, fc, h), "mm_6h": acumulat(cap, fc, 6)}
    except Exception:
        pass
    return res


def coma(x):
    return f"{x:.0f}" if x >= 10 else f"{x:.1f}".replace(".", ",")


def missatge(riera, nom):
    hora = dt.datetime.fromisoformat(riera["fins"]).strftime("%H:%M")
    if nom == "perill":
        cap = ("Riera de Sant Cugat, perill de desbordament a Montflorit: a Sant Cugat han caigut "
               f"{coma(riera['mm_3h'])} mm en 3 hores i {coma(riera['mm_6h'])} en 6 (fins a les {hora})")
    else:
        cap = ("Riera de Sant Cugat, atenció: a Sant Cugat han caigut "
               f"{coma(riera['mm_3h'])} mm en 3 hores (fins a les {hora})")
    radar = riera.get("radar_1h")
    if radar and radar >= 1:
        cap += f" i el radar en preveu uns {coma(radar)} més a la conca des de llavors fins d'aquí a una hora"
    cap += "."
    altres = []
    if riera.get("capcalera"):
        altres.append(f"al Fabra (Collserola), {coma(riera['capcalera']['mm_3h'])} mm")
    if riera.get("montflorit_3h") is not None:
        altres.append(f"a Montflorit, {coma(riera['montflorit_3h'])} mm")
    if altres:
        cap += " En 3 hores, " + " i ".join(altres) + "."
    if nom == "perill":
        cap += (" Els desbordaments del 2024 i el 2026 van arribar amb 53 a 67 mm en 3 hores i més de 65 "
                "en 6, en acabar la pluja més forta.")
    else:
        cap += (f" S'ha desbordat amb {C.RIERA_PERILL_MM} mm o més en 3 hores i "
                f"{C.RIERA_PERILL_6H_MM} en 6.")
    if riera.get("incomplet"):
        cap += " A l'estació li falten mesures: la pluja real pot ser més alta."
    return cap


def missatge_fi(riera, ep):
    """El final d'un episodi amb avís: 3 hores sense pluja forta a Sant Cugat
    ni al radar."""
    que = "ha passat el perill de desbordament" if ep["avisos"].get("perill") else "ja no hi ha risc de desbordament"
    return (f"Riera de Sant Cugat: {que}. A Sant Cugat fa {C.RIERA_FI_H} hores que no plou amb força "
            f"({coma(riera['mm_3h'])} mm en les últimes 3 hores) i el radar no hi veu pluja forta. "
            "Si torna a ploure fort, tornarà l'avís.")


def fila_registro(ep):
    fila = dict.fromkeys(CAMPOS, "")
    fila.update({k: ep.get(k, "") for k in ("inici", "hora_max", "index_max", "mm_3h_max",
                                             "mm_6h_max", "capcalera_3h_max", "montflorit_3h_max")})
    fila["fi"] = ep["vist"]
    fila["avis_atencio"] = ep["avisos"].get("atencio") or ""
    fila["avis_perill"] = ep["avisos"].get("perill") or ""
    return fila


def compara(estat, riera, ahora):
    """Pone al día el episodio y devuelve (mensaje o None, fila del registro
    del episodio que acaba o None)."""
    ep = estat.get("episodi")
    if not riera:
        return None, None
    ara = ahora.isoformat(timespec="minutes")
    senyal = riera["index"] >= C.RIERA_REGISTRE_MM
    text = fila = None
    # Con huecos en la estación, lo medido puede quedarse corto: el episodio
    # no se cierra hasta tener las medias horas que faltan.
    if ep and not senyal and not riera.get("incomplet") \
            and ahora - dt.datetime.fromisoformat(ep["vist"]) >= dt.timedelta(hours=C.RIERA_FI_H):
        # Si es va avisar, es diu que ha passat (Juanjo, 08-10-2026): un sol
        # missatge per episodi, i només després de 3 hores de calma, perquè
        # no es converteixi en una successió d'avís i contraavís.
        if ep["avisos"]:
            text = missatge_fi(riera, ep)
        fila, ep = fila_registro(ep), None
    if senyal:
        if not ep:
            ep = {"inici": ara, "avisos": {}, "index_max": 0, "mm_3h_max": 0, "mm_6h_max": 0,
                  "capcalera_3h_max": 0, "montflorit_3h_max": 0, "hora_max": ara}
        ep["vist"] = ara
        if riera["index"] > ep["index_max"]:
            ep["index_max"], ep["hora_max"] = riera["index"], ara
        ep["mm_3h_max"] = max(ep["mm_3h_max"], riera["mm_3h"])
        ep["mm_6h_max"] = max(ep["mm_6h_max"], riera["mm_6h"])
        if riera.get("capcalera"):
            ep["capcalera_3h_max"] = max(ep["capcalera_3h_max"], riera["capcalera"]["mm_3h"])
        if riera.get("montflorit_3h") is not None:
            ep["montflorit_3h_max"] = max(ep.get("montflorit_3h_max", 0), riera["montflorit_3h"])
        nom = nivell(riera["index"], riera.get("index_6h", riera["mm_6h"]))
        if nom in ("perill", "atencio") and not ep["avisos"].get(nom):
            text = missatge(riera, nom)
            ep["avisos"][nom] = ara
            ep["avisos"].setdefault("atencio", ara)
    estat["episodi"] = ep
    return text, fila


# --- En el NAS -----------------------------------------------------------------

def llegeix_estat():
    try:
        with open(ESTADO, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {"episodi": None}


def desa_estat(estat):
    with open(ESTADO + ".tmp", "w", encoding="utf-8") as f:
        json.dump(estat, f, ensure_ascii=False, indent=1)
    os.replace(ESTADO + ".tmp", ESTADO)


def apunta(fila):
    nou = not os.path.exists(REGISTRO)
    os.makedirs(DIR, exist_ok=True)
    with open(REGISTRO, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if nou:
            w.writeheader()
        w.writerow(fila)


def avisa(ruta, ahora=None):
    ahora = ahora or dt.datetime.now().astimezone()
    with open(ruta, encoding="utf-8") as f:
        salida = json.load(f)
    # Con datos viejos (la pasada ha fallado), no se avisa.
    if ahora - dt.datetime.fromisoformat(salida["generat"]) > dt.timedelta(minutes=C.INTERVALO_CASA_MIN):
        return None
    estat = llegeix_estat()
    text, fila = compara(estat, salida.get("riera"), ahora)
    desa_estat(estat)
    if fila:
        apunta(fila)
    if text:
        print(text)         # al registro del NAS; ya no se manda a Juanjo (ADR 0027)
    return text


def resum():
    if not os.path.exists(REGISTRO):
        return "Encara no hi ha cap episodi apuntat."
    with open(REGISTRO, encoding="utf-8") as f:
        files_ = list(csv.DictReader(f))
    return "\n".join(f"{f['inici']} · índex {f['index_max']} mm · 3 h {f['mm_3h_max']} · 6 h {f['mm_6h_max']}"
                     f" · Fabra {f['capcalera_3h_max']} · Montflorit {f.get('montflorit_3h_max', '')} · atenció {f['avis_atencio'] or '-'}"
                     f" · perill {f['avis_perill'] or '-'} · desbordament {f['desbordament'] or '?'}"
                     for f in files_)


if __name__ == "__main__":
    ordre = sys.argv[1] if len(sys.argv) > 1 else ""
    if ordre == "ara":
        import prevision as P
        try:
            nc = P.radar()["nowcast"]
        except Exception as ex:
            print("Sense radar:", ex, file=sys.stderr)
            nc = None
        print(json.dumps(calcula(P.AHORA, nc), ensure_ascii=False, indent=1))
    elif ordre == "avisa" and len(sys.argv) > 2:
        avisa(sys.argv[2])
    elif ordre == "estat":
        print(json.dumps(llegeix_estat(), ensure_ascii=False, indent=1))
    elif ordre == "resum":
        print(resum())
    else:
        print(__doc__)
        sys.exit(1)
