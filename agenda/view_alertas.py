import sys
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render

from core.funciones import addData, log, paginador, secure_module
from core.funciones_adicionales import salva_logs
from seguridad.models import Notificacion
from .funciones_alertas import alertas_pendientes, avisar_tarde, preferencia_de
from .models import Cita


@login_required
@secure_module
def alertasView(request):
    data = {
        'titulo': 'Alertas',
        'descripcion': 'Avisos de tus citas y de tus conexiones, y cómo quieres recibirlos.',
        'modulo': 'Agenda',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)
    pref = preferencia_de(request.user)
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'preferencias':
                    try:
                        minutos = int(request.POST.get('aviso_previo_min', pref.aviso_previo_min))
                    except ValueError:
                        raise ValueError('Los minutos de aviso deben ser un número.')
                    if not 1 <= minutos <= 120:
                        raise ValueError('El aviso debe estar entre 1 y 120 minutos.')
                    pref.aviso_previo_min = minutos
                    pref.alerta_pantalla = request.POST.get('alerta_pantalla') in ('1', 'on', 'true')
                    pref.alerta_push = request.POST.get('alerta_push') in ('1', 'on', 'true')
                    pref.alerta_correo = request.POST.get('alerta_correo') in ('1', 'on', 'true')
                    pref.save(request)
                    log('Cambió sus preferencias de alertas', request, 'change', obj=pref.id)
                    messages.success(request, 'Preferencias guardadas')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'leer':
                    Notificacion.objects.filter(destinatario=request.user, pk=int(request.POST['id']), leido=False).update(leido=True, fecha_hora_leido=datetime.now())
                    res_json = {'error': False}
                elif action == 'leertodas':
                    Notificacion.objects.filter(destinatario=request.user, leido=False).update(leido=True, fecha_hora_leido=datetime.now())
                    messages.success(request, 'Todas las alertas quedaron leídas')
                    res_json = {'error': False}
                elif action == 'tarde':
                    cita = Cita.objects.select_related('cliente').get(pk=int(request.POST['id']), status=True,
                                                                     participantes__usuario=request.user, participantes__status=True)
                    minutos = max(1, min(60, int(request.POST.get('minutos') or 5)))
                    avisar_tarde(cita, request.user, minutos, request)
                    log(f'Avisó que llega {minutos} min tarde a la cita {cita.codigo}', request, 'change', obj=cita.id)
                    res_json = {'error': False, 'message': f'Avisamos al cliente y a tu equipo que llegas {minutos} min tarde.'}
                elif action == 'guia_vista':
                    pref.primer_ingreso_visto = True
                    pref.save(request)
                    res_json = {'error': False}
                else:
                    raise ValueError('Acción no permitida.')
        except ValueError as ex:
            res_json = [{'error': True, 'message': str(ex)}]
        except Cita.DoesNotExist:
            res_json = [{'error': True, 'message': 'Esa cita no es tuya.'}]
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json = [{'error': True, 'message': 'Intente nuevamente.'}]
        return JsonResponse(res_json, safe=False)
    elif request.method == 'GET':
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'pendientes':
                return JsonResponse({'result': True, 'data': alertas_pendientes(request.user), 'minutos': pref.aviso_previo_min})
            return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
        solo = request.GET.get('solo', 'nuevas')
        listado = Notificacion.objects.filter(status=True, destinatario=request.user).order_by('-fecha_registro')
        if solo == 'nuevas':
            listado = listado.filter(leido=False)
        data.update({'pref': pref, 'solo': solo, 'nuevas': Notificacion.objects.filter(status=True, destinatario=request.user, leido=False).count()})
        data['url_vars'] = f'&solo={solo}'
        paginador(request, listado, 20, data, data['url_vars'])
        return render(request, 'agenda/alertas/listado.html', data)
