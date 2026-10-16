# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Clientes que agendan (primarios en lo público):** sobre todo personas mayores y poco técnicas que quieren una cita por videollamada sobre un producto de Exducere Online. Usan computador o teléfono, en español, inglés o portugués. Necesitan una sola decisión por pantalla, letra grande, trato de «usted» y una salida humana (teléfono visible, pedir que les llamen).
- **Empresas que podrían contratar Turno:** visitantes que evalúan Turno como servicio de agendamiento para su propio negocio (sección secundaria de la landing).
- **Equipo interno (unas 7 personas con Google Workspace):** líder general, líderes de equipo, coordinador y miembros. Declaran turnos, atienden citas por Google Meet, registran el cierre y siguen leads.

## Product Purpose

Turno es la plataforma de citas de Exducere Online: el cliente elige día y hora en un portal propio, la cita se asigna al equipo del proyecto y se crea en Google Calendar con Meet, y el equipo la atiende y la cierra. Éxito: que una persona mayor agende sin ayuda en menos de dos minutos y que el equipo deje de coordinar por mensajes.

## Positioning

Una agenda que nace en portales propios, pensada primero para personas mayores (paso a paso, sin cuadrícula de mes como primera pantalla), con enlace personal «Mis citas» y continuidad de sesiones por cliente, asignación automática al equipo del proyecto y Google Calendar/Meet como canal, no como fuente de verdad.

## Operating Context

- Entrada pública en `/`: landing con los productos de Exducere Online y, más abajo, la presentación de Turno para empresas. Mientras el portal de reserva no exista, cada producto muestra su sitio; el botón «Agendar» se suma cuando el portal esté listo.
- Micrositio interno (panel Django): Mi día, agenda, Mis turnos, equipos, cola, cierre, clientes y configuración.
- Google Workspace con cuenta de servicio del sistema; cada usuario conectará además sus cuentas (Gmail, Teams, Zoom) en un perfil de aplicaciones individual.

## Capabilities and Constraints

- Backend Django 5.2 (WSGI, PostgreSQL), Bootstrap 5, sin Celery ni Redis; tareas por cron.
- Un solo dominio: portales y productos son rutas.
- Productos de ejemplo: Kawana Proctoring (kawana.app), Moodle con IA (moodle-assistant-demo.exducereonline.com), Moodle (web y teléfono móvil) y Servidores (exducereonline.com).
- Abierto: teléfono/WhatsApp de atención (se carga después en Configuración del sitio; mientras falte, no se muestra), quién revisa las traducciones en/pt, nombre definitivo de los productos (el estudio decía Qwana/MoAI).

## Brand Commitments

- Nombre: **TURNO de Exducere Online**. Logos en `static/images/turno/` (color, blanco e ícono).
- Paleta: azul `#005082`, verde `#67BD01`, nube `#E6F0F5`, tinta `#1A2B3C`, rojo de alerta `#D93838`.
- Tipografía: títulos Fredoka (o Quicksand), cuerpo Inter (o Plus Jakarta Sans).
- Prohibido: degradados, deformar el logo y sombras. Tamaño mínimo del logo 24 px; área de respeto igual a la altura de la «T».
- Voz: cercanía, confianza, puntualidad y sencillez; «Alguien le atiende a la hora acordada». Trato de «usted»; «cita» y «videollamada», no «reunión» ni «Meet» hacia el cliente.

## Evidence on Hand

- Estudio de requerimientos: `docs/Estudio micrositio de agendas - Exducere Online.docx`; maquetas: `docs/Micrositio de agendas demos de interfaz (1).html`; plan: `docs/plan_micrositio_agendas.md`.
- No hay testimonios, clientes, precios ni métricas reales: no inventarlos.

## Product Principles

1. Una decisión por pantalla para el cliente; la densidad queda para el equipo interno.
2. Siempre una salida humana: teléfono visible y opción de que le llamen.
3. Configurar una vez y olvidar: turnos y portales trabajan solos.
4. La base de Turno es la fuente de verdad; Google es el canal.
5. No construir otro calendario: pedir a Google solo libre y ocupado.

## Accessibility & Inclusion

Clientes mayores: texto base de 19 px o más, botones de al menos 56 px de alto, contraste alto (texto mínimo 4.5:1), botón «Letra más grande», tres idiomas (es, en, pt).
