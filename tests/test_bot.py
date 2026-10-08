# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas del bot de Telegram y de sus avisos (ADR 0034), sin red."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ARREL)
sys.path.insert(0, os.path.join(ARREL, "bot"))
import avisos_bot as AB  # noqa: E402
import bot as B  # noqa: E402

# Les proves no escriuen mai a ~/.temps-bot: el registre d'errors i el comptador
# van a una carpeta temporal.
_BASE = tempfile.TemporaryDirectory()
B.BASE = _BASE.name
B.COMPTADOR = os.path.join(_BASE.name, "comptador.json")

ARA = dt.datetime(2026, 10, 7, 7, 0).astimezone()


class Api:
    """Telegram de mentira: apunta lo que se envía."""
    def __init__(self, bloquejats=(), al_canal=(), canal_falla=False):
        self.enviats, self.bloquejats, self.al_canal = [], set(bloquejats), set(al_canal)
        self.canal_falla = canal_falla

    def __call__(self, metode, temps=30, **p):
        if metode == "getChatMemberCount":
            return 10
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
        estat = {"resums": {"5": "2026-10-07", "6": "2026-10-07"},
                 "pendents": {"riera:1": {"avis": {}, "canal": False, "chats": ["5", "6"]}}}
        B.atén(api, subs, {"message": {"chat": {"id": 5, "type": "private"}, "from": {}, "text": "/baixa"}}, estat)
        self.assertNotIn("5", subs)
        # La baja borra el chat de todo el estado (auditoría del 07-10-2026).
        self.assertEqual(estat["resums"], {"6": "2026-10-07"})
        self.assertEqual(estat["pendents"]["riera:1"]["chats"], ["6"])
        self.assertEqual(json.dumps(estat).count('"5"'), 0)

    def test_neteja_de_restes(self):
        estat = {"resums": {"1": "d", "9": "d"}, "pendents": {"x": {"avis": {}, "canal": False, "chats": ["1", "9"]}}}
        B.neteja({"1": {}}, estat)
        self.assertEqual(estat, {"resums": {"1": "d"}, "pendents": {"x": {"avis": {}, "canal": False, "chats": ["1"]}}})

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

    def test_altes_i_baixes_del_canal_avisen_a_juanjo(self):
        avisos, original = [], B.avisa_juanjo
        B.avisa_juanjo = avisos.append
        canal = {"id": -100, "type": "channel", "username": "TempsMontflorit"}
        usuari = {"id": 5, "first_name": "Quela", "username": "Glamurosa"}
        def canvi(chat, abans, despres):
            return {"chat_member": {"chat": chat, "old_chat_member": {"status": abans, "user": usuari},
                                    "new_chat_member": {"status": despres, "user": usuari}}}
        try:
            B.atén(Api(), {}, canvi(canal, "left", "member"))
            B.atén(Api(), {}, canvi(canal, "member", "left"))
            B.atén(Api(), {}, canvi(canal, "member", "kicked"))
            B.atén(Api(), {}, canvi(canal, "member", "administrator"))   # ja hi era
            B.atén(Api(), {}, canvi({"id": -200, "type": "channel", "username": "Altre"}, "left", "member"))
        finally:
            B.avisa_juanjo = original
        self.assertEqual(avisos, ["Temps a Montflorit: alta nova al canal, Quela (@Glamurosa). Ja en són 10.",
                                  "Temps a Montflorit: baixa del canal, Quela (@Glamurosa). Ja en són 10.",
                                  "Temps a Montflorit: baixa del canal, Quela (@Glamurosa). Ja en són 10."])

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

    def test_sense_hores_no_hi_ha_previsio(self):
        # Auditoria del 08-10-2026: amb hores: null deia «Sense pluja prevista».
        for moment in (ARA, ARA.replace(hour=20)):
            d = {"generat": moment.isoformat(), "hores": None, "errors": ["previsió: caiguda"]}
            r = B.resum(d, "ca", moment)
            self.assertIn(f"Ara no hi ha previsió disponible: les dades de les {moment:%H:%M} no en porten.", r)
            self.assertNotIn("Sense pluja", r)
            self.assertIn("Ahora no hay previsión disponible", B.resum(d, "es", moment))
        # Amb hores només d'avui, a les 20 h tampoc n'hi ha de demà.
        vespre = ARA.replace(hour=20)
        d = dades(vespre)
        d["hores"] = [f for f in d["hores"] if f["hora"][:10] == vespre.date().isoformat()]
        self.assertIn("no en porten", B.resum(d, "ca", vespre))

    def test_sense_montflorit_el_zero_de_casa_no_diu_que_no_plou(self):
        self.assertEqual(B.text_ara({"ara": None, "ara_casa": {"temperatura": 20, "plou": False}}, "es"),
                         "Ahora mismo: 20 °C.")
        self.assertEqual(B.text_ara({"ara": None, "ara_casa": {"temperatura": 20, "plou": True}}, "ca"),
                         "Ara mateix: 20 °C, plou.")
        self.assertEqual(B.text_ara({"ara": {"intensitat": 0}, "ara_casa": {"temperatura": 20, "plou": False}}, "ca"),
                         "Ara mateix: 20 °C, no plou.")

    def test_avis_aemet_que_ve_d_ahir(self):
        # Auditoria del 08-10-2026: un avís començat ahir i vigent avui no sortia.
        migdia = ARA.replace(hour=12)
        ahir, dema = (migdia - dt.timedelta(days=1)).date(), (migdia + dt.timedelta(days=1)).date()
        d = {"avisos": [{"inicio": f"{ahir}T23:00:00+02:00", "fin": f"{migdia.date()}T13:59:59+02:00",
                         "nivel": "taronja", "tipo": "pluja", "zona": "Prelitoral de Barcelona"}]}
        self.assertEqual(B.text_avisos_aemet(d, "es", migdia.date(), migdia),
                         ["Aviso naranja de la AEMET por lluvia hasta las 14:00."])
        self.assertEqual(B.text_avisos_aemet(d, "ca", dema, migdia), [])
        # I el de demà que comença avui a la nit també compta per a demà.
        d = {"avisos": [{"inicio": f"{migdia.date()}T22:00:00+02:00", "fin": f"{dema}T05:59:59+02:00",
                         "nivel": "groc", "tipo": "vent", "zona": "Prelitoral de Barcelona"}]}
        self.assertEqual(B.text_avisos_aemet(d, "ca", dema, migdia), ["Avís groc de l'AEMET per vent de 22:00 a 06:00."])

    def test_a_les_20_la_de_dema(self):
        vespre = ARA.replace(hour=20)
        d = dades(vespre)
        d["avisos"].append({"inicio": "2026-10-08T10:00:00+02:00", "fin": "2026-10-08T19:59:59+02:00",
                            "nivel": "groc", "tipo": "pluja", "zona": "Prelitoral de Barcelona"})
        r = B.resum(d, "ca", vespre)
        self.assertTrue(r.startswith("<b>Previsió per a demà, dijous, a Montflorit</b> (fins a les 20 h)"))
        self.assertIn("Temperatura: entre ", r)
        self.assertIn("Pluja: possible de 12 a 15 h (probabilitat fins al 40 %).", r)
        self.assertIn("Avís groc de l'AEMET per pluja de 10:00 a 20:00.", r)
        self.assertNotIn("Ara mateix", r)
        self.assertNotIn("Trens", r)
        self.assertNotIn("Aquesta nit", r)
        self.assertTrue(B.resum(d, "es", vespre).startswith("<b>Previsión para mañana, jueves, en Montflorit</b> (hasta las 20 h)"))

    def test_pluja_aquesta_nit(self):
        # El 08-10-2026 deia «Esta noche: posible de 20 a 23 h»: hi faltava la pluja.
        vespre = ARA.replace(hour=20)
        d = dades(vespre)
        for f in d["hores"][:3]:
            f["probabilitat"] = 0.56
        self.assertIn("Aquesta nit: pluja possible de 20 a 23 h (probabilitat fins al 56 %).", B.resum(d, "ca", vespre))
        self.assertIn("Esta noche: lluvia posible de 20 a 23 h (probabilidad hasta el 56 %).", B.resum(d, "es", vespre))

    def test_roba_de_tot_el_dia(self):
        # Les dades de prova van de 15 °C (7 h) a 24 °C (16 h): dues peces, per ordre d'hora.
        self.assertIn("Roba per anar a peu: jaqueta lleugera o jersei a les 7 h (15 °C); "
                      "màniga curta o màniga llarga fina a les 16 h (24 °C).", B.resum(dades(), "ca", ARA))
        self.assertIn("Ropa para ir a pie: chaqueta ligera o jersey a las 7 h (15 °C); "
                      "manga corta o manga larga fina a las 16 h (24 °C).", B.resum(dades(), "es", ARA))

    def test_la_roba_al_final_i_apart(self):
        # Juanjo, 08-10-2026: la ropa, al final y separada del resto.
        for moment in (ARA, ARA.replace(hour=20)):
            for idioma in ("ca", "es"):
                linies = B.resum(dades(moment), idioma, moment).split("\n")
                self.assertEqual(linies[-1], B.WEB)
                self.assertTrue(linies[-2].startswith(("Roba per anar a peu", "Ropa para ir a pie")))
                self.assertEqual(linies[-3], "")
                self.assertNotIn("", linies[:-3])

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

    def test_ara_amb_el_mateix_limit_i_l_hora_de_la_mesura(self):
        # Auditoría del 07-10-2026: /ara contestaba con medidas de hace horas.
        d = dades()
        d["ara"]["hora"] = (ARA - dt.timedelta(minutes=9)).isoformat(timespec="minutes")
        self.assertEqual(B.text_ara_bot(d, "ca", ARA), "Ara mateix a Montflorit: 16 °C, no plou. (mesura de les 06:51)")
        self.assertEqual(B.text_ara_bot(d, "es", ARA), "Ahora mismo en Montflorit: 16 °C, no llueve. (medida de las 06:51)")
        vell = dades(ARA - dt.timedelta(hours=3))
        self.assertIn("ara no puc dir el temps que fa", B.text_ara_bot(vell, "ca", ARA))
        self.assertIn("ahora no puedo decir el tiempo que hace", B.text_ara_bot(vell, "es", ARA))
        # Medida congelada con un generat reciente: tampoco.
        d["ara"]["hora"] = (ARA - dt.timedelta(hours=5)).isoformat(timespec="minutes")
        self.assertIn("des de les 02:00", B.text_ara_bot(d, "ca", ARA))
        self.assertEqual(B.text_ara_bot({}, "ca", ARA), B.T["ca"]["velles_ara"].format("?"))


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
        self.assertIn((B.CANAL, "R ca"), enviats)            # el canal, solo en catalán
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
        self.assertTrue(canal.startswith("<b>El temps avui"))
        self.assertNotIn("El tiempo hoy", canal)              # el canal, solo en catalán
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

    def test_qui_te_el_bot_en_castella_tampoc_ho_rep_dos_cops(self):
        # El canal va en catalán, pero tampoco se repite a quien lee en castellano (Juanjo, 08-10-2026).
        self.escriu([{"id": "riera:1", "tipus": "riera", "hora": ARA.isoformat(), "ca": "R ca", "es": "R es"},
                     {"id": "pluja:1", "tipus": "pluja", "hora": ARA.isoformat(), "ca": "P ca", "es": "P es"}])
        subs = {"1": {"idioma": "es", "avisos": ["riera", "pluja"], "resum": "7"}}
        api = Api(al_canal=["1"])
        B.reparteix(api, subs, {}, ARA)
        rebut = [p["text"] for _, p in api.enviats if str(p["chat_id"]) == "1"]
        self.assertEqual(rebut, ["P es"])      # la pluja sí; la riera i el resum, pel canal

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


