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


def hora(fins, mm=0.0, temp=20.0, antelacio=3.0, error_ara=1.0):
    d = {"fins": fins, "antelacio_h": antelacio, "prob_ens": 0.1, "temperature_2m": temp,
         "relative_humidity_2m": 80, "cloud_cover": 50, "wind_speed_10m": 10,
         "shortwave_radiation": 300, "error_temp_ara": error_ara, "deficit_rosada_ara": 2.0}
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
        # Aire seco al prever: cuenta en las primeras horas; sin dato, no hay vector.
        self.assertAlmostEqual(x[A.RASGOS_PROPIS.index("sequedat")], 0.2)
        self.assertEqual(lejos[A.RASGOS_PROPIS.index("sequedat")], 0.0)
        self.assertIsNone(A.rasgos({**d, "deficit_rosada_ara": None}, A.RASGOS_PROPIS))
        # La lluvia de Sant Cugat al prever, como la persistencia; sin dato, no hay vector (ADR 0042).
        xv = A.rasgos({**d, "pluja_1h_xv": 2.0}, A.RASGOS_PROPIS_XV)
        self.assertAlmostEqual(xv[A.RASGOS_PROPIS_XV.index("sant_cugat")], 1.0986, places=3)
        self.assertEqual(A.rasgos({**d, "pluja_1h_xv": 2.0, "antelacio_h": 10}, A.RASGOS_PROPIS_XV)[-1], 0.0)
        self.assertIsNone(A.rasgos(d, A.RASGOS_PROPIS_XV))
        self.assertIsNotNone(A.rasgos(d, A.RASGOS_PROPIS))     # sin el rasgo, el vector de siempre
        # Lo oficial de la hora (ADR 0047): sin dato, no hay vector de esa variante.
        av = A.rasgos({**d, "avis_pluja": 1.0, "pla_inuncat": 0.0}, A.RASGOS_PROPIS_AVIS)
        self.assertEqual(av[-2:], [1.0, 0.0])
        self.assertIsNone(A.rasgos(d, A.RASGOS_PROPIS_AVIS))

    def test_modelos_que_dan_lluvia_y_coinciden(self):
        # ADR 0021: que un modelo dé algo de lluvia cuenta por sí mismo, y
        # también cuántos coinciden.
        d = hora("2026-10-05T18:00", antelacio=12)
        d.update(pluja_meteofrance_arome_france_hd=0.0, pluja_meteofrance_arome_france=0.1,
                 pluja_icon_eu=0.3)
        x = dict(zip(A.RASGOS_ARXIU, A.rasgos(d, A.RASGOS_ARXIU)))
        self.assertEqual([x["plou_arome_hd"], x["plou_arome"], x["plou_icon_eu"]], [0.0, 1.0, 1.0])
        self.assertEqual([x["dos_models"], x["tres_models"]], [1.0, 0.0])
        self.assertAlmostEqual(x["icon_eu_antelacio"], x["icon_eu"] * 0.5)
        self.assertEqual([x["algun_antelacio"], x["tres_antelacio"]], [0.5, 0.0])

    def test_un_solo_modelo_con_poca_lluvia_no_es_casi_cero(self):
        # El caso del 06-10-2026: solo ICON-EU daba 0,2 mm y la página decía
        # un 2 %; en el archivo, con solo ICON-EU dando 0,2 mm llovió una de
        # cada diez horas (729 horas). Y cuantos más coinciden, más probabilidad.
        m = {"pluja": A.modelo_arxiu()}

        def prob(hd, arome, icon):
            d = hora("2026-10-06T16:00", antelacio=3)
            d.update(pluja_meteofrance_arome_france_hd=hd, pluja_meteofrance_arome_france=arome,
                     pluja_icon_eu=icon)
            return A.prob_pluja(m, d)
        nada, uno, dos, tres = prob(0, 0, 0), prob(0, 0, 0.2), prob(0.2, 0, 0.2), prob(0.2, 0.2, 0.2)
        self.assertLess(nada, 0.02)
        self.assertGreater(uno, 0.06)
        self.assertLess(uno, 0.15)
        self.assertGreater(dos, uno)
        self.assertGreater(tres, dos)

    def test_fiabilidad_del_modelo_del_archivo(self):
        # La comprobación guardada con el modelo: en cada tramo de
        # probabilidad con bastantes horas, lo dado y lo que llovió no se
        # separan más de 5 puntos, a corto plazo y un día antes.
        v = A.modelo_arxiu()["validacio"]
        for clave in ("curt_termini", "un_dia_abans"):
            self.assertLess(v[clave]["error"], 0.95 * v[clave]["error_abans"])
            for f in v[clave]["fiabilitat"]:
                if f["hores"] >= 150:
                    self.assertLess(abs(f["donada"] - f["va_ploure"]), 0.05, (clave, f))

    def test_error_al_prever_se_apaga_con_la_antelacion(self):
        i = A.RASGOS_TEMPERATURA.index("error_ara_3h")
        cerca = A.rasgos(hora("2026-10-05T18:00", antelacio=0, error_ara=2.0), A.RASGOS_TEMPERATURA)
        lejos = A.rasgos(hora("2026-10-05T18:00", antelacio=12, error_ara=2.0), A.RASGOS_TEMPERATURA)
        self.assertAlmostEqual(cerca[i], 2.0)
        self.assertLess(lejos[i], 0.05)
        self.assertGreater(lejos[i + 1], 1.0)        # la parte lenta dura más

    def test_modelo_del_archivo(self):
        # Más lluvia prevista, más probabilidad; sin modelo, None.
        m = {"pluja": A.modelo_arxiu(), "temperatura": None}
        seco, mojado = (A.prob_pluja(m, hora("2026-10-05T18:00", mm=x)) for x in (0.0, 3.0))
        self.assertLess(seco, 0.05)
        self.assertGreater(mojado, 0.5)
        self.assertIsNone(A.prob_pluja({"pluja": None}, hora("2026-10-05T18:00")))
        self.assertEqual(A.temperatura(m, hora("2026-10-05T18:00", temp=21.5)), 21.5)

    def test_temperatura_del_archivo_con_y_sin_estacion(self):
        # El modelo da más calor que la estación de casa: la corrección baja la
        # temperatura; sin la estación al prever, también, con los otros pesos.
        m = {"temperatura": A.modelo_arxiu_temperatura()}
        con = A.temperatura(m, hora("2026-10-05T14:00", temp=22.0, antelacio=1, error_ara=2.0))
        sin = A.temperatura(m, hora("2026-10-05T14:00", temp=22.0, antelacio=1, error_ara=None))
        self.assertLess(con, sin)
        self.assertLess(sin, 22.0)

    def test_modelo_propio_sin_estacion_usa_el_archivo(self):
        propio = {"origen": "local", "rasgos": A.RASGOS_PROPIS, "w": [0.0] * len(A.RASGOS_PROPIS)}
        d = hora("2026-10-05T18:00", mm=3.0, antelacio=1)
        self.assertAlmostEqual(A.prob_pluja({"pluja": propio}, d), 0.5)
        sin = A.prob_pluja({"pluja": propio}, {**d, "deficit_rosada_ara": None})
        self.assertAlmostEqual(sin, A.prob_pluja({"pluja": A.modelo_arxiu()}, d))

    def test_lluvia_observada(self):
        # Montflorit manda; casa solo suma cuando marca lluvia.
        self.assertEqual(A.pluja_observada({"pluja_mm": "0.0"}, {"pluja_mm": "0.0"}), 0.0)
        self.assertEqual(A.pluja_observada({"pluja_mm": "0.0"}, {"pluja_mm": "1.2"}), 1.2)
        self.assertEqual(A.pluja_observada(None, {"pluja_mm": "1.2"}), 1.2)
        self.assertIsNone(A.pluja_observada(None, {"pluja_mm": "0.0"}))


