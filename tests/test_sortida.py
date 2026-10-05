# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas de la salida fuera de las franjas (casa.sortides, sin red)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import casa  # noqa: E402


def hora(h, p=0.01, mm=0.0, t=18.0, avisos=None, dia="2026-10-05"):
    return {"hora": f"{dia}T{h:02d}:00", "probabilitat": p, "pluja_mm": mm, "temperatura": t,
            "avisos": avisos or [], "plou_ara": False}


class Sortides(unittest.TestCase):
    def test_medio_por_las_horas_de_circular(self):
        hores = [hora(16), hora(17, p=0.8, mm=2), hora(18), hora(19, p=0.3)]
        s = casa.sortides(hores, [])
        self.assertEqual(s[0]["surt"], "2026-10-05T16:00")
        tornades = {t["hora"][11:13]: t for t in s[0]["tornades"]}
        # Llueve a las 17 pero se vuelve a las 18: moto (el vehículo está aparcado).
        self.assertEqual(tornades["18"]["mitja"], "moto")
        self.assertEqual(tornades["17"]["mitja"], "cotxe")
        self.assertEqual(tornades["19"]["mitja"], "compte")
        self.assertEqual(tornades["19"]["tornada"]["motiu"], "pluja 30 %")
        self.assertIn("A partir de les 17 h, pluja probable", tornades["18"]["canvis"][0])
        # También con la salida en la hora siguiente.
        self.assertEqual(s[1]["surt"], "2026-10-05T17:00")

    def test_avisos_y_proteccion_civil(self):
        hores = [hora(8), hora(9, avisos=[{"nivell": "groc", "tipus": ["pluja"]}])]
        t = casa.sortides(hores, [])[0]["tornades"][0]
        self.assertEqual((t["mitja"], t["tornada"]["motiu"]), ("cotxe", "avís groc de l’AEMET"))
        t = casa.sortides([hora(8), hora(9)], [{"fase": "emergència"}])[0]["tornades"][0]
        self.assertEqual(t["anada"]["motiu"], "Protecció Civil en emergència")

    def test_cambio_de_temperatura_y_ropa(self):
        hores = [hora(6, t=8), hora(9, t=12), hora(14, t=19)]
        t = casa.sortides(hores, [])[0]["tornades"][-1]
        self.assertIn("La temperatura va de 8 °C (6 h) a 19 °C (14 h).", t["canvis"])
        self.assertIn("capes", t["roba"]["text"])
        self.assertEqual(t["roba"]["peca"], "jaqueta")


if __name__ == "__main__":
    unittest.main()
