---
name: frontend-design
description: Método de diseño de interfaces para este repo (Django + Bootstrap 5, panel del Agente CNE). Úsala al crear o rediseñar cualquier pantalla, template o CSS de una feature: obliga a decidir un plan de tokens (color, tipografía, layout, firma) ANTES de escribir código y a hacer una autocrítica contra los defaults genéricos antes de dar la pantalla por terminada.
---

# Método de diseño (backmanagercne)

Reconstruida el 2026-09-16: el puntero original apuntaba a `.agents/skills/`, carpeta que no existe
en este repo. Este contenido es propio del proyecto y manda sobre cualquier estética importada.

## Regla cero

**Las reglas de `CLAUDE.md` ganan siempre.** En particular, en este repo: Bootstrap 5 con su grid
(nunca Tailwind ni CSS Grid para estructura), **nunca degradados** ni glassmorphism, CSS en
`static/css/<app>/` enlazado con ruta absoluta y cache-busting `?vN.N`, jamás `<style>` en el
template, sin comentarios en HTML/CSS/JS, copy en español.

## Paso 1 — Antes de escribir una línea, el plan de tokens

Escribe (en tu respuesta, no en el código) cuatro decisiones. Si no las puedes justificar, todavía
no entendiste la pantalla:

1. **Color.** Qué acento, qué superficies, qué color dice «activo», «pendiente» y «apagado».
   Paleta institucional CNE: `#1C3F86` (azul acento), `#16324f` (texto fuerte), `#5b6b7a` (apoyo),
   `#f4f6f8` / `#fbfcfd` (superficies), `#dfe5ea` (bordes), `#2e7d4f` (ok), `#c8a84b` (atención),
   `#ca3120` (destructivo). Un acento, no tres.
2. **Tipografía.** Qué tamaño y peso tiene el dato principal, y cómo se ven los metadatos
   (convención del repo: etiqueta `.7rem` en mayúsculas con `letter-spacing: .04em` y color de
   apoyo; cifras con `font-variant-numeric: tabular-nums`).
3. **Layout.** Qué ve el ojo primero, segundo y tercero. Cuántas columnas en `col-lg-*` y qué pasa
   al bajar a teléfono. Densidad: esta es una herramienta de trabajo, no una landing.
4. **Firma.** El detalle que hace reconocible la pantalla en una captura: un borde superior que
   cambia de color con el estado, una píldora con punto, una celda de dato. **Una sola.**

## Paso 2 — Jerarquía por decisión, no por inercia

Pregúntate qué hace el administrador en esta pantalla **hoy**, no lo que hacía cuando se escribió.
Lo que ya no se usa (un token que antes se copiaba a mano y ahora viaja solo) baja a un
`<details>`; lo que decide la acción sube. Una sola acción primaria por tarjeta o por fila; el
resto, secundarias o terciarias.

## Paso 3 — Los estados no son un adorno

Toda pantalla necesita sus cuatro estados resueltos: **vacío** (qué es esto y cuál es el primer
paso real, con el botón que lo dispara), **cargando**, **con datos** y **error**. El estado vacío
enseña el flujo vigente: si el flujo cambió, ese texto es lo primero que queda mintiendo.

## Paso 4 — Autocrítica antes de cerrar

Responde por escrito, sin piedad:

- ¿Esto se distingue de un Bootstrap por defecto, o son tarjetas grises con badges azules?
- ¿Hay algo que grite y no lo merezca (un bloque oscuro enorme para un dato secundario)?
- ¿Qué se puede **quitar** sin perder información? Quítalo.
- ¿Los números se leen de un vistazo o hay que buscarlos dentro de una frase?
- ¿El copy dice lo que el usuario hace («Vincular aula»), o lo que hace el sistema («Procesar»)?
- ¿Sobrevive a un nombre de aula larguísimo y a 40 filas?

## Paso 5 — Cerrar con la auditoría

Termina siempre pasando la pantalla por `web-design-guidelines` (accesibilidad, foco, responsive).
Para retoques menores (una columna, un badge) alcanza con esa auditoría sola.
