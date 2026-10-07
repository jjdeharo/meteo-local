# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas del bot de Telegram y de sus avisos (ADR 0034), sin red."""
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

ARA = dt.datetime(2026, 10, 7, 7, 0).astimezone()


class Api:
    """Telegram de mentira: apunta lo que se envía."""
    def __init__(self, bloquejats=()):
        self.enviats, self.bloquejats = [], set(bloquejats)

    def __call__(self, metode, temps=30, **p):
        if metode == "sendMessage" and str(p["chat_id"]) in self.bloquejats:
            raise B.Bloquejat()
        self.enviats.append((metode, p))
        return {}


def dades(generat=ARA):
    hores = []
    for i in range(24):
        h = (generat + dt.timedelta(hours=i)).replace(minute=0, tzinfo=None)
        hores.append({"hora": h.isoformat(timespec="minutes"), "fins": (h + dt.timedelta(hours=1)).isoformat(timespec="minutes"),
                      "temperatura": 15 + i % 10, "probabilitat": 0.4 if 12 <= h.hour < 15 else 0.0, "pluja_mm": 0})
    return {"generat": generat.isoformat(timespec="minutes"), "ara": {"temperatura": 16.2, "intensitat": 0},
            "hores": hores, "trens": {"linies": [{"linia": "R4", "estat": "sense_trens"}, {"linia": "S2", "estat": "circula"}]},
            "avisos": [{"inicio": "2026-10-07T12:00:00+02:00", "fin": "2026-10-07T19:59:59+02:00", "nivel": "groc",
                        "tipo": "tempestes", "zona": "Prelitoral de Barcelona"}]}


class Menu(unittest.TestCase):
    def test_alta_per_defecte_i_idioma(self):
        self.assertEqual(B.nou_subscriptor({"language_code": "es"})["idioma"], "es")
        sub = B.nou_subscriptor({})
        self.assertEqual((sub["idioma"], sub["avisos"], sub["resum"]), ("ca", ["riera", "perill"], None))

    def test_botons(self):
        sub = B.nou_subscriptor({})
        self.assertTrue(B.canvia(sub, "t:pluja"))
        self.assertTrue(B.canvia(sub, "t:riera"))
        self.assertEqual(sub["avisos"], ["perill", "pluja"])
        self.assertTrue(B.canvia(sub, "r:7"))
        self.assertTrue(B.canvia(sub, "i:es"))
        self.assertFalse(B.canvia(sub, "-"))
        self.assertEqual((sub["resum"], sub["idioma"]), ("7", "es"))
        textos = [b["text"] for fila in B.teclat(sub) for b in fila]
        self.assertIn("✓ Lluvia dentro de 15 minutos", textos)
        self.assertIn("· Desbordamiento de la riera de Sant Cugat (en pruebas)", textos)
        self.assertIn("• 7 h", textos)
        self.assertIn("20 h (para mañana)", textos)

    def test_start_i_baixa(self):
        api, subs = Api(), {}
        B.atén(api, subs, {"message": {"chat": {"id": 5, "type": "private"}, "from": {}, "text": "/start"}})
        self.assertIn("5", subs)
        self.assertIn("orientatius, no oficials", api.enviats[0][1]["text"])
        self.assertIn("inline_keyboard", api.enviats[1][1]["reply_markup"])
        B.atén(api, subs, {"callback_query": {"id": "q", "data": "t:trens", "from": {},
                                              "message": {"chat": {"id": 5}, "message_id": 9}}})
        self.assertIn("trens", subs["5"]["avisos"])
        B.atén(api, subs, {"message": {"chat": {"id": 5, "type": "private"}, "from": {}, "text": "/baixa"}})
        self.assertNotIn("5", subs)

    def test_alta_avisa_a_juanjo_sense_nom(self):
        avisos, original = [], B.avisa_juanjo
        B.avisa_juanjo = avisos.append
        try:
            subs = {}
            for _ in range(2):
                B.atén(Api(), subs, {"message": {"chat": {"id": 7, "type": "private"},
                                                 "from": {"first_name": "Maria"}, "text": "/start"}})
        finally:
            B.avisa_juanjo = original
        self.assertEqual(avisos, ["Temps a Montflorit: alta nova al bot (ja en són 1)."])

    def test_grups_no(self):
        api, subs = Api(), {}
        B.atén(api, subs, {"message": {"chat": {"id": -9, "type": "group"}, "text": "/start"}})
        self.assertEqual((subs, api.enviats), ({}, []))


