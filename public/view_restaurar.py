from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import render

from agenda import funciones_portal
from autenticacion.funciones_autenticacion import solicitar_restauracion_clave
from core.funciones import addData, rate_limit


def restaurar(request):
    if request.method == 'POST':
        return _solicitar(request)
    data = {'ruta': request.path, 'fecha': datetime.now()}
    addData(request, data)
    t = funciones_portal.contexto_publico(request, data, funciones_portal.portal_principal())
    data['titulo'] = t['au_rp_titulo']
    return render(request, 'public/seguridad/recover_pass.html', data)


@rate_limit(limit=5, seconds=300)
def _solicitar(request):
    """Respuesta siempre neutra: no revela si el correo existe o está habilitado (evita enumerar cuentas)."""
    t = funciones_portal.textos(funciones_portal.idioma_de(request))
    if 'email' not in request.POST:
        return JsonResponse({'resp': False, 'error': t['au_error']})
    solicitar_restauracion_clave(request.POST['email'])
    return JsonResponse({'resp': True, 'url': '/login/', 'mensaje': t['au_rp_ok']})
