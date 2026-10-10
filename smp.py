#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Los avisos de peligro de Meteocat (SMP) para el Vallès Occidental (ADR 0067).

Los planes de Protección Civil se activan para Cataluña o para unas comarcas,
según cada comunicado, y los datos abiertos no dicen cuáles (ADR 0066). Junto
a un plan activo se dice si Meteocat tiene un aviso de peligro para la
comarca del barrio, que es lo que le importa al vecino (Juanjo, 10-10-2026).

La API de Meteocat prohíbe difundir sus datos a terceros; las páginas
públicas de meteo.cat llevan los mismos avisos dentro, en la llamada
«Meteocat.avisosSMP({… avisos: [...] …})», y su aviso legal permite
reutilizar lo que publica en abierto sin alterarlo, citando la fuente y la
fecha (Llei 37/2007, la misma base que el radar, ADR 0019). Se lee solo
mientras se muestra un plan.

Los avisos son episodios con la estructura de /smp/episodis-oberts de la API:
cada episodio, un meteoro; cada aviso, sus evoluciones por día, con las
franjas («00-06», «06-12», «12-18», «18-00») y las comarcas afectadas
(idComarca) y su grado de peligro. Como el mapa de meteo.cat, cuentan los
avisos vigentes que no son preavisos, y el grado de 1 a 6: 1-2 moderado,
3-4 alto, 5-6 muy alto (script.min.js de meteo.cat, _crearAvisosCombinatsLayer).
"""
import datetime as dt
import json
import re

import config as C

URL = "https://www.meteo.cat/prediccio/general"
DIES = {"ca": ("dilluns", "dimarts", "dimecres", "dijous", "divendres", "dissabte", "diumenge"),
        "es": ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")}
GRAU = {"ca": {"mig": "moderat", "alt": "alt", "maxim": "molt alt"},
        "es": {"mig": "moderado", "alt": "alto", "maxim": "muy alto"}}


def nivell(perill):
    """El grado de Meteocat (1-6) en la escala de la página."""
    return "mig" if perill <= 2 else "alt" if perill <= 4 else "maxim"


def episodis(pagina):
    """La lista «avisos» de la llamada Meteocat.avisosSMP de una página de meteo.cat."""
    i = pagina.find("Meteocat.avisosSMP(")
    if i < 0:
        raise ValueError("la pàgina de Meteocat no porta els avisos")
    m = re.compile(r"\n\s*avisos:\s*(\[)").search(pagina, i)
    if not m:
        raise ValueError("la pàgina de Meteocat no porta la llista d'avisos")
    llista, _ = json.JSONDecoder().raw_decode(pagina, m.start(1))
    return llista


def franja(nom):
    """«18-00» → (18, 24)."""
    a, b = (int(x) for x in nom.split("-"))
    return a, (24 if b == 0 else b)


def de_la_comarca(llista, comarca=None):
    """Los avisos que afectan a la comarca: [{meteor, llindar, perill, emissio,
    dies: {AAAA-MM-DD: [(inici, fi), …]}}], uno por aviso."""
    comarca = comarca or C.SMP_COMARCA
    res = []
    for ep in llista or []:
        meteor = ((ep.get("meteor") or {}).get("nom") or "").strip()
        for av in ep.get("avisos") or []:
            if (av.get("estat") or "").lower() != "vigent" or (av.get("tipus") or "").lower().startswith("preav"):
                continue
            dies, perill, llindar = {}, 0, None
            for ev in av.get("evolucions") or []:
                for per in ev.get("periodes") or []:
                    for af in per.get("afectacions") or []:
                        if af.get("idComarca") != comarca:
                            continue
                        dia = (af.get("dia") or ev.get("dia") or "")[:10]
                        dies.setdefault(dia, set()).add(franja(per["nom"]))
                        perill = max(perill, af.get("perill") or 0)
                        llindar = llindar or af.get("llindar") or ev.get("llindar1")
            if dies and perill:
                res.append({"meteor": meteor, "llindar": llindar, "perill": perill, "emissio": av.get("dataEmisio"),
                            "dies": {d: junta(sorted(f)) for d, f in sorted(dies.items())}})
    return res


def junta(franges):
    """Las franjas seguidas, juntas: [(12, 18), (18, 24)] → [(12, 24)]."""
    res = []
    for a, b in franges:
        if res and res[-1][1] == a:
            res[-1] = (res[-1][0], b)
        else:
            res.append((a, b))
    return res


def hora_local(iso):
    """«2026-10-10T08:09Z» → «10:09» (hora de Montflorit)."""
    if not iso:
        return None
    t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return t.astimezone().strftime("%H:%M")


def quan(dies, idioma):
    """«dissabte 10 de 12 a 24 h i diumenge 11 de 0 a 6 h»."""
    de, i = ("de", "y") if idioma == "es" else ("de", "i")
    peces = []
    for dia, franges in dies.items():
        d = dt.date.fromisoformat(dia)
        hores = f" {i} ".join(f"{de} {a} a {b} h" for a, b in franges)
        peces.append(f"{DIES[idioma][d.weekday()]} {d.day} {hores}")
    return f" {i} ".join(peces)


def textos(avisos, hora):
    """Una línea por aviso, en catalán y castellano, con el meteoro y el umbral
    tal como los publica Meteocat (sin traducir: ADR 0067); sin avisos, que no
    hay ninguno, con la hora de la lectura."""
    nom = C.SMP_COMARCA_NOM
    if not avisos:
        return [{"nivell": "nul",
                 "ca": f"Meteocat no té cap avís de perill per al {nom} (dades de les {hora}).",
                 "es": f"Meteocat no tiene ningún aviso de peligro para el {nom} (datos de las {hora})."}]
    res = []
    for a in avisos:
        n = nivell(a["perill"])
        llindar = f"{a['llindar']}; " if a.get("llindar") else ""
        emes = hora_local(a.get("emissio"))
        res.append({"nivell": n,
                    "ca": (f"Meteocat: avís de perill {GRAU['ca'][n]} per «{a['meteor']}» al {nom}, "
                           f"{quan(a['dies'], 'ca')} ({llindar}emès a les {emes})."),
                    "es": (f"Meteocat: aviso de peligro {GRAU['es'][n]} por «{a['meteor']}» en el {nom}, "
                           f"{quan(a['dies'], 'es')} ({llindar}emitido a las {emes}).")})
    return res


def llegeix(get, ahora):
    """Lo que se publica: {hora, avisos (los de la comarca), linies (los textos)}."""
    avisos = de_la_comarca(episodis(get(URL)))
    hora = ahora.strftime("%H:%M")
    return {"hora": ahora.isoformat(timespec="minutes"), "avisos": avisos, "linies": textos(avisos, hora)}


def comprova(get, marca, avisa=True):
    """La prueba diaria (aprenentatge.diari): como la página no es una API, si
    deja de traer los avisos se le dice una vez a Juanjo, y otra cuando vuelve.
    Mientras falla, junto a los planes no sale nada (casa.py)."""
    import os
    import subprocess
    try:
        episodis(get(URL))
        error = None
    except Exception as ex:
        error = str(ex)
    text = None
    if error and not os.path.exists(marca):
        open(marca, "w").close()
        text = (f"Temps a Montflorit: la pàgina de Meteocat ja no porta els avisos de perill ({error}). "
                "Al costat dels plans de Protecció Civil no se'n diu res fins que es torni a llegir: mira smp.py.")
    elif not error and os.path.exists(marca):
        os.remove(marca)
        text = "Temps a Montflorit: els avisos de perill de Meteocat es tornen a llegir."
    if text:
        print(text)
        if avisa:
            subprocess.run(["avisar-juanjo", "--asunto", "meteo-local", text], check=False)
    return error
