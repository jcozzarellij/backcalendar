from django.http import JsonResponse
from django.shortcuts import render

from core.funciones import addData, rate_limit
from autenticacion.funciones_autenticacion import solicitar_restauracion_clave

_MENSAJE_NEUTRO = ('Si el correo está registrado y habilitado, te enviamos las instrucciones para '
                   'recuperar tu clave. Revisá tu bandeja de entrada.')


@rate_limit(limit=5, seconds=300)
def restaurar(request):
    data = {'titulo': 'Recuperar Clave', 'url_auth': True}
    addData(request, data)
    resp = {'resp': False}
    if request.method == 'POST':
        if 'email' in request.POST:
            # Respuesta SIEMPRE neutra: no revelar si el correo existe/está habilitado (evita
            # enumeración de cuentas). La restauración real ocurre adentro solo si corresponde.
            solicitar_restauracion_clave(request.POST['email'])
            return JsonResponse({'resp': True, 'url': '/', 'mensaje': _MENSAJE_NEUTRO})
        else:
            data['error'] = 'Credenciales Incorrectas'
            return JsonResponse(data)

    elif request.method == 'GET':
        return render(request, 'public/seguridad/recover_pass.html', data)