class Consultes(unittest.TestCase):
    """/dema, /radar, /trens i /avisos_actius (Juanjo, 08-10-2026): només llegeixen,
    i la llista de subscriptors queda igual."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        B.DADES = self.dir.name
        d = dades()
        d["radar"] = {"hora": ARA.isoformat(timespec="minutes"), "imatge": "rainviewer", "cap_a": "a l'est",
                      "velocitat_kmh": 37, "arriba": None, "possible": None}
        d["plans"] = [{"pla": "INUNCAT", "nom": "d'inundacions", "fase": "emergència", "comunicat": None}]
        d["trens"] = {"linies": [{"linia": "R4", "estacio": "Cerdanyola del Vallès", "estat": "incidencies",
                                  "avisos": [{"ca": "Obres <a Montcada>.", "es": "Obras en Montcada."}]},
                                 {"linia": "S2", "estacio": "Bellaterra", "estat": "circula", "avisos": []}]}
        with open(os.path.join(self.dir.name, "montflorit.json"), "w") as f:
            json.dump(d, f)

    def tearDown(self):
        self.dir.cleanup()

    def ordre(self, text, subs, chat=7, idioma="ca"):
        api = Api()
        missatge = {"message": {"chat": {"id": chat, "type": "private"}, "from": {"language_code": idioma}, "text": text}}
        with unittest.mock.patch.object(B, "ara", return_value=ARA):
            B.atén(api, subs, missatge)
        return api.enviats[-1][1]["text"]

    def test_les_consultes_no_toquen_ningu(self):
        subs = {"1": {"idioma": "ca", "avisos": ["riera"], "resum": "7", "alta": "x"},
                "7": {"idioma": "es", "avisos": ["perill", "pluja"], "resum": "20", "alta": "y"}}
        abans = json.dumps(subs, sort_keys=True)
        for o in ("/dema", "/radar", "/trens", "/avisos_actius", "/ara", "/resum", "/ajuda", "/xyz"):
            self.ordre(o, subs, chat=7, idioma="es")
        self.assertEqual(json.dumps(subs, sort_keys=True), abans)

    def test_respostes(self):
        subs = {"7": {"idioma": "ca", "avisos": [], "resum": None}}
        self.assertIn("No s'acosta pluja en 2 hores.", self.ordre("/radar", subs))
        self.assertIn("https://www.rainviewer.com/map.html", self.ordre("/radar", subs))
        trens = self.ordre("/trens", subs)
        # Cada línia una sola vegada, amb el seu avís al costat i el text de l'operador escapat.
        self.assertIn("<b>R4</b> (Cerdanyola del Vallès): amb incidències. «Obres &lt;a Montcada&gt;.»", trens)
        self.assertEqual(trens.count("R4"), 1)
        self.assertIn("<b>S2</b> (Bellaterra): sense incidències\n", trens)
        self.assertIn("<b>Protecció Civil</b>\nPla d'inundacions (INUNCAT) en fase d'emergència.", self.ordre("/avisos_actius", subs))
        self.assertTrue(self.ordre("/dema", subs).startswith("<b>Previsió per a demà"))
        # /resum, sempre la d'avui, també de vespre; el resum programat de les 20 h, la de demà.
        with unittest.mock.patch.object(B, "ara", return_value=ARA.replace(hour=20)):
            d = json.load(open(os.path.join(self.dir.name, "montflorit.json")))
            d["generat"] = ARA.replace(hour=20).isoformat()
            json.dump(d, open(os.path.join(self.dir.name, "montflorit.json"), "w"))
            api = Api()
            B.atén(api, subs, {"message": {"chat": {"id": 7, "type": "private"}, "from": {}, "text": "/resum"}})
        self.assertTrue(api.enviats[-1][1]["text"].startswith("<b>El temps avui"))
        self.assertTrue(B.resum(d, "ca", ARA.replace(hour=20)).startswith("<b>Previsió per a demà"))
        subs["7"]["idioma"] = "es"
        self.assertIn("en fase de emergencia", self.ordre("/avisos_actius", subs))
        # El temps excepcional calculat també hi surt, dit que no és oficial.
        d = json.load(open(os.path.join(self.dir.name, "montflorit.json")))
        d["riscos"] = [{"tipus": "ratxa", "nivell": "groc", "origen": "mesura", "valor": 75, "llindar": 70,
                        "unitat": "km/h", "text": "Ara bufa vent molt fort: ratxes de 75 km/h."}]
        json.dump(d, open(os.path.join(self.dir.name, "montflorit.json"), "w"))
        r = self.ordre("/avisos_actius", subs)
        self.assertIn("<b>Tiempo excepcional</b>\n<i>Lo calcula Temps a Montflorit", r)
        subs["7"]["idioma"] = "ca"
        self.assertIn("Ara bufa vent molt fort: ratxes de 75\u00a0km/h.", self.ordre("/avisos_actius", subs))
        subs["7"]["idioma"] = "es"
        self.assertIn("va hacia el este", self.ordre("/radar", subs))

    def test_entorn_a_avisos_actius(self):
        # Incendis a prop i Pla Alfa des del 3 (ADR 0046).
        d = json.load(open(os.path.join(self.dir.name, "montflorit.json")))
        d["entorn"] = {"incendis": [{"id": "x", "municipi": "Sant Cugat del Vallès", "km": 3.2,
                                     "inici": ARA.isoformat()}],
                       "pla_alfa": {"avui": 4, "dema": 2, "tancaments": []}}
        json.dump(d, open(os.path.join(self.dir.name, "montflorit.json"), "w"))
        subs = {"7": {"idioma": "ca", "avisos": [], "resum": None}}
        r = self.ordre("/avisos_actius", subs)
        self.assertIn("<b>Bombers</b>\nIncendi forestal a Sant Cugat del Vallès, a 3,2 km", r)
        self.assertIn("<b>Pla Alfa</b>\nNivell 4 avui a Cerdanyola", r)
        self.assertNotIn("nivell 2", r)
        self.assertNotIn("Avisos actius", r)             # sense títol: l'ordre ja diu què és
        self.assertNotIn("de l'AEMET per", r)          # l'AEMET ja és el títol del bloc
        self.assertIn("\n\n<b>", r)                     # un bloc per font
        subs["7"]["idioma"] = "es"
        self.assertIn("<b>Plan Alfa</b>\nNivel 4 hoy en Cerdanyola", self.ordre("/avisos_actius", subs))

    def test_el_menu_cap_en_una_linia(self):
        # «Situacions de perill», curt (Juanjo, 08-10-2026: amb el parèntesi no hi cabia).
        self.assertEqual(B.T["ca"]["perill"], "Situacions de perill")
        self.assertEqual(B.T["es"]["perill"], "Situaciones de peligro")

    def test_dades_velles(self):
        subs = {"7": {"idioma": "ca", "avisos": [], "resum": None}}
        with unittest.mock.patch.object(B, "ara", return_value=ARA + dt.timedelta(hours=3)):
            api = Api()
            B.atén(api, subs, {"message": {"chat": {"id": 7, "type": "private"}, "from": {}, "text": "/trens"}})
        self.assertIn("no s'actualitzen", api.enviats[-1][1]["text"])


class Comptador(unittest.TestCase):
    """Comptador anònim de les ordres (Juanjo, 08-10-2026): sense qui, sense Juanjo."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.abans = B.COMPTADOR
        B.COMPTADOR = os.path.join(self.dir.name, "comptador.json")

    def tearDown(self):
        B.COMPTADOR = self.abans
        self.dir.cleanup()

    def test_compta_sense_qui_i_sense_juanjo(self):
        with unittest.mock.patch.object(B, "chat_juanjo", return_value="99"):
            for ordre, chat in (("/resum", "1"), ("/resum", "2"), ("/trens", "1"), ("/resum", "99"), ("/hola", "3")):
                B.compta(ordre, chat, dia="2026-10-08")
        c = json.load(open(B.COMPTADOR))
        self.assertEqual(c, {"2026-10-08": {"/resum": 2, "/trens": 1, "altres": 1}})
        self.assertNotIn("1", json.dumps(c).replace('"/resum": 2', "").replace('"/trens": 1', "").replace("2026-10-08", "").replace('"altres": 1', ""))
        text = B.text_estadistiques(avui=dt.date(2026, 10, 8))
        self.assertIn("Últims 7 dies: 4 (/resum 2, /trens 1, altres 1)", text)

    def test_estadistiques_nomes_per_a_juanjo(self):
        B.compta("/ara", "1", dia=ARA.date().isoformat())
        with unittest.mock.patch.object(B, "chat_juanjo", return_value="99"), \
                unittest.mock.patch.object(B, "ara", return_value=ARA):
            api = Api()
            B.atén(api, {"99": {"idioma": "es", "avisos": [], "resum": None}},
                   {"message": {"chat": {"id": 99, "type": "private"}, "from": {}, "text": "/estadistiques"}})
            self.assertTrue(api.enviats[-1][1]["text"].startswith("Usos del bot"))
            api = Api()
            B.atén(api, {"5": {"idioma": "es", "avisos": [], "resum": None}},
                   {"message": {"chat": {"id": 5, "type": "private"}, "from": {}, "text": "/estadistiques"}})
            self.assertFalse(api.enviats[-1][1]["text"].startswith("Usos del bot"))


