# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas del radar llevado hacia delante (sin red)."""
import datetime as dt
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402
import nowcast as N  # noqa: E402
import prevision as P  # noqa: E402

T0 = dt.datetime(2026, 10, 6, 12, 0).astimezone()


def camp(centre, radi=15, mmh=10.0):
    """Un chubasco redondo de mmh en el mosaico."""
    yy, xx = np.mgrid[:N.MIDA, :N.MIDA]
    return np.where((yy - centre[0]) ** 2 + (xx - centre[1]) ** 2 <= radi ** 2, mmh, 0.0)


class Conversions(unittest.TestCase):
    def test_marshall_palmer(self):
        self.assertAlmostEqual(float(N.mm_h(np.array(23.0))), 1.0, delta=0.1)   # 23 dBZ ≈ 1 mm/h
        self.assertAlmostEqual(float(N.mm_h(np.array(44.0))), 20.5, delta=1.5)
        self.assertEqual(float(N.mm_h(np.array(-32.0))), 0.0)

    def test_llegenda_meteocat_i_rainviewer(self):
        claus, valors = N.llegenda((int(c + "ff", 16), d + 1.5) for d, c in N.LLEGENDA_METEOCAT)
        rgba = np.array([[[0x00, 0xff, 0x00, 0xff], [0, 0, 0, 0], [1, 2, 3, 0xff]]], dtype=np.uint64)
        r = N.a_mm_h(rgba, claus, valors)
        self.assertAlmostEqual(float(r[0, 0]), float(N.mm_h(np.array(25.5))), places=3)
        self.assertEqual(float(r[0, 1]), 0.0)
        self.assertEqual(float(r[0, 2]), 0.0)          # color fuera de la leyenda
        self.assertGreater(len(N.taula_dbz()), 70)


class Moviment(unittest.TestCase):
    def test_desplacament_d_un_xubasc(self):
        a, b = camp((380, 370)), camp((372, 384))
        d = N.desplacament(a, b)
        self.assertAlmostEqual(d[0], -8, delta=0.6)
        self.assertAlmostEqual(d[1], 14, delta=0.6)

    def test_sense_pluja(self):
        self.assertIsNone(N.desplacament(np.zeros((N.MIDA, N.MIDA)), np.zeros((N.MIDA, N.MIDA))))

    def test_rumb(self):
        self.assertEqual(N.rumb((-1, 0)), "al nord")
        self.assertEqual(N.rumb((0, 1)), "a l'est")
        self.assertEqual(N.rumb((1, -1)), "al sud-oest")

    def test_rainviewer_nomes_si_els_parells_coincideixen(self):
        hores = [T0 - dt.timedelta(minutes=10 * k) for k in range(6, -1, -1)]
        bo = {"hores": hores, "mm_h": [camp((380, 360 + 2 * k)) for k in range(7)]}
        r = {"km_px": 0.92, "rainviewer": bo}
        v, origen = N.moviment(r, T0)
        self.assertEqual(origen, "rainviewer")
        self.assertAlmostEqual(v[1], 0.2, delta=0.03)          # 2 píxeles cada 10 minutos
        salts = [camp((380, 360 + (40 if k % 2 else 0))) for k in range(7)]
        self.assertIsNone(N.moviment({"km_px": 0.92, "rainviewer": {"hores": hores, "mm_h": salts}}, T0))

    def test_adveccio_de_meteocat_mana(self):
        adv = {"base": T0 - dt.timedelta(minutes=20),
               "previsions": [(T0 - dt.timedelta(minutes=14), camp((380, 360))),
                              (T0 + dt.timedelta(minutes=40), camp((380, 387)))]}
        v, origen = N.moviment({"km_px": 0.92, "meteocat": {"adveccio": adv}}, T0)
        self.assertEqual(origen, "meteocat")
        self.assertAlmostEqual(v[1], 0.5, delta=0.03)
        # Una advección de hace más de una hora no vale.
        self.assertIsNone(N.moviment({"km_px": 0.92, "meteocat": {"adveccio": adv}},
                                     T0 + dt.timedelta(minutes=50)))


