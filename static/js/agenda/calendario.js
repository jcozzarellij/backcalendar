(function () {
    const parametros = new URLSearchParams(window.location.search);
    const vistaGuardada = document.cookie.split('; ').some(c => c.startsWith('cal_vista='));
    if (!parametros.has('vista') && !vistaGuardada && window.matchMedia('(max-width: 575.98px)').matches) {
        parametros.set('vista', 'dia');
        window.location.replace(window.location.pathname + '?' + parametros.toString());
        return;
    }
    if (parametros.has('google')) {
        parametros.delete('google');
        const limpia = parametros.toString();
        window.history.replaceState(null, '', window.location.pathname + (limpia ? '?' + limpia : ''));
    }
    const rejilla = document.querySelector('.cal-rejilla');
    const ruta = window.location.pathname;
    const paso = rejilla ? parseInt(rejilla.dataset.paso, 10) || 40 : 40;
    const nodoPlataformas = document.getElementById('cal-plataformas');
    const plataformas = nodoPlataformas ? JSON.parse(nodoPlataformas.textContent) : [];
    let arrastre = null;

    function dos(n) { return (n < 10 ? '0' : '') + n; }

    function sumarMinutos(valor, minutos) {
        const f = new Date(valor.replace('T', ' ').replace(/-/g, '/'));
        f.setMinutes(f.getMinutes() + minutos);
        return f.getFullYear() + '-' + dos(f.getMonth() + 1) + '-' + dos(f.getDate()) + 'T' + dos(f.getHours()) + ':' + dos(f.getMinutes());
    }

    function texto(valor) {
        return valor.slice(8, 10) + '/' + valor.slice(5, 7) + ' ' + valor.slice(11, 16);
    }

    function elemento(etiqueta, clase, contenido) {
        const nodo = document.createElement(etiqueta);
        if (clase) nodo.className = clase;
        if (contenido) nodo.appendChild(document.createTextNode(contenido));
        return nodo;
    }

    function conIcono(nodo, icono, contenido) {
        const i = elemento('i', icono + ' me-2');
        i.setAttribute('aria-hidden', 'true');
        nodo.appendChild(i);
        nodo.appendChild(document.createTextNode(contenido));
        return nodo;
    }

    function enviar(datos, exito, alSugerir) {
        pantallaespera();
        $.post(ruta, Object.assign({csrfmiddlewaretoken: csrfAgenda()}, datos), function (data) {
            $.unblockUI();
            const res = Array.isArray(data) ? data[0] : data;
            if (res && res.error === false) {
                (exito || function () { location.reload(); })(res);
            } else if (res && res.sugerencias && alSugerir) {
                elegirSugerencia(res.message, res.sugerencias, alSugerir);
            } else {
                mensajeWarning((res && res.message) || 'No se pudo completar la acción.');
            }
        }, 'json').fail(function () {
            $.unblockUI();
            mensajeWarning('Error de conexión.');
        });
    }

    function confirmar(titulo, detalle, boton, accion) {
        Swal.fire({
            title: titulo,
            text: detalle,
            type: 'question',
            showCancelButton: true,
            confirmButtonText: boton,
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#005082'
        }).then(function (r) {
            if (r.value) accion();
        });
    }

    function moverYa(actual, inicio) {
        const fin = sumarMinutos(inicio, actual.minutos);
        const otraHora = function (valor) { moverYa(actual, valor); };
        if (actual.tipo === 'cita') {
            enviar({action: 'mover', id: actual.pk, inicio: inicio, fin: fin}, null, otraHora);
        } else {
            enviar({action: 'mover_reunion', id: actual.ref, plataforma: actual.plataforma, inicio: inicio, fin: fin}, null, otraHora);
        }
    }

    function mover(actual, inicio) {
        const que = actual.tipo === 'cita' ? 'la cita' : 'la reunión';
        confirmar('Mover ' + que + ' al ' + texto(inicio), 'Se actualiza en el calendario y se avisa a los invitados. ¿Continuar?', 'Sí, mover', function () {
            moverYa(actual, inicio);
        });
    }

    function preguntarHora(actual, fecha) {
        const cuerpo = elemento('div', 'text-start');
        const etiqueta = elemento('label', 'form-label', '¿A qué hora?');
        etiqueta.htmlFor = 'cal-hora-destino';
        const hora = elemento('input', 'form-control');
        hora.type = 'time';
        hora.id = 'cal-hora-destino';
        hora.step = 300;
        hora.required = true;
        hora.value = actual.hora || '09:00';
        cuerpo.appendChild(etiqueta);
        cuerpo.appendChild(hora);
        const nombre = actual.tipo === 'solicitud' ? 'Asignar a ' + actual.nombre : (actual.tipo === 'cita' ? 'Mover la cita' : 'Mover la reunión');
        Swal.fire({
            titleText: nombre + ' · ' + fecha.slice(8, 10) + '/' + fecha.slice(5, 7),
            html: cuerpo,
            showCancelButton: true,
            confirmButtonText: actual.tipo === 'solicitud' ? 'Continuar' : 'Sí, mover',
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#005082',
            onOpen: function () { hora.focus(); },
            preConfirm: function () {
                if (!/^\d{2}:\d{2}$/.test(hora.value)) {
                    Swal.showValidationMessage('Escribe una hora válida.');
                    return false;
                }
                return hora.value;
            }
        }).then(function (r) {
            if (!r.value) return;
            const inicio = fecha + 'T' + r.value;
            if (actual.tipo === 'solicitud') {
                formModal(actual.pk, 'Asignar horario a ' + actual.nombre, 'asignar', {inicio: inicio}, '/agenda/solicitudes/');
            } else {
                moverYa(actual, inicio);
            }
        });
    }

    function nuevaReunion(plataforma, inicio) {
        formModal(0, 'Nueva reunión · ' + plataforma.nombre, 'reunion', {plataforma: plataforma.clave, inicio: inicio, duracion: 30});
    }

    function nuevaCita(inicio) {
        formModal(0, 'Nueva cita', 'agendar', {inicio: inicio, duracion: paso});
    }

    function elegir(inicio) {
        if (!plataformas.length) {
            nuevaCita(inicio);
            return;
        }
        const cuerpo = elemento('div', 'cal-elegir');
        const cita = elemento('button', 'btn btn-primary');
        cita.type = 'button';
        conIcono(cita, 'fas fa-user-clock', 'Cita con cliente');
        cita.addEventListener('click', function () { Swal.close(); nuevaCita(inicio); });
        cuerpo.appendChild(cita);
        plataformas.forEach(function (p) {
            const boton = elemento('button', 'btn ' + (p.disponible ? 'btn-success' : 'btn-light'));
            boton.type = 'button';
            boton.disabled = !p.disponible;
            const etiqueta = conIcono(elemento('span'), p.icono, 'Reunión en ' + p.nombre);
            boton.appendChild(etiqueta);
            if (p.motivo || p.aviso) boton.appendChild(elemento('small', '', p.motivo || 'Conexión caída: se sincroniza después'));
            boton.addEventListener('click', function () { Swal.close(); nuevaReunion(p, inicio); });
            cuerpo.appendChild(boton);
        });
        Swal.fire({titleText: 'Nueva · ' + texto(inicio), html: cuerpo, showConfirmButton: false, showCancelButton: true, cancelButtonText: 'Cancelar'});
    }

    function detalle(boton) {
        const d = boton.dataset;
        const cuerpo = elemento('div', 'text-start');
        conIcono(cuerpo.appendChild(elemento('p', 'mb-1')), 'far fa-clock', d.horario);
        if (d.lugar) conIcono(cuerpo.appendChild(elemento('p', 'mb-1')), 'fas fa-map-marker-alt', d.lugar);
        conIcono(cuerpo.appendChild(elemento('p', 'mb-1')), 'fab fa-google',
            d.origen === 'turno' ? 'Reunión creada en Turno, en tu Google Calendar.' : 'Generada en Google Calendar.');
        if (d.pendiente) {
            const aviso = conIcono(elemento('p', 'mb-1 text-warning-emphasis'), 'fas fa-rotate', d.pendiente + '. ' + (d.error || 'Se sincroniza cuando la plataforma responda.'));
            cuerpo.appendChild(aviso);
        }
        if (d.editable !== '1') conIcono(cuerpo.appendChild(elemento('p', 'mb-1 text-muted')), 'fas fa-lock', 'Solo su organizador puede modificarla.');
        const acciones = elemento('div', 'd-flex flex-wrap justify-content-center gap-2 mt-3');
        function enlace(url, clase, icono, valor) {
            if (!url) return;
            const a = conIcono(elemento('a', 'btn btn-sm ' + clase), icono, valor);
            a.href = url;
            a.target = '_blank';
            a.rel = 'noopener';
            acciones.appendChild(a);
        }
        function accion(clase, icono, valor, alHacer) {
            const b = conIcono(elemento('button', 'btn btn-sm ' + clase), icono, valor);
            b.type = 'button';
            b.addEventListener('click', alHacer);
            acciones.appendChild(b);
        }
        enlace(d.meet, 'btn-success', 'fas fa-video', 'Unirse');
        if (d.editable === '1') {
            accion('btn-primary', 'fas fa-pen', 'Editar', function () {
                Swal.close();
                formModal(0, 'Editar reunión', 'editar_reunion', {plataforma: d.plataforma, evento: d.ref});
            });
            accion('btn-danger', 'fas fa-trash', 'Eliminar', function () {
                confirmar('Eliminar «' + d.titulo + '»', 'Se quita de tu calendario y se avisa a los invitados.', 'Sí, eliminar', function () {
                    enviar({action: 'eliminar_reunion', id: d.ref, plataforma: d.plataforma});
                });
            });
        }
        if (d.pendiente) {
            accion('btn-warning', 'fas fa-rotate', 'Reintentar', function () {
                Swal.close();
                enviar({action: 'reintentar_reunion', id: d.ref});
            });
        }
        enlace(d.enlace, 'btn-light', 'fas fa-arrow-up-right-from-square', 'Abrir en Google');
        cuerpo.appendChild(acciones);
        Swal.fire({titleText: d.titulo, html: cuerpo, showConfirmButton: false, showCloseButton: true});
    }

    function arrastrable(nodo, datos) {
        nodo.addEventListener('dragstart', function (e) {
            arrastre = datos();
            nodo.classList.add('cal-arrastrando');
            e.dataTransfer.effectAllowed = arrastre.tipo === 'solicitud' ? 'copy' : 'move';
            e.dataTransfer.setData('text/plain', arrastre.pk || arrastre.ref);
        });
        nodo.addEventListener('dragend', function () {
            nodo.classList.remove('cal-arrastrando');
            arrastre = null;
            document.querySelectorAll('.cal-sobre').forEach(function (c) { c.classList.remove('cal-sobre'); });
        });
    }

    document.querySelectorAll('.cal-cita[draggable="true"]').forEach(function (cita) {
        arrastrable(cita, function () { return {tipo: 'cita', pk: cita.dataset.pk, minutos: parseInt(cita.dataset.minutos, 10) || paso}; });
    });

    document.querySelectorAll('a.cal-mes-cita[draggable="true"]').forEach(function (cita) {
        arrastrable(cita, function () {
            return {tipo: 'cita', pk: cita.dataset.pk, minutos: parseInt(cita.dataset.minutos, 10) || paso, hora: cita.dataset.hora};
        });
    });

    document.querySelectorAll('.cal-google[draggable="true"]').forEach(function (reunion) {
        arrastrable(reunion, function () {
            return {tipo: 'reunion', ref: reunion.dataset.ref, plataforma: reunion.dataset.plataforma,
                    minutos: parseInt(reunion.dataset.minutos, 10) || paso, hora: reunion.dataset.hora};
        });
    });

    document.querySelectorAll('.cal-mes-dia[data-fecha]').forEach(function (dia) {
        dia.addEventListener('dragover', function (e) {
            if (!arrastre) return;
            e.preventDefault();
            e.dataTransfer.dropEffect = arrastre.tipo === 'solicitud' ? 'copy' : 'move';
            dia.classList.add('cal-sobre');
        });
        dia.addEventListener('dragleave', function (e) {
            if (!dia.contains(e.relatedTarget)) dia.classList.remove('cal-sobre');
        });
        dia.addEventListener('drop', function (e) {
            e.preventDefault();
            dia.classList.remove('cal-sobre');
            if (!arrastre) return;
            const actual = arrastre;
            arrastre = null;
            preguntarHora(actual, dia.dataset.fecha);
        });
    });

    document.querySelectorAll('.cal-cola').forEach(function (tarjeta) {
        arrastrable(tarjeta, function () { return {tipo: 'solicitud', pk: tarjeta.dataset.pk, nombre: tarjeta.dataset.nombre}; });
    });

    document.querySelectorAll('.cal-google').forEach(function (boton) {
        boton.addEventListener('click', function () { detalle(boton); });
    });

    document.querySelectorAll('.cal-celda.cal-libre, .cal-celda.cal-fuera').forEach(function (celda) {
        celda.addEventListener('dragover', function (e) {
            if (!arrastre) return;
            e.preventDefault();
            e.dataTransfer.dropEffect = arrastre.tipo === 'solicitud' ? 'copy' : 'move';
            celda.classList.add('cal-sobre');
        });
        celda.addEventListener('dragleave', function () {
            celda.classList.remove('cal-sobre');
        });
        celda.addEventListener('drop', function (e) {
            e.preventDefault();
            celda.classList.remove('cal-sobre');
            if (!arrastre) return;
            const inicio = celda.dataset.inicio;
            const actual = arrastre;
            arrastre = null;
            if (actual.tipo === 'solicitud') {
                formModal(actual.pk, 'Asignar horario a ' + actual.nombre, 'asignar', {inicio: inicio}, '/agenda/solicitudes/');
            } else if (celda.classList.contains('cal-fuera')) {
                sugerirHorario('Ese horario está fuera de tus turnos disponibles.', actual.minutos, function (valor) { moverYa(actual, valor); });
            } else {
                mover(actual, inicio);
            }
        });
        celda.addEventListener('click', function () {
            if (!celda.classList.contains('cal-libre')) return;
            elegir(celda.dataset.inicio);
        });
    });

    const nueva = document.getElementById('cal-nueva');
    if (nueva) {
        nueva.addEventListener('click', function () {
            const f = new Date();
            f.setHours(f.getHours() + 1, 0, 0, 0);
            elegir(f.getFullYear() + '-' + dos(f.getMonth() + 1) + '-' + dos(f.getDate()) + 'T' + dos(f.getHours()) + ':00');
        });
    }
})();
