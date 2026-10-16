(function () {
    var raiz = document.getElementById('pt-portal');
    var T = raiz ? raiz.dataset : {};

    function csrf(form) {
        var campo = form.querySelector('input[name=csrfmiddlewaretoken]');
        return campo ? campo.value : '';
    }

    function mostrarError(el, texto) {
        if (!el) return;
        el.textContent = texto;
        el.hidden = !texto;
    }

    function enviar(form, alTerminar) {
        var boton = form.querySelector('button[type=submit]');
        var error = form.querySelector('[data-error]') || form.querySelector('.pt-error');
        mostrarError(error, '');
        if (boton) { boton.disabled = true; boton.setAttribute('aria-busy', 'true'); }
        fetch(form.getAttribute('action') || window.location.pathname, {
            method: 'POST',
            body: new FormData(form),
            headers: {'X-CSRFToken': csrf(form), 'X-Requested-With': 'XMLHttpRequest'},
            credentials: 'same-origin'
        }).then(function (r) { return r.json(); }).then(function (data) {
            if (data.error) {
                mostrarError(error, data.message || 'No se pudo completar. Intente de nuevo.');
                return;
            }
            alTerminar(data);
        }).catch(function () {
            mostrarError(error, T.tConexion || 'Sin conexión. Revise su internet e intente de nuevo.');
        }).finally(function () {
            if (boton) { boton.disabled = false; boton.removeAttribute('aria-busy'); }
        });
    }

    function urlHoras(base, fecha) {
        return base + (base.indexOf('?') >= 0 ? '&' : '?') + 'action=horas&fecha=' + encodeURIComponent(fecha);
    }

    function marcar(lista, activo) {
        lista.forEach(function (b) { b.setAttribute('aria-pressed', b === activo ? 'true' : 'false'); });
    }

    function cargarHoras(base, fecha, contenedor, alElegir) {
        contenedor.innerHTML = '<p class="pt-horas-vacio">' + (T.tBuscando || 'Buscando horarios…') + '</p>';
        fetch(urlHoras(base, fecha), {credentials: 'same-origin'})
            .then(function (r) { return r.json(); })
            .then(function (data) {
                contenedor.innerHTML = '';
                if (!data.result || !data.data.length) {
                    contenedor.innerHTML = '<p class="pt-horas-vacio">' + (T.tSinHoras || 'Ese día ya no tiene horarios libres. Elija otro.') + '</p>';
                    return;
                }
                data.data.forEach(function (h) {
                    var b = document.createElement('button');
                    b.type = 'button';
                    b.className = 'pt-hora';
                    b.textContent = h.texto;
                    b.dataset.valor = h.valor;
                    b.setAttribute('aria-pressed', 'false');
                    b.addEventListener('click', function () {
                        marcar(Array.prototype.slice.call(contenedor.querySelectorAll('.pt-hora')), b);
                        alElegir(h, b);
                    });
                    contenedor.appendChild(b);
                });
            })
            .catch(function () {
                contenedor.innerHTML = '<p class="pt-horas-vacio">' + (T.tConexion || 'No pudimos cargar los horarios. Intente de nuevo.') + '</p>';
            });
    }

    function agendaReserva(seccion) {
        var base = seccion.dataset.urlHoras;
        var dias = Array.prototype.slice.call(seccion.querySelectorAll('.pt-dia'));
        var bloqueDia = document.getElementById('pt-bloque-dia');
        var bloqueHora = document.getElementById('pt-bloque-hora');
        var bloqueDatos = document.getElementById('pt-bloque-datos');
        var horas = document.getElementById('pt-horas');
        var inicio = document.getElementById('pt-inicio');
        var resDia = document.getElementById('pt-res-dia');
        var resHora = document.getElementById('pt-res-hora');
        var titulo = document.getElementById('pt-titulo-paso');
        var sub = document.getElementById('pt-sub-paso');
        var numero = document.getElementById('pt-paso-num');
        var progreso = seccion.querySelectorAll('.pt-progreso span');
        var aviso = document.getElementById('pt-apartado');
        var textos = {
            1: [titulo.textContent, sub.textContent],
            2: [seccion.dataset.t2Titulo || '¿A qué hora?', seccion.dataset.t2Sub || 'Horarios libres del día elegido, hora de Ecuador.'],
            3: [seccion.dataset.t3Titulo || 'Sus datos', seccion.dataset.t3Sub || 'Solo su nombre y su correo. Sin registro ni contraseña.']
        };
        var porElegir = resDia.textContent;
        var textoFecha = '';

        function paso(n) {
            bloqueDia.hidden = n !== 1;
            bloqueHora.hidden = n !== 2;
            bloqueDatos.hidden = n !== 3;
            titulo.textContent = textos[n][0];
            sub.textContent = textos[n][1];
            numero.textContent = (T.tPaso || 'Paso') + ' ' + n + ' ' + (T.tDe || 'de') + ' 4';
            progreso.forEach(function (p, i) { p.classList.toggle('activo', i < n); });
            seccion.scrollIntoView({behavior: 'smooth', block: 'start'});
        }

        function apartar(valor, boton) {
            if (!seccion.dataset.apartar) return;
            fetch(base + (base.indexOf('?') >= 0 ? '&' : '?') + 'action=apartar&inicio=' + encodeURIComponent(valor), {credentials: 'same-origin'})
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (!data.result) {
                        mostrarError(document.getElementById('pt-error'), data.message || T.tOcupado || 'Ese horario ya no está libre.');
                        boton.disabled = true;
                        boton.setAttribute('aria-pressed', 'false');
                        inicio.value = '';
                        resHora.textContent = porElegir;
                        paso(2);
                        return;
                    }
                    if (aviso) {
                        aviso.textContent = (T.tGuardado || 'Le guardamos este horario por {n} minutos mientras completa sus datos.').replace('{n}', data.minutos);
                        aviso.hidden = false;
                    }
                })
                .catch(function () {});
        }

        dias.forEach(function (boton) {
            boton.addEventListener('click', function () {
                marcar(dias, boton);
                textoFecha = boton.dataset.texto;
                resDia.textContent = textoFecha;
                resHora.textContent = porElegir;
                inicio.value = '';
                paso(2);
                cargarHoras(base, boton.dataset.fecha, horas, function (h, b) {
                    inicio.value = h.valor;
                    resHora.textContent = h.texto;
                    paso(3);
                    var primero = bloqueDatos.querySelector('input[name=nombres]');
                    if (primero) primero.focus({preventScroll: true});
                    apartar(h.valor, b);
                });
            });
        });

        var volverDia = document.getElementById('pt-volver-dia');
        if (volverDia) volverDia.addEventListener('click', function () { paso(1); });
        var volverHora = document.getElementById('pt-volver-hora');
        if (volverHora) volverHora.addEventListener('click', function () { inicio.value = ''; resHora.textContent = porElegir; paso(2); });

        var form = document.getElementById('pt-form');
        if (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                if (!inicio.value) {
                    mostrarError(document.getElementById('pt-error'), T.tElegir || 'Elija primero el día y la hora.');
                    return;
                }
                if (!form.reportValidity()) return;
                enviar(form, function (data) { window.location = data.to; });
            });
        }
    }

    function agendaCambio(seccion) {
        var base = seccion.dataset.urlHoras;
        var dias = Array.prototype.slice.call(seccion.querySelectorAll('.pt-dia'));
        var horas = seccion.querySelector('[data-horas]');
        var form = seccion.querySelector('[data-form-cambio]');
        var inicio = form.querySelector('input[name=inicio]');
        var resumen = form.querySelector('[data-resumen]');
        var textoFecha = '';
        dias.forEach(function (boton) {
            boton.addEventListener('click', function () {
                marcar(dias, boton);
                textoFecha = boton.dataset.texto;
                form.hidden = true;
                inicio.value = '';
                cargarHoras(base, boton.dataset.fecha, horas, function (h) {
                    inicio.value = h.valor;
                    resumen.textContent = 'Nueva fecha: ' + textoFecha + ' a las ' + h.texto;
                    form.hidden = false;
                });
            });
        });
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            if (!inicio.value) {
                mostrarError(form.querySelector('[data-error]'), 'Elija el nuevo día y la hora.');
                return;
            }
            enviar(form, function () { window.location.reload(); });
        });
    }

    document.querySelectorAll('[data-pt-agenda]').forEach(function (seccion) {
        if (seccion.dataset.action === 'reservar') agendaReserva(seccion);
        else agendaCambio(seccion);
    });

    document.querySelectorAll('[data-form-cancelar]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            enviar(form, function () { window.location.reload(); });
        });
    });

    function alternar(boton, panel) {
        panel.hidden = !panel.hidden;
        boton.setAttribute('aria-expanded', panel.hidden ? 'false' : 'true');
        if (!panel.hidden) panel.scrollIntoView({behavior: 'smooth', block: 'start'});
    }

    document.querySelectorAll('[data-abrir]').forEach(function (boton) {
        boton.addEventListener('click', function () {
            var panel = document.getElementById(boton.dataset.abrir);
            if (panel) alternar(boton, panel);
        });
    });

    [['pt-abrir-cambio', 'pt-cambio'], ['pt-abrir-cancelar', 'pt-cancelar']].forEach(function (par) {
        var boton = document.getElementById(par[0]);
        var panel = document.getElementById(par[1]);
        if (boton && panel) boton.addEventListener('click', function () { alternar(boton, panel); });
    });

    var formLlamar = document.getElementById('pt-form-llamar');
    if (formLlamar) {
        var abrir = document.getElementById('pt-abrir-llamar');
        var datos = document.getElementById('pt-ll-datos');
        var tel = document.getElementById('pt-ll-telefono');
        if (abrir && datos) {
            abrir.addEventListener('click', function () {
                if (!tel.reportValidity()) return;
                datos.hidden = false;
                abrir.hidden = true;
                var n = document.getElementById('pt-ll-nombres');
                if (n) n.focus();
            });
        }
        formLlamar.addEventListener('submit', function (e) {
            e.preventDefault();
            var n = document.getElementById('pt-ll-nombres');
            var c = document.getElementById('pt-ll-correo');
            if (n) formLlamar.querySelector('input[name=nombres]').value = n.value;
            if (c) formLlamar.querySelector('input[name=correo]').value = c.value;
            if ((n && !n.value) || (c && !c.reportValidity())) {
                mostrarError(document.getElementById('pt-ll-error'), 'Escriba su nombre y su correo.');
                return;
            }
            enviar(formLlamar, function (data) {
                var exito = document.getElementById('pt-ll-exito');
                exito.textContent = data.message;
                exito.hidden = false;
                if (datos) datos.hidden = true;
            });
        });
    }
})();
