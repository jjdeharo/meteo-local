# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas de la recogida de datos de prevision.py con datos inventados (sin red)."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import prevision as P  # noqa: E402


class EstacionMinutal(unittest.TestCase):
    def filas(self, valores, inicio="2026-10-05 06:30"):
        t0 = dt.datetime.fromisoformat(inicio)
        return [{"dt_local": (t0 + dt.timedelta(minutes=i)).isoformat(sep=" "),
                 "PREC": p, "PINT": 0} for i, p in enumerate(valores)]

    def test_lluvia_de_la_ultima_media_hora(self):
        # 40 minutos: 1 mm al principio (fuera de la media hora) y 2 mm al final.
        valores = [0.0] * 5 + [1.0] * 30 + [2.0, 3.0, 3.0, 3.0, 3.0]
        r = P.resumen_minutal(self.filas(valores), "Prova", "prova")
        self.assertEqual(r["mm_hoy"], 3.0)
        self.assertEqual(r["mm_ultima_media_hora"], 2.0)

    def test_el_acumulado_vuelve_a_cero_a_medianoche(self):
        valores = [5.0] * 10 + [0.0, 0.5, 1.0]
        r = P.resumen_minutal(self.filas(valores, "2026-10-04 23:50"), "Prova", "prova")
        self.assertEqual(r["mm_ultima_media_hora"], 1.0)

    def test_sin_filas_no_hay_dato(self):
        self.assertIsNone(P.resumen_minutal([], "Prova", "prova"))


class ProteccionCivil(unittest.TestCase):
    def test_un_plan_de_otra_zona_no_cuenta(self):
        self.assertFalse(P.afecta_la_zona("CHE. Vigilància per previsió meteorològica adversa conca de l'Ebre - "))
        self.assertTrue(P.afecta_la_zona("Emergència INUNCAT 3-5 Octubre"))
        self.assertTrue(P.afecta_la_zona("Pluges intenses a Girona i al Vallès"))
        self.assertTrue(P.afecta_la_zona(None))


if __name__ == "__main__":
    unittest.main()
