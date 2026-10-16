# SweetAlert2 legado (backcalendar)

`base.html` carga `/static/sweetalert2/sweetalert2.js` versión **8.18.6**. Su API difiere de la documentación actual: copiar ejemplos modernos falla en silencio.

| Concepto | Usar | No usar |
|---|---|---|
| Ícono | `type: 'success'` | `icon: 'success'` |
| Confirmación | `result.value` | `result.isConfirmed` |
| Entrada | `Swal.fire({...})` | `swal({...})` (no está definido) |

Tipos: `success`, `error`, `warning`, `info`, `question`.

## Toast

Preferir los wrappers globales `alertaSuccess(msg)`, `alertaWarning(msg)`, `alertaDanger(msg, timer)`. Equivale a:

```javascript
Swal.fire({toast: true, position: 'top-end', type: 'success', title: 'Guardado', showConfirmButton: false, timer: 6000});
```

## Modal simple

Preferir `mensajeSuccess(msg)`, `mensajeWarning(msg)`, `mensajeDanger(msg)` (usan `nombreempresa` como subtítulo).

```javascript
Swal.fire('Verifique los datos ingresados', '', 'warning');
```

## Confirmación

```javascript
Swal.fire({
    title: '¿Confirmar la reserva?',
    text: 'Se enviará la invitación al cliente.',
    type: 'question',
    showCancelButton: true,
    allowOutsideClick: false,
    confirmButtonText: 'Sí, confirmar',
    cancelButtonText: 'Cancelar'
}).then(function (result) {
    if (!result.value) return;
    pantallaespera();
    $.post('{{ request.path }}', {action: 'confirmar', id: pk}, function (data) {
        $.unblockUI();
        if (data.error === false) { location.reload(); } else { mensajeWarning(data.message); }
    }, 'json');
});
```

`type: 'warning'` para acciones destructivas, `type: 'question'` para las que no lo son.

## Entrada de texto o selección

```javascript
Swal.fire({
    title: 'Motivo de la cancelación',
    input: 'textarea',
    inputPlaceholder: 'Escriba el motivo...',
    showCancelButton: true,
    confirmButtonText: 'Aceptar',
    cancelButtonText: 'Cancelar',
    inputValidator: function (valor) { if (!valor) { return 'El motivo es obligatorio'; } }
}).then(function (result) {
    if (result.value) { enviarMotivo(result.value); }
});
```

Con `input: 'select'` se pasan las opciones en `inputOptions: {clave: 'Etiqueta'}`; `result.value` trae la clave elegida.

## Mensajes del servidor

Los `messages.success/error/warning` de Django se pintan como toast en `window.onload` de `base.html` (`type` = tag del mensaje). Para avisar después de un POST que recarga, usar `messages` en la vista en lugar de un `Swal` en el cliente.
