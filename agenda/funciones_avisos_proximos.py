"""Aviso «empieza en 10 minutos» por correo y web push (cron `avisos_proximos`).

`enviar_avisos_proximos(ahora=None)` recorre las citas activas y las reuniones propias que empiezan
dentro de los próximos `MINUTOS_AVISO` minutos y avisa una sola vez por usuario y canal:

- Cita: responsables asignados y el usuario del panel que la agendó (una reserva del portal no tiene
  autor en el panel, así que solo avisa al responsable).
- Reunión: el organizador.

`AvisoProximo` (inmutable) es la evidencia y la guarda contra duplicados. Devuelve (enviados, fallidos).
"""
import logging
from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.template.loader import get_template
from django.utils.formats import date_format

from core import correos
from seguridad.models import Configuracion
from .models import ESTADOS_CITA_ACTIVOS, AvisoProximo, Cita, Reunion

logger = logging.getLogger(__name__)
MINUTOS_AVISO = 10


def enviar_avisos_proximos(ahora=None):
    ahora = ahora or datetime.now()
    tope = ahora + timedelta(minutes=MINUTOS_AVISO)
    enviados = fallidos = 0
    citas = (Cita.objects.filter(status=True, estado__in=ESTADOS_CITA_ACTIVOS, inicio__gt=ahora, inicio__lte=tope)
             .select_related('cliente', 'producto', 'usuario_creacion', 'organizador'))
    for cita in citas:
        for usuario in destinatarios_cita(cita):
            ok, ko = _avisar(usuario, _contenido_cita(cita, ahora), cita=cita)
            enviados, fallidos = enviados + ok, fallidos + ko
    reuniones = (Reunion.objects.filter(status=True, eliminada=False, inicio__gt=ahora, inicio__lte=tope)
                 .select_related('organizador'))
    for reunion in reuniones:
        if reunion.organizador.is_active:
            ok, ko = _avisar(reunion.organizador, _contenido_reunion(reunion, ahora), reunion=reunion)
            enviados, fallidos = enviados + ok, fallidos + ko
    return enviados, fallidos


def destinatarios_cita(cita):
    usuarios = {p.usuario.pk: p.usuario for p in cita.participantes.filter(status=True, rol='responsable')
                .select_related('usuario')}
    if not usuarios:
        usuarios[cita.organizador.pk] = cita.organizador
    autor = cita.usuario_creacion
    if autor is not None and autor.is_staff:
        usuarios.setdefault(autor.pk, autor)
    return [u for u in usuarios.values() if u.is_active]


def _faltan(inicio, ahora):
    return max(1, int((inicio - ahora).total_seconds() // 60))


def _contenido_cita(cita, ahora):
    faltan = _faltan(cita.inicio, ahora)
    return {
        'titulo': f'Tu cita empieza en {faltan} min',
        'cuerpo': f'{cita.inicio:%H:%M} · {cita.titulo} con {cita.cliente}.',
        'asunto': f'Tu cita {cita.codigo} empieza en {faltan} minutos',
        'nombre': cita.titulo,
        'detalle': f'Cliente: {cita.cliente}',
        'inicio': cita.inicio,
        'faltan': faltan,
        'enlace': cita.enlace_meet,
        'url': f'/agenda/citas/{cita.pk}/',
        'tag': f'proxima-cita-{cita.pk}',
    }


def _contenido_reunion(reunion, ahora):
    faltan = _faltan(reunion.inicio, ahora)
    return {
        'titulo': f'Tu reunión empieza en {faltan} min',
        'cuerpo': f'{reunion.inicio:%H:%M} · {reunion.titulo}.',
        'asunto': f'Tu reunión «{reunion.titulo}» empieza en {faltan} minutos',
        'nombre': reunion.titulo,
        'detalle': reunion.lugar,
        'inicio': reunion.inicio,
        'faltan': faltan,
        'enlace': reunion.enlace_videollamada,
        'url': '/agenda/mi-agenda/',
        'tag': f'proxima-reunion-{reunion.pk}',
    }


def _avisar(usuario, contenido, cita=None, reunion=None):
    ya = set(AvisoProximo.objects.filter(usuario=usuario, cita=cita, reunion=reunion).values_list('canal', flat=True))
    enviados = fallidos = 0
    for canal, enviar in (('correo', _enviar_correo), ('push', _enviar_push)):
        if canal in ya:
            continue
        try:
            detalle = enviar(usuario, contenido)
            exito = True
        except Exception as ex:
            logger.warning('Aviso próximo por %s a %s falló: %s', canal, usuario, ex)
            detalle, exito = str(ex)[:300], False
        try:
            with transaction.atomic():
                AvisoProximo.objects.create(cita=cita, reunion=reunion, usuario=usuario, canal=canal,
                                            exito=exito, detalle=detalle)
        except IntegrityError:
            continue
        if exito:
            enviados += 1
        else:
            fallidos += 1
    return enviados, fallidos


def _enviar_correo(usuario, contenido):
    if not usuario.email:
        raise ValueError('El usuario no tiene correo')
    confi = Configuracion.get_instancia()
    html = get_template('email/aviso_proximo.html').render({
        'usuario': usuario, 'aviso': contenido,
        'hora': contenido['inicio'].strftime('%H:%M'),
        'fecha_larga': date_format(contenido['inicio'], r'l j \d\e F').capitalize(),
        'nombreempresa': confi.nombre_empresa or 'Turno', 'sucursal': confi.nombre_empresa or 'Turno'})
    correos.enviar_ahora(correos.armar(contenido['asunto'], html, to=[usuario.email]))
    return usuario.email


def _enviar_push(usuario, contenido):
    from pwa.notificaciones import enviar_push_usuario
    if not enviar_push_usuario(usuario, contenido['titulo'], contenido['cuerpo'],
                               url=contenido['enlace'] or contenido['url'], tag=contenido['tag'],
                               require_interaction=True):
        raise ValueError('Sin suscripción push activa o el envío fue rechazado')
    return 'push'
