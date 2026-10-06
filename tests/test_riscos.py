# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas de las situaciones de peligro de la página de casa (sin red ni Telegram)."""
import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import riscos as RS  # noqa: E402

AHORA = dt.datetime(2026, 10, 6, 12, 10).astimezone()


def hores(cambios=None, n=24):
    """n horas tranquilas desde las 12; cambios = {índice: {campo: valor}}."""
    res = []
    for i in range(n):
        ini = dt.datetime(2026, 10, 6, 12) + dt.timedelta(hours=i)
        f = {"hora": ini.strftime("%Y-%m-%dT%H:%M"),
             "fins": (ini + dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
             "temperatura": 18, "pluja_mm": 0.0, "ratxa": 20, "neu": 0}
        f.update((cambios or {}).get(i, {}))
        res.append(f)
    return res


def salida(h=None, ara=None, casa=None):
    d = {"hores": h if h is not None else hores(), "ara": ara or {"pluja_1h": 0, "pluja_12h": 0, "temperatura": 18},
         "ara_casa": casa}
    d["riscos"] = RS.detecta(d, AHORA)
    return d


class Deteccio(unittest.TestCase):
    def test_tranquil(self):
        self.assertEqual(salida()["riscos"], [])

    def test_ratxa_amb_tram_i_nivell(self):
        r = salida(hores({3: {"ratxa": 75}, 5: {"ratxa": 95}}))["riscos"]
        self.assertEqual(len(r), 1)
        self.assertEqual((r[0]["tipus"], r[0]["nivell"], r[0]["valor"]), ("ratxa", "taronja", 95))
        self.assertIn("avui de 15 a 18 h", r[0]["text"])

    def test_pluja_12h_sense_cap_hora_forta(self):
        h = hores({i: {"pluja_mm": 6} for i in range(10, 22)})
        r = salida(h)["riscos"]
        self.assertEqual([x["tipus"] for x in r], ["pluja_12h"])
        self.assertEqual(r[0]["valor"], 72)
        self.assertIn("avui de 22 a 10 h", r[0]["text"])

    def test_mesura_ara_i_previsio_son_claus_diferents(self):
        r = salida(hores({0: {"pluja_mm": 25}}), ara={"pluja_1h": 42, "pluja_12h": 50, "temperatura": 15})["riscos"]
        self.assertEqual({x["clau"]: x["nivell"] for x in r}, {"ara:pluja_1h": "taronja", "previsio:pluja_1h": "groc"})
        self.assertEqual(r[0]["nivell"], "taronja")   # el pitjor primer

    def test_pluja_de_casa_nomes_si_en_marca(self):
        ara = {"pluja_1h": 0, "temperatura": 15}
        self.assertEqual(salida(ara=ara, casa={"pluja_1h": 30, "plou": False, "temperatura": 15})["riscos"], [])
        self.assertEqual(len(salida(ara=ara, casa={"pluja_1h": 30, "plou": True, "temperatura": 15})["riscos"]), 1)

    def test_fred_i_neu(self):
        h = hores({i: {"temperatura": -5, "neu": 0.5} for i in range(14, 20)})
        tipus = {x["tipus"]: x["nivell"] for x in salida(h)["riscos"]}
        self.assertEqual(tipus, {"fred": "groc", "neu_24h": "groc"})

    def test_sense_previsio(self):
        self.assertEqual(salida(h=[])["riscos"], [])


class Avis(unittest.TestCase):
    def setUp(self):
        self.estat = {"actius": {}}

    def pas(self, s, minuts):
        return RS.compara(self.estat, s, AHORA + dt.timedelta(minutes=minuts))

    def test_avisa_un_cop_puja_i_acaba(self):
        groc = salida(hores({3: {"ratxa": 75}}))
        self.assertIn("risc groc", self.pas(groc, 0))
        self.assertIsNone(self.pas(groc, 30))                                  # ja avisat
        self.assertIn("risc taronja", self.pas(salida(hores({3: {"ratxa": 92}})), 60))
        self.assertIsNone(self.pas(groc, 90))                                  # baixa: no avisa
        self.assertIsNone(self.pas(salida(), 120))                             # encara no fa 3 h
        self.assertIn("ja no", self.pas(salida(), 90 + 180))
        self.assertEqual(self.estat["actius"], {})
        self.assertIsNone(self.pas(salida(), 300))

    def test_sense_previsio_no_dona_per_acabat(self):
        self.pas(salida(hores({3: {"ratxa": 75}})), 0)
        self.assertIsNone(self.pas(salida(h=[]), 600))
        self.assertIn("previsio:ratxa", self.estat["actius"])

    def test_desa_i_llegeix(self):
        RS.ESTADO = os.path.join(tempfile.mkdtemp(), "riscos.json")
        ruta = os.path.join(os.path.dirname(RS.ESTADO), "casa.json")
        import json
        with open(ruta, "w") as f:
            json.dump(salida(hores({3: {"ratxa": 75}})), f)
        self.assertIn("risc groc", RS.avisa(ruta, AHORA, envia=False))
        self.assertIsNone(RS.avisa(ruta, AHORA, envia=False))


if __name__ == "__main__":
    unittest.main()
