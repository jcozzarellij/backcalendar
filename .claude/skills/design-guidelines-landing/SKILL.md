---
name: design-guidelines-landing
description: "Línea visual del landing público de Turno y su catálogo, el «mostrador»: tickets troquelados, barra de vidrio, Manrope + DM Sans, verde de acción con texto blanco. Usar al tocar `templates/public/landing.html`, `catalogo.html`, `static/css/public/landing.css` o sus parciales, al cambiar qué productos se publican o destacan, y al llevar otra pantalla pública (portal de agendar, Mis citas, legales) a este estilo."
---

# Landing de Turno: el mostrador

Cada producto se presenta como un **ticket** de mostrador y el cliente solo pulsa «Agendar». La disponibilidad (días, horas, cupos) vive en la página de agendar de cada producto; el landing presenta, no agenda. El landing muestra los **destacados** en una rejilla corta; `/catalogo/` muestra todos los activos con un buscador.

Fuentes de verdad, en este orden:

- Tokens: bloque `:root` de `static/css/public/landing.css`.
- Tokens en el frontmatter de `DESIGN.md`; sistema y reglas de marca: `DESIGN-landing.md`.
- Contrato de dirección: `.impeccable/surfaces/templates-public-landing-html.md`.
- Referencia visual plana: `static/referencias/landing_base.html`, generada con `python scripts/generar_referencia_landing.py`.

## Página nueva con esta línea

Extiende `templates/public/base_landing.html`: ya trae fuentes precargadas, `landing.css`, la barra, el botón de letra grande y los scripts. La página llena `meta_pagina`, `pagina` y, si necesita su JS, `js_pagina`. La vista arma su contexto con `_contexto_publico(request, clave_titulo)` de `public/view_landing.py` (idioma, textos `t`, portal, contacto); las vistas van primero y el helper al final del archivo.

## El mundo

- **Escena**: personas mayores que piden una videollamada desde el computador o el teléfono. Una decisión por bloque, letra grande, trato de usted.
- **Fondo**: nube `#E6F0F5`, con una sola hoja verde del logo asomando arriba a la derecha, recortada por el borde de la página.
- **Ticket**: papel blanco con radio de 20 px. El troquel es discontinuo (`#c3d4df`), con dos muescas del color del fondo, y el talón lleva la acción. Un producto con partes (Moodle) corta el ticket en horizontal y lista cada parte como fila nube con su propia píldora «Agendar».
- **Vidrio**: solo la barra superior (blanco al 60 %, blur 22 px, radio 22 px). Se vuelve sólida con `prefers-reduced-transparency`, con `prefers-contrast` y cuando el navegador no soporta `backdrop-filter`.
- **Tipografía**: Manrope 800 en titulares (−0.03 a −0.035em) y DM Sans en el cuerpo. La base es de 19 px (23 px con letra grande) y todo tamaño público va en `em` sobre esa base.
- **Color**:
  - El azul `#005082` informa y navega: enlaces, iconos, «Iniciar sesión», numeradores y la banda de empresas.
  - El verde de acción `#3f7f00` (hover `#336600`), con texto blanco, va solo en «Agendar» y en el botón de la banda.
  - El verde del logo `#67BD01` queda para la hoja, las viñetas y los iconos, siempre sin texto encima.

## De dónde sale cada dato

Todo ticket se arma en `agenda/funciones_portal.py`: `productos_destacados(portal, idioma, t)` (landing: tickets + total en una consulta) y `productos_publicos(portal, idioma, t)` (catálogo). Ambos parten de `productos_raiz(portal)`, la única definición de producto visible, y devuelven diccionarios ya traducidos; las plantillas solo pintan.

| En el ticket | Campo de `Producto` |
|---|---|
| Título y subtítulo | `nombre` / `descripcion` (y sus versiones `_en`, `_pt`) |
| «40 minutos, por videollamada» | `duracion_min` (o el padre o el parámetro global, vía `tiempos_de`) + la clave `minutos_video`; toda cita es por videollamada |
| «Conocer el sitio» | `sitio_web`; sin URL no se pinta |
| Partes | subproductos con `activo` |

- **Visibilidad**: `activo` = se agenda y aparece en el catálogo; `destacado` = además va al landing (máximo `DESTACADOS_LANDING`). Sin ningún destacado, el landing toma los primeros activos por `orden`.
- «Ver todo el catálogo» aparece solo cuando hay más activos que tickets en el landing.

## Piezas

