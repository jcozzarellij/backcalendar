from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.shortcuts import render

from autenticacion.models import Usuario
from core.funciones import addData, secure_module
from seguridad.models import Modulo, TareaCron


@login_required
@secure_module
def index_adm(request):
    data = {
        'titulo': 'Panel',
        'descripcion': 'Resumen de la plataforma.',
        'modulo': 'Menu',
        'ruta': '/',
        'fecha': datetime.now(),
    }
    addData(request, data)
    data['usuarios_activos'] = Usuario.objects.filter(status=True, is_active=True).count()
    data['usuarios_staff'] = Usuario.objects.filter(status=True, is_active=True, is_staff=True).count()
    data['roles_total'] = Group.objects.count()
    data['modulos_total'] = Modulo.objects.filter(status=True).count()
    data['crons_activos'] = TareaCron.objects.filter(status=True, activo=True).count()
    return render(request, 'seguridad/index_adm.html', data)
