function cerrarSolicitud(id, codigo) {
    Swal.fire({
        title: 'Cerrar ' + codigo + ' sin cita',
        input: 'text',
        inputPlaceholder: 'Motivo (por ejemplo: el cliente ya no necesita la reunión)',
        showCancelButton: true,
        confirmButtonText: 'Cerrar solicitud',
        cancelButtonText: 'Volver',
        confirmButtonColor: '#16C784',
        cancelButtonColor: '#64748B'
    }).then(function (r) {
        if (r.value === undefined) return;
        accionAgenda(id, 'cerrar', {motivo: r.value || ''});
    });
}
