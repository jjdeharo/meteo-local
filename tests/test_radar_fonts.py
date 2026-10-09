# SPDX-License-Identifier: AGPL-3.0-or-later
"""Qué radar se usa y cómo se elige con lo que acierta cada uno (ADR 0026)."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import nowcast as N  # noqa: E402
import radar_fonts as RF  # noqa: E402

T0 = dt.datetime(2026, 10, 6, 19, 0).astimezone()


def r_amb(retard_mc, retard_rv=0):
    camp = np.zeros((N.MIDA, N.MIDA))
    return {"meteocat": {"hora": T0 - dt.timedelta(minutes=retard_mc), "mm_h": camp},
            "rainviewer": {"hores": [T0 - dt.timedelta(minutes=retard_rv)], "mm_h": [camp]}}


class Imatge(unittest.TestCase):
    def test_amb_rainviewer_preferit_n_hi_ha_prou_amb_10_minuts(self):
        self.assertEqual(N.imatge(r_amb(10), "rainviewer")[2], "rainviewer")
        self.assertEqual(N.imatge(r_amb(8), "rainviewer")[2], "meteocat")

    def test_amb_meteocat_preferit_la_regla_d_abans(self):
        self.assertEqual(N.imatge(r_amb(14), "meteocat")[2], "meteocat")
        self.assertEqual(N.imatge(r_amb(16), "meteocat")[2], "rainviewer")

    def test_preferida_del_fitxer(self):
        vell = N.FONT_PREFERIDA
        N.FONT_PREFERIDA = os.path.join(tempfile.mkdtemp(), "radar-font.json")
        try:
            self.assertEqual(N.font_preferida(), N.FONT_PER_DEFECTE)
            with open(N.FONT_PREFERIDA, "w") as f:
                json.dump({"preferida": "meteocat"}, f)
            self.assertEqual(N.font_preferida(), "meteocat")
            self.assertEqual(N.imatge(r_amb(12))[2], "meteocat")
        finally:
            N.FONT_PREFERIDA = vell


def linia(t, plou, mc=None, rv=None, retard_mc=15, retard_rv=5):
    fonts = {}
    if mc is not None:
        fonts["meteocat"] = {"hora": (t - dt.timedelta(minutes=retard_mc)).isoformat(), "prob": mc}
    if rv is not None:
        fonts["rainviewer"] = {"hora": (t - dt.timedelta(minutes=retard_rv)).isoformat(), "prob": rv}
    return {"t": t.isoformat(), "plou": plou, "triada": "meteocat", "fonts": fonts}


def episodis(encerta, dies=4, passades=12):
    """Pasadas cada 6 minutos con lluvia a partir de la mitad de cada día;
    la fuente «encerta» lo prevé y la otra no."""
    files = []
    for d in range(dies):
        for k in range(passades):
            t = T0 + dt.timedelta(days=d, minutes=6 * k)
            plou = k >= passades // 2
            bona, dolenta = [0.9] * 25, [0.1] * 25
            mc, rv = (bona, dolenta) if encerta == "meteocat" else (dolenta, bona)
            files.append(linia(t, plou, mc, rv))
    return files


class Compara(unittest.TestCase):
    def test_parelles_a_l_hora_prevista(self):
        files = [linia(T0, False, [0.0] * 25, [1.0] * 25),
                 linia(T0 + dt.timedelta(minutes=30), True)]
        ps = RF.parelles(files)
        # Una sola observación, a los 30 minutos: la hora de las dos fuentes
        # que cae ahí (Meteocat, 45 min desde su imagen; RainViewer, 35).
        self.assertEqual([(p[0], p[1], p[2]) for p in ps], [(0.0, 1.0, True)])

    def test_sense_les_dues_fonts_no_compta(self):
        self.assertEqual(RF.parelles([linia(T0, False, mc=[0.5] * 25), linia(T0 + dt.timedelta(minutes=30), True)]), [])

    def test_canvia_a_la_que_encerta_mes(self):
        c = RF.compara(episodis("meteocat"))
        self.assertGreaterEqual(c["amb_pluja"], RF.MIN_PLUJA)
        self.assertLess(c["brier_meteocat"], c["brier_rainviewer"])
        self.assertEqual(RF.decideix(c, "rainviewer"), "meteocat")
        self.assertEqual(RF.decideix(RF.compara(episodis("rainviewer")), "meteocat"), "rainviewer")

    def test_cal_millorar_un_5_per_cent(self):
        c = {"amb_pluja": 100, "dies_pluja": 5, "brier_meteocat": 0.097, "brier_rainviewer": 0.1}
        self.assertEqual(RF.decideix(c, "rainviewer"), "rainviewer")
        c["brier_meteocat"] = 0.094
        self.assertEqual(RF.decideix(c, "rainviewer"), "meteocat")

    def test_amb_pocs_casos_no_canvia(self):
        c = RF.compara(episodis("meteocat", dies=2))
        self.assertEqual(RF.decideix(c, "rainviewer"), "rainviewer")

    def test_verifica_desa_i_llegeix(self):
        dir_ = tempfile.mkdtemp()
        vell_dir, vell_pref = RF.DIR, N.FONT_PREFERIDA
        RF.DIR, N.FONT_PREFERIDA = dir_, os.path.join(dir_, "apr", "radar-font.json")
        try:
            for l in episodis("meteocat"):
                t = dt.datetime.fromisoformat(l["t"])
                with open(os.path.join(dir_, f"radar-fonts-{t:%Y-%m}.jsonl"), "a") as f:
                    f.write(json.dumps(l) + "\n")
            estat = RF.verifica(T0.date() + dt.timedelta(days=5), avisa=False)
            self.assertEqual(estat["preferida"], "meteocat")
            self.assertEqual(N.font_preferida(), "meteocat")
            # Más de DIES días después, sin casos nuevos: se queda la que hay.
            estat = RF.verifica(T0.date() + dt.timedelta(days=RF.DIES + 10), avisa=False)
            self.assertEqual(estat["preferida"], "meteocat")
        finally:
            RF.DIR, N.FONT_PREFERIDA = vell_dir, vell_pref

    def test_apunta(self):
        dir_ = tempfile.mkdtemp()
        vell = RF.DIR
        RF.DIR = dir_
        try:
            nc = {"imatge": "rainviewer", "fonts": {"rainviewer": {"hora": T0.isoformat(), "prob": [0.2]}}}
            RF.apunta(T0, nc, {"plou": True})
            with open(os.path.join(dir_, f"radar-fonts-{T0:%Y-%m}.jsonl")) as f:
                l = json.loads(f.read())
            self.assertTrue(l["plou"])
            self.assertEqual(l["triada"], "rainviewer")
        finally:
            RF.DIR = vell

    def test_que_plou(self):
        # Plou si el pluviòmetre de casa ha recollit res en els últims minuts;
        # sense estació no se sap, i la passada no compta (ADR 0058).
        self.assertTrue(RF.plou({"plou": True, "intensitat": 0}))
        self.assertFalse(RF.plou({"plou": False, "intensitat": 0.8}))
        self.assertIsNone(RF.plou(None))
        self.assertEqual(RF.parelles([{"t": T0.isoformat(), "plou": None, "triada": "meteocat", "fonts": {}}]), [])


class Resum(unittest.TestCase):
    def test_les_dues_fonts_al_resum(self):
        import config as C
        r = {"tx": 64, "ty": 47, "km_px": N.km_px(41.52), **r_amb(15, 5)}
        f, c = N.pixel(*C.CASA, 64, 47)
        yy, xx = np.mgrid[:N.MIDA, :N.MIDA]
        r["rainviewer"]["mm_h"] = [np.where((yy - f) ** 2 + (xx - c) ** 2 <= 100, 5.0, 0.0)]
        fs = N.fonts(r, (0.0, 0.0))
        self.assertEqual(set(fs), {"meteocat", "rainviewer"})
        self.assertEqual(fs["meteocat"]["prob"][0], 0.0)
        self.assertGreater(fs["rainviewer"]["prob"][0], 0.5)
        self.assertEqual(len(fs["rainviewer"]["prob"]), N.HORITZO_MIN // N.PAS_MIN + 1)


if __name__ == "__main__":
    unittest.main()