class Moto(unittest.TestCase):
    """La regla de lluvia de la moto de «Si surts» (ADR 0047)."""

    def test_mismos_umbrales_que_la_pagina(self):
        web = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "sortir.js")
        js = open(web, encoding="utf-8").read()
        for nom, valor in (("PROB_RISC_RODES", C.MOTO_PROB_RISC), ("PROB_PLUJA_RODES", C.MOTO_PROB_PLUJA),
                           ("MM_RISC", C.MOTO_MM_RISC), ("MM_PLUJA", C.MOTO_MM_PLUJA)):
            self.assertIn(f"const {nom} = {valor:g};", js)

    def test_el_cas_del_8_d_octubre(self):
        # A les 10 h, només l'avís; a les 17 h, ICON-EU 1,7 mm i un 25 %.
        deu, cinc = {"probabilitat": 0.0, "pluja_mm": 0.0}, {"probabilitat": 0.25, "pluja_mm": 1.7}
        self.assertEqual([A.nivell_moto(deu, True), A.nivell_moto(cinc, True)], ["compte", "compte"])
        self.assertEqual([A.nivell_moto(deu, True, abans=True), A.nivell_moto(cinc, False, abans=True)], ["no", "no"])
        self.assertEqual(A.nivell_moto({"probabilitat": 0.4, "pluja_mm": 0}, False), "no")
        self.assertEqual(A.nivell_moto({"probabilitat": 0.05, "pluja_mm": 0.5}, False), "be")
        self.assertEqual(A.nivell_moto({"probabilitat": None, "pluja_mm": 1.0}, False), "no")
        self.assertEqual(A.nivell_moto({"probabilitat": 0.0, "pluja_mm": 0, "plou_ara": True}, False), "no")