class Cache(unittest.TestCase):
    def test_nomes_baixa_un_cop_i_neteja(self):
        import tempfile, time
        base = tempfile.mkdtemp()
        N.CACHE = os.path.join(base, "radar-cache")
        baixades = []
        get = lambda url, binari: baixades.append(url) or b"png"
        self.assertEqual(N.tesela(get, "https://x/1.png"), b"png")
        self.assertEqual(N.tesela(get, "https://x/1.png"), b"png")
        self.assertEqual(baixades, ["https://x/1.png"])
        vell = os.path.join(N.CACHE, os.listdir(N.CACHE)[0])
        os.utime(vell, (time.time() - 4 * 3600,) * 2)
        N.neteja_cache()
        self.assertEqual(os.listdir(N.CACHE), [])

    def test_sense_carpeta_no_desa(self):
        N.CACHE = "/no/existeix/radar-cache"
        self.assertEqual(N.tesela(lambda u, b: b"x", "https://x/2.png"), b"x")


class Endavant(unittest.TestCase):
    def setUp(self):
        self.r = {"tx": 64, "ty": 47, "km_px": N.km_px(41.52)}
        self.f, self.c = N.pixel(*C.CASA, 64, 47)

    def test_arriba_quan_toca(self):
        # Un chubasco a 30 píxeles al oeste de casa que va al este a 0,5 px/min:
        # llega en unos 60 minutos.
        ara = camp((self.f, self.c - 30), radi=8)
        s = N.serie(self.r, ara, (0.0, 0.5), *C.CASA)
        nc = {"hora": T0.isoformat(), "llocs": {"casa": s}}
        arriba = N.arribada(nc)
        self.assertTrue(T0 + dt.timedelta(minutes=45) <= arriba <= T0 + dt.timedelta(minutes=65))
        abans = N.en_tram(nc, "casa", T0, T0 + dt.timedelta(minutes=30))
        despres = N.en_tram(nc, "casa", T0 + dt.timedelta(minutes=50), T0 + dt.timedelta(minutes=70))
        self.assertEqual(abans["prob"], 0)
        self.assertGreater(despres["prob"], 0.5)
        self.assertGreater(despres["mm"], 1)
        self.assertIsNone(N.en_tram(nc, "casa", T0 + dt.timedelta(hours=3), T0 + dt.timedelta(hours=4)))

    def test_si_se_n_va_no_arriba(self):
        ara = camp((self.f, self.c - 30), radi=8)
        s = N.serie(self.r, ara, (0.0, -0.5), *C.CASA)
        self.assertIsNone(N.arribada({"hora": T0.isoformat(), "llocs": {"casa": s}}))


class Trajecte(unittest.TestCase):
    def nc(self, prob, mm_h):
        passos = [{"min": m, "mm_h": mm_h, "prob": prob} for m in range(0, 125, 5)]
        return {"hora": P.AHORA.isoformat(), "cap_a": "a l'est", "velocitat_kmh": 30,
                "llocs": {k: passos for k in ("casa", "mig", "desti")}}

    def nivell(self, prob, mm_h):
        ini, fin = P.AHORA + dt.timedelta(minutes=30), P.AHORA + dt.timedelta(minutes=60)
        t = N.en_tram(self.nc(prob, mm_h), "casa", ini, fin)
        return P.motivo_nowcast(t, self.nc(prob, mm_h), ini, fin)[1]

    def test_nivells(self):
        self.assertEqual(self.nivell(0.7, 3.0), "cotxe")
        self.assertEqual(self.nivell(0.7, 0.4), "compte")     # probable però feble
        self.assertEqual(self.nivell(0.3, 3.0), "compte")
        self.assertEqual(self.nivell(0.05, 3.0), "moto")

    def test_mode_avis(self):
        self.assertEqual(P.motivos_modo_aviso([], [], [], {"km_lluvia": None, "nowcast": self.nc(0.4, 1)}),
                         ["pluja al radar"])
        self.assertEqual(P.motivos_modo_aviso([], [], [], {"km_lluvia": None, "nowcast": self.nc(0.0, 0)}), [])


if __name__ == "__main__":
    unittest.main()
