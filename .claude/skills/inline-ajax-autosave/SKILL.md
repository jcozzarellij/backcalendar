---
name: inline-ajax-autosave
description: Usar al guardar un único campo al salir del input (blur/change) vía AJAX, en una fila de tabla o un modal donde el registro ya existe (orden, descripción, un número o fecha) en backcalendar.
---

# Autoguardado inline por AJAX

Persistir un campo de un registro existente en cuanto el usuario sale del input, sin enviar formulario. Para un formulario completo, usar la skill `formmodal`.

Referencia real: `templates/seguridad/modulossistema/listado.html` (`.orden-input`, acción `act_orden`) + `seguridad/view_modulos_sistema.py` (`act_orden`, `act_icono`).

No usar x-editable: el paquete en `static/assets/plugins/x-editable-bs4/` es para Bootstrap 4 y ninguna pantalla lo usa.

## Markup

Cada input lleva el id del registro y el valor guardado, para saltar el request si no cambió. Un span hermano muestra el estado.

```django
<input type="number" class="form-control orden-input" min="0"
       data-id="{{ l.pk }}" data-original="{{ l.orden }}" value="{{ l.orden }}"
       aria-label="Orden de {{ l.nombre }}">
<span class="autosave-estado" id="estado-{{ l.pk }}" aria-live="polite"></span>
```

## JavaScript

Delegado en `$(document)` para sobrevivir a redibujados de DataTables y modales. Usar `change` para selects/números y `blur` para textos.

```javascript
$(document).on('change', '.orden-input', function () {
    var $el = $(this);
    var pk = $el.data('id');
    var original = String($el.data('original'));
    var actual = $el.val();
    if (actual === original) return;
    if (actual === '' || isNaN(parseInt(actual))) { $el.val(original); return; }
    var $estado = $('#estado-' + pk);
    $estado.html('<i class="fa fa-spinner fa-spin text-muted"></i>');
    $.post('{{ ruta }}', {action: 'act_orden', id: pk, valor: actual}, function (data) {
        if (data.result === true) {
            $el.data('original', String(data.orden));
            $estado.html('<i class="fa fa-check text-success"></i>');
            setTimeout(function () { $estado.html(''); }, 2000);
        } else {
            $el.val(original);
            $estado.html('<i class="fa fa-times text-danger"></i>');
            alertaWarning(data.mensaje || 'No se pudo guardar');
        }
    }, 'json').fail(function () {
        $el.val(original);
        $estado.html('<i class="fa fa-times text-danger"></i>');
        alertaDanger('Error de conexión.', 3000);
    });
});
```

El CSRF lo agrega `$.ajaxSetup` de `base.html` (header `X-CSRFToken`); no hace falta mandarlo en el body. Actualizar `data-original` en el éxito evita reenvíos del mismo valor. Usar `.data()` de forma consistente (lectura y escritura): mezclar `.attr('va')` con `.attr('vl')` es justo el bug que tiene `act_descrip` en ese listado.

## Backend

Rama dentro del `with transaction.atomic()` del POST, con su propio `try/except` y `return` temprano de un dict plano (no el array de `forms.js`):

```python
elif action == 'act_orden':
    try:
        filtro = model.objects.get(pk=int(request.POST['id']), status=True)
        filtro.orden = int(request.POST['valor'])
        filtro.save(request)
        log(f"Actualizó el orden de {filtro}", request, "change", obj=filtro.id)
        return HttpResponse(json.dumps({'result': True, 'orden': filtro.orden}))
    except (ValueError, TypeError):
        return HttpResponse(json.dumps({'result': False, 'mensaje': 'Orden inválido'}))
    except Exception as ex:
        return HttpResponse(json.dumps({'result': False, 'mensaje': 'No se pudo guardar el orden.'}))
```

`JsonResponse({...})` sirve igual. Validar el valor en el servidor (tipo, rango, longitud): el input del cliente no es garantía.

## Variantes

- **Varios campos por fila**: mandar `campo` + `valor` y validar `campo` contra una lista blanca en la vista; nunca `setattr` con un nombre libre del cliente.
- **Por tecla (debounce)**: evento `input` con `setTimeout` de ~800 ms, manteniendo la guarda `actual === original`.
- **Recargar tras guardar** (como hace `act_orden` real, porque reordena la lista): solo si el cambio altera el orden o los totales visibles.

## Trampas

- Binding directo (`$('.x').blur(...)`) en vez de delegado: deja de guardar tras paginar.
- `data-original` sin actualizar: cada blur vuelve a guardar.
- Guardar campos que requieren validación cruzada con otros: eso es un formulario, no autoguardado.
- Sin feedback visible: el usuario no sabe si guardó. Siempre spinner → check / cruz.
