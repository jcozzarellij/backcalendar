
from core.email_config import send_html_mail
from core.funciones import addData, rate_limit
from backcalendar import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils.timezone import activate
from autenticacion.models import Usuario

activate(settings.TIME_ZONE)
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from seguridad.models import Configuracion
import time
from django.utils.timezone import activate


@rate_limit(limit=5, seconds=300)
def recordarusername(request):
    confi = Configuracion.objects.first()
    data = {'titulo': 'Recuperar Nombre de Usuario', 'url_auth':True}
    addData(request, data)
    resp = {'resp': False}
    # Respuesta SIEMPRE neutra: no revelar si el correo tiene cuenta (evita enumeración).
    mensaje_neutro = 'Si el correo está registrado, te enviamos el recordatorio. Revisá tu bandeja de entrada.'
    if request.method == 'POST':
        if 'email' in request.POST:
            email = request.POST['email']
            try:
                us = Usuario.objects.filter(email=email, is_active=True, status=True).first()
                if us is not None:
                    with transaction.atomic():
                        datos = {
                            'sucursal': confi.nombre_empresa,
                            'usuario': us,
                            'fecha': str(time.strftime("%Y-%m-%d %H:%M")),
                            'correo': str(settings.EMAIL_HOST_USER)
                        }
                        send_html_mail('Recordar nombre de usuario', "email/restaurar.html", datos, [us.email], [], [])
            except Exception:
                import logging
                logging.getLogger('autenticacion').exception('recordarusername: fallo enviando el recordatorio')
            return JsonResponse({'resp': True, 'url': '/', 'mensaje': mensaje_neutro})
        else:
            data['error'] = 'Credenciales Incorrectas'
            return JsonResponse(data)

    elif request.method == 'GET':
        if request.user.username != "":
            return redirect('/')
        # return render(request, 'public/seguridad/recuperar_username.html', data)
        return render(request, 'public/seguridad/recover_username.html', data)