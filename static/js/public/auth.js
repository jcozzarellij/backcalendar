function pantallaespera(titulo, mensaje) {
    titulo = titulo || 'Procesando';
    mensaje = mensaje || 'Por favor espere...';
    var logo = window.auLogoEspera ? '<img src="' + window.auLogoEspera + '" class="au-espera-logo" alt="">' : '';
    $.blockUI({
        message: '<div class="au-espera">' + logo +
            '<div class="spinner-border text-light au-espera-spinner" role="status"></div>' +
            '<div class="au-espera-titulo">' + titulo + '</div>' +
            '<div class="au-espera-texto">' + mensaje + '</div></div>',
        css: {padding: '20px', backgroundColor: 'rgba(0, 80, 130, 0.92)', border: 'none', borderRadius: '12px', width: '280px', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', zIndex: 9999999},
        overlayCSS: {backgroundColor: 'rgba(0, 0, 0, 0.5)', zIndex: 9999990}
    });
}

function mensajeDanger(mensaje) {
    Swal.fire('', mensaje, 'error');
}

function mensajeWarning(mensaje) {
    Swal.fire('', mensaje, 'warning');
}

function mensajeSuccess(mensaje) {
    Swal.fire('', mensaje, 'success');
}

function alertaDanger(mensaje) {
    Swal.fire({toast: true, position: 'top-end', type: 'error', title: mensaje, showConfirmButton: false, timer: 6000});
}

function alertaSuccess(mensaje) {
    Swal.fire({toast: true, position: 'top-end', type: 'success', title: mensaje, showConfirmButton: false, timer: 6000});
}

$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        function getCookie(name) {
            var cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var cookie = jQuery.trim(cookies[i]);
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }

        if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
            xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
        }
    }
});

$('.valnum').on('keypress', function (e) {
    return soloNumeros(e);
});

$(document).on('click', '.au-pass-toggle', function () {
    var inp = $(this).siblings('input');
    var tipo = inp.attr('type') === 'password' ? 'text' : 'password';
    inp.attr('type', tipo);
    $(this).attr('aria-pressed', tipo === 'text' ? 'true' : 'false');
    $(this).attr('aria-label', tipo === 'password' ? 'Mostrar contraseña' : 'Ocultar contraseña');
    $(this).find('i').attr('class', tipo === 'password' ? 'fas fa-eye' : 'fas fa-eye-slash');
});
