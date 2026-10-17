window.colaAvisos = window.colaAvisos || (function () {
    const PAUSA_MS = 600;
    const pendientes = [];
    let ocupado = false;

    function pedir(mostrar) {
        if (ocupado) {
            pendientes.push(mostrar);
            return;
        }
        ocupado = true;
        mostrar();
    }

    function liberar() {
        ocupado = false;
        const siguiente = pendientes.shift();
        if (siguiente) setTimeout(() => pedir(siguiente), PAUSA_MS);
    }

    return {pedir, liberar};
})();
