# SPDX-License-Identifier: AGPL-3.0-or-later
"""Los avisos de peligro de Meteocat de la comarca, junto a los planes (ADR 0067), sin red."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
sys.path.insert(0, os.path.join(ARREL, "bot"))
import avisos_bot as AB  # noqa: E402
import bot as B  # noqa: E402
import smp  # noqa: E402

AHORA = dt.datetime(2026, 10, 10, 19, 0).astimezone()


def afectacio(comarca, perill, dia="2026-10-10T00:00Z"):
    return {"dia": dia, "llindar": "Intensitat > 20 mm / 30 minuts", "auxiliar": False, "perill": perill,
            "idComarca": comarca, "nivell": 1}


# Com l'exemple de /smp/episodis-oberts de la documentació de l'API de Meteocat.
EPISODIS = [{
    "estat": {"nom": "Obert", "data": None}, "meteor": {"nom": "Intensitat de pluja"},
    "avisos": [{
        "tipus": "Avís", "dataEmisio": "2026-10-10T08:09Z", "dataInici": "2026-10-10T12:00Z",
        "dataFi": "2026-10-11T05:59Z", "estat": "Vigent",
        "evolucions": [
            {"dia": "2026-10-10T00:00Z", "llindar1": "Intensitat > 20 mm / 30 minuts", "periodes": [
                {"nom": "00-06", "afectacions": None}, {"nom": "06-12", "afectacions": None},
                {"nom": "12-18", "afectacions": [afectacio(40, 3), afectacio(41, 2)]},
                {"nom": "18-00", "afectacions": [afectacio(40, 2)]}]},
            {"dia": "2026-10-11T00:00Z", "llindar1": "Intensitat > 20 mm / 30 minuts", "periodes": [
                {"nom": "00-06", "afectacions": [afectacio(40, 1, "2026-10-11T00:00Z")]}]}]},
        {"tipus": "Preavís", "estat": "Vigent", "evolucions": [{"dia": "2026-10-12T00:00Z", "periodes": [
            {"nom": "00-06", "afectacions": [afectacio(40, 5, "2026-10-12T00:00Z")]}]}]}]},
    {"estat": {"nom": "Obert"}, "meteor": {"nom": "Acumulació de pluja"}, "avisos": [{
        "tipus": "Avís", "estat": "Vigent", "dataEmisio": "2026-10-10T08:09Z",
        "evolucions": [{"dia": "2026-10-10T00:00Z", "periodes": [
            {"nom": "12-18", "afectacions": [afectacio(31, 4)]}]}]}]},
]


def pagina(episodis):
    return ("<script>\n            Meteocat.avisosSMP({\n                dom: 'mapaAvisos',\n"
            "                prediccions: [{\"general\":{}}],\n"
            "                episodisPreavisos: [{\"avisos\": [{\"tipus\": \"Preavís\"}]}],\n"
            f"                avisos: {json.dumps(episodis)},\n                cataleg: []\n            }});\n</script>")


class Smp(unittest.TestCase):
    def test_llegeix_els_avisos_de_la_pagina(self):
        self.assertEqual(smp.episodis(pagina(EPISODIS)), EPISODIS)
        self.assertEqual(smp.episodis(pagina([])), [])
        with self.assertRaises(ValueError):
            smp.episodis("<html>sense avisos</html>")

    def test_nomes_els_vigents_de_la_comarca(self):
        a = smp.de_la_comarca(EPISODIS, 40)
        # El preavís i l'avís d'una altra comarca no hi són; les franges seguides, juntes.
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["meteor"], "Intensitat de pluja")
        self.assertEqual(a[0]["perill"], 3)
        self.assertEqual(a[0]["dies"], {"2026-10-10": [(12, 24)], "2026-10-11": [(0, 6)]})
        self.assertEqual(smp.de_la_comarca(EPISODIS, 99), [])

    def test_grau_com_el_mapa_de_meteocat(self):
        self.assertEqual([smp.nivell(p) for p in range(1, 7)], ["mig", "mig", "alt", "alt", "maxim", "maxim"])

    def test_textos(self):
        r = smp.llegeix(lambda url: pagina(EPISODIS), AHORA)
        l = r["linies"][0]
        self.assertEqual(l["nivell"], "alt")
        hora = smp.hora_local("2026-10-10T08:09Z")
        self.assertEqual(l["ca"], "Meteocat: avís de perill alt per «Intensitat de pluja» al Vallès Occidental, "
                                  "dissabte 10 de 12 a 24 h i diumenge 11 de 0 a 6 h "
                                  f"(Intensitat > 20 mm / 30 minuts; emès a les {hora}).")
        self.assertTrue(l["es"].startswith("Meteocat: aviso de peligro alto por «Intensitat de pluja» en el Vallès "
                                           "Occidental, sábado 10 de 12 a 24 h y domingo 11 de 0 a 6 h"))
        cap = smp.llegeix(lambda url: pagina([]), AHORA)["linies"]
        self.assertEqual(cap, [{"nivell": "nul",
                                "ca": "Meteocat no té cap avís de perill per al Vallès Occidental (dades de les 19:00).",
                                "es": "Meteocat no tiene ningún aviso de peligro para el Vallès Occidental "
                                      "(datos de las 19:00)."}])

    def test_al_costat_del_pla(self):
        s = smp.llegeix(lambda url: pagina(EPISODIS), AHORA)
        pla = {"pla": "INUNCAT", "nom": "d'inundacions", "fase": "alerta"}
        d = {"generat": AHORA.isoformat(), "plans": [pla], "smp": s}
        r = B.text_avisos_actius(d, "ca", AHORA)
        self.assertIn("🟠 Pla d'inundacions (INUNCAT) en fase d'alerta.\n🟠 Meteocat: avís de perill alt", r)
        # A l'avís del pla nou, també.
        t = AB.text_pla(pla, smp=s)
        self.assertIn("\n🟠 Meteocat: avís de perill alt per «Intensitat de pluja»", t["ca"])
        self.assertIn("\n🟠 Meteocat: aviso de peligro alto", t["es"])
        # Sense lectura de Meteocat, res.
        self.assertNotIn("Meteocat", AB.text_pla(pla)["ca"])
        self.assertNotIn("Meteocat", B.text_avisos_actius({**d, "smp": None}, "ca", AHORA))

    def test_prova_diaria(self):
        with tempfile.TemporaryDirectory() as dir:
            marca = os.path.join(dir, "smp-falla")
            self.assertIsNotNone(smp.comprova(lambda url: "<html></html>", marca, avisa=False))
            self.assertTrue(os.path.exists(marca))
            self.assertIsNone(smp.comprova(lambda url: pagina([]), marca, avisa=False))
            self.assertFalse(os.path.exists(marca))


if __name__ == "__main__":
    unittest.main()
