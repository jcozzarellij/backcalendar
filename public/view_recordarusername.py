import logging
import time
from datetime import datetime

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render

from agenda import funciones_portal
from autenticacion.models import Usuario
from backcalendar import settings
from core.email_config import send_html_mail
from core.funciones import addData, rate_limit
from seguridad.models import Configuracion

logger = logging.getLogger('autenticacion')


def recordarusername(request):
    if request.method == 'POST':
        return _recordar(request)
    if request.user.is_authenticated:
        return redirect('/')
    data = {'ruta': request.path, 'fecha': datetime.now()}
    addData(request, data)
    t = funciones_portal.contexto_publico(request, data, funciones_portal.portal_principal())
    data['titulo'] = t['au_ru_titulo']
    return render(request, 'public/seguridad/recover_username.html', data)


@rate_limit(limit=5, seconds=300)
def _recordar(request):
    """Respuesta siempre neutra: no revela si el correo tiene cuenta (evita enumerar cuentas)."""
    t = funciones_portal.textos(funciones_portal.idioma_de(request))
    if 'email' not in request.POST:
        return JsonResponse({'resp': False, 'error': t['au_error']})
    try:
        usuario = Usuario.objects.filter(email=request.POST['email'], is_active=True, status=True).first()
        if usuario is not None:
            with transaction.atomic():
                datos = {
                    'sucursal': Configuracion.get_instancia().nombre_empresa,
                    'usuario': usuario,
                    'fecha': time.strftime('%Y-%m-%d %H:%M'),
                    'correo': str(settings.EMAIL_HOST_USER),
                }
                send_html_mail('Recordar nombre de usuario', 'email/restaurar.html', datos, [usuario.email], [], [])
    except Exception:
        logger.exception('recordarusername: fallo enviando el recordatorio')
    return JsonResponse({'resp': True, 'url': '/login/', 'mensaje': t['au_ru_ok']})
