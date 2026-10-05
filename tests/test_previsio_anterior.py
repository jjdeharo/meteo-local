# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas de la previsión de reserva de la página de casa (sin red)."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import casa  # noqa: E402
import prevision as P  # noqa: E402


def guarda(datos):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(datos, f)
    f.close()
    return f.name


def fila(fins, p=0.1):
    return {"hora": "", "fins": fins, "temperatura": 18.0, "pluja_mm": 0.0, "probabilitat": p,
            "plou_ara": False, "segons_estacio": False, "avisos": []}


class PrevisioAnterior(unittest.TestCase):
    def setUp(self):
        self.ahora = P.AHORA
        P.AHORA = dt.datetime(2026, 10, 5, 19, 37).astimezone()

    def tearDown(self):
        P.AHORA = self.ahora

    def test_horas_que_quedan_y_lluvia_de_ahora(self):
        antes = {"generat": "2026-10-05T19:27+02:00",
                 "hores": [fila("2026-10-05T19:00"), fila("2026-10-05T20:00"), fila("2026-10-05T21:00")]}
        r = casa.previsio_anterior(guarda(antes), {"intensitat": 3.0, "pluja_30min": 1.0}, [])
        self.assertEqual([f["fins"] for f in r["hores"]], ["2026-10-05T20:00", "2026-10-05T21:00"])
        self.assertEqual(r["previsio_de"], "2026-10-05T19:27+02:00")
        # Llueve ahora: la primera hora lo dice, aunque la previsión no lo viera.
        self.assertTrue(r["hores"][0]["plou_ara"])
        self.assertEqual(r["hores"][0]["probabilitat"], 1.0)
        self.assertFalse(r["hores"][1]["plou_ara"])

    def test_se_encadena_y_caduca(self):
        # Una reserva de otra reserva conserva la hora de la previsión buena.
        antes = {"generat": "2026-10-05T19:27+02:00", "previsio_de": "2026-10-05T14:00+02:00",
                 "hores": [fila("2026-10-05T20:00")]}
        self.assertEqual(casa.previsio_anterior(guarda(antes), None, [])["previsio_de"],
                         "2026-10-05T14:00+02:00")
        antes["previsio_de"] = "2026-10-05T13:00+02:00"      # más de 6 horas
        self.assertIsNone(casa.previsio_anterior(guarda(antes), None, []))
        self.assertIsNone(casa.previsio_anterior(None, None, []))
        self.assertIsNone(casa.previsio_anterior("/no/existeix.json", None, []))


if __name__ == "__main__":
    unittest.main()
