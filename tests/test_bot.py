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
    def __init__(self, bloquejats=(), al_canal=(), canal_falla=False):
        self.enviats, self.bloquejats, self.al_canal = [], set(bloquejats), set(al_canal)
        self.canal_falla = canal_falla

    def __call__(self, metode, temps=30, **p):
        if metode == "getChatMember":       # preguntar no envía nada
            return {"status": "member" if str(p["user_id"]) in self.al_canal else "left"}
        if metode == "sendMessage" and str(p["chat_id"]) in self.bloquejats:
            raise B.Bloquejat()
        if metode == "sendMessage" and p["chat_id"] == B.CANAL and self.canal_falla:
            raise RuntimeError("canal")
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
        self.assertIn("✓ Lluvia a punto de empezar (15 min antes)", textos)
        self.assertIn("Desbordamiento de la riera de Sant Cugat (en pruebas)", textos)
        self.assertIn("✓ 7 h", textos)
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
        self.assertIn("Ara mateix: 16 °C, no plou.", r)
        self.assertIn("Pluja: possible de 12 a 15 h (probabilitat fins al 40 %).", r)
        self.assertIn("Avís groc de l'AEMET per tempestes fins a les 20:00.", r)
        self.assertIn("Trens de Cerdanyola: R4 sense trens.", r)
        self.assertIn("Lluvia: posible de 12 a 15 h", B.resum(dades(), "es", ARA))

    def test_ara_amb_l_estacio_particular_i_fins_a_mitjanit(self):
        # La temperatura d'ara, de l'estació particular; la pluja, de qualsevol.
        d = dades()
        d["ara_casa"] = {"temperatura": 14.6, "plou": True}
        r = B.resum(d, "ca", ARA)
        self.assertIn("Ara mateix: 15 °C, plou.", r)
        self.assertIn("Temperatura d'aquí a mitjanit: entre ", r)
        self.assertIn("Temperatura de aquí a medianoche: entre ", B.resum(d, "es", ARA))

    def test_a_les_20_la_de_dema(self):
        vespre = ARA.replace(hour=20)
        d = dades(vespre)
        d["avisos"].append({"inicio": "2026-10-08T10:00:00+02:00", "fin": "2026-10-08T19:59:59+02:00",
                            "nivel": "groc", "tipo": "pluja", "zona": "Prelitoral de Barcelona"})
        r = B.resum(d, "ca", vespre)
        self.assertTrue(r.startswith("<b>Previsió per a demà, dijous, a Montflorit</b>"))
        self.assertIn("Temperatura: entre ", r)
        self.assertIn("Pluja: possible de 12 a 15 h (probabilitat fins al 40 %).", r)
        self.assertIn("Avís groc de l'AEMET per pluja de 10:00 a 20:00.", r)
        self.assertNotIn("Ara mateix", r)
        self.assertNotIn("Trens", r)
        self.assertNotIn("Aquesta nit", r)
        self.assertTrue(B.resum(d, "es", vespre).startswith("<b>Previsión para mañana, jueves, en Montflorit</b>"))

    def test_roba_de_tot_el_dia(self):
        # Les dades de prova van de 15 °C (7 h) a 24 °C (16 h): dues peces, per ordre d'hora.
        self.assertIn("Roba per anar a peu: jaqueta lleugera o jersei a les 7 h (15 °C); "
                      "màniga curta o màniga llarga fina a les 16 h (24 °C).", B.resum(dades(), "ca", ARA))
        self.assertIn("Ropa para ir a pie: chaqueta ligera o jersey a las 7 h (15 °C); "
                      "manga corta o manga larga fina a las 16 h (24 °C).", B.resum(dades(), "es", ARA))

    def test_roba_amb_vent_i_una_sola_peca(self):
        hora = lambda h, t, v=0: {"hora": f"2026-10-08T{h:02d}:00", "temperatura": t, "vent": v}
        # 8 °C amb 30 km/h es noten com 4 °C; fora de les 7-21 h no compta.
        self.assertEqual(B.text_roba([hora(5, -2), hora(9, 8, 30), hora(14, 9)], "ca"),
                         "Roba per anar a peu: abric, bufanda i guants a les 9 h (8 °C, es noten com 4 °C); "
                         "abric a les 14 h (9 °C).")
        self.assertEqual(B.text_roba([hora(9, 26), hora(14, 30)], "es"), "Ropa para ir a pie: manga corta.")
        self.assertIsNone(B.text_roba([hora(23, 12)], "ca"))

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


    def test_qui_es_al_canal_no_ho_rep_dos_cops(self):
        hora = ARA.isoformat(timespec="minutes")
        self.escriu([{"id": "riera:1", "tipus": "riera", "hora": hora, "ca": "R ca", "es": "R es"},
                     {"id": "pluja:1", "tipus": "pluja", "hora": hora, "ca": "P ca", "es": "P es"}])
        subs = {"1": {"idioma": "ca", "avisos": ["riera", "pluja"], "resum": "7"},
                "2": {"idioma": "ca", "avisos": ["riera"], "resum": "7"}}
        api = Api(al_canal=["1"])
        B.reparteix(api, subs, {}, ARA)
        enviats = [(str(p["chat_id"]), p["text"]) for _, p in api.enviats]
        self.assertNotIn(("1", "R ca"), enviats)       # la riera ja li arriba pel canal
        self.assertIn(("1", "P ca"), enviats)          # la pluja, el canal no la dona
        self.assertIn(("2", "R ca"), enviats)          # no és al canal
        destins = [d for d, _ in enviats]
        self.assertEqual(destins.count("1"), 1)        # sense la previsió de les 7
        self.assertEqual(destins.count("2"), 2)

    def test_si_el_canal_falla_el_bot_ho_envia(self):
        self.escriu([{"id": "riera:1", "tipus": "riera", "hora": ARA.isoformat(), "ca": "R ca", "es": "R es"}])
        subs = {"1": {"idioma": "ca", "avisos": ["riera"], "resum": "7"}}
        api = Api(al_canal=["1"], canal_falla=True)
        B.reparteix(api, subs, {}, ARA)
        self.assertEqual([(str(p["chat_id"]), p["text"][:4]) for _, p in api.enviats],
                         [("1", "R ca"), ("1", "<b>E")])

    def test_la_benvinguda_diu_que_ja_hi_ha_marcat(self):
        subs, api = {}, Api()
        missatge = {"message": {"chat": {"id": 9, "type": "private"}, "from": {"language_code": "ca"}, "text": "/start"}}
        B.atén(api, subs, missatge)
        self.assertTrue(api.enviats[-1][1]["text"].startswith("Per començar, t'he activat"))
        self.assertEqual(B.PER_DEFECTE, ["riera", "perill"])    # el que diu el text
        api.enviats.clear()
        B.atén(api, subs, missatge)                               # qui ja hi era: sense la frase
        self.assertTrue(api.enviats[-1][1]["text"].startswith("Toca el que vulguis"))

    def test_el_menu_explica_el_canal(self):
        for idioma in ("ca", "es"):
            self.assertIn("@TempsMontflorit)", B.T[idioma]["menu"])


