(function () {
    const boton = document.getElementById('md-cerrar-guia');
    if (!boton) {
        return;
    }
    boton.addEventListener('click', function () {
        const datos = new FormData();
        datos.append('action', 'guia_vista');
        datos.append('csrfmiddlewaretoken', csrfAgenda());
        fetch('/agenda/alertas/', {method: 'POST', body: datos, credentials: 'same-origin'})
            .then(function () {
                const tarjeta = boton.closest('.md-guia');
                if (tarjeta) tarjeta.remove();
            });
    });
})();
