import sys
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
from .forms import CitaRapidaForm
from .funciones_citas import crear_cita, obtener_o_crear_cliente, responsables_de
from .funciones_disponibilidad import espacios_comunes, ocupacion_del_dia
from .funciones_permisos import equipos_visibles
from .funciones_turnos import duracion_turno
from .models import Equipo

HORA_INICIO = 7
HORA_FIN = 20


@login_required
@secure_module
def agendaEquipoView(request):
    data = {
        'titulo': 'Agenda del equipo',
        'descripcion': 'Un carril por persona: turnos, citas y lo ocupado en Google. Los espacios comunes se pueden agendar.',
        'modulo': 'Agenda',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)
    equipos = equipos_visibles(request.user).select_related('proyecto', 'lider').order_by('proyecto__nombre', 'nombre')
    elegido = request.GET.get('equipo') or request.POST.get('equipo') or ''
    equipo = equipos.filter(pk=int(elegido)).first() if elegido.isdigit() else equipos.first()
    texto_fecha = request.GET.get('fecha') or request.POST.get('fecha') or ''
    try:
        fecha = datetime.strptime(texto_fecha, '%Y-%m-%d').date() if texto_fecha else date.today()
    except ValueError:
        fecha = date.today()
    paso = duracion_turno()
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            if equipo is None:
                raise ValueError('Elige un equipo.')
            with transaction.atomic():
                if action == 'agendar':
                    form = CitaRapidaForm(request.POST, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    d = form.cleaned_data
                    cliente = obtener_o_crear_cliente(d['nombres'], d['correo'], d.get('telefono', ''), None, request)
                    organizador = equipo.lider or equipo.proyecto.lider or request.user
                    inicio = d['inicio']
                    cita = crear_cita(cliente=cliente, inicio=inicio, fin=inicio + timedelta(minutes=d['duracion']),
                                      organizador=organizador, titulo=d['titulo'], equipo=equipo, proyecto=equipo.proyecto,
                                      producto=d.get('producto'), asignada_por='coordinador', request=request)
                    log(f'Agendó la cita {cita.codigo} para {equipo}', request, 'add', obj=cita.id)
                    messages.success(request, f'Cita {cita.codigo} creada para el {inicio:%d/%m/%Y %H:%M}.')
                    res_json.append({'error': False, 'to': f'/agenda/citas/{cita.pk}/'})
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
                if action == 'agendar':
                    inicio = request.GET.get('inicio', '')
                    nombre_equipo = equipo.nombre if equipo else ''
                    data['form'] = CitaRapidaForm(initial={'inicio': inicio, 'duracion': paso,
                                                           'titulo': f'Cita con {nombre_equipo}'.strip()})
                    data['usuario_param'] = None
                    template = get_template('agenda/parciales/form_campos.html')
                    html = template.render(data)
                    html += f'<input type="hidden" name="equipo" value="{equipo.pk if equipo else ""}">'
                    return JsonResponse({'result': True, 'data': html})
                return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
            except Exception as ex:
                salva_logs(request, __file__, request.method, action, type(ex).__name__,
                           'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
                return JsonResponse({'result': False, 'message': 'No se pudo cargar el formulario.'})
        horas = []
        actual = datetime.combine(fecha, datetime.min.time()).replace(hour=HORA_INICIO)
        tope = actual.replace(hour=HORA_FIN)
        while actual + timedelta(minutes=paso) <= tope:
            horas.append(actual)
            actual += timedelta(minutes=paso)
        filas = []
        comunes = set()
        if equipo:
            miembros = list(equipo.miembros.filter(status=True).select_related('usuario').order_by('rol', 'usuario__first_name'))
            responsables = responsables_de(equipo)
            comunes = {h.strftime('%H:%M') for h in espacios_comunes(responsables, fecha, paso)}
            for m in miembros:
                bloques = ocupacion_del_dia(m.usuario, fecha)
                celdas = []
                for h in horas:
                    fin = h + timedelta(minutes=paso)
                    estado, cita = 'fuera', None
                    if any(b['tipo'] == 'turno' and b['inicio'] <= h and b['fin'] >= fin for b in bloques):
                        estado = 'libre'
                    for b in bloques:
                        if b['tipo'] != 'turno' and b['inicio'] < fin and b['fin'] > h:
                            estado = 'cita' if b['tipo'] == 'cita' else b['tipo']
                            cita = b.get('cita')
                            break
                    celdas.append({'hora': h, 'estado': estado, 'cita': cita})
                filas.append({'miembro': m, 'celdas': celdas})
        data.update({
            'equipos': equipos, 'equipo': equipo, 'fecha_sel': fecha, 'anterior': fecha - timedelta(days=1),
            'siguiente': fecha + timedelta(days=1), 'horas': horas, 'filas': filas, 'comunes': comunes,
            'paso': paso, 'num_comunes': len(comunes),
        })
        return render(request, 'agenda/agenda_equipo/listado.html', data)
