---
name: diseno-backcalendar
description: Identidad visual y patrones de interfaz del panel de backcalendar (Bootstrap 5.3 sobre el tema assets_riz): tokens reales, listados, filtros, tablas, modales, botones, badges, tarjetas de métricas y estados vacíos. Usar al crear o retocar cualquier template o CSS del panel o de las páginas públicas.
---

# Diseño backcalendar

Cómo se ve y se arma una pantalla de backcalendar. Las reglas de `CLAUDE.md`, `docs/agentes/templates.md` y `docs/agentes/diseno-frontend.md` mandan (Bootstrap 5 grid, **nunca degradados**, CSS en `static/css/<app>/` con `?v`, rutas absolutas `/static/...`, sin `<style>`, sin comentarios en HTML/CSS/JS, copy en español). Esta skill no inventa paleta: todo sale de los archivos citados. Para el método de diseño y la auditoría final siguen valiendo `frontend-design`, `high-end-visual-design` y `web-design-guidelines` (subordinadas a esto).

## Base del panel

- Tema: `static/assets_riz/css/bootstrap.min.css` (Bootstrap **5.3.3**) + `app.min.css` (layout `topbar` / `startbar` / `page-wrapper` / `container-xxl`). Fuente del tema: `"Be Vietnam Pro"` vía `--bs-font-sans-serif`; no cambiar `font-family`.
- Ajustes globales: `static/base_adicional.css` (tokens `--bs-*`, cards, botones, `.btn-mini`) y `static/base_tablas.css` (tablas).
- Íconos: Font Awesome 5 (`fa`, `fas`) y Line Awesome (`icons.min.css`).
- Interacción: `static/css/core/interaccion.css` (press `scale` en `.btn`, `.dropdown-item`, `.page-link`; skeleton `.io-esqueleto`; bloque de error `.io-fallo`; todo con `prefers-reduced-motion`).
- Sin sidebar: `body.sin-sidebar` en `static/css/core/sin_sidebar.css` (`data['ocultar_sidebar']`).

## Tokens del panel (`static/base_adicional.css`, `:root`)

| Token | Valor | Rol |
|---|---|---|
| `--bs-primary` | `#0d6efd` | acción principal, enlaces, info de navegación |
| `--bs-success` | `#16C784` | guardar, confirmar, estados completos |
| `--bs-warning` | `#F59E0B` | pendiente, atención |
| `--bs-danger` | `#EF4444` | error, eliminar, cancelar en modales |
| `--bs-info` | `#06B6D4` | dato informativo secundario |
| `--bs-secondary` | `#64748B` | texto secundario, labels |
| `--bs-body-bg` | `#F6F7FB` | fondo de página |
| `--bs-border-radius` / `-sm` / `-lg` | `.85rem` / `.55rem` / `1.1rem` | radios |
| `--bs-box-shadow-sm` / `--bs-box-shadow` | sombras azuladas `rgba(5, 44, 101, …)` | card en reposo / hover |

Cada color tiene su `*-bg-subtle` y `*-border-subtle`: usarlos para pills, contenedores de ícono y alertas suaves en vez de inventar tintes. En CSS propio referenciar `var(--bs-…)`, no hex sueltos.

Tablas (`base_tablas.css`): `th` con fondo `rgb(243,243,243)`, bordes `#e4e7ea`, hover `#f2f4f5`, fila enfocada `.tableRowFocus`.

### Páginas públicas (`static/css/public/auth.css`, `publico.css`)

Paleta institucional propia: `--app-azul #1C3F86`, `--app-rojo #D3112A`, `--app-amarillo #FFD100`, `--app-tinta #16324f`, `--app-texto #3d4c5c`, `--app-muted #5b6b7a`, `--app-fondo #f4f7fa`, `--app-borde #DCE4F3`; tipografía `--au-font-display` (Poppins) y `--au-font-body` (Segoe UI). Solo para `templates/public/`; no mezclarla con el panel.

### Legado que no se copia

`base_adicional.css` tiene degradados en `.btn-primary`, `.btn-success` y el ítem activo del `startbar`, y `static/css/autenticacion/listado_cards.css` en `.membresia-pill`; `crons.css` usa franja de color a la izquierda (`border-left-width: 4px`). Son previos a la regla: no tocarlos sin pedido y **no replicarlos** en CSS nuevo. Un fondo plano con `*-bg-subtle` resuelve lo mismo.

## Listado estándar

Referencia: `templates/area_geografica/pais/listado.html`. Orden vertical:

