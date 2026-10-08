#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""La web pública «Temps a Montflorit» (ADR 0024).

Es la página de casa (web/casa.html) publicada aparte, en otro repositorio,
para quien quiera saber el tiempo en el barrio: sin la página del trayecto,
sin nada que hable de «casa» y con su propio nombre e icono. No se mantiene
a mano: se genera aquí a partir de web/, para que las dos no se separen.

- **La web**: casa.html pasa a ser index.html con los cambios de CANVIS_INDEX
  y fonts.html con los de CANVIS_FONTS; estil.css, comu.js y casa.js van tal
  cual (casa.js lee del <html> el nombre del lugar y el archivo de datos); el
  manifiesto, los iconos y el README salen de montflorit/. Cada cambio tiene
  que encontrar su texto: si casa.html cambia y uno deja de encajar, falla
  aquí y en las pruebas, no en la web.
- **Los datos**: casa.json sin lo que es del trayecto (PRIVADES).
- **En castellano** (ADR 0025): las mismas dos páginas en es/, traducidas
  bloque a bloque con i18n/es.json. Un bloque de texto sin traducción hace
  fallar la generación. Los textos que pone el programa de la página los
  traduce montflorit/es.js.

Uso:
  python3 montflorit.py web DESTINO        genera la web en la carpeta DESTINO
  python3 montflorit.py dades CASA SALIDA  los datos públicos a partir de casa.json
