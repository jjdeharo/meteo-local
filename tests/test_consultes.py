# SPDX-License-Identifier: AGPL-3.0-or-later
"""«Consultes» (ADR 0054): el pol·len, l'aire i el sol, els seus textos al bot
i a la web, sense xarxa. El pol·len, amb les respostes reals de l'API del PIA
del 09-10-2026 (tests/dades)."""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import unittest

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
sys.path.insert(0, os.path.join(ARREL, "bot"))
import aire as AI  # noqa: E402
import bot as B  # noqa: E402
import montflorit as M  # noqa: E402
import pollen as PO  # noqa: E402

ARA = dt.datetime(2026, 10, 9, 11, 40).astimezone()


def llegeix_js():
    with open(os.path.join(ARREL, "web", "consultes.js"), encoding="utf-8") as f:
        return f.read()
DADES = os.path.join(ARREL, "tests", "dades")


def pollen():
    with open(os.path.join(DADES, "pollen-bellaterra-ca.xml"), "rb") as ca, \
            open(os.path.join(DADES, "pollen-bellaterra-es.xml"), "rb") as es:
        return PO.llegeix(ca.read(), es.read())


HORES = [f"2026-10-09T{h:02d}:00" for h in range(24)]
# Hora a hora d'avui, del model (µg/m³): el NO₂ puja al vespre.
AIRE = {"hourly": {"time": HORES,
                   "nitrogen_dioxide": [20.0] * 19 + [40.0, 70.0, 80.0, 60.0, 50.0],
                   "ozone": [50.0] * 24, "pm10": [10.0] * 24, "pm2_5": [4.0] * 24,
                   "sulphur_dioxide": [2.0] * 24}}
SOL = [{"dia": "2026-10-09", "sortida": "2026-10-09T07:56", "posta": "2026-10-09T19:20", "uv_max": 4.85},
       {"dia": "2026-10-10", "sortida": "2026-10-10T07:57", "posta": "2026-10-10T19:18", "uv_max": 4.65}]


class Pollen(unittest.TestCase):
    def test_llegeix_l_api(self):
        p = pollen()
        self.assertEqual((p["estacio"], p["km"], p["inici"], p["fi"]), ("Bellaterra", 3.1, "2026-10-05", "2026-10-11"))
        xiprers = {t["codi"]: t for t in p["pollens"]}["CUPR"]
        self.assertEqual(xiprers, {"codi": "CUPR", "nom": {"ca": "Xiprers", "es": "Cipreses"}, "nivell": 0,
                                   "tendencia": "A"})
        self.assertEqual([t["nivell"] for t in p["espores"]], [4, 4])

    def test_text_del_bot(self):
        t = B.text_pollen_bot({"pollen": pollen()}, "ca", ARA)
        self.assertIn("<b>Pol·len a Bellaterra</b> (setmana del 5/10 al 11/10, a 3,1 km)", t)
        self.assertIn("Mig: Artemísia, Compostes.\nBaix: Parietària, Gramínies, Blets, Pi (en descens).\n"
                      "Nul: Olivera, Casuarina, Palmeres, Plantatge, Plàtan.", t)
        self.assertIn("Comencen a pujar: Xiprers.", t)
        self.assertIn("<b>Espores de fongs</b>\nMàxim: Alternària, Cladosporium.", t)
        self.assertIn("CC BY-NC-SA 4.0", t)
        self.assertNotIn("última setmana", t)
        # Si la setmana ja ha passat, es diu.
        self.assertIn("Son los datos de la última semana publicada.",
                      B.text_pollen_bot({"pollen": pollen()}, "es", ARA + dt.timedelta(days=5)))