class Resum(unittest.TestCase):
    def test_resum(self):
        r = B.resum(dades(), "ca", ARA)
        self.assertIn("Ara a Montflorit: 16 °C, no plou.", r)
        self.assertIn("Pluja: possible de 12 a 15 h (fins al 40 %).", r)
        self.assertIn("Avís groc de l'AEMET per tempestes fins a les 20:00.", r)
        self.assertIn("Trens: R4 sense trens.", r)
        self.assertIn("Lluvia: posible de 12 a 15 h", B.resum(dades(), "es", ARA))

    def test_a_les_20_la_de_dema(self):
        vespre = ARA.replace(hour=20)
        d = dades(vespre)
        d["avisos"].append({"inicio": "2026-10-08T10:00:00+02:00", "fin": "2026-10-08T19:59:59+02:00",
                            "nivel": "groc", "tipo": "pluja", "zona": "Prelitoral de Barcelona"})
        r = B.resum(d, "ca", vespre)
        self.assertTrue(r.startswith("Previsió per a demà, dijous:"))
        self.assertIn("Demà: de ", r)
        self.assertIn("Pluja: possible de 12 a 15 h (fins al 40 %).", r)
        self.assertIn("Avís groc de l'AEMET per pluja de 10:00 a 20:00.", r)
        self.assertNotIn("Ara a Montflorit", r)
        self.assertNotIn("Trens", r)
        self.assertNotIn("Aquesta nit", r)
        self.assertTrue(B.resum(d, "es", vespre).startswith("Previsión para mañana, jueves:"))

    def test_milimetres_sense_probabilitat_no_compten(self):
        d = dades()
        for f in d["hores"]:
            f.update(probabilitat=0.17, pluja_mm=0.4)
        self.assertIn("Sense pluja prevista.", B.resum(d, "ca", ARA))

    def test_dades_velles(self):
        r = B.resum(dades(ARA - dt.timedelta(hours=3)), "ca", ARA)
        self.assertIn("no s'actualitzen des de les", r)


