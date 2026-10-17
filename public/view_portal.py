import sys
from datetime import date, datetime, timedelta

from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt

from agenda import funciones_portal, funciones_tokens
from agenda.forms import ReservaPublicaForm
from agenda.models import Cita, Portal, Producto
from core.funciones import addData, rate_limit
from core.funciones_adicionales import salva_logs

DESTACADAS = 3


def _fecha(texto):
    try:
        return datetime.strptime(texto or '', '%Y-%m-%d').date()
    except ValueError:
        return None


def _sesion(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _horas_json(producto, fecha, sesion=None):
    if fecha is None:
        return JsonResponse({'result': False, 'message': 'Fecha no válida.'})
    horas = [{'valor': h.strftime('%Y-%m-%dT%H:%M'), 'texto': h.strftime('%H:%M')}
             for h in funciones_portal.espacios_del_dia(producto, fecha, sesion)]
    return JsonResponse({'result': True, 'data': horas})


def _en_ventana(request, data, portal):
    """`?ventana=1`: la página va dentro de un iframe de otro sitio. Oculta cabecera y pie y, en la respuesta,
    permite solo los sitios autorizados del portal."""
    data['ventana'] = request.GET.get('ventana') == '1' or request.POST.get('ventana') == '1'
    return data['ventana']


def _sitios(portal):
    return [s.strip() for s in (portal.sitios_autorizados or '').splitlines() if s.strip()]


def _con_marco(respuesta, portal):
    sitios = _sitios(portal)
    respuesta['Content-Security-Policy'] = 'frame-ancestors ' + (' '.join(["'self'"] + sitios))
    respuesta.xframe_options_exempt = True
    return respuesta


def _dias(producto):
    dias = funciones_portal.dias_con_cupo(producto)
    for d in dias:
        d['valor'] = d['fecha'].strftime('%Y-%m-%d')
    return dias


@xframe_options_exempt
@rate_limit(limit=60, seconds=60)
def agendar(request, slug):
    producto = funciones_portal.producto_por_slug(slug)
    if producto is None:
        raise Http404('Producto no encontrado')
    data = {
        'titulo': f'Agendar · {producto.nombre}',
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)
    ventana = _en_ventana(request, data, producto.portal)
    sesion = _sesion(request)
    if request.method == 'POST':
        res_json = {}
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'reservar':
                    form = ReservaPublicaForm(request.POST)
                    if not form.is_valid():
                        raise ValueError(form.primer_error())
                    datos = dict(form.cleaned_data, idioma=funciones_portal.idioma_de(request))
                    cita, token = funciones_portal.reservar(producto, form.cleaned_data['inicio'], datos, request, sesion)
                    res_json = {'error': False, 'to': f'/cita/{token}/' + ('?ventana=1' if ventana else '')}
                elif action == 'llamar':
                    form = ReservaPublicaForm(request.POST, requiere_inicio=False, requiere_telefono=True)
                    if not form.is_valid():
                        raise ValueError(form.primer_error())
                    solicitud = funciones_portal.pedir_llamada(producto, form.cleaned_data, request)
                    res_json = {'error': False, 'message': f'Listo. Le llamamos al {solicitud.telefono_para_llamar} en horario de oficina. Su referencia es {solicitud.codigo}.'}
                else:
                    raise ValueError('Acción no permitida.')
        except ValueError as ex:
            res_json = {'error': True, 'message': str(ex)}
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json = {'error': True, 'message': 'No pudimos registrar su cita. Intente de nuevo en un momento.'}
        return JsonResponse(res_json)
    elif request.method == 'GET':
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'horas':
                return _horas_json(producto, _fecha(request.GET.get('fecha')), sesion)
            if action == 'apartar':
                try:
                    inicio = datetime.strptime(request.GET.get('inicio', ''), '%Y-%m-%dT%H:%M')
                except ValueError:
                    return JsonResponse({'result': False, 'message': 'Elija un horario.'})
                if not funciones_portal.apartar(producto, inicio, sesion):
                    return JsonResponse({'result': False, 'message': 'Otra persona está reservando ese horario. Elija otro, por favor.'})
                return JsonResponse({'result': True, 'minutos': funciones_portal.minutos_apartado()})
            return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
        idioma = funciones_portal.idioma_de(request)
        t = funciones_portal.textos(idioma)
        tiempos = funciones_portal.tiempos_de(producto)
        dias = _dias(producto)
        cupos = {d['fecha']: d['espacios'] for d in dias}
        try:
            primero = datetime.strptime(request.GET.get('mes', ''), '%Y-%m').date().replace(day=1)
        except ValueError:
            primero = (dias[0]['fecha'] if dias else date.today()).replace(day=1)
        semanas, tope = funciones_portal.calendario_mes(producto, primero, cupos)
        mes_anterior = (primero - timedelta(days=1)).replace(day=1)
        mes_siguiente = (primero.replace(day=28) + timedelta(days=4)).replace(day=1)
        data.update({
            'producto': producto,
            'portal': producto.portal,
            'equipo': funciones_portal.equipo_de(producto),
            'tiempos': tiempos,
            'dias': dias,
            'destacadas': dias[:DESTACADAS],
            'telefono': producto.portal.telefono_atencion,
            'url_horas': request.path,
            'idioma': idioma,
            't': t,
            'atencion': funciones_portal.atencion_de(producto, t, tiempos),
            'nombre_producto': funciones_portal.nombre_producto(producto, idioma),
            'descripcion_producto': funciones_portal.descripcion_producto(producto, idioma),
            'semanas': semanas,
            'mes': primero,
            'mes_anterior': mes_anterior if mes_anterior >= date.today().replace(day=1) else None,
            'mes_siguiente': mes_siguiente if mes_siguiente <= tope else None,
            'tope': tope,
            'minutos_apartado': funciones_portal.minutos_apartado(),
        })
        respuesta = render(request, 'public/portal/agendar.html', data)
        return _con_marco(respuesta, producto.portal) if ventana else respuesta


def _datos_cita(request, cita, token_url):
    producto = cita.producto
    return {
        'cita': cita,
        'producto': producto,
        'portal': producto.portal if producto else cita.cliente.portal_origen,
        'qr': funciones_portal.qr_data_uri(request.build_absolute_uri(token_url)),
        'puede_cambiar': cita.estado == 'confirmada' and cita.inicio > datetime.now() and producto is not None,
        'puede_cancelar': cita.estado in ('confirmada', 'pendiente') and cita.inicio > datetime.now(),
        'dias': _dias(producto) if producto and cita.estado == 'confirmada' else [],
        'url_horas': token_url,
    }


@xframe_options_exempt
@rate_limit(limit=60, seconds=60)
def cita_cliente(request, token):
    acceso = funciones_tokens.validar(token, 'cita')
    data = {'titulo': 'Su cita', 'ruta': request.path, 'fecha': datetime.now()}
    addData(request, data)
    data['ventana'] = request.GET.get('ventana') == '1'
    if acceso is None or acceso.cita is None:
        return render(request, 'public/portal/enlace_invalido.html', data, status=410)
    cita = Cita.objects.select_related('cliente', 'producto', 'producto__portal', 'equipo', 'organizador').get(pk=acceso.cita_id)
    if request.method == 'POST':
        res_json = {}
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'cancelar':
                    funciones_portal.cancelar_por_cliente(cita, request.POST.get('motivo', '')[:200], request)
                    res_json = {'error': False, 'reload': True}
                elif action == 'reprogramar':
                    inicio = datetime.strptime(request.POST.get('inicio', ''), '%Y-%m-%dT%H:%M')
                    funciones_portal.reprogramar_por_cliente(cita, inicio, request)
                    res_json = {'error': False, 'reload': True}
                else:
                    raise ValueError('Acción no permitida.')
        except ValueError as ex:
            res_json = {'error': True, 'message': str(ex) if 'strptime' not in str(ex) else 'Elija un horario.'}
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json = {'error': True, 'message': 'No pudimos aplicar el cambio. Intente de nuevo en un momento.'}
        return JsonResponse(res_json)
    elif request.method == 'GET':
        if 'action' in request.GET:
            if request.GET['action'] == 'horas' and cita.producto_id:
                return _horas_json(cita.producto, _fecha(request.GET.get('fecha')))
            return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
        data['titulo'] = f'Su cita {cita.codigo}'
        data.update(_datos_cita(request, cita, request.path))
        respuesta = render(request, 'public/portal/cita.html', data)
        return _con_marco(respuesta, data['portal']) if data['ventana'] and data['portal'] else respuesta


@rate_limit(limit=60, seconds=60)
def conectar(request, portal, token):
    acceso = funciones_tokens.validar(token, 'cliente')
    data = {'titulo': 'Mis citas', 'ruta': request.path, 'fecha': datetime.now()}
    addData(request, data)
    if acceso is None or acceso.cliente is None:
        return render(request, 'public/portal/enlace_invalido.html', data, status=410)
    cliente = acceso.cliente
    portal_obj = Portal.objects.filter(status=True, activo=True, slug=portal).first() or cliente.portal_origen
    citas = (Cita.objects.filter(status=True, cliente=cliente)
             .select_related('producto', 'producto__portal', 'equipo').order_by('-inicio'))

    def _cita_propia():
        pk = request.POST.get('cita') or request.GET.get('cita') or ''
        cita = citas.filter(pk=int(pk)).first() if pk.isdigit() else None
        if cita is None:
            raise ValueError('Esa cita no es suya o ya no existe.')
        return cita

    if request.method == 'POST':
        res_json = {}
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'cancelar':
                    cita = _cita_propia()
                    funciones_portal.cancelar_por_cliente(cita, request.POST.get('motivo', '')[:200], request)
                    res_json = {'error': False, 'reload': True}
                elif action == 'reprogramar':
                    cita = _cita_propia()
                    inicio = datetime.strptime(request.POST.get('inicio', ''), '%Y-%m-%dT%H:%M')
                    funciones_portal.reprogramar_por_cliente(cita, inicio, request)
                    res_json = {'error': False, 'reload': True}
                else:
                    raise ValueError('Acción no permitida.')
        except ValueError as ex:
            res_json = {'error': True, 'message': str(ex) if 'strptime' not in str(ex) else 'Elija un horario.'}
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json = {'error': True, 'message': 'No pudimos aplicar el cambio. Intente de nuevo en un momento.'}
        return JsonResponse(res_json)
    elif request.method == 'GET':
        if 'action' in request.GET:
            if request.GET['action'] == 'horas':
                try:
                    cita = _cita_propia()
                except ValueError as ex:
                    return JsonResponse({'result': False, 'message': str(ex)})
                if cita.producto_id:
                    return _horas_json(cita.producto, _fecha(request.GET.get('fecha')))
            return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
        ahora = datetime.now()
        proximas = [c for c in citas if c.inicio >= ahora and c.estado in ('confirmada', 'pendiente')]
        pasadas = [c for c in citas if c not in proximas]
        for c in proximas:
            c.dias_cambio = _dias(c.producto) if c.producto_id and c.estado == 'confirmada' else []
        productos = []
        if portal_obj:
            productos = list(Producto.objects.filter(status=True, activo=True, portal=portal_obj, padre__isnull=True)
                             .order_by('orden', 'nombre'))
        data.update({'cliente': cliente, 'portal': portal_obj, 'proximas': proximas, 'pasadas': pasadas,
                     'productos': productos, 'url_horas': request.path})
        return render(request, 'public/portal/conectar.html', data)


@xframe_options_exempt
@rate_limit(limit=60, seconds=60)
def incrustar(request, portal):
    portal_obj = Portal.objects.filter(status=True, activo=True, slug=portal).first()
    if portal_obj is None:
        raise Http404('Portal no encontrado')
    data = {'titulo': f'Agendar · {portal_obj.nombre}', 'ruta': request.path, 'fecha': datetime.now(), 'ventana': True}
    addData(request, data)
    data['portal'] = portal_obj
    data['productos'] = list(Producto.objects.filter(status=True, activo=True, portal=portal_obj, padre__isnull=True)
                             .order_by('orden', 'nombre'))
    return _con_marco(render(request, 'public/portal/incrustar.html', data), portal_obj)
