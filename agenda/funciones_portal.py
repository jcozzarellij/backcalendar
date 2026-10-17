"""Portal público de reserva: lo que el cliente puede hacer sin cuenta.

- `producto_por_slug(slug)` — producto activo de un portal activo.
- `tiempos_de(producto)` — duración, antelación, ventana, margen y límites, heredando padre → parámetros.
- `dias_con_cupo(producto, desde, dias)` — fechas con al menos un espacio común del equipo.
- `espacios_del_dia(producto, fecha)` — inicios libres (datetime) del equipo ese día.
- `reservar(producto, inicio, datos, request)` — crea cliente, cita y tokens; los avisos van por `funciones_avisos_cita`. Dentro de `atomic()`.
- `pedir_llamada(producto, datos, request)` — solicitud en cola con teléfono.
- `cancelar_por_cliente` / `reprogramar_por_cliente` — acciones de la página de la cita.
- `qr_data_uri(texto)` / `qr_png(texto)` — QR en SVG para la página de la cita y en PNG para los correos.
- `productos_publicos(portal, idioma, t)` / `productos_destacados(portal, idioma, t)` — tickets del catálogo y del landing.
- `atencion_de(producto, t)` — «40 minutos, por videollamada».
"""
import io
from collections import Counter
from datetime import datetime, timedelta
from functools import lru_cache

import segno
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Prefetch, prefetch_related_objects

from seguridad.models import ParametroSistema
from . import funciones_avisos_cita, funciones_tokens
from .funciones_alertas import avisar_solicitud_nueva
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


RUTAS_RESERVADAS = frozenset({
    'admin', 'health', 'panel', 'notificaciones', 'perfilpanel', 'consultas', 'ajaxrequest', 'redirect-to-url',
    'favicon', 'clear-site-data', 'select2', 'webpush', 'media', 'static', 'catalogo', 'login', 'logout',
    'restorepass', 'restoreusername', 'changepass', 'privacidad', 'terminosycondiciones', 'proteccion-datos',
    'agendar', 'mi-cita', 'cita', 'conectar', 'incrustar', 'agenda', 'area-geografica', 'autenticacion',
    'seguridad', 'manifest', 'serviceworker', 'offline', 'pwa',
})


def producto_por_slug(slug, padre=None):
    """Producto raíz por su ruta, o subproducto por la ruta de su padre y la propia. Sin `padre`, una ruta que
    solo existe como subproducto también se resuelve (la vista redirige a su ruta completa)."""
    base = Producto.objects.filter(status=True, activo=True, slug=slug, portal__status=True, portal__activo=True)
    relacionados = ('portal', 'equipo', 'padre', 'padre__equipo')
    if padre:
        return base.filter(padre__slug=padre, padre__status=True, padre__activo=True).select_related(*relacionados).first()
    return (base.filter(padre__isnull=True).select_related(*relacionados).first()
            or base.select_related(*relacionados).first())


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
    transaction.on_commit(lambda: funciones_avisos_cita.avisar_reserva(cita.pk, url_cita, url_cliente))
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
    solicitud_pk = solicitud.pk
    transaction.on_commit(lambda: avisar_solicitud_nueva(solicitud_pk))
    return solicitud


def cancelar_por_cliente(cita, motivo, request=None):
    if cita.estado in ('cerrada', 'realizada', 'no_asistio'):
        raise ValueError('Esta cita ya se realizó y no se puede cancelar.')
    if cita.inicio < datetime.now():
        raise ValueError('Esta cita ya pasó.')
    return cancelar_cita(cita, f'Canceló el cliente. {motivo}'.strip(), request, por_cliente=True)


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
    return mover_cita(cita, inicio, fin, request, 'Cambio pedido por el cliente.', por_cliente=True)


@lru_cache(maxsize=256)
def qr_data_uri(texto):
    return segno.make(texto, error='m').svg_data_uri(scale=4, border=1, dark='#1d1d1f')


def qr_png(texto):
    """QR en PNG para los correos: los clientes de correo no muestran el SVG en línea de la página."""
    salida = io.BytesIO()
    segno.make(texto, error='m').save(salida, kind='png', scale=8, border=2, dark='#1A2B3C')
    return salida.getvalue()


IDIOMAS_PORTAL = ('es', 'en', 'pt')


def idioma_de(request, preferido=None):
    """Idioma del portal: `?idioma=` manda, luego la sesión, luego el idioma guardado del cliente o la cita
    (`preferido`), luego español."""
    pedido = request.GET.get('idioma') or request.POST.get('idioma') or ''
    if pedido in IDIOMAS_PORTAL:
        request.session['idioma_portal'] = pedido
        return pedido
    return request.session.get('idioma_portal') or (preferido if preferido in IDIOMAS_PORTAL else 'es')


def textos(idioma='es'):
    """Diccionario clave → texto en el idioma pedido (con español de respaldo). Cacheado por idioma;
    `TextoPortal.save` lo invalida y el TTL corto cubre a los demás procesos."""
    from .models import TextoPortal

    def _armar():
        from .textos_portal import TEXTOS
        columna = {'es': 1, 'en': 2, 'pt': 3}.get(idioma, 1)
        salida = {fila[0]: fila[columna] or fila[1] for fila in TEXTOS}
        for fila in TextoPortal.objects.filter(status=True):
            salida[fila.clave] = (getattr(fila, idioma, '') if idioma != 'es' else '') or fila.es
        return salida

    return cache.get_or_set(TextoPortal.CACHE_CLAVE.format(idioma), _armar, 300)


def formatear(texto, **valores):
    """Reemplaza `{clave}` por su valor; deja intacto el resto del texto."""
    for clave, valor in valores.items():
        texto = texto.replace('{' + clave + '}', str(valor or ''))
    return texto


def con_marca(textos, empresa, marca):
    """Reemplaza {empresa} (nombre del portal) y {marca} (nombre de la empresa en Configuración) en los textos."""
    return {clave: formatear(texto, empresa=empresa, marca=marca) if '{' in texto else texto
            for clave, texto in textos.items()}


def portal_principal():
    from .models import Portal
    return Portal.objects.filter(status=True, activo=True, principal=True).first()


def contexto_publico(request, data, portal=None, preferido=None):
    """Completa `data` (ya pasado por `addData`) con idioma, textos con la marca y el contacto del portal:
    teléfono del portal, si no el de la empresa; correo de la empresa. Devuelve los textos."""
    idioma = idioma_de(request, preferido)
    marca = data['confi'].nombre_empresa or ''
    t = con_marca(textos(idioma), (portal.nombre if portal else '') or marca, marca)
    data.update({
        'idioma': idioma,
        't': t,
        'contacto_telefono': (portal.telefono_atencion if portal else '') or data.get('telefonoempresa', ''),
        'contacto_correo': data['confi'].email or '',
    })
    return t


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
        'ruta': f'/{p.slug}/',
        'sitio_web': p.sitio_web,
        'atencion': atencion_de(p, t),
        'partes': [{'nombre': nombre_producto(s, idioma), 'descripcion': descripcion_producto(s, idioma),
                    'slug': s.slug, 'ruta': f'/{p.slug}/{s.slug}/'}
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
