"""Alertas internas de la agenda (para el equipo, no para el cliente).

- `preferencia_de(usuario)` — preferencias personales, creadas con los valores por defecto.
- `alertas_pendientes(usuario, ahora)` — citas que entran en la ventana de aviso: las consulta el JS
  global cada minuto para la alerta en pantalla.
- `generar_avisos(ahora)` — cron: por cada cita que entra en la ventana de aviso de cada participante,
  crea la `Notificacion` y manda el push una sola vez (la propia Notificacion es la guarda).
- `avisar_asignacion(cita)` — notificación (+ correo si lo pidió) a los participantes de una cita nueva.
- `avisar_solicitud_nueva(solicitud_pk, autor_id)` — líder y responsables del equipo cuando entra una solicitud a la cola.
- `avisar_miembro_equipo(miembro, agregado, autor_id)` — al usuario que entra o sale de un equipo.
- `avisar_google_desconectado(conexion)` — notificación cuando Google rechaza el token.
- `avisar_tarde(cita, usuario, minutos)` — «llego tarde»: anota, avisa a los demás y manda correo al cliente.
"""
import logging
from datetime import datetime, timedelta

from django.template.loader import get_template
from django.utils.formats import date_format

from core import correos
from core.funciones import notificacion
from seguridad.models import Configuracion, Notificacion, ParametroSistema
from .funciones_citas import anotar, lider_de, responsables_de
from .models import Cita, ParticipanteCita, PreferenciaAgenda, Solicitud

logger = logging.getLogger(__name__)
TITULO_AVISO = 'Tu cita empieza pronto'
TITULO_ASIGNACION = 'Te asignaron una cita'
TITULO_GOOGLE = 'Google Calendar se desconectó'
TITULO_TARDE = 'Un compañero llega tarde'
TITULO_SOLICITUD = 'Nueva solicitud en la cola'
TITULO_EQUIPO_ALTA = 'Te agregaron a un equipo'
TITULO_EQUIPO_BAJA = 'Te quitaron de un equipo'


def _default_aviso():
    try:
        return int(ParametroSistema.valor_de('agenda_aviso_previo_min', 15))
    except (TypeError, ValueError):
        return 15


def preferencia_de(usuario):
    pref, _ = PreferenciaAgenda.objects.get_or_create(usuario=usuario, defaults={'status': True, 'aviso_previo_min': _default_aviso()})
    if not pref.status:
        pref.status = True
        pref.save()
    return pref


def _url(cita):
    return f'/agenda/citas/{cita.pk}/'


def _ya_avisada(usuario, cita, titulo):
    return Notificacion.objects.filter(destinatario=usuario, url=_url(cita), titulo=titulo).exists()


