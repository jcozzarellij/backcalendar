"""Ciclo de vida de una cita: crear, mover, cancelar y cerrar, con su rastro en Google Calendar.

La base es la fuente de verdad: primero se escribe la cita y sus bloques (dentro de la transacción
del llamador, con `select_for_update` sobre los usuarios implicados); Google se actualiza después
y, si falla, la cita queda con `sincronizada_google=False` y el error guardado.

Interfaz:
- `codigo_cliente()`, `codigo_solicitud()`, `codigo_cita()` — códigos legibles únicos.
- `obtener_o_crear_cliente(nombres, correo, telefono, portal, request)`.
- `responsables_de(equipo)` — usuarios obligatorios del equipo; `copias_de(equipo)`.
- `crear_cita(...)` / `mover_cita(...)` / `cancelar_cita(...)` / `registrar_cierre(...)`.
- `sincronizar_google(cita)` — crea o actualiza el evento en el calendario del organizador.
"""
import secrets
import string
from datetime import timedelta

import logging

from django.db import transaction
from django.utils import timezone

from . import funciones_google
from .funciones_disponibilidad import bloques_propios, invalidar_google, ocupados_google
from .models import (ActividadCita, BloqueOcupado, Cita, Cliente, ConexionAplicacion, MiembroEquipo,
                     ParticipanteCita, Solicitud)

ALFABETO = string.ascii_uppercase.replace('O', '').replace('I', '') + string.digits.replace('0', '').replace('1', '')


logger = logging.getLogger(__name__)


def _codigo(prefijo, modelo, largo=6):
    while True:
        cuerpo = ''.join(secrets.choice(ALFABETO) for _ in range(largo))
        codigo = f'{prefijo}-{cuerpo[:4]}-{cuerpo[4:]}' if largo > 4 else f'{prefijo}-{cuerpo}'
        if not modelo.objects.filter(codigo=codigo).exists():
            return codigo


def codigo_cliente():
    return _codigo('C', Cliente, 5)


def codigo_solicitud():
    return _codigo('REQ', Solicitud, 5)


def codigo_cita():
    return _codigo('QW', Cita, 6)


def obtener_o_crear_cliente(nombres, correo, telefono='', portal=None, request=None, idioma='es'):
    correo = (correo or '').strip().lower()
    cliente = Cliente.objects.filter(correo__iexact=correo).first() if correo else None
    if cliente is None:
        cliente = Cliente(codigo=codigo_cliente(), nombres=nombres.strip(), correo=correo, telefono=telefono or '',
                          portal_origen=portal, idioma=idioma)
    else:
        cliente.status = True
        cliente.nombres = nombres.strip() or cliente.nombres
        cliente.telefono = telefono or cliente.telefono
    cliente.save(request)
    return cliente


def responsables_de(equipo):
    return [m.usuario for m in MiembroEquipo.objects.filter(status=True, equipo=equipo, rol='responsable')
            .select_related('usuario')]


def copias_de(equipo):
    return [m.usuario for m in MiembroEquipo.objects.filter(status=True, equipo=equipo, rol='copia')
            .select_related('usuario')]


def anotar(cita, accion, detalle='', autor=None):
    ActividadCita.objects.create(cita=cita, accion=accion, detalle=detalle[:300], autor=autor)


def _verificar_libres(usuarios, inicio, fin, excluir_cita=None):
    for usuario in usuarios:
        propios = BloqueOcupado.objects.filter(status=True, usuario=usuario, inicio__lt=fin, fin__gt=inicio)
        if excluir_cita is not None:
            propios = propios.exclude(cita=excluir_cita)
        if propios.exists():
            raise ValueError(f'{usuario.get_full_name() or usuario.username} ya tiene algo en ese horario.')
        if any(b_ini < fin and b_fin > inicio for b_ini, b_fin in ocupados_google(usuario, inicio, fin)):
            raise ValueError(f'{usuario.get_full_name() or usuario.username} está ocupado en Google Calendar a esa hora.')


