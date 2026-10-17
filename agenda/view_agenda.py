import math
import sys
from datetime import date, datetime, time, timedelta

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
from . import funciones_reuniones
from .forms import CitaRapidaForm, ReunionForm
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
                                      asignada_por='coordinador', plataforma=d['plataforma'], request=request)
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
                elif action in ('reunion', 'editar_reunion'):
                    plataforma = request.POST.get('plataforma', '')
                    todo_el_dia = request.POST.get('todo_el_dia') == '1'
                    form = ReunionForm(request.POST, todo_el_dia=todo_el_dia, creando=action == 'reunion')
                    if not form.is_valid():
                        raise FormError(form)
                    d = form.cleaned_data
                    if action == 'reunion':
                        funciones_reuniones.crear(request.user, plataforma, d, request)
                        log(f'Creó la reunión «{d["titulo"]}» en {plataforma} desde su agenda', request, 'add')
                        messages.success(request, f'Reunión «{d["titulo"]}» creada en tu calendario.')
                    else:
                        funciones_reuniones.editar(request.user, plataforma, request.POST.get('evento', ''), d, todo_el_dia, request)
                        log(f'Editó la reunión «{d["titulo"]}» de {plataforma} desde su agenda', request, 'change')
                        messages.success(request, f'Reunión «{d["titulo"]}» actualizada.')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'mover_reunion':
                    inicio = datetime.strptime(request.POST['inicio'][:16], '%Y-%m-%dT%H:%M')
                    fin = datetime.strptime(request.POST['fin'][:16], '%Y-%m-%dT%H:%M')
                    funciones_reuniones.mover(request.user, request.POST.get('plataforma', ''), request.POST.get('id', ''), inicio, fin, request)
                    log(f'Movió una reunión de {request.POST.get("plataforma", "")} al {inicio:%d/%m/%Y %H:%M}', request, 'change')
                    res_json.append({'error': False, 'message': f'Reunión movida al {inicio:%d/%m %H:%M}.'})
                elif action == 'eliminar_reunion':
                    funciones_reuniones.eliminar(request.user, request.POST.get('plataforma', ''), request.POST.get('id', ''), request)
                    log(f'Eliminó una reunión de {request.POST.get("plataforma", "")} desde su agenda', request, 'del')
                    messages.success(request, 'Reunión eliminada de tu calendario.')
                    res_json.append({'error': False})
                elif action == 'reintentar_reunion':
                    funciones_reuniones.reintentar(request.user, request.POST.get('id', ''))
                    messages.success(request, 'Reunión sincronizada con la plataforma.')
                    res_json.append({'error': False})
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
                if action in ('reunion', 'editar_reunion'):
                    plataforma = request.GET.get('plataforma', 'google')
                    data['plataforma'] = next((p for p in funciones_reuniones.plataformas_de(request.user) if p['clave'] == plataforma), None)
                    if data['plataforma'] is None or not data['plataforma']['disponible']:
                        return JsonResponse({'result': False, 'message': 'Esa plataforma todavía no está disponible para ti.'})
                    if action == 'reunion':
                        inicio = request.GET.get('inicio', '')[:16]
                        data['form'] = ReunionForm(initial={'inicio': inicio, 'duracion': request.GET.get('duracion') or 30})
                    else:
                        try:
                            evento = funciones_reuniones.para_editar(request.user, plataforma, request.GET.get('evento', ''))
                        except ValueError as ex:
                            return JsonResponse({'result': False, 'message': str(ex)})
                        data['evento'] = evento
                        data['form'] = ReunionForm(todo_el_dia=evento['todo_el_dia'], creando=False, initial={
                            'titulo': evento['titulo'], 'inicio': evento['inicio'].strftime('%Y-%m-%dT%H:%M'),
                            'duracion': max(5, int((evento['fin'] - evento['inicio']).total_seconds() // 60)),
                            'color': evento['color_id'], 'lugar': evento['lugar'], 'descripcion': evento['descripcion'],
                            'invitados': ', '.join(evento['invitados']),
                        })
                    data['accion_form'] = action
                    template = get_template('agenda/agenda/form_reunion.html')
                    return JsonResponse({'result': True, 'data': template.render(data, request)})
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
        inicio_rango = datetime.combine(desde, datetime.min.time())
        fin_rango = datetime.combine(hasta, datetime.min.time())
        citas = list(citas_del_usuario(request.user, inicio_rango, fin_rango))
        mapa = {}
        proyectos = {}
        for c in citas:
            idx = _color(c.proyecto_id, mapa)
            c.color_fondo, c.color_borde = PALETA[idx], PALETA_BORDE[idx]
            if c.proyecto_id and c.proyecto_id not in proyectos:
                proyectos[c.proyecto_id] = {'nombre': c.proyecto.nombre, 'fondo': PALETA[idx], 'borde': PALETA_BORDE[idx]}
        eventos, data['google_conectado'], data['google_error'] = funciones_reuniones.agenda_externa(
            request.user, inicio_rango, fin_rango, excluir=[c.google_event_id for c in citas],
            refrescar=request.GET.get('google') == 'actualizar')
        data['plataformas'] = funciones_reuniones.plataformas_de(request.user)
        items = [{'inicio': c.inicio, 'fin': c.fin, 'cita': c} for c in citas]
        items += [{'inicio': e['inicio'], 'fin': e['fin'], 'evento': e} for e in eventos if not e['todo_el_dia']]
        de_todo_el_dia = [e for e in eventos if e['todo_el_dia']]
        horas = _horas(dias, items, paso) if vista != 'mes' else []
        columnas = []
        for d in dias:
            franjas = franjas_del_dia(request.user, d)
            del_dia = [dict(i) for i in items if _toca(i, d)]
            completos = [e for e in de_todo_el_dia if _toca(e, d)]
            columnas.append({'fecha': d, 'celdas': _celdas(d, horas, paso, franjas, del_dia), 'hoy': d == date.today(),
                             'otro_mes': vista == 'mes' and d.month != fecha.month, 'todo_el_dia': completos,
                             'items': [{'evento': e} for e in completos] + [i for i in del_dia if i['inicio'].date() == d],
                             'libre': bool(franjas)})
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
            'hay_todo_el_dia': any(col['todo_el_dia'] for col in columnas),
            'cola': cola, 'hoy': date.today(),
        })
        respuesta = render(request, 'agenda/agenda/listado.html', data)
        if request.GET.get('vista') == vista:
            respuesta.set_cookie('cal_vista', vista, max_age=60 * 60 * 24 * 365, samesite='Lax')
        return respuesta


