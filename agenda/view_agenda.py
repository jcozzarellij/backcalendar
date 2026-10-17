import sys
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.utils.formats import date_format

from core.custom_models import FormError
from core.funciones import addData, log, secure_module
from core.funciones_adicionales import salva_logs
from .forms import CitaRapidaForm
from .funciones_citas import citas_del_usuario, crear_cita, mover_cita, obtener_o_crear_cliente
from .funciones_permisos import equipos_visibles, es_admin_proyectos
from .funciones_turnos import duracion_turno, franjas_del_dia
from .models import Cita, Equipo, Solicitud

PALETA = ['#dbe9f4', '#e7f3d9', '#f3e6f7', '#fdebd3', '#e0f2f1', '#f1e5d8']
PALETA_BORDE = ['#005082', '#4f8f00', '#7b3fa0', '#b45309', '#00796b', '#8a5a2b']
HORA_INICIO = 7
HORA_FIN = 20


def _lunes(fecha):
    return fecha - timedelta(days=fecha.weekday())


def _color(proyecto_id, mapa):
    if proyecto_id not in mapa:
        mapa[proyecto_id] = len(mapa) % len(PALETA)
    return mapa[proyecto_id]


@login_required
@secure_module
def agendaView(request):
    data = {
        'titulo': 'Mi agenda',
        'descripcion': 'Arrastra una cita a otro espacio para reprogramarla, o una solicitud de la cola para asignarla. Haz clic en una cita para ver sus acciones.',
        'modulo': 'Agenda',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)
    mis_equipos = Equipo.objects.filter(status=True, activo=True, miembros__status=True, miembros__usuario=request.user).select_related('proyecto').distinct()
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'agendar':
                    form = CitaRapidaForm(request.POST, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    d = form.cleaned_data
                    equipo_pk = request.POST.get('equipo', '')
                    equipo = mis_equipos.filter(pk=int(equipo_pk)).first() if equipo_pk.isdigit() else None
                    cliente = obtener_o_crear_cliente(d['nombres'], d['correo'], d.get('telefono', ''), None, request)
                    inicio = d['inicio']
                    cita = crear_cita(cliente=cliente, inicio=inicio, fin=inicio + timedelta(minutes=d['duracion']),
                                      organizador=request.user, titulo=d['titulo'], equipo=equipo,
                                      proyecto=equipo.proyecto if equipo else None, producto=d.get('producto'),
                                      asignada_por='coordinador', request=request)
                    log(f'Agendó la cita {cita.codigo} desde su agenda', request, 'add', obj=cita.id)
                    messages.success(request, f'Cita {cita.codigo} creada para el {inicio:%d/%m/%Y %H:%M}.')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'mover':
                    cita = Cita.objects.select_for_update().get(pk=int(request.POST['id']), status=True,
                                                                 participantes__usuario=request.user, participantes__status=True)
                    inicio = datetime.strptime(request.POST['inicio'][:16], '%Y-%m-%dT%H:%M')
                    fin = datetime.strptime(request.POST['fin'][:16], '%Y-%m-%dT%H:%M') if request.POST.get('fin') else inicio + (cita.fin - cita.inicio)
                    mover_cita(cita, inicio, fin, request, 'Movida desde el calendario.')
                    log(f'Reprogramó la cita {cita.codigo} a {inicio:%d/%m/%Y %H:%M}', request, 'change', obj=cita.id)
                    res_json.append({'error': False, 'message': f'Cita movida al {inicio:%d/%m %H:%M}.'})
                else:
                    raise ValueError('Acción no permitida.')
        except ValueError as ex:
            res_json = [{'error': True, 'message': str(ex)}]
        except FormError as ex:
            res_json = [ex.dict_error]
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json = [{'error': True, 'message': 'No se pudo completar la acción.'}]
        return JsonResponse(res_json, safe=False)
    elif request.method == 'GET':
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            try:
                if action == 'agendar':
                    inicio = request.GET.get('inicio', '')[:16]
                    try:
                        duracion = int(request.GET.get('duracion') or duracion_turno())
                    except ValueError:
                        duracion = duracion_turno()
                    data['form'] = CitaRapidaForm(initial={'inicio': inicio, 'duracion': duracion})
                    data['equipos'] = mis_equipos
                    template = get_template('agenda/agenda/form_cita.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
            except Exception as ex:
                salva_logs(request, __file__, request.method, action, type(ex).__name__,
                           'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
                return JsonResponse({'result': False, 'message': 'No se pudo cargar el formulario.'})
        vista = request.GET.get('vista') or request.COOKIES.get('cal_vista') or 'semana'
        if vista not in ('dia', 'semana', 'mes'):
            vista = 'semana'
        try:
            fecha = datetime.strptime(request.GET.get('fecha', ''), '%Y-%m-%d').date()
        except ValueError:
            fecha = date.today()
        paso = duracion_turno()
        if vista == 'dia':
            desde, hasta = fecha, fecha + timedelta(days=1)
            dias = [fecha]
            eyebrow = date_format(fecha, r'l j \d\e F \d\e Y')
            anterior, siguiente = fecha - timedelta(days=1), fecha + timedelta(days=1)
        elif vista == 'semana':
            desde = _lunes(fecha)
            hasta = desde + timedelta(days=5)
            dias = [desde + timedelta(days=i) for i in range(5)]
            mes_anio = date_format(desde, r'F \d\e Y')
            eyebrow = f'Semana del {desde.day} al {(hasta - timedelta(days=1)).day} de {mes_anio}'
            anterior, siguiente = desde - timedelta(days=7), desde + timedelta(days=7)
        else:
            primero = fecha.replace(day=1)
            desde = _lunes(primero)
            ultimo = (primero.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            hasta = _lunes(ultimo) + timedelta(days=7)
            dias = [desde + timedelta(days=i) for i in range((hasta - desde).days)]
            eyebrow = date_format(primero, 'F \\d\\e Y')
            anterior = (primero - timedelta(days=1)).replace(day=1)
            siguiente = (primero.replace(day=28) + timedelta(days=4)).replace(day=1)
        citas = list(citas_del_usuario(request.user, datetime.combine(desde, datetime.min.time()), datetime.combine(hasta, datetime.min.time())))
        mapa = {}
        proyectos = {}
        for c in citas:
            idx = _color(c.proyecto_id, mapa)
            c.color_fondo, c.color_borde = PALETA[idx], PALETA_BORDE[idx]
            if c.proyecto_id and c.proyecto_id not in proyectos:
                proyectos[c.proyecto_id] = {'nombre': c.proyecto.nombre, 'fondo': PALETA[idx], 'borde': PALETA_BORDE[idx]}
        horas = []
        if vista != 'mes':
            actual = datetime.combine(desde, datetime.min.time()).replace(hour=HORA_INICIO)
            tope = actual.replace(hour=HORA_FIN)
            while actual + timedelta(minutes=paso) <= tope:
                horas.append(actual.time())
                actual += timedelta(minutes=paso)
        columnas = []
        for d in dias:
            franjas = franjas_del_dia(request.user, d)
            celdas = []
            if vista != 'mes':
                for h in horas:
                    ini = datetime.combine(d, h)
                    fin = ini + timedelta(minutes=paso)
                    en_turno = any(datetime.combine(d, a) <= ini and datetime.combine(d, b) >= fin for a, b in franjas)
                    cita = next((c for c in citas if c.inicio.date() == d and c.inicio.time() == h), None)
                    ocupada = cita is None and any(c.inicio < fin and c.fin > ini for c in citas)
                    filas = max(1, round((cita.fin - cita.inicio).total_seconds() / 60 / paso)) if cita else 1
                    celdas.append({'inicio': ini, 'en_turno': en_turno, 'cita': cita, 'ocupada': ocupada, 'filas': filas})
            columnas.append({'fecha': d, 'celdas': celdas, 'hoy': d == date.today(), 'otro_mes': vista == 'mes' and d.month != fecha.month,
                             'citas': [c for c in citas if c.inicio.date() == d], 'libre': bool(franjas)})
        filas = []
        if vista != 'mes':
            for i, h in enumerate(horas):
                filas.append({'hora': h, 'celdas': [col['celdas'][i] for col in columnas]})
        semanas = [columnas[i:i + 7] for i in range(0, len(columnas), 7)] if vista == 'mes' else []
        cola = []
        if es_admin_proyectos(request.user) or mis_equipos.exists():
            visibles = equipos_visibles(request.user)
            cola = list(Solicitud.objects.filter(status=True, estado='en_cola').filter(equipo__in=visibles) | Solicitud.objects.filter(status=True, estado='en_cola', equipo__isnull=True))
            cola = sorted({s.pk: s for s in cola}.values(), key=lambda s: s.fecha_registro)[:12]
        data.update({
            'vista': vista, 'fecha_sel': fecha, 'eyebrow_agenda': eyebrow.capitalize(), 'anterior': anterior, 'siguiente': siguiente,
            'filas': filas, 'columnas': columnas, 'semanas': semanas, 'paso': paso, 'proyectos': list(proyectos.values()),
            'cola': cola, 'hoy': date.today(),
        })
        respuesta = render(request, 'agenda/agenda/listado.html', data)
        if request.GET.get('vista') == vista:
            respuesta.set_cookie('cal_vista', vista, max_age=60 * 60 * 24 * 365, samesite='Lax')
        return respuesta
