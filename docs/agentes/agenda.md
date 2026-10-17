# Módulo agenda

Integración con Google Calendar y Gmail: skill `agendamiento-google`.

## Plataformas externas (Google hoy; Teams y Zoom después)

- Si una plataforma se cae, Turno sigue funcionando: la BD es la fuente de verdad. Citas (`Cita.plataforma`) y
  reuniones propias (`Reunion`, desde Mi agenda) se guardan primero y se reflejan después; lo que falle queda
  pendiente y lo reintenta el cron `reconciliar_google` (y el botón «Reintentar»).
- Toda llamada a Google sale por `funciones_google`, que tiene tiempo límite y convierte cualquier fallo en
  `ErrorGoogle` (con `reintentable`). Ninguna vista ni `on_commit` debe dejar escapar una excepción de red.
- Las reuniones van por `funciones_reuniones` (crear, editar, mover, eliminar, sincronizar); una plataforma nueva
  se suma con su rama en `sincronizar` y su clave en `IMPLEMENTADAS`.

## Micrositio

- Toda pantalla autenticada, incluidas las de `agenda/`, extiende `base.html` (barra lateral agrupada por `ModuloGrupo`, cabecera con `eyebrow`/`titulo_pagina`/`acciones`, estilos en `static/css/agenda/micrositio.css`).
- Menú y contadores salen de `agenda/context_processors.py`.
- Referencia visual obligatoria: `docs/Micrositio de agendas demos de interfaz (1).html`. Pantalla nueva = calco de la maqueta; verla con render en Chrome headless.

## Autogestión vs. administración

«Mis turnos», «Mi agenda», «Mis aplicaciones» muestran solo lo del usuario, sin selector de otras personas. La vista de todo el equipo es otra pantalla o módulo (ej. `/agenda/turnos-equipo/`) para líderes y administradores.
