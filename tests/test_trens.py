# SPDX-License-Identifier: AGPL-3.0-or-later
"""Proves de l'estat dels trens (sense xarxa)."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402
import trens as T  # noqa: E402

ARA = dt.datetime(2026, 10, 7, 7, 50).astimezone()
R7 = C.TRENS_ESTACIONS["R7"]


def camp(num, valor):
    """Un camp protobuf de longitud variable (o un enter)."""
    def varint(n):
        res = b""
        while True:
            b = n & 0x7F
            n >>= 7
            res += bytes([b | (0x80 if n else 0)])
            if not n:
                return res
    if isinstance(valor, int):
        return varint(num << 3) + varint(valor)
    if isinstance(valor, str):
        valor = valor.encode()
    return varint(num << 3 | 2) + varint(len(valor)) + valor


def traduccio(text, idioma):
    return camp(1, camp(1, text) + camp(2, idioma))


class Protobuf(unittest.TestCase):
    def test_avis_gtfs_rt(self):
        alerta = (camp(1, camp(1, 1791350000)) + camp(5, camp(2, "S2")) + camp(5, camp(2, "S1"))
                  + camp(11, traduccio("Obres a Bellaterra.", "ca") + traduccio("Obras en Bellaterra.", "es")))
        feed = camp(1, camp(1, "2.0")) + camp(2, camp(1, "a1") + camp(5, alerta))
        self.assertEqual(T.avisos_pb(feed), [{"rutes": ["S2", "S1"], "text": {
            "ca": "Obres a Bellaterra.", "es": "Obras en Bellaterra."}, "inici": T.iso(1791350000), "fi": None}])
        amb_fi = feed.replace(camp(1, camp(1, 1791350000)), camp(1, camp(1, 1791350000) + camp(2, 1791353600)))
        self.assertEqual(T.avisos_pb(amb_fi)[0]["fi"], T.iso(1791353600))
        self.assertEqual(T.iso(1791350000), "2026-10-07T07:13+02:00")
        self.assertIsNone(T.iso(None))

    def test_avisos_renfe_amb_inici(self):
        # Formato real de alerts.json (08-10-2026): activePeriod con start en segundos.
        dades = {"entity": [{"alert": {"activePeriod": [{"start": "1791354540"}],
                                       "informedEntity": [{"routeId": "51T0036R8"}],
                                       "descriptionText": {"translation": [
                                           {"text": "Circulació ferroviària a tot el recorregut.", "language": "es"},
                                           {"text": "Circulación ferroviaria en todo su recorrido.", "language": "es"}]}}},
                            {"alert": {"informedEntity": [{"routeId": "51T0036R8"}],
                                       "descriptionText": {"translation": [{"text": "Sense data.", "language": "es"}]}}}]}
        r = T.avisos_renfe(dades)
        self.assertEqual([a["linies"] for a in r], [{"R8"}, {"R8"}])
        self.assertEqual(r[0]["inici"], "2026-10-07T08:29+02:00")
        self.assertIsNone(r[0]["fi"])          # sense end: obert
        self.assertIsNone(r[1]["inici"])
        dades["entity"][0]["alert"]["activePeriod"][0]["end"] = "1791358140"
        self.assertEqual(T.avisos_renfe(dades)[0]["fi"], "2026-10-07T09:29+02:00")

    def test_un_avis_futur_o_acabat_no_decideix(self):
        # Auditoria del 08-10-2026: un avís de carretera per a demà posava «bus» avui.
        def avis(inici, fi):
            return {"linies": {"R8"}, "inici": inici, "fi": fi,
                    "text": {"ca": "Servei alternatiu per carretera.", "es": "Servicio alternativo por carretera."}}
        dema = (ARA + dt.timedelta(days=1)).isoformat(timespec="minutes")
        ahir = (ARA - dt.timedelta(days=1)).isoformat(timespec="minutes")
        fa_una_hora = (ARA - dt.timedelta(hours=1)).isoformat(timespec="minutes")
        mou = [{"linia": "R8", "lat": 0, "lon": 0}]
        self.assertEqual(T.estat_linia("R8", mou, None, [avis(dema, None)], ARA)["estat"], "incidencies")
        self.assertEqual(T.estat_linia("R8", mou, None, [avis(ahir, fa_una_hora)], ARA)["estat"], "incidencies")
        self.assertEqual(T.estat_linia("R8", mou, None, [avis(ahir, None)], ARA)["estat"], "bus")
        self.assertEqual(T.estat_linia("R8", mou, None, [avis(None, None)], ARA)["estat"], "bus")
        # L'avís futur es mostra igualment.
        self.assertEqual(len(T.estat_linia("R8", mou, None, [avis(dema, None)], ARA)["avisos"]), 1)

    def test_posicions_velles_no_serveixen(self):
        feed = {"header": {"timestamp": str(int((ARA - dt.timedelta(minutes=11)).timestamp()))},
                "entity": [{"vehicle": {"vehicle": {"label": "R8-1", "id": "1"}, "position": {"latitude": 41.5, "longitude": 2.1}}}]}
        with self.assertRaises(ValueError):
            T.trens_renfe(feed, ARA)
        feed["header"]["timestamp"] = str(int((ARA - dt.timedelta(minutes=2)).timestamp()))
        self.assertEqual([t["linia"] for t in T.trens_renfe(feed, ARA)], ["R8"])


class Idiomes(unittest.TestCase):
    def test_renfe_marca_els_dos_com_a_castella(self):
        r = T.idiomes(["Per causes alienes a Rodalies no es pot garantir la prestació del servei.\r\n",
                       "Por causas ajenas a Rodalies no se puede garantizar la prestación del servicio."])
        self.assertTrue(r["ca"].startswith("Per causes"))
        self.assertTrue(r["es"].startswith("Por causas"))

    def test_un_sol_idioma_es_queda_tal_qual(self):
        r = T.idiomes(["Servicio alternativo por carretera en todo su recorrido."])
        self.assertEqual(r["ca"], r["es"])

    def test_linia_renfe(self):
        self.assertEqual(T.linia_renfe("51T0037R7"), "R7")
        self.assertEqual(T.linia_renfe("51T0094R2N"), "R2N")
        self.assertIsNone(T.linia_renfe("10T0001C1"))


def tren(linia, lat, lon, aturat=False, ident="1"):
    return {"id": ident, "linia": linia, "lat": lat, "lon": lon, "aturat": aturat}


class Estat(unittest.TestCase):
    def test_aturat_a_l_estacio_no_circula(self):
        # 07-10-2026: dos trens de l'R7 «a l'estació», sense moure's.
        abans = {"hora": (ARA - dt.timedelta(minutes=15)).isoformat(), "posicions": {"1": R7}}
        self.assertEqual(T.es_mouen([tren("R7", *R7, aturat=True)], abans, ARA), [])
        # Sense passada anterior, l'aturat tampoc no compta.
        self.assertEqual(T.es_mouen([tren("R7", *R7, aturat=True)], None, ARA), [])

    def test_lluny_de_l_estacio_no_compta(self):
        # L'R4 pel tram sud (Martorell) no serveix a qui surt de Cerdanyola.
        self.assertEqual(T.es_mouen([tren("R4", 41.47, 1.93)], None, ARA), [])

    def test_es_mou(self):
        abans = {"hora": (ARA - dt.timedelta(minutes=15)).isoformat(), "posicions": {"1": (41.48, 2.12)}}
        self.assertEqual(len(T.es_mouen([tren("R7", *R7)], abans, ARA)), 1)

    def avis(self, linies, ca, es=None, inici=None):
        return {"linies": set(linies), "text": {"ca": ca, "es": es or ca}, "inici": inici}

    def test_estats(self):
        bus = self.avis(["R8"], "Servei alternatiu per carretera en tot el seu recorregut.")
        general = self.avis(["R4", "R7", "R8"], "No es pot garantir la prestació del servei.")
        mou = [tren("R7", *R7)]
        self.assertEqual(T.estat_linia("R8", [], None, [bus, general], ARA)["estat"], "bus")
        self.assertEqual(T.estat_linia("R7", mou, None, [general], ARA)["estat"], "incidencies")
        self.assertEqual(T.estat_linia("R7", mou, None, [], ARA)["estat"], "circula")
        self.assertEqual(T.estat_linia("R4", [], None, [general], ARA)["estat"], "sense_trens")
        nit = ARA.replace(hour=2)
        self.assertEqual(T.estat_linia("R4", [], None, [], nit)["estat"], "fora_horari")

    def test_horari_de_cada_linia(self):
        # 08-10-2026, 05:39: «l'R7 no circula», però el primer tren és a les 06:40.
        general = self.avis(["R4", "R7", "R8"], "No es pot garantir la prestació del servei.")
        matinada = ARA.replace(hour=5, minute=39)
        self.assertEqual(T.estat_linia("R7", [], None, [general], matinada)["estat"], "fora_horari")
        self.assertEqual(T.estat_linia("R8", [], None, [], matinada)["estat"], "fora_horari")
        self.assertEqual(T.estat_linia("R4", [], None, [], matinada)["estat"], "fora_horari")   # 05:20 + 30 min
        self.assertEqual(T.estat_linia("R4", [], None, [], ARA.replace(hour=5, minute=50))["estat"], "sense_trens")
        self.assertEqual(T.estat_linia("S2", [], None, [], ARA.replace(hour=5, minute=45))["estat"], "sense_trens")
        # Mitja hora després del primer tren de l'R7 (06:35 a Cerdanyola), ja compta.
        self.assertEqual(T.estat_linia("R7", [], None, [], ARA.replace(hour=7, minute=4))["estat"], "fora_horari")
        self.assertEqual(T.estat_linia("R7", [], None, [], ARA.replace(hour=7, minute=5))["estat"], "sense_trens")
        # I després de l'últim (22:40), tampoc; l'R4 fins a mitjanit.
        self.assertEqual(T.estat_linia("R7", [], None, [], ARA.replace(hour=22, minute=50))["estat"], "fora_horari")
        self.assertEqual(T.estat_linia("R4", [], None, [], ARA.replace(hour=23, minute=50))["estat"], "sense_trens")
        # Una línia que es mou circula a qualsevol hora.
        self.assertEqual(T.estat_linia("R7", [tren("R7", *R7)], None, [], matinada)["estat"], "circula")

    def test_vist_fa_poc_circula(self):
        # Amb trens cada 30 minuts, en una passada pot no haver-n'hi cap a prop.
        fa_poc = (ARA - dt.timedelta(minutes=20)).isoformat()
        fa_molt = (ARA - dt.timedelta(minutes=C.TRENS_VIST_MIN + 5)).isoformat()
        self.assertEqual(T.estat_linia("R4", [], fa_poc, [], ARA)["estat"], "circula")
        self.assertEqual(T.estat_linia("R4", [], fa_molt, [], ARA)["estat"], "sense_trens")

    def test_l_avis_propi_va_primer(self):
        bus = self.avis(["R8"], "Servei alternatiu per carretera.")
        general = self.avis(["R4", "R8"], "No es pot garantir el servei.")
        r = T.estat_linia("R8", [], None, [general, bus, bus], ARA)
        self.assertEqual([a["ca"] for a in r["avisos"]], ["Servei alternatiu per carretera.",
                                                          "No es pot garantir el servei."])

    def test_l_avis_mes_recent_mana(self):
        # 07-10-2026, 20:21: l'R8 tenia un avís vell de servei per carretera i
        # un de nou de circulació ferroviària, i sortia «bus» (auditoria).
        vespre = ARA.replace(hour=20, minute=21)
        bus = self.avis(["R8"], "Servei alternatiu per carretera en tot el seu recorregut.", inici="2026-10-06T18:33+02:00")
        tren = self.avis(["R8"], "Circulació ferroviària a tot el recorregut.", inici="2026-10-07T09:49+02:00")
        general = self.avis(["R4", "R7", "R8"], "No es pot garantir la prestació del servei.", inici="2026-10-07T09:02+02:00")
        r = T.estat_linia("R8", [], None, [bus, general, tren], vespre)
        # Sense trens vistos, però l'avís oficial més nou diu que hi ha
        # circulació: mana ell, i es diu que no se n'ha vist cap (09-10-2026).
        self.assertEqual((r["estat"], r.get("no_vist")), ("incidencies", True))
        # De servei, només el més nou: el de carretera ja no val. Després, el general.
        self.assertEqual([a["ca"][:12] for a in r["avisos"]], ["Circulació f", "No es pot ga"])
        # Al revés (el de carretera és el nou), bus.
        bus["inici"], tren["inici"] = tren["inici"], bus["inici"]
        self.assertEqual(T.estat_linia("R8", [], None, [tren, general, bus], vespre)["estat"], "bus")
        # Un avís nou que no parla del servei (obres) no treu el bus.
        obres = self.avis(["R8"], "Obres a l'estació de Mollet.", inici="2026-10-07T12:00+02:00")
        self.assertEqual(T.estat_linia("R8", [], None, [tren, general, bus, obres], vespre)["estat"], "bus")
        # Sense dates, com abans: qualsevol avís propi de carretera.
        for a in (bus, tren, general):
            a["inici"] = None
        self.assertEqual(T.estat_linia("R8", [], None, [tren, bus], vespre)["estat"], "bus")


if __name__ == "__main__":
    unittest.main()
