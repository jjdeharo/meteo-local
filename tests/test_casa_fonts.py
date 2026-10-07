# SPDX-License-Identifier: AGPL-3.0-or-later
"""casa.py ante fuentes congeladas o caídas (revisión del 07-10-2026), sin red."""
import datetime as dt
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import casa  # noqa: E402
import prevision as P  # noqa: E402

AHORA = dt.datetime(2026, 10, 7, 18, 30).astimezone()


def files(fins):
    res = []
    for i in range(60):
        t = fins - dt.timedelta(minutes=59 - i)
        res.append({"dt_local": t.strftime("%Y-%m-%d %H:%M:%S"), "TEMP": 20.0, "HUM": 70, "VEL": 0, "PREC": 0.0, "PINT": 0})
    return res


class Fonts(unittest.TestCase):
    def setUp(self):
        self.ahora, self.get_recent, self.get = P.AHORA, P.get_recent, P.get
        P.AHORA = AHORA

    def tearDown(self):
        P.AHORA, P.get_recent, P.get = self.ahora, self.get_recent, self.get

    def test_montflorit_congelada_no_val(self):
        P.get_recent = lambda url, segons=120: json.dumps({"rows": files(AHORA - dt.timedelta(minutes=45))})
        with self.assertRaises(RuntimeError):
            casa.montflorit()
        P.get_recent = lambda url, segons=120: json.dumps({"rows": files(AHORA - dt.timedelta(minutes=5))})
        _, ara = casa.montflorit()
        self.assertEqual(ara["temperatura"], 20.0)
        self.assertIsNone(ara["vent"])     # el vent de Montflorit no es publica (ADR 0037)

    def test_sense_ensemble_la_previsio_segueix(self):
        def get(url):
            if "ensemble" in url:
                raise RuntimeError("502")
            return json.dumps({"hourly": {"time": []}})
        P.get = get
        errors = []
        h, e = casa.modelos(AHORA, errors)
        self.assertEqual((h, e), ({"time": []}, {}))
        self.assertTrue(errors and errors[0].startswith("ensemble: "))
        with self.assertRaises(RuntimeError):
            casa.modelos(AHORA)        # sense llista d'errors, com abans: falla


if __name__ == "__main__":
    unittest.main()
