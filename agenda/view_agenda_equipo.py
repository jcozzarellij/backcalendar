import sys
from collections import Counter
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
from .funciones_asignacion import es_por_persona, espacios_equipo_rango, organizador_para
from .funciones_citas import crear_cita, obtener_o_crear_cliente
from .funciones_disponibilidad import ocupacion_rango
from .funciones_permisos import equipos_visibles
from .funciones_turnos import duracion_turno
from .models import Cita, Equipo

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
                    inicio = d['inicio']
                    fin = inicio + timedelta(minutes=d['duracion'])
                    organizador = organizador_para(equipo, inicio, fin, respaldo=request.user)
                    cita = crear_cita(cliente=cliente, inicio=inicio, fin=fin,
                                      organizador=organizador, titulo=d['titulo'], equipo=equipo, proyecto=equipo.proyecto,
                                      producto=d.get('producto'), asignada_por='coordinador', plataforma=d['plataforma'],
                                      request=request)
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
        vista = request.GET.get('vista') or request.COOKIES.get('ae_vista') or 'dia'
        if vista not in ('dia', 'semana', 'mes'):
            vista = 'dia'
        desde, hasta, anterior, siguiente = _rango(vista, fecha)
        miembros = list(equipo.miembros.filter(status=True).select_related('usuario').order_by('rol', 'usuario__first_name')) if equipo else []
        disponibles = espacios_equipo_rango(equipo, desde, hasta, paso) if equipo else {}
        data.update({
            'equipos': equipos, 'equipo': equipo, 'fecha_sel': fecha, 'vista': vista, 'desde': desde, 'hasta': hasta,
            'anterior': anterior, 'siguiente': siguiente, 'paso': paso, 'hoy': date.today(),
            'por_persona': es_por_persona(equipo), 'hay_miembros': bool(miembros),
        })
        if vista == 'mes':
            data['semanas'] = _mes(equipo, fecha, desde, hasta, disponibles) if equipo else []
        else:
            ocupacion = {m.usuario_id: ocupacion_rango(m.usuario, desde, hasta) for m in miembros}
            if vista == 'dia':
                data.update(_dia(fecha, paso, miembros, ocupacion, disponibles.get(fecha, [])))
            else:
                data.update(_semana(desde, hasta, paso, miembros, ocupacion, disponibles))
        respuesta = render(request, 'agenda/agenda_equipo/listado.html', data)
        if request.GET.get('vista') == vista:
            respuesta.set_cookie('ae_vista', vista, max_age=60 * 60 * 24 * 365, samesite='Lax')
        return respuesta


def _rango(vista, fecha):
    if vista == 'dia':
        return fecha, fecha, fecha - timedelta(days=1), fecha + timedelta(days=1)
    if vista == 'semana':
        lunes = fecha - timedelta(days=fecha.weekday())
        return lunes, lunes + timedelta(days=6), lunes - timedelta(days=7), lunes + timedelta(days=7)
    primero = fecha.replace(day=1)
    ultimo = (primero.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    desde = primero - timedelta(days=primero.weekday())
    hasta = ultimo + timedelta(days=6 - ultimo.weekday())
    return desde, hasta, (primero - timedelta(days=1)).replace(day=1), ultimo + timedelta(days=1)


def _estado(bloques, inicio, fin):
    """Estado de una franja para una persona: lo ocupado manda sobre el turno."""
    for b in bloques:
        if b['tipo'] != 'turno' and b['inicio'] < fin and b['fin'] > inicio:
            return b['tipo'], b
    if any(b['tipo'] == 'turno' and b['inicio'] <= inicio and b['fin'] >= fin for b in bloques):
        return 'libre', None
    return 'fuera', None


def _dia(fecha, paso, miembros, ocupacion, disponibles):
    salto = timedelta(minutes=paso)
    horas = []
    actual = datetime.combine(fecha, datetime.min.time()).replace(hour=HORA_INICIO)
    while actual + salto <= actual.replace(hour=HORA_FIN):
        horas.append(actual)
        actual += salto
    filas = []
    for m in miembros:
        bloques = ocupacion[m.usuario_id][fecha]
        celdas = []
        for h in horas:
            estado, bloque = _estado(bloques, h, h + salto)
            celdas.append({'hora': h, 'estado': estado, 'cita': (bloque or {}).get('cita'), 'reunion': (bloque or {}).get('reunion')})
        filas.append({'miembro': m, 'celdas': celdas})
    comunes = {h.strftime('%H:%M') for h in disponibles}
    return {'horas': horas, 'filas': filas, 'comunes': comunes, 'num_comunes': len(comunes)}


def _semana(desde, hasta, paso, miembros, ocupacion, disponibles):
    dias = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
    filas = []
    for m in miembros:
        celdas = []
        for d in dias:
            bloques = ocupacion[m.usuario_id][d]
            turno = sum((b['fin'] - b['inicio']).total_seconds() for b in bloques if b['tipo'] == 'turno') / 60
            ocupado = [b for b in bloques if b['tipo'] != 'turno']
            dentro = sum(_solape(b, bloques) for b in ocupado) / 60
            horas_libres, minutos_libres = divmod(max(0, int(turno - dentro)), 60)
            libre = ' '.join(t for t in (f'{horas_libres} h' if horas_libres else '', f'{minutos_libres} min' if minutos_libres else '') if t)
            celdas.append({'fecha': d, 'items': ocupado, 'libre': f'{libre} libres' if libre else 'Sin espacio libre',
                           'con_turno': turno > 0})
        filas.append({'miembro': m, 'celdas': celdas})
    totales = [{'fecha': d, 'disponibles': len(disponibles.get(d, []))} for d in dias]
    por_dia = [{'fecha': d, 'disponibles': totales[i]['disponibles'],
                'personas': [{'miembro': f['miembro'], 'celda': f['celdas'][i]} for f in filas]} for i, d in enumerate(dias)]
    return {'dias': dias, 'filas_semana': filas, 'totales': totales, 'por_dia': por_dia}


def _solape(bloque, bloques):
    """Segundos de `bloque` que caen dentro de algún turno declarado."""
    return sum(max(0, (min(bloque['fin'], t['fin']) - max(bloque['inicio'], t['inicio'])).total_seconds())
               for t in bloques if t['tipo'] == 'turno')


def _mes(equipo, fecha, desde, hasta, disponibles):
    rango_ini = datetime.combine(desde, datetime.min.time())
    rango_fin = datetime.combine(hasta, datetime.min.time()) + timedelta(days=1)
    citas = Counter(Cita.objects.filter(status=True, equipo=equipo, inicio__gte=rango_ini, inicio__lt=rango_fin)
                    .exclude(estado='cancelada').values_list('inicio__date', flat=True))
    dias = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
    celdas = [{'fecha': d, 'citas': citas.get(d, 0), 'disponibles': len(disponibles.get(d, [])),
               'otro_mes': d.month != fecha.month, 'hoy': d == date.today()} for d in dias]
    return [celdas[i:i + 7] for i in range(0, len(celdas), 7)]
