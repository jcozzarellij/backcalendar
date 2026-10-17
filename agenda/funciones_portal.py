"""Portal público de reserva: lo que el cliente puede hacer sin cuenta.

- `producto_por_slug(slug)` — producto activo de un portal activo.
- `tiempos_de(producto)` — duración, antelación, ventana, margen y límites, heredando padre → parámetros.
- `dias_con_cupo(producto, desde, dias)` — fechas con al menos un espacio común del equipo.
- `espacios_del_dia(producto, fecha)` — inicios libres (datetime) del equipo ese día.
- `reservar(producto, inicio, datos, request)` — crea cliente, cita, tokens y manda el correo. Dentro de `atomic()`.
- `pedir_llamada(producto, datos, request)` — solicitud en cola con teléfono.
- `cancelar_por_cliente` / `reprogramar_por_cliente` — acciones de la página de la cita.
- `qr_data_uri(texto)` — QR en SVG para la página de la cita.
- `productos_publicos(portal, idioma, t)` / `productos_destacados(portal, idioma, t)` — tickets del catálogo y del landing.
- `atencion_de(producto, t)` — «40 minutos, por videollamada».
"""
from collections import Counter
from datetime import datetime, timedelta

import segno
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Prefetch, prefetch_related_objects
from django.template.loader import get_template
from django.utils.formats import date_format

from core import correos
from seguridad.models import Configuracion, ParametroSistema
from . import funciones_tokens
from .funciones_citas import (cancelar_cita, codigo_solicitud, crear_cita, mover_cita, obtener_o_crear_cliente,
                              responsables_de)
from .funciones_disponibilidad import espacios_comunes_rango
from .funciones_turnos import duracion_turno
from .models import CapturaTecnica, Cita, Producto, Solicitud


def _parametro_int(clave, default):
    try:
        return int(ParametroSistema.valor_de(clave, default))
    except (TypeError, ValueError):
        return default


def producto_por_slug(slug):
    base = Producto.objects.filter(status=True, activo=True, slug=slug, portal__status=True, portal__activo=True)
    return (base.filter(padre__isnull=True).select_related('portal', 'equipo', 'padre').first()
            or base.select_related('portal', 'equipo', 'padre').first())


def equipo_de(producto):
    return producto.equipo or (producto.padre.equipo if producto.padre_id else None)


def _heredado(producto, campo, clave_parametro, default):
    for p in (producto, producto.padre if producto.padre_id else None):
        if p is not None and getattr(p, campo) is not None:
            return getattr(p, campo)
    return _parametro_int(clave_parametro, default)


def tiempos_de(producto):
    return {
        'duracion': _heredado(producto, 'duracion_min', 'agenda_duracion_turno', duracion_turno()),
        'antelacion': _heredado(producto, 'antelacion_horas', 'agenda_antelacion_horas', 24),
        'ventana': _heredado(producto, 'ventana_dias', 'agenda_ventana_dias', 14),
        'margen': _heredado(producto, 'margen_min', 'agenda_margen_min', 0),
        'limite_dia': _heredado(producto, 'limite_dia', 'agenda_limite_dia', 0),
    }


def _minimo(producto):
    return datetime.now() + timedelta(hours=tiempos_de(producto)['antelacion'])


def _clave_apartado(producto, inicio):
    return f'agenda_apartado:{producto.pk}:{inicio:%Y%m%d%H%M}'


def minutos_apartado():
    return _parametro_int('portal_reserva_temporal_min', 10)


def apartar(producto, inicio, sesion):
    """Aparta `inicio` para `sesion` durante `portal_reserva_temporal_min`; False si otro lo tiene."""
    clave = _clave_apartado(producto, inicio)
    actual = cache.get(clave)
    if actual and actual != sesion:
        return False
    cache.set(clave, sesion, timeout=max(60, minutos_apartado() * 60))
    return True


def liberar(producto, inicio, sesion):
    clave = _clave_apartado(producto, inicio)
    if cache.get(clave) == sesion:
        cache.delete(clave)


def apartado_por_otro(producto, inicio, sesion=None):
    actual = cache.get(_clave_apartado(producto, inicio))
    return bool(actual) and actual != sesion


def espacios_del_dia(producto, fecha, sesion=None):
    return _espacios_rango(producto, fecha, fecha, sesion).get(fecha, [])


