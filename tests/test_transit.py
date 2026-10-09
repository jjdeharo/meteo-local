# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas de las incidencias de tráfico de cerca (sin red), con el formato
real del Servei Català de Trànsit del 09-10-2026."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402
import transit as T  # noqa: E402


def afectacio(ident, tipus, nivell, carretera, lon, lat, descripcio, causa, cap_a=None,
              data="Fri, 09 Oct 2026 05:34:12 GMT", pk=("150.00", "149.50")):
    cap = f"<cite:cap_a>{cap_a}</cite:cap_a>" if cap_a else ""
    return (f'<gml:featureMember><cite:mct2_v_afectacions_data fid="x"><cite:geom><gml:Point>'
            f'<gml:coordinates decimal="." cs="," ts=" ">{lon},{lat}</gml:coordinates></gml:Point></cite:geom>'
            f"<cite:identificador>{ident}</cite:identificador><cite:tipus>{tipus}</cite:tipus>"
            f"<cite:subtipus>9</cite:subtipus><cite:carretera>{carretera}</cite:carretera>"
            f"<cite:pk_inici>{pk[0]}</cite:pk_inici><cite:pk_fi>{pk[1]}</cite:pk_fi><cite:causa>{causa}</cite:causa>"
            f"{cap}<cite:data>{data}</cite:data><cite:nivell>{nivell}</cite:nivell>"
            f"<cite:sentit>Decreixent</cite:sentit><cite:descripcio>{descripcio}</cite:descripcio>"
            f"<cite:descripcio_tipus>x</cite:descripcio_tipus><cite:font>SCT</cite:font>"
            f"</cite:mct2_v_afectacions_data></gml:featureMember>")


GML = ('<?xml version="1.0" encoding="UTF-8"?><wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs"'
       ' xmlns:gml="http://www.opengis.net/gml" xmlns:cite="http://www.opengeospatial.net/cite">'
       # AP-7 a Cerdanyola, 2,5 km: avaria amb circulació intensa (nivell 2).
       + afectacio("151666901", 2, 2, "AP-7", 2.1081, 41.4956, "Circulació intensa", "Avaria",
                   "TARRAGONA-UN CARRIL TALLAT")
       # C-58, retencions (nivell 3).
       + afectacio("151664203", 2, 3, "C-58", 2.1720, 41.4600, "Circulació amb retencions", "Circulació",
                   "NUS TRINITAT", "Fri, 09 Oct 2026 07:03:36 GMT", ("0.00", "1.50"))
       # Obres de manteniment amb un carril restringit: no surten.
       + afectacio("151503301", 3, 2, "BV-1415", 2.1305, 41.4469, "Calçada restringida", "Treballs de manteniment")
       # Obres de nivell 2 però amb l'accés tallat: surten.
       + afectacio("147748402", 3, 2, "BV-1414", 2.1500, 41.4500, "Calçada restringida",
                   "Insatal·lació i/o desmuntatge de pòrtics", "C-58-INCORPORACIÓ A C-58 TALLADA ,DESVIAMENT SENYALITZAT",
                   "Wed, 22 Apr 2026 18:57:49 GMT", ("4.00", "0.00"))
       # Calçada tallada lluny (Jorba): fora del radi.
       + afectacio("142217830", 2, 5, "A-2", 1.5400, 41.6000, "Calçada tallada", "Esfondraments")
       + "</wfs:FeatureCollection>").encode()

RSS = ("<?xml version='1.0' encoding='UTF-8'?><rss version='2.0'><channel>"
       "<item><guid isPermaLink='false'>151666901</guid><title>AVARIA. Circulació intensa (Retenció)</title>"
       "<description>AP-7 | CERDANYOLA DEL VALLÈS | Sentit Sud cap a TARRAGONA-UN CARRIL TALLAT | "
       "Punt km. 150-149.5 | 07:34</description></item>"
       "<item><guid isPermaLink='false'>147748402</guid><title>x</title>"
       "<description>BV-1414 | CERDANYOLA DEL VALLÈS | Sentit Sud cap a C-58-INCORPORACIÓ A C-58 TALLADA "
       ",DESVIAMENT SENYALITZAT | Punt km. 4-0 | 20:57</description></item>"
       "</channel></rss>").encode()


class Transit(unittest.TestCase):
    def test_filtra_per_distancia_i_tipus(self):
        r = T.filtra(T.llegeix_gml(GML), T.llegeix_rss(RSS))
        # Primer les retencions, de la més greu a la més lleu; després les obres.
        self.assertEqual([i["carretera"] for i in r], ["C-58", "AP-7", "BV-1414"])
        self.assertTrue(all(i["km"] <= C.TRANSIT_RADI_KM for i in r))

    def test_text_tal_com_el_publica_el_sct(self):
        ap7 = {i["id"]: i for i in T.filtra(T.llegeix_gml(GML), T.llegeix_rss(RSS))}["151666901"]
        self.assertEqual(ap7, {"id": "151666901", "tipus": "retencio", "nivell": 2, "carretera": "AP-7",
                               "municipi": "Cerdanyola del Vallès",
                               "sentit": "Sentit Sud cap a TARRAGONA-UN CARRIL TALLAT", "causa": "Avaria",
                               "descripcio": "Circulació intensa", "pk": "150-149,5", "km": ap7["km"]})

    def test_sense_rss_surten_igual(self):
        # Sense el RSS, sense municipi i amb el «cap a» del GML.
        c58 = T.filtra(T.llegeix_gml(GML))[0]
        self.assertIsNone(c58["municipi"])
        self.assertEqual(c58["sentit"], "Cap a NUS TRINITAT")
        self.assertEqual(c58["pk"], "0-1,5")

    def test_obres(self):
        obres = lambda nivell, desc, cap_a=None: T.es_mostra({"tipus": 3, "nivell": nivell, "descripcio": desc,
                                                               "cap_a": cap_a})
        self.assertFalse(obres(2, "Calçada restringida"))
        self.assertFalse(obres(2, "Calçada restringida", "HORARI: 7 a 15h"))
        self.assertTrue(obres(2, "Calçada restringida", "C-58-INCORPORACIÓ A C-58 TALLADA"))
        self.assertTrue(obres(3, "Calçada restringida. Desviaments"))
        self.assertTrue(obres(5, "Calçada tallada"))
        self.assertTrue(obres(2, "Calçada restringida", "TALL TOTAL EN HORARI NOCTURN"))

    def test_noms_de_municipi(self):
        self.assertEqual([T.nom_municipi(x) for x in ("CERDANYOLA DEL VALLÈS", "MONTCADA I REIXAC",
                                                       "L'HOSPITALET DE LLOBREGAT", "CASTELL D'ARO", "LA LLAGOSTA")],
                         ["Cerdanyola del Vallès", "Montcada i Reixac", "L'Hospitalet de Llobregat",
                          "Castell d'Aro", "La Llagosta"])

    def test_punt_quilometric(self):
        self.assertEqual([T.pk("150.00", "149.50"), T.pk("7.20", "7.20"), T.pk("4.00", None), T.pk(None, None)],
                         ["150-149,5", "7,2", "4", None])

    def test_mateix_nivell_que_la_pagina(self):
        web = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "sortir.js")
        with open(web, encoding="utf-8") as f:
            self.assertIn(f"const NIVELL_TRANSIT = {C.TRANSIT_NIVELL_SORTIDA};", f.read())


if __name__ == "__main__":
    unittest.main()
