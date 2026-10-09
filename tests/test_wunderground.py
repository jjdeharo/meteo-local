# SPDX-License-Identifier: AGPL-3.0-or-later
"""La subida de la estación de casa a Weather Underground (wunderground.py, ADR 0059), sin red."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import wunderground as W  # noqa: E402

CASA = {"hora": "2026-10-09T22:40+02:00", "temperatura": 12.5, "humitat": 89.0, "rosada": 10.7,
        "pressio": 1018.6, "solar": 0.0, "uv": 0.0, "intensitat": 0.0, "pluja_1h": 0.2, "pluja_avui": 2.54,
        "pluja_15min": 0.0, "plou": False, "files": []}


class Parametres(unittest.TestCase):
    def test_unitats_de_weather_underground(self):
        p = W.parametres(CASA)
        self.assertEqual(p["dateutc"], "2026-10-09 20:40:00")        # en UTC
        self.assertEqual(p["tempf"], 54.5)
        self.assertEqual(p["dewptf"], 51.3)
        self.assertEqual(p["humidity"], 89.0)
        self.assertEqual(p["baromin"], 30.079)                         # inHg, al nivell del mar
        self.assertEqual((p["rainin"], p["dailyrainin"]), (0.008, 0.1))  # polzades
        self.assertEqual((p["solarradiation"], p["UV"]), (0.0, 0.0))
        self.assertEqual(p["action"], "updateraw")
        self.assertNotIn("windspeedmph", p)                            # el vent no es puja (ADR 0017)

    def test_sense_dades_no_s_envien_camps_buits(self):
        p = W.parametres({"hora": CASA["hora"], "temperatura": 12.5})
        self.assertEqual(set(p), {"dateutc", "tempf", "softwaretype", "action"})


class Puja(unittest.TestCase):
    def test_sense_claus_no_puja(self):
        with mock.patch.dict(os.environ, {"HOME": tempfile.mkdtemp()}, clear=True):
            self.assertFalse(W.disponible())
            self.assertIsNone(W.puja(CASA))

    def test_amb_claus_envia_id_i_clau(self):
        urls = []
        with mock.patch.dict(os.environ, {"WU_STATION_ID": "IPROVA1", "WU_STATION_KEY": "clau"}):
            r = W.puja(CASA, lector=lambda u: urls.append(u) or "success")
        self.assertEqual(r, "success")
        self.assertIn("ID=IPROVA1&PASSWORD=clau&dateutc=2026-10-09+20%3A40%3A00&tempf=54.5", urls[0])
        self.assertTrue(urls[0].startswith(W.URL))


if __name__ == "__main__":
    unittest.main()