def dias_con_cupo(producto, desde=None, dias=None):
    t = tiempos_de(producto)
    minimo = _minimo(producto)
    fecha = max(desde or minimo.date(), minimo.date())
    tope = minimo.date() + timedelta(days=dias if dias is not None else t['ventana'])
    if fecha > tope:
        return []
    return [{'fecha': f, 'espacios': len(e)} for f, e in sorted(_espacios_rango(producto, fecha, tope).items()) if e]


def _espacios_rango(producto, desde, hasta, sesion=None):
    """{fecha: inicios libres del equipo} entre `desde` y `hasta`, respetando antelación, límite diario y
    horarios apartados por otra sesión. Carga turnos, bloques, Google y citas una vez para todo el rango."""
    equipo = equipo_de(producto)
    responsables = responsables_de(equipo) if equipo else []
    if not responsables:
        return {}
    t = tiempos_de(producto)
    minimo = _minimo(producto)
    desde = max(desde, minimo.date())
    if desde > hasta:
        return {}
    por_dia = espacios_comunes_rango(responsables, desde, hasta, t['duracion'], t['margen'], desde_hora=minimo)
    if t['limite_dia']:
        rango_ini = datetime.combine(desde, datetime.min.time())
        citas = Counter(Cita.objects.filter(status=True, equipo=equipo, inicio__gte=rango_ini,
                                            inicio__lt=datetime.combine(hasta, datetime.min.time()) + timedelta(days=1))
                        .exclude(estado='cancelada').values_list('inicio__date', flat=True))
        por_dia = {f: ([] if citas[f] >= t['limite_dia'] else e) for f, e in por_dia.items()}
    return {f: [e for e in espacios if not apartado_por_otro(producto, e, sesion)] for f, espacios in por_dia.items()}


def _organizador(equipo):
    if equipo.lider_id:
        return equipo.lider
    responsables = responsables_de(equipo)
    if responsables:
        return responsables[0]
    return equipo.proyecto.lider


def _reservas_activas(cliente):
    return Cita.objects.filter(status=True, cliente=cliente, estado__in=('confirmada', 'pendiente'),
                               inicio__gte=datetime.now()).count()


def capturar(request, cita=None, solicitud=None):
    """Guarda IP, navegador y origen de la reserva (abuso y soporte). Nunca rompe la reserva."""
    if request is None:
        return None
    try:
        from core.funciones import get_client_ip
        meta = request.META
        return CapturaTecnica.objects.create(
            cita=cita, solicitud=solicitud,
            ip=(get_client_ip(request) or meta.get('REMOTE_ADDR') or '')[:64],
            navegador=meta.get('HTTP_USER_AGENT', '')[:300], origen=meta.get('HTTP_REFERER', '')[:300],
            idioma_navegador=meta.get('HTTP_ACCEPT_LANGUAGE', '')[:40])
    except Exception:
        return None


def reservar(producto, inicio, datos, request=None, sesion=None):
    """Crea la cita del cliente en `inicio` (datetime local). Lanza `ValueError` con mensaje para el cliente."""
    equipo = equipo_de(producto)
    if equipo is None or not responsables_de(equipo):
        raise ValueError('Este producto todavía no tiene un equipo que lo atienda. Pida que le llamen.')
    t = tiempos_de(producto)
    if inicio < _minimo(producto):
        raise ValueError('Ese horario ya no está disponible. Elija otro, por favor.')
    if inicio not in espacios_del_dia(producto, inicio.date(), sesion):
        raise ValueError('Ese horario se acaba de ocupar. Elija otro, por favor.')
    cliente = obtener_o_crear_cliente(datos['nombres'], datos['correo'], datos.get('telefono', ''), producto.portal,
                                      request, idioma=datos.get('idioma') or 'es')
    tope = _parametro_int('cliente_reservas_activas', 2)
    if tope and _reservas_activas(cliente) >= tope:
        raise ValueError(f'Ya tiene {tope} citas pendientes. Puede cambiarlas o cancelarlas desde el enlace de su correo.')
    solicitud = Solicitud(codigo=codigo_solicitud(), cliente=cliente, portal=producto.portal, producto=producto,
                          proyecto=equipo.proyecto, equipo=equipo, origen='portal', estado='en_cola',
                          mensaje=(datos.get('mensaje') or '')[:2000], motivo=f'Reserva web · {producto}'[:300])
    solicitud.save(request)
    fin = inicio + timedelta(minutes=t['duracion'])
    cita = crear_cita(cliente=cliente, inicio=inicio, fin=fin, organizador=_organizador(equipo),
                      titulo=f'{producto.nombre} · {cliente.nombres}'[:200], equipo=equipo, proyecto=equipo.proyecto,
                      producto=producto, solicitud=solicitud, asignada_por='cliente', idioma=cliente.idioma,
                      request=request)
    capturar(request, cita=cita, solicitud=solicitud)
    token_cita = funciones_tokens.emitir('cita', cita=cita, request=request)
    token_cliente = funciones_tokens.emitir('cliente', cliente=cliente, request=request)
    url_cita = funciones_tokens.url_cita(token_cita)
    url_cliente = funciones_tokens.url_cliente(producto.portal, token_cliente)
    transaction.on_commit(lambda: enviar_confirmacion(cita.pk, url_cita, url_cliente))
    if sesion:
        liberar(producto, inicio, sesion)
    return cita, token_cita


