# 15. Instalable como aplicación

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

Juanjo quería instalar la web en el móvil como aplicación y el navegador le
decía que no se podía. La web no tenía manifiesto ni service worker. También
pidió que la recomendación lleve un dibujo visible del vehículo.

## Decisión

- **Manifiesto** (`web/manifest.webmanifest`): nombre «Moto o cotxe?»,
  ventana propia (`standalone`), inicio en la página del trayecto, colores de
  la web e iconos PNG de 192 y 512 px, también para recorte (`maskable`).
- **Icono** (`web/icones/icona.svg`, de donde salen los PNG con
  `rsvg-convert`): el ciclomotor de Tabler Icons bajo la nube con lluvia de
  Lucide, en blanco sobre el azul de la web, dentro de la zona segura del
  recorte. Y `apple-touch-icon` de 180 px para iPhone.
- **Service worker** (`web/sw.js`), primero la red: con conexión siempre se ve
  lo publicado; sin conexión, las páginas guardadas. **Los datos (`.json`) no
  se guardan nunca**: una previsión vieja no debe parecer actual.
- **Vehículo en el veredicto**: coche o ciclomotor de Tabler Icons (MIT),
  del color del veredicto, en la recomendación de la mañana y en la salida
  fuera de las franjas.

## Alternativas descartadas

- **Sin service worker:** algunas versiones de Chrome aún lo piden para
  ofrecer la instalación; con él, Chrome no da ningún error de instalabilidad.
- **Guardar también los datos para verlos sin conexión:** enseñaría como
  actual una previsión de horas antes.
- **Iconos de vehículo de MingCute** (los de la ropa): su «scooter» es un
  patinete, no un ciclomotor.

## Evidencia

- Chrome (Playwright, protocolo de depuración): `Page.getInstallabilityErrors`
  devuelve una lista vacía, el manifiesto no tiene errores y el service
  worker controla la página (05-10-2026, en local).
- Cómo se instala en cada navegador: Chrome, Edge y Samsung Internet lo
  ofrecen solos; Firefox para Android tiene «Añadir a pantalla de inicio» en
  el menú; en iPhone, Safari «Añadir a pantalla de inicio» (desde iOS 26 se
  abre como aplicación por defecto).

## Validación

`probar-web` en los tres navegadores y axe-core en las dos páginas; pruebas
automáticas sin cambios (el entorno de prueba simula `navigator`).
