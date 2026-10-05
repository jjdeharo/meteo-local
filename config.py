# SPDX-License-Identifier: AGPL-3.0-or-later
"""Datos fijos del trayecto. Se cambian aquí, no en prevision.py."""

VERSION = "2.7.1"

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

# Horario de actualización con datos en directo (hora local), cada media
# hora. Por la mañana, para decidir el medio; al mediodía, el tiempo de la
# vuelta. La web lo muestra tal cual.
HORARIO = [("05:00", "07:30"), ("13:00", "15:30")]
INTERVALO_MIN = 30

# La página de casa (casa.html): previsión a 24 horas, actualizada cada media hora
# todo el día.
HORARIO_CASA = ("00:00", "23:30")
HORARIO_CASA_AVISO = ("00:00", "23:50")
INTERVALO_CASA_MIN = 30

# Agente diario (agent/): a qué hora y en qué modo se ejecuta, y con qué
# modelo. Va después de la actualización de la hora en punto, para leer datos
# recientes.
AGENTE_HORAS = {"05:47": "mati", "13:07": "tarda"}   # la de la mañana, lista antes de las 6
AGENTE_MODELO = "claude-sonnet-5-5"   # fijo: el alias «sonnet» cambiaría solo

# Modo aviso: con aviso de AEMET vigente, plan de Protección Civil en alerta o
# emergencia, lluvia en Montflorit o lluvia en el radar a menos de
# RADAR_AVISO_KM, las dos páginas se actualizan cada 10 minutos (la del
# trayecto, dentro de sus franjas). El radar publica una imagen cada 10
# minutos en punto, con unos minutos de retraso: se actualiza DESFASE minutos
# después para coger siempre la imagen nueva.
MODO_AVISO_INTERVALO_MIN = 10
MODO_AVISO_DESFASE_MIN = 1   # el radar publica unos 20-50 s después de la hora
RADAR_AVISO_KM = 15

# Registro de aciertos (registre.py): a qué hora se comprueba la lluvia que
# cayó, a los cuántos días se manda el resumen por Telegram y cuántos días de
# lluvia hacen falta para juzgar la regla.
HORA_VERIFICACION = "16:00"
REGISTRO_DIAS_AVISO = 28
REGISTRO_LLUVIAS_MINIMAS = 5

# Zonas de aviso de AEMET. La primera es la del trayecto; un aviso solo en la
# segunda, la costa, se tiene en cuenta pero no decide.
ZONA_TRAYECTO = "Prelitoral de Barcelona"
ZONA_CERCANA = "Litoral de Barcelona"

# Planes de Protección Civil de la Generalitat que dependen del tiempo, con el
# nombre que ve el lector. Un plan en alerta o emergencia cuenta como riesgo
# alto; en prealerta solo se avisa.
PLANES_PC = {"INUNCAT": "d'inundacions", "VENTCAT": "de vent", "NEUCAT": "de neu"}
# Si la descripción del plan nombra solo otras zonas, no afecta al trayecto.
ZONAS_PROPIAS_PC = ["Vallès", "Barcelona", "Catalunya"]
ZONAS_AJENAS_PC = ["Ebre", "Pirineu", "Aran", "Lleida", "Girona", "Tarragona", "Empordà"]

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

# Ropa (prevision.roba): el ciclomotor va como mucho a 45 km/h. Con 10 °C o
# menos, el frío se calcula como sensación térmica a esa velocidad (índice de
# Environment Canada); por encima, con la temperatura del aire.
VELOCIDAD_CICLOMOTOR_KMH = 45
ROPA_DIFERENCIA_CAPAS = 8      # °C entre ida y vuelta para avisar de las capas

# Si Open-Meteo falla, la página de casa usa la última previsión buena, si no
# tiene más de estas horas (ADR 0016).
CASA_PREVISION_ANTERIOR_MAX_H = 6

# Salida fuera de las franjas (casa.py, sortides): vuelta por defecto dentro de
# estas horas, y cambio de temperatura que se avisa.
SALIDA_VUELTA_POR_DEFECTO_H = 4
SALIDA_CAMBIO_TEMPERATURA = 6

# Umbrales de la decisión (mm en una hora; fracción de miembros; km).
UMBRAL_MM = 0.2          # ya moja en moto
UMBRAL_MM_COCHE = 1.0    # lluvia clara
PROB_ATENCION = 0.2
PROB_COCHE = 0.5
RADAR_COCHE_KM = 15
RADAR_ATENCION_KM = 40
