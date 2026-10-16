---
name: Turno de Exducere Online
description: Papel blanco sobre un blanco cálido, tinta casi negra, un solo azul institucional y un solo verde para actuar; Geist en todo.
colors:
  azul: "#005082"
  azul-oscuro: "#003a5f"
  azul-medio: "#0a6aa6"
  verde: "#67BD01"
  verde-oscuro: "#58a300"
  fondo: "#fcfbf8"
  fondo-suave: "#f3f4f6"
  papel: "#ffffff"
  tinta: "#071a31"
  texto: "#3d4a56"
  gris: "#5f6d77"
  borde: "#e4e6e9"
  nube: "#E6F0F5"
  tinta-panel: "#1A2B3C"
  pizarra: "#64748B"
  rojo: "#D93838"
  azul-velo: "rgba(0, 80, 130, 0.1)"
  azul-borde-suave: "#b3cbdb"
typography:
  display:
    fontFamily: "Geist, Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "clamp(2.4rem, 4.8vw, 3.75rem)"
    fontWeight: 500
    lineHeight: 1.06
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Geist, Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "clamp(1.6rem, 2.8vw, 2.25rem)"
    fontWeight: 500
    lineHeight: 1.12
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Geist, Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "1.25em"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  numeral:
    fontFamily: "Geist, Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "2.4em"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "-0.04em"
    fontVariation: "tabular-nums"
  body:
    fontFamily: "Geist, Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.5
  body-panel:
    fontFamily: "Geist, Inter, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  titulo-panel:
    fontFamily: "Geist, Inter, system-ui, sans-serif"
    fontWeight: 600
    letterSpacing: "-0.02em"
  label:
    fontFamily: "Geist, Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "0.8em"
    fontWeight: 600
    letterSpacing: "0.06em"
rounded:
  pildora: "999px"
  hoja: "0.9rem"
  interior: "0.9rem"
  tarjeta: "1.25rem"
  banda: "1.5rem"
  acceso: "16px"
  campo: "10px"
  panel-sm: "0.55rem"
  panel-md: "0.85rem"
  panel-lg: "1.1rem"
  panel-xl: "1.6rem"
spacing:
  xs: "0.5rem"
  sm: "1rem"
  md: "1.5rem"
  lg: "2.5rem"
  xl: "3.5rem"
  hero: "3rem 0 4rem"
components:
  button-primary:
    backgroundColor: "{colors.azul}"
    textColor: "{colors.papel}"
    rounded: "{rounded.pildora}"
    padding: "0.6rem 1.5rem"
    height: "48px"
    typography: "{typography.body}"
  button-primary-hover:
    backgroundColor: "{colors.azul-oscuro}"
    textColor: "{colors.papel}"
  button-action:
    backgroundColor: "{colors.verde}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.pildora}"
    padding: "0.6rem 1.5rem"
    height: "48px"
    typography: "{typography.body}"
  button-action-hover:
    backgroundColor: "{colors.verde-oscuro}"
    textColor: "{colors.tinta}"
  button-toggle:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.pildora}"
    padding: "0.4rem 1.1rem"
    height: "44px"
  button-toggle-pressed:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.papel}"
  nav-link:
    backgroundColor: "transparent"
    textColor: "{colors.gris}"
    padding: "8px 0"
  nav-link-active:
    backgroundColor: "transparent"
    textColor: "{colors.azul}"
  nav-btn:
    backgroundColor: "{colors.azul}"
    textColor: "{colors.papel}"
    rounded: "{rounded.pildora}"
    padding: "9px 20px"
    height: "44px"
  chip-etiqueta:
    backgroundColor: "{colors.fondo-suave}"
    textColor: "{colors.gris}"
    rounded: "{rounded.pildora}"
    padding: "0.1rem 0.7rem"
  card-turno:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.tarjeta}"
    padding: "1.5rem 1.5rem 1.25rem"
  card-paso:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.tarjeta}"
    padding: "1.5rem 1.5rem 1.5rem 4.4rem"
  lista-productos:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.tarjeta}"
    padding: "1.4rem 1.5rem"
  hoja-calendario:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.hoja}"
    width: "5rem"
  hoja-calendario-mes:
    backgroundColor: "{colors.azul}"
    textColor: "{colors.papel}"
    padding: "0.25rem 0.6rem"
    typography: "{typography.label}"
  bloque-suave:
    backgroundColor: "{colors.fondo-suave}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.interior}"
    padding: "0.9rem 1rem"
  banda-tinta:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.papel}"
    rounded: "{rounded.banda}"
    padding: "3rem 2.5rem"
  input-acceso:
    backgroundColor: "{colors.fondo}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.campo}"
    padding: "0.55rem 0.9rem"
    height: "50px"
  celda-turno:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.pizarra}"
    rounded: "{rounded.panel-sm}"
    height: "2.1rem"
  celda-turno-pressed:
    backgroundColor: "{colors.azul}"
    textColor: "{colors.papel}"
