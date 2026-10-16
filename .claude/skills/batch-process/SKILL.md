---
name: batch-process
description: Usar cuando una acción masiva debe procesar registros uno por uno con barra de progreso en backcalendar (sincronizar N eventos, reenviar N invitaciones, recalcular N registros): GET que lista los ids, un POST por ítem y un modal de progreso.
---

# Proceso por lotes con barra de progreso

El cliente maneja el lote **ítem por ítem**: cada ítem es un request independiente y reintentable, y el usuario ve progreso real en vez de un request largo que bloquea (y que en WSGI puede cortar el timeout). No es el flujo de `formModal`: tiene su propio contrato JSON.

Úsalo cuando cada ítem es costoso (llamada a una API externa, correo, render). Si son pocos y baratos, un solo POST con `formmodal-data-preview` alcanza.

## Contrato

Los endpoints por ítem responden un objeto plano `{status: bool, message|data}`, **distinto** del array `[{error: ...}]` de `forms.js`. El cliente lee `response.status`.

## 1. GET: listar los ítems

Valida precondiciones y devuelve los ids respetando los filtros actuales del listado (mismo armado de filtros; si se repite, a `<app>/funciones_<tema>.py`).

```python
elif action == 'listar_pendientes':
    try:
        filtros = Q(status=True, sincronizado=False)
        criterio = request.GET.get('criterio', '').strip()
        if criterio:
            filtros &= Q(nombre__icontains=criterio)
        items = [{'id': r.pk, 'nombre': str(r)} for r in Reserva.objects.filter(filtros).order_by('pk')]
        return JsonResponse({'status': True, 'data': items})
    except Exception as ex:
        return JsonResponse({'status': False, 'message': 'No se pudo obtener la lista.'})
```

## 2. POST: procesar UN ítem

La rama vive **dentro** del `try` + `with transaction.atomic()` común, pero con su propio `try/except` y `return` temprano, igual que `act_orden` en `seguridad/view_modulos_sistema.py`. El `return` sale del `with` y confirma; un error interno no llega al manejador global de `forms.js`. Como `ATOMIC_REQUESTS` está en `False`, cada POST es su propia transacción: un ítem fallido no revierte los anteriores.

```python
elif action == 'procesar_item':
    try:
        r = Reserva.objects.select_for_update().get(pk=int(request.POST['pk']), status=True)
        if r.sincronizado:
            return JsonResponse({'status': True, 'message': f'{r} ya estaba sincronizada.'})
        r.sincronizado = True
        r.save(request)
        log(f"Sincronizó la reserva {r}", request, "change", obj=r.pk)
        return JsonResponse({'status': True, 'message': f'{r} sincronizada.'})
    except Exception as ex:
        salva_logs(request, __file__, request.method, action, type(ex).__name__,
                   'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
        return JsonResponse({'status': False, 'message': 'No se pudo procesar el registro.'})
```

Cada ítem debe ser **idempotente**: si el usuario reintenta, el ya procesado se salta sin duplicar efectos.

## 3. Modal de progreso

```django
<div class="modal fade" id="modalProgreso" tabindex="-1" aria-hidden="true" data-bs-backdrop="static" data-bs-keyboard="false">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-body">
                <h5 class="mb-3"><i class="fa fa-cog me-1"></i><span id="progresoTitulo"></span></h5>
                <div class="progress" role="progressbar" aria-label="Progreso" aria-valuemin="0" aria-valuemax="100">
                    <div id="progresoBarra" class="progress-bar progress-bar-striped progress-bar-animated"></div>
                </div>
                <p class="mt-3 mb-1 fw-semibold" id="progresoMensaje">Cargando...</p>
                <p class="text-warning small mb-0"><i class="fa fa-info-circle me-1"></i>No cierres esta ventana.</p>
            </div>
        </div>
    </div>
</div>
```

## 4. Cliente: listar y recorrer

```javascript
function filtrosActuales() {
    return {criterio: $('input[name="criterio"]').val() || ''};
}

function iniciarProceso() {
    Swal.fire({
        title: '¿Sincronizar las reservas filtradas?', type: 'question',
        showCancelButton: true, allowOutsideClick: false,
        confirmButtonText: 'Sí, sincronizar', cancelButtonText: 'Cancelar'
    }).then(function (r) { if (r.value) { correrProceso(); } });
}

async function correrProceso() {
    var modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('modalProgreso'));
    var $barra = $('#progresoBarra');
    $('#progresoTitulo').text('Sincronizando');
    $('#progresoMensaje').text('Cargando registros...');
    $barra.css('width', '0%');
    modal.show();
    try {
        var resp = await $.ajax({type: 'GET', url: '{{ request.path }}', dataType: 'json',
            data: Object.assign({action: 'listar_pendientes'}, filtrosActuales())});
        if (!resp.status) { modal.hide(); mensajeWarning(resp.message); return; }
        var items = resp.data, total = items.length, fallidos = 0;
        if (total === 0) { modal.hide(); mensajeWarning('No hay registros pendientes.'); return; }
        for (var i = 0; i < total; i++) {
            $('#progresoMensaje').text('Procesando ' + (i + 1) + '/' + total + ': ' + items[i].nombre);
            $barra.css('width', Math.floor((i / total) * 100) + '%');
            var res = await $.ajax({type: 'POST', url: '{{ request.path }}', dataType: 'json',
                data: {action: 'procesar_item', pk: items[i].id}});
            if (!res.status) { fallidos++; }
        }
        $barra.css('width', '100%');
        $('#progresoMensaje').text(fallidos ? 'Terminado con ' + fallidos + ' error(es).' : 'Proceso completado.');
        setTimeout(function () { modal.hide(); location.reload(); }, 1000);
    } catch (error) {
        modal.hide();
        mensajeWarning('Se cortó la conexión. Lo ya procesado quedó guardado; podés reintentar.');
    }
}
```

El CSRF lo agrega `$.ajaxSetup` de `base.html`. Decidir con el usuario si un ítem fallido corta el lote (`throw`) o se cuenta y se sigue (el ejemplo cuenta y sigue).

## Trampas

- Mezclar contratos: por ítem va `{status, message}`, nunca el array `[{error}]`.
- Ignorar los filtros: listar, procesar y cualquier acción complementaria deben usar el mismo armado de filtros que el listado.
- Ítems no idempotentes: un reintento duplica correos o eventos.
- Sin precondición: validar en el GET y otra vez por ítem, con mensaje claro en español.
- Barra sin accesibilidad: el contenedor lleva `role="progressbar"` y `aria-label`.
- Lotes enormes en una sola pestaña: si el lote supera lo razonable para un usuario esperando, es tarea de cron (`seguridad/funciones_cron.py`), no de esta skill.
