(function () {
    var boton = document.getElementById('ld-letra');
    if (!boton) {
        return;
    }
    var texto = document.getElementById('ld-letra-texto');
    var raiz = document.documentElement;

    function aplicar(grande) {
        raiz.classList.toggle('ld-grande', grande);
        boton.setAttribute('aria-pressed', grande ? 'true' : 'false');
        texto.textContent = grande ? boton.dataset.grande : boton.dataset.normal;
        boton.title = texto.textContent;
    }

    var guardado = false;
    try {
        guardado = localStorage.getItem('ld-letra-grande') === '1';
    } catch (e) {
    }
    aplicar(guardado);

    boton.addEventListener('click', function () {
        var grande = !raiz.classList.contains('ld-grande');
        aplicar(grande);
        try {
            localStorage.setItem('ld-letra-grande', grande ? '1' : '0');
        } catch (e) {
        }
    });
})();
