(function () {
    const boton = document.getElementById('mi-menu-boton');
    const lateral = document.getElementById('mi-lateral');
    const fondo = document.getElementById('mi-fondo');
    if (!boton || !lateral || !fondo) return;
    function alternar(abrir) {
        lateral.classList.toggle('abierto', abrir);
        fondo.classList.toggle('abierto', abrir);
        boton.setAttribute('aria-expanded', abrir ? 'true' : 'false');
    }
    boton.addEventListener('click', function () { alternar(!lateral.classList.contains('abierto')); });
    fondo.addEventListener('click', function () { alternar(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') alternar(false); });
})();
