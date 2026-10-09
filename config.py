# SPDX-License-Identifier: AGPL-3.0-or-later
"""Datos fijos de «Temps a Montflorit»: lugares, horario, fuentes y umbrales.
Se cambian aquí, no en los programas."""

VERSION = "3.32.1"

# Coordenadas con tres decimales (unos 100 m), no las exactas: para el tiempo
# da igual una calle u otra, y el repositorio es público.
CASA = (41.482, 2.135)      # Cerdanyola del Vallès (Montflorit)

# Estaciones de meteocerdanyola.com (nombre en su web: nombre), minuto a
# minuto. Montflorit es la del barrio.
ESTACIONES_LOCALES = {
    "cerdanyola_montflorit": "Cerdanyola (Montflorit)",
}

# La estación de casa (Ecowitt, API oficial; ADR 0017), a unos 300-400 m de
# Montflorit. Temperatura, humedad, punto de rocío, presión y radiación son
# fiables; el viento no se usa. El pluviómetro registró toda la lluvia hasta
# PLUVIOMETRE_CASA_FIABLE_FINS; desde entonces a veces no marca la lluvia
# débil, así que solo cuenta cuando marca lluvia.
ESTACIO_CASA = "Casa"
PLUVIOMETRE_CASA_FIABLE_FINS = "2026-08-31"
# La estación da la presión medida a su altura (la «relativa» de Ecowitt no
# está calibrada: el 07-10-2026 marcaba 1002 hPa con 1011 de QNH en Sabadell).
# Se reduce al nivel del mar con esta altitud (modelo digital del terreno de
# Open-Meteo para las coordenadas redondeadas), que es lo que publican las
# demás estaciones y los mapas (ADR 0037).
ALTITUD_CASA_M = 70

# El viento de ahora: el anemómetro de Montflorit marca casi siempre 0 (el
# 07-10-2026, 0 en 1.072 de 1.094 minutos con 13 km/h en Open-Meteo), así que
# se muestra el de la estación de Meteocat más cercana, por medias horas
# (ADR 0037).
VENT_ESTACIO = "XV"

# Estaciones automáticas de Meteocat más próximas (código: nombre).
ESTACIONES = {
    "XF": "Sabadell (Parc Agrari)",
    "XV": "Sant Cugat (CAR)",
}

# Horario de actualización con datos en directo (hora local): previsión a 24
# horas, actualizada cada cuarto de hora todo el día. La web lo muestra tal
# cual. Los datos van a IONOS en cada pasada y la web a GitHub cada media hora
# como mucho (ADR 0020).
HORARIO_CASA = ("00:00", "23:45")
HORARIO_CASA_AVISO = ("00:00", "23:54")
INTERVALO_CASA_MIN = 15

# Modo aviso: con aviso de AEMET vigente, plan de Protección Civil en alerta o
# emergencia, lluvia en Montflorit o lluvia en el radar a menos de
# RADAR_AVISO_KM de casa (o que llegará a casa en la próxima hora), la página
# se actualiza cada 6 minutos: el ritmo del radar de Meteocat, que saca una
# imagen a :00, :06, :12… y la publica unos 13-14 minutos después. Con el
# desfase de 3 minutos, cada pasada coge la imagen nueva (la de las 10:06,
# publicada a las 10:19:43, a las 10:21).
MODO_AVISO_INTERVALO_MIN = 6
MODO_AVISO_DESFASE_MIN = 3
RADAR_AVISO_KM = 15

# A qué hora el reloj del NAS (nas/reloj.sh) rellena las horas que falten de
# la estación de casa (registre.py estacio) y la página aprende de sus
# aciertos (aprenentatge.py diari).
HORA_VERIFICACION = "16:00"

# Zonas de aviso de AEMET. La primera es la del barrio; un aviso solo en la
# segunda, la costa, se tiene en cuenta pero no decide.
ZONA_AVISOS = "Prelitoral de Barcelona"
ZONA_CERCANA = "Litoral de Barcelona"

# Planes de Protección Civil de la Generalitat que dependen del tiempo, con el
# nombre que ve el lector. Un plan en alerta o emergencia cuenta como riesgo
# alto; en prealerta solo se muestra en la web (ADR 0051).
PLANES_PC = {"INUNCAT": "d'inundacions", "VENTCAT": "de vent", "NEUCAT": "de neu"}
# El PROCICAT agrupa riesgos distintos: el de cada registro lo dice su icono
# (ico_PROCICAT_<RIESGO>.png). Solo los que afectan a toda una zona; ni la
# pandemia ni el ferrocarril (los trenes ya están en «Si surts»).
PROCICAT_PC = {"ONADA_CALOR": "per onada de calor", "ONADA_FRED": "per onada de fred",
               "CONTAMINACIÓ": "per contaminació", "VENT": "per vent"}
