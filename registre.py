#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Registro de aciertos y fallos, para decidir con datos (ADR 0006).

Lo ejecuta el reloj del NAS, sin IA:

  python3 registre.py apunta DADES.json   cada actualización: guarda todo lo
                                          que vio el programa (una línea JSON)
  python3 registre.py verifica [DIA]      a las 16:00: la lluvia que cayó en
                                          la ida y la vuelta, y si acertó
  python3 registre.py resum [--avisa]     resumen; con --avisa lo manda por
                                          Telegram una sola vez, cuando hay
                                          bastantes días

Además, casa.py apunta en cada pasada lo que mide Montflorit hora a hora
(montflorit.csv) y, una vez por hora, lo que daban los modelos para las 24
horas siguientes (casa-AAAA-MM.jsonl), para aprender de los fallos (ADR 0012).

Los datos van a REGISTRE_DIR (en el NAS, /estat/registre), no al repositorio.
"""
import csv
import datetime as dt
import json
import os
import subprocess
import sys

import config as C
import prevision as P

DIR = os.environ.get("REGISTRE_DIR", "/estat/registre")
RESULTADOS = os.path.join(DIR, "resultats.csv")
AVISO_ENVIADO = os.path.join(DIR, "resum-enviat")
CAMPOS = ["dia", "mitja", "decidit", "risc_anada", "risc_tornada", "risc_tornada_final",
          "pluja_anada_mm", "pluja_tornada_mm", "plou_anada", "plou_tornada", "resultat",
          "detall_estacions"]


def apunta(ruta):
    os.makedirs(DIR, exist_ok=True)
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    mes = datos["generat"][:7]
    with open(os.path.join(DIR, f"{mes}.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(datos, ensure_ascii=False) + "\n")


# --- Página de casa: previsiones y lo que pasó -----------------------------------

MONTFLORIT = os.path.join(DIR, "montflorit.csv")
CAMPOS_MONTFLORIT = ["fins", "pluja_mm", "temperatura", "humitat", "lectures"]
CASA_DARRERA = os.path.join(DIR, "casa-darrera")


def hay_registro():
    """El registro vive en el NAS (/estat); en un ordenador no se apunta nada."""
    return os.path.isdir(os.path.dirname(DIR))


def horas_montflorit(filas):
    """Horas completas de los datos minuto a minuto: la lluvia de la hora que
    acaba en «fins» y la temperatura y la humedad de la lectura más cercana a
    la hora en punto (a 5 minutos como mucho; la estación se salta minutos)."""
    if not filas:
        return {}
    por_hora, cerca = {}, {}
    for antes, despues in zip(filas, filas[1:]):
        t = dt.datetime.fromisoformat(despues["dt_local"])
        fin = t.replace(minute=0, second=0) + (dt.timedelta(hours=1) if t.minute or t.second else dt.timedelta())
        salto = despues["PREC"] - antes["PREC"]
        h = por_hora.setdefault(fin, {"pluja_mm": 0.0, "lectures": 0})
        h["pluja_mm"] += despues["PREC"] if salto < 0 else salto
        h["lectures"] += 1
    for f in filas:
        t = dt.datetime.fromisoformat(f["dt_local"])
        marca = (t + dt.timedelta(minutes=30)).replace(minute=0, second=0)
        dist = abs((t - marca).total_seconds())
        if dist <= 300 and f.get("TEMP") is not None and dist < cerca.get(marca, (999, None))[0]:
            cerca[marca] = (dist, f)
    ultima = dt.datetime.fromisoformat(filas[-1]["dt_local"])
    primera = dt.datetime.fromisoformat(filas[0]["dt_local"])
    res = {}
    # Solo las horas enteras: ni la que está en curso ni la primera, cortada.
    for fin, h in por_hora.items():
        if fin <= ultima and fin - dt.timedelta(hours=1) >= primera:
            f = cerca.get(fin, (None, {}))[1]
            res[fin] = {**h, "temperatura": f.get("TEMP"), "humitat": f.get("HUM")}
    return res


def apunta_montflorit(filas):
    nuevas = horas_montflorit(filas)
    if not nuevas:
        return
    os.makedirs(DIR, exist_ok=True)
    guardadas = {}
    if os.path.exists(MONTFLORIT):
        with open(MONTFLORIT, encoding="utf-8") as f:
            guardadas = {r["fins"]: r for r in csv.DictReader(f)}
    for fin, h in nuevas.items():
        guardadas[fin.strftime("%Y-%m-%dT%H:%M")] = {
            "fins": fin.strftime("%Y-%m-%dT%H:%M"), "pluja_mm": round(h["pluja_mm"], 1),
            "temperatura": h.get("temperatura"), "humitat": h.get("humitat"), "lectures": h["lectures"]}
    with open(MONTFLORIT + ".tmp", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_MONTFLORIT)
        w.writeheader()
        w.writerows(guardadas[k] for k in sorted(guardadas))
    os.replace(MONTFLORIT + ".tmp", MONTFLORIT)


def apunta_casa(emes, ara, hores):
    """Una línea por hora de reloj: la primera pasada de cada hora."""
    hora = emes.strftime("%Y-%m-%dT%H")
    if os.path.exists(CASA_DARRERA):
        with open(CASA_DARRERA) as f:
            if f.read().strip() == hora:
                return
    os.makedirs(DIR, exist_ok=True)
    linea = {"emes": emes.isoformat(timespec="minutes"), "ara": ara, "hores": hores}
    with open(os.path.join(DIR, f"casa-{emes.strftime('%Y-%m')}.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(linea, ensure_ascii=False) + "\n")
    with open(CASA_DARRERA, "w") as f:
        f.write(hora)


def lineas_del_dia(dia):
    ruta = os.path.join(DIR, f"{dia[:7]}.jsonl")
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8") as f:
        return [d for d in map(json.loads, f) if d.get("dia") == dia]


# --- Lluvia observada ----------------------------------------------------------

def lluvia_montflorit(dia, ventanas):
    """mm en cada ventana, con los datos minuto a minuto (últimas 24 h)."""
    slug = next(iter(C.ESTACIONES_LOCALES))
    filas = json.loads(P.get(P.METEOCERDANYOLA.format(slug))).get("rows", [])
    filas = [f for f in filas if f.get("PREC") is not None]
    res = []
    for ini, fin in ventanas:
        mm = 0.0
        for antes, despues in zip(filas, filas[1:]):
            t = dt.datetime.fromisoformat(despues["dt_local"]).astimezone()
            if ini < t <= fin:
                salto = despues["PREC"] - antes["PREC"]
                mm += despues["PREC"] if salto < 0 else salto
        res.append(round(mm, 1))
    return res


def lluvia_meteocat(codi, ventanas):
    filas = P.taula_meteocat(codi)
    return [round(sum(mm for t, mm in filas if ini <= t < fin), 1) for ini, fin in ventanas]


def verifica(dia=None):
    dia = dia or P.AHORA.date().isoformat()
    lineas = lineas_del_dia(dia)
    if not lineas:
        print(f"{dia}: no hay actualizaciones registradas")
        return
    # La decisión es la de la última actualización que aún la recalculaba.
    decision = next((d for d in reversed(lineas) if not d["decisio"]["mantinguda"]), lineas[-1])
    ventanas = [(P.momento(dia, a), P.momento(dia, b)) for a, b in (C.IDA, C.VUELTA)]
    detalle, ida, vuelta = {}, [], []
    fuentes = [(C.ESTACIONES_LOCALES[s], lambda v: lluvia_montflorit(dia, v))
               for s in C.ESTACIONES_LOCALES]
    fuentes += [(nom, lambda v, c=codi: lluvia_meteocat(c, v)) for codi, nom in C.ESTACIONES.items()]
    for nom, funcion in fuentes:
        try:
            a, v = funcion(ventanas)
        except Exception as ex:
            detalle[nom] = f"sense dades ({ex.__class__.__name__})"
            continue
        detalle[nom] = [a, v]
        ida.append(a)
        vuelta.append(v)
    if not ida:
        print(f"{dia}: no hay datos de lluvia")
        return
    plou_a = max(ida) >= C.UMBRAL_MM
    plou_v = max(vuelta) >= C.UMBRAL_MM
    mitja = decision["decisio"]["mitja"]
    plou = plou_a or plou_v
    if mitja == "cotxe":
        resultat = "encert" if plou else "cotxe de mes"
    elif not plou:
        resultat = "encert"
    else:
        resultat = "pluja en moto amb impermeable" if mitja == "compte" else "pluja en moto"
    fila = {"dia": dia, "mitja": mitja, "decidit": decision["decisio"]["decidit"],
            "risc_anada": decision["anada"]["nivell"], "risc_tornada": decision["tornada"]["nivell"],
            "risc_tornada_final": lineas[-1]["tornada"]["nivell"],
            "pluja_anada_mm": max(ida), "pluja_tornada_mm": max(vuelta),
            "plou_anada": plou_a, "plou_tornada": plou_v, "resultat": resultat,
            "detall_estacions": json.dumps(detalle, ensure_ascii=False)}
    filas = leer_resultados()
    filas = [f for f in filas if f["dia"] != dia] + [fila]
    filas.sort(key=lambda f: f["dia"])
    os.makedirs(DIR, exist_ok=True)
    with open(RESULTADOS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)
    print(f"{dia}: {mitja}, ida {max(ida)} mm, vuelta {max(vuelta)} mm -> {resultat}")


def leer_resultados():
    if not os.path.exists(RESULTADOS):
        return []
    with open(RESULTADOS, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# --- Resumen ---------------------------------------------------------------------

def resum(avisa=False):
    filas = leer_resultados()
    if not filas:
        print("Aún no hay días verificados.")
        return
    n = len(filas)
    cuenta = {}
    for f in filas:
        cuenta[f["resultat"]] = cuenta.get(f["resultat"], 0) + 1
    lluvia = sum(f["plou_anada"] == "True" or f["plou_tornada"] == "True" for f in filas)
    dias = (dt.date.fromisoformat(filas[-1]["dia"]) - dt.date.fromisoformat(filas[0]["dia"])).days + 1
    texto = (f"*Moto o cotxe: resumen de {n} días* ({filas[0]['dia']} a {filas[-1]['dia']}).\n"
             f"Llovió en algún trayecto {lluvia} días.\n"
             f"Aciertos: {cuenta.get('encert', 0)}. Coche sin lluvia: {cuenta.get('cotxe de mes', 0)}. "
             f"Lluvia en moto: {cuenta.get('pluja en moto', 0)}, y con aviso de impermeable: "
             f"{cuenta.get('pluja en moto amb impermeable', 0)}.\n")
    if lluvia < C.REGISTRO_LLUVIAS_MINIMAS:
        texto += (f"Con solo {lluvia} días de lluvia aún no se puede juzgar la regla: "
                  "propongo esperar más.")
    else:
        texto += "Pídele a Claude que lo analice para decidir si vale la pena el modelo estadístico."
    print(texto)
    if avisa and dias >= C.REGISTRO_DIAS_AVISO and not os.path.exists(AVISO_ENVIADO):
        subprocess.run(["avisar-juanjo", "--asunto", "moto o cotxe", texto], check=True)
        with open(AVISO_ENVIADO, "w") as f:
            f.write(dt.datetime.now().isoformat())


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else ""
    if orden == "apunta":
        apunta(sys.argv[2])
    elif orden == "verifica":
        verifica(sys.argv[2] if len(sys.argv) > 2 else None)
    elif orden == "resum":
        resum("--avisa" in sys.argv)
    else:
        print(__doc__)