def _toca(item, dia):
    inicio_dia = datetime.combine(dia, datetime.min.time())
    return item['inicio'] < inicio_dia + timedelta(days=1) and item['fin'] > inicio_dia


def _horas(dias, items, paso):
    """Franjas de la rejilla: de HORA_INICIO a HORA_FIN, ampliadas de a un paso para que entre todo lo del rango."""
    primero, ultimo = HORA_INICIO * 60, 0
    for d in dias:
        inicio_dia = datetime.combine(d, datetime.min.time())
        for item in items:
            if _toca(item, d):
                primero = min(primero, (max(item['inicio'], inicio_dia) - inicio_dia).total_seconds() / 60)
                ultimo = max(ultimo, (min(item['fin'], inicio_dia + timedelta(days=1)) - inicio_dia).total_seconds() / 60)
    desde = HORA_INICIO * 60
    while desde > primero and desde - paso >= 0:
        desde -= paso
    horas = []
    while desde + paso <= 24 * 60 and (desde + paso <= HORA_FIN * 60 or desde < ultimo):
        horas.append(time(desde // 60, desde % 60))
        desde += paso
    return horas


def _celdas(dia, horas, paso, franjas, items):
    """Celdas de un día de la rejilla. Lo que se solapa o comparte franja forma un bloque con rowspan; dentro,
    cada cita o evento va en su carril, con su posición en porcentaje del bloque."""
    if not horas:
        return []
    salto = timedelta(minutes=paso)
    base = datetime.combine(dia, horas[0])
    total = len(horas)
    grupos = []
    for item in sorted(items, key=lambda i: (i['inicio'], i['fin'])):
        a = max(0, math.floor((item['inicio'] - base) / salto))
        b = min(total - 1, math.ceil((item['fin'] - base) / salto) - 1)
        if a >= total or b < 0:
            continue
        b = max(a, b)
        if grupos and a <= grupos[-1]['b']:
            grupos[-1]['b'] = max(grupos[-1]['b'], b)
            grupos[-1]['items'].append(item)
        else:
            grupos.append({'a': a, 'b': b, 'items': [item]})
    for g in grupos:
        _repartir(g['items'], base + g['a'] * salto, (g['b'] - g['a'] + 1) * salto)
    por_inicio = {g['a']: g for g in grupos}
    cubiertas = {n for g in grupos for n in range(g['a'] + 1, g['b'] + 1)}
    celdas = []
    for n, h in enumerate(horas):
        ini = datetime.combine(dia, h)
        grupo = por_inicio.get(n)
        celdas.append({
            'inicio': ini,
            'en_turno': any(datetime.combine(dia, a) <= ini and datetime.combine(dia, b) >= ini + salto for a, b in franjas),
            'grupo': grupo,
            'filas': grupo['b'] - grupo['a'] + 1 if grupo else 1,
            'ocupada': n in cubiertas,
        })
    return celdas


def _repartir(items, inicio, largo):
    carriles = []
    for item in items:
        carril = next((n for n, fin in enumerate(carriles) if fin <= item['inicio']), len(carriles))
        if carril == len(carriles):
            carriles.append(item['fin'])
        else:
            carriles[carril] = item['fin']
        item['carril'] = carril
    ancho = 100 / len(carriles)
    for item in items:
        arriba = max(item['inicio'] - inicio, timedelta(0)) / largo * 100
        abajo = min(item['fin'] - inicio, largo) / largo * 100
        item['estilo'] = (f'top: {arriba:.2f}%; height: calc({max(abajo - arriba, 0):.2f}% - 2px); '
                          f'left: calc({item["carril"] * ancho:.2f}% + 1px); width: calc({ancho:.2f}% - 2px)')