def crear_cita(*, cliente, inicio, fin, organizador, titulo, equipo=None, proyecto=None, producto=None,
               solicitud=None, asignada_por='coordinador', idioma='es', request=None):
    """Crea la cita con sus participantes y bloques. Llamar dentro de `transaction.atomic()`."""
    if fin <= inicio:
        raise ValueError('La hora final debe ser posterior a la inicial.')
    responsables = responsables_de(equipo) if equipo else []
    copias = copias_de(equipo) if equipo else []
    obligatorios = list({u.pk: u for u in [organizador] + responsables}.values())
    from autenticacion.models import Usuario
    list(Usuario.objects.select_for_update().filter(pk__in=[u.pk for u in obligatorios]).order_by('pk'))
    _verificar_libres(obligatorios, inicio, fin)
    sesion = Cita.objects.filter(status=True, cliente=cliente).exclude(estado='cancelada').count() + 1
    cita = Cita(codigo=codigo_cita(), solicitud=solicitud, cliente=cliente, producto=producto, proyecto=proyecto,
                equipo=equipo, organizador=organizador, titulo=titulo, inicio=inicio, fin=fin, estado='confirmada',
                asignada_por=asignada_por, numero_sesion=sesion, idioma=idioma)
    cita.save(request)
    ParticipanteCita(cita=cita, usuario=organizador, rol='organizador').save(request)
    for u in responsables:
        if u.pk != organizador.pk:
            ParticipanteCita(cita=cita, usuario=u, rol='responsable').save(request)
    for u in copias:
        if u.pk != organizador.pk and u.pk not in {r.pk for r in responsables}:
            ParticipanteCita(cita=cita, usuario=u, rol='copia').save(request)
    for u in obligatorios:
        BloqueOcupado(usuario=u, inicio=inicio, fin=fin, fuente='cita', cita=cita).save(request)
    if solicitud is not None:
        solicitud.estado = 'asignada'
        solicitud.equipo = solicitud.equipo or equipo
        solicitud.save(request)
    autor = getattr(request, 'user', None) if request is not None else None
    anotar(cita, 'Cita creada', f'{inicio:%d/%m/%Y %H:%M} · asignada por {dict(Cita._meta.get_field("asignada_por").choices)[asignada_por].lower()}',
           autor if autor is not None and autor.is_authenticated else None)
    transaction.on_commit(lambda: sincronizar_google(cita))
    transaction.on_commit(lambda: _avisar_asignacion(cita))
    return cita


def _avisar_asignacion(cita):
    try:
        from .funciones_alertas import avisar_asignacion
        avisar_asignacion(cita)
    except Exception as ex:
        logger.warning('No se pudo avisar la asignación de %s: %s', cita.codigo, ex)


def _conexion_organizador(cita):
    return ConexionAplicacion.objects.filter(status=True, usuario=cita.organizador, proveedor='google', conectada=True).first()


def _invitados(cita):
    correos = [cita.cliente.correo] if cita.cliente.correo else []
    for p in cita.participantes.filter(status=True).select_related('usuario'):
        correo = (ConexionAplicacion.objects.filter(status=True, usuario=p.usuario, proveedor='google')
                  .values_list('cuenta', flat=True).first() or p.usuario.email)
        if correo and p.usuario_id != cita.organizador_id and correo not in correos:
            correos.append(correo)
    return correos


def sincronizar_google(cita):
    """Crea o actualiza el evento en el Google del organizador. Nunca lanza: deja el estado en la cita."""
    cita = Cita.objects.select_related('cliente', 'organizador').get(pk=cita.pk)
    conexion = _conexion_organizador(cita)
    if conexion is None:
        cita.sincronizada_google = False
        cita.error_google = 'El organizador no tiene Google Calendar conectado.'
        cita.save(update_fields=['sincronizada_google', 'error_google'])
        return False
    descripcion = f'Cita {cita.codigo} con {cita.cliente.nombres}.'
    if cita.producto_id:
        descripcion += f' Producto: {cita.producto}.'
    try:
        if cita.estado == 'cancelada':
            if cita.google_event_id:
                funciones_google.eliminar_evento(conexion, cita.google_event_id)
        elif cita.google_event_id:
            funciones_google.actualizar_evento(conexion, cita.google_event_id, inicio=cita.inicio, fin=cita.fin,
                                               titulo=cita.titulo, descripcion=descripcion)
        else:
            id_evento, meet, enlace = funciones_google.crear_evento(
                conexion, cita.titulo, cita.inicio, cita.fin, descripcion=descripcion, invitados=_invitados(cita),
                request_id=f'cita-{cita.pk}', extra={'cita_id': cita.pk, 'cita_codigo': cita.codigo})
            cita.google_event_id, cita.enlace_meet, cita.enlace_evento = id_evento or '', meet or '', enlace or ''
        cita.sincronizada_google = True
        cita.error_google = ''
    except funciones_google.ErrorGoogle as ex:
        cita.sincronizada_google = False
        cita.error_google = str(ex)[:300]
    cita.save(update_fields=['google_event_id', 'enlace_meet', 'enlace_evento', 'sincronizada_google', 'error_google'])
    invalidar_google(cita.organizador)
    return cita.sincronizada_google


