function copiarEnlace(id) {
    const campo = document.getElementById(id);
    if (!campo) return;
    campo.select();
    const copiar = navigator.clipboard ? navigator.clipboard.writeText(campo.value) : Promise.reject();
    copiar.then(function () {
        alertaSuccess('Copiado.');
    }).catch(function () {
        document.execCommand('copy');
        alertaSuccess('Copiado.');
    });
}

(function () {
    const enlace = document.getElementById('po-enlace');
    const botones = document.querySelectorAll('[data-po-tipo]');
    if (!enlace || !botones.length) return;
    botones.forEach(function (b) {
        b.addEventListener('click', function () {
            botones.forEach(function (o) { o.classList.remove('btn-primary'); o.classList.add('btn-light'); });
            b.classList.remove('btn-light');
            b.classList.add('btn-primary');
            enlace.value = enlace.dataset[b.dataset.poTipo] || '';
            enlace.rows = b.dataset.poTipo === 'incrustado' ? 4 : 2;
        });
    });
})();
