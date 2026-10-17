# Módulo agenda

Integración con Google Calendar y Gmail: skill `agendamiento-google`.

## Micrositio

- Toda pantalla autenticada, incluidas las de `agenda/`, extiende `base.html` (barra lateral agrupada por `ModuloGrupo`, cabecera con `eyebrow`/`titulo_pagina`/`acciones`, estilos en `static/css/agenda/micrositio.css`).
- Menú y contadores salen de `agenda/context_processors.py`.
- Referencia visual obligatoria: `docs/Micrositio de agendas demos de interfaz (1).html`. Pantalla nueva = calco de la maqueta; verla con render en Chrome headless.

## Autogestión vs. administración

«Mis turnos», «Mi agenda», «Mis aplicaciones» muestran solo lo del usuario, sin selector de otras personas. La vista de todo el equipo es otra pantalla o módulo (ej. `/agenda/turnos-equipo/`) para líderes y administradores.
