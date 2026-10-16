import sys
from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from core.funciones import addData, secure_module, log
from core.funciones_adicionales import salva_logs
from seguridad.models import TareaCron, CRON_PERIODICIDAD_CHOICES


# Máximo atraso tolerado por periodicidad antes de marcar «caído»: el intervalo esperado ×3,
# con un piso. Si un cron */5 no corre en 20 min, algo pasa; uno semanal tiene mucho más aire.
def _tolerancia_seg(schedule):
    s = (schedule or '').strip()
    if s.startswith('*/'):
        try:
            minutos = int(s.split()[0][2:])
            return max(minutos * 3, 15) * 60
        except (ValueError, IndexError):
            return 3600
    if s.startswith('0 * '):
        return 3 * 3600
    # Diario / semanal: un día y una semana de gracia respectivamente (campo 5 = día semana).
    partes = s.split()
    if len(partes) == 5 and partes[4] != '*':
        return 8 * 24 * 3600
    return 30 * 3600


def _estado(t):
    if not t.activo:
        return 'apagado'
    if not t.ultima_ejecucion:
        return 'sin_correr'
    edad = (datetime.now() - t.ultima_ejecucion.replace(tzinfo=None)).total_seconds()
    if edad > _tolerancia_seg(t.schedule):
        return 'caido'
    return 'error' if t.ultimo_exito is False else 'ok'


@login_required
@secure_module
def cronsView(request):
    data = {
        'titulo': 'Tareas programadas',
        'descripcion': 'Estado, activación y horario de los crons de la plataforma.',
        'modulo': 'Seguridad',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)

    if request.method == 'POST':
        res = []
        action = request.POST.get('action', '')
        try:
            if action == 'toggle':
                t = TareaCron.objects.get(pk=int(request.POST['id']), status=True)
                t.activo = not t.activo
                t.save(update_fields=['activo'])
                estado = 'activó' if t.activo else 'desactivó'
                log(f"{estado.capitalize()} el cron «{t.nombre}»", request, 'change')
                res.append({'error': False, 'reload': True})

            elif action == 'guardar_horario':
                t = TareaCron.objects.get(pk=int(request.POST['id']), status=True)
                schedule = (request.POST.get('schedule') or '').strip()
                if schedule == 'personalizado':
                    schedule = (request.POST.get('schedule_custom') or '').strip()
                partes = schedule.split()
                if len(partes) != 5:
                    raise ValueError('La expresión cron debe tener 5 campos (min hora díames mes díasem).')
                t.schedule = schedule
                t.gestionado_crontab = (request.POST.get('gestionado') == '1')
                t.save(update_fields=['schedule', 'gestionado_crontab'])
                log(f"Cambió el horario del cron «{t.nombre}» a «{schedule}»", request, 'change')
                res.append({'error': False, 'reload': True,
                            'message': 'Horario guardado. Se aplica al crontab en la próxima '
                                       'sincronización (hasta 15 min).'})
        except ValueError as ex:
            res.append({'error': True, 'message': str(ex)})
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res.append({'error': True, 'message': 'Intente nuevamente.'})
        return JsonResponse(res, safe=False)

    if 'action' in request.GET and request.GET['action'] == 'editar':
        t = TareaCron.objects.filter(pk=int(request.GET.get('id') or 0), status=True).first()
        if not t:
            return JsonResponse({'error': True, 'message': 'Tarea no encontrada.'})
        data['tarea'] = t
        data['periodicidades'] = CRON_PERIODICIDAD_CHOICES
        data['es_predefinida'] = any(t.schedule == c[0] for c in CRON_PERIODICIDAD_CHOICES)
        from django.template.loader import get_template
        html = get_template('seguridad/crons/editar.html').render(data)
        return JsonResponse({'error': False, 'html': html})

    tareas = list(TareaCron.objects.filter(status=True).order_by('orden', 'nombre'))
    ahora = datetime.now()
    for t in tareas:
        t.estado = _estado(t)
        t.hace = None
        if t.ultima_ejecucion:
            mins = int((ahora - t.ultima_ejecucion.replace(tzinfo=None)).total_seconds() // 60)
            t.hace = f'{mins} min' if mins < 90 else f'{mins // 60} h'
    data['tareas'] = tareas
    data['resumen'] = {
        'total': len(tareas),
        'ok': sum(1 for t in tareas if t.estado == 'ok'),
        'caidos': sum(1 for t in tareas if t.estado == 'caido'),
        'apagados': sum(1 for t in tareas if t.estado == 'apagado'),
        'error': sum(1 for t in tareas if t.estado == 'error'),
    }
    return render(request, 'seguridad/crons/listado.html', data)
