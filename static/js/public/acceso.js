(function () {
    document.querySelectorAll('[data-ver-clave]').forEach(function (boton) {
        boton.addEventListener('click', function () {
            var campo = document.getElementById(boton.getAttribute('aria-controls'));
            var visible = campo.type === 'text';
            campo.type = visible ? 'password' : 'text';
            boton.setAttribute('aria-pressed', visible ? 'false' : 'true');
            boton.querySelector('i').className = visible ? 'fas fa-eye' : 'fas fa-eye-slash';
        });
    });

    document.querySelectorAll('form[data-acceso]').forEach(function (form) {
        var d = form.dataset;
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            if (!form.reportValidity()) return;
            pantallaespera(d.espera, d.espere);
            $.ajax({
                url: form.getAttribute('action') || window.location.pathname,
                data: new FormData(form),
                method: 'POST',
                dataType: 'json',
                cache: false,
                contentType: false,
                processData: false
            }).done(function (data) {
                $.unblockUI();
                if (data.resp !== true) {
                    Alerta.fire(data.error || d.error, '', 'error');
                    return;
                }
                Alerta.fire({title: data.mensaje || '', type: 'success'}).then(function () {
                    window.location = data.url || '/';
                });
            }).fail(function () {
                $.unblockUI();
                Alerta.fire(d.conexion, '', 'error');
            });
        });
    });
})();
