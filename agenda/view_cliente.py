import sys
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from core.custom_models import FormError
from core.funciones import addData, log, paginador, secure_module
from core.funciones_adicionales import salva_logs
from . import funciones_tokens
from .forms import CitaRapidaForm, ClienteForm
from .funciones_citas import codigo_cliente, crear_cita
from .funciones_turnos import duracion_turno
from .models import CapturaTecnica, Cita, Cliente, Equipo, Solicitud


@login_required
@secure_module
def clienteView(request, pk=None):
    data = {
        'titulo': 'Clientes',
        'descripcion': 'Quién nos pidió cita, su historial y quién lo atendió, para darle continuidad.',
        'modulo': 'Agenda',
        'ruta': '/agenda/clientes/',
        'fecha': str(date.today()),
    }
    addData(request, data)
    model = Cliente
    Formulario = ClienteForm
    cliente = None
    if pk is not None:
        cliente = model.objects.filter(pk=pk, status=True).select_related('portal_origen').first()
        if cliente is None:
            raise Http404
    mis_equipos = Equipo.objects.filter(status=True, activo=True, miembros__status=True, miembros__usuario=request.user).select_related('proyecto').distinct()
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'add':
                    form = Formulario(request.POST, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.instance.codigo = codigo_cliente()
                    form.save()
                    log(f'Registró el cliente {form.instance}', request, 'add', obj=form.instance.id)
                    messages.success(request, 'Cliente registrado')
                    res_json.append({'error': False, 'to': f'/agenda/clientes/{form.instance.pk}/'})
                elif action == 'change':
                    filtro = model.objects.get(pk=int(request.POST['pk']), status=True)
                    form = Formulario(request.POST, instance=filtro, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    log(f'Editó el cliente {filtro}', request, 'change', obj=filtro.id)
                    messages.success(request, 'Cliente actualizado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'nota':
                    filtro = model.objects.get(pk=int(request.POST['pk']), status=True)
                    filtro.nota_privada = request.POST.get('texto', '')[:5000]
                    filtro.save(request)
                    res_json.append({'error': False, 'message': 'Nota guardada'})
                elif action == 'agendar':
                    filtro = model.objects.get(pk=int(request.POST['pk']), status=True)
                    form = CitaRapidaForm(request.POST, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    d = form.cleaned_data
                    equipo_pk = request.POST.get('equipo', '')
                    equipo = mis_equipos.filter(pk=int(equipo_pk)).first() if equipo_pk.isdigit() else None
                    inicio = d['inicio']
                    cita = crear_cita(cliente=filtro, inicio=inicio, fin=inicio + timedelta(minutes=d['duracion']),
                                      organizador=request.user, titulo=d['titulo'], equipo=equipo,
                                      proyecto=equipo.proyecto if equipo else None, producto=d.get('producto'),
                                      asignada_por='coordinador', idioma=filtro.idioma, request=request)
                    log(f'Agendó la cita {cita.codigo} para el cliente {filtro}', request, 'add', obj=cita.id)
                    messages.success(request, f'Cita {cita.codigo} creada para el {inicio:%d/%m/%Y %H:%M}.')
                    res_json.append({'error': False, 'to': f'/agenda/citas/{cita.pk}/'})
                elif action == 'enlace':
                    filtro = model.objects.get(pk=int(request.POST['id']), status=True)
                    token = funciones_tokens.emitir('cliente', cliente=filtro, request=request)
                    url = funciones_tokens.url_cliente(filtro.portal_origen, token)
                    log(f'Generó un enlace personal para el cliente {filtro}', request, 'add', obj=filtro.id)
                    res_json = {'error': False, 'url': url}
                elif action == 'delete':
                    filtro = model.objects.get(pk=int(request.POST['id']), status=True)
                    if Cita.objects.filter(status=True, cliente=filtro, estado__in=('confirmada', 'pendiente'), inicio__gte=datetime.now()).exists():
                        raise ValueError('Tiene citas próximas: cancélalas primero.')
                    filtro.status = False
                    filtro.save(request)
                    log(f'Eliminó el cliente {filtro}', request, 'del', obj=filtro.id)
                    messages.success(request, 'Cliente eliminado')
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
                    data['pk'] = pk_form = int(request.GET['pk'])
                    data['form'] = Formulario(instance=model.objects.get(pk=pk_form, status=True))
                    template = get_template('agenda/parciales/form_campos.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                elif action == 'agendar':
                    data['pk'] = pk_form = int(request.GET['pk'])
                    objetivo = model.objects.get(pk=pk_form, status=True)
                    ultimo = Cita.objects.filter(status=True, cliente=objetivo).exclude(estado='cancelada').order_by('-inicio').first()
                    inicio = (datetime.now() + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
                    data['form'] = CitaRapidaForm(initial={
                        'nombres': objetivo.nombres, 'correo': objetivo.correo, 'telefono': objetivo.telefono,
                        'producto': ultimo.producto if ultimo else None,
                        'titulo': f'{ultimo.producto.nombre if ultimo and ultimo.producto_id else "Cita"} · {objetivo.nombres}'[:200],
                        'inicio': inicio.strftime('%Y-%m-%dT%H:%M'), 'duracion': duracion_turno()})
                    for campo in ('nombres', 'correo', 'telefono'):
                        data['form'].fields[campo].widget.attrs['readonly'] = True
                    data['equipos'] = mis_equipos
                    template = get_template('agenda/agenda/form_cita.html')
                    html = template.render(data).replace('name="pk" value="0"', f'name="pk" value="{pk_form}"')
                    return JsonResponse({'result': True, 'data': html})
                return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
            except Exception as ex:
                salva_logs(request, __file__, request.method, action, type(ex).__name__,
                           'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
                return JsonResponse({'result': False, 'message': 'No se pudo cargar el formulario.'})
        if cliente is not None:
            citas = list(Cita.objects.filter(status=True, cliente=cliente)
                         .select_related('producto', 'equipo', 'organizador').prefetch_related('cierre').order_by('-inicio'))
            ahora = datetime.now()
            proximas = [c for c in citas if c.inicio >= ahora and c.estado in ('confirmada', 'pendiente')]
            pasadas = [c for c in citas if c not in proximas]
            atendio = next((c.organizador for c in pasadas if c.estado in ('cerrada', 'realizada')), None)
            personas = {}
            for c in citas:
                if c.estado != 'cancelada':
                    personas[c.organizador_id] = personas.get(c.organizador_id, {'usuario': c.organizador, 'n': 0})
                    personas[c.organizador_id]['n'] += 1
            data.update({
                'titulo': cliente.nombres,
                'cliente': cliente,
                'proximas': proximas,
                'pasadas': pasadas,
                'atendio': atendio,
                'personas': sorted(personas.values(), key=lambda p: -p['n']),
                'solicitudes': Solicitud.objects.filter(status=True, cliente=cliente).select_related('producto', 'equipo').order_by('-fecha_registro')[:20],
                'kpi': {
                    'citas': len([c for c in citas if c.estado != 'cancelada']),
                    'asistidas': len([c for c in citas if c.estado in ('cerrada', 'realizada')]),
                    'canceladas': len([c for c in citas if c.estado == 'cancelada']),
                    'no_asistio': len([c for c in citas if c.estado == 'no_asistio']),
                },
                'es_lead': any(getattr(getattr(c, 'cierre', None), 'es_lead', False) for c in pasadas),
                'capturas': list(CapturaTecnica.objects.filter(status=True).filter(Q(cita__cliente=cliente) | Q(solicitud__cliente=cliente)).order_by('-fecha_registro')[:1]),
            })
            data['listado_lateral'] = (model.objects.filter(status=True).annotate(n_citas=Count('citas', filter=Q(citas__status=True) & ~Q(citas__estado='cancelada')))
                                       .order_by('nombres')[:40])
            data['criterio'] = ''
            return render(request, 'agenda/cliente/listado.html', data)
        criterio, filtros, url_vars = request.GET.get('criterio', '').strip(), Q(status=True), ''
        if criterio:
            filtros &= (Q(nombres__icontains=criterio) | Q(correo__icontains=criterio) | Q(telefono__icontains=criterio)
                        | Q(codigo__icontains=criterio))
            data['criterio'] = criterio
            url_vars += '&criterio=' + criterio
        listado = (model.objects.filter(filtros).select_related('portal_origen')
                   .annotate(n_citas=Count('citas', filter=Q(citas__status=True) & ~Q(citas__estado='cancelada')),
                             ultima=Max('citas__inicio', filter=Q(citas__status=True)))
                   .order_by('-ultima', 'nombres'))
        data['list_count'] = listado.count()
        data['url_vars'] = url_vars
        data['listado_lateral'] = listado[:40]
        primero = listado.first()
        if primero is not None and not criterio:
            from django.shortcuts import redirect
            return redirect(f'/agenda/clientes/{primero.pk}/')
        return render(request, 'agenda/cliente/listado.html', data)
