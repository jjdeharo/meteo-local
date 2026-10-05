# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas de la regla de decisión con datos inventados (sin red)."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import prevision as P  # noqa: E402

MANANA = (P.AHORA.date() + dt.timedelta(days=1)).isoformat()


def modelos(mm):
    horas = [f"{MANANA}T{h:02d}:00" for h in range(24)]
    serie = [mm if h in (8, 16) else 0.0 for h in range(24)]
    return [{"hourly": {"time": horas, **{f"precipitation_{m}": serie for m in P.C.MODELOS_FINOS}}}]


def ensemble(mojados, total=40):
    horas = [f"{MANANA}T{h:02d}:00" for h in range(24)]
    e = {"time": horas}
    for i in range(total):
        e[f"precipitation_member{i:02d}"] = [1.0 if i < mojados and h == 8 else 0.0 for h in range(24)]
    return e


def aviso(zona):
    return {"zona": zona, "tipo": "tempestes", "nivel": "groc",
            "inicio": f"{MANANA}T05:00:00+02:00", "fin": f"{MANANA}T19:59:59+02:00"}


class Decision(unittest.TestCase):
    def ida(self, **d):
        return P.decidir(MANANA, P.C.IDA, d)

    def test_todo_seco_es_moto(self):
        r = self.ida(avisos=[], modelos=modelos(0), ensemble=ensemble(0))
        self.assertEqual(r["veredicte"], "moto")

    def test_aviso_en_el_valles_es_coche(self):
        r = self.ida(avisos=[aviso(P.C.ZONA_TRAYECTO)], modelos=modelos(0), ensemble=ensemble(0))
        self.assertEqual(r["veredicte"], "cotxe")
        self.assertIn("20:00", r["motius"][0]["text"])

    def test_aviso_solo_en_la_costa_es_atencion(self):
        r = self.ida(avisos=[aviso(P.C.ZONA_CERCANA)], modelos=modelos(0), ensemble=ensemble(0))
        self.assertEqual(r["veredicte"], "compte")

    def test_lluvia_clara_en_modelos_es_coche(self):
        r = self.ida(avisos=[], modelos=modelos(1.5), ensemble=ensemble(0))
        self.assertEqual(r["veredicte"], "cotxe")

    def test_probabilidad_media_es_atencion(self):
        r = self.ida(avisos=[], modelos=modelos(0), ensemble=ensemble(16))
        self.assertEqual(r["veredicte"], "compte")

    def test_probabilidad_alta_es_coche(self):
        r = self.ida(avisos=[], modelos=modelos(0), ensemble=ensemble(20))
        self.assertEqual(r["veredicte"], "cotxe")

    def test_sin_datos_es_atencion(self):
        self.assertEqual(self.ida()["veredicte"], "compte")

    def test_ventana_cuenta_la_hora_siguiente(self):
        # La lluvia de 7:00 a 7:30 está en el acumulado que acaba a las 8:00.
        self.assertEqual(P.horas_ventana(("07:00", "07:30")), [8])
        self.assertEqual(P.horas_ventana(("15:00", "15:30")), [16])


if __name__ == "__main__":
    unittest.main()
