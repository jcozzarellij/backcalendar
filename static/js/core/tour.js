(function () {
    const boton = document.getElementById('mi-guia-boton');
    if (!boton || typeof introJs !== 'function') return;
    const CLAVE_VISTA = 'turno_tour_visto';

    const GENERALES = [
        {selector: '#mi-lateral .mi-nav', texto: 'Este es tu menú. Desde aquí llegas a cada pantalla del panel según los permisos de tu rol.'},
        {selector: '#mi-lateral a[href="/agenda/aplicaciones/"]', texto: 'Paso 1 · Conexiones: conecta tu cuenta de Google (Gmail y Calendar). Tus citas y reuniones se crean con enlace de Meet y se cruzan con lo que ya tienes ocupado.'},
        {selector: '#mi-lateral a[href="/agenda/mis-turnos/"]', texto: 'Paso 2 · Mis turnos: declara los días y horas en que atiendes. Solo en esos turnos se puede agendar.'},
        {selector: '#mi-lateral a[href="/agenda/alertas/"]', texto: 'Paso 3 · Alertas: elige cuántos minutos antes te avisamos y activa las notificaciones push y por correo.'},
        {selector: '#mi-lateral a[href="/agenda/mi-agenda/"]', texto: 'Mi agenda: crea citas y reuniones en tus horas libres. Si eliges un horario ocupado te sugerimos días disponibles.'},
        {selector: '[data-tour="agenda-flotante"]', texto: 'Este botón abre tu agenda del día y tus próximas reuniones desde cualquier pantalla.'},
        {selector: '[data-tour="notificaciones"]', texto: 'Aquí llegan los avisos: citas asignadas, cambios y recordatorios 10 minutos antes de empezar.'},
        {selector: '#mi-guia-boton', texto: 'Puedes volver a ver esta guía cuando quieras con este botón.'}
    ];

    function visible(nodo) {
        return !!nodo && !!(nodo.offsetWidth || nodo.offsetHeight || nodo.getClientRects().length);
    }

    function abrirGrupo(nodo) {
        const grupo = nodo && nodo.closest('.collapse');
        if (grupo && !grupo.classList.contains('show') && window.bootstrap) {
            bootstrap.Collapse.getOrCreateInstance(grupo, {toggle: false}).show();
        }
    }

    function pasos() {
        const propios = Array.prototype.slice.call(document.querySelectorAll('[data-tour-texto]'))
            .filter(visible)
            .sort(function (a, b) { return (parseInt(a.dataset.tourPaso, 10) || 0) - (parseInt(b.dataset.tourPaso, 10) || 0); })
            .map(function (nodo) { return {element: nodo, intro: nodo.dataset.tourTexto}; });
        const generales = GENERALES.map(function (p) {
            const nodo = document.querySelector(p.selector);
            if (!nodo) return null;
            abrirGrupo(nodo);
            return {element: nodo, intro: p.texto};
        }).filter(Boolean);
        const lista = [{intro: 'Bienvenido a Turno. Te mostramos en pocos pasos cómo dejar lista tu agenda.'}].concat(generales, propios);
        return lista;
    }

    function marcarVista() {
        try { localStorage.setItem(CLAVE_VISTA, '1'); } catch (e) {}
        if (boton.dataset.auto !== '1') return;
        boton.dataset.auto = '';
        const datos = new FormData();
        datos.append('csrfmiddlewaretoken', boton.dataset.csrf);
        datos.append('action', 'guia_vista');
        fetch('/agenda/alertas/', {method: 'POST', body: datos, credentials: 'same-origin', headers: {'X-Requested-With': 'XMLHttpRequest'}}).catch(function () {});
    }

    function iniciar() {
        const menu = document.getElementById('mi-lateral');
        const lateralMovil = window.matchMedia('(max-width: 991.98px)').matches;
        if (lateralMovil && menu) menu.classList.add('abierto');
        const tour = introJs();
        tour.setOptions({
            steps: pasos(),
            nextLabel: 'Siguiente',
            prevLabel: 'Anterior',
            skipLabel: 'Saltar',
            doneLabel: 'Listo',
            showStepNumbers: false,
            showBullets: true,
            exitOnOverlayClick: false,
            scrollToElement: true,
            tooltipClass: 'tour-turno'
        });
        tour.onbeforechange(function (nodo) { abrirGrupo(nodo); });
        function terminar() {
            if (lateralMovil && menu) menu.classList.remove('abierto');
            marcarVista();
        }
        tour.oncomplete(terminar);
        tour.onexit(terminar);
        tour.start();
    }

    boton.addEventListener('click', iniciar);

    let vista = false;
    try { vista = localStorage.getItem(CLAVE_VISTA) === '1'; } catch (e) {}
    if (boton.dataset.auto === '1' && !vista) {
        window.addEventListener('load', function () { setTimeout(iniciar, 600); });
    }
})();
