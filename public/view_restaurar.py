from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import render

from agenda import funciones_portal
from autenticacion.funciones_autenticacion import solicitar_restauracion_clave
from core.funciones import addData, rate_limit


def restaurar(request):
    t = funciones_portal.textos(funciones_portal.idioma_de(request))
    data = {
        'titulo': t['au_rp_titulo'],
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)

    if request.method == 'POST':
        return _solicitar(request, t)
    elif request.method == 'GET':
        if 'action' in request.GET:
            data["action"] = action = request.GET['action']
    funciones_portal.contexto_publico(request, data, funciones_portal.portal_principal())
    return render(request, 'public/seguridad/recover_pass.html', data)


@rate_limit(limit=5, seconds=300)
def _solicitar(request, t):
    """Respuesta siempre neutra: no revela si el correo existe o está habilitado (evita enumerar cuentas)."""
    if 'email' not in request.POST:
        return JsonResponse({'resp': False, 'error': t['au_error']})
    solicitar_restauracion_clave(request.POST['email'])
    return JsonResponse({'resp': True, 'url': '/login/', 'mensaje': t['au_rp_ok']})
