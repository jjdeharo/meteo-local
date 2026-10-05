# SPDX-License-Identifier: AGPL-3.0-or-later
"""Datos fijos del trayecto. Se cambian aquí, no en prevision.py."""

VERSION = "1.5.0"

# Coordenadas redondeadas a unos 500 m: para el tiempo da igual una calle u
# otra, y el repositorio es público.
CASA = (41.482, 2.135)      # Cerdanyola del Vallès (Montflorit)
DESTINO = (41.557, 2.109)   # Parc Taulí, Sabadell

# Ventanas del trayecto en moto (hora local). Unos 8 km, 15-20 minutos.
IDA = ("06:30", "07:30")      # llegada a las 7:30
VUELTA = ("15:00", "15:30")   # salida a las 15:00

# Estaciones de meteocerdanyola.com (nombre en su web: nombre), minuto a
# minuto. Montflorit está al principio del trayecto.
ESTACIONES_LOCALES = {
    "cerdanyola_montflorit": "Cerdanyola (Montflorit)",
}

# Estaciones automáticas de Meteocat más próximas (código: nombre).
ESTACIONES = {
    "XF": "Sabadell (Parc Agrari)",
    "XV": "Sant Cugat (CAR)",
}

# Zonas de aviso de AEMET. La primera es la del trayecto; un aviso solo en la
# segunda, la costa, se tiene en cuenta pero no decide.
ZONA_TRAYECTO = "Prelitoral de Barcelona"
ZONA_CERCANA = "Litoral de Barcelona"

# Modelos deterministas de Open-Meteo. Los «finos» deciden; los globales,
# con celdas de 10-25 km que incluyen mar, solo se muestran.
MODELOS_FINOS = [
    "meteofrance_arome_france_hd",  # 1,5 km, el más fino que cubre Cataluña
    "meteofrance_arome_france",     # 2,5 km
    "icon_eu",                      # 7 km
]
MODELOS_GLOBALES = ["ecmwf_ifs025", "ukmo_seamless", "gfs_seamless"]
# Ensemble horario usado como probabilidad.
ENSEMBLE = "icon_eu_eps"

# Umbrales de la decisión (mm en una hora; fracción de miembros; km).
UMBRAL_MM = 0.2          # ya moja en moto
UMBRAL_MM_COCHE = 1.0    # lluvia clara
PROB_ATENCION = 0.2
PROB_COCHE = 0.5
RADAR_COCHE_KM = 15
RADAR_ATENCION_KM = 40
