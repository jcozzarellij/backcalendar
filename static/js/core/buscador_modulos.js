(function () {
    const campo = document.getElementById('mi-buscar-modulo');
    const nav = document.getElementById('mi-nav-principal');
    if (!campo || !nav) return;
    const vacio = document.getElementById('mi-buscar-vacio');
    const grupos = Array.prototype.slice.call(nav.querySelectorAll('.mi-grupo'));
    const sueltos = Array.prototype.slice.call(nav.querySelectorAll(':scope > .mi-nav-item'));
    const estadoInicial = grupos.map(function (g) { return g.querySelector('.collapse').classList.contains('show'); });

    function normalizar(texto) {
        return (texto || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
    }

    function mostrarGrupo(grupo, abrir) {
        const panel = grupo.querySelector('.collapse');
        const titulo = grupo.querySelector('.mi-grupo-titulo');
        panel.classList.toggle('show', abrir);
        titulo.setAttribute('aria-expanded', abrir ? 'true' : 'false');
    }

    function primerVisible() {
        return nav.querySelector('.mi-nav-item[href]:not([hidden]):not(.mi-grupo-titulo)');
    }

    function filtrar() {
        const consulta = normalizar(campo.value);
        let total = 0;
        sueltos.forEach(function (item) {
            const coincide = !consulta || normalizar(item.textContent).includes(consulta);
            item.hidden = !coincide;
            if (coincide) total++;
        });
        grupos.forEach(function (grupo, i) {
            const nombreGrupo = normalizar(grupo.querySelector('.mi-grupo-titulo').textContent);
            const porGrupo = consulta && nombreGrupo.includes(consulta);
            let visibles = 0;
            grupo.querySelectorAll('.mi-nav-sub').forEach(function (item) {
                const coincide = !consulta || porGrupo || normalizar(item.textContent).includes(consulta);
                item.hidden = !coincide;
                if (coincide) visibles++;
            });
            grupo.hidden = visibles === 0;
            total += visibles;
            mostrarGrupo(grupo, consulta ? visibles > 0 : estadoInicial[i]);
        });
        nav.querySelectorAll('.mi-nav-item.mi-resaltado').forEach(function (n) { n.classList.remove('mi-resaltado'); });
        const primero = consulta ? primerVisible() : null;
        if (primero) primero.classList.add('mi-resaltado');
        vacio.hidden = total > 0;
    }

    campo.addEventListener('input', filtrar);
    campo.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            const primero = primerVisible();
            if (campo.value && primero) {
                e.preventDefault();
                window.location.href = primero.getAttribute('href');
            }
        } else if (e.key === 'Escape') {
            campo.value = '';
            filtrar();
            campo.blur();
        } else if (e.key === 'ArrowDown') {
            const primero = primerVisible();
            if (primero) {
                e.preventDefault();
                primero.focus();
            }
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return;
        const activo = document.activeElement;
        if (activo && (activo.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(activo.tagName))) return;
        if (document.querySelector('.modal.show, .swal2-container, .introjs-tooltip')) return;
        e.preventDefault();
        const lateral = document.getElementById('mi-lateral');
        if (lateral && window.matchMedia('(max-width: 991.98px)').matches) lateral.classList.add('abierto');
        campo.focus();
    });
})();