def pedir_llamada(producto, datos, request=None):
    equipo = equipo_de(producto)
    cliente = obtener_o_crear_cliente(datos['nombres'], datos['correo'], datos.get('telefono', ''), producto.portal,
                                      request)
    solicitud = Solicitud(codigo=codigo_solicitud(), cliente=cliente, portal=producto.portal, producto=producto,
                          proyecto=equipo.proyecto if equipo else None, equipo=equipo, origen='portal',
                          estado='en_cola', mensaje=(datos.get('mensaje') or '')[:2000],
                          telefono_para_llamar=datos.get('telefono', '')[:40],
                          motivo=f'Pidió que le llamen · {producto}'[:300], causa_cola='El cliente pidió una llamada')
    solicitud.save(request)
    capturar(request, solicitud=solicitud)
    return solicitud


def cancelar_por_cliente(cita, motivo, request=None):
    if cita.estado in ('cerrada', 'realizada', 'no_asistio'):
        raise ValueError('Esta cita ya se realizó y no se puede cancelar.')
    if cita.inicio < datetime.now():
        raise ValueError('Esta cita ya pasó.')
    return cancelar_cita(cita, f'Canceló el cliente. {motivo}'.strip(), request)


def reprogramar_por_cliente(cita, inicio, request=None):
    if cita.estado != 'confirmada':
        raise ValueError('Solo se puede cambiar una cita confirmada.')
    producto = cita.producto
    if producto is None:
        raise ValueError('Esta cita no se puede cambiar desde aquí. Escríbanos, por favor.')
    if inicio < _minimo(producto):
        raise ValueError('Ese horario ya no está disponible. Elija otro, por favor.')
    if inicio not in espacios_del_dia(producto, inicio.date()) and inicio != cita.inicio:
        raise ValueError('Ese horario se acaba de ocupar. Elija otro, por favor.')
    fin = inicio + (cita.fin - cita.inicio)
    return mover_cita(cita, inicio, fin, request, 'Cambio pedido por el cliente.')


def qr_data_uri(texto):
    return segno.make(texto, error='m').svg_data_uri(scale=4, border=1, dark='#1d1d1f')


def enviar_confirmacion(cita_pk, url_cita, url_cliente):
    cita = Cita.objects.select_related('cliente', 'producto', 'equipo').get(pk=cita_pk)
    if not cita.cliente.correo:
        return
    confi = Configuracion.get_instancia()
    contexto = {
        'cita': cita,
        'cliente': cita.cliente,
        'producto': cita.producto,
        'fecha_larga': date_format(cita.inicio, r'l j \d\e F \d\e Y').capitalize(),
        'hora': cita.inicio.strftime('%H:%M'),
        'hora_fin': cita.fin.strftime('%H:%M'),
        'url_cita': url_cita,
        'url_cliente': url_cliente,
        'nombreempresa': confi.nombre_empresa or 'Turno',
        'logo': f"{funciones_tokens.base_publica()}{confi.logo_sistema_white.url}" if confi.logo_sistema_white else '',
        'sucursal': confi.nombre_empresa or 'Turno',
    }
    html = get_template('email/cita_confirmada.html').render(contexto)
    asunto = f'Su cita del {cita.inicio:%d/%m/%Y} a las {cita.inicio:%H:%M} · {cita.codigo}'
    correos.despachar(correos.armar(asunto, html, to=[cita.cliente.correo]))


