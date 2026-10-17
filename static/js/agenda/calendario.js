(function () {
    const parametros = new URLSearchParams(window.location.search);
    const vistaGuardada = document.cookie.split('; ').some(c => c.startsWith('cal_vista='));
    if (!parametros.has('vista') && !vistaGuardada && window.matchMedia('(max-width: 575.98px)').matches) {
        parametros.set('vista', 'dia');
        window.location.replace(window.location.pathname + '?' + parametros.toString());
        return;
    }
    const rejilla = document.querySelector('.cal-rejilla');
    const ruta = window.location.pathname;
    const paso = rejilla ? parseInt(rejilla.dataset.paso, 10) || 40 : 40;
    let arrastre = null;

    function sumarMinutos(valor, minutos) {
        const f = new Date(valor.replace('T', ' ').replace(/-/g, '/'));
        f.setMinutes(f.getMinutes() + minutos);
        const p = function (n) { return (n < 10 ? '0' : '') + n; };
        return f.getFullYear() + '-' + p(f.getMonth() + 1) + '-' + p(f.getDate()) + 'T' + p(f.getHours()) + ':' + p(f.getMinutes());
    }

    function texto(valor) {
        return valor.slice(8, 10) + '/' + valor.slice(5, 7) + ' ' + valor.slice(11, 16);
    }

    function mover(pk, inicio, minutos) {
        Swal.fire({
            title: 'Mover la cita al ' + texto(inicio),
            text: 'Se actualiza en el calendario y se avisa a los invitados. ¿Continuar?',
            type: 'question',
            showCancelButton: true,
            confirmButtonText: 'Sí, mover',
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#005082'
        }).then(function (r) {
            if (!r.value) return;
            pantallaespera();
            $.post(ruta, {action: 'mover', id: pk, inicio: inicio, fin: sumarMinutos(inicio, minutos), csrfmiddlewaretoken: csrfAgenda()}, function (data) {
                $.unblockUI();
                const res = Array.isArray(data) ? data[0] : data;
                if (res && res.error === false) {
                    location.reload();
                } else {
                    mensajeWarning((res && res.message) || 'No se pudo mover la cita.');
                }
            }, 'json').fail(function () {
                $.unblockUI();
                mensajeWarning('Error de conexión.');
            });
        });
    }

    document.querySelectorAll('.cal-cita[draggable="true"]').forEach(function (cita) {
        cita.addEventListener('dragstart', function (e) {
            arrastre = {tipo: 'cita', pk: cita.dataset.pk, minutos: parseInt(cita.dataset.minutos, 10) || paso};
            cita.classList.add('cal-arrastrando');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', cita.dataset.pk);
        });
        cita.addEventListener('dragend', function () {
            cita.classList.remove('cal-arrastrando');
            arrastre = null;
            document.querySelectorAll('.cal-sobre').forEach(function (c) { c.classList.remove('cal-sobre'); });
        });
    });

    document.querySelectorAll('.cal-cola').forEach(function (tarjeta) {
        tarjeta.addEventListener('dragstart', function (e) {
            arrastre = {tipo: 'solicitud', pk: tarjeta.dataset.pk, nombre: tarjeta.dataset.nombre};
            tarjeta.classList.add('cal-arrastrando');
            e.dataTransfer.effectAllowed = 'copy';
            e.dataTransfer.setData('text/plain', tarjeta.dataset.pk);
        });
        tarjeta.addEventListener('dragend', function () {
            tarjeta.classList.remove('cal-arrastrando');
            arrastre = null;
            document.querySelectorAll('.cal-sobre').forEach(function (c) { c.classList.remove('cal-sobre'); });
        });
    });

    document.querySelectorAll('.cal-celda.cal-libre, .cal-celda.cal-fuera').forEach(function (celda) {
        celda.addEventListener('dragover', function (e) {
            if (!arrastre) return;
            e.preventDefault();
            e.dataTransfer.dropEffect = arrastre.tipo === 'cita' ? 'move' : 'copy';
            celda.classList.add('cal-sobre');
        });
        celda.addEventListener('dragleave', function () {
            celda.classList.remove('cal-sobre');
        });
        celda.addEventListener('drop', function (e) {
            e.preventDefault();
            celda.classList.remove('cal-sobre');
            if (!arrastre) return;
            const inicio = celda.dataset.inicio;
            const actual = arrastre;
            arrastre = null;
            if (actual.tipo === 'cita') {
                mover(actual.pk, inicio, actual.minutos);
            } else {
                formModal(actual.pk, 'Asignar horario a ' + actual.nombre, 'asignar', {inicio: inicio}, '/agenda/solicitudes/');
            }
        });
        celda.addEventListener('click', function () {
            if (!celda.classList.contains('cal-libre')) return;
            formModal(0, 'Nueva cita · ' + texto(celda.dataset.inicio), 'agendar', {inicio: celda.dataset.inicio, duracion: paso});
        });
    });

    const nueva = document.getElementById('cal-nueva');
    if (nueva) {
        nueva.addEventListener('click', function () {
            const f = new Date();
            f.setHours(f.getHours() + 1, 0, 0, 0);
            const p = function (n) { return (n < 10 ? '0' : '') + n; };
            const inicio = f.getFullYear() + '-' + p(f.getMonth() + 1) + '-' + p(f.getDate()) + 'T' + p(f.getHours()) + ':00';
            formModal(0, 'Nueva cita', 'agendar', {inicio: inicio, duracion: paso});
        });
    }
})();
