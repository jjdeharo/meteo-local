# SPDX-License-Identifier: AGPL-3.0-or-later
"""Incendios cerca, Pla Alfa y acceso a Collserola (entorn.py, ADR 0046), y sus
avisos (sin red)."""
import datetime as dt
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import avisos_bot as AB  # noqa: E402
import config as C  # noqa: E402
import entorn as EN  # noqa: E402

ARA = dt.datetime(2026, 10, 8, 13, 0).astimezone()


def feature(desc, municipi, y, x, fi=None, gid="g1"):
    return {"attributes": {"GlobalID": gid, "TAL_DESC_ALARMA2": desc, "MUNICIPI_SIG": municipi,
                           "ACT_DAT_INICI": int(ARA.timestamp() * 1000), "ACT_DAT_FI": fi,
                           "ACT_NUM_VEH": 4, "COM_FASE": None}, "geometry": {"x": x, "y": y}}


def post(pid, titol, data="2026-03-12"):
    return {"id": pid, "date": data + "T18:51:00", "link": f"https://parcnaturalcollserola.cat/{pid}/",
            "title": {"rendered": titol}}


class Fonts(unittest.TestCase):
    def test_incendis_forestals_en_curs(self):
        d = {"features": [feature("Incendi vegetació forestal", "Sant Cugat del Vallès", 41.47, 2.09, gid="a"),
                          feature("Incendi vegetació urbana", "Cerdanyola del Vallès", 41.49, 2.14, gid="b"),
                          feature("Incendi vegetació forestal", "Ripollet", 41.50, 2.16, fi=1, gid="c")]}
        r = EN.incendis(d)
        self.assertEqual([i["id"] for i in r], ["a"])      # ni l'urbà ni l'acabat
        self.assertEqual(r[0]["municipi"], "Sant Cugat del Vallès")
        self.assertAlmostEqual(r[0]["km"], 3.9, delta=0.3)

    def test_pla_alfa_el_5_no_es_cap_nivell(self):
        respostes = {"avui": 4, "dema": 5}
        def get(url, params=None):
            if params == {"f": "json"}:
                return {"editingInfo": {"lastEditDate": int(ARA.timestamp() * 1000)}}
            if "Espai_prot" in str(params):
                return {"features": [{"attributes": {"Espai_prot": "Parc Natural de la Serra de Collserola"}}]}
            dia = "avui" if "Avui" in url else "dema"
            return {"features": [{"attributes": {"PERIL_M": respostes[dia]}}]}
        with mock.patch.object(EN, "get", get):
            r = EN.pla_alfa(ARA)
        self.assertEqual((r["avui"], r["dema"]), (4, None))
        self.assertEqual(len(r["tancaments"]), 2)

    def test_pla_alfa_capa_vella_no_val(self):
        vell = int((ARA - dt.timedelta(days=50)).timestamp() * 1000)
        def get(url, params=None):
            return {"editingInfo": {"lastEditDate": vell}} if params == {"f": "json"} else {"features": []}
        with mock.patch.object(EN, "get", get):
            self.assertEqual(EN.pla_alfa(ARA), {"avui": None, "dema": None, "tancaments": []})

    def test_collserola_nomes_restriccions_d_acces(self):
        posts = [post(1, "Tancat l&#8217;accés al medi natural al Parc Natural de la Serra de Collserola"),
                 post(2, "Es limita l’accès al Parc Natural per risc alt de ventades"),
                 post(3, "Tancament temporal per mal estat de conservació de la passera"),
                 post(4, "Horaris d’estiu dels equipaments del Parc Natural 2026")]
        self.assertEqual([a["id"] for a in EN.collserola(posts)], [1, 2])


class Avisos(unittest.TestCase):
    def passada(self, estat, incendis, collserola, minuts=0):
        salida = {"entorn": {"incendis": incendis, "collserola": collserola, "pla_alfa": {}}}
        return [a for a in AB.decideix(estat, salida, ARA + dt.timedelta(minutes=minuts)) if a["tipus"] == "perill"]

    def test_la_primera_vegada_nomes_s_apunta(self):
        estat = {}
        tancat = [{"id": 131489, "titol": "Tancat l’accés al medi natural", "data": "2026-03-12", "enllac": "u"}]
        self.assertEqual(self.passada(estat, [], tancat), [])
        self.assertEqual(self.passada(estat, [], tancat, 15), [])

    def test_incendi_a_prop_i_quan_s_acaba(self):
        estat = {}
        self.passada(estat, [], [])
        foc = [{"id": "x", "municipi": "Sant Cugat del Vallès", "km": 3.2, "inici": ARA.isoformat(), "vehicles": 4}]
        nous = self.passada(estat, foc, [], 6)
        self.assertEqual(len(nous), 1)
        self.assertTrue(nous[0]["ca"].startswith("<b>Incendi forestal a prop de Montflorit: Sant Cugat del Vallès</b>"))
        self.assertIn("a unos 3,2 km", nous[0]["es"])
        self.assertEqual(self.passada(estat, foc, [], 12), [])          # una sola vegada
        fi = self.passada(estat, [], [], 18)
        self.assertIn("ja no consta com a actiu", fi[0]["ca"])

    def test_collserola_tanca_i_reobre(self):
        estat = {}
        self.passada(estat, [], [])
        tancat = [{"id": 7, "titol": "Tancat l’accés al medi natural", "data": "2026-11-02", "enllac": "u7"}]
        nous = self.passada(estat, [], tancat, 6)
        self.assertIn("Collserola: restricció d'accés al parc", nous[0]["ca"])
        self.assertIn("«Tancat l’accés al medi natural»", nous[0]["ca"])
        obre = self.passada(estat, [], [], 12)
        self.assertIn("el parc ja no té cap avís de restricció d'accés", obre[0]["ca"])

    def test_si_una_font_falla_no_es_toca_l_estat(self):
        estat = {}
        foc = [{"id": "x", "municipi": "Cerdanyola del Vallès", "km": 1.0, "inici": ARA.isoformat()}]
        self.passada(estat, foc, [])
        self.assertEqual(self.passada(estat, None, None, 6), [])     # Bombers no respon: no «s'ha acabat»
        self.assertIn("x", estat["entorn"]["incendis"])


if __name__ == "__main__":
    unittest.main()
