import sys
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from core.custom_models import FormError
from core.funciones import addData, log, paginador, secure_module
from core.funciones_adicionales import salva_logs
from .forms import CitaRapidaForm, SolicitudForm
from .funciones_citas import crear_cita, responsables_de
from .funciones_disponibilidad import primer_espacio
from .funciones_permisos import equipos_visibles, es_admin_proyectos
from .funciones_portal import tiempos_de
from .models import ESTADO_SOLICITUD, Equipo, Solicitud


@login_required
@secure_module
def solicitudView(request):
    data = {
        'titulo': 'Solicitudes',
        'descripcion': 'Pedidos de cita que esperan horario: asígnales equipo y fecha o ciérralos.',
        'modulo': 'Agenda',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)
    model = Solicitud
    Formulario = SolicitudForm
    visibles = equipos_visibles(request.user)
    todo = es_admin_proyectos(request.user)
    base = model.objects.filter(status=True) if todo else model.objects.filter(
        status=True).filter(Q(equipo__in=visibles) | Q(equipo__isnull=True))
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'add':
                    form = Formulario(request.POST, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    from .funciones_citas import codigo_solicitud
                    form.instance.codigo = codigo_solicitud()
                    form.instance.estado = 'en_cola'
                    form.instance.causa_cola = 'Creada desde el panel'
                    form.save()
                    log(f'Registró la solicitud {form.instance.codigo}', request, 'add', obj=form.instance.id)
                    messages.success(request, 'Solicitud registrada en la cola')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'change':
                    filtro = base.get(pk=int(request.POST['pk']))
                    form = Formulario(request.POST, instance=filtro, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    log(f'Editó la solicitud {filtro.codigo}', request, 'change', obj=filtro.id)
                    messages.success(request, 'Solicitud actualizada')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'asignar':
                    filtro = base.select_for_update().get(pk=int(request.POST['pk']), estado='en_cola')
                    form = CitaRapidaForm(request.POST, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    d = form.cleaned_data
                    equipo_pk = request.POST.get('equipo', '')
                    equipo = visibles.filter(pk=int(equipo_pk)).first() if equipo_pk.isdigit() else filtro.equipo
                    if equipo is None:
                        raise ValueError('Elige el equipo que atenderá la solicitud.')
                    organizador = equipo.lider or equipo.proyecto.lider or request.user
                    inicio = d['inicio']
                    cita = crear_cita(cliente=filtro.cliente, inicio=inicio, fin=inicio + timedelta(minutes=d['duracion']),
                                      organizador=organizador, titulo=d['titulo'], equipo=equipo, proyecto=equipo.proyecto,
                                      producto=d.get('producto') or filtro.producto, solicitud=filtro,
                                      asignada_por='coordinador', idioma=filtro.cliente.idioma, request=request)
                    log(f'Asignó la solicitud {filtro.codigo} a la cita {cita.codigo}', request, 'change', obj=filtro.id)
                    messages.success(request, f'Cita {cita.codigo} creada para el {inicio:%d/%m/%Y %H:%M}.')
                    res_json.append({'error': False, 'to': f'/agenda/citas/{cita.pk}/'})
                elif action == 'cerrar':
                    filtro = base.get(pk=int(request.POST['id']), estado='en_cola')
                    filtro.estado = 'cerrada'
                    filtro.causa_cola = (request.POST.get('motivo') or 'Cerrada sin cita')[:200]
                    filtro.save(request)
                    log(f'Cerró la solicitud {filtro.codigo} sin cita', request, 'change', obj=filtro.id)
                    messages.success(request, 'Solicitud cerrada')
                    res_json = {'error': False}
                elif action == 'delete':
                    filtro = base.get(pk=int(request.POST['id']))
                    if filtro.estado == 'asignada':
                        raise ValueError('Tiene una cita asignada: cancela la cita primero.')
                    filtro.status = False
                    filtro.save(request)
                    log(f'Eliminó la solicitud {filtro.codigo}', request, 'del', obj=filtro.id)
                    messages.success(request, 'Solicitud eliminada')
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
                if action == 'add':
                    data['form'] = Formulario()
                    template = get_template('agenda/parciales/form_campos.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                elif action == 'change':
                    data['pk'] = pk = int(request.GET['pk'])
                    data['form'] = Formulario(instance=base.get(pk=pk))
                    template = get_template('agenda/parciales/form_campos.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                elif action == 'asignar':
                    data['pk'] = pk = int(request.GET['pk'])
                    solicitud = base.select_related('cliente', 'producto', 'equipo').get(pk=pk, estado='en_cola')
                    equipo = solicitud.equipo
                    if equipo is None and solicitud.producto_id:
                        equipo = solicitud.producto.equipo
                    sugerido, duracion = None, None
                    if equipo is not None:
                        t = tiempos_de(solicitud.producto) if solicitud.producto_id else None
                        duracion = t['duracion'] if t else None
                        sugerido = primer_espacio(responsables_de(equipo), datetime.now(), duracion=duracion,
                                                  margen=t['margen'] if t else 0, antelacion_horas=0)
                    data['form'] = CitaRapidaForm(initial={
                        'nombres': solicitud.cliente.nombres, 'correo': solicitud.cliente.correo,
                        'telefono': solicitud.cliente.telefono, 'producto': solicitud.producto,
                        'titulo': f'{solicitud.producto.nombre if solicitud.producto_id else "Cita"} · {solicitud.cliente.nombres}'[:200],
                        'inicio': request.GET.get('inicio', '')[:16] or (sugerido.strftime('%Y-%m-%dT%H:%M') if sugerido else ''),
                        'duracion': duracion or 40})
                    for campo in ('nombres', 'correo', 'telefono'):
                        data['form'].fields[campo].widget.attrs['readonly'] = True
                    data['equipos'] = visibles.select_related('proyecto')
                    data['equipo_sel'] = equipo
                    data['sugerido'] = sugerido
                    template = get_template('agenda/solicitud/form_asignar.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
            except Exception as ex:
                salva_logs(request, __file__, request.method, action, type(ex).__name__,
                           'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
                return JsonResponse({'result': False, 'message': 'No se pudo cargar el formulario.'})
        criterio, estado, url_vars = request.GET.get('criterio', '').strip(), request.GET.get('estado', 'en_cola'), ''
        filtros = Q()
        if criterio:
            filtros &= (Q(codigo__icontains=criterio) | Q(cliente__nombres__icontains=criterio) |
                        Q(cliente__correo__icontains=criterio) | Q(motivo__icontains=criterio))
            data['criterio'] = criterio
            url_vars += '&criterio=' + criterio
        if estado:
            filtros &= Q(estado=estado)
            url_vars += '&estado=' + estado
        data['estado'] = estado
        data['estados'] = ESTADO_SOLICITUD
        if request.GET.get('vista') == 'tablero':
            tablero = base.select_related('cliente', 'producto', 'equipo').prefetch_related('citas').order_by('-fecha_registro')
            data['columnas'] = [
                {'clave': 'en_cola', 'nombre': 'En cola', 'items': list(tablero.filter(estado='en_cola')), 'vacio': 'La cola está vacía.'},
                {'clave': 'asignada', 'nombre': 'Con cita', 'items': list(tablero.filter(estado='asignada')[:40]), 'vacio': 'Ninguna con cita asignada.'},
                {'clave': 'cerrada', 'nombre': 'Cerradas', 'items': list(tablero.filter(estado__in=('cerrada', 'realizada', 'cancelada'))[:40]), 'vacio': 'Nada cerrado todavía.'},
            ]
            return render(request, 'agenda/solicitud/tablero.html', data)
        listado = base.filter(filtros).select_related('cliente', 'producto', 'equipo', 'proyecto').order_by('fecha_registro')
        data['en_cola'] = base.filter(estado='en_cola').count()
        data['list_count'] = listado.count()
        data['url_vars'] = url_vars
        paginador(request, listado, 20, data, url_vars)
        return render(request, 'agenda/solicitud/listado.html', data)