class Aire(unittest.TestCase):
    def test_index_de_cada_contaminant(self):
        # Taula de l'índex europeu d'Open-Meteo: el NO₂ de 10 a 25 µg/m³ és 20-40.
        self.assertEqual([AI.index_de("nitrogen_dioxide", x) for x in (0, 10, 17.5, 25, 60, 150, 200)],
                         [0, 20, 30, 40, 60, 100, 120])
        self.assertEqual([AI.categoria(x) for x in (0, 20, 21, 59, 80, 101)],
                         ["bona", "bona", "raonablement_bona", "regular", "desfavorable", "extremadament_desfavorable"])

    def test_factors_amb_dues_estacions(self):
        model = {"time": HORES[:80 // 1][:24] * 4, "nitrogen_dioxide": [20.0] * 96, "pm10": [10.0] * 96}
        model["time"] = [f"2026-10-0{d}T{h:02d}:00" for d in range(5, 9) for h in range(24)]
        mesures = {}
        for t in model["time"]:
            mesures[("Sant Cugat del Vallès", "nitrogen_dioxide", t)] = 8.0
            mesures[("Barberà del Vallès", "nitrogen_dioxide", t)] = 12.0
            mesures[("Montcada i Reixac", "pm10", t)] = 25.0        # una sola estació: no es corregeix
        f = AI.factors(model, mesures)
        self.assertEqual(f, {"nitrogen_dioxide": {"factor": 0.5, "hores": 96}})

    def test_ultimes_mesures(self):
        files = [{"nom_estacio": "Sant Cugat del Vallès", "contaminant": "NO2", "data": "2026-10-09T00:00:00.000",
                  "h01": "11", "h04": "7"},
                 {"nom_estacio": "Sant Cugat del Vallès", "contaminant": "O3", "data": "2026-10-09T00:00:00.000",
                  "h04": "32"}]
        m = AI.ultimes(AI.per_hora(files))
        self.assertEqual(m, [{"estacio": "Sant Cugat del Vallès", "km": 3.9, "hora": "2026-10-09T04:00",
                              "valors": {"nitrogen_dioxide": 7.0, "ozone": 32.0}, "index": 14}])

    def test_ara_i_el_pitjor_d_avui_corregits(self):
        corr = {"factors": {"nitrogen_dioxide": {"factor": 0.5, "hores": 700}},
                "mesures": [{"estacio": "Sant Cugat del Vallès", "km": 3.9, "hora": "2026-10-09T04:00",
                             "valors": {"nitrogen_dioxide": 7.0, "ozone": 32.0}, "index": 14}]}
        a = AI.llegeix(AIRE, ARA, corr)
        # 11:40: el NO₂ de 20 passa a 10 (índex 20); l'ozó, sense corregir, 50 µg/m³ (índex 17).
        self.assertEqual((a["hora"], a["index"], a["contaminant"], a["corregit"]),
                         ("2026-10-09T11:00", 20, "nitrogen_dioxide", True))
        self.assertEqual(a["pitjor"], {"hora": "2026-10-09T21:00", "index": 49, "categoria": "regular"})
        sense = AI.llegeix(AIRE, ARA)
        self.assertEqual((sense["index"], sense["corregit"]), (33, False))
        t = B.text_aire_bot({"generat": ARA.isoformat(), "aire": a}, "ca", ARA)
        self.assertIn("Ara: bona (índex europeu 20).", t)
        self.assertIn("El pitjor d'avui: regular cap a les 21:00.", t)
        self.assertIn("no mesurada a Montflorit; NO₂, corregits amb les mesures", t)
        self.assertIn("Sant Cugat del Vallès (3,9 km), a les 4 h: NO₂ 7, ozó 32 µg/m³ (bona).", t)


class Sol(unittest.TestCase):
    def test_text_del_bot(self):
        t = B.text_sol_bot({"generat": ARA.isoformat(), "sol": SOL}, "ca", ARA)
        self.assertIn("Surt a les 07:56 i es pon a les 19:20: 11 h 24 min de llum.", t)
        self.assertIn("Índex UV màxim: 5 (moderat). A les hores centrals, protector solar", t)
        self.assertIn("Demà surt a les 07:57 i es pon a les 19:18.", t)
        self.assertIn("Sale a las 07:56", B.text_sol_bot({"generat": ARA.isoformat(), "sol": SOL}, "es", ARA))


class DadesDeLaWeb(unittest.TestCase):
    def test_les_consultes_son_les_del_bot(self):
        dades = {"generat": ARA.isoformat(), "sol": SOL, "aire": AI.llegeix(AIRE, ARA), "pollen": pollen(),
                 "hores": [], "trens": {"linies": []}, "transit": {"hora": ARA.isoformat(), "incidencies": []}}
        c = M.dades_publiques(dades)["consultes"]
        self.assertEqual(list(c["ca"]), list(M.CONSULTES))
        self.assertEqual(c["ca"]["sol"], B.text_sol_bot(dades, "ca", ARA))
        self.assertNotIn(B.WEB, json.dumps(c))                   # sense l'enllaç a la web: ja s'hi és


@unittest.skipUnless(shutil.which("node"), "cal Node")
class Pagina(unittest.TestCase):
    def trossos(self, text):
        codi = ("const T = (x) => x; const $ = () => null; const element = () => ({});"
                + llegeix_js().split("// Paràgrafs")[0]
                .split("let triada = triadaInicial();")[1]
                + f"console.log(JSON.stringify(trossos({json.dumps(text)})));")
        r = subprocess.run(["node", "-e", codi], capture_output=True, text=True, check=True)
        return json.loads(r.stdout)

    def test_l_html_de_telegram_es_llegeix_sense_innerhtml(self):
        l = self.trossos('<b>Trens</b>\n«Obres &lt;a Montcada&gt;.» <a href="https://x.cat/a?b=1&amp;c=2">Mapa</a>')
        self.assertEqual(l[0], [{"t": "Trens", "b": True, "i": False, "href": None}])
        self.assertEqual(l[1][0]["t"], "«Obres <a Montcada>.» ")
        self.assertEqual(l[1][1], {"t": "Mapa", "b": False, "i": False, "href": "https://x.cat/a?b=1&c=2"})
        # Una adreça solta, enllaçada; una que no és https, no.
        l = self.trossos("En directe: https://www.meteo.cat/radar.\n<a href=\"javascript:x\">x</a>")
        self.assertEqual(l[0][1]["href"], "https://www.meteo.cat/radar")
        self.assertIsNone(l[1][0]["href"])

    def test_opcions_en_l_ordre_del_bot(self):
        js = llegeix_js()
        claus = [c for c in M.CONSULTES]
        posicions = [js.index(f"['{c}',") for c in claus]
        self.assertEqual(posicions, sorted(posicions))


if __name__ == "__main__":
    unittest.main()
