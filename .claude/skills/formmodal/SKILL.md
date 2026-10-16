---
name: formmodal
description: Usar al crear o modificar cualquier formulario en modal (formModal), envío AJAX con forms.js, campos Select2/switchery/dropify, borrado con eliminarajax o validación de formularios en backcalendar.
---

# formModal (backcalendar)

Cómo se cargan, envían y validan los formularios en modal. Bootstrap 5 (`data-bs-*`, `btn-close`, `new bootstrap.Modal`). Referencias reales: `templates/area_geografica/pais/listado.html` + `form.html`, `templates/autenticacion/usuario/formmodal.html`.

## Bloques de `templates/base.html`

| Bloque | Uso |
|---|---|
| `{% block head %}` | solo `<link>` de CSS de la pantalla |
| `{% block content %}` | markup, sin `<script>` |
| `{% block jscript %}` | JS de la pantalla (jQuery, Select2, DataTables y SweetAlert2 ya cargados) |
| `{% block atras %}` | URL del botón Atrás, si no sirve la por defecto |

No existe `extra_jscript`. `base.html` **no** carga `forms.js`: lo carga cada listado (o el `{{ form.media }}` de un `ModelFormBase`).

## Flujo

`listado.html` tiene el shell `#modalDetalle` con un `<form method="post">` vacío → `formModal(pk, titulo, action)` hace GET a `{{ request.path }}?action=...&pk=...` → la vista devuelve `{'result': True, 'data': html}` → el JS inyecta el HTML en `.detalleProdModal` y abre el modal → el submit lo captura `forms.js`.

### listado.html

```django
<a href="javascript:void(0)" onclick="formModal(0, 'Nuevo país', 'add')" class="btn btn-success btn-sm">
    <i class="fas fa-plus-circle me-2"></i>Nuevo país
</a>

<a class="dropdown-item" href="javascript:void(0)" onclick="formModal({{ l.pk }}, 'Editar país', 'change')">
    <i class="fas fa-edit me-2 text-primary"></i>Editar
</a>
<a class="dropdown-item" href="javascript:void(0)" onclick="eliminarajax({{ l.pk }}, '{{ l.nombre }}', 'delete')">
    <i class="fas fa-trash me-2 text-danger"></i>Eliminar
</a>

<div class="modal fade" id="modalDetalle" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg">
        <div class="modal-content">
            <form method="post" action="{{ ruta }}" enctype="multipart/form-data">
                {% csrf_token %}
                <div class="modal-header">
                    <h5 class="modal-title" id="modalNombre"></h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
                </div>
                <div class="modal-body detalleProdModal"></div>
            </form>
        </div>
    </div>
</div>
```

```django
{% block jscript %}
    <script src="/static/js/forms.js?v=12"></script>
    <script>
        function formModal(id, text, action) {
            pantallaespera();
            $.ajax({
                type: "GET",
                url: `{{ request.path }}`,
                data: {'action': action, 'pk': id},
                success: function (data) {
                    setTimeout($.unblockUI, 1);
                    if (data.result === true) {
                        $('#modalNombre').html(text);
                        $('.detalleProdModal').html(data.data);
                        bootstrap.Modal.getOrCreateInstance(document.getElementById('modalDetalle')).show();
                    } else {
                        mensajeWarning(data.message);
                    }
                },
                error: function () {
                    setTimeout($.unblockUI, 1);
                    mensajeWarning("Error de conexión.");
                },
                dataType: "json"
            });
        }
    </script>
{% endblock %}
```

- Usar `getOrCreateInstance`: `new bootstrap.Modal(...)` en cada apertura apila instancias.
- Borrado: `eliminarajax(pk, nombre, accion)` ya es global en `base.html` (confirma con SweetAlert2, postea `{action, id}` con CSRF por `$.ajaxSetup`, recarga si `error === false`). No redefinirlo salvo que necesites `dict_url_vars`.
- Modal genérico ya presente en `base.html`: `#modalPostAjax` + `verModalPostAjax(action, pk, icono, 'modal-xl')`; espera `{result, data, titulo}` y opcional `execJs`. `verModalPost`/`verModalGet` apuntan a variables que no existen: no usarlos.

### form.html (fragmento)