class AvisosPublics(unittest.TestCase):
    def test_trens_dues_passades(self):
        estat = {}
        linia = {"linies": [{"linia": "R7", "estacio": "Cerdanyola Universitat", "estat": "sense_trens"}]}
        self.assertEqual(AB.decideix(estat, {"trens": linia}, ARA), [])
        nous = AB.decideix(estat, {"trens": linia}, ARA + dt.timedelta(minutes=15))
        self.assertEqual(nous[0]["ca"], "<b>Trens: l'R7 no circula a Cerdanyola Universitat</b>")
        self.assertEqual(AB.decideix(estat, {"trens": linia}, ARA + dt.timedelta(minutes=30)), [])
        torna = {"linies": [dict(linia["linies"][0], estat="circula")]}
        AB.decideix(estat, {"trens": torna}, ARA + dt.timedelta(minutes=45))
        nous = AB.decideix(estat, {"trens": torna}, ARA + dt.timedelta(minutes=60))
        self.assertEqual(nous[0]["es"], "<b>Trenes: la R7 vuelve a circular en Cerdanyola Universitat</b>")

    def test_riera_amb_avis_orientatiu(self):
        estat = {}
        riera = {"fins": ARA.isoformat(), "mm_3h": 52, "mm_6h": 70, "radar_1h": 3.0, "index": 55, "index_6h": 75,
                 "capcalera": None, "montflorit_3h": None}
        nous = AB.decideix(estat, {"riera": riera}, ARA)
        self.assertEqual(nous[0]["nivell"], "perill")
        self.assertTrue(nous[0]["ca"].startswith("<b>Perill de desbordament de la riera de Sant Cugat a Montflorit</b>"))
        self.assertIn("Aviso en pruebas, orientativo y no oficial", nous[0]["es"])
        self.assertEqual(AB.decideix(estat, {"riera": riera}, ARA + dt.timedelta(minutes=15)), [])

    def test_perill_en_castella(self):
        r = {"clau": "previsio:ratxa", "tipus": "ratxa", "origen": "previsio", "nivell": "groc", "valor": 75,
             "des_de": "2026-10-07T15:00+02:00", "fins": "2026-10-07T16:00+02:00",
             "text": "Vent molt fort previst: ratxes de fins a 75 km/h, avui de 15 a 16 h."}
        nous = AB.decideix({}, {"riscos": [r]}, ARA)
        self.assertIn("Viento muy fuerte previsto: rachas de hasta 75 km/h, hoy de 15 a 16 h.", nous[0]["es"])
        self.assertTrue(nous[0]["es"].startswith("<b>Aviso de peligro (amarillo): viento muy fuerte</b>"))



