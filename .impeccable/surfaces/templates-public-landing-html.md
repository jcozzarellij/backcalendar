---
version: 1
slug: "templates-public-landing-html"
primary_target: "templates/public/landing.html"
related_targets: []
---

# Landing pública de Turno ("/")

Modo: Persuade. Audiencias: clientes (sobre todo personas mayores) que vienen a pedir una cita por videollamada sobre un producto de Exducere Online; en segundo plano, empresas que evalúan Turno para su negocio.
Trabajo del visitante: entender en segundos que aquí agenda una videollamada y pulsar «Agendar» en su producto; la página de cada producto (`/agendar/<slug>/`) agenda en 4 pasos dentro de la misma página.
Contenido real: productos y subproductos desde la base (Qwana, MoAI · Moodle con IA, Moodle con Plataforma web y Aplicación móvil). El landing no muestra horarios ni cupos. Sin testimonios, precios ni métricas. Teléfono de atención solo cuando exista en el portal.
Restricciones del usuario (2026-10-16): Manrope (titulares) + DM Sans (cuerpo) como lienzocreativo; colores del logo; barra de navegación de vidrio; idioma en un desplegable, no un botón por idioma; botón de acción verde con texto tinta. Bootstrap 5 grid, sin comentarios ni <style>, texto base ≥19 px, botones ≥56 px, trato de usted.
Pendiente: revisión de traducciones en/pt, teléfono de atención, rediseño del portal de agendar con el mismo mundo.

## Direction contract

THESIS: Cada producto se presenta como un ticket de mostrador —papel con muescas y línea troquelada, talón con «Agendar»— en vez de una tarjeta genérica o una lista; se niega a mostrar cupos, métricas y la cuadrícula de iconos.
OWN-WORLD: fondo nube #E6F0F5 con una gran hoja verde #67BD01 (la del logo, forma de esquinas opuestas redondeadas) que asoma arriba a la derecha; barra flotante de vidrio blanco (blur 22px) con radio 22px; tickets de papel blanco con muescas del color del fondo y troquel discontinuo #c9d7e1; Manrope 800 con tracking −0.03em en titulares, DM Sans en cuerpo; azul #005082 para marca e información, verde con texto tinta solo en «Agendar»; banda de empresas en azul sólido.
STORY: El visitante lee que aquí agenda una videollamada, ve los tickets de cada producto, pulsa «Agendar» en el suyo (o en la parte de Moodle que le interesa); si duda, tiene el teléfono y «Ya tengo una cita» a la vista; si es empresa, al final encuentra la banda azul de Turno.
FIRST VIEWPORT: barra de vidrio arriba (logo, Mis citas, Para empresas, desplegable de idioma, «Aa»); columna izquierda 5/12 con titular Manrope de 3 líneas, bajada, ayuda por teléfono y «Ya tengo una cita»; columna derecha 7/12 con la pila de tickets, el primero completo a la vista con su talón verde «Agendar».
FORM: dispensador de turnos de mostrador (estructura 2 de 7 en la lista propia, re-roll 1) · seed:84d8d88db432b19c · construcción por código.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
