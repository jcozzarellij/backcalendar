---
name: design-guidelines-panel
description: "Patrones de interfaz del panel de backcalendar (Bootstrap 5.3, tema assets_riz): listados, filtros, tablas, modales, botones, badges, KPIs, carga y estados vacíos. Usar al crear o retocar cualquier template o CSS bajo `templates/<app>/` o `static/css/<app>/` del panel, y para decidir la apariencia de una pantalla interna."
---

# Panel de Turno

Cómo se arma una pantalla del panel. Tokens, colores, sombras y tipografía: `DESIGN-panel.md` y `static/base_adicional.css`; esta skill no los repite ni inventa paleta. Landing público y páginas que extienden `base_landing.html`: skill `design-guidelines-landing`.

`CLAUDE.md` y `docs/agentes/templates.md` mandan (grid de Bootstrap 5, CSS en `static/css/<app>/` con `?v`, rutas absolutas `/static/...`, sin `<style>`, sin comentarios). Para pantalla nueva, el método está en `docs/agentes/diseno-frontend.md`.

## Base

- Interacción: `static/css/core/interaccion.css` (press `scale` en `.btn`, `.dropdown-item`, `.page-link`; skeleton `.io-esqueleto`; bloque de error `.io-fallo`; todo con `prefers-reduced-motion`).
- Sin sidebar: `body.sin-sidebar` en `static/css/core/sin_sidebar.css` (`data['ocultar_sidebar']`).

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

- Degradados, glassmorphism y sombras fuera de las tres de `DESIGN-panel.md`.
- Hex fuera de los tokens.
- Franjas de color a la izquierda de tarjetas (`static/css/seguridad/crons.css` tiene una previa: no replicarla ni tocarla sin pedido).
- `{% static %}`, `<style>`, comentarios, `style=""` estructural.
- `data-toggle`/`data-dismiss` de Bootstrap 4: en BS5 son `data-bs-*`.
- Texto en inglés o descripciones largas en la UI.
