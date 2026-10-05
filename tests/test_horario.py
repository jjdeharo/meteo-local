# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas del horario de actualización y del modo aviso (sin red)."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402
import prevision as P  # noqa: E402
import que_toca as Q  # noqa: E402


def datos(horari):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump({"generat": dt.datetime.now().isoformat(), "horari": horari}, f)
    f.close()
    return f.name


class QueToca(unittest.TestCase):
    def test_horario_normal(self):
        d = datos(P.horario(C.HORARIO, C.INTERVALO_MIN, []))
        c = datos(P.horario([C.HORARIO_CASA], C.INTERVALO_CASA_MIN, []))
        self.assertEqual(Q.que_toca("06:30", d, c), "completa")
        self.assertEqual(Q.que_toca("10:00", d, c), "casa")
        self.assertEqual(Q.que_toca("10:10", d, c), "")

    def test_modo_aviso_cada_10_min_con_desfase(self):
        dsf = C.MODO_AVISO_DESFASE_MIN
        d = datos(P.horario(C.HORARIO, C.INTERVALO_MIN, ["pluja al radar"]))
        c = datos(P.horario([C.HORARIO_CASA_AVISO], C.INTERVALO_CASA_MIN, ["pluja al radar"]))
        self.assertEqual(Q.que_toca(f"06:{10 + dsf:02d}", d, c), "completa")
        self.assertEqual(Q.que_toca(f"23:{50 + dsf:02d}", d, c), "casa")
        self.assertEqual(Q.que_toca(f"10:{10 + dsf:02d}", d, c), "casa")
        self.assertEqual(Q.que_toca("10:00", d, c), "" if dsf else "casa")

    def test_sin_datos_de_hoy_usa_el_horario_normal(self):
        self.assertEqual(Q.que_toca("13:00", "/no/existe", "/no/existe"), "completa")


class ModoAviso(unittest.TestCase):
    def test_sin_nada_no_hay_modo_aviso(self):
        self.assertEqual(P.motivos_modo_aviso([], [], [], {"km_lluvia": None}), [])

    def test_plan_en_emergencia(self):
        self.assertIn("pla de Protecció Civil",
                      P.motivos_modo_aviso([], [{"fase": "emergència"}], [], None))

    def test_lluvia_cerca_en_el_radar(self):
        self.assertEqual(P.motivos_modo_aviso([], [], [], {"km_lluvia": 8}), ["pluja al radar"])
        self.assertEqual(P.motivos_modo_aviso([], [], [], {"km_lluvia": 40}), [])


if __name__ == "__main__":
    unittest.main()
