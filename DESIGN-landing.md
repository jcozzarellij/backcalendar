# Design System: Landing de Turno

Tokens en el frontmatter de `DESIGN.md`; en código viven en el bloque `:root` de `static/css/public/landing.css`. Cómo armar una pantalla: skill `design-guidelines-landing`.

## Overview

**Creative North Star: "El mostrador de turnos"**

Cada producto es un ticket de papel blanco y el cliente solo pulsa «Agendar». Una decisión por bloque, letra grande, trato de usted. El landing presenta; la disponibilidad (días, horas, cupos) vive en la página de agendar de cada producto.

Cuatro materiales: fondo nube, papel blanco, tinta y vidrio (solo la barra). El azul informa y navega; el verde actúa.

## Colors

- **Nube** `#E6F0F5`: fondo de página, con una sola hoja verde del logo arriba a la derecha, recortada por el borde. También el fondo de cada parte de un ticket.
- **Papel** `#ffffff`: ticket, menús.
- **Tinta** `#071a31`: titulares, fondo de la banda de cierre. `tinta-panel` `#1A2B3C`: texto dentro de barra, ticket y menús.
- **Texto público** `#3a4b5c` (cuerpo) y **gris** `#5f6d77` (lo que acompaña).
- **Línea pública** `#c3d4df`: troquel discontinuo del ticket. **Borde** `#e4e6e9`: líneas continuas.
- **Azul** `#005082` (hover `#003a5f`, `#0a6aa6`): enlaces, iconos, numeradores, «Iniciar sesión», banda de empresas. Es la superficie del botón de navegación, nunca el fondo de página.
- **Verde de acción** `#3f7f00` (hover `#336600`): fondo de «Agendar» y del botón de la banda, siempre con texto blanco (4.9:1).
- **Verde del logo** `#67BD01`: la hoja, viñetas e iconos, sin texto encima.
- **Vidrio** `rgba(255,255,255,.6)`: la barra superior.

### Named Rules

**El único verde.** Un botón verde de acción por bloque; si hay dos a la vista, uno sobra.

**El verde del logo no lleva texto.** Todo texto sobre verde va en blanco sobre `#3f7f00` o más oscuro.

**El azul que informa.** Banda, numerador, icono, enlace o botón de navegación; ninguna página ni tarjeta es azul. La banda de empresas es la única superficie azul grande.

**Contraste.** Todo texto ≥ 4.5:1 sobre su fondo.

## Typography

Roboto en todo el landing y el portal público: 800/900 para titulares, con tracking de −0.03 a −0.035em, y 400 para el cuerpo. Autoalojada en `static/fonts/family-roboto/woff` (subconjunto latino 400, 500, 700 y 900), declarada en `static/fonts/turno_fuentes.css`. El botón de confirmación de los avisos (`.ag-swal-si`, el «OK» de «¡Listo! Su cita quedó agendada») es sólido azul `#005082` con texto blanco, sin aro de enfoque exterior.

- **Display** `clamp(2.2em, 2.4vw + 1.3em, 3.7em)`, 1.02: un titular por página.
- **Headline** `clamp(1.5em, 1.2vw + 1.1em, 2.1em)`, 1.12: encabezados de sección.
- **Ticket** `1.65em`, 1.1: nombre del producto.
- **Body** Roboto 400, 19 px (23 px con «Letra más grande»), 1.5.

### Named Rules

**El em público.** Ningún tamaño va en `rem` ni `px` salvo `--ld-base`; todo deriva en `em` para que «Letra más grande» escale titulares, botones y tickets sin romper nada.

**Una sola mayúscula.** Sin kickers ni eyebrows en mayúsculas sobre titulares.

## Shapes y profundidad

- Píldora (999 px) para lo que se pulsa; ticket 20 px; parte de ticket 16 px; barra de vidrio 22 px; menú 14 px.
- Sin `box-shadow` ni degradados. La profundidad sale de los planos (nube, papel, tinta) y de las líneas de 1 px.
- Vidrio solo en la barra: `backdrop-filter: blur(22px) saturate(170%)`, sólida con `prefers-reduced-transparency`, con `prefers-contrast` y sin soporte de `backdrop-filter`.
- Movimiento: los tickets entran una vez, escalonados 80 ms, con 18 px de desplazamiento y `cubic-bezier(.16, 1, .3, 1)`. El botón pulsado hace `scale(0.97)` en 100 ms. Toda animación nueva declara `prefers-reduced-motion`.
- Foco: anillo de 3 px azul con 3 px de separación.

## Components

- **Ticket** `.ld-ticket`: papel, radio 20 px, troquel discontinuo `#c3d4df` con dos muescas del color del fondo; el talón lleva «Agendar» (`ticket-agendar`, 56 px).
- **Parte** `.ld-parte`: fila nube con su propia píldora verde, para productos con subproductos.
- **Barra** `nav-vidrio`: 72 px, enlaces como píldoras transparentes de 44 px; «Iniciar sesión» (`nav-btn`) es la única píldora sólida.
- **Idioma** `menu-idioma`: menú `<details>` con globo.
- **Letra grande** `.ld-letra`: píldora `sticky` abajo a la derecha, 44 px.
- El detalle de cada pieza (archivos, partials, estados) está en la skill `design-guidelines-landing`.

## Do's and Don'ts

### Do
- Componer con el grid de Bootstrap 5 (`row` + `col-*`) y dejar al CSS propio solo el material de cada pieza.
- Escribir «cita» y «videollamada» hacia el cliente.
- Mantener una decisión por bloque y trato de «usted».
- Subir el `?vX.Y` del `<link>` de cada CSS tocado.

### Don't
- No mostrar horarios, cupos ni «quedan N» en el landing.
- No usar `btn-outline-*`, `<style>` en plantillas ni comentarios en HTML, CSS o JS.
- No abrir una pantalla pública con una cuadrícula de mes ni con tarjetas genéricas de icono y título.
- No agregar sombras, degradados ni segunda familia tipográfica.
