# Templates, CSS y JS

Stack: Bootstrap 5 (`data-bs-*`), jQuery, DataTables, SweetAlert2 (sintaxis legacy). Skills de patrón: `formmodal`, `formmodal-data-preview`, `inline-ajax-autosave`, `batch-process`.

## Estructura

- `templates/base.html`: layout autenticado. `templates/public/base.html`: login, legales, páginas públicas.
- `templates/<app>/` — `*_listado.html` (DataTables), `*_form.html` (modal o página completa), `*_detalle.html` (solo lectura).

## Assets

- Rutas absolutas: `/static/...`, `/media/...`. `{% load %}` de otras librerías (ej. `templatefunctions`) sigue permitido; `{% static %}` no.
- Estilos en `static/css/<app>/<archivo>.css`, nombrado por template o feature, enlazado con `?v1.0`. Al modificar un `.css` existente, subir el `?v` del `<link>` (revisar la versión actual antes).
- Archivo CSS nuevo: `git add static/css/<app>/<archivo>.css` al crearlo.
- Sin comentarios en HTML, plantillas Django, CSS ni JS (`<!-- -->`, `{# #}`, `/* */`, `//`).

```html
<link rel="stylesheet" href="/static/css/seguridad/crons.css?v1.2">
```

## Componentes

- Selects: clase `select2` en todo `<select>` de formulario o filtro (`ModelFormBase` ya la pone en FK y choices; en filtros GET escribirla). `base.html` los inicializa.
- Botones: sólidos (`btn-primary`, `-success`, `-danger`, `-warning`, `-info`, `-secondary`, `-light`, `-default`), también en JS que arma HTML y en CSS. Los `btn-outline-*` están prohibidos.
- Layout multicolumna: grid de Bootstrap 5 (`row` + `col-*`); CSS Grid o flex propio solo si se pide.

## Copy

Todo texto visible en español: títulos, alertas, SweetAlert, botones, encabezados, `messages.*`, tooltips, badges, `JsonResponse({'message': ...})`. Descripciones de pantallas y directorio: una frase corta. Términos técnicos universales (push, URL, endpoint, API) quedan como están.
