(function () {
    var campo = document.getElementById('ct-buscar');
    var lista = document.getElementById('ct-lista');
    if (!campo || !lista) {
        return;
    }
    var celdas = Array.prototype.slice.call(lista.querySelectorAll('.ld-ticket-celda'));
    var vacio = document.getElementById('ct-sin-resultados');
    var cuenta = document.getElementById('ct-cuenta');

    function normalizar(texto) {
        return (texto || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
    }

    celdas.forEach(function (celda) {
        celda.dataset.indice = normalizar(celda.dataset.buscar);
    });

    campo.addEventListener('input', function () {
        var busqueda = normalizar(campo.value.trim());
        var visibles = 0;
        celdas.forEach(function (celda) {
            var coincide = !busqueda || celda.dataset.indice.indexOf(busqueda) !== -1;
            celda.hidden = !coincide;
            if (coincide) {
                visibles += 1;
            }
        });
        vacio.hidden = visibles !== 0;
        cuenta.textContent = visibles + ' ' + (visibles === 1 ? cuenta.dataset.sufijoUno : cuenta.dataset.sufijo);
    });
})();