class AvisosPublics(unittest.TestCase):
    def test_riera_avis_i_final(self):
        # Atenció una vegada i, 3 hores després de calmar-se, el missatge de final (Juanjo, 08-10-2026).
        def riera(index):
            return {"fins": ARA.isoformat(timespec="minutes"), "mm_3h": index, "mm_6h": index + 20,
                    "radar_1h": 0, "index": index, "index_6h": index + 20}
        estat, nous = {}, []
        for i, index in enumerate([38, 30, 10, 5, 5, 5, 5, 5, 5]):
            nous += AB.decideix(estat, {"riera": riera(index)}, ARA + dt.timedelta(minutes=30 * i))
        self.assertEqual([(a["nivell"], a["id"].split(":")[-1]) for a in nous], [("atencio", "atencio"), ("fi", "fi")])
        self.assertTrue(nous[0]["ca"].startswith("<b>Atenció: possible desbordament"))
        self.assertTrue(nous[1]["ca"].startswith("<b>Riera de Sant Cugat: ja no hi ha risc de desbordament</b>"))
        self.assertIn("ya no hay riesgo de desbordamiento", nous[1]["es"])
        self.assertIn("Avís en proves", nous[1]["ca"])
        self.assertEqual(nous[0]["tipus"], nous[1]["tipus"], "riera")

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

    def test_pluja_amb_el_radar(self):
        # El radar en directe que ha donat l'avís: enllaç a Telegram; a la
        # notificació, en tocar-la (Juanjo, 08-10-2026).
        def salida(imatge, arriba="2026-10-07T07:15+02:00"):
            return {"radar": {"imatge": imatge, "hora": "2026-10-07T07:00+02:00", "arriba": arriba,
                              "arriba_mm_h": 5}}
        with unittest.mock.patch.object(AB.PA, "falta_min", return_value=12):
            t = AB.text_pluja(salida("rainviewer"), ARA)
        self.assertEqual(t["url"], AB.C.RADAR_EN_DIRECTE["rainviewer"])
        self.assertTrue(t["ca"].endswith(f'Radar en directe: <a href="{AB.html.escape(t["url"])}">RainViewer</a>'))
        self.assertIn("Puede ser fuerte.\nRadar en directo:", t["es"])
        self.assertTrue(t["push"]["ca"].endswith("Pot ser forta. Toca per veure el radar."))
        self.assertNotIn("<a ", t["push"]["es"])
        with unittest.mock.patch.object(AB.PA, "falta_min", return_value=1):
            t = AB.text_pluja(salida("meteocat"), ARA)
        self.assertEqual(t["url"], "https://www.meteo.cat/observacions/radar")
        self.assertIn("Pluja imminent", t["ca"])

    def test_el_radar_en_directe_igual_a_tot_arreu(self):
        casa_js = open(os.path.join(ARREL, "web", "casa.js"), encoding="utf-8").read()
        for font, url in AB.C.RADAR_EN_DIRECTE.items():
            self.assertEqual(B.RADAR_EN_DIRECTE[font], url)
            self.assertIn(f"{font}: '{url}'", casa_js)

    def test_perill_acabat(self):
        # Quan ja no en queda cap, un avís que ho diu (abans només el rebia Juanjo).
        r = {"clau": "previsio:ratxa", "tipus": "ratxa", "origen": "previsio", "nivell": "groc", "valor": 75,
             "text": "Vent molt fort previst."}
        dades = {"hores": [{}], "ara": {"temperatura": 18}}
        estat = {}
        AB.decideix(estat, {**dades, "riscos": [r]}, ARA)
        self.assertEqual(AB.decideix(estat, dades, ARA + dt.timedelta(hours=1)), [])
        fi = AB.decideix(estat, dades, ARA + dt.timedelta(hours=3))
        self.assertEqual([(a["tipus"], a["nivell"]) for a in fi], [("perill", "fi")])
        self.assertTrue(fi[0]["ca"].startswith("<b>Ja no hi ha cap situació de perill a Montflorit</b>"))
        self.assertEqual(AB.decideix(estat, dades, ARA + dt.timedelta(hours=4)), [])
        # Sense previsió no es pot saber: no es dona per acabat.
        estat = {}
        AB.decideix(estat, {**dades, "riscos": [r]}, ARA)
        self.assertEqual(AB.decideix(estat, {}, ARA + dt.timedelta(hours=3)), [])