---

# Design System: Turno de Exducere Online

## Overview

**Creative North Star: "El turno sobre la mesa"**

Turno es la plataforma de citas de Exducere Online y su mundo visual nace de un solo objeto: el turno que el cliente va a recibir, puesto en grande antes de pedirle nada. Todo lo demás es la mesa de alrededor. En lo público esa mesa es un blanco cálido (#fcfbf8) sobre el que descansan superficies de papel blanco delimitadas por líneas finas (#e4e6e9); la tinta es un azul casi negro (#071a31) que escribe titulares, numerales y la banda de cierre; el azul institucional (#005082) solo pinta la banda de mes de la hoja de calendario, los numeradores de los pasos y los botones que llevan a otro sitio; el verde (#67BD01) aparece una vez por bloque, en el botón que hay que pulsar. No hay degradados, no hay vidrio, no hay sombras, no hay cuadrícula de mes.

Una sola familia tipográfica, Geist (autoalojada, eje variable 100–900), hace todo el trabajo: titulares en peso 500 con tracking muy cerrado (−0.035em en el display), cuerpo en 400, etiquetas en 600. Lo que diferencia un titular de un párrafo es el tamaño, el color de tinta y el tracking, no el cambio de fuente. El estilo es plano y sin ornamentos, parecido a una herramienta de agenda profesional: la jerarquía la dan el espacio en blanco y las líneas de 1 px.

El sistema tiene dos registros con la misma marca y la misma fuente. El **registro público** (landing `/`, legales, acceso) es lento, grande y formal: texto base de 17 px (21 px con «Letra más grande»), píldoras de 48 px, trato de usted, una decisión por pantalla. El **registro interno** (panel Django sobre Bootstrap 5.3, `/agenda/…`) es denso y operativo: hereda los tokens de marca por las variables `--turno-*` y `--bs-*` redefinidas en `static/base_adicional.css`, sigue sobre fondo nube (#E6F0F5) con tinta #1A2B3C, y admite tres sombras tonales en tarjetas, menús y modales. Entre registros cambia la temperatura del fondo y la tinta; no cambian el azul, el verde, Geist, las píldoras ni la regla de un solo botón de acción.

**Key Characteristics:**
- Blanco cálido de fondo, papel blanco con borde de 1 px (#e4e6e9), tinta casi negra: tres materiales en lo público.
- Geist en todo, peso 500 para titulares con tracking negativo; nunca una segunda familia.
- Azul #005082 para informar y navegar; verde #67BD01 una sola vez por bloque, siempre con texto tinta.
- Sin sombras, degradados ni vidrio en lo público; el panel usa solo tres sombras de tinta azulada.
- Píldoras de 999 px para lo que se pulsa, 1.25 rem para lo que contiene; grid de Bootstrap 5 para toda composición.

## Colors

Una paleta institucional corta sobre un blanco cálido: tinta casi negra para leer, un azul profundo para la marca y un verde ácido para actuar.

### Primary
- **Azul institucional** (`azul`, #005082): tinta de marca. Banda de mes en la hoja de calendario, numerador circular de cada paso, subproductos en la fila de producto, iconos de contexto (videollamada, teléfono, integraciones), enlaces, botón `btn-primary` («Ver sitio»), píldora «Iniciar sesión» de la cabecera, lado institucional de la pantalla de acceso, anillo de foco público (3 px), `--bs-primary` y celda de turno seleccionada en el panel.
- **Azul institucional oscuro** (`azul-oscuro`, #003a5f): hover y focus del botón azul de la landing y `--bs-link-hover-color` del panel. No se usa en reposo.
- **Azul medio** (`azul-medio`, #0a6aa6): hover de la píldora «Iniciar sesión» y del botón de acceso, borde de foco del campo de acceso y color del eyebrow de la pantalla de acceso. Solo en `publico.css` y `auth.css`.
- **Velo azul** (`azul-velo`, rgba(0,80,130,0.1)): `--bs-primary-bg-subtle`; resumen de turnos, hover de cabeceras de la rejilla, icono de Google en aplicaciones, ítem activo de la barra lateral (al 12 %). Solo en el panel.
- **Borde azul suave** (`azul-borde-suave`, #b3cbdb): `--bs-primary-border-subtle`; borde de hover de las celdas de turno.

### Secondary
- **Verde acción** (`verde`, #67BD01): el único color de acción. Botón `btn-success` («Elegir producto», «Conocer Exducere Online», guardar en el panel), `::selection` al 35 %, subrayado de 2 px del ítem activo de la navegación pública, foco de la navegación (2 px) y de la rejilla de turnos (3 px). El texto sobre verde es siempre tinta, nunca blanco.
- **Verde acción oscuro** (`verde-oscuro`, #58a300): hover y focus del botón verde en la landing.

### Tertiary
- **Rojo alerta** (`rojo`, #D93838): `--bs-danger` del panel. Solo errores, borrado y alertas; no aparece en lo público.
- **Pizarra** (`pizarra`, #64748B): `--bs-secondary` del panel; texto auxiliar (`.agenda-sub`, horas de la rejilla, texto de celda en hover, icono de Zoom).

### Neutral
- **Blanco cálido** (`fondo`, #fcfbf8): fondo de todas las páginas públicas (`.pb-body`, `.au-body`), hover de la fila de producto y fondo en reposo del campo de acceso.
- **Gris suave** (`fondo-suave`, #f3f4f6): la cuarta superficie, solo dentro de la tarjeta de turno: bloque «Videollamada con el equipo de…» y píldora «Ejemplo».
- **Papel** (`papel`, #ffffff): cabecera pública, tarjeta de turno, tarjetas de paso, lista de productos, tarjeta de acceso, celdas de turno libres y todo `.form-control` del panel (regla global `!important`).
- **Tinta** (`tinta`, #071a31): titulares, día y hora de la hoja, código de cita, nombres de producto, fondo de la banda de cierre y del botón «Letra más grande» cuando está pulsado.
- **Texto** (`texto`, #3d4a56): color base del cuerpo público (`.pb-body`).
- **Gris** (`gris`, #5f6d77): bajada del hero, fechas, descripciones, intros de sección, etiquetas del turno, enlaces de navegación en reposo y pie. Es el color de todo lo que acompaña.
- **Borde** (`borde`, #e4e6e9): la única línea pública. Borde de tarjetas, hoja de calendario, lista de productos, cabecera y pie; línea continua entre filas y entre secciones (`.ld-seccion`); línea discontinua del pie de la tarjeta; punto medio «·» entre subproductos.
- **Nube** (`nube`, #E6F0F5): fondo del panel interno (`--bs-body-bg`) y del chip de miembro. En lo público ya no se usa.
- **Tinta del panel** (`tinta-panel`, #1A2B3C): `--bs-body-color`, títulos, texto sobre verde y base de las tres sombras del panel.

### Named Rules
**La regla del único verde.** El verde solo se pinta en el botón de acción principal de cada bloque, en la selección de texto y en el subrayado del ítem activo. Nunca en texto corrido, iconos, bordes decorativos ni fondos. Si hay dos botones verdes a la vista en una sección, uno sobra.

**La regla de la tinta sobre verde.** Todo texto sobre #67BD01 va en tinta (`.btn-success` público y del panel, `.badge.bg-success`, `::selection`). Blanco sobre ese verde no cumple contraste y está prohibido en el código.

**La regla del azul que informa.** El azul institucional nunca es fondo de página ni de tarjeta: aparece como banda, numerador, icono, enlace o botón de navegación. La única superficie azul grande es el lado institucional de la pantalla de acceso.

## Typography

**Display Font:** Geist (fallback Inter, system-ui), eje variable 100–900, autoalojada en `/static/fonts/turno_fuentes.css`, subconjunto latino, `font-display: swap`.
**Body Font:** Geist, la misma familia.

**Character:** Una sola sans geométrica y neutra que se vuelve titular por tamaño y tracking, no por peso: los encabezados van en 500 con tracking de −0.025 a −0.035em, el cuerpo en 400 con tracking apenas negativo (−0.005 a −0.01em), y las pocas etiquetas en 600. El resultado es sobrio y técnico, nunca gritón; la calidez la ponen el fondo y el copy.

### Hierarchy
- **Display** (Geist 500, `clamp(2.4rem, 4.8vw, 3.75rem)`, 1.06, −0.035em): el titular de la landing («Su cita, a la hora acordada.»), máximo 14ch, `text-wrap: balance`. Uno por página.
- **Headline** (Geist 500, `clamp(1.6rem, 2.8vw, 2.25rem)`, 1.12, −0.03em): encabezados de sección (`.ld-h2`), también en blanco dentro de la banda de cierre. El lema de la pantalla de acceso (`.au-lema`, 600, `clamp(2rem, 4vw, 3.4rem)`, 1.18) y su título (`.au-title`, 600, 1.75rem) viven en esta capa.
- **Title** (Geist 500, 1.25em, 1.2, −0.025em): nombre de cada producto (`.ld-fila-nombre`); el título de cada paso baja a 1.15em con −0.02em.
- **Numeral** (Geist 500, 2.4em, 1, −0.04em, `tabular-nums`): el día en la hoja de calendario. Sus hermanos: la hora en palabras (1.7em, 1.1, −0.03em) y el código de la cita (1.3em, +0.04em). Todo numeral va en tinta, nunca en gris.
- **Body** (Geist 400, 17px, 1.5): texto base público (`--ld-base`), 21 px cuando `html.ld-grande` está activo. Todo lo público se mide en `em` sobre esta base. La bajada del hero sube a 1.15em y 40ch; las intros se detienen en 52ch y las descripciones de producto en 48ch.
- **Body (panel)** (Geist 400, 1rem, 1.5): cuerpo del panel a escala Bootstrap; `.agenda-sub` y cabeceras de la rejilla bajan a 0.8rem, las celdas a 0.72rem.
- **Título (panel)** (Geist 600, tamaño Bootstrap, −0.02em en la marca): `h1–h6`, `.page-title`, `.modal-title` y el alias de la barra lateral; el total de turnos usa 2rem en azul con `tabular-nums`.
- **Label** (Geist 600, 0.8em, +0.06em, mayúsculas): la banda de mes de la hoja, blanco sobre azul. Es la única mayúscula del mundo público de la landing.

### Named Rules
**La regla de la única familia.** Geist en todo: titulares, cuerpo, numerales, botones, panel. No se añade una segunda fuente ni se usan los `@font-face` de Fredoka, Inter o Plus Jakarta Sans que siguen declarados en `turno_fuentes.css`.

**La regla del em público.** En lo público ningún tamaño va en `rem` ni `px` salvo `--ld-base`; todo deriva en `em` para que «Letra más grande» (17 → 21 px) escale titulares, botones y hoja de calendario sin romper nada.

**La regla del 500 cerrado.** Un titular es Geist 500 con tracking negativo; el 700 no existe en la landing. Si un texto necesita más presencia, crece de tamaño o pasa a tinta, no engorda.

## Layout

Toda composición multicolumna usa el grid de Bootstrap 5 (`.container`, `.row`, `col-*`); el CSS propio solo describe el material de cada pieza. La landing vive en un `.container` normal con cabecera blanca pegajosa de 1 px de borde inferior (14 px de relleno vertical) y pie con la misma línea; el `main` lleva 36 px arriba y 60 px abajo.

**Primer viewport público:** barra superior con el conmutador «Letra más grande» alineado a la derecha; luego `row align-items-center g-4 g-lg-5` con `col-lg-7` para titular, bajada, botón verde y nota «Sin registro ni contraseña», y `col-lg-5` para la tarjeta de turno a escala real con su nota debajo. El hero mide 3 rem arriba y 4 rem abajo (1.75 / 2.75 rem en < 768 px); por debajo de 992 px la tarjeta pasa debajo del texto, el titular pierde su tope de 14ch y los botones se estiran al 100 %.

**Ritmo vertical:** cada sección (`.ld-seccion`) lleva 3.5 rem arriba y abajo y una línea superior de 1 px (2.5 rem en móvil); la banda de cierre no lleva línea y termina con 3.5 rem de margen. Dentro de la tarjeta de turno el paso es 1.25 rem entre bloques y 1 rem entre pie y cuerpo.

**Pasos:** `ol.ld-pasos.row.g-3` con tres `col-md-4`; cada paso es una tarjeta de papel con el número en un círculo azul de 2 rem a la izquierda (relleno izquierdo 4.4 rem). **Lista de productos:** una sola tarjeta contenedora con filas internas (`.ld-fila`, 1.4 rem 1.5 rem) separadas por líneas de 1 px y `row g-3` dentro: `col-lg` para texto, `col-lg-auto` para el botón «Ver sitio» (100 % en móvil, mínimo 10 rem desde 992 px). **Integraciones:** lista horizontal de icono + texto con `gap: .75rem 1.5rem`.

**Panel interno:** pantallas en `.card` de Bootstrap con `row g-3`; la rejilla de turnos es una `<table>` real (`border-spacing: 4px`, cabecera pegajosa sobre fondo nube, mínimo 560 px con scroll horizontal, 70 vh de alto). La barra lateral muestra un icono cuadrado de 38 px (radio 0.6 rem) junto al alias en Geist 600 azul. **Acceso:** dos columnas a pantalla completa (`.au-stage`, 100svh), lado azul a la izquierda con relleno `clamp(28px, 5vw, 72px)` y tarjeta de 460 px centrada a la derecha; en < 992 px se apilan y el lado azul se reduce a logo y lema.

**Puntos de corte observados:** 420 px (hoja a 4.3 rem, día a 2.1em, hora a 1.4em), 575.98, 767.98 y 991.98 px (Bootstrap).

## Elevation & Depth

Lo público es plano por contrato de marca: ninguna superficie de la landing lleva `box-shadow`, `backdrop-filter` ni degradado. La profundidad se construye con tres planos (blanco cálido, papel, tinta) y con líneas de 1 px: borde continuo para contener, línea horizontal para separar secciones y filas, borde discontinuo para el pie de la tarjeta. Lo único que «llega» es la tarjeta de turno, que entra con 12 px de desplazamiento y fundido de 0.6 s (`cubic-bezier(.2, .9, .25, 1)`) una sola vez; los botones responden con `scale(0.97)` en 100 ms al pulsarse y las filas cambian de fondo en 150 ms. Todo se desactiva con `prefers-reduced-motion`.

El panel interno sí usa una familia mínima de sombras tonales de la tinta, definidas como `--bs-box-shadow*` en `static/base_adicional.css`, siempre azuladas (rgba(26, 43, 60, …)), nunca negras ni desplazadas en duro.

### Shadow Vocabulary (solo panel interno)
- **Reposo de tarjeta** (`box-shadow: 0 0.15rem 0.4rem rgba(26, 43, 60, 0.06)`): `.card` en reposo.
- **Tarjeta en hover / menú desplegable** (`box-shadow: 0 0.5rem 1.25rem rgba(26, 43, 60, 0.08)`): `.card:hover` y `.dropdown-menu` (sin borde).
- **Modal** (`box-shadow: 0 1rem 2rem rgba(26, 43, 60, 0.12)`): `.modal-content` (sin borde).

### Named Rules
**La regla del papel plano.** Fuera del panel interno no hay sombras: una pieza pública que necesite destacar cambia de plano (papel sobre blanco cálido, tinta sobre blanco cálido) o gana un borde, no una sombra.

**La regla de la sombra de tinta.** Cuando el panel usa sombra, es de la tinta (#1A2B3C) a 6–12 % y difusa; nunca negra, nunca de desplazamiento duro.

## Shapes

Dos geometrías conviven: la píldora y la esquina generosa. Todo lo que se pulsa es píldora (999 px): botones, enlace-botón de la cabecera, conmutador de letra, etiqueta «Ejemplo», chips de miembro en el panel. Todo lo que contiene es redondeado en proporción a su tamaño: hoja de calendario 0.9 rem con la banda de mes recortada por `overflow: hidden`; bloque interior 0.9 rem; tarjeta de turno, tarjetas de paso y lista de productos 1.25 rem; banda de cierre 1.5 rem; tarjeta de acceso 16 px con campos y botón de 10 px. En el panel la escala la fija Bootstrap redefinido: 0.55 / 0.85 / 1.1 / 1.6 / 2.25 rem, con 50 rem para píldora.

Los bordes son siempre de 1 px (#e4e6e9 en lo público, `--bs-border-color` en el panel); no hay bordes gruesos ni dobles. El numerador de los pasos es un círculo perfecto (`border-radius: 50%`, 2 rem). Los logos de Turno nunca se deforman, nunca bajan de 24 px de alto y conservan un área de respeto igual a la altura de la «T».

## Components

### Buttons
Píldoras de color sólido, sin relieve, que se oscurecen al tocarlas y se encogen un 3 % al pulsarlas.
- **Shape:** píldora (999 px), `min-height: 48px`, `padding: .6rem 1.5rem`, Geist 500 a 1em con −0.01em, `inline-flex` centrado; el icono Font Awesome va delante con 0.6 rem de separación o detrás con `ms-2`.
- **Primary (`btn-primary`):** azul #005082 con texto blanco; para ir a algún lado («Ver sitio»). Hover: #003a5f.
- **Action (`btn-success`):** verde #67BD01 con texto tinta; el único botón de acción principal de cada bloque («Elegir producto», «Conocer Exducere Online», guardar en el panel). Hover: #58a300.
- **Focus:** anillo `outline: 3px solid #005082; outline-offset: 3px` en toda la landing (`.pb-body a/button:focus-visible`).
- **Active:** `transform: scale(0.97)` en 100 ms; sin sombra ni desplazamiento.
- **Toggle «Letra más grande» (`.ld-letra`):** `btn-light` de 44 px con borde 1 px #e4e6e9 sobre papel, texto tinta Geist 500 a 0.95em, una «A» en 600 a 1.3em como icono; con `aria-pressed="true"` invierte a fondo tinta y texto blanco y el rótulo pasa a «Letra normal». Persiste en `localStorage`.
- **Acceso (`.au-card .btn-primary`):** la excepción cuadrada: 48 px de alto, radio 10 px, ancho completo, Geist 600 a 0.97rem; hover a #0a6aa6; foco con anillo verde de 3 px.
- **Mobile:** todo `.ld-boton` ocupa el 100 % del ancho por debajo de 768 px.

### Chips
- **Etiqueta «Ejemplo» (`.ld-turno-tag`):** píldora de gris suave #f3f4f6 con texto gris #5f6d77, Geist 500 a 0.8em con +0.02em, sin mayúsculas, `padding: .1rem .7rem`; alineada a la derecha sobre la tarjeta.
- **Chip de miembro (panel, `.agenda-miembro`):** píldora `--bs-border-radius-pill` con borde `--bs-border-color`, fondo nube, 0.8rem, con un botón mínimo de quitar dentro.

### Cards / Containers
- **Tarjeta de turno (`.ld-turno`):** papel, borde 1 px #e4e6e9, radio 1.25 rem, `padding: 1.5rem 1.5rem 1.25rem`, texto tinta. Estructura fija: fila con hoja de calendario (`col-auto`) y fecha en gris + hora en tinta (`col`); bloque gris suave «Videollamada con el equipo de…» con icono azul; pie con borde discontinuo que lleva el QR de 88 px (`col-auto`) y etiqueta gris + código en tinta (`col`). Entra con la animación `ld-llegar`.
- **Tarjeta de paso (`.ld-paso`):** papel, borde 1 px, radio 1.25 rem, relleno 1.5 rem con 4.4 rem a la izquierda para el numerador azul de 2 rem; título Geist 500 a 1.15em y texto gris.
- **Lista de productos (`.ld-lista`):** una tarjeta contenedora de papel con borde 1 px y radio 1.25 rem; filas de 1.4 rem 1.5 rem separadas por líneas de 1 px que pasan a blanco cálido en hover.
- **Tarjeta del panel (`.card`):** Bootstrap con sombra de reposo y hover (ver Elevation & Depth).
- **Tarjeta de acceso (`.au-card`):** papel, borde 1 px, radio 16 px, `padding: 40px 40px 32px`, 460 px de ancho máximo.
- **Prosa legal (`.lnd-prose`):** papel, borde 1 px, radio 14 px, `padding: 28px 32px`, interlineado 1.65.

### Inputs / Fields
- **Style:** `.form-control` siempre con fondo blanco en el panel (regla global `!important`). En el acceso: 50 px de alto mínimo, borde 1 px, radio 10 px, 1rem, texto tinta, fondo blanco cálido en reposo que pasa a blanco en foco, placeholder #94a3b8, etiqueta Geist 600 a 0.82rem.
- **Focus:** borde #0a6aa6 con anillo de 3 px; el panel usa el foco por defecto de Bootstrap recoloreado por `--bs-primary`.
- **Disabled:** `opacity: .7; cursor: wait` en el botón de envío del acceso.

### Navigation
- **Pública (`.pb-nav`):** cabecera blanca pegajosa con borde inferior de 1 px; enlaces Geist 500 a 1rem en gris, sin subrayado, borde inferior de 2 px transparente que pasa a verde en hover y en `.is-active` mientras el texto pasa a azul; el último ítem («Iniciar sesión») es una píldora azul de 44 px (`.pb-btn`, hover #0a6aa6). Marca a la izquierda con logo de 40 px máximo. Foco: `outline 2px` verde.
- **Panel:** barra lateral del tema con ítem activo/hover en velo azul al 12 % y radio `--bs-border-radius-sm`; marca = icono cuadrado de 38 px + alias en Geist 600 azul con −0.02em.

### Hoja de calendario (firma)
El objeto que identifica a Turno: un bloque de 5 rem (4.3 rem en < 420 px) con borde de 1 px #e4e6e9, radio 0.9 rem y recorte interior; arriba la banda de mes en azul sólido con el mes en Geist 600 mayúsculas a 0.8em (+0.06em) en blanco; abajo el día en Geist 500 a 2.4em, tinta, −0.04em, tabular. A su derecha, la fecha completa en gris y la hora en palabras («2:20 de la tarde») en Geist 500 a 1.7em tinta. Se reutiliza en cualquier superficie que muestre una cita; nunca se sustituye por una cuadrícula de mes.

### Banda de cierre (firma)
Sección a todo ancho dentro del contenedor, fondo tinta #071a31, texto blanco, radio 1.5 rem, `padding: 3rem 2.5rem` (2 rem 1.25 rem en móvil): logo blanco de Turno de 200 px (170 en móvil), headline en blanco, lista con viñetas en blanco al 85 % y, en la columna derecha (`col-lg-5 text-lg-end`), un único botón verde. Es la única superficie oscura de la landing y marca el final de la página.

### Rejilla de turnos (panel)
Celdas de 2.1 rem de alto, papel con borde 1 px `--bs-border-color` y radio `--bs-border-radius-sm`; en hover el borde pasa a #b3cbdb y aparece la hora en pizarra; `aria-pressed="true"` las llena de azul con texto blanco. Foco: anillo verde de 3 px. El resumen (`.turnos-resumen`) va en velo azul con el total en Geist 600 a 2rem azul.

## Do's and Don'ts

### Do:
- **Do** componer con el grid de Bootstrap 5 (`row` + `col-*`) y dejar el CSS propio para el material; archivo en `static/css/<app>/` enlazado por ruta absoluta `/static/...` con `?vX.Y` incrementado en cada cambio.
- **Do** mantener en lo público texto base de 17 px, píldoras de 48 px, tamaños en `em`, el conmutador «Letra más grande» y el trato de «usted»; «cita» y «videollamada», nunca «reunión» ni «Meet» hacia el cliente.
- **Do** escribir todo en Geist: titulares en 500 con tracking negativo, cuerpo en 400, etiquetas en 600.
- **Do** usar verde solo en el botón de acción principal de cada bloque, siempre con texto tinta, y azul #005082 para informar y navegar.
- **Do** mostrar una cita con la hoja de calendario y la tarjeta de turno; una lista de opciones como filas separadas por líneas de 1 px dentro de una sola tarjeta.
- **Do** declarar `prefers-reduced-motion` para toda animación o transición nueva.
- **Do** escribir el copy visible en español y los textos de ayuda de iconos con `aria-hidden` en el icono y `visually-hidden` en el texto.

### Don't:
- **Don't** usar degradados, mesh, glassmorphism ni `backdrop-filter`, ni deformar o reducir el logo por debajo de 24 px.
- **Don't** añadir `box-shadow` a ninguna superficie pública; en el panel, solo las tres sombras de tinta ya definidas.
- **Don't** usar `btn-outline-*`: los botones son píldoras sólidas azules o verdes.
- **Don't** escribir `<style>` en plantillas ni comentarios en HTML, CSS o JS.
- **Don't** poner texto blanco sobre el verde #67BD01 ni verde en texto, iconos o bordes.
- **Don't** abrir una pantalla pública con una cuadrícula de mes ni con tarjetas icono+título genéricas; el cliente ve primero su turno.
- **Don't** introducir kickers o eyebrows en mayúsculas sobre los titulares de las superficies nuevas, ni una segunda familia tipográfica, ni titulares en 700.
