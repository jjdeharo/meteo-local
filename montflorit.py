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

ARREL = os.path.dirname(os.path.abspath(__file__))
REPO = "https://github.com/jjdeharo/meteo-montflorit"
DADES = "montflorit.json"
# Lo que casa.json lleva para la página del trayecto, y el estado de la
# riera, que solo sirve para el aviso por Telegram (ADR 0027).
PRIVADES = ("sortides", "sortida_per_defecte_h", "riera")
# Con False, la página pide a los buscadores que no la indexen. Desde el
# 06-10-2026, con el permiso de meteocerdanyola.com, sí (ADR 0024).
INDEXABLE = True
# Palabras que no pueden quedar en lo que se lee de la web pública.
PROHIBIDES = ("casa", "cotxe", "moto", "trajecte", "meteo-local")

NAV = re.compile(r'\n  <nav class="pagines".*?</nav>', re.S)
ROBOTS = '  <meta name="robots" content="noindex">\n'

CANVIS_INDEX = [
    ('<html lang="ca" data-theme="light">',
     '<html lang="ca" data-theme="light" data-lloc="Montflorit" data-estacio="l’estació particular"'
     f' data-dades="{DADES}" data-notes="{REPO}">'),
    ('content="El temps ara a casa (Montflorit, Cerdanyola del Vallès) i',
     'content="El temps ara a Montflorit (Cerdanyola del Vallès) i'),
    ("<title>Temps a casa</title>", "<title>Temps a Montflorit</title>"),
    ('<h1>Temps a casa</h1>\n      <p class="ruta">Montflorit, Cerdanyola del Vallès</p>',
     '<h1>Temps a Montflorit</h1>\n      <p class="ruta">Cerdanyola del Vallès'
     ' · <a href="es/" lang="es" hreflang="es">Castellano</a></p>'),
    ("de l'estació de casa; la pluja i el vent, de l'estació de Montflorit de meteocerdanyola.com, a uns 300-400 m, minut a minut",
     "d'una estació particular del barri; la pluja i el vent, de l'estació de Montflorit de meteocerdanyola.com, minut a minut"),
    ("amb el que ha mesurat l'estació de casa des de", "amb el que ha mesurat l'estació particular des de"),
    ("a Montflorit i a casa. Comprovada", "a Montflorit. Comprovada"),
    ('href="https://github.com/jjdeharo/meteo-local/releases"', f'href="{REPO}"'),
]

CANVIS_FONTS = [
    ("<title>Fonts i crèdits · Moto o cotxe?</title>", "<title>Fonts i crèdits · Temps a Montflorit</title>"),
    ("<strong>Estació de casa:</strong> una estació pròpia a uns 300-400 m de la de Montflorit, llegida",
     "<strong>Estació particular:</strong> una estació pròpia del mateix barri, llegida"),
    ("<p>És una recomanació calculada automàticament, no una previsió oficial.",
     "<p>És una previsió calculada automàticament, no una previsió oficial."),
    ('href="https://github.com/jjdeharo/meteo-local"', f'href="{REPO}"'),
    # Los modelos globales solo los usa la página del trayecto.
    ("amb models de Météo-France (AROME), del servei meteorològic alemany (ICON-EU i les seves 40 variants), "
     "de l'ECMWF, del Met Office britànic i de la NOAA.",
     "amb models de Météo-France (AROME i ARPEGE) i del servei meteorològic alemany (ICON-EU i les seves 40 variants)."),
]
# Créditos de iconos que solo usa la página del trayecto.
FORA_FONTS = [re.compile(r"\n      <li>Icones de roba i pluja de .*?</li>"),
              re.compile(r"\n      <li>Icones del cotxe i del ciclomotor de .*?</li>")]

SW_PECES = re.compile(r"const PECES = \[.*?\];", re.S)
PECES = ["./", "index.html", "fonts.html", "es/", "es/fonts.html", "estil.css", "comu.js", "casa.js",
         "es.js", "manifest.webmanifest", "icones/icona-192.png"]

# --- En castellano (ADR 0025) ---
TRADUCCIONS = os.path.join(ARREL, "i18n", "es.json")
BLOC = re.compile(r"<(title|h1|h2|p|li|summary)\b([^>]*)>(.*?)</\1>", re.S)
ATRIBUT = re.compile(r'(\b(?:title|aria-label)="|<meta name="description" content=")([^"]*)"')
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
    t = canvia(t, CANVIS_ES_INDEX if nom == "index.html" else [CREDIT_TRADUCCIO], nom)
    comprova("es/" + nom, t)
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


def comprova(nom, text):
    visible = text_visible(text).lower()
    for paraula in PROHIBIDES:
        if re.search(rf"\b{re.escape(paraula)}\b", visible):
            raise ValueError(f"{nom}: hi queda «{paraula}»")


def index(casa_html):
    t = treu(canvia(casa_html, CANVIS_INDEX, "casa.html"), NAV, "casa.html")
    if INDEXABLE:
        t = canvia(t, [(ROBOTS, "")], "casa.html")
    comprova("index.html", t)
    return t


def fonts(fonts_html):
    t = canvia(fonts_html, CANVIS_FONTS, "fonts.html")
    for patro in FORA_FONTS:
        t = treu(t, patro, "fonts.html")
    if INDEXABLE:
        t = canvia(t, [(ROBOTS, "")], "fonts.html")
    comprova("fonts.html", t)
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
    pagines = {"index.html": index(llegeix("casa.html")), "fonts.html": fonts(llegeix("fonts.html"))}
    os.makedirs(os.path.join(desti, "es"), exist_ok=True)
    for nom, html in pagines.items():
        escriu(nom, html)
        escriu("es/" + nom, castella(html, nom))
    escriu("sw.js", service_worker(llegeix("sw.js")))
    for nom in ("estil.css", "comu.js", "casa.js"):
        shutil.copy(os.path.join(web, nom), desti)
    shutil.copytree(propi, desti, dirs_exist_ok=True)
    for nom in ("LICENSE", "LICENSE-CONTINGUTS.md"):
        shutil.copy(os.path.join(ARREL, nom), desti)
    open(os.path.join(desti, ".nojekyll"), "w").close()
    for nom in ("manifest.webmanifest", "README.md"):
        comprova(nom, llegeix_fitxer(os.path.join(desti, nom)))
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
