(function () {
    const form = document.getElementById('co-form');
    if (!form) return;
    const duracion = document.getElementById('co-duracion');
    const manual = document.getElementById('co-manual');

    function fin(inicio, minutos) {
        const f = new Date(inicio.replace('T', ' ').replace(/-/g, '/'));
        f.setMinutes(f.getMinutes() + minutos);
        const p = function (n) { return (n < 10 ? '0' : '') + n; };
        return p(f.getHours()) + ':' + p(f.getMinutes());
    }

    function pintarFines() {
        const minutos = parseInt(duracion.value, 10) || 40;
        form.querySelectorAll('.co-fin').forEach(function (el) {
            el.textContent = fin(el.dataset.inicio, minutos);
        });
    }

    pintarFines();
    $(duracion).on('change', pintarFines);

    manual.addEventListener('change', function () {
        form.querySelectorAll('input[name=inicio]').forEach(function (r) { r.checked = false; });
    });

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        const datos = new FormData(form);
        if (manual.value) {
            datos.set('inicio', manual.value.slice(0, 16));
        }
        if (!datos.get('inicio')) {
            mensajeWarning('Elige un espacio sugerido o escribe un horario a mano.');
            return;
        }
        pantallaespera();
        fetch(form.getAttribute('action'), {method: 'POST', body: datos, credentials: 'same-origin'})
            .then(function (r) { return r.json(); })
            .then(function (data) {
                $.unblockUI();
                const res = Array.isArray(data) ? data[0] : data;
                if (res && res.error === false) {
                    location.href = res.to || '/agenda/cola/';
                } else if (res && res.form) {
                    const primero = res.form[0];
                    mensajeWarning(primero ? Object.values(primero)[0] : (res.message || 'Revisa los datos.'));
                } else {
                    mensajeWarning((res && res.message) || 'No se pudo asignar.');
                }
            })
            .catch(function () {
                $.unblockUI();
                mensajeWarning('Error de conexión.');
            });
    });
})();
