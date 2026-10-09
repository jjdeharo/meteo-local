# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas de la corrección de la calidad del aire (aire.py, ADR 0054), sin red."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aire as A  # noqa: E402


def hores(dies):
    return [f"2026-10-{d:02d}T{h:02d}:00" for d in dies for h in range(24)]


class Factors(unittest.TestCase):
    def test_el_factor_s_aplica_nomes_si_encerta_mes_en_dies_no_usats(self):
        # Auditoría del 09-10-2026: el factor se aplicaba sin comprobar que
        # mejorara el modelo. NO₂: el modelo da siempre el doble (factor 0,5,
        # que acierta). Ozono: un día el doble y otro la mitad; el factor
        # global vale 1 y, calculado con los otros días, empeora: se descarta.
        temps = hores((1, 2, 3, 4))
        model = {"time": temps, "nitrogen_dioxide": [20.0] * len(temps),
                 "ozone": [60.0] * len(temps)}
        mesures = {}
        for t in temps:
            dia = int(t[8:10])
            for e in ("Barberà del Vallès", "Sant Cugat del Vallès"):
                mesures[(e, "nitrogen_dioxide", t)] = 10.0
                mesures[(e, "ozone", t)] = 120.0 if dia % 2 else 30.0
        adoptats, descartats = A.factors(model, mesures, tot=True)
        self.assertEqual(list(adoptats), ["nitrogen_dioxide"])
        self.assertEqual((adoptats["nitrogen_dioxide"]["factor"], adoptats["nitrogen_dioxide"]["hores"]), (0.5, 96))
        self.assertEqual(adoptats["nitrogen_dioxide"]["error"], 0.0)
        self.assertEqual(adoptats["nitrogen_dioxide"]["error_sense"], 10.0)
        self.assertEqual(list(descartats), ["ozone"])
        self.assertGreater(descartats["ozone"]["error"], A.AIRE_MILLORA * descartats["ozone"]["error_sense"])
        self.assertEqual(A.factors(model, mesures), adoptats)

    def test_sense_prou_hores_o_estacions_no_es_corregeix(self):
        temps = hores((1, 2))
        model = {"time": temps, "nitrogen_dioxide": [20.0] * len(temps)}
        una = {("Barberà del Vallès", "nitrogen_dioxide", t): 10.0 for t in temps}
        self.assertEqual(A.factors(model, una), {})
        dues = {**una, **{("Montcada i Reixac", "nitrogen_dioxide", t): 10.0 for t in temps[:60]}}
        self.assertEqual(A.factors(model, dues), {})      # 48 horas, menos de 72

    def test_index_interpolat(self):
        self.assertEqual(A.index_de("nitrogen_dioxide", 0), 0)
        self.assertEqual(A.index_de("nitrogen_dioxide", 10), 20)
        self.assertEqual(A.index_de("nitrogen_dioxide", 42.5), 50)
        self.assertEqual(A.categoria(50), "regular")


if __name__ == "__main__":
    unittest.main()