def mover_cita(cita, inicio, fin, request=None, detalle=''):
    """Reprograma: revalida a todos los obligatorios y mueve sus bloques. Dentro de `atomic()`."""
    if fin <= inicio:
        raise ValueError('La hora final debe ser posterior a la inicial.')
    if cita.estado in ('cancelada', 'cerrada'):
        raise ValueError('Una cita cerrada o cancelada no se puede mover.')
    bloques = list(BloqueOcupado.objects.select_for_update().filter(status=True, cita=cita).select_related('usuario'))
    _verificar_libres([b.usuario for b in bloques], inicio, fin, excluir_cita=cita)
    anterior = f'{cita.inicio:%d/%m/%Y %H:%M}'
    cita.inicio, cita.fin = inicio, fin
    cita.save(request)
    for b in bloques:
        b.inicio, b.fin = inicio, fin
        b.save(request)
    autor = getattr(request, 'user', None) if request is not None else None
    anotar(cita, 'Cita reprogramada', f'De {anterior} a {inicio:%d/%m/%Y %H:%M}. {detalle}'.strip(),
           autor if autor is not None and autor.is_authenticated else None)
    transaction.on_commit(lambda: sincronizar_google(cita))
    return cita


def cancelar_cita(cita, motivo='', request=None):
    if cita.estado == 'cancelada':
        return cita
    cita.estado = 'cancelada'
    cita.motivo_cancelacion = motivo[:300]
    cita.save(request)
    for b in BloqueOcupado.objects.filter(status=True, cita=cita):
        b.status = False
        b.save(request)
    if cita.solicitud_id and cita.solicitud.estado == 'asignada':
        cita.solicitud.estado = 'cancelada'
        cita.solicitud.save(request)
    autor = getattr(request, 'user', None) if request is not None else None
    anotar(cita, 'Cita cancelada', motivo, autor if autor is not None and autor.is_authenticated else None)
    transaction.on_commit(lambda: sincronizar_google(cita))
    return cita


def registrar_cierre(cita, datos, usuario, request=None):
    from .models import CierreCita
    cierre = CierreCita.objects.filter(cita=cita).first() or CierreCita(cita=cita, registrado_por=usuario)
    for campo in ('resumen', 'pidio_proforma', 'fue_soporte', 'es_lead', 'asistio', 'tipo_reunion'):
        if campo in datos:
            setattr(cierre, campo, datos[campo])
    cierre.status = True
    cierre.registrado_por = usuario
    cierre.save(request)
    cita.estado = 'no_asistio' if not cierre.asistio else 'cerrada'
    cita.save(request)
    if cita.solicitud_id:
        cita.solicitud.estado = 'cerrada'
        cita.solicitud.save(request)
    anotar(cita, 'Cierre registrado', cierre.get_tipo_reunion_display(), usuario)
    return cierre


def citas_del_usuario(usuario, desde, hasta):
    return (Cita.objects.filter(status=True, inicio__lt=hasta, fin__gt=desde, participantes__usuario=usuario,
                                participantes__status=True)
            .exclude(estado='cancelada').select_related('cliente', 'proyecto', 'equipo', 'producto').distinct().order_by('inicio'))


def pendientes_de_cierre(usuario):
    ahora = timezone.now().replace(tzinfo=None) if timezone.is_aware(timezone.now()) else timezone.now()
    return (Cita.objects.filter(status=True, fin__lt=ahora, estado__in=('confirmada', 'pendiente', 'realizada'),
                                participantes__usuario=usuario, participantes__status=True)
            .select_related('cliente', 'proyecto').distinct().order_by('-inicio'))


def limite_pendientes(dias=30):
    return timedelta(days=dias)