# Si la descripción del plan nombra solo otras zonas, no afecta al barrio.
ZONAS_PROPIAS_PC = ["Vallès", "Barcelona", "Catalunya"]
ZONAS_AJENAS_PC = ["Ebre", "Pirineu", "Aran", "Lleida", "Girona", "Tarragona", "Empordà"]

# Modelos deterministas «finos» de Open-Meteo: los que usa la previsión.
MODELOS_FINOS = [
    "meteofrance_arome_france_hd",  # 1,5 km, el más fino que cubre Cataluña
    "meteofrance_arome_france",     # 2,5 km
    "icon_eu",                      # 7 km
]
# Ensemble horario usado como probabilidad.
ENSEMBLE = "icon_eu_eps"

# Si Open-Meteo falla, la página de casa usa la última previsión buena, si no
# tiene más de estas horas (ADR 0016).
CASA_PREVISION_ANTERIOR_MAX_H = 6

# Situaciones de peligro en casa (riscos.py, ADR 0018): los umbrales de aviso
# amarillo, naranja y rojo de AEMET para el Prelitoral de Barcelona (zona
# 690803; Plan Meteoalerta, anexo 1, «Umbrales y niveles de aviso», versión del
# 31-05-2022). Se comparan con lo que miden las estaciones y con la previsión
# de la página de casa, no con los avisos de AEMET. Lluvia en mm, racha en
# km/h, temperatura en °C y nieve en cm.
RISC_LLINDARS = {
    "pluja_1h": (20, 40, 90),
    "pluja_12h": (60, 100, 180),
    "ratxa": (70, 90, 130),
    "calor": (36, 39, 42),
    "fred": (-4, -8, -12),
    "neu_24h": (2, 5, 20),
}
# Horas sin ver un riesgo para darlo por acabado: así el vaivén de los modelos
# entre una pasada y otra no repite el aviso por Telegram.
RISC_FI_H = 3

# Aviso de antes de llover (pluja_arriba.py, ADR 0022; el público, avisos_bot.py,
# ADR 0034 y 0048; desde el 08-10-2026 no hay uno aparte para Juanjo): sale
# cuando el radar llevado hacia delante dice que faltan AVIS_PLUJA_MIN minutos
# más una pasada del modo aviso (entre 15 y 21 minutos antes): lo que importa
# es que llegue con margen, no el minuto exacto. Un episodio de
# lluvia acaba tras AVIS_PLUJA_REPOS_MIN minutos sin lluvia medida ni
# anunciada, y hay un aviso por episodio. El aviso cuenta como acierto si
# empieza a llover en AVIS_PLUJA_VERIFICA_MIN minutos.
AVIS_PLUJA_MIN = 15
AVIS_PLUJA_REPOS_MIN = 60
AVIS_PLUJA_VERIFICA_MIN = 45

# Umbrales de la lluvia (mm en una hora; fracción de miembros del ensemble o
# del círculo del radar): lo que ya moja, y desde qué probabilidad se avisa
# de lluvia posible.
UMBRAL_MM = 0.2
PROB_ATENCION = 0.2
# Llueve ahora si una de las dos estaciones ha recogido lluvia en estos
# minutos. Ni la intensidad que dan (tarda en volver a cero) ni la media hora:
# el 08-10-2026 las dos pararon a las 19:50 y la página aún decía «Pluja a
# sobre» a las 20:15. Con 15, una llovizna de 0,8 mm/h (una marca de 0,2 mm
# cada 15 minutos) sigue contando como lluvia.
PLOU_ARA_MIN = 15
# El radar en directo, centrado en Montflorit si se puede: el que da el aviso
# de lluvia lo enlaza (avisos_bot.py, ADR 0048). Los mismos en web/casa.js y
# bot/bot.py, que las pruebas comparan.
RADAR_EN_DIRECTE = {"rainviewer": "https://www.rainviewer.com/map.html?loc=41.482,2.135,9&layer=radar",
                    "meteocat": "https://www.meteo.cat/observacions/radar"}

# «Si surts», lluvia en moto y en bici (web/sortir.js, ADR 0047): solo la
# probabilidad, desde el 10 % «compte» y desde el 40 % «millor no»; sin
# probabilidad, la lluvia de los modelos. Un aviso de AEMET solo, «compte».
# Comprobado con el archivo (calibracio/regla_moto.py); las pruebas miran que
# coincidan con los de la página.
MOTO_PROB_RISC = 0.1
MOTO_PROB_PLUJA = 0.4
MOTO_MM_RISC = 0.2
MOTO_MM_PLUJA = 1.0