class Repartiment(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        B.DADES = self.dir.name

    def tearDown(self):
        self.dir.cleanup()

    def escriu(self, avisos, dades_=None):
        with open(os.path.join(self.dir.name, "avisos.json"), "w") as f:
            json.dump({"avisos": avisos}, f)
        with open(os.path.join(self.dir.name, "montflorit.json"), "w") as f:
            json.dump(dades_ or dades(), f)

    def test_cadascu_el_que_tria_i_canal(self):
        hora = ARA.isoformat(timespec="minutes")
        self.escriu([{"id": "riera:1", "tipus": "riera", "hora": hora, "ca": "R ca", "es": "R es"},
                     {"id": "pluja:1", "tipus": "pluja", "hora": hora, "ca": "P ca", "es": "P es"}])
        subs = {"1": {"idioma": "ca", "avisos": ["riera"], "resum": None},
                "2": {"idioma": "es", "avisos": ["riera", "pluja"], "resum": None},
                "3": {"idioma": "ca", "avisos": ["pluja"], "resum": None}}
        api, estat = Api(bloquejats=["3"]), {}
        B.reparteix(api, subs, estat, ARA + dt.timedelta(minutes=30))   # la lluvia ya no vale
        enviats = [(p["chat_id"], p["text"]) for _, p in api.enviats]
        self.assertIn(("1", "R ca"), enviats)
        self.assertIn(("2", "R es"), enviats)
        self.assertIn((B.CANAL, "R ca\n\nR es"), enviats)
        self.assertNotIn(("2", "P es"), enviats)
        # Una sola vez.
        api.enviats.clear()
        B.reparteix(api, subs, estat, ARA + dt.timedelta(minutes=31))
        self.assertEqual(api.enviats, [])

    def test_bloquejat_es_dona_de_baixa(self):
        self.escriu([{"id": "pluja:1", "tipus": "pluja", "hora": ARA.isoformat(), "ca": "P", "es": "P"}])
        subs = {"3": {"idioma": "ca", "avisos": ["pluja"], "resum": None}}
        B.reparteix(Api(bloquejats=["3"]), subs, {}, ARA)
        self.assertEqual(subs, {})

    def test_resum_a_l_hora_i_canal(self):
        self.escriu([])
        subs = {"1": {"idioma": "ca", "avisos": [], "resum": "7"}, "2": {"idioma": "ca", "avisos": [], "resum": "8"}}
        api, estat = Api(), {}
        B.reparteix(api, subs, estat, ARA)
        destins = [p["chat_id"] for _, p in api.enviats]
        self.assertEqual(sorted(map(str, destins)), sorted(["1", B.CANAL]))
        canal = [p["text"] for _, p in api.enviats if p["chat_id"] == B.CANAL][0]
        self.assertEqual(canal.count(B.WEB), 1)
        api.enviats.clear()
        B.reparteix(api, subs, estat, ARA + dt.timedelta(minutes=20))
        self.assertEqual(api.enviats, [])


class AvisosPublics(unittest.TestCase):
    def test_trens_dues_passades(self):
        estat = {}
        linia = {"linies": [{"linia": "R7", "estacio": "Cerdanyola Universitat", "estat": "sense_trens"}]}
        self.assertEqual(AB.decideix(estat, {"trens": linia}, ARA), [])
        nous = AB.decideix(estat, {"trens": linia}, ARA + dt.timedelta(minutes=15))
        self.assertEqual(nous[0]["ca"], "R7 (Cerdanyola Universitat): sense trens.")
        self.assertEqual(AB.decideix(estat, {"trens": linia}, ARA + dt.timedelta(minutes=30)), [])
        torna = {"linies": [dict(linia["linies"][0], estat="circula")]}
        AB.decideix(estat, {"trens": torna}, ARA + dt.timedelta(minutes=45))
        nous = AB.decideix(estat, {"trens": torna}, ARA + dt.timedelta(minutes=60))
        self.assertEqual(nous[0]["es"], "R7 (Cerdanyola Universitat): vuelve a circular.")

    def test_riera_amb_avis_orientatiu(self):
        estat = {}
        riera = {"fins": ARA.isoformat(), "mm_3h": 52, "mm_6h": 70, "radar_1h": 3.0, "index": 55, "index_6h": 75,
                 "capcalera": None, "montflorit_3h": None}
        nous = AB.decideix(estat, {"riera": riera}, ARA)
        self.assertEqual(nous[0]["nivell"], "perill")
        self.assertIn("perill de desbordament", nous[0]["ca"])
        self.assertIn("Aviso en pruebas, orientativo y no oficial", nous[0]["es"])
        self.assertEqual(AB.decideix(estat, {"riera": riera}, ARA + dt.timedelta(minutes=15)), [])

    def test_perill_en_castella(self):
        r = {"clau": "previsio:ratxa", "tipus": "ratxa", "origen": "previsio", "nivell": "groc", "valor": 75,
             "des_de": "2026-10-07T15:00+02:00", "fins": "2026-10-07T16:00+02:00",
             "text": "Vent molt fort previst: ratxes de fins a 75 km/h, avui de 15 a 16 h."}
        nous = AB.decideix({}, {"riscos": [r]}, ARA)
        self.assertIn("Viento muy fuerte previsto: rachas de hasta 75 km/h, hoy de 15 a 16 h.", nous[0]["es"])


if __name__ == "__main__":
    unittest.main()
