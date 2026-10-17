from datetime import datetime

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render

from agenda import funciones_portal
from autenticacion.funciones_autenticacion import cambiar_password_forzada
from autenticacion.models import Usuario
from core.funciones import addData, log


@login_required()
def changepass(request):
    t = funciones_portal.textos(funciones_portal.idioma_de(request))
    data = {
        'titulo': t['au_cc_titulo'],
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)

    if request.method == 'POST':
        if 'passNew' not in request.POST:
            return JsonResponse({'resp': False, 'error': t['au_error']})
        try:
            with transaction.atomic():
                usuario = Usuario.objects.get(id=request.user.id)
                cambiar_password_forzada(usuario, request.POST['passNew'])
                login(request, usuario)
                log(f'Cambio contraseña manual {usuario.get_full_name()}', request, 'change')
            return JsonResponse({'resp': True, 'url': '/login/', 'mensaje': t['au_cc_ok']})
        except Exception as ex:
            return JsonResponse({'resp': False, 'error': str(ex)})
    elif request.method == 'GET':
        if 'action' in request.GET:
            data["action"] = action = request.GET['action']
    funciones_portal.contexto_publico(request, data, funciones_portal.portal_principal())
    return render(request, 'public/seguridad/cambiarclave.html', data)