class RepartimentAmbReintents(unittest.TestCase):
    """Un fallo pasajero de Telegram no pierde ningún aviso (ADR 0034)."""

    class ApiQueFalla(Api):
        def __init__(self, falla_chats=(), **kw):
            super().__init__(**kw)
            self.falla_chats = set(falla_chats)

        def __call__(self, metode, temps=30, **p):
            if metode == "sendMessage" and str(p["chat_id"]) in self.falla_chats:
                self.falla_chats.discard(str(p["chat_id"]))      # falla una sola vez
                raise RuntimeError("Telegram")
            return super().__call__(metode, temps, **p)

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        B.DADES = self.dir.name
        with open(os.path.join(self.dir.name, "avisos.json"), "w") as f:
            json.dump({"avisos": [{"id": "riera:1", "tipus": "riera", "hora": ARA.isoformat(timespec="minutes"),
                                   "ca": "R ca", "es": "R es"}]}, f)
        with open(os.path.join(self.dir.name, "montflorit.json"), "w") as f:
            json.dump(dades(), f)

    def tearDown(self):
        self.dir.cleanup()

    def test_un_chat_que_falla_ho_rep_al_minut_seguent(self):
        subs = {"1": {"idioma": "ca", "avisos": ["riera"], "resum": None},
                "2": {"idioma": "es", "avisos": ["riera"], "resum": None}}
        api, estat = self.ApiQueFalla(falla_chats=["2"]), {}
        B.reparteix(api, subs, estat, ARA + dt.timedelta(minutes=10))
        enviats = [(str(p["chat_id"]), p["text"]) for _, p in api.enviats]
        self.assertIn(("1", "R ca"), enviats)
        self.assertNotIn(("2", "R es"), enviats)
        self.assertEqual(estat["pendents"]["riera:1"]["chats"], ["2"])
        api.enviats.clear()
        B.reparteix(api, subs, estat, ARA + dt.timedelta(minutes=11))
        self.assertEqual([(str(p["chat_id"]), p["text"]) for _, p in api.enviats], [("2", "R es")])
        self.assertEqual(estat["pendents"], {})
        api.enviats.clear()
        B.reparteix(api, subs, estat, ARA + dt.timedelta(minutes=12))
        self.assertEqual(api.enviats, [])

    def test_el_canal_que_falla_es_reintenta_i_despres_es_deixa_estar(self):
        subs = {"1": {"idioma": "ca", "avisos": ["riera"], "resum": None}}
        api, estat = Api(canal_falla=True), {}
        # Fora de les 7, perquè el resum del canal no es barregi amb l'avís.
        ara = ARA.replace(hour=10)
        with open(os.path.join(self.dir.name, "avisos.json"), "w") as f:
            json.dump({"avisos": [{"id": "riera:1", "tipus": "riera", "hora": ara.isoformat(timespec="minutes"),
                                   "ca": "R ca", "es": "R es"}]}, f)
        B.reparteix(api, subs, estat, ara + dt.timedelta(minutes=10))
        self.assertEqual([str(p["chat_id"]) for _, p in api.enviats], ["1"])   # el bot no espera el canal
        self.assertTrue(estat["pendents"]["riera:1"]["canal"])
        api.canal_falla = False
        api.enviats.clear()
        B.reparteix(api, subs, estat, ara + dt.timedelta(minutes=11))
        self.assertEqual([(p["chat_id"], p["text"]) for _, p in api.enviats], [(B.CANAL, "R ca\n\nR es")])
        self.assertEqual(estat["pendents"], {})
        # Si el aviso caduca antes de que el canal responda, se deja de intentar.
        api, estat = Api(canal_falla=True), {}
        B.reparteix(api, subs, estat, ara + dt.timedelta(minutes=10))
        B.reparteix(api, subs, estat, ara + dt.timedelta(days=1))
        self.assertEqual(estat["pendents"], {})

    def test_el_resum_del_canal_es_reintenta_dins_de_la_mateixa_hora(self):
        subs = {}
        api, estat = Api(canal_falla=True), {}
        B.reparteix(api, subs, estat, ARA)
        self.assertNotIn("canal_resum", estat)
        api.canal_falla = False
        B.reparteix(api, subs, estat, ARA + dt.timedelta(minutes=1))
        self.assertEqual(estat["canal_resum"], ARA.date().isoformat())
        api.enviats.clear()
        B.reparteix(api, subs, estat, ARA + dt.timedelta(minutes=2))
        self.assertEqual(api.enviats, [])

    def test_trens_sense_dades_no_son_sense_incidencies(self):
        d = dades()
        d["trens"]["linies"] = [{"linia": "R4", "estat": "sense_dades"}, {"linia": "S2", "estat": "sense_dades"}]
        self.assertIn("Trens de Cerdanyola: ara mateix no hi ha dades de Renfe ni d'FGC.", B.resum(d, "ca", ARA))
        self.assertIn("ahora mismo no hay datos de Renfe ni de FGC.", B.resum(d, "es", ARA))
        d["trens"]["linies"] = [{"linia": "R4", "estat": "sense_dades"}, {"linia": "S2", "estat": "circula"}]
        self.assertIn("Trens de Cerdanyola: R4 sense dades.", B.resum(d, "ca", ARA))

if __name__ == "__main__":
    unittest.main()