| Pieza | Dónde | Regla |
|---|---|---|
| Barra | `.pb-header-inner`, `.ld-nav` | Enlaces como píldoras transparentes de 44 px que se aclaran al pasar el mouse; un separador fino antes del idioma; todo en una sola fila. |
| Idioma | `public/parciales/idioma.html` | Menú `<details>` transparente, con globo y nombre del idioma. Bajo 768 px se oculta y el idioma pasa al menú móvil. |
| Sesión | `public/parciales/usuario.html` | Foto redonda de `request.user.get_foto_gris`, sin nombre. «Ir al panel» y «Mi perfil» solo con `is_staff`; «Cerrar sesión» va a `/logout/`. |
| Visitante | `.ld-ingresar` | Píldora azul sólida, la única de la barra. Bajo 768 px se oculta e «Iniciar sesión» va al final del menú móvil, en verde. |
| Menú móvil | `.ld-menu` en `nav_landing.html` | Bajo 768 px la barra queda con logo, foto (si hay sesión) y una píldora azul «Menú» (`<details class="pb-menu">`, la cierra `menus.js`). Despliega Catálogo, Mi cita y Para empresas, el idioma con banderas e «Iniciar sesión». La barra se separa 10 px de los bordes y su vidrio sube a 94 % para que la hoja verde no la tiña. Bajo 360 px la píldora queda solo con el ícono. |
| Barra (plantilla) | `public/parciales/nav_landing.html` | La comparten landing y catálogo; «Catálogo» marca `aria-current` en `/catalogo/`. |
| Letra grande | `public/parciales/letra.html` (`.ld-letra`) | `position: sticky` al final del contenido: flota abajo a la derecha y se detiene antes del pie sin JS. `landing.js` guarda la preferencia en `localStorage`. En el teléfono queda solo «Aa». |
| Vacío y contacto | `public/parciales/ticket_vacio.html`, `contacto.html` | Un solo lugar para «Estamos preparando…» y para «llámenos / escríbanos»; se incluyen con `encabezado` y `clase`. |
| Producto | `public/parciales/ticket.html` (`.ld-ticket`, `.ld-ticket-talon`, `.ld-agendar`) | Un `li` `col-12` por ticket. El talón va a la derecha desde 576 px (con partes, desde 992 px) y debajo en el teléfono; el troquel cambia solo con las variables `--troquel-*` y `--muesca-*`. `.ld-agendar` pinta el verde redefiniendo las `--bs-btn-*` de Bootstrap. |
| Catálogo | `public/catalogo.html`, `static/js/public/catalogo.js` | Buscador sin acentos sobre `data-buscar` del ticket; contador en singular o plural y mensaje sin resultados. |
| Parte | `.ld-parte`, `.ld-parte-accion` | Una parte por fila. En el teléfono la píldora ocupa el ancho completo, debajo del texto. |
| Cierre | `.ld-pasos`, `.ld-banda` | «Tres pasos» es una franja de una fila y solo aparece cuando hay productos; la banda azul siempre cierra la página. |

Los menús comparten `.pb-menu` (en `publico.css`) y `static/js/public/menus.js` (cierra al hacer clic fuera o con Escape; lo cargan `base_landing.html` y `agendar.html`). El aspecto se ajusta con variables `--pb-menu-*`: el landing las redefine en `.pb-landing`, sin sobreescribir reglas. La hoja verde es un SVG de fondo del `body`, así no desborda la página.

## Contenido y estados

- **Textos**: cada texto visible es una clave `ld_*` de `agenda/textos_portal.py`, con español, inglés y portugués. La plantilla solo lee `t.<clave>`.
- **Sin productos**: aparece el ticket vacío `.ld-ticket-vacio` («Estamos preparando los productos») con el sello «Muy pronto» en el talón y los enlaces de contacto, si hay alguno.
- **Contacto**: se toma el teléfono del portal y, si falta, el teléfono de Configuración. Si tampoco hay, se ofrece el correo de Configuración. Sin ningún dato queda solo «¿Ya tiene una cita?».
- **Con sesión iniciada**: la foto reemplaza a «Iniciar sesión».

## Al cambiar el landing

1. Edita la plantilla o el CSS y sube el `?vX.Y` de cada archivo tocado.
2. Si agregaste texto, crea su clave `ld_*` en los tres idiomas.
3. Regenera la referencia: `python scripts/generar_referencia_landing.py`.
4. Mide los contrastes: todo texto ≥4.5:1 sobre su fondo. Cualquier texto sobre verde va en blanco sobre `#3f7f00` o más oscuro.
5. Revisa a 1440, 768, 390 y 320 px los estados: con productos (la referencia), sin productos, sin sesión, con sesión y el menú abierto, el catálogo con búsqueda y sin resultados, y el final de la página con el botón flotante sobre el pie. Playwright solo cuando el usuario lo pide. Si el navegador del MCP está ocupado por otra sesión, lanza `playwright-core` (está en la caché de npx) con un contexto propio.

El trabajo termina cuando, en los cuatro anchos y todos los estados, el documento mide lo mismo que la ventana, la barra ocupa una sola fila y cada menú abierto queda dentro de la pantalla.
