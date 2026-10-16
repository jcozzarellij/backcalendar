---
name: web-design-guidelines
description: Checklist de auditoría para cerrar una pantalla de este repo: accesibilidad, foco y teclado, responsive, formularios, estados y rendimiento, más las reglas duras del proyecto (Bootstrap 5, sin degradados, CSS externo con cache-busting, copy en español). Úsala al TERMINAR cualquier pantalla nueva o rediseñada, y sola para retoques menores.
---

# Auditoría de pantalla (backmanagercne)

Reconstruida el 2026-09-16 con las convenciones reales del repo. Pasa la lista entera antes de dar
una pantalla por terminada; anota en tu respuesta lo que corregiste.

## 1. Reglas duras del repo (si alguna falla, la pantalla está mal, no «opinable»)

- [ ] Bootstrap 5 y su grid (`row` + `col-*`) para toda estructura multicolumna. Nada de CSS Grid
      ni flexbox propio para el esqueleto.
- [ ] **Ningún degradado**, ni `backdrop-filter`, ni glass.
- [ ] Ningún `<style>` en el template. El CSS vive en `static/css/<app>/<archivo>.css`.
- [ ] `<link>` con ruta absoluta (`/static/...`) y `?vN.N` incrementado si el CSS cambió.
- [ ] `git add` del CSS si es nuevo.
- [ ] Sin comentarios en HTML, CSS ni JS.
- [ ] Todo el texto visible en español, voz activa, sin jerga de sistema.

## 2. Accesibilidad

- [ ] Un solo `h1`/encabezado de pantalla y jerarquía sin saltos.
- [ ] Contraste ≥ 4.5:1 en texto normal; el gris de apoyo `#5b6b7a` sobre blanco cumple, los grises
      más claros no sirven para texto.
- [ ] El color no es el único portador de significado: el estado lleva texto o icono además del color.
- [ ] Todo `<img>` con `alt` (vacío si es decorativa) y todo icono solo con `aria-hidden="true"`.
- [ ] Botones sin texto con `aria-label`.
- [ ] Inputs con `<label>` asociado (o `visually-hidden`), no solo `placeholder`.
- [ ] Regiones que cambian solas con `aria-live="polite"`.
- [ ] Modales con `aria-labelledby` y foco devuelto al disparador al cerrar.

## 3. Foco y teclado

- [ ] Foco visible y diseñado en todo lo interactivo; nunca `outline: none` a secas.
- [ ] Todo lo accionable es alcanzable con Tab y se activa con Enter/Espacio: si es acción, es
      `<button>`; si navega, es `<a>`.
- [ ] Orden de tabulación coherente con el orden visual.

## 4. Responsive

- [ ] A 400px no hay scroll horizontal; las columnas apilan.
- [ ] Tablas anchas dentro de `.table-responsive`.
- [ ] Nombres, URLs y correos largos no rompen la caja (`text-truncate` + `title`, o
      `overflow-wrap: anywhere`).
- [ ] Objetivos táctiles cómodos (≈40px); botones pegados separados con `gap`.

## 5. Formularios

- [ ] Errores junto al campo, en español y explicando cómo arreglarlo.
- [ ] El botón de envío se bloquea mientras procesa y vuelve si falla.
- [ ] Nada destructivo sin confirmación que nombre lo que se pierde.
- [ ] Los campos opcionales dicen que lo son.

## 6. Estados

- [ ] Vacío, cargando, con datos y error, los cuatro resueltos.
- [ ] El estado vacío enseña el flujo **vigente** y trae el botón del primer paso.
- [ ] «Sin resultados» de una búsqueda ofrece volver a la lista completa.
- [ ] Los mensajes de éxito dicen qué pasó y qué sigue.

## 7. Rendimiento y solidez

- [ ] Listados paginados o acotados; nada que dependa de que haya pocas filas.
- [ ] Imágenes con `width`/`height` y `loading="lazy"` cuando aplica.
- [ ] Sin consultas dentro del bucle del template (resolverlas en la view).

## 8. Pasada final

- [ ] Leé la pantalla como si fuera tu primera vez: ¿qué es, qué hago primero, qué pasa si me equivoco?
- [ ] ¿Qué sobra? Quitalo.
- [ ] Verificá con `pycheck` la parte Python y dejá que el developer levante el servidor.
