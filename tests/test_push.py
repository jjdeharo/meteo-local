# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas de los avisos en el navegador (bot/push.py, ADR 0048), sin red."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ARREL, "bot"))
import bot as B  # noqa: E402
import push as P  # noqa: E402

ARA = dt.datetime(2026, 10, 8, 7, 0).astimezone()
CA = "https://fcm.googleapis.com/fcm/send/ca"
ES = "https://updates.push.services.mozilla.com/wpush/v2/es"


class Envia:
    """El servicio de notificaciones de mentira: apunta lo que se envía."""
    def __init__(self, mortes=(), fallen=()):
        self.enviats, self.mortes, self.fallen = [], set(mortes), set(fallen)

    def __call__(self, sub, dades, ttl, urgent=False):
        if sub["endpoint"] in self.mortes:
            raise P.Morta()
        if sub["endpoint"] in self.fallen:
            raise RuntimeError("503")
        self.enviats.append((sub["endpoint"], dades, ttl, urgent))


class Push(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = self.dir.name
        B.BASE, B.DADES = d, d
        P.SUBS, P.ESTAT, P.CADENAT_SUBS = (os.path.join(d, n) for n in ("push.json", "push-estat.json", "push.lock"))
        self.avisa = unittest.mock.patch.object(B, "avisa_juanjo").start()
        self.addCleanup(unittest.mock.patch.stopall)
        self.addCleanup(self.dir.cleanup)
        claus = {"keys": {"p256dh": "x", "auth": "y"}}
        B.desa(P.SUBS, {CA: {**claus, "avisos": ["riera", "perill"], "resum": "7", "idioma": "ca"},
                        ES: {**claus, "avisos": ["pluja"], "resum": "", "idioma": "es"}})
        self.avisos([])

    def avisos(self, llista):
        B.desa(os.path.join(B.DADES, "avisos.json"), {"avisos": llista})

    def avis(self, tipus, hora=ARA):
        return {"id": f"{tipus}:1", "tipus": tipus, "hora": hora.isoformat(timespec="minutes"),
                "ca": f"<b>Avís de {tipus}</b>\nEl que passa &amp; què fer.\n{B.WEB}",
                "es": f"<b>Aviso de {tipus}</b>\nLo que pasa &amp; qué hacer.\n{B.WEB}"}

    def test_text_de_la_notificacio(self):
        n = P.notificacio("<b>Pluja d'aquí a uns 15 minuts</b>\nSegons el radar &amp; l'estació.\n\n\n"
                          f"Orientatiu.\n{B.WEB}", "./", "pluja:1")
        self.assertEqual(n, {"title": "Pluja d'aquí a uns 15 minuts", "url": "./", "tag": "pluja:1",
                             "body": "Segons el radar & l'estació.\n\nOrientatiu."})
        self.assertTrue(P.notificacio("<b>T</b>\n" + "x" * 3000)["body"].endswith("…"))
        self.assertEqual([P.url("./", "es"), P.url("sortir.html#trens", "es"), P.url("./", "ca")],
                         ["es/", "es/sortir.html#trens", "./"])

    def test_cada_avis_a_qui_l_ha_triat_i_una_sola_vegada(self):
        self.avisos([self.avis("riera"), self.avis("pluja"), self.avis("trens")])
        envia, estat = Envia(), {"resums": {CA: ARA.date().isoformat()}}     # la previsió ja ha arribat
        P.reparteix(estat, ARA, envia)
        enviats = {(e, d["title"]) for e, d, _, _ in envia.enviats}
        self.assertEqual(enviats, {(CA, "Avís de riera"), (ES, "Aviso de pluja")})
        self.assertTrue(all(u for _, _, _, u in envia.enviats))       # urgents
        self.assertEqual({d["url"] for e, d, _, _ in envia.enviats if e == ES}, {"es/"})
        P.reparteix(estat, ARA + dt.timedelta(minutes=1), envia)
        self.assertEqual(len(envia.enviats), 2)

    def test_es_reintenta_mentre_es_vigent(self):
        self.avisos([self.avis("pluja")])
        estat = {"resums": {CA: ARA.date().isoformat()}}
        P.reparteix(estat, ARA, Envia(fallen={ES}))
        self.assertEqual(estat["pendents"]["pluja:1"]["subs"], [ES])
        envia = Envia()
        P.reparteix(estat, ARA + dt.timedelta(minutes=1), envia)
        self.assertEqual([e for e, *_ in envia.enviats], [ES])
        self.assertEqual(estat["pendents"], {})
        # Si caduca sense entrar, es deixa estar.
        self.avisos([{**self.avis("pluja"), "id": "pluja:2"}])
        P.reparteix(estat, ARA, Envia(fallen={ES}))
        P.reparteix(estat, ARA + dt.timedelta(minutes=30), Envia(fallen={ES}))
        self.assertNotIn("pluja:2", estat["pendents"])

    def test_la_subscripcio_morta_s_esborra(self):
        self.avisos([self.avis("pluja")])
        P.reparteix({}, ARA, Envia(mortes={ES}))
        self.assertEqual(list(B.llegeix(P.SUBS, {})), [CA])

    def test_previsio_a_l_hora_triada_una_vegada(self):
        B.desa(os.path.join(B.DADES, "montflorit.json"), {})
        envia, estat = Envia(), {}
        P.reparteix(estat, ARA, envia)
        self.assertEqual([(e, d["tag"], ttl) for e, d, ttl, _ in envia.enviats], [(CA, "resum", P.TTL_RESUM_S)])
        P.reparteix(estat, ARA + dt.timedelta(minutes=5), envia)
        self.assertEqual(len(envia.enviats), 1)

    def test_prova(self):
        subs = B.llegeix(P.SUBS, {})
        subs[ES]["prova"] = (ARA - dt.timedelta(minutes=1)).isoformat()
        subs[CA]["prova"] = (ARA - dt.timedelta(minutes=30)).isoformat()     # massa vella
        B.desa(P.SUBS, subs)
        envia = Envia()
        P.reparteix({"resums": {CA: ARA.date().isoformat()}}, ARA, envia)
        self.assertEqual([(e, d["title"], d["url"]) for e, d, _, _ in envia.enviats],
                         [(ES, "Prueba de Temps a Montflorit", "es/avisos.html")])
        self.assertFalse(any("prova" in s for s in B.llegeix(P.SUBS, {}).values()))

    def test_altes_a_juanjo(self):
        estat = {}
        P.altes(estat)                  # la primera vegada només aprèn les que hi ha
        self.avisa.assert_not_called()
        subs = B.llegeix(P.SUBS, {})
        subs["https://web.push.apple.com/nou"] = subs[CA]
        B.desa(P.SUBS, subs)
        P.altes(estat)
        self.avisa.assert_called_once()
        self.assertIn("ja en són 3", self.avisa.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
