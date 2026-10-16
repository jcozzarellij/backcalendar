(function () {
    const config = document.getElementById('ct-config');
    if (!config) {
        return;
    }
    const ruta = config.dataset.ruta;
    const nota = document.getElementById('ct-nota');
    const estado = document.getElementById('ct-nota-estado');
    let temporizador = null;
    let ultimo = nota ? nota.value : '';

    function guardarNota() {
        if (!nota || nota.value === ultimo) {
            return;
        }
        const texto = nota.value;
        estado.textContent = 'Guardando…';
        $.post(ruta, {action: 'nota', texto: texto, csrfmiddlewaretoken: csrfAgenda()}, function (data) {
            const r = Array.isArray(data) ? data[0] : data;
            if (r && r.error === false) {
                ultimo = texto;
                estado.textContent = 'Guardado a las ' + r.guardado;
            } else {
                estado.textContent = (r && r.message) || 'No se pudo guardar.';
            }
        }, 'json').fail(function () {
            estado.textContent = 'Sin conexión: se reintenta al seguir escribiendo.';
        });
    }

    if (nota) {
        nota.addEventListener('input', function () {
            clearTimeout(temporizador);
            temporizador = setTimeout(guardarNota, 900);
        });
        nota.addEventListener('blur', guardarNota);
    }

    const rp = document.getElementById('rp-confirmar');
    if (rp) {
        rp.addEventListener('click', function () {
            const inicio = document.getElementById('rp-inicio').value;
            const duracion = document.getElementById('rp-duracion').value;
            if (!inicio) {
                mensajeWarning('Indica el nuevo inicio.');
                return;
            }
            accionAgenda(0, 'reprogramar', {inicio: inicio, duracion: duracion});
        });
    }

    const cn = document.getElementById('cn-confirmar');
    if (cn) {
        cn.addEventListener('click', function () {
            accionAgenda(0, 'cancelar', {motivo: document.getElementById('cn-motivo').value});
        });
    }
})();
