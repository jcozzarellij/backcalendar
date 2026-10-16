---
name: formmodal-data-preview
description: Usar cuando un modal debe mostrar una vista previa de filas (dataset) antes de ejecutar una acción masiva o costosa (enviar N correos, generar N recordatorios, cerrar N registros) en backcalendar.
---

# Modal con vista previa de datos

Un modal que lista exactamente las filas sobre las que se va a actuar, con un botón de confirmar al pie. Se monta sobre el flujo de la skill `formmodal` (shell + `forms.js`); acá solo va la capa de vista previa y confirmación. Referencia real del patrón: la extracción de URLs en `seguridad/view_modulos_sistema.py` (`_urls_pendientes_por_grupo` alimenta la vista previa y vuelve a validar en el POST `extraer_urls`; solo se crean las seleccionadas que siguen pendientes).

## Abrir el modal

Opción A, el shell propio del listado (`#modalDetalle`) con el tamaño elegido en el markup. Opción B, el modal genérico de `base.html`:

```javascript
verModalPostAjax('preview_recordatorios', 0, 'fa fa-envelope', 'modal-xl');
```

`verModalPostAjax` manda `pk` y `dict_url_vars`, espera `{result, data, titulo}` e inyecta `data` dentro de un `<form method="POST">` que ya tiene `{% csrf_token %}`; el submit lo procesa `forms.js` si el listado lo cargó.

Tamaño según contenido: `modal-lg` (1-3 campos), `modal-xl` (tabla chica), `modal-fullscreen` (tabla ancha).

## GET: armar la vista previa

Las filas salen del **mismo** armado de filtros que el listado; los filtros viajan como `url_vars` para que el POST ejecute sobre el mismo conjunto.

```python
elif action == 'preview_recordatorios':
    try:
        filtros, url_vars = Q(status=True, estado=1), ''
        criterio = request.GET.get('criterio', '').strip()
        if criterio:
            filtros &= Q(nombre__icontains=criterio)
            url_vars += '&criterio=' + criterio
        data['filas'] = filas = list(Reserva.objects.filter(filtros).select_related('ciudad')[:500])
        data['list_count'] = len(filas)
        data['url_vars'] = url_vars
        template = get_template('<app>/<recurso>/modal_preview.html')
        return JsonResponse({'result': True, 'data': template.render(data), 'titulo': 'Enviar recordatorios'})
    except Exception as ex:
        return JsonResponse({'result': False, 'message': 'No se pudo armar la vista previa.'})
```

Si el armado de filtros se repite entre listado, vista previa y POST, va a `<app>/funciones_<tema>.py`, no a un `def` dentro del `view_*.py`.

## Plantilla del modal

```django
<div class="row g-2">
    <div class="col-12">
        <div class="alert alert-info mb-2">
            <i class="fa fa-info-circle me-1"></i>Se enviará un recordatorio a cada reserva de la lista.
        </div>
    </div>
    <div class="col-12 mb-2">
        <span class="badge bg-primary">Total: {{ list_count }}</span>
    </div>
    <div class="col-12">
        <div class="table-responsive">
            <table id="tablaPreview" class="table table-hover table-striped">
                <thead><tr><th>Nombre</th><th>Ciudad</th></tr></thead>
                <tbody>
                {% for f in filas %}
                    <tr><td>{{ f.nombre }}</td><td>{{ f.ciudad }}</td></tr>
                {% empty %}
                    <tr><td colspan="2" class="text-center text-muted">No hay reservas que cumplan el filtro.</td></tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<input type="hidden" name="action" value="enviar_recordatorios">
<input type="hidden" name="url_vars" value="{{ url_vars }}">

<div class="border-top my-3"></div>
<div class="d-flex justify-content-end">
    <button type="button" class="btn btn-danger btn-sm me-1" data-bs-dismiss="modal">
        <i class="fa fa-window-close me-1"></i>Cancelar
    </button>
    <button type="submit" class="btn btn-success btn-sm" {% if not list_count %}disabled{% endif %}>
        <i class="fa fa-paper-plane me-1"></i>Confirmar envío
    </button>
</div>

<script>
    (function () {
        if ($.fn.DataTable.isDataTable('#tablaPreview')) {
            $('#tablaPreview').DataTable().destroy();
        }
        $('#tablaPreview').DataTable({
            ordering: true, searching: true, bInfo: true, pageLength: 15,
            language: {url: '/static/js/i18n/Spanish.json'}
        });
    })();
</script>
```

DataTables ya está cargado globalmente (`templates/datatable.html` incluido en `base.html`). No usar el id `tabla`: `base.html` lo auto-inicializa sin paginación. Para elegir filas, checkboxes con `name="c_ids"` y en el POST `request.POST.getlist('c_ids')`, como `c_urls` en módulos.

## POST: ejecutar

```python
elif action == 'enviar_recordatorios':
    params = QueryDict(request.POST.get('url_vars', '').lstrip('&'))
    filtros = Q(status=True, estado=1)
    if params.get('criterio'):
        filtros &= Q(nombre__icontains=params['criterio'])
    enviados = 0
    for r in Reserva.objects.filter(filtros).select_related('ciudad'):
        despachar(armar('Recordatorio de reserva', render_to_string('email/recordatorio.html', {'r': r}), to=[r.email]))
        enviados += 1
    log(f"Envió {enviados} recordatorios", request, "change")
    messages.success(request, f"Se enviaron {enviados} recordatorio(s).")
    res_json.append({'error': False, 'reload': True})
```

Nunca ejecutar sobre ids que vengan del cliente sin volver a validarlos contra el filtro del servidor.

## Trampas

- `action` oculto distinto de la rama POST (no es la acción GET que abrió el modal).
- Filtros que divergen entre vista previa y POST: siempre `url_vars` en ambos.
- No destruir la DataTable antes de reinicializar: "Cannot reinitialize" en la segunda apertura.
- Datasets grandes: acotar en la vista previa y avisar el total; si cada fila es costosa, usar la skill `batch-process`.
- Cancelar sin `data-bs-dismiss="modal"` no cierra el modal.
