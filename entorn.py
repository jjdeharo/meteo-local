# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lo que pasa alrededor de Montflorit y condiciona salir (ADR 0046):

- incendios forestales en curso a menos de ENTORN_RADI_KM, de la capa pública
  de actuaciones urgentes de Bombers de la Generalitat (ArcGIS);
- el nivel del Pla Alfa de Cerdanyola hoy y mañana, y los cierres de espacios
  naturales que tocan Collserola, de las capas públicas de Agents Rurals
  (ArcGIS);
- las restricciones de acceso al Parc Natural de la Serra de Collserola, de
  los avisos vigentes de su web (API de WordPress).

Las dos fuentes de ArcGIS son las que usan los visores oficiales, no conjuntos
de datos documentados: si una falla, su parte queda en None y se dice.

    python3 entorn.py        lo que hay ahora, en JSON
"""
import datetime as dt
import html
import json
import math
import re
import sys
import urllib.parse
import urllib.request

import config as C

ARCGIS = "https://services7.arcgis.com/ZCqVt1fRXwwK6GF4/arcgis/rest/services"
BOMBERS = ARCGIS + "/ACTUACIONS_URGENTS_online_PRO_AMB_FASE_VIEW/FeatureServer/0"
ALFA_MUNICIPAL = {"avui": ARCGIS + "/Pla_Alfa_Municipal_Avui_FL_2_view/FeatureServer/0",
                  "dema": ARCGIS + "/pla_alfa_municipal_dema_FL_VW/FeatureServer/5"}
ALFA_TANCAMENTS = {"avui": ARCGIS + "/tancaments_pla_alfa_avui_VW/FeatureServer/2",
                   "dema": ARCGIS + "/tancaments_pla_alfa_dema_VW/FeatureServer/2"}
COLLSEROLA_AVISOS = "https://parcnaturalcollserola.cat/wp-json/wp/v2/posts"
COLLSEROLA_CATEGORIA = 877          # «avisos-ca»: los vigentes (los caducados van a otra)
UA = {"User-Agent": "Temps a Montflorit (https://meteo-montflorit.github.io/)"}

# Un aviso del parque es de acceso si su título habla de cerrar, limitar o
# restringir el acceso o el paso (el 12-03-2026: «Tancat l'accés al medi
# natural…»; el 12-02-2026: «Es limita l'accès al Parc Natural…»).
ACCES = re.compile(r"(tanca|limita|restring|restricci|prohib).{0,60}(acc[eè]s|pas\b|medi natural)"
                   r"|(acc[eè]s|medi natural).{0,40}(tancat|limitat|restringit|prohibit)", re.I)


def get(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    return 6371 * math.hypot((lo2 - lo1) * math.cos((la1 + la2) / 2), la2 - la1)


def hora_iso(ms):
    return dt.datetime.fromtimestamp(ms / 1000).astimezone().isoformat(timespec="minutes") if ms else None


def incendis(dades=None):
    """Incendios de vegetación forestal en curso a menos de ENTORN_RADI_KM de casa."""
    d = dades or get(BOMBERS + "/query", {
        "where": "TAL_COD_ALARMA1='IV'", "geometry": f"{C.CASA[1]},{C.CASA[0]}",
        "geometryType": "esriGeometryPoint", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
        "distance": C.ENTORN_RADI_KM, "units": "esriSRUnit_Kilometer", "outSR": 4326,
        "outFields": "GlobalID,TAL_DESC_ALARMA2,MUNICIPI_SIG,ACT_DAT_INICI,ACT_DAT_FI,ACT_NUM_VEH,COM_FASE",
        "returnGeometry": "true", "f": "json"})
    if "error" in d:
        raise RuntimeError(d["error"].get("message"))
    res = []
    for f in d.get("features", []):
        a, g = f["attributes"], f.get("geometry") or {}
        # Solo los forestales: los de solares urbanos son muchos y no limitan salir.
        if "forestal" not in (a.get("TAL_DESC_ALARMA2") or "").lower() or a.get("ACT_DAT_FI"):
            continue
        dist = km(C.CASA, (g["y"], g["x"])) if "x" in g else None
        res.append({"id": a["GlobalID"], "municipi": a.get("MUNICIPI_SIG"), "km": round(dist, 1) if dist else None,
                    "inici": hora_iso(a.get("ACT_DAT_INICI")), "vehicles": a.get("ACT_NUM_VEH"),
                    "fase": a.get("COM_FASE")})
    return sorted(res, key=lambda i: i["km"] if i["km"] is not None else 99)


def actualitzada(url, ara, hores):
    """Si la capa se ha editado en las últimas `hores`: fuera de campaña, la
    del Pla Alfa municipal se queda con el último valor y no vale."""
    edit = ((get(url, {"f": "json"}).get("editingInfo") or {}).get("lastEditDate"))
    return bool(edit) and ara - dt.datetime.fromtimestamp(edit / 1000).astimezone() <= dt.timedelta(hours=hores)


def pla_alfa(ara):
    """Nivel del Pla Alfa de Cerdanyola hoy y mañana (None si la capa no está
    al día) y los cierres de espacios naturales que tocan Collserola."""
    res = {}
    for dia, url in ALFA_MUNICIPAL.items():
        nivell = None
        if actualitzada(url, ara, C.ALFA_ACTUAL_H):
            d = get(url + "/query", {"where": f"CODIMUNI='{C.ALFA_MUNICIPI}'", "outFields": "PERIL_M",
                                     "returnGeometry": "false", "f": "json"})
            files = d.get("features") or []
            nivell = files[0]["attributes"]["PERIL_M"] if files else None
        # La escala es 0-4; el 5 es «sin nivel» (gris claro en el mapa oficial).
        res[dia] = nivell if nivell in (0, 1, 2, 3, 4) else None
    tancaments = []
    for dia, url in ALFA_TANCAMENTS.items():
        d = get(url + "/query", {"where": "1=1", "outFields": "Espai_prot", "returnGeometry": "false", "f": "json"})
        for f in d.get("features") or []:
            nom = f["attributes"].get("Espai_prot") or ""
            if "collserola" in nom.lower():
                tancaments.append({"dia": dia, "espai": nom})
    res["tancaments"] = tancaments
    return res


def collserola(dades=None):
    """Los avisos vigentes del parque que restringen el acceso."""
    posts = dades if dades is not None else get(COLLSEROLA_AVISOS, {
        "categories": COLLSEROLA_CATEGORIA, "per_page": 30, "_fields": "id,date,link,title"})
    res = []
    for p in posts:
        titol = html.unescape(re.sub(r"<[^>]+>", "", p["title"]["rendered"])).strip()
        if ACCES.search(titol):
            res.append({"id": p["id"], "titol": titol, "data": p["date"][:10], "enllac": p["link"]})
    return res


def calcula(ara=None):
    """Para casa.json y los datos públicos. Cada parte, None si su fuente falla."""
    ara = ara or dt.datetime.now().astimezone()
    res = {"hora": ara.isoformat(timespec="minutes"), "errors": []}
    for clau, funcio in (("incendis", incendis), ("pla_alfa", lambda: pla_alfa(ara)), ("collserola", collserola)):
        try:
            res[clau] = funcio()
        except Exception as ex:
            res[clau] = None
            res["errors"].append(f"{clau}: {ex}")
    return res


if __name__ == "__main__":
    print(json.dumps(calcula(), ensure_ascii=False, indent=1))