# Riera de Sant Cugat (riera.py, ADR 0027): nace en Collserola y pasa por
# Montflorit. Se desbordó con 53 mm en 3 horas en Sant Cugat (29-04-2024, el
# agua llegó a la puerta de las casas) y con 67 (29-09-2026 y 04-10-2026,
# entró en ellas), justo al acabar las 3 horas más lluviosas. Cuenta la
# lluvia de las últimas 3 horas en la estación de Meteocat de Sant Cugat más
# la que el radar lleva hacia delante sobre la cuenca en la hora siguiente.
# Desde RIERA_REGISTRE_MM se apunta el episodio; desde ATENCIO, aviso por
# Telegram; con PERILL en 3 horas y PERILL_6H en 6, otro: el 13-09-2025
# cayeron 52 mm en 3 horas sin lluvia antes (52 en 6) y no se desbordó, y los
# tres desbordamientos tenían 67 o más en 6 horas. Son una hipótesis con
# cuatro casos: se ajustan con el registro.
RIERA_ESTACIO = "XV"                # Sant Cugat (CAR), en medio de la cuenca
RIERA_CAPCALERA = ("D5", "Observatori Fabra")   # cresta de Collserola, junto a Les Planes
CONCA_RIERA = (41.46, 2.10)         # centro aproximado de la cuenca, para el radar
RIERA_HORES = 3
RIERA_REGISTRE_MM = 20
RIERA_ATENCIO_MM = 35
RIERA_PERILL_MM = 50
RIERA_PERILL_6H_MM = 60
RIERA_FI_H = 3                      # horas por debajo del registro para cerrar el episodio

# Trenes de cerca (trens.py, ADR 0029): línea, operador y dónde para en
# Cerdanyola. Una línea circula si se ha visto un tren suyo moviéndose a
# TRENS_RADI_KM o menos de su estación (TRENS_ESTACIONS) en los últimos
# TRENS_VIST_MIN minutos; fuera de su horario, sin trenes es lo normal. El
# horario es el de cada línea en Cerdanyola (TRENS_HORARI_LINIA: primer y
# último tren, del GTFS de Renfe y de FGC del 08-10-2026, con el primero del
# tipo de día que empieza más tarde), y hasta TRENS_MARGE_INICI_MIN minutos
# después del primer tren no se dice que no circula: el 08-10-2026 a las 05:39
# el bot avisó de que la R7 no circulaba, y su primer tren es a las 06:40
# (ADR 0038). Sin horario propio, TRENS_HORARI.
TRENS = [
    ("R4", "rodalies", "Cerdanyola del Vallès"),
    ("R7", "rodalies", "Cerdanyola Universitat"),
    ("R8", "rodalies", "Cerdanyola Universitat"),
    ("S2", "fgc", "Bellaterra i Universitat Autònoma"),
]
# Lo que pasa alrededor (entorn.py, ADR 0046): incendios forestales en curso
# de Bombers a menos de ENTORN_RADI_KM; el Pla Alfa del municipio
# (ALFA_MUNICIPI, código de Agents Rurals), solo si la capa se ha editado en
# las últimas ALFA_ACTUAL_H horas (fuera de campaña se queda con el último
# valor); se muestra desde el nivel ALFA_NIVELL_MOSTRAR, el que restringe el
# acceso a los espacios forestales.
ENTORN_RADI_KM = 5
ALFA_MUNICIPI = "082665"            # Cerdanyola del Vallès
ALFA_ACTUAL_H = 36
ALFA_NIVELL_MOSTRAR = 3

# Tráfico de cerca (transit.py, ADR 0052): las incidencias del Servei Català de
# Trànsit que empiezan a TRANSIT_RADI_KM o menos de casa (AP-7, B-30, C-58,
# C-17, C-33, BV-1414, BV-1415, BV-1462 y las rondas por el norte). Las
# retenciones, accidentes y averías salen siempre; las obras, solo si desvían
# o cortan la vía (nivel TRANSIT_NIVELL_OBRES o más, o «tallada» en el texto).
# En «Si surts», si se sale ahora, el coche y la moto pasan a «compte» con una
# incidencia de nivel TRANSIT_NIVELL_SORTIDA o más (3, retenciones; 4,
# congestión; 5, calzada cortada); la «circulació intensa» (2) solo se lista.
TRANSIT_RADI_KM = 6
TRANSIT_NIVELL_OBRES = 3
TRANSIT_NIVELL_SORTIDA = 3

TRENS_ESTACIONS = {"R4": (41.493, 2.148), "R7": (41.497, 2.115), "R8": (41.497, 2.115),
                   "S2": (41.502, 2.091)}
TRENS_RADI_KM = 6
TRENS_VIST_MIN = 60
TRENS_HORARI = ("05:30", "23:30")
TRENS_HORARI_LINIA = {"R4": ("05:20", "23:59"), "R7": ("06:35", "22:40"), "R8": ("06:49", "21:50"),
                      "S2": ("05:14", "23:59")}
TRENS_MARGE_INICI_MIN = 30
