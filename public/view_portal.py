import sys
from datetime import date, datetime, timedelta

from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils import translation
from django.views.decorators.clickjacking import xframe_options_exempt

from agenda import funciones_portal, funciones_tokens
from agenda.forms import BuscarCitaForm, ReservaPublicaForm
from agenda.models import Cita, Portal, Producto
from core.custom_forms import FormError
from core.funciones import addData, rate_limit
from core.funciones_adicionales import salva_logs

DESTACADAS = 3
AVISOS = ('reservada', 'movida', 'cancelada')
TERMINADAS = ('cerrada', 'realizada', 'no_asistio')
RELACIONES_CITA = ('cliente', 'producto', 'producto__portal', 'producto__equipo', 'producto__padre',
                   'producto__padre__equipo', 'equipo', 'organizador')


@xframe_options_exempt
@rate_limit(limit=60, seconds=60)
def agendar(request, slug, padre=None):
    producto = funciones_portal.producto_por_slug(slug, padre)
    if producto is None:
        raise Http404('Producto no encontrado')
    if producto.ruta != request.path:
        return redirect(producto.ruta + (f'?{request.META["QUERY_STRING"]}' if request.META.get('QUERY_STRING') else ''))
    idioma = funciones_portal.idioma_de(request)
    t = funciones_portal.textos(idioma)
    data = {
        'titulo': f"{t['ld_agendar']} · {funciones_portal.nombre_producto(producto, idioma)}",
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)
    ventana = _en_ventana(request, data)
    sesion = _sesion(request)

    if request.method == 'POST':
        t = funciones_portal.contexto_publico(request, data, producto.portal)
        res_json = {}
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'reservar':
                    form = ReservaPublicaForm(request.POST)
                    if not form.is_valid():
                        raise ValueError(form.primer_error())
                    datos = dict(form.cleaned_data, idioma=data['idioma'])
                    cita, token = funciones_portal.reservar(producto, form.cleaned_data['inicio'], datos, request, sesion)
                    res_json = {'error': False, 'to': _con_aviso(f'/cita/{token}/', 'reservada', ventana)}
                elif action == 'llamar':
                    form = ReservaPublicaForm(request.POST, requiere_inicio=False, requiere_telefono=True)
                    if not form.is_valid():
                        raise ValueError(form.primer_error())
                    solicitud = funciones_portal.pedir_llamada(producto, form.cleaned_data, request)
                    res_json = {'error': False, 'message': funciones_portal.formatear(
                        t['llamada_lista'], tel=solicitud.telefono_para_llamar, codigo=solicitud.codigo)}
                else:
                    raise ValueError('Acción no permitida.')
        except ValueError as ex:
            res_json = {'error': True, 'message': str(ex)}
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json = {'error': True, 'message': t['error_reserva']}
        return JsonResponse(res_json)
    elif request.method == 'GET':
        if 'action' in request.GET:
            data["action"] = action = request.GET['action']
            if action == 'horas':
                return _horas_json(producto, _fecha(request.GET.get('fecha')), sesion)
            if action == 'apartar':
                inicio = _inicio(request.GET.get('inicio'))
                if inicio is None:
                    return JsonResponse({'result': False, 'message': 'Elija un horario.'})
                if not funciones_portal.apartar(producto, inicio, sesion):
                    return JsonResponse({'result': False, 'message': 'Otra persona está reservando ese horario. Elija otro, por favor.'})
                return JsonResponse({'result': True, 'minutos': funciones_portal.minutos_apartado()})
            return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
        t = funciones_portal.contexto_publico(request, data, producto.portal)
        idioma = data['idioma']
        nombre = funciones_portal.nombre_producto(producto, idioma)
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
            'url_horas': request.path,
            'atencion': funciones_portal.atencion_de(producto, t, tiempos),
            'nombre_producto': nombre,
            'descripcion_producto': funciones_portal.descripcion_producto(producto, idioma),
            'nombre_padre': funciones_portal.nombre_producto(producto.padre, idioma) if producto.padre_id else '',
            'partes': [{'nombre': funciones_portal.nombre_producto(s, idioma), 'ruta': s.ruta}
                       for s in producto.subproductos.filter(status=True, activo=True).order_by('orden', 'nombre')],
            'dias_semana': t['dias_semana'].split(','),
            'semanas': semanas,
            'mes': primero,
            'mes_anterior': mes_anterior if mes_anterior >= date.today().replace(day=1) else None,
            'mes_siguiente': mes_siguiente if mes_siguiente <= tope else None,
            'tope': tope,
            'minutos_apartado': funciones_portal.minutos_apartado(),
        })
        respuesta = _render(request, 'public/portal/agendar.html', data)
        return _con_marco(respuesta, producto.portal) if ventana else respuesta


