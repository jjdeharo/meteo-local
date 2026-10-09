# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas de la estación de casa (ADR 0017), sin red."""
import datetime as dt
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import casa  # noqa: E402
import config as C  # noqa: E402
import ecowitt as E  # noqa: E402
import registre as R  # noqa: E402

TZ = dt.timezone(dt.timedelta(hours=2))


def lectura(hhmm, pluja, temp=18.0, pressio=1010.0, dia="2026-10-05"):
    return {"t": dt.datetime.fromisoformat(f"{dia}T{hhmm}").replace(tzinfo=TZ), "pluja_avui": pluja,
            "temperatura": temp, "humitat": 90.0, "rosada": temp - 1, "pressio": pressio, "solar": 0.0}


class Ecowitt(unittest.TestCase):
    def test_hores_lluvia_y_lecturas(self):
        filas = [lectura("06:00", 0.0), lectura("06:30", 0.4), lectura("07:00", 1.0, 17.5),
                 lectura("07:30", 1.0), lectura("08:00", 1.6, 17.0)]
        h = E.hores(filas)
        siete, ocho = (dt.datetime(2026, 10, 5, x, 0, tzinfo=TZ) for x in (7, 8))
        self.assertEqual(list(h), [siete, ocho])
        self.assertAlmostEqual(h[siete]["pluja_mm"], 1.0)
        self.assertEqual(h[siete]["temperatura"], 17.5)
        self.assertAlmostEqual(h[ocho]["pluja_mm"], 0.6)
        # La primera hora, cortada, no cuenta: guardada encima de la buena,
        # apuntaba la lluvia de unos minutos (06-10-2026, ADR 0017).
        tallades = [lectura("20:55", 2.2), lectura("21:00", 3.5), lectura("21:30", 8.3), lectura("22:00", 8.9)]
        h = E.hores(tallades)
        self.assertEqual(list(h), [dt.datetime(2026, 10, 5, 22, 0, tzinfo=TZ)])
        self.assertAlmostEqual(h[dt.datetime(2026, 10, 5, 22, 0, tzinfo=TZ)]["pluja_mm"], 5.4)

    def test_medianoche_y_presion(self):
        filas = [lectura("23:30", 5.0, dia="2026-10-04"), lectura("00:00", 5.2, dia="2026-10-05"),
                 lectura("00:05", 0.1, dia="2026-10-05")]
        ini = dt.datetime(2026, 10, 4, 23, 0, tzinfo=TZ)
        self.assertAlmostEqual(E.pluja_entre(filas, ini, ini + dt.timedelta(hours=2)), 0.3)
        p = [lectura("09:00", 0, pressio=1012.0), lectura("12:00", 0, pressio=1009.5)]
        self.assertEqual(E.tendencia_pressio(p, p[1]["t"]), -2.5)

    def test_solo_cuenta_si_marca_lluvia(self):
        seco = {"plou": False, "hora": "2026-10-05T07:00+02:00"}
        self.assertIsNone(E.observacio(seco, "Casa"))
        mojado = {"plou": True, "hora": "2026-10-05T07:00+02:00", "pluja_avui": 3.0,
                  "pluja_30min": 1.2, "intensitat": 4.0}
        self.assertEqual(E.observacio(mojado, "Casa")["mm_ultima_media_hora"], 1.2)

    def test_sin_claves_no_esta_disponible(self):
        with mock.patch.dict(os.environ, {"HOME": tempfile.mkdtemp()}, clear=True):
            self.assertFalse(E.disponible())


class Casa(unittest.TestCase):
    def test_llueve_ahora_solo_si_casa_marca(self):
        # Només el pluviòmetre de casa, i només el sí (ADR 0017 i 0058).
        self.assertFalse(casa.llueve_ahora_en({"plou": False, "intensitat": 0.8}))
        self.assertTrue(casa.llueve_ahora_en({"plou": True}))
        self.assertFalse(casa.llueve_ahora_en(None))

    def test_error_del_modelo_al_prever(self):
        h = {"time": ["2026-10-05T10:00", "2026-10-05T11:00"],
             "temperature_2m_meteofrance_seamless": [18.0, 20.0]}
        est = {"hora": "2026-10-05T10:30+02:00", "temperatura": 17.0, "rosada": 15.5, "pluja_1h": 0.4}
        d = casa.al_prever(None, h, est)
        self.assertEqual(d["error_temp_ara"], 2.0)      # 19,0 del modelo a las 10:30 - 17,0
        self.assertEqual(d["deficit_rosada_ara"], 1.5)
        self.assertEqual(d["pluja_1h_emes"], 0.4)       # la lluvia de la última hora en casa
        self.assertIsNone(casa.al_prever(None, h, None)["error_temp_ara"])
        self.assertIsNone(casa.al_prever(None, h, None)["pluja_1h_emes"])


class Registre(unittest.TestCase):
    def test_apunta_y_sobrescribe_horas(self):
        R.ESTACIO_CASA = os.path.join(tempfile.mkdtemp(), "estacio-casa.csv")
        R.DIR = os.path.dirname(R.ESTACIO_CASA)
        siete = dt.datetime(2026, 10, 5, 7, 0, tzinfo=TZ)
        R.apunta_estacio_casa({siete: {"pluja_mm": 0.0, "temperatura": 17.0}})
        R.apunta_estacio_casa({siete: {"pluja_mm": 0.4, "temperatura": 17.2},
                               siete + dt.timedelta(hours=1): {"pluja_mm": None, "temperatura": None}})
        with open(R.ESTACIO_CASA) as f:
            lineas = f.read().splitlines()
        self.assertEqual(lineas[0], ",".join(R.CAMPOS_ESTACIO_CASA))
        self.assertEqual(len(lineas), 2)                 # la hora vacía no se guarda
        self.assertTrue(lineas[1].startswith("2026-10-05T07:00,0.4,17.2"))



class PressioNivellMar(unittest.TestCase):
    def test_reduccio(self):
        # 07-10-2026, 18:30: la estación marcaba 1002,1 hPa a 23 °C; Open-Meteo
        # daba 1010,2 al nivel del mar y el METAR de Sabadell, QNH 1011.
        self.assertEqual(E.pressio_mar(1002.1, 23.0, 70), 1010.2)
        self.assertEqual(E.pressio_mar(1002.1, 23.0), 1010.2)      # config.ALTITUD_CASA_M
        self.assertEqual(E.pressio_mar(1002.1, None, 70), 1010.4)  # sin temperatura, 15 °C
        self.assertIsNone(E.pressio_mar(None, 20.0))
        self.assertEqual(E.pressio_mar(1000.0, 20.0, 0), 1000.0)

if __name__ == "__main__":
    unittest.main()
