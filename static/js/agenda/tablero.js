(function () {
    const columnas = document.querySelectorAll('.tb-columna');
    if (!columnas.length) {
        return;
    }
    let arrastrada = null;

    document.querySelectorAll('.tb-tarjeta[draggable="true"]').forEach(function (tarjeta) {
        tarjeta.addEventListener('dragstart', function (e) {
            arrastrada = tarjeta;
            tarjeta.classList.add('tb-arrastrando');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', tarjeta.dataset.pk);
        });
        tarjeta.addEventListener('dragend', function () {
            tarjeta.classList.remove('tb-arrastrando');
            columnas.forEach(function (c) { c.classList.remove('tb-sobre'); });
        });
    });

    columnas.forEach(function (columna) {
        columna.addEventListener('dragover', function (e) {
            if (!arrastrada || columna.dataset.estado === arrastrada.dataset.estado) return;
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            columna.classList.add('tb-sobre');
        });
        columna.addEventListener('dragleave', function () {
            columna.classList.remove('tb-sobre');
        });
        columna.addEventListener('drop', function (e) {
            e.preventDefault();
            columna.classList.remove('tb-sobre');
            if (!arrastrada) return;
            const pk = arrastrada.dataset.pk;
            const nombre = arrastrada.getAttribute('aria-label');
            const destino = columna.dataset.estado;
            arrastrada = null;
            if (destino === 'asignada') {
                formModal(pk, 'Asignar horario · ' + nombre, 'asignar');
            } else if (destino === 'cerrada') {
                cerrarSolicitud(pk, nombre);
            }
        });
    });
})();