@xframe_options_exempt
@rate_limit(limit=60, seconds=60)
def cita_cliente(request, token):
    acceso = funciones_tokens.validar(token, 'cita')
    t = funciones_portal.textos(funciones_portal.idioma_de(request))
    data = {
        'titulo': t['su_cita'],
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)
    ventana = _en_ventana(request, data)
    if acceso is None or acceso.cita is None:
        funciones_portal.contexto_publico(request, data)
        return _render(request, 'public/portal/enlace_invalido.html', data, status=410)
    cita = Cita.objects.select_related(*RELACIONES_CITA).get(pk=acceso.cita_id)
    portal = cita.producto.portal if cita.producto_id else cita.cliente.portal_origen
    t = funciones_portal.contexto_publico(request, data, portal, preferido=cita.idioma)

    if request.method == 'POST':
        res_json = {}
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'cancelar':
                    funciones_portal.cancelar_por_cliente(cita, request.POST.get('motivo', '')[:200], request)
                    res_json = {'error': False, 'to': _con_aviso(request.path, 'cancelada', ventana)}
                elif action == 'reprogramar':
                    funciones_portal.reprogramar_por_cliente(cita, _inicio_obligatorio(request, t), request)
                    res_json = {'error': False, 'to': _con_aviso(request.path, 'movida', ventana)}
                else:
                    raise ValueError('Acción no permitida.')
        except ValueError as ex:
            res_json = {'error': True, 'message': str(ex)}
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json = {'error': True, 'message': t['error_cambio']}
        return JsonResponse(res_json)
    elif request.method == 'GET':
        if 'action' in request.GET:
            data["action"] = action = request.GET['action']
            if action == 'horas' and cita.producto_id:
                return _horas_json(cita.producto, _fecha(request.GET.get('fecha')))
            return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
        _presentar(cita, data['idioma'], t)
        puede_cambiar = cita.estado == 'confirmada' and cita.inicio > datetime.now() and cita.producto_id is not None
        data.update({
            'titulo': f"{t['su_cita']} {cita.codigo}",
            'cita': cita,
            'producto': cita.producto,
            'portal': portal,
            'fase': 'cancelada' if cita.estado == 'cancelada' else 'terminada' if cita.estado in TERMINADAS else 'activa',
            'qr': funciones_portal.qr_data_uri(request.build_absolute_uri(request.path)),
            'puede_cambiar': puede_cambiar,
            'puede_cancelar': cita.estado in ('confirmada', 'pendiente') and cita.inicio > datetime.now(),
            'dias': _dias(cita.producto) if puede_cambiar else [],
            'url_horas': request.path,
            'aviso': _aviso(request, t),
        })
        data['aviso_texto'] = t['ok_texto'] if data['aviso'] and cita.estado != 'cancelada' else ''
        respuesta = _render(request, 'public/portal/cita.html', data)
        return _con_marco(respuesta, portal) if ventana and portal else respuesta


@rate_limit(limit=10, seconds=60)
def mi_cita(request):
    t = funciones_portal.textos(funciones_portal.idioma_de(request))
    data = {
        'titulo': t['mc_titulo'],
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)

    if request.method == 'POST':
        action = request.POST.get('action', '')
        try:
            if action != 'buscar':
                return JsonResponse({'error': True, 'message': 'Acción no permitida.'})
            form = BuscarCitaForm(request.POST)
            if not form.is_valid():
                raise FormError(form)
            cita = Cita.objects.filter(status=True, codigo=form.cleaned_data['codigo'],
                                       cliente__correo__iexact=form.cleaned_data['correo']).first()
            if cita is None:
                return JsonResponse({'error': True, 'message': t['mc_no_encontrada']})
            with transaction.atomic():
                token = funciones_tokens.emitir('cita', cita=cita, request=request)
            return JsonResponse({'error': False, 'to': f'/cita/{token}/'})
        except FormError as ex:
            return JsonResponse({**ex.dict_error, 'message': t['mc_no_encontrada']})
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            return JsonResponse({'error': True, 'message': t['error_cambio']})
    elif request.method == 'GET':
        if 'action' in request.GET:
            data["action"] = action = request.GET['action']
    funciones_portal.contexto_publico(request, data, funciones_portal.portal_principal())
    return _render(request, 'public/portal/mi_cita.html', data)