def alertas_pendientes(usuario, ahora=None):
    ahora = ahora or datetime.now()
    pref = preferencia_de(usuario)
    if not pref.alerta_pantalla:
        return []
    tope = ahora + timedelta(minutes=pref.aviso_previo_min)
    citas = (Cita.objects.filter(status=True, estado='confirmada', inicio__lte=tope, fin__gt=ahora,
                                 participantes__usuario=usuario, participantes__status=True)
             .select_related('cliente').distinct().order_by('inicio'))
    salida = []
    for c in citas:
        faltan = int((c.inicio - ahora).total_seconds() // 60)
        salida.append({'id': c.pk, 'codigo': c.codigo, 'titulo': c.titulo, 'cliente': str(c.cliente),
                       'inicio': c.inicio.strftime('%H:%M'), 'faltan': faltan, 'meet': c.enlace_meet, 'url': _url(c)})
    return salida


def generar_avisos(ahora=None):
    ahora = ahora or datetime.now()
    creados = 0
    tope = ahora + timedelta(hours=2)
    participaciones = (ParticipanteCita.objects.filter(status=True, cita__status=True, cita__estado='confirmada',
                                                        cita__inicio__gt=ahora, cita__inicio__lte=tope)
                       .select_related('cita', 'cita__cliente', 'usuario'))
    for p in participaciones:
        pref = preferencia_de(p.usuario)
        if p.cita.inicio - timedelta(minutes=pref.aviso_previo_min) > ahora:
            continue
        if _ya_avisada(p.usuario, p.cita, TITULO_AVISO):
            continue
        cuerpo = f'{p.cita.inicio:%H:%M} · {p.cita.titulo} con {p.cita.cliente}.'
        notificacion(TITULO_AVISO, cuerpo, p.usuario, _url(p.cita), 1, tipo=1)
        if pref.alerta_push:
            try:
                from pwa.notificaciones import enviar_push_usuario
                enviar_push_usuario(p.usuario, TITULO_AVISO, cuerpo, url=p.cita.enlace_meet or _url(p.cita),
                                    tag=f'cita-{p.cita.pk}', require_interaction=True)
            except Exception as ex:
                logger.warning('Push de aviso falló para %s: %s', p.usuario, ex)
        creados += 1
    return creados


def avisar_asignacion(cita):
    cita = Cita.objects.select_related('cliente', 'organizador').get(pk=cita.pk)
    autor_id = cita.organizador_id
    for p in cita.participantes.filter(status=True).select_related('usuario'):
        if p.usuario_id == autor_id:
            continue
        cuerpo = f'{date_format(cita.inicio, "D d M H:i")} · {cita.titulo} con {cita.cliente}.'
        notificacion(TITULO_ASIGNACION, cuerpo, p.usuario, _url(cita), 2, tipo=1)
        pref = preferencia_de(p.usuario)
        if pref.alerta_correo and p.usuario.email:
            try:
                html = get_template('email/cita_asignada.html').render({
                    'cita': cita, 'usuario': p.usuario, 'nombreempresa': Configuracion.get_instancia().nombre_empresa or 'Turno',
                    'sucursal': Configuracion.get_instancia().nombre_empresa or 'Turno',
                    'fecha_larga': date_format(cita.inicio, r'l j \d\e F \d\e Y').capitalize()})
                correos.despachar(correos.armar(f'Te asignaron una cita el {cita.inicio:%d/%m %H:%M} · {cita.codigo}', html, to=[p.usuario.email]))
            except Exception as ex:
                logger.warning('Correo de asignación falló para %s: %s', p.usuario, ex)


def avisar_solicitud_nueva(solicitud_pk, autor_id=None):
    try:
        solicitud = Solicitud.objects.select_related('cliente', 'equipo', 'equipo__lider', 'equipo__proyecto__lider').get(pk=solicitud_pk)
        equipo = solicitud.equipo
        if equipo is None:
            return
        destinatarios = {u.pk: u for u in responsables_de(equipo)}
        lider = lider_de(equipo)
        if lider:
            destinatarios[lider.pk] = lider
        pedido = 'pidió que le llamen' if solicitud.telefono_para_llamar else 'dejó una solicitud'
        cuerpo = f'{solicitud.cliente} {pedido}. {solicitud.motivo or solicitud.codigo}'[:300]
        for usuario in destinatarios.values():
            if usuario.pk != autor_id:
                notificacion(TITULO_SOLICITUD, cuerpo, usuario, '/agenda/cola/', 2, tipo=1)
    except Exception as ex:
        logger.warning('Aviso de la solicitud %s falló: %s', solicitud_pk, ex)


def avisar_miembro_equipo(miembro, agregado, autor_id=None):
    if miembro.usuario_id == autor_id:
        return
    try:
        if agregado:
            titulo, cuerpo = TITULO_EQUIPO_ALTA, f'Ahora eres {miembro.get_rol_display().lower()} del equipo {miembro.equipo}.'
        else:
            titulo, cuerpo = TITULO_EQUIPO_BAJA, f'Ya no formas parte del equipo {miembro.equipo}.'
        notificacion(titulo, cuerpo, miembro.usuario, '/agenda/mi-dia/', 3, tipo=1)
    except Exception as ex:
        logger.warning('Aviso de equipo para %s falló: %s', miembro.usuario, ex)


def avisar_google_desconectado(conexion):
    url = '/agenda/aplicaciones/'
    if Notificacion.objects.filter(destinatario=conexion.usuario, url=url, titulo=TITULO_GOOGLE, leido=False).exists():
        return
    notificacion(TITULO_GOOGLE, 'Google rechazó el acceso: vuelve a conectar tu cuenta en Conexiones para que tus citas sigan llegando a tu calendario.',
                 conexion.usuario, url, 3, tipo=1)


def avisar_tarde(cita, usuario, minutos, request=None):
    nombre = usuario.get_full_name() or usuario.username
    anotar(cita, 'Llega tarde', f'{nombre} avisó que llega {minutos} min tarde.', usuario)
    for p in cita.participantes.filter(status=True).exclude(usuario=usuario).select_related('usuario'):
        notificacion(TITULO_TARDE, f'{nombre} llega {minutos} min tarde a {cita.titulo} ({cita.inicio:%H:%M}).', p.usuario, _url(cita), 2, tipo=1)
    if cita.cliente.correo:
        confi = Configuracion.get_instancia()
        html = get_template('email/cita_tarde.html').render({
            'cita': cita, 'cliente': cita.cliente, 'minutos': minutos,
            'nombreempresa': confi.nombre_empresa or 'Turno', 'sucursal': confi.nombre_empresa or 'Turno'})
        correos.despachar(correos.armar(f'Empezamos unos minutos tarde · cita {cita.codigo}', html, to=[cita.cliente.correo]))
