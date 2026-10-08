# SPDX-License-Identifier: AGPL-3.0-or-later
"""Incendios cerca y Pla Alfa (entorn.py, ADR 0046), y sus avisos (sin red)."""
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


class Avisos(unittest.TestCase):
    def passada(self, estat, incendis, minuts=0):
        salida = {"entorn": {"incendis": incendis, "pla_alfa": {}}}
        return [a for a in AB.decideix(estat, salida, ARA + dt.timedelta(minutes=minuts)) if a["tipus"] == "perill"]

    def test_la_primera_vegada_nomes_s_apunta(self):
        estat = {}
        foc = [{"id": "x", "municipi": "Ripollet", "km": 2.0, "inici": ARA.isoformat()}]
        self.assertEqual(self.passada(estat, foc), [])
        self.assertEqual(self.passada(estat, foc, 15), [])

    def test_incendi_a_prop_i_quan_s_acaba(self):
        estat = {}
        self.passada(estat, [])
        foc = [{"id": "x", "municipi": "Sant Cugat del Vallès", "km": 3.2, "inici": ARA.isoformat(), "vehicles": 4}]
        nous = self.passada(estat, foc, 6)
        self.assertEqual(len(nous), 1)
        self.assertTrue(nous[0]["ca"].startswith("<b>Incendi forestal a prop de Montflorit: Sant Cugat del Vallès</b>"))
        self.assertIn("a unos 3,2 km", nous[0]["es"])
        self.assertEqual(self.passada(estat, foc, 12), [])          # una sola vegada
        fi = self.passada(estat, [], 18)
        self.assertIn("ja no consta com a actiu", fi[0]["ca"])

    def test_si_una_font_falla_no_es_toca_l_estat(self):
        estat = {}
        foc = [{"id": "x", "municipi": "Cerdanyola del Vallès", "km": 1.0, "inici": ARA.isoformat()}]
        self.passada(estat, foc)
        self.assertEqual(self.passada(estat, None, 6), [])     # Bombers no respon: no «s'ha acabat»
        self.assertIn("x", estat["entorn"]["incendis"])


if __name__ == "__main__":
    unittest.main()
