---
version: 1
slug: "templates-public-landing-html"
primary_target: "templates/public/landing.html"
related_targets: []
---

# Landing pública de Turno ("/")

Modo: Persuade. Audiencias: clientes (sobre todo personas mayores) que vienen a pedir una cita sobre un producto de Exducere Online; en segundo plano, empresas que evalúan Turno para su negocio.
Trabajo del visitante: entender en segundos que aquí pide una cita por videollamada y elegir el producto. Mientras no exista el portal de reserva, cada producto lleva a su sitio; «Agendar» se suma en la fase 4.
Contenido real: productos desde la base (Kawana Proctoring, Moodle con IA, Moodle web/móvil, Servidores). Sin testimonios, precios ni métricas. Teléfono de atención: se muestra solo cuando exista en Configuración.
Restricciones: texto base ≥19 px, botones ≥56 px, trato de usted, sin degradados ni sombras, Bootstrap 5 grid, sin comentarios ni <style>.
Pendiente: textos en/pt (fase 7), teléfono de atención, botón «Agendar» por producto.

## Direction contract

THESIS: La página abre mostrando el objeto que el cliente va a recibir —su turno— en vez de un hero de marketing con métricas; se niega a la cuadrícula de mes y a las tarjetas icono+título genéricas.
OWN-WORLD (revisado por el usuario): lenguaje de materiales de Apple. Fondo nube #E6F0F5 con tres campos de color desenfocados (celeste, verde claro, azul) detrás; cabecera, tarjeta de turno y lista de productos como vidrio translúcido (blanco al 58 %, backdrop-filter blur 28px saturate 170 %, borde claro de 1px, sombra suave y difusa); banda de empresas como vidrio oscuro (#003052 al 72 %). Tipografía de sistema (SF Pro / Segoe UI) con tracking negativo en titulares (-0.03em) y cuerpo cerca de 0; azul #005082 para la hoja de calendario y los botones de acción, verde #67BD01 para el botón principal y el foco. Fallbacks: prefers-reduced-transparency → superficies sólidas; prefers-contrast → bordes definidos; prefers-reduced-motion → sin materialización.
STORY: El visitante ve su cita tal como llegará (día, hora en palabras, videollamada, código), entiende que solo debe elegir el producto, baja a la lista de productos, y si es una empresa encuentra al final la banda azul que presenta Turno.
FIRST VIEWPORT: Columna izquierda (7/12): titular Fredoka de 3 líneas «Su cita, a la hora acordada.», bajada de 2 líneas y botón verde de 56px «Elegir producto». Columna derecha (5/12): tarjeta de turno a escala real con hoja de calendario (mes en banda azul, día grande), «2:20 de la tarde», «Videollamada con el equipo de Moodle» y código QW-7K2M-91, rotulada «Así llega su cita».
FORM: Tarjeta de turno en grande (estructura 3 de 7 en la lista propia, sorteada) · seed b30b84d5 · construcción por código.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
