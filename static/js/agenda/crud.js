function csrfAgenda() {
    return $('input[name=csrfmiddlewaretoken]').first().val();
}

function formModal(id, texto, action, extra, url) {
    const destino = url || window.location.pathname;
    pantallaespera();
    $.ajax({
        type: 'GET',
        url: destino,
        data: Object.assign({'action': action, 'pk': id}, extra || {}),
        dataType: 'json',
        success: function (data) {
            $.unblockUI();
            if (data.result === true) {
                $('#modalNombre').text(texto);
                $('#modalDetalle form').attr('action', destino);
                $('.detalleProdModal').html(data.data);
                bootstrap.Modal.getOrCreateInstance(document.getElementById('modalDetalle')).show();
            } else {
                mensajeWarning(data.message);
            }
        },
        error: function () {
            $.unblockUI();
            mensajeWarning('Error de conexión.');
        }
    });
}

function accionAgenda(id, action, extra) {
    pantallaespera();
    $.ajax({
        type: 'POST',
        url: window.location.pathname,
        data: Object.assign({'action': action, 'id': id, 'csrfmiddlewaretoken': csrfAgenda()}, extra || {}),
        dataType: 'json',
        success: function (data) {
            $.unblockUI();
            const r = Array.isArray(data) ? data[0] : data;
            if (r && r.error === false) {
                if (r.to) {
                    location.href = r.to;
                } else {
                    location.reload();
                }
            } else {
                mensajeWarning((r && r.message) || 'No se pudo completar la acción.');
            }
        },
        error: function () {
            $.unblockUI();
            mensajeWarning('Error de conexión.');
        }
    });
}
