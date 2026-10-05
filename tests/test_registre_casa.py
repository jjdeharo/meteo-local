# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas del registro de la página de casa (sin red)."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import registre as R  # noqa: E402


def fila(hhmm, prec, temp=20.0, dia="2026-10-05"):
    return {"dt_local": f"{dia} {hhmm}:00", "PREC": prec, "TEMP": temp, "HUM": 90}


class HorasMontflorit(unittest.TestCase):
    def test_lluvia_y_temperatura_por_hora(self):
        filas = [fila("06:58", 1.0), fila("07:00", 1.2, 17.0), fila("07:30", 3.0),
                 fila("07:57", 4.0, 18.0), fila("08:10", 4.5)]
        h = R.horas_montflorit(filas)
        # La hora de 6 a 7 está cortada (empieza a las 6:58): no cuenta.
        self.assertEqual(list(h), [dt.datetime(2026, 10, 5, 8, 0)])
        self.assertAlmostEqual(h[dt.datetime(2026, 10, 5, 8, 0)]["pluja_mm"], 2.8)
        # Sin lectura a las 8:00 en punto, la de las 7:57.
        self.assertEqual(h[dt.datetime(2026, 10, 5, 8, 0)]["temperatura"], 18.0)

    def test_paso_por_medianoche(self):
        # El acumulado del día vuelve a cero a medianoche.
        filas = [fila("22:59", 5.0, dia="2026-10-04"), fila("23:30", 5.4, dia="2026-10-04"),
                 fila("00:00", 5.6, dia="2026-10-05"), fila("00:20", 0.2, dia="2026-10-05"),
                 fila("01:00", 0.3, dia="2026-10-05")]
        h = R.horas_montflorit(filas)
        self.assertAlmostEqual(h[dt.datetime(2026, 10, 5, 0, 0)]["pluja_mm"], 0.6)
        self.assertAlmostEqual(h[dt.datetime(2026, 10, 5, 1, 0)]["pluja_mm"], 0.3)


if __name__ == "__main__":
    unittest.main()