class Diari(unittest.TestCase):
    """Registro sintético: el modelo da siempre dos grados más de lo que mide
    la estación de casa."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        A.REGISTRE = os.path.join(self.dir, "registre")
        A.DIR = os.path.join(self.dir, "aprenentatge")
        A.MODEL, A.PROPOSAT = os.path.join(A.DIR, "model.json"), os.path.join(A.DIR, "proposat.json")
        A.ATURA, A.HISTORIAL = os.path.join(A.DIR, "atura"), os.path.join(A.DIR, "historial.csv")
        A.AVIS_XV = os.path.join(A.DIR, "avis-sant-cugat")
        A.MOTO, A.AVIS_MOTO = os.path.join(A.REGISTRE, "moto.csv"), os.path.join(A.DIR, "avis-moto")
        os.makedirs(A.REGISTRE)

    def registra(self, dias, error=2.0, com_arxiu=False):
        """com_arxiu: la estación mide justo lo que da la corrección del
        archivo, que entonces no se puede mejorar."""
        rnd = random.Random(1)
        mont = ["fins,pluja_mm,temperatura,humitat,lectures"]
        casa = ["fins,pluja_mm,temperatura,humitat,rosada,pressio,solar"]
        arxiu_t = {"temperatura": A.modelo_arxiu_temperatura()}
        inici = dt.datetime(2026, 9, 1)
        with open(os.path.join(A.REGISTRE, "casa-2026-09.jsonl"), "w") as f:
            for k in range(dias * 24):
                t = inici + dt.timedelta(hours=k)
                real = 15 + 8 * rnd.random()
                fins = (t + dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
                h = hora(fins, temp=round(real + error, 1), antelacio=1, error_ara=error)
                if com_arxiu:
                    real = A.temperatura(arxiu_t, h)
                mont.append(f"{fins},0.0,,80,45")
                casa.append(f"{fins},0.0,{real:.3f},80,15,1013,0")
                linea = {"emes": t.strftime("%Y-%m-%dT%H:%M") + "+02:00", "ara": {"pluja_1h": 0},
                         "ara_casa": {"pluja_1h": 0}, "hores": [h], "sant_cugat": {"pluja_1h": 0.0} if k % 2 else None}
                f.write(json.dumps(linea) + "\n")
        for nom, filas in (("montflorit.csv", mont), ("estacio-casa.csv", casa)):
            with open(os.path.join(A.REGISTRE, nom), "w") as f:
                f.write("\n".join(filas) + "\n")

    def test_horas_de_lluvia_unicas_y_grupos_por_hora_observada(self):
        # Auditoría del 08-10-2026: dos horas con lluvia previstas 24 veces contaban 48.
        ms = []
        for d in (dt.datetime(2026, 9, 7, 18), dt.datetime(2026, 9, 14, 18)):
            for k in range(24):
                for plou in (True, False):
                    fins = d + dt.timedelta(hours=0 if plou else 1)
                    ms.append({**hora(fins.isoformat(timespec="minutes"), mm=2 if plou else 0, antelacio=k + 1),
                               "emes": (fins - dt.timedelta(hours=k + 1)).isoformat(timespec="minutes") + "+02:00",
                               "obs_pluja": 2 if plou else 0, "obs_temp": None, "pluja_1h_emes": 0})
        v = A.valida_pluja(ms, A.modelo_arxiu())
        self.assertEqual(v["hores_pluja"], 2)
        self.assertEqual(v["mostres"], 96)
        # La misma hora observada, emitida el domingo o el lunes: mismo grupo.
        g = [A.grupo_semana({"emes": e, "fins": "2026-10-12T01:00"}) for e in ("2026-10-11T23:00+02:00", "2026-10-12T00:00+02:00")]
        self.assertEqual(g[0], g[1])

    def test_sant_cugat_entra_en_las_muestras_y_se_valida_aparte(self):
        self.registra(20)
        ms = A.mostres()
        self.assertEqual({m["pluja_1h_xv"] for m in ms}, {0.0, None})
        vp = A.valida_pluja(ms, A.modelo_arxiu(), A.RASGOS_PROPIS_XV)
        self.assertEqual(vp["rasgos"], A.RASGOS_PROPIS_XV)
        self.assertEqual(vp["mostres"], len([m for m in ms if m["pluja_1h_xv"] is not None]))
        # El aviso de una vez: solo con bastante lluvia, y deja huella para no repetirse.
        self.assertIsNone(A.avis_sant_cugat({"error": 0.1, "error_abans": 0.12, "xv": {**vp, "hores_pluja": 5}}))
        text = A.avis_sant_cugat({"error": 0.1, "error_abans": 0.12, "xv": {**vp, "hores_pluja": 30, "error": 0.09}})
        self.assertIn("30 hores de pluja amb la dada de Sant Cugat", text)
        self.assertIn("Ajuda", text)
        self.assertTrue(os.path.exists(A.AVIS_XV))
        self.assertIsNone(A.avis_sant_cugat({"error": 0.1, "error_abans": 0.12, "xv": {**vp, "hores_pluja": 30, "error": 0.09}}))
        os.remove(A.AVIS_XV)
        self.assertIn("No ajuda", A.avis_sant_cugat({"error": 0.1, "error_abans": 0.12, "xv": {**vp, "hores_pluja": 30, "error": 0.11}}))

    def test_verifica_la_moto_una_vez_por_hora(self):
        # Cada hora, previsiones de 1 a 9 horas antes; llueve de 12 a 13 h.
        mont = ["fins,pluja_mm,temperatura,humitat,lectures"]
        with open(os.path.join(A.REGISTRE, "casa-2026-10.jsonl"), "w") as f:
            for k in range(30):
                emes = dt.datetime(2026, 10, 8, 0) + dt.timedelta(hours=k)
                hores = []
                for ant in range(1, 10):
                    fins = (emes + dt.timedelta(hours=ant)).strftime("%Y-%m-%dT%H:%M")
                    hores.append({**hora(fins, antelacio=ant - 0.05), "avis_pluja": 1.0 if ant > 5 else 0.0,
                                  "mostrat": {"probabilitat": 0.15, "pluja_mm": 0.0}})
                f.write(json.dumps({"emes": emes.strftime("%Y-%m-%dT%H:%M") + "+02:00", "hores": hores}) + "\n")
                fins = (emes + dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
                mont.append(f"{fins},{1.5 if fins.endswith('13:00') else 0.0},18,80,45")
        with open(os.path.join(A.REGISTRE, "montflorit.csv"), "w") as f:
            f.write("\n".join(mont) + "\n")
        ara = dt.datetime(2026, 10, 9, 0).astimezone()
        n = A.verifica_moto(ara)
        self.assertEqual(n, 16 + 16)               # de 7 a 22 h, al sortir i la tornada
        self.assertEqual(A.verifica_moto(ara), 0)  # no es repeteix
        r = A.resum_moto()
        self.assertEqual(r["sortida"]["hores_pluja"], 1)
        # Amb un 15 % i sense l'avís (al sortir), «compte»; la regla d'abans, «bé».
        self.assertEqual(r["sortida"]["nivell"]["pluja"]["compte"], 1)
        self.assertEqual(r["sortida"]["nivell_abans"]["pluja"]["be"], 1)
        # La tornada porta l'avís: abans era «no» cada hora seca, ara «compte».
        self.assertEqual(r["tornada"]["nivell_abans"]["sec"]["no"], 15)
        self.assertEqual(r["tornada"]["nivell"]["sec"]["no"], 0)
        self.assertIn("Encara hi ha massa poca pluja", A.text_resum_moto(r))
        # El resum per Telegram, només amb prou dies i una sola vegada.
        self.assertIsNone(A.avis_moto(avisa=False))
        A.DIES_RESUM_MOTO = 1
        try:
            self.assertIn("Si surts, pluja en moto", A.avis_moto(avisa=False))
            self.assertIsNone(A.avis_moto(avisa=False))
        finally:
            A.DIES_RESUM_MOTO = 28

    def test_propone_avisa_y_aplica_al_dia_siguiente(self):
        self.registra(20)
        A.diari("2026-09-21", avisa=False)
        self.assertTrue(os.path.exists(A.PROPOSAT))
        self.assertEqual(A.carrega()["temperatura"]["origen"], "arxiu")      # aún no se aplica
        A.diari("2026-09-22", avisa=False)
        m = A.carrega()
        self.assertEqual(m["temperatura"]["origen"], "casa")
        self.assertAlmostEqual(A.temperatura(m, hora("2026-09-10T12:00", temp=22.0, antelacio=1, error_ara=2.0)),
                               20.0, delta=0.3)
        # La lluvia sigue con el archivo: no hay horas de lluvia propias.
        self.assertEqual(m["pluja"]["origen"], "arxiu")

    def test_atura(self):
        self.registra(20)
        A.diari("2026-09-21", avisa=False)
        os.makedirs(A.DIR, exist_ok=True)
        open(A.ATURA, "w").close()
        A.diari("2026-09-22", avisa=False)
        self.assertEqual(A.carrega()["temperatura"]["origen"], "arxiu")

    def test_pocos_dias_o_sin_mejora_no_cambia(self):
        self.registra(5)
        A.diari("2026-09-06", avisa=False)
        self.assertFalse(os.path.exists(A.PROPOSAT))
        self.registra(20, com_arxiu=True)
        A.diari("2026-09-21", avisa=False)
        self.assertFalse(os.path.exists(A.PROPOSAT))


if __name__ == "__main__":
    unittest.main()
