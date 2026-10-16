(function () {
    const config = document.getElementById('turnos-config');
    if (!config) {
        return;
    }
    const paso = parseInt(config.dataset.paso, 10) || 40;
    const usuario = config.dataset.usuario;
    const celdas = Array.from(document.querySelectorAll('.turnos-celda'));
    const inicial = JSON.parse(document.getElementById('turnos-celdas').textContent || '{}');
    let pintando = false;
    let marcar = true;

    function minutos(hora) {
        const partes = hora.split(':');
        return parseInt(partes[0], 10) * 60 + parseInt(partes[1], 10);
    }

    function poner(celda, valor) {
        celda.setAttribute('aria-pressed', valor ? 'true' : 'false');
    }

    function marcada(celda) {
        return celda.getAttribute('aria-pressed') === 'true';
    }

    function resumir() {
        const total = celdas.filter(marcada).length;
        const horas = Math.round(total * paso / 6) / 10;
        document.getElementById('turnos-total').textContent = total;
        document.getElementById('turnos-horas').textContent = String(horas).replace('.', ',') + ' h';
    }

    function rellenar(desde, hasta, dias) {
        celdas.forEach(function (celda) {
            const inicio = minutos(celda.dataset.hora);
            const dia = parseInt(celda.dataset.dia, 10);
            poner(celda, dias.indexOf(dia) >= 0 && inicio >= desde && inicio + paso <= hasta);
        });
        resumir();
    }

    celdas.forEach(function (celda) {
        const horas = inicial[celda.dataset.dia] || [];
        poner(celda, horas.indexOf(celda.dataset.hora) >= 0);
        celda.addEventListener('pointerdown', function (e) {
            e.preventDefault();
            pintando = true;
            marcar = !marcada(celda);
            poner(celda, marcar);
            resumir();
        });
        celda.addEventListener('pointerenter', function () {
            if (pintando) {
                poner(celda, marcar);
                resumir();
            }
        });
        celda.addEventListener('keydown', function (e) {
            if (e.key === ' ' || e.key === 'Enter') {
                e.preventDefault();
                poner(celda, !marcada(celda));
                resumir();
            }
        });
    });
    document.addEventListener('pointerup', function () {
        pintando = false;
    });

    document.querySelectorAll('.turnos-cabecera[data-dia]').forEach(function (boton) {
        boton.addEventListener('click', function () {
            const grupo = celdas.filter(function (c) { return c.dataset.dia === boton.dataset.dia; });
            const valor = !grupo.every(marcada);
            grupo.forEach(function (c) { poner(c, valor); });
            resumir();
        });
    });

    document.querySelectorAll('.turnos-cabecera[data-hora]').forEach(function (boton) {
        boton.addEventListener('click', function () {
            const grupo = celdas.filter(function (c) { return c.dataset.hora === boton.dataset.hora; });
            const valor = !grupo.every(marcada);
            grupo.forEach(function (c) { poner(c, valor); });
            resumir();
        });
    });

    const laborables = [0, 1, 2, 3, 4];
    document.querySelectorAll('[data-relleno]').forEach(function (boton) {
        boton.addEventListener('click', function () {
            const tipo = boton.dataset.relleno;
            if (tipo === 'completa') {
                rellenar(8 * 60, 17 * 60, laborables);
            } else if (tipo === 'mananas') {
                rellenar(8 * 60, 12 * 60 + 40, laborables);
            } else if (tipo === 'tardes') {
                rellenar(14 * 60, 18 * 60, laborables);
            } else if (tipo === 'limpiar') {
                celdas.forEach(function (c) { poner(c, false); });
                resumir();
            } else if (tipo === 'copiar') {
                const lunes = celdas.filter(function (c) { return c.dataset.dia === '0' && marcada(c); })
                    .map(function (c) { return c.dataset.hora; });
                celdas.forEach(function (c) {
                    const dia = parseInt(c.dataset.dia, 10);
                    if (dia >= 1 && dia <= 4) {
                        poner(c, lunes.indexOf(c.dataset.hora) >= 0);
                    }
                });
                resumir();
            }
        });
    });

    const alcance = document.getElementById('turnos-alcance');
    $(alcance).on('change', function () {
        document.getElementById('turnos-rango').classList.toggle('d-none', alcance.value !== 'rango');
    });

    document.getElementById('turnos-guardar').addEventListener('click', function () {
        const seleccion = {};
        celdas.filter(marcada).forEach(function (c) {
            (seleccion[c.dataset.dia] = seleccion[c.dataset.dia] || []).push(c.dataset.hora);
        });
        const datos = {
            'action': 'guardarsemana',
            'celdas': JSON.stringify(seleccion),
            'alcance': alcance.value,
            'desde': document.getElementById('turnos-desde').value,
            'hasta': document.getElementById('turnos-hasta').value,
            'csrfmiddlewaretoken': csrfAgenda()
        };
        if (usuario) {
            datos['usuario'] = usuario;
        }
        pantallaespera();
        $.ajax({
            type: 'POST',
            url: window.location.pathname,
            data: datos,
            dataType: 'json',
            success: function (data) {
                $.unblockUI();
                const r = Array.isArray(data) ? data[0] : data;
                if (r && r.error === false) {
                    location.reload();
                } else {
                    mensajeWarning((r && r.message) || 'No se pudo guardar la semana.');
                }
            },
            error: function () {
                $.unblockUI();
                mensajeWarning('Error de conexión.');
            }
        });
    });

    resumir();
})();
