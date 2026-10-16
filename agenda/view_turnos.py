import json
import sys
from calendar import monthrange
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from core.custom_models import FormError
from core.funciones import addData, log, secure_module
from core.funciones_adicionales import salva_logs
from .forms import ExcepcionTurnoForm
from .funciones_permisos import es_lider_general, equipos_que_lidera, puede_editar_turnos_de
from .funciones_turnos import (aplicar_semana_tipo, celdas_a_franjas, duracion_turno, franjas_a_celdas,
                               horas_rejilla, patron_vigente)
from autenticacion.models import Usuario
from .models import DIA_SEMANA, ExcepcionTurno

ALCANCES = (
    ('sin_fin', 'Sin fecha de fin'),
    ('este_mes', 'Este mes'),
    ('tres_meses', 'Próximos 3 meses'),
    ('fin_anio', 'Hasta fin de año'),
    ('rango', 'Entre dos fechas'),
)


@login_required
@secure_module
def turnosView(request):
    administrar = request.path.rstrip('/').endswith('turnos-equipo')
    data = {
        'titulo': 'Horarios del equipo' if administrar else 'Horarios',
        'descripcion': ('Revisa y ajusta la semana tipo de cada persona de tu equipo.' if administrar
                        else 'Define tu semana una sola vez; solo se asignan citas dentro de estos espacios.'),
        'modulo': 'Agenda',
        'ruta': request.path,
        'fecha': str(date.today()),
        'administrar': administrar,
    }
    addData(request, data)
    usuario = request.user
    elegido = request.GET.get('usuario') or request.POST.get('usuario') or ''
    if administrar and elegido.isdigit():
        candidato = Usuario.objects.filter(pk=int(elegido), is_active=True).first()
        if candidato and puede_editar_turnos_de(request.user, candidato):
            usuario = candidato
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'guardarsemana':
                    paso = duracion_turno()
                    celdas = json.loads(request.POST.get('celdas') or '{}')
                    if not isinstance(celdas, dict) or any(int(d) not in range(7) for d in celdas):
                        raise ValueError('La semana enviada no es válida.')
                    validas = {h.strftime('%H:%M') for h in horas_rejilla(paso)}
                    if any(h not in validas for horas in celdas.values() for h in horas):
                        raise ValueError('Hay espacios fuera de la rejilla; recarga la página.')
                    hoy = date.today()
                    alcance = request.POST.get('alcance', 'sin_fin')
                    desde, hasta = hoy, None
                    if alcance == 'este_mes':
                        hasta = hoy.replace(day=monthrange(hoy.year, hoy.month)[1])
                    elif alcance == 'tres_meses':
                        hasta = hoy + timedelta(days=91)
                    elif alcance == 'fin_anio':
                        hasta = date(hoy.year, 12, 31)
                    elif alcance == 'rango':
                        try:
                            desde = datetime.strptime(request.POST['desde'], '%Y-%m-%d').date()
                            hasta = datetime.strptime(request.POST['hasta'], '%Y-%m-%d').date()
                        except (KeyError, ValueError):
                            raise ValueError('Indica las dos fechas del rango.')
                        if desde < hoy:
                            raise ValueError('El rango no puede empezar en el pasado.')
                    elif alcance != 'sin_fin':
                        raise ValueError('Elige hasta cuándo aplica.')
                    patron = aplicar_semana_tipo(usuario, celdas_a_franjas(celdas, paso), desde, hasta, request)
                    log(f'Guardó la semana tipo de {usuario} ({patron})', request, 'add', obj=patron.id)
                    messages.success(request, 'Semana tipo guardada')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'addexcepcion':
                    form = ExcepcionTurnoForm(request.POST, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.instance.usuario = usuario
                    form.save()
                    log(f'Registró la excepción {form.instance} de {usuario}', request, 'add', obj=form.instance.id)
                    messages.success(request, 'Excepción registrada')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'delete':
                    filtro = ExcepcionTurno.objects.get(pk=int(request.POST['id']), usuario=usuario, status=True)
                    filtro.status = False
                    filtro.save(request)
                    log(f'Quitó la excepción {filtro} de {usuario}', request, 'del', obj=filtro.id)
                    messages.success(request, 'Excepción quitada')
                    res_json = {'error': False}
                else:
                    raise ValueError('Acción no permitida.')
        except ValueError as ex:
            res_json = [{'error': True, 'message': str(ex)}]
        except FormError as ex:
            res_json = [ex.dict_error]
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json = [{'error': True, 'message': 'Intente nuevamente.'}]
        return JsonResponse(res_json, safe=False)
    elif request.method == 'GET':
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            try:
                if action == 'addexcepcion':
                    data['form'] = ExcepcionTurnoForm()
                    if usuario != request.user:
                        data['usuario_param'] = usuario.pk
                    template = get_template('agenda/parciales/form_campos.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
            except Exception as ex:
                salva_logs(request, __file__, request.method, action, type(ex).__name__,
                           'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
                return JsonResponse({'result': False, 'message': 'No se pudo cargar el formulario.'})
        data['usuario_turnos'] = usuario
        if administrar:
            if es_lider_general(request.user):
                data['usuarios'] = Usuario.objects.filter(is_active=True, is_staff=True).order_by('first_name', 'last_name')
            else:
                del_equipo = equipos_que_lidera(request.user).values_list('miembros__usuario_id', flat=True)
                ids = {request.user.pk} | {i for i in del_equipo if i}
                data['usuarios'] = Usuario.objects.filter(pk__in=ids, is_active=True).order_by('first_name', 'last_name')
        paso = duracion_turno()
        patron = patron_vigente(usuario, date.today())
        data['paso'] = paso
        data['horas'] = [h.strftime('%H:%M') for h in horas_rejilla(paso)]
        data['dias'] = DIA_SEMANA
        data['patron'] = patron
        data['celdas'] = franjas_a_celdas(patron, paso)
        data['alcances'] = ALCANCES
        data['proximos'] = usuario.patrones_turno.filter(status=True, vigencia_desde__gt=date.today()).order_by('vigencia_desde')
        data['excepciones'] = usuario.excepciones_turno.filter(status=True, fecha_hasta__gte=date.today()).order_by('fecha_desde')
        return render(request, 'agenda/turnos/listado.html', data)
