(function () {
    if (!document.body.dataset.alertasAgenda) {
        return;
    }
    const ruta = '/agenda/alertas/';
    const CLAVE = 'agenda_alerta_pospuesta';
    let caja = null;
    let actual = null;

    function pospuestas() {
        try {
            return JSON.parse(sessionStorage.getItem(CLAVE) || '{}');
        } catch (e) {
            return {};
        }
    }

    function posponer(id, minutos) {
        const datos = pospuestas();
        datos[id] = Date.now() + minutos * 60000;
        try {
            sessionStorage.setItem(CLAVE, JSON.stringify(datos));
        } catch (e) {
        }
    }

    function pospuesta(id) {
        const hasta = pospuestas()[id];
        return hasta && hasta > Date.now();
    }

    function csrf() {
        const campo = document.querySelector('input[name=csrfmiddlewaretoken]');
        if (campo) return campo.value;
        const m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? m[1] : '';
    }

    function cerrar() {
        if (caja) {
            caja.hidden = true;
        }
        actual = null;
    }

    function pintar(alerta) {
        if (!caja) {
            caja = document.createElement('aside');
            caja.className = 'af-caja';
            caja.setAttribute('role', 'alert');
            caja.setAttribute('aria-live', 'assertive');
            document.body.appendChild(caja);
        }
        const faltan = alerta.faltan;
        const texto = faltan <= 0 ? 'Empieza ahora' : 'Empieza en ' + faltan + ' min';
        caja.innerHTML =
            '<button type="button" class="af-cerrar" aria-label="Cerrar"><i class="fas fa-times"></i></button>' +
            '<p class="af-eyebrow">Tu próxima cita · ' + alerta.inicio + '</p>' +
            '<p class="af-titulo">' + alerta.titulo + '</p>' +
            '<p class="agenda-sub mb-1">' + alerta.cliente + ' · ' + alerta.codigo + '</p>' +
            '<p class="af-faltan' + (faltan <= 0 ? ' af-ahora' : '') + '">' + texto + '</p>' +
            '<div class="af-acciones">' +
            (alerta.meet ? '<a href="' + alerta.meet + '" target="_blank" rel="noopener" class="btn btn-success btn-sm"><i class="fas fa-video me-1"></i>Entrar</a>' : '<a href="' + alerta.url + '" class="btn btn-primary btn-sm"><i class="fas fa-eye me-1"></i>Ver cita</a>') +
            '<button type="button" class="btn btn-light btn-sm" data-af="posponer"><i class="fas fa-clock me-1"></i>Avisar en 5</button>' +
            '<button type="button" class="btn btn-warning btn-sm" data-af="tarde"><i class="fas fa-running me-1"></i>Llego tarde</button>' +
            '</div>';
        caja.hidden = false;
        actual = alerta;
        caja.querySelector('.af-cerrar').addEventListener('click', function () {
            posponer(alerta.id, 60);
            cerrar();
        });
        caja.querySelector('[data-af=posponer]').addEventListener('click', function () {
            posponer(alerta.id, 5);
            cerrar();
        });
        caja.querySelector('[data-af=tarde]').addEventListener('click', function () {
            const minutos = window.prompt('¿Cuántos minutos tarde llegas?', '5');
            if (minutos === null) return;
            const datos = new FormData();
            datos.append('action', 'tarde');
            datos.append('id', alerta.id);
            datos.append('minutos', minutos);
            datos.append('csrfmiddlewaretoken', csrf());
            fetch(ruta, {method: 'POST', body: datos, credentials: 'same-origin'})
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    const res = Array.isArray(data) ? data[0] : data;
                    if (res && res.error === false) {
                        if (typeof alertaSuccess === 'function') alertaSuccess(res.message);
                        posponer(alerta.id, 60);
                        cerrar();
                    } else if (typeof mensajeWarning === 'function') {
                        mensajeWarning((res && res.message) || 'No se pudo avisar.');
                    }
                });
        });
    }

    function consultar() {
        fetch(ruta + '?action=pendientes', {credentials: 'same-origin', headers: {'X-Requested-With': 'XMLHttpRequest'}})
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                if (!data || !data.result) return;
                const alerta = data.data.find(function (a) { return !pospuesta(a.id); });
                if (!alerta) {
                    if (actual) cerrar();
                    return;
                }
                if (!actual || actual.id !== alerta.id || actual.faltan !== alerta.faltan) {
                    pintar(alerta);
                }
            })
            .catch(function () {
            });
    }

    consultar();
    setInterval(consultar, 60000);
})();
