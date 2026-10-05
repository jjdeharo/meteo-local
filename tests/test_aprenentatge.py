# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas del aprendizaje de la página de casa (sin red ni Telegram)."""
import datetime as dt
import json
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aprenentatge as A  # noqa: E402
import config as C  # noqa: E402


def hora(fins, mm=0.0, temp=20.0, antelacio=3.0):
    d = {"fins": fins, "antelacio_h": antelacio, "prob_ens": 0.1, "temperature_2m": temp,
         "relative_humidity_2m": 80, "cloud_cover": 50, "wind_speed_10m": 10}
    d.update({f"pluja_{m}": mm for m in C.MODELOS_FINOS})
    return d


class Rasgos(unittest.TestCase):
    def test_vector_y_persistencia(self):
        d = {**hora("2026-10-05T18:00", mm=1.0), "pluja_1h_emes": 2.0}
        x = A.rasgos(d, A.RASGOS_PROPIS)
        self.assertEqual(len(x), len(A.RASGOS_PROPIS))
        self.assertAlmostEqual(x[A.RASGOS_PROPIS.index("persistencia")], 1.0986, places=3)
        # Lejos en el tiempo, la lluvia medida al prever ya no cuenta.
        lejos = A.rasgos({**d, "antelacio_h": 10}, A.RASGOS_PROPIS)
        self.assertEqual(lejos[A.RASGOS_PROPIS.index("persistencia")], 0.0)
        # Falta un modelo: no hay vector.
        self.assertIsNone(A.rasgos({**d, "pluja_icon_eu": None}, A.RASGOS_PROPIS))

    def test_modelo_del_archivo(self):
        # Más lluvia prevista, más probabilidad; sin modelo, None.
        m = {"pluja": A.modelo_arxiu(), "temperatura": None}
        seco, mojado = (A.prob_pluja(m, hora("2026-10-05T18:00", mm=x)) for x in (0.0, 3.0))
        self.assertLess(seco, 0.05)
        self.assertGreater(mojado, 0.5)
        self.assertIsNone(A.prob_pluja({"pluja": None}, hora("2026-10-05T18:00")))
        self.assertEqual(A.temperatura(m, hora("2026-10-05T18:00", temp=21.5)), 21.5)


class Diari(unittest.TestCase):
    """Registro sintético: el modelo da siempre dos grados de más."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        A.REGISTRE = os.path.join(self.dir, "registre")
        A.DIR = os.path.join(self.dir, "aprenentatge")
        A.MODEL, A.PROPOSAT = os.path.join(A.DIR, "model.json"), os.path.join(A.DIR, "proposat.json")
        A.ATURA, A.HISTORIAL = os.path.join(A.DIR, "atura"), os.path.join(A.DIR, "historial.csv")
        os.makedirs(A.REGISTRE)

    def registra(self, dias, error=2.0):
        rnd = random.Random(1)
        obs = ["fins,pluja_mm,temperatura,humitat,lectures"]
        inici = dt.datetime(2026, 9, 1)
        with open(os.path.join(A.REGISTRE, "casa-2026-09.jsonl"), "w") as f:
            for k in range(dias * 24):
                t = inici + dt.timedelta(hours=k)
                real = 15 + 8 * rnd.random()
                fins = (t + dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
                obs.append(f"{fins},0.0,{real:.1f},80,45")
                linea = {"emes": t.strftime("%Y-%m-%dT%H:%M") + "+02:00", "ara": {"pluja_1h": 0},
                         "hores": [hora(fins, temp=round(real + error, 1), antelacio=1)]}
                f.write(json.dumps(linea) + "\n")
        with open(os.path.join(A.REGISTRE, "montflorit.csv"), "w") as f:
            f.write("\n".join(obs) + "\n")

    def test_propone_avisa_y_aplica_al_dia_siguiente(self):
        self.registra(20)
        A.diari("2026-09-21", avisa=False)
        self.assertTrue(os.path.exists(A.PROPOSAT))
        self.assertIsNone(A.carrega()["temperatura"])      # aún no se aplica
        A.diari("2026-09-22", avisa=False)
        m = A.carrega()
        self.assertEqual(m["temperatura"]["origen"], "montflorit")
        self.assertAlmostEqual(A.temperatura(m, hora("2026-09-10T12:00", temp=22.0)), 20.0, delta=0.3)
        # La lluvia sigue con el archivo: no hay horas de lluvia propias.
        self.assertEqual(m["pluja"]["origen"], "arxiu")

    def test_atura(self):
        self.registra(20)
        A.diari("2026-09-21", avisa=False)
        os.makedirs(A.DIR, exist_ok=True)
        open(A.ATURA, "w").close()
        A.diari("2026-09-22", avisa=False)
        self.assertIsNone(A.carrega()["temperatura"])

    def test_pocos_dias_o_sin_mejora_no_cambia(self):
        self.registra(5)
        A.diari("2026-09-06", avisa=False)
        self.assertFalse(os.path.exists(A.PROPOSAT))
        self.registra(20, error=0.0)
        A.diari("2026-09-21", avisa=False)
        self.assertFalse(os.path.exists(A.PROPOSAT))


if __name__ == "__main__":
    unittest.main()
