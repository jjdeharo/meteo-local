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



class TemperaturaDelTram(unittest.TestCase):
    def test_mitjana_del_principi_i_del_final(self):
        # La temperatura és la d'un instant: el tram de 18 a 19, la mitjana de
        # les 18 i les 19 (abans, la de les 19).
        import config as C
        desde = dt.datetime(2026, 10, 7, 18, 3).astimezone()
        h = {"time": [f"2026-10-07T{x:02d}:00" for x in range(24)],
             "temperature_2m_meteofrance_seamless": [float(x) for x in range(24)]}
        for m in C.MODELOS_FINOS:
            h[f"precipitation_{m}"] = [0.0] * 24
        files = casa.previsio(desde, h, {}, None, [])
        self.assertEqual([(f["hora"][11:16], f["temperatura"]) for f in files[:2]],
                         [("18:00", 18.5), ("19:00", 19.5)])

    def test_acaba_el_tram_del_dia(self):
        # Juanjo, 09-10-2026: la previsió arriba a 24 hores com a mínim i fins
        # a les 21 h de demà, i acaba sempre amb un tram (matí, tarda o nit).
        import config as C
        t0 = dt.datetime(2026, 10, 9, 0)
        temps = [(t0 + dt.timedelta(hours=x)).strftime("%Y-%m-%dT%H:%M") for x in range(72)]
        h = {"time": temps, "temperature_2m_meteofrance_seamless": [15.0] * 72}
        for m in C.MODELOS_FINOS:
            h[f"precipitation_{m}"] = [0.0] * 72
        # La primera fila és l'hora en curs: a les 16.03, la de 16 a 17.
        for minut, fi, n in ((dt.datetime(2026, 10, 9, 16, 3), "2026-10-10T21:00", 29),
                             (dt.datetime(2026, 10, 9, 20, 3), "2026-10-10T21:00", 25),
                             (dt.datetime(2026, 10, 9, 21, 3), "2026-10-10T21:00", 24),
                             # La nit dura 10 hores: 9 hores més.
                             (dt.datetime(2026, 10, 9, 22, 3), "2026-10-11T07:00", 33),
                             # Al matí, demà sencer: fins a les 21 h, el màxim.
                             (dt.datetime(2026, 10, 9, 7, 3), "2026-10-10T21:00", 38),
                             (dt.datetime(2026, 10, 9, 11, 3), "2026-10-10T21:00", 34),
                             # De matinada, la nit és d'ahir: «demà» és avui.
                             (dt.datetime(2026, 10, 9, 0, 30), "2026-10-10T07:00", 31)):
            files = casa.previsio(minut.astimezone(), h, {}, None, [])
            self.assertEqual((files[-1]["fins"], len(files)), (fi, n))


class SantCugatAlPreveure(unittest.TestCase):
    def test_la_pluja_de_sant_cugat_arriba_al_model(self):
        # Auditoría del 09-10-2026: la variante con Sant Cugat se entrenaba con
        # ese dato, pero al prever no llegaba y las primeras horas usaban el
        # modelo del archivo sin decirlo.
        import config as C
        desde = dt.datetime(2026, 10, 9, 10, 3).astimezone()
        h = {"time": [f"2026-10-09T{x:02d}:00" for x in range(24)],
             "temperature_2m_meteofrance_seamless": [15.0] * 24}
        for m in C.MODELOS_FINOS:
            h[f"precipitation_{m}"] = [0.0] * 24
        riera = {"mm_1h": 3.0}
        self.assertEqual(casa.al_prever(desde, h, None, None, riera)["pluja_1h_xv"], 3.0)
        self.assertIsNone(casa.al_prever(desde, h, None, None)["pluja_1h_xv"])
        # Un modelo propio que necesita Sant Cugat: con el dato lo usa (la
        # sigmoide de 2, 0,88); sin él, cae al archivo.
        model = {"pluja": {"origen": "local", "rasgos": ["constant", "sant_cugat"], "w": [2.0, 0.0]}}
        amb = casa.previsio(desde, h, {}, None, [], model, riera=riera)
        sense = casa.previsio(desde, h, {}, None, [], model)
        self.assertAlmostEqual(amb[0]["probabilitat"], 0.88, places=2)
        self.assertNotAlmostEqual(sense[0]["probabilitat"], 0.88, places=2)
        # El registro no repite el dato en cada hora: ya va en «sant_cugat», una vez por línea.
        fila = casa.filas_registro(desde, h, {}, None, amb[:1], riera=riera)[0]
        self.assertNotIn("pluja_1h_xv", fila)


if __name__ == "__main__":
    unittest.main()
