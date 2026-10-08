# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas de la comprobación del final de la lluvia (fi_pluja.py, ADR 0049)
y de la lluvia de Montflorit cada 5 minutos (registre.py)."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fi_pluja as F  # noqa: E402
import registre as R  # noqa: E402

TZ = dt.timezone(dt.timedelta(hours=2))


def t(hhmm, dia=6):
    h, m = map(int, hhmm.split(":"))
    return dt.datetime(2026, 10, dia, h, m, tzinfo=TZ)


class CincMinuts(unittest.TestCase):
    def test_trams_complets(self):
        fila = lambda hhmm, prec: {"dt_local": f"2026-10-06T{hhmm}:00", "PREC": prec}
        filas = [fila("20:03", 1.0), fila("20:05", 1.2), fila("20:07", 1.6), fila("20:10", 2.0), fila("20:12", 2.2)]
        cincs = R.cincs_montflorit(filas)
        # El de 20:00 a 20:05 comença a les 20:03: no és complet; el de 20:10 a 20:15 tampoc.
        self.assertEqual(list(cincs), [dt.datetime(2026, 10, 6, 20, 10)])
        self.assertAlmostEqual(cincs[dt.datetime(2026, 10, 6, 20, 10)], 0.8)


class Final(unittest.TestCase):
    def test_episodis(self):
        pluja = {t("20:05"): 0.2, t("20:10"): 1.0, t("20:35"): 0.2, t("21:20"): 0.2}
        pluja.update({t("22:00"): 0.0})
        # Una pausa de 25 minuts no talla; la de 45, sí. L'últim té 40 minuts de calma després: compta.
        self.assertEqual(F.episodis(pluja), [[t("20:00"), t("20:35")], [t("21:15"), t("21:20")]])
        # Si la pluja pot continuar (no hi ha prou calma registrada després), l'últim no compta.
        self.assertEqual(F.episodis({t("20:05"): 0.2, t("20:15"): 0.0}), [])

    def test_fi_previst(self):
        prob = [1.0, 0.9, 0.5, 0.1, 0.1, 0.3, 0.1, 0.1, 0.1, 0.0]
        # Baixa del 20 % a les 20:15, però a les 20:25 torna a pujar: el final, a les 20:30.
        self.assertEqual(F.fi_previst(t("20:00"), prob, t("20:00")), t("20:30"))
        self.assertIsNone(F.fi_previst(t("20:00"), [1.0] * 25, t("20:00")))

    def test_resultat_i_avis_una_vegada(self):
        with tempfile.TemporaryDirectory() as d:
            F.DIR, F.APRENENTATGE, F.AVIS = d, d, os.path.join(d, "avis-fi-pluja")
            with open(os.path.join(d, "montflorit-5min.csv"), "w") as f:
                f.write("fins,pluja_mm\n" + "".join(f"2026-10-06T{h},{mm}\n" for h, mm in
                        (("20:05", 0.4), ("20:10", 1.0), ("20:15", 0.6), ("20:20", 0.0), ("21:00", 0.0))))
            linia = lambda hora, prob: json.dumps({"t": f"2026-10-06T{hora}+02:00", "triada": "meteocat",
                                                   "fonts": {"meteocat": {"hora": f"2026-10-06T{hora}+02:00",
                                                                          "prob": prob}}})
            with open(os.path.join(d, "radar-fonts-2026-10.jsonl"), "w") as f:
                f.write(linia("20:05", [1, 1, 1, 0, 0, 0]) + "\n" + linia("20:10", [1] * 25) + "\n")
            casos, n = F.compara(F.pluja_5min(), F.passades())
            r = F.resultat(casos, n)
            self.assertEqual((r["episodis"], r["passades"], r["amb_final"], r["encerts"], r["sense_final"]),
                             (1, 2, 1, 1, 1))
            F.MIN_EPISODIS = 2
            self.assertIsNone(F.verifica(avisa=False))
            F.MIN_EPISODIS = 1
            self.assertIn("1 episodis", F.verifica(avisa=False))
            self.assertIsNone(F.verifica(avisa=False))       # una sola vegada
            F.MIN_EPISODIS = 5


    def test_fi_radar_per_a_la_pagina(self):
        nc = {"hora": "2026-10-08T19:00+02:00",
              "llocs": {"casa": [{"min": 5 * k, "prob": p} for k, p in enumerate([1, 1, 0.9, 0.1, 0.1, 0.1, 0.0])]}}
        with tempfile.TemporaryDirectory() as d:
            F.REGLA = os.path.join(d, "fi-pluja.json")
            self.assertEqual(F.fi_radar(nc, t("19:00", 8)), {"fi": "2026-10-08T19:15+02:00", "sense_fi": False})
            # La pluja encara no ha arribat: el final es busca des que arriba.
            self.assertEqual(F.fi_radar(nc, t("18:40", 8), "2026-10-08T19:20+02:00")["fi"], "2026-10-08T19:20+02:00")
            self.assertTrue(F.fi_radar({**nc, "llocs": {"casa": [{"min": 0, "prob": 1}] * 4}}, t("19:00", 8))["sense_fi"])
            self.assertIsNone(F.fi_radar(None, t("19:00", 8)))

    def test_apren_la_variant_que_menys_s_equivoca(self):
        with tempfile.TemporaryDirectory() as d:
            F.APRENENTATGE, F.REGLA, F.ATURA = d, os.path.join(d, "fi-pluja.json"), os.path.join(d, "atura")
            # Tres episodis en què la probabilitat baixa al 25 % just quan para la pluja:
            # amb el 20 % no s'hi veu mai el final; amb el 30 %, sí.
            pluja, regs = {}, []
            for dia in (6, 7, 8):
                for m in (5, 10, 15, 20):
                    pluja[t(f"20:{m:02d}", dia)] = 0.4
                pluja[t("21:00", dia)] = 0.0
                for m in (0, 5):
                    regs.append({"t": t(f"20:{m:02d}", dia).isoformat(), "triada": "meteocat",
                                 "fonts": {"meteocat": {"hora": t("20:00", dia).isoformat(),
                                                        "prob": [1, 1, 1, 1, 0.25, 0.25, 0.25, 0.25, 0.25]}}})
            text = F.aprèn(pluja, regs, avisa=False)
            self.assertIn("menys del 30 %", text)
            self.assertEqual(F.regla()["llindar"], 0.3)
            self.assertIsNone(F.aprèn(pluja, regs, avisa=False))       # ja és la millor
            open(F.ATURA, "w").close()
            os.remove(F.REGLA)
            self.assertIsNone(F.aprèn(pluja, regs, avisa=False))       # aturat



if __name__ == "__main__":
    unittest.main()
