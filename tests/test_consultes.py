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


AIRE = {"current": {"time": "2026-10-09T11:00", "european_aqi": 38, "european_aqi_pm2_5": 23,
                    "european_aqi_pm10": 13, "european_aqi_nitrogen_dioxide": 38, "european_aqi_ozone": 17},
        "hourly": {"time": [f"2026-10-09T{h:02d}:00" for h in range(24)],
                   "european_aqi": [46, 44, 43, 40, 36, 34, 37, 43, 51, 55, 47, 38, 28, 26, 31, 31, 29, 29, 38, 46,
                                    63, 72, 71, 68]}}
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
    def test_categories(self):
        self.assertEqual([AI.categoria(x) for x in (0, 20, 21, 59, 80, 101)],
                         ["bona", "bona", "raonablement_bona", "regular", "desfavorable", "extremadament_desfavorable"])

    def test_ara_i_el_pitjor_d_avui(self):
        a = AI.llegeix(AIRE, ARA)
        self.assertEqual((a["index"], a["categoria"], a["contaminant"]), (38, "raonablement_bona", "nitrogen_dioxide"))
        self.assertEqual(a["pitjor"], {"hora": "2026-10-09T21:00", "index": 72, "categoria": "desfavorable"})
        self.assertEqual(a["contaminants"]["ozone"], 17)
        self.assertEqual([h["hora"][11:13] for h in a["hores"]][:2], ["11", "12"])
        self.assertEqual(len(a["hores"]), 13)
        t = B.text_aire_bot({"generat": ARA.isoformat(), "aire": a}, "ca", ARA)
        self.assertIn("Ara: raonablement bona (índex europeu 38). El que més pesa és el diòxid de nitrogen (NO₂).", t)
        self.assertIn("El pitjor d'avui: desfavorable cap a les 21:00.", t)
        self.assertIn("no una mesura", t)


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