IDIOMAS_PORTAL = ('es', 'en', 'pt')


def idioma_de(request):
    """Idioma del portal: `?idioma=` manda, luego la sesión, luego español."""
    pedido = request.GET.get('idioma') or request.POST.get('idioma') or ''
    if pedido in IDIOMAS_PORTAL:
        request.session['idioma_portal'] = pedido
        return pedido
    return request.session.get('idioma_portal') or 'es'


def textos(idioma='es'):
    """Diccionario clave → texto en el idioma pedido (con español de respaldo)."""
    from .models import TextoPortal
    from .textos_portal import TEXTOS
    columna = {'es': 1, 'en': 2, 'pt': 3}.get(idioma, 1)
    salida = {fila[0]: fila[columna] or fila[1] for fila in TEXTOS}
    for fila in TextoPortal.objects.filter(status=True):
        salida[fila.clave] = (getattr(fila, idioma, '') if idioma != 'es' else '') or fila.es
    return salida


def nombre_producto(producto, idioma='es'):
    return (getattr(producto, f'nombre_{idioma}', '') if idioma != 'es' else '') or producto.nombre


def descripcion_producto(producto, idioma='es'):
    return (getattr(producto, f'descripcion_{idioma}', '') if idioma != 'es' else '') or producto.descripcion


DESTACADOS_LANDING = 4


def atencion_de(producto, t, tiempos=None):
    """Texto «40 minutos, por videollamada» del producto, con su duración heredada."""
    return f"{(tiempos or tiempos_de(producto))['duracion']} {t['minutos_video']}"


def productos_raiz(portal):
    """Productos raíz que el público puede agendar: la única definición de «producto visible»."""
    return Producto.objects.filter(status=True, activo=True, portal=portal, padre__isnull=True).order_by('orden', 'nombre')


def _tarjetas(productos, idioma, t):
    prefetch_related_objects(productos, Prefetch(
        'subproductos', queryset=Producto.objects.filter(status=True, activo=True).order_by('orden', 'nombre'),
        to_attr='partes_activas'))
    return [{
        'nombre': nombre_producto(p, idioma),
        'descripcion': descripcion_producto(p, idioma),
        'slug': p.slug,
        'sitio_web': p.sitio_web,
        'atencion': atencion_de(p, t),
        'partes': [{'nombre': nombre_producto(s, idioma), 'descripcion': descripcion_producto(s, idioma), 'slug': s.slug}
                   for s in p.partes_activas],
    } for p in productos]


def productos_publicos(portal, idioma, t):
    """Tickets de todos los productos raíz visibles, con sus partes, ya traducidos."""
    return _tarjetas(list(productos_raiz(portal)), idioma, t) if portal else []


def productos_destacados(portal, idioma, t):
    """Tickets del landing y total de productos visibles, en una consulta: los marcados como destacados
    (máximo `DESTACADOS_LANDING`) o, si no hay ninguno, los primeros por orden."""
    if portal is None:
        return [], 0
    raices = list(productos_raiz(portal))
    elegidos = [p for p in raices if p.destacado][:DESTACADOS_LANDING] or raices[:DESTACADOS_LANDING]
    return _tarjetas(elegidos, idioma, t), len(raices)


def calendario_mes(producto, primero, cupos, sesion=None):
    """Semanas del mes (lunes a domingo) con el cupo de cada día dentro de la ventana."""
    t = tiempos_de(producto)
    minimo = _minimo(producto).date()
    tope = minimo + timedelta(days=t['ventana'])
    inicio = primero - timedelta(days=primero.weekday())
    ultimo = (primero.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    fin = ultimo + timedelta(days=6 - ultimo.weekday())
    semanas, fila, dia = [], [], inicio
    while dia <= fin:
        fila.append({'fecha': dia, 'otro_mes': dia.month != primero.month, 'en_ventana': minimo <= dia <= tope,
                     'cupo': cupos.get(dia, 0)})
        if len(fila) == 7:
            semanas.append(fila)
            fila = []
        dia += timedelta(days=1)
    return semanas, tope