1. **Filtros** en `card mb-3` > `card-body` > `<form method="GET" class="mb-0">` con `row g-3`: búsqueda `input-group` (`input-group-text` con `fa-search`) en `col-md-4`, columna «Acciones» con botón buscar `btn btn-primary` y limpiar `btn btn-default` (solo si hay `url_vars`).
2. **Barra de acciones**: `row align-items-center mb-3` con el botón «Nuevo …» `btn btn-success btn-sm` + `fa-plus-circle me-2`.
3. **Tabla** en `card` > `card-body` > `table-responsive` > `table#tabla.table.table-hover.table-striped`, encabezados centrados en español, `{% include "paginacion.html" %}` al final. `#tabla` lo inicializa `base.html` como DataTable sin paginación ni búsqueda (la paginación es la del servidor).
4. **Acciones por fila**: `dropdown` con botón `btn btn-icon` + `fa-ellipsis-v` y `dropdown-menu dropdown-menu-end`; ítems con ícono de color (`text-primary` editar, `text-danger` eliminar). El `style="background:none;border:none"` inline que tiene `pais` va a una clase en el CSS de la app.
5. **Estado vacío**: `{% empty %}` con una fila `text-center text-muted` que diga qué falta y, si aplica, cómo crearlo («Todavía no hay países. Creá el primero con Nuevo país.»).

## Modales y formularios

- Shell: `modal-dialog modal-dialog-centered` + `modal-lg` (formularios) / `modal-xl` (tablas); `modal-title` en `h5`; cierre `btn-close` con `data-bs-dismiss="modal"` y `aria-label="Cerrar"`.
- Fragmento: `row g-2`, cada campo en `col-lg-{{ col }}` > `mb-2`, `label.form-label.small.mb-1`, `.invalid-feedback#errorMessage<campo>`; separador `border-top my-3`; pie `d-flex justify-content-end` con **Cancelar `btn btn-danger btn-sm me-1`** (`fa-window-close`) y **Guardar `btn btn-success btn-sm`** (`fa-save`). Detalle técnico en la skill `formmodal`.
- Selects: `select2` (lo pone `ModelFormBase`); booleanos: switchery (`js-switch`); archivos: dropify.

## Botones

- Sólidos de Bootstrap (`btn-primary`, `btn-success`, `btn-danger`, `btn-default` para neutro). **Regla obligatoria: nunca `btn-outline-*`**, ni en pantallas nuevas ni al retocar las existentes; tampoco recrearlo con CSS propio (fondo transparente + borde de color).
- Tamaño en listados y modales: `btn-sm`. Compacto en celdas o barras densas: `.btn-mini`.
- Ícono + texto con `me-1`/`me-2`. Botón solo-ícono lleva `aria-label` o `title`.

## Badges y estados

- Pills de BS5: `badge bg-success|bg-warning|bg-danger|bg-secondary|bg-primary` (ver `templates/seguridad/databasebackup/listado.html`) o, para algo más suave, `badge rounded-pill` con `bg-*-subtle text-*-emphasis border border-*-subtle`.
- Semántica fija: verde = hecho/activo, ámbar = pendiente, rojo = error/vencido, azul = informativo, gris = inactivo. Booleanos del modelo ya traen `<campo>_boolhtml` y `<campo>_yesorno` (`NormalModel` en `core/custom_models.py`).

## Métricas (KPIs) arriba de un listado

`row g-3 mb-3` con `col-6 col-md-3` por tarjeta. Cada una: `card` estándar (sin relleno de color), número grande con `font-variant-numeric: tabular-nums` y peso 700, debajo la descripción en `--bs-secondary` pequeña y en mayúsculas, y a la derecha un contenedor de ícono con `*-bg-subtle` y el ícono en el color fuerte. El color semántico va solo en el ícono, nunca en toda la tarjeta ni como franja lateral.

## Carga y error

- Operación corta: `pantallaespera()` / `$.unblockUI()`.
- Contenido que tarda en un modal o panel: `.io-esqueleto` con 3-5 `<span>`; si falla, `.io-fallo` con título, causa en una línea y botón de reintentar.
- Mensajes: toasts (`alertaSuccess/Warning/Danger`) para confirmaciones; `mensaje*` para lo que exige lectura.

## Archivo CSS de una pantalla

`static/css/<app>/<pantalla>.css`, enlazado en `{% block head %}` con `<link rel="stylesheet" href="/static/css/<app>/<pantalla>.css?v1.0">`; subir `?v` en cada edición; `git add` al crearlo. Clases con prefijo de la pantalla (`.reserva-…`) para no chocar con `app.min.css`. Responsive con las utilidades y breakpoints de BS5; nada de CSS Grid ni flex propio para la estructura de columnas (eso es `row`/`col-*`).

## Evitar

- Degradados de cualquier tipo, glassmorphism, sombras pesadas.
- Paleta nueva o hex fuera de los tokens.
- Franjas de color a la izquierda de tarjetas.
- `{% static %}`, `<style>`, comentarios, `style=""` estructural.
- `data-toggle`/`data-dismiss` de Bootstrap 4: en BS5 son `data-bs-*`.
- Texto en inglés o descripciones largas en la UI.
