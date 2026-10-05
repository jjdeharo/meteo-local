# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas de la regla de decisión con datos inventados (sin red)."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import prevision as P  # noqa: E402

MANANA = (P.AHORA.date() + dt.timedelta(days=1)).isoformat()


def modelos(mm, horas_lluvia=(8, 16)):
    horas = [f"{MANANA}T{h:02d}:00" for h in range(24)]
    serie = [mm if h in horas_lluvia else 0.0 for h in range(24)]
    return [{"hourly": {"time": horas, **{f"precipitation_{m}": serie for m in P.C.MODELOS_FINOS}}}]


def ensemble(mojados, total=40):
    horas = [f"{MANANA}T{h:02d}:00" for h in range(24)]
    e = {"time": horas}
    for i in range(total):
        e[f"precipitation_member{i:02d}"] = [1.0 if i < mojados and h == 8 else 0.0 for h in range(24)]
    return e


def aviso(zona):
    return {"zona": zona, "tipo": "tempestes", "nivel": "groc",
            "inicio": f"{MANANA}T05:00:00+02:00", "fin": f"{MANANA}T19:59:59+02:00"}


class Decision(unittest.TestCase):
    def ida(self, **d):
        return P.decidir(MANANA, P.C.IDA, d)

    def test_todo_seco_es_moto(self):
        r = self.ida(avisos=[], modelos=modelos(0), ensemble=ensemble(0))
        self.assertEqual(r["nivell"], "moto")

    def test_aviso_en_el_valles_es_coche(self):
        r = self.ida(avisos=[aviso(P.C.ZONA_TRAYECTO)], modelos=modelos(0), ensemble=ensemble(0))
        self.assertEqual(r["nivell"], "cotxe")
        self.assertIn("20:00", r["motius"][0]["text"])

    def test_aviso_solo_en_la_costa_es_atencion(self):
        r = self.ida(avisos=[aviso(P.C.ZONA_CERCANA)], modelos=modelos(0), ensemble=ensemble(0))
        self.assertEqual(r["nivell"], "compte")

    def test_lluvia_clara_en_modelos_es_coche(self):
        r = self.ida(avisos=[], modelos=modelos(1.5), ensemble=ensemble(0))
        self.assertEqual(r["nivell"], "cotxe")

    def test_probabilidad_media_es_atencion(self):
        r = self.ida(avisos=[], modelos=modelos(0), ensemble=ensemble(16))
        self.assertEqual(r["nivell"], "compte")

    def test_probabilidad_alta_es_coche(self):
        r = self.ida(avisos=[], modelos=modelos(0), ensemble=ensemble(20))
        self.assertEqual(r["nivell"], "cotxe")

    def test_sin_datos_es_atencion(self):
        self.assertEqual(self.ida()["nivell"], "compte")

    def test_ventana_cuenta_la_hora_siguiente(self):
        # La lluvia de 6:30 a 7:30 está en los acumulados que acaban a las 7 y a las 8.
        self.assertEqual(P.horas_ventana(("06:30", "07:30")), [7, 8])
        self.assertEqual(P.horas_ventana(("15:00", "15:30")), [16])


class Historico(unittest.TestCase):
    def test_el_motivo_de_los_modelos_da_la_frecuencia_real(self):
        if not P.CALIBRACION:
            self.skipTest("sin calibracio/calibracio.json")
        r = P.decidir(MANANA, P.C.IDA, {"modelos": modelos(0)})
        texto = r["motius"][0]["text"]
        self.assertIn("Des del 2024", texto)
        self.assertIn("de cada", texto)


class UnSoloMedio(unittest.TestCase):
    """Quien va en moto vuelve en moto: un medio para todo el día."""

    def setUp(self):
        self.ahora = P.AHORA

    def tearDown(self):
        P.AHORA = self.ahora

    def a_las(self, hhmm):
        P.AHORA = P.momento(MANANA, hhmm)

    def test_manda_el_trayecto_peor(self):
        self.a_las("05:30")
        r = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(1.5, (16,)),
                                   "ensemble": ensemble(0)})
        self.assertEqual(r["anada"]["nivell"], "moto")
        self.assertEqual(r["tornada"]["nivell"], "cotxe")
        self.assertEqual(r["decisio"]["mitja"], "cotxe")

    def test_antes_de_salir_se_recalcula(self):
        self.a_las("06:00")
        anterior = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(0)})
        r = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(1.5)}, anterior)
        self.assertEqual(r["decisio"]["mitja"], "cotxe")

    def test_despues_de_salir_se_mantiene_y_avisa(self):
        self.a_las("06:00")
        anterior = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(0)})
        self.assertEqual(anterior["decisio"]["mitja"], "moto")
        self.a_las("13:00")
        r = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(1.5)}, anterior)
        self.assertEqual(r["decisio"]["mitja"], "moto")
        self.assertTrue(r["decisio"]["mantinguda"])
        self.assertIn("impermeable", r["avis_tornada"])

    def test_sin_decision_previa_se_decide_al_momento(self):
        self.a_las("08:00")
        r = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(0)}, None)
        self.assertFalse(r["decisio"]["abans_de_sortir"])
        self.assertIsNone(r["avis_tornada"])

    def test_decision_de_otro_dia_no_cuenta(self):
        self.a_las("06:00")
        anterior = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(1.5)})
        anterior["dia"] = "2000-01-01"
        self.a_las("13:00")
        r = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(0)}, anterior)
        self.assertEqual(r["decisio"]["mitja"], "moto")


if __name__ == "__main__":
    unittest.main()
