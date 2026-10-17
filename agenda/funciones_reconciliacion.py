"""Reconciliación periódica con Google Calendar (cron `reconciliar_google`).

Por cada cita confirmada futura:
- sin evento y con `error_google` → reintenta `sincronizar_google`;
- con evento → lo lee en Google: si está cancelado, la cita pasa a «pendiente» y se avisa al organizador;
  si lo movieron desde Google, se mueve aquí (bloques incluidos) y se anota; se refrescan el Meet y
  las respuestas de los invitados (`ParticipanteCita.respuesta`).
Después reintenta las reuniones propias que quedaron pendientes (`funciones_reuniones.sincronizar_pendientes`).
Devuelve un resumen con contadores. Nunca lanza por una cita: registra y sigue.
"""
import logging
from datetime import datetime, timedelta

from django.db import transaction

from core.funciones import notificacion
from . import funciones_google
from .funciones_citas import anotar, mover_cita, sincronizar_google
from .models import Cita, ConexionAplicacion, ParticipanteCita

logger = logging.getLogger(__name__)
RESPUESTAS = {'accepted': 'acepto', 'declined': 'rechazo', 'needsAction': 'pendiente', 'tentative': 'pendiente'}


def _conexion(cita):
    return ConexionAplicacion.objects.filter(status=True, usuario=cita.organizador, proveedor='google', conectada=True).first()


def _local(valor):
    return funciones_google._a_local(valor) if valor else None


def reconciliar(ahora=None, dias=30):
    ahora = ahora or datetime.now()
    resumen = {'revisadas': 0, 'reintentadas': 0, 'canceladas_en_google': 0, 'movidas_en_google': 0,
               'respuestas': 0, 'errores': 0}
    citas = (Cita.objects.filter(status=True, estado='confirmada', inicio__gte=ahora - timedelta(hours=1),
                                 inicio__lte=ahora + timedelta(days=dias))
             .select_related('organizador', 'cliente').order_by('inicio'))
    for cita in citas:
        resumen['revisadas'] += 1
        try:
            if not cita.google_event_id:
                if _conexion(cita) is not None:
                    resumen['reintentadas'] += 1
                    sincronizar_google(cita)
                continue
            conexion = _conexion(cita)
            if conexion is None:
                continue
            evento = funciones_google.obtener_evento(conexion, cita.google_event_id)
            if evento.get('status') == 'cancelled':
                with transaction.atomic():
                    cita.estado = 'pendiente'
                    cita.google_event_id = ''
                    cita.enlace_evento = ''
                    cita.sincronizada_google = False
                    cita.error_google = 'El evento fue eliminado en Google Calendar.'
                    cita.save(update_fields=['estado', 'google_event_id', 'enlace_evento', 'sincronizada_google', 'error_google'])
                    anotar(cita, 'Evento borrado en Google', 'Alguien eliminó el evento desde Google Calendar; la cita queda pendiente de confirmar.')
                    notificacion('Cita sin evento en Google', f'{cita.codigo} · {cita.titulo}: el evento fue borrado en Google. Confírmala o cancélala.',
                                 cita.organizador, f'/agenda/citas/{cita.pk}/', 3, tipo=1)
                resumen['canceladas_en_google'] += 1
                continue
            inicio = _local(evento.get('start', {}).get('dateTime'))
            fin = _local(evento.get('end', {}).get('dateTime'))
            if inicio and fin and (inicio != cita.inicio or fin != cita.fin):
                with transaction.atomic():
                    cita = Cita.objects.select_for_update().get(pk=cita.pk)
                    try:
                        mover_cita(cita, inicio, fin, None, 'Movida desde Google Calendar.')
                        resumen['movidas_en_google'] += 1
                    except ValueError as ex:
                        anotar(cita, 'Conflicto con Google', f'Movida en Google a {inicio:%d/%m %H:%M} pero aquí choca: {ex}')
                        notificacion('Conflicto con Google Calendar', f'{cita.codigo}: la movieron en Google a {inicio:%d/%m %H:%M} pero ese horario choca. Revísala.',
                                     cita.organizador, f'/agenda/citas/{cita.pk}/', 3, tipo=1)
            meet = evento.get('hangoutLink') or ''
            cambios = []
            if meet and meet != cita.enlace_meet:
                cita.enlace_meet = meet
                cambios.append('enlace_meet')
            if cita.sincronizada_google is False or cita.error_google:
                cita.sincronizada_google, cita.error_google = True, ''
                cambios += ['sincronizada_google', 'error_google']
            if cambios:
                cita.save(update_fields=cambios)
            respuestas = {(a.get('email') or '').lower(): RESPUESTAS.get(a.get('responseStatus'), 'pendiente')
                          for a in evento.get('attendees', [])}
            if respuestas:
                for p in ParticipanteCita.objects.filter(status=True, cita=cita).select_related('usuario'):
                    correo = (ConexionAplicacion.objects.filter(status=True, usuario=p.usuario, proveedor='google')
                              .values_list('cuenta', flat=True).first() or p.usuario.email or '').lower()
                    nueva = respuestas.get(correo)
                    if nueva and nueva != p.respuesta:
                        p.respuesta = nueva
                        p.save(update_fields=['respuesta'])
                        resumen['respuestas'] += 1
        except Exception as ex:
            resumen['errores'] += 1
            logger.warning('Reconciliación de %s falló: %s', cita.codigo, ex)
    try:
        from .funciones_reuniones import sincronizar_pendientes
        resumen['reuniones_pendientes'], resumen['reuniones_al_dia'] = sincronizar_pendientes()
    except Exception as ex:
        resumen['errores'] += 1
        logger.warning('Sincronizar reuniones pendientes falló: %s', ex)
    return resumen