```django
<div class="row g-2">
    <input type="hidden" name="action" value="{{ action }}">
    <input type="hidden" name="pk" value="{{ pk|default:0 }}">
    {% for field in form %}
        {% if field.is_hidden %}
            {{ field }}
        {% else %}
            <div class="col-lg-{{ field.field.widget.attrs.col }}">
                <div class="mb-2">
                    <label class="form-label small mb-1" for="id_{{ field.name }}">{{ field.label }}</label>
                    {{ field }}
                    <div class="invalid-feedback" id="errorMessage{{ field.name }}"></div>
                </div>
            </div>
        {% endif %}
    {% endfor %}
</div>

<div class="border-top my-3"></div>

<div class="d-flex justify-content-end">
    <button type="button" class="btn btn-danger btn-sm me-1" data-bs-dismiss="modal">
        <i class="fa fa-window-close me-1"></i>Cancelar
    </button>
    <button type="submit" id="submit" class="btn btn-success btn-sm">
        <i class="fa fa-save me-1"></i>Guardar
    </button>
</div>

{{ form.media }}

{% include 'base_formulario_modal.html' %}
```

`base_formulario_modal.html` reinicializa `.select2` con `dropdownParent` del modal y `dropify` en `shown.bs.modal`. Sin ese include, inicializar a mano (`$('.detalleProdModal .select2').select2({width: '100%', dropdownParent: $('#modalDetalle')})`, como en `pais/listado.html`).

## forms.js (`static/js/forms.js`)

Se engancha a todo `<form>` POST presente al cargar la página: arma `FormData` (soporta archivos), bloquea con `pantallaespera()`, deshabilita los botones submit visibles con spinner, postea a la URL actual y procesa la respuesta. Un guard (`meta[name=formsJsValidator]`) evita doble binding si se carga dos veces.

Excluidos (manejarlos a mano): `#frmEliminar`, `#excluirFormAjax`, otros ids listados en el selector del archivo, y todo `[method=GET]`.

Extras: si existe el array global `lista_items1` se envía como JSON (`json.loads(request.POST.get('lista_items1', '[]'))`); inputs con `data-datoseguro="true"` se cifran con RSA (`doRSA`) antes de enviar.

### Respuesta (array; un dict suelto también se acepta)

| Éxito (`error: false`) | Efecto |
|---|---|
| `reload: true` | recarga |
| `to: '/url/'` | redirige |
| `function_js: '...'` | `eval` |

No existen `msg_reload`/`msg_to`. Para avisar y recargar: `messages.success(request, '...')` + `reload: True`; `base.html` muestra el toast al recargar.

| Error (`error: true`) | Efecto |
|---|---|
| `form: [{campo: msg}]` | `is-invalid` en `#id_<campo>`, texto en `#errorMessage<campo>`, activa la pestaña (`data-bs-target`) del primer inválido, scroll y alerta con su mensaje |
| `input_id` + `div_id` + `message` | marca un solo campo |
| solo `message` | `Swal.fire(message, '', 'error')` |

Hooks opcionales en la página: `funcionAntesDeGuardar()`, `funcionDespuesDeGuardar()`, `funcionSiFallaElPost(jqXHR, textStatus, errorThrown, formData, url)`.

## Clase del formulario

`ModelFormBase` (`core/custom_models.py`) ya asigna `class` (`select2`, `form-control`, `js-switch`), `col=12`, asterisco de requerido y `accept` de archivos. Solo ajustar `widget.attrs['col']` y lo puntual; nunca pisar `class` en un loop. Detalle de kwargs (`querysets`, `no_requeridos`, `no_select2`, `ver`...) en la skill `django-backend`.

Dropdown dependiente: queryset vacío en el form (`Modelo.objects.none()`) y asignarlo en la vista, tanto en GET como en POST, antes de `is_valid()`.

## Helpers globales de `base.html`

- `pantallaespera(titulo, mensaje)` / `$.unblockUI()`.
- Toasts arriba a la derecha: `alertaSuccess`, `alertaWarning`, `alertaDanger(msg, timer)`.
- Modales: `mensajeSuccess`, `mensajeWarning`, `mensajeDanger`.
- `getPromise(url, params)` / `postPromise(url, params)`; `tooltips()` para `.tl/.tr/.tu/.tb`.
- CSRF: `$.ajaxSetup` agrega `X-CSRFToken` a todo `$.ajax` relativo.

## SweetAlert2 es legado (8.18.6)

`Swal.fire({...})` con `type:` (no `icon:`) y `result.value` (no `result.isConfirmed`). Sintaxis completa en [references/sweetalert-legacy.md](references/sweetalert-legacy.md).
