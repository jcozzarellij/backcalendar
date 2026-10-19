from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.utils.formats import date_format

from core.funciones import addData, secure_module
from seguridad.models import Notificacion
from .funciones_alertas import preferencia_de
from .funciones_citas import citas_del_usuario, pendientes_de_cierre
from . import funciones_reuniones
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
    if 'action' in request.GET:
        data['action'] = action = request.GET['action']
        if action == 'offcanvas':
            data.update(_agenda_offcanvas(request.user, hoy, ahora))
            template = get_template('agenda/mi_dia/offcanvas.html')
            return JsonResponse({'result': True, 'data': template.render(data)})
        return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
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
    eventos, _, data['google_error'] = funciones_reuniones.agenda_externa(request.user, dia_ini, dia_fin,
                                                                        excluir=[c.google_event_id for c in citas])
    agenda += [{'inicio': e['inicio'], 'fin': e['fin'], 'cita': None, 'evento': e} for e in eventos]
    agenda.sort(key=lambda a: (a['inicio'], 'evento' not in a))
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


DIAS_PROXIMOS = 7
MAX_PROXIMOS = 8


def _agenda_offcanvas(usuario, hoy, ahora):
    """Lo de hoy y lo próximo (citas y reuniones) para el panel lateral «Mi agenda» del panel."""
    dia_ini = datetime.combine(hoy, datetime.min.time())
    dia_fin = dia_ini + timedelta(days=1)
    tope = dia_ini + timedelta(days=DIAS_PROXIMOS + 1)
    citas = list(citas_del_usuario(usuario, dia_ini, tope))
    items = [{'inicio': c.inicio, 'fin': c.fin, 'titulo': c.titulo,
              'detalle': '' if str(c.cliente) in c.titulo else str(c.cliente), 'tipo': 'cita',
              'url': f'/agenda/citas/{c.pk}/', 'enlace': c.enlace_meet} for c in citas]
    eventos, _, error = funciones_reuniones.agenda_externa(usuario, dia_ini, tope, excluir=[c.google_event_id for c in citas])
    items += [{'inicio': e['inicio'], 'fin': e['fin'], 'titulo': e['titulo'], 'detalle': e.get('lugar', ''),
               'tipo': 'reunion', 'url': '/agenda/mi-agenda/', 'enlace': e.get('meet', ''),
               'todo_el_dia': e['todo_el_dia']} for e in eventos]
    items.sort(key=lambda i: i['inicio'])
    for i in items:
        i['en_curso'] = i['inicio'] <= ahora < i['fin']
        i['terminado'] = i['fin'] <= ahora
    return {
        'oc_hoy': [i for i in items if i['inicio'] < dia_fin and i['fin'] > dia_ini],
        'oc_proximas': [i for i in items if i['inicio'] >= dia_fin][:MAX_PROXIMOS],
        'oc_error': error,
    }
