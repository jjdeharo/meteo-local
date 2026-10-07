# SPDX-License-Identifier: AGPL-3.0-or-later
"""El viento de ahora, de la estación de Meteocat (ADR 0037), sin red."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import prevision as P  # noqa: E402

TAULA = """<html><table class="tblperiode"><thead><tr>
<th>Període<span>TU</span></th><th>TM<span>°C</span></th><th>PPT<span>mm</span></th>
<th>VVM (10 m)<span>km/h</span></th><th>DVM (10 m)<span>graus</span></th><th>VVX (10 m)<span>km/h</span></th>
</tr></thead><tbody>
<tr><td>16:00 - 16:30</td><td>24.1</td><td>0.2</td><td>13.0</td><td>220</td><td>25.2</td></tr>
<tr><td>16:30 - 17:00</td><td>(s/d)</td><td>(s/d)</td><td>(s/d)</td><td>(s/d)</td><td>(s/d)</td></tr>
</tbody></table></html>"""


class Vent(unittest.TestCase):
    def test_ultima_mitja_hora_amb_dada(self):
        v = P.vent_meteocat("XV", lector=lambda url: TAULA)
        self.assertEqual((v["estacio"], v["mitja"], v["ratxa"]), ("Sant Cugat", 13.0, 25.2))
        fins = dt.datetime.fromisoformat(v["fins"])
        self.assertEqual(fins.astimezone(dt.timezone.utc).time(), dt.time(16, 30))

    def test_sense_dades(self):
        self.assertIsNone(P.vent_meteocat("XV", lector=lambda url: "<html></html>"))

    def test_la_pluja_segueix_igual(self):
        files = P.taula_meteocat("XV", lector=lambda url: TAULA)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0][1], 0.2)
        self.assertEqual(files[0][0].time(), dt.time(16, 0))


if __name__ == "__main__":
    unittest.main()
