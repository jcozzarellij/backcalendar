(function () {
    const nota = document.getElementById('cl-nota');
    if (nota) {
        const estado = document.getElementById('cl-nota-estado');
        let temporizador = null;
        let ultimo = nota.value;
        nota.addEventListener('input', function () {
            estado.textContent = 'Escribiendo…';
            clearTimeout(temporizador);
            temporizador = setTimeout(function () {
                if (nota.value === ultimo) {
                    estado.textContent = 'Guardado.';
                    return;
                }
                $.post('/agenda/clientes/', {
                    action: 'nota', pk: nota.dataset.pk, texto: nota.value, csrfmiddlewaretoken: csrfAgenda()
                }, function (data) {
                    const r = Array.isArray(data) ? data[0] : data;
                    if (r && r.error === false) {
                        ultimo = nota.value;
                        estado.textContent = 'Guardado ' + new Date().toLocaleTimeString('es-EC', {hour: '2-digit', minute: '2-digit'}) + '.';
                    } else {
                        estado.textContent = 'No se pudo guardar.';
                    }
                }, 'json').fail(function () {
                    estado.textContent = 'Sin conexión: no se guardó.';
                });
            }, 900);
        });
    }
})();

function enlaceCliente(id) {
    pantallaespera();
    $.post('/agenda/clientes/', {action: 'enlace', id: id, csrfmiddlewaretoken: csrfAgenda()}, function (data) {
        $.unblockUI();
        const r = Array.isArray(data) ? data[0] : data;
        if (!r || r.error !== false) {
            mensajeWarning((r && r.message) || 'No se pudo generar el enlace.');
            return;
        }
        Swal.fire({
            title: 'Enlace personal del cliente',
            html: '<p class="agenda-sub">Cópialo y envíaselo: con él ve y cambia sus citas sin contraseña. Vence según el parámetro «Vigencia del enlace personal».</p>' +
                '<input type="text" class="form-control" id="cl-enlace" value="' + r.url + '" readonly>',
            confirmButtonText: 'Copiar',
            confirmButtonColor: '#005082',
            showCancelButton: true,
            cancelButtonText: 'Cerrar'
        }).then(function (res) {
            if (!res.value) return;
            const campo = document.getElementById('cl-enlace');
            if (navigator.clipboard) {
                navigator.clipboard.writeText(r.url).then(function () { alertaSuccess('Enlace copiado.'); });
            } else if (campo) {
                campo.select();
                document.execCommand('copy');
                alertaSuccess('Enlace copiado.');
            }
        });
    }, 'json').fail(function () {
        $.unblockUI();
        mensajeWarning('Error de conexión.');
    });
}
