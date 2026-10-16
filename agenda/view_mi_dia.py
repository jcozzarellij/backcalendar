from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.formats import date_format

from core.funciones import addData, secure_module
from seguridad.models import Notificacion
from .funciones_alertas import preferencia_de
from .funciones_citas import citas_del_usuario, pendientes_de_cierre
from .funciones_disponibilidad import espacios_libres
from .funciones_turnos import duracion_turno
from .models import ConexionAplicacion, PatronTurno, Solicitud


@login_required
@secure_module
def miDiaView(request):
    hoy = date.today()
    ahora = datetime.now()
    data = {
        'titulo': 'Mi día',
        'descripcion': date_format(hoy, r'l j \d\e F \d\e Y').capitalize(),
        'modulo': 'Agenda',
        'ruta': request.path,
        'fecha': str(hoy),
    }
    addData(request, data)
    dia_ini = datetime.combine(hoy, datetime.min.time())
    dia_fin = dia_ini + timedelta(days=1)
    citas = list(citas_del_usuario(request.user, dia_ini, dia_fin))
    proxima = next((c for c in citas if c.fin > ahora), None)
    paso = duracion_turno()
    libres = [h for h in espacios_libres(request.user, hoy, paso) if h >= ahora]
    agenda = [{'inicio': c.inicio, 'fin': c.fin, 'cita': c} for c in citas]
    for h in libres:
        if not any(a['inicio'] <= h < a['fin'] for a in agenda):
            agenda.append({'inicio': h, 'fin': h + timedelta(minutes=paso), 'cita': None})
    agenda.sort(key=lambda a: a['inicio'])
    data['proxima'] = proxima
    data['agenda'] = agenda
    data['citas_hoy'] = len(citas)
    data['pendientes'] = list(pendientes_de_cierre(request.user)[:5])
    data['pendientes_total'] = pendientes_de_cierre(request.user).count()
    data['en_cola'] = Solicitud.objects.filter(status=True, estado='en_cola').count()
    data['alertas'] = Notificacion.objects.filter(status=True, destinatario=request.user, leido=False).order_by('-fecha_registro')[:5]
    data['google'] = ConexionAplicacion.objects.filter(status=True, usuario=request.user, proveedor='google').first()
    pref = preferencia_de(request.user)
    tiene_horarios = PatronTurno.objects.filter(status=True, usuario=request.user).exists()
    data['guia'] = None if pref.primer_ingreso_visto else {
        'google': bool(data['google'] and data['google'].conectada),
        'horarios': tiene_horarios,
        'equipo': request.user.membresias_agenda.filter(status=True).exists(),
    }
    return render(request, 'agenda/mi_dia/listado.html', data)