@rate_limit(limit=60, seconds=60)
def conectar(request, portal, token):
    acceso = funciones_tokens.validar(token, 'cliente')
    t = funciones_portal.textos(funciones_portal.idioma_de(request))
    data = {
        'titulo': t['mis_citas'],
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)
    if acceso is None or acceso.cliente is None:
        funciones_portal.contexto_publico(request, data)
        return _render(request, 'public/portal/enlace_invalido.html', data, status=410)
    cliente = acceso.cliente
    portal_obj = Portal.objects.filter(status=True, activo=True, slug=portal).first() or cliente.portal_origen
    t = funciones_portal.contexto_publico(request, data, portal_obj, preferido=cliente.idioma)
    idioma = data['idioma']
    citas = Cita.objects.filter(status=True, cliente=cliente).select_related(*RELACIONES_CITA).order_by('-inicio')

    def _cita_propia():
        pk = request.POST.get('cita') or request.GET.get('cita') or ''
        cita = citas.filter(pk=int(pk)).first() if pk.isdigit() else None
        if cita is None:
            raise ValueError(t['mx_ajena'])
        return cita

    if request.method == 'POST':
        res_json = {}
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'cancelar':
                    funciones_portal.cancelar_por_cliente(_cita_propia(), request.POST.get('motivo', '')[:200], request)
                    res_json = {'error': False, 'to': _con_aviso(request.path, 'cancelada')}
                elif action == 'reprogramar':
                    funciones_portal.reprogramar_por_cliente(_cita_propia(), _inicio_obligatorio(request, t), request)
                    res_json = {'error': False, 'to': _con_aviso(request.path, 'movida')}
                else:
                    raise ValueError('Acción no permitida.')
        except ValueError as ex:
            res_json = {'error': True, 'message': str(ex)}
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json = {'error': True, 'message': t['error_cambio']}
        return JsonResponse(res_json)
    elif request.method == 'GET':
        if 'action' in request.GET:
            data["action"] = action = request.GET['action']
            if action == 'horas':
                try:
                    cita = _cita_propia()
                except ValueError as ex:
                    return JsonResponse({'result': False, 'message': str(ex)})
                if cita.producto_id:
                    return _horas_json(cita.producto, _fecha(request.GET.get('fecha')))
            return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
        ahora = datetime.now()
        proximas, pasadas, dias_por_producto = [], [], {}
        for c in citas:
            _presentar(c, idioma, t)
            (proximas if c.inicio >= ahora and c.estado in ('confirmada', 'pendiente') else pasadas).append(c)
        proximas.reverse()
        for c in proximas:
            if c.producto_id and c.estado == 'confirmada' and c.producto_id not in dias_por_producto:
                dias_por_producto[c.producto_id] = _dias(c.producto)
            c.dias_cambio = dias_por_producto.get(c.producto_id, []) if c.estado == 'confirmada' else []
        productos = []
        if portal_obj:
            productos = [{'nombre': funciones_portal.nombre_producto(p, idioma), 'slug': p.slug}
                         for p in Producto.objects.filter(status=True, activo=True, portal=portal_obj, padre__isnull=True)
                         .order_by('orden', 'nombre')]
        data.update({
            'cliente': cliente, 'portal': portal_obj, 'proximas': proximas,
            'pasadas': pasadas, 'productos': productos, 'url_horas': request.path, 'aviso': _aviso(request, t),
        })
        return _render(request, 'public/portal/conectar.html', data)


@xframe_options_exempt
@rate_limit(limit=60, seconds=60)
def incrustar(request, portal):
    portal_obj = Portal.objects.filter(status=True, activo=True, slug=portal).first()
    if portal_obj is None:
        raise Http404('Portal no encontrado')
    t = funciones_portal.textos(funciones_portal.idioma_de(request))
    data = {
        'titulo': f"{t['ld_agendar']} · {portal_obj.nombre}",
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)
    data['ventana'] = True
    t = funciones_portal.contexto_publico(request, data, portal_obj)

    if request.method == 'POST':
        pass
    elif request.method == 'GET':
        if 'action' in request.GET:
            data["action"] = action = request.GET['action']
    data.update({
        'portal': portal_obj,
        'productos': funciones_portal.productos_publicos(portal_obj, data['idioma'], t),
    })
    return _con_marco(_render(request, 'public/portal/incrustar.html', data), portal_obj)


def _render(request, plantilla, data, status=200):
    """Renderiza con el idioma del portal activo, así meses, días y validaciones salen en ese idioma."""
    with translation.override(data.get('idioma') or 'es'):
        return render(request, plantilla, data, status=status)


def _presentar(cita, idioma, t):
    cita.nombre_mostrar = funciones_portal.nombre_producto(cita.producto, idioma) if cita.producto_id else cita.titulo
    cita.estado_texto = t.get(f'estado_{cita.estado}') or cita.get_estado_display()
    return cita


def _aviso(request, t):
    aviso = request.GET.get('aviso', '')
    return t.get(f'ok_{aviso}', '') if aviso in AVISOS else ''


def _con_aviso(ruta, aviso, ventana=False):
    return f'{ruta}?aviso={aviso}' + ('&ventana=1' if ventana else '')


def _fecha(texto):
    try:
        return datetime.strptime(texto or '', '%Y-%m-%d').date()
    except ValueError:
        return None


def _inicio(texto):
    try:
        return datetime.strptime(texto or '', '%Y-%m-%dT%H:%M')
    except ValueError:
        return None


def _inicio_obligatorio(request, t):
    inicio = _inicio(request.POST.get('inicio'))
    if inicio is None:
        raise ValueError(t['elegir_primero'])
    return inicio


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


def _en_ventana(request, data):
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
