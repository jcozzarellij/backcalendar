function selectorOrganizador(opciones) {
    const organizador = $(opciones.organizador);
    const nota = opciones.nota ? document.querySelector(opciones.nota) : null;
    const estados = {libre: 'libre', ocupado: 'ocupado', fuera: 'fuera de turno'};
    let pedido = 0;

    function etiqueta(p) {
        return p.nombre + ' · ' + p.rol + ' · ' + (estados[p.estado] || p.estado) + ' · ' + p.citas
            + (p.citas === 1 ? ' cita' : ' citas') + ' esta semana' + (p.google ? '' : ' · sin Google conectado');
    }

    function cargar() {
        const numero = ++pedido;
        const elegido = organizador.val();
        $.getJSON(opciones.url, {action: 'candidatos', equipo: opciones.equipo(), inicio: opciones.inicio(), duracion: opciones.duracion()}, function (data) {
            if (numero !== pedido || !data.result) return;
            const personas = data.personas || [];
            const sugerido = personas.find(function (p) { return p.sugerido; });
            const automatico = data.por_persona
                ? 'Automático: menos carga y por turnos' + (sugerido ? ' → ' + sugerido.nombre : (personas.length ? ' (nadie libre a esa hora)' : ''))
                : 'Líder del equipo' + (sugerido ? ' → ' + sugerido.nombre : '');
            organizador.empty().append(new Option(automatico, ''));
            personas.forEach(function (p) {
                const opcion = new Option(etiqueta(p), p.pk, false, String(p.pk) === String(elegido) && p.estado !== 'ocupado');
                opcion.disabled = p.estado === 'ocupado';
                organizador.append(opcion);
            });
            organizador.trigger('change');
            if (nota) {
                nota.textContent = data.por_persona
                    ? 'Este equipo reparte las citas: va solo a la persona asignada y se bloquea solo su horario.'
                    : 'Este equipo atiende completo: asisten todos los responsables. Aquí eliges quién la organiza (en su cuenta se crea la videollamada).';
            }
        });
    }

    (opciones.cambios || []).forEach(function (selector) {
        $(document).on('change', selector, cargar);
    });
    cargar();
}
