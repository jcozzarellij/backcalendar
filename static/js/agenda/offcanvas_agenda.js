(function () {
    const panel = document.getElementById('mi-agenda-offcanvas');
    if (!panel) return;
    const cuerpo = document.getElementById('mi-agenda-offcanvas-cuerpo');
    let cargadoEn = 0;

    function cargar() {
        if (Date.now() - cargadoEn < 60000) return;
        fetch(panel.dataset.url + '?action=offcanvas', {credentials: 'same-origin', headers: {'X-Requested-With': 'XMLHttpRequest'}})
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.result) throw new Error(data.message || '');
                cuerpo.innerHTML = data.data;
                cargadoEn = Date.now();
            })
            .catch(function () {
                cuerpo.innerHTML = '';
                const p = document.createElement('p');
                p.className = 'text-center text-muted py-4 mb-0';
                p.textContent = 'No se pudo cargar tu agenda. Intenta de nuevo en un momento.';
                cuerpo.appendChild(p);
            });
    }

    panel.addEventListener('show.bs.offcanvas', cargar);

    const boton = document.querySelector('.mi-agenda-flotante');
    const movil = window.matchMedia('(max-width: 991.98px)');

    let pendiente = false;

    function acomodar() {
        if (!boton || pendiente) return;
        pendiente = true;
        requestAnimationFrame(function () {
            pendiente = false;
            const caja = document.querySelector('.af-caja');
            if (!caja || caja.hidden || !caja.getClientRects().length || !movil.matches) {
                boton.style.bottom = '';
                return;
            }
            boton.style.bottom = Math.max(16, window.innerHeight - caja.getBoundingClientRect().top + 12) + 'px';
        });
    }

    new MutationObserver(acomodar).observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['hidden', 'class']});
    window.addEventListener('resize', acomodar);
    movil.addEventListener('change', acomodar);
    acomodar();
})();
