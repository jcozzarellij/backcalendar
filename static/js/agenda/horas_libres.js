(function () {
    const ruta = window.location.pathname;

    function boton(dia, hora) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'btn btn-light btn-sm cal-sugerencia';
        b.dataset.fecha = dia.fecha;
        b.dataset.valor = hora.valor;
        b.textContent = hora.texto;
        return b;
    }

    function listaSugerencias(dias) {
        const lista = document.createElement('div');
        lista.className = 'cal-sugerencias-lista';
        if (!dias.length) {
            const vacio = document.createElement('p');
            vacio.className = 'small text-muted mb-0';
            vacio.textContent = 'No tienes espacios libres en tus turnos de las próximas dos semanas.';
            lista.appendChild(vacio);
            return lista;
        }
        dias.forEach(function (dia) {
            const fila = document.createElement('div');
            fila.className = 'cal-sugerencia-dia';
            const etiqueta = document.createElement('span');
            etiqueta.className = 'cal-sugerencia-fecha';
            etiqueta.textContent = dia.etiqueta;
            fila.appendChild(etiqueta);
            dia.horas.forEach(function (h) { fila.appendChild(boton(dia, h)); });
            lista.appendChild(fila);
        });
        return lista;
    }

    function repintar($caja, dias) {
        if (!$caja.length) return;
        $caja.find('.cal-sugerencias-lista').replaceWith(listaSugerencias(dias));
    }

    function cargarHoras($form, seleccionar) {
        const $select = $form.find('#id_inicio');
        const fecha = $form.find('#id_fecha').val();
        const $caja = $form.find('#cal-sugerencias');
        if (!$select.is('select') || !fecha) return;
        $.getJSON(ruta, {action: 'horas_libres', fecha: fecha, duracion: $form.find('#id_duracion').val(), actual: $caja.data('actual') || ''}, function (data) {
            $select.empty();
            if (!data.result) {
                $select.append(new Option('Elige una fecha válida', ''));
                $select.trigger('change.select2');
                return;
            }
            $select.append(new Option(data.horas.length ? 'Elige una hora' : 'Sin horas libres ese día', ''));
            data.horas.forEach(function (h) {
                $select.append(new Option(h.texto, h.valor, false, h.valor === seleccionar));
            });
            $select.prop('disabled', !data.horas.length).trigger('change.select2');
            $select.removeClass('is-invalid');
            $form.find('#errorMessageinicio').html('');
            if (data.sugerencias.length) repintar($caja, data.sugerencias);
        });
    }

    $(document).on('change', '#id_fecha, #id_duracion', function () {
        cargarHoras($(this).closest('form'));
    });

    $(document).on('click', '#cal-sugerencias .cal-sugerencia', function () {
        const $form = $(this).closest('form');
        $form.find('#cal-sugerencias .cal-sugerencia').removeClass('btn-primary').addClass('btn-light');
        $(this).removeClass('btn-light').addClass('btn-primary');
        $form.find('#id_fecha').val(this.dataset.fecha);
        cargarHoras($form, this.dataset.valor);
    });

    $(document).ajaxSuccess(function (evento, xhr) {
        const res = xhr.responseJSON;
        const primero = Array.isArray(res) ? res[0] : res;
        const $caja = $('.modal.show #cal-sugerencias');
        if (!primero || primero.error !== true || !Array.isArray(primero.sugerencias) || !$caja.length) return;
        repintar($caja, primero.sugerencias);
        cargarHoras($caja.closest('form'));
    });

    window.elegirSugerencia = function (mensaje, dias, alElegir) {
        const cuerpo = document.createElement('div');
        cuerpo.className = 'cal-sugerencias text-start';
        const texto = document.createElement('p');
        texto.className = 'mb-2';
        texto.textContent = mensaje;
        cuerpo.appendChild(texto);
        cuerpo.appendChild(listaSugerencias(dias));
        cuerpo.addEventListener('click', function (e) {
            const elegido = e.target.closest('.cal-sugerencia');
            if (!elegido) return;
            Swal.close();
            alElegir(elegido.dataset.valor);
        });
        Swal.fire({titleText: 'Elige un horario disponible', html: cuerpo, type: 'warning', showConfirmButton: false,
            showCancelButton: true, cancelButtonText: 'Cerrar'});
    };

    window.sugerirHorario = function (mensaje, minutos, alElegir) {
        $.getJSON(ruta, {action: 'sugerencias', duracion: minutos}, function (data) {
            window.elegirSugerencia(mensaje, data.sugerencias || [], alElegir);
        });
    };
})();