"""
import json
import os
import re
import shutil
import sys

from config import VERSION

ARREL = os.path.dirname(os.path.abspath(__file__))
REPO = "https://github.com/meteo-montflorit/meteo-montflorit.github.io"
WEB = "https://meteo-montflorit.github.io/"
# La versión del pie enlaza sus notas, en el repositorio del código.
NOTES = f"https://github.com/meteo-montflorit/meteo-local/releases/tag/v{VERSION}"
DADES = "montflorit.json"
# Lo que casa.json lleva para la página del trayecto, y el estado de la
# riera, que solo sirve para el aviso por Telegram (ADR 0027).
PRIVADES = ("sortides", "sortida_per_defecte_h", "riera")
# Con False, la página pide a los buscadores que no la indexen. Desde el
# 06-10-2026, con el permiso de meteocerdanyola.com, sí (ADR 0024).
INDEXABLE = True
# Palabras que no pueden quedar en lo que se lee de la web pública. El nombre
# del repositorio del código ya no está prohibido: los créditos lo enlazan
# (Juanjo, 07-10-2026) y la versión del pie enlaza sus notas (NOTES).
PROHIBIDES = ("casa", "cotxe", "moto", "trajecte")

NAV = re.compile(r'\n( *)<nav class="pagines".*?</nav>', re.S)   # amb el sagnat que tingui
# El menú de la web pública: el temps ara i «Si surts» (ADR 0029).
# «El temps», sense «ara»: la pàgina també porta la previsió (Juanjo, 08-10-2026).
PAGINES_PUBLIQUES = [("./", "El temps", "i-cloud-sun"), ("sortir.html", "Si surts", "i-door-open")]


def nav_publica(actual, sagnat="  "):
    enllacos = "".join(f'\n{sagnat}  <a href="{href}"' + (' aria-current="page"' if href == actual else "")
                       + f'><svg aria-hidden="true"><use href="#{icona}"></use></svg>{text}</a>'
                       for href, text, icona in PAGINES_PUBLIQUES)
    return f'\n{sagnat}<nav class="pagines" aria-label="Pàgines">{enllacos}\n{sagnat}</nav>'
ROBOTS = '  <meta name="robots" content="noindex">\n'

CANVIS_INDEX = [
    ('<html lang="ca" data-theme="light">',
     '<html lang="ca" data-theme="light" data-lloc="Montflorit" data-estacio="l’estació particular"'
     f' data-dades="{DADES}" data-notes="{NOTES}">'),
    ('content="El temps ara a casa (Montflorit, Cerdanyola del Vallès) i',
     'content="El temps ara a Montflorit (Cerdanyola del Vallès) i'),
    ("<title>Temps a casa</title>", "<title>Temps a Montflorit</title>"),
    ('<h1>Temps a casa</h1>\n      <p class="ruta">Montflorit, Cerdanyola del Vallès</p>',
     '<h1>Temps a Montflorit</h1>\n      <p class="ruta">Cerdanyola del Vallès'
     ' · <a href="es/" lang="es" hreflang="es">Castellano</a></p>'),
    ("de l'estació de casa; la pluja, de l'estació de Montflorit de meteocerdanyola.com, a uns 300-400 m, minut a minut",
     "d'una estació particular del barri; la pluja, de l'estació de Montflorit de meteocerdanyola.com, minut a minut"),
    ("amb el que ha mesurat l'estació de casa des de", "amb el que ha mesurat l'estació particular des de"),
    ("a Montflorit i a casa. Comprovada", "a Montflorit. Comprovada"),
]

CANVIS_FONTS = [
    ('<html lang="ca" data-theme="light">',
     f'<html lang="ca" data-theme="light" data-dades="{DADES}" data-notes="{NOTES}">'),
    ("<title>Fonts i crèdits · Temps a casa</title>", "<title>Fonts i crèdits · Temps a Montflorit</title>"),
    ('<p class="ruta">Montflorit, Cerdanyola del Vallès</p>',
     '<p class="ruta">Montflorit, Cerdanyola del Vallès'
     ' · <a href="es/fonts.html" lang="es" hreflang="es">Castellano</a></p>'),
    ("<strong>Estació de casa:</strong> una estació pròpia a uns 300-400 m de la de Montflorit, llegida",
     "<strong>Estació particular:</strong> una estació pròpia del mateix barri, llegida"),
    ("<li>Icones del cotxe i del ciclomotor de <a href=\"https://tabler.io/icons\" target=\"_blank\" rel=\"noopener\">"
     "Tabler Icons</a>, llicència MIT; la icona de l'aplicació els combina amb el núvol de Lucide.</li>",
     "<li>La icona de la moto de «Si surts», de <a href=\"https://tabler.io/icons\" target=\"_blank\" rel=\"noopener\">"
     "Tabler Icons</a>, llicència MIT.</li>"),
]
CANVIS_SORTIR = [
    ('<html lang="ca" data-theme="light">',
     f'<html lang="ca" data-theme="light" data-dades="{DADES}" data-notes="{NOTES}">'),
    ("<title>Si surts</title>", "<title>Si surts · Temps a Montflorit</title>"),
    ('<p class="ruta">Montflorit, Cerdanyola del Vallès</p>',
     '<p class="ruta">Montflorit, Cerdanyola del Vallès'
     ' · <a href="es/sortir.html" lang="es" hreflang="es">Castellano</a></p>'),
]
CANVIS_TELEGRAM = [
    ('<html lang="ca" data-theme="light">',
     f'<html lang="ca" data-theme="light" data-dades="{DADES}" data-notes="{NOTES}">'),
    ("<title>Avisos a Telegram</title>", "<title>Avisos a Telegram · Temps a Montflorit</title>"),
    ('<p class="ruta">Montflorit, Cerdanyola del Vallès</p>',
     '<p class="ruta">Montflorit, Cerdanyola del Vallès'
     ' · <a href="es/telegram.html" lang="es" hreflang="es">Castellano</a></p>'),
]
# En «Si surts» se habla de medios de transporte: ahí sí van «moto» y «cotxe».
PROHIBIDES_SORTIR = ("casa", "trajecte")
# Los créditos y el README enlazan el código fuente y los ADR, que están en
# meteo-montflorit/meteo-local (Juanjo, 07-10-2026); lo demás sigue sin nombrarlo.
# «moto» sí: el crédito del icono de la moto de «Si surts».
PROHIBIDES_FONTS = ("casa", "cotxe", "trajecte")
PROHIBIDES_README = ("casa", "trajecte")

# Créditos de iconos que solo usa la página del trayecto. El de Tabler se queda
# por el icono de la moto de «Si surts» (CANVIS_FONTS).
FORA_FONTS = [re.compile(r"\n      <li>Icones de roba i pluja de .*?</li>")]

SW_PECES = re.compile(r"const PECES = \[.*?\];", re.S)
PECES = ["./", "index.html", "sortir.html", "telegram.html", "fonts.html", "es/", "es/sortir.html",
         "es/telegram.html", "es/fonts.html", "estil.css",
         "comu.js", "casa.js", "sortir.js", "es.js", "manifest.webmanifest", "icones/icona-192.png"]

# --- En castellano (ADR 0025) ---
TRADUCCIONS = os.path.join(ARREL, "i18n", "es.json")
BLOC = re.compile(r"<(title|h1|h2|p|li|summary)\b([^>]*)>(.*?)</\1>", re.S)
ATRIBUT = re.compile(r'(\b(?:title|aria-label|alt)="|<meta name="description" content=")([^"]*)"')
# Lo que cambia además del texto: idioma, cómo se llama la estación propia y
# dónde están los archivos comunes, que quedan una carpeta más arriba.
CANVIS_ES = [
    ('<html lang="ca"', '<html lang="es"'),
    ('href="manifest.webmanifest"', 'href="../manifest.webmanifest"'),
    ('href="icones/apple-touch-icon.png"', 'href="../icones/apple-touch-icon.png"'),
    ('href="estil.css"', 'href="../estil.css"'),
]
CANVIS_ES_INDEX = [
    ('data-estacio="l’estació particular"', 'data-estacio="la estación particular" data-arrel="../"'),
    ('<script src="comu.js"></script>', '<script src="../es.js"></script>\n  <script src="../comu.js"></script>'),
    ('<script src="casa.js"></script>', '<script src="../casa.js"></script>'),
]
CANVIS_ES_TELEGRAM = [
    (f'data-dades="{DADES}"', f'data-dades="{DADES}" data-arrel="../"'),
    ('<script src="comu.js"></script>', '<script src="../es.js"></script>\n  <script src="../comu.js"></script>'),
]
CANVIS_ES_FONTS = [
    (f'data-dades="{DADES}"', f'data-dades="{DADES}" data-arrel="../"'),
    ('<script src="comu.js"></script>', '<script src="../es.js"></script>\n  <script src="../comu.js"></script>'),
]
CANVIS_ES_SORTIR = [
    (f'data-dades="{DADES}"', f'data-dades="{DADES}" data-arrel="../"'),
    ('<script src="comu.js"></script>', '<script src="../es.js"></script>\n  <script src="../comu.js"></script>'),
    ('<script src="sortir.js"></script>', '<script src="../sortir.js"></script>'),
    ("<label>Surto ", "<label>Salgo "),
    ("<label>Torno ", "<label>Vuelvo "),
    (">Mitjans que vols veure</legend>", ">Medios que quieres ver</legend>"),
]
# El menú público: lo que no traduce la tabla de bloques (los enlaces).
CANVIS_ES_NAV = [(">El temps</a>", ">El tiempo</a>"), (">Si surts</a>", ">Si sales</a>")]
# La traducción es automática: se dice en los créditos.
CREDIT_TRADUCCIO = ('</a>, licencia ISC.</li>',
                    '</a>, licencia ISC.</li>\n      <li>Versión en castellano traducida con IA, sin revisión profesional.</li>')


def espais(text):
    return re.sub(r"\s+", " ", text).strip()


def te_lletres(html):
    return bool(re.search(r"[A-Za-zÀ-ÿ]{2}", re.sub(r"<[^>]+>|&\w+;", " ", html)))


def blocs(html):
    """Los textos de la página que hay que traducir: bloques y atributos."""
    res = [espais(m.group(3)) for m in BLOC.finditer(html) if te_lletres(m.group(3))]
    res += [m.group(2) for m in ATRIBUT.finditer(html) if te_lletres(m.group(2))]
    return list(dict.fromkeys(res))


def tradueix(html, taula, nom):
    falten = [b for b in blocs(html) if b not in taula]
    if falten:
        raise ValueError(f"{nom}: falta la traducció de: " + " | ".join(f"«{b[:70]}»" for b in falten))
    html = BLOC.sub(lambda m: f"<{m.group(1)}{m.group(2)}>{taula[espais(m.group(3))]}</{m.group(1)}>"
                    if te_lletres(m.group(3)) else m.group(0), html)
    return ATRIBUT.sub(lambda m: f'{m.group(1)}{taula[m.group(2)]}"' if te_lletres(m.group(2)) else m.group(0), html)


def castella(html, nom, taula=None):
    """La página pública en castellano, a partir de la pública en catalán."""
    if taula is None:
        with open(TRADUCCIONS, encoding="utf-8") as f:
            taula = json.load(f)
    t = canvia(tradueix(html, taula, nom), CANVIS_ES, nom)
    t = canvia(t, {"index.html": CANVIS_ES_INDEX + CANVIS_ES_NAV, "sortir.html": CANVIS_ES_SORTIR + CANVIS_ES_NAV,
                   "telegram.html": CANVIS_ES_TELEGRAM + CANVIS_ES_NAV,
                   "fonts.html": CANVIS_ES_FONTS + CANVIS_ES_NAV + [CREDIT_TRADUCCIO]}[nom], nom)
    if nom == "telegram.html":     # les captures, les de Telegram en castellà
        t = t.replace('img/telegram/ca/', 'img/telegram/es/').replace('="img/', '="../img/')
    comprova("es/" + nom, t, PROHIBIDES_SORTIR if nom in ("sortir.html", "telegram.html") else
             PROHIBIDES_FONTS if nom == "fonts.html" else PROHIBIDES)
    return t


def canvia(text, canvis, nom):
    for vell, nou in canvis:
        if text.count(vell) != 1:
            raise ValueError(f"{nom}: el text «{vell[:60]}…» hi surt {text.count(vell)} vegades, no 1")
        text = text.replace(vell, nou)
    return text


def treu(text, patro, nom):
    text, n = patro.subn("", text)
    if n != 1:
        raise ValueError(f"{nom}: no trobo el que s'havia de treure ({patro.pattern[:40]}…)")
    return text


def text_visible(html):
    """Lo que se lee: sin etiquetas, programas ni estilos, pero con los
    atributos que se muestran o se leen en voz alta."""
    html = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", html, flags=re.S)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    atributs = " ".join(re.findall(r'(?:content|title|aria-label|href|data-\w+)="([^"]*)"', html))
    return re.sub(r"<[^>]+>", " ", html) + " " + atributs


def comprova(nom, text, prohibides=PROHIBIDES):
    visible = text_visible(text).lower()
    for paraula in prohibides:
        if re.search(rf"\b{re.escape(paraula)}\b", visible):
            raise ValueError(f"{nom}: hi queda «{paraula}»")


def menu(text, actual, nom):
    text, n = NAV.subn(lambda m: nav_publica(actual, m.group(1)), text)
    if n != 1:
        raise ValueError(f"{nom}: no trobo el menú de pàgines")
    return text


def alternes(html, nom):
    """Cada página pública dice dónde está en la otra lengua (hreflang), para
    los buscadores; el enlace visible ya está junto al municipio."""
    ca = WEB + ("" if nom == "index.html" else nom)
    enllacos = (f'\n  <link rel="alternate" hreflang="ca" href="{ca}">'
                f'\n  <link rel="alternate" hreflang="es" href="{WEB}es/{"" if nom == "index.html" else nom}">'
                f'\n  <link rel="alternate" hreflang="x-default" href="{ca}">')
    return canvia(html, [("\n</head>", enllacos + "\n</head>")], nom)


def index(casa_html):
    t = menu(canvia(casa_html, CANVIS_INDEX, "casa.html"), "./", "casa.html")
    if INDEXABLE:
        t = canvia(t, [(ROBOTS, "")], "casa.html")
    comprova("index.html", t)
    return t


def sortir(sortir_html):
    t = menu(canvia(sortir_html, CANVIS_SORTIR, "sortir.html"), "sortir.html", "sortir.html")
    if INDEXABLE:
        t = canvia(t, [(ROBOTS, "")], "sortir.html")
    comprova("sortir.html", t, PROHIBIDES_SORTIR)
    return t


def telegram(html):
    t = menu(canvia(html, CANVIS_TELEGRAM, "telegram.html"), "telegram.html", "telegram.html")
    if INDEXABLE:
        t = canvia(t, [(ROBOTS, "")], "telegram.html")
    comprova("telegram.html", t, PROHIBIDES_SORTIR)
    return t


def fonts(fonts_html):
    t = menu(canvia(fonts_html, CANVIS_FONTS, "fonts.html"), "fonts.html", "fonts.html")
    for patro in FORA_FONTS:
        t = treu(t, patro, "fonts.html")
    if INDEXABLE:
        t = canvia(t, [(ROBOTS, "")], "fonts.html")
    comprova("fonts.html", t, PROHIBIDES_FONTS)
    return t


def service_worker(sw):
    t = canvia(sw, [("const MAGATZEM = 'meteo-local';", "const MAGATZEM = 'meteo-montflorit';")], "sw.js")
    t, n = SW_PECES.subn("const PECES = " + json.dumps(PECES).replace('"', "'") + ";", t)
    if n != 1:
        raise ValueError("sw.js: no trobo la llista de peces")
    return t


def llegeix_fitxer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def escriu_fitxer(ruta, text):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(text)


def construeix(desti, web=None):
    """Deja en desti la web pública completa (sin los datos)."""
    web = web or os.path.join(ARREL, "web")
    propi = os.path.join(ARREL, "montflorit")
    llegeix = lambda nom: llegeix_fitxer(os.path.join(web, nom))
    os.makedirs(desti, exist_ok=True)
    escriu = lambda nom, text: escriu_fitxer(os.path.join(desti, nom), text)
    pagines = {"index.html": index(llegeix("casa.html")), "sortir.html": sortir(llegeix("sortir.html")),
               "telegram.html": telegram(llegeix("telegram.html")), "fonts.html": fonts(llegeix("fonts.html"))}
    pagines = {nom: alternes(html, nom) for nom, html in pagines.items()}
    os.makedirs(os.path.join(desti, "es"), exist_ok=True)
    for nom, html in pagines.items():
        escriu(nom, html)
        escriu("es/" + nom, castella(html, nom))
    escriu("sw.js", service_worker(llegeix("sw.js")))
    for nom in ("estil.css", "comu.js", "casa.js", "sortir.js"):
        shutil.copy(os.path.join(web, nom), desti)
    shutil.copytree(propi, desti, dirs_exist_ok=True)
    shutil.copytree(os.path.join(web, "img"), os.path.join(desti, "img"), dirs_exist_ok=True)
    for nom in ("LICENSE", "LICENSE-CONTINGUTS.md"):
        shutil.copy(os.path.join(ARREL, nom), desti)
    open(os.path.join(desti, ".nojekyll"), "w").close()
    comprova("manifest.webmanifest", llegeix_fitxer(os.path.join(desti, "manifest.webmanifest")))
    # El README presenta també «Si surts»: hi poden sortir els mitjans.
    comprova("README.md", llegeix_fitxer(os.path.join(desti, "README.md")), PROHIBIDES_README)
    falten = [p for p in PECES[1:] if not os.path.exists(os.path.join(desti, p.replace("es/", "es/index.html")
                                                                      if p == "es/" else p))]
    if falten:
        raise ValueError(f"sw.js: falten peces: {falten}")


def dades_publiques(casa):
    """Los datos de casa sin lo que es del trayecto."""
    return {k: v for k, v in casa.items() if k not in PRIVADES}


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "web":
        construeix(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "dades":
        with open(sys.argv[2], encoding="utf-8") as f:
            publiques = dades_publiques(json.load(f))
        with open(sys.argv[3], "w", encoding="utf-8") as f:
            json.dump(publiques, f, ensure_ascii=False, separators=(",", ":"))
    else:
        sys.exit(__doc__)
