# SPDX-License-Identifier: AGPL-3.0-or-later
"""Els ecos del radar a prop de casa, apuntats a cada pasada (seguiment del 10-10-2026)."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402

import nowcast as N  # noqa: E402
import prevision as P  # noqa: E402
import registre as R  # noqa: E402
import config as C  # noqa: E402


class RadarAProp(unittest.TestCase):
    def radar_fals(self):
        lat, lon = C.CASA
        tx, ty = N.geometria(lat, lon)
        fila, col = (int(v) for v in N.pixel(lat, lon, tx, ty))
        kmpx = N.km_px(lat)
        mc = np.zeros((N.MIDA, N.MIDA))
        mc[fila, col + round(5 / kmpx)] = 0.17        # un eco feble a uns 5 km a l'est
        mc[fila - round(30 / kmpx), col] = 3.0        # pluja a 30 km al nord: no és a prop
        hora = dt.datetime(2026, 10, 10, 11, 24).astimezone()
        rv = {"hores": [hora + dt.timedelta(minutes=10)], "mm_h": [np.zeros((N.MIDA, N.MIDA))]}
        return {"tx": tx, "ty": ty, "km_px": kmpx, "errors": [],
                "meteocat": {"hora": hora, "mm_h": mc}, "rainviewer": rv}

    def test_pixels_de_cada_radar_a_prop_de_casa(self):
        r = self.radar_fals()
        with mock.patch.object(N, "carrega", return_value=r), mock.patch.object(N, "resum", return_value=None), \
                mock.patch.object(N, "font_preferida", return_value="meteocat"):
            res = P.radar()
        mc = res["a_prop"]["meteocat"]
        self.assertEqual(len(mc["px"]), 1)
        km, rumb, mm = mc["px"][0]
        self.assertAlmostEqual(km, 5, delta=1)
        self.assertAlmostEqual(rumb, 90, delta=5)
        self.assertEqual(mm, 0.17)
        self.assertEqual(res["a_prop"]["rainviewer"]["px"], [])
        # El que ja feia el radar no canvia: la pluja més propera, la del píxel de 5 km.
        self.assertAlmostEqual(res["km_lluvia"], 5, delta=1)

    def test_una_linia_per_pasada(self):
        radar = {"imatge": "meteocat", "km_lluvia": 8.4,
                 "a_prop": {"meteocat": {"hora": "2026-10-10T11:24+02:00", "px": [[8.4, 310, 0.17]]}}}
        obs = [{"estacion": "Sabadell", "mm_ultima_media_hora": 0.0}, {"estacion": "casa", "intensitat": 1.2}]
        ara = dt.datetime(2026, 10, 10, 11, 30).astimezone()
        with tempfile.TemporaryDirectory() as d, mock.patch.object(R, "DIR", d):
            R.apunta_radar_a_prop(ara, radar, ["pluja al radar"], obs)
            R.apunta_radar_a_prop(ara, radar, [], [])
            with open(os.path.join(d, "radar-a-prop-2026-10.jsonl"), encoding="utf-8") as f:
                linies = [json.loads(l) for l in f]
        self.assertEqual(len(linies), 2)
        self.assertEqual(linies[0]["mode_avis"], ["pluja al radar"])
        self.assertEqual(linies[0]["pluja_mesurada"], ["casa"])
        self.assertEqual(linies[0]["radars"]["meteocat"]["px"], [[8.4, 310, 0.17]])
        self.assertEqual(linies[1]["pluja_mesurada"], [])


if __name__ == "__main__":
    unittest.main()