class Registre(unittest.TestCase):
    """Los fallos de Telegram dejan rastro y un aviso que caduca sin
    entregarse se dice (auditoría del 07-10-2026)."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        B.DADES = B.BASE = self.dir.name
        self.avisos, self.original = [], B.avisa_juanjo
        B.avisa_juanjo = self.avisos.append

    def tearDown(self):
        B.avisa_juanjo = self.original
        self.dir.cleanup()

    def registre(self):
        try:
            with open(os.path.join(self.dir.name, "errors.log")) as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def test_un_avis_que_caduca_queda_apuntat_i_avisa(self):
        ara = ARA.replace(hour=10)
        with open(os.path.join(self.dir.name, "avisos.json"), "w") as f:
            json.dump({"avisos": [{"id": "riera:1", "tipus": "riera", "hora": ara.isoformat(timespec="minutes"),
                                   "ca": "R ca", "es": "R es"}]}, f)
        with open(os.path.join(self.dir.name, "montflorit.json"), "w") as f:
            json.dump(dades(), f)
        subs = {"1": {"idioma": "ca", "avisos": ["riera"], "resum": None}}
        api, estat = Api(canal_falla=True), {}
        api.falla_tot = True

        class Tot(Api):
            def __call__(self, metode, temps=30, **p):
                if metode == "sendMessage":
                    raise RuntimeError("Too Many Requests")
                return super().__call__(metode, temps, **p)
        api = Tot()
        B.reparteix(api, subs, estat, ara + dt.timedelta(minutes=1))
        self.assertIn("el canal no lo acepta: Too Many Requests", self.registre())
        self.assertIn("1 chat(s) sin entregar: Too Many Requests", self.registre())
        self.assertNotIn('"1"', self.registre())      # sin identificadores
        self.assertEqual(self.avisos, [])
        B.reparteix(api, subs, estat, ara + dt.timedelta(hours=4))
        self.assertIn("aviso riera:1 caducado sin entregar a el canal y 1 chat(s)", self.registre())
        self.assertEqual(len(self.avisos), 1)
        self.assertIn("ha caducado sin llegar", self.avisos[0])
        self.assertEqual(estat["pendents"], {})
        # Un aviso de lluvia caducado deja rastro, pero no molesta a Juanjo.
        with open(os.path.join(self.dir.name, "avisos.json"), "w") as f:
            json.dump({"avisos": [{"id": "pluja:1", "tipus": "pluja", "hora": ara.isoformat(timespec="minutes"),
                                   "ca": "P", "es": "P"}]}, f)
        subs = {"1": {"idioma": "ca", "avisos": ["pluja"], "resum": None}}
        B.reparteix(api, subs, estat, ara + dt.timedelta(minutes=5))
        B.reparteix(api, subs, estat, ara + dt.timedelta(minutes=40))
        self.assertIn("aviso pluja:1 caducado", self.registre())
        self.assertEqual(len(self.avisos), 1)


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
        self.assertEqual([(p["chat_id"], p["text"]) for _, p in api.enviats], [(B.CANAL, "R ca")])
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


class AltesIRiscos(unittest.TestCase):
    def test_un_text_qualsevol_no_dona_d_alta(self):
        api, subs = Api(), {}
        B.atén(api, subs, {"message": {"chat": {"id": 5, "type": "private"}, "from": {}, "text": "hola"}})
        self.assertEqual(subs, {})
        self.assertEqual(len(api.enviats), 1)       # només l'ajuda
        B.atén(api, subs, {"message": {"chat": {"id": 5, "type": "private"}, "from": {}, "text": "/start"}})
        self.assertIn("5", subs)

    def test_un_risc_no_caduca_mentre_falten_dades(self):
        r = {"clau": "previsio:ratxa", "tipus": "ratxa", "origen": "previsio", "nivell": "groc", "valor": 75,
             "des_de": "2026-10-07T15:00+02:00", "fins": "2026-10-07T16:00+02:00",
             "text": "Vent molt fort previst: ratxes de fins a 75 km/h, avui de 15 a 16 h."}
        complet = {"riscos": [r], "hores": [{}], "ara": {"temperatura": 1}}
        estat = {}
        self.assertEqual(len(AB.decideix(estat, complet, ARA)), 1)
        # Sense previsió ni estació durant hores: el risc segueix apuntat i no es repeteix en tornar.
        AB.decideix(estat, {"riscos": [], "hores": None, "ara": None}, ARA + dt.timedelta(hours=5))
        self.assertIn("previsio:ratxa", estat["perill"])
        self.assertEqual(AB.decideix(estat, complet, ARA + dt.timedelta(hours=6)), [])
        # Amb dades i sense veure'l 3 hores, caduca i es tornaria a avisar.
        AB.decideix(estat, {"riscos": [], "hores": [{}], "ara": {"temperatura": 1}}, ARA + dt.timedelta(hours=10))
        self.assertNotIn("previsio:ratxa", estat["perill"])

if __name__ == "__main__":
    unittest.main()
