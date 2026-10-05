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
        detalle = r["motius"][0]["detall"]
        self.assertIn("Des del 2024", detalle)
        self.assertIn("de cada", detalle)


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

    def test_si_llueve_en_montflorit_es_coche(self):
        hora_salida = P.momento(MANANA, P.C.IDA[0])
        ahora = P.AHORA
        try:
            P.AHORA = hora_salida - dt.timedelta(minutes=20)
            obs = [{"estacion": "Cerdanyola (Montflorit)", "mm_ultima_media_hora": 4.0,
                    "intensitat": 40.4, "hasta": P.AHORA.isoformat()}]
            r = P.decidir(MANANA, P.C.IDA, {"observaciones": obs})
        finally:
            P.AHORA = ahora
        self.assertEqual(r["nivell"], "cotxe")
        self.assertIn("Plou a Cerdanyola (Montflorit), 40,4\u00a0mm/h a les", r["motius"][0]["text"])


class TiempoDeLaVuelta(unittest.TestCase):
    def test_temperatura_y_rachas_de_la_ventana(self):
        horas = [f"{MANANA}T{h:02d}:00" for h in range(24)]
        hourly = {"time": horas}
        for m in P.C.MODELOS_FINOS:
            hourly[f"temperature_2m_{m}"] = [10.0 + h for h in range(24)]
            hourly[f"wind_gusts_10m_{m}"] = [5.0 * (h == 16) for h in range(24)]
        t = P.tiempo_ventana(MANANA, P.C.VUELTA, [{"hourly": hourly}])
        self.assertEqual((t["temp_min"], t["temp_max"], t["ratxa_max"]), (25, 26, 5))


class ProteccionCivil(unittest.TestCase):
    def plan(self, fase):
        return {"pla": "INUNCAT", "nom": "d'inundacions", "fase": fase}

    def test_emergencia_es_coche(self):
        r = P.decidir(MANANA, P.C.IDA, {"planes": [self.plan("emergència")], "modelos": modelos(0)})
        self.assertEqual(r["nivell"], "cotxe")
        self.assertIn("INUNCAT", r["motius"][0]["text"])

    def test_prealerta_no_cambia_el_riesgo(self):
        r = P.decidir(MANANA, P.C.IDA, {"planes": [self.plan("prealerta")], "modelos": modelos(0)})
        self.assertEqual(r["nivell"], "moto")

    def test_un_plan_de_otra_zona_no_cuenta(self):
        self.assertFalse(P.afecta_al_trayecto("CHE. Vigilància per previsió meteorològica adversa conca de l'Ebre - "))
        self.assertTrue(P.afecta_al_trayecto("Emergència INUNCAT 3-5 Octubre"))
        self.assertTrue(P.afecta_al_trayecto("Pluges intenses a Girona i al Vallès"))


class Agente(unittest.TestCase):
    def setUp(self):
        self.ahora = P.AHORA
        P.AHORA = P.momento(MANANA, "06:10")

    def tearDown(self):
        P.AHORA = self.ahora

    def comentario(self, mitja, anada="moto", tornada="moto", mode="mati"):
        return {"dia": MANANA, "mode": mode, "text": "Prova.", "mitja": mitja,
                "nivells_programa": {"anada": anada, "tornada": tornada}}

    def test_puede_hacerla_mas_prudente(self):
        r = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(0)}, None, self.comentario("cotxe"))
        self.assertEqual(r["decisio"]["mitja"], "cotxe")
        self.assertTrue(r["decisio"]["per_la_ia"])
        self.assertTrue(r["comentari"]["vigent"])

    def test_no_puede_hacerla_menos_prudente(self):
        c = self.comentario("moto", "cotxe", "cotxe")
        r = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(1.5)}, None, c)
        self.assertEqual(r["decisio"]["mitja"], "cotxe")
        self.assertNotIn("per_la_ia", r["decisio"])

    def test_caduca_si_cambian_los_niveles(self):
        c = self.comentario("cotxe", "moto", "moto")
        r = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(0.5)}, None, c)
        self.assertFalse(r["comentari"]["vigent"])
        self.assertEqual(r["decisio"]["mitja"], "compte")


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

    def test_despues_de_salir_se_mantiene(self):
        self.a_las("06:00")
        anterior = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(0)})
        self.assertEqual(anterior["decisio"]["mitja"], "moto")
        self.a_las("13:00")
        r = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(1.5)}, anterior)
        self.assertEqual(r["decisio"]["mitja"], "moto")
        self.assertTrue(r["decisio"]["mantinguda"])
        # La vuelta se sigue actualizando, aunque ya no cambie el medio.
        self.assertEqual(r["tornada"]["nivell"], "cotxe")

    def test_dentro_de_la_ventana_de_ida_aun_se_recalcula(self):
        self.a_las("06:00")
        anterior = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(0)})
        self.a_las("07:10")
        r = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(1.5)}, anterior)
        self.assertEqual(r["decisio"]["mitja"], "cotxe")
        self.assertFalse(r["decisio"]["mantinguda"])

    def test_la_pasada_de_las_730_aun_recalcula(self):
        self.a_las("06:00")
        anterior = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(0)})
        P.AHORA = P.momento(MANANA, "07:30") + dt.timedelta(seconds=13)
        r = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(1.5)}, anterior)
        self.assertFalse(r["decisio"]["mantinguda"])
        self.assertEqual(r["decisio"]["mitja"], "cotxe")

    def test_sin_decision_previa_se_decide_al_momento(self):
        self.a_las("08:00")
        r = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(0)}, None)
        self.assertFalse(r["decisio"]["abans_de_sortir"])

    def test_decision_de_otro_dia_no_cuenta(self):
        self.a_las("06:00")
        anterior = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(1.5)})
        anterior["dia"] = "2000-01-01"
        self.a_las("13:00")
        r = P.decidir_dia(MANANA, {"avisos": [], "modelos": modelos(0)}, anterior)
        self.assertEqual(r["decisio"]["mitja"], "moto")


if __name__ == "__main__":
    unittest.main()


class Roba(unittest.TestCase):
    def tram(self, tmin, tmax):
        return {"temps": {"temp_min": tmin, "temp_max": tmax, "ratxa_max": 20}}

    def test_sensacion_a_45_kmh(self):
        self.assertAlmostEqual(P.sensacion(10), 5.7, places=1)
        self.assertAlmostEqual(P.sensacion(5), -1.0, places=1)
        # Por encima de 10 °C el índice no vale: la temperatura del aire.
        self.assertEqual(P.sensacion(12), 12)

    def test_frio_con_sensacion(self):
        r = P.roba("moto", self.tram(5, 7), self.tram(8, 9))
        self.assertIn("Roba d'hivern", r["text"])
        self.assertIn("5\u00a0°C es noten com \u22121\u00a0°C", r["text"])
        self.assertEqual((r["peca"], r["pluja"]), ("jaqueta", None))

    def test_lluvia_capas_y_coche(self):
        r = P.roba("compte", self.tram(12, 14), self.tram(20, 22))
        self.assertTrue(r["text"].startswith("Impermeable"))
        self.assertIn("capes", r["text"])
        self.assertEqual(r["pluja"], "impermeable")
        self.assertEqual(P.roba("cotxe", self.tram(20, 21), self.tram(22, 23)),
                         {"text": "Jaqueta lleugera o jersei i paraigua.", "peca": "jaqueta",
                          "pluja": "paraigua"})
        self.assertEqual(P.roba("cotxe", self.tram(25, 26), self.tram(27, 28))["peca"], "samarreta")
        self.assertIsNone(P.roba("moto", {"temps": None}, {"temps": None}))
