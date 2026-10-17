"""Correos y avisos internos del ciclo de una cita: agendada, reprogramada y cancelada.

- `avisar_reserva(cita_pk, url_cita, url_cliente)` — confirmación al cliente y aviso al líder del equipo.
- `avisar_reprogramacion(cita_pk, inicio_anterior, fin_anterior, por_cliente, autor_id)` — al cliente y al líder.
- `avisar_cancelacion(cita_pk, por_cliente, autor_id)` — al cliente y al líder.

El cliente recibe el correo en su idioma (`cita.idioma`) con los textos de `textos_portal` y, si la cita sigue
vigente, el QR de su enlace personal como imagen en línea; el líder, en español,
por correo y con una `Notificacion` del panel. Se llaman desde `transaction.on_commit` y nunca lanzan: si algo
falla queda en el log y la cita sigue su curso. Al líder no se le avisa de lo que él mismo hizo (`autor_id`).
"""
import logging

from django.utils import translation
from django.utils.formats import date_format

from core.email_config import send_html_mail
from core.funciones import notificacion
from seguridad.models import Configuracion
from . import funciones_tokens
from .models import Cita

logger = logging.getLogger(__name__)

QR_CID = 'qr-cita'
TITULOS_LIDER = {
    'reservada': 'Nueva cita agendada',
    'movida': 'Una cita cambió de fecha',
    'cancelada': 'Se canceló una cita',
}


def avisar_reserva(cita_pk, url_cita, url_cliente):
    cita = _cita(cita_pk)
    _al_cliente(cita, 'reservada', url_cita=url_cita, url_cliente=url_cliente)
    _al_lider(cita, 'reservada', por_cliente=True)


def avisar_reprogramacion(cita_pk, inicio_anterior, fin_anterior, por_cliente=False, autor_id=None):
    cita = _cita(cita_pk)
    _al_cliente(cita, 'movida', anterior=(inicio_anterior, fin_anterior), por_cliente=por_cliente)
    _al_lider(cita, 'movida', anterior=(inicio_anterior, fin_anterior), por_cliente=por_cliente, autor_id=autor_id)


def avisar_cancelacion(cita_pk, por_cliente=False, autor_id=None):
    cita = _cita(cita_pk)
    _al_cliente(cita, 'cancelada', por_cliente=por_cliente)
    _al_lider(cita, 'cancelada', por_cliente=por_cliente, autor_id=autor_id)


def _al_cliente(cita, evento, url_cita='', url_cliente='', anterior=None, por_cliente=True):
    try:
        if not cita.cliente.correo:
            return
        from . import funciones_portal
        idioma = cita.idioma if cita.idioma in funciones_portal.IDIOMAS_PORTAL else 'es'
        confi = Configuracion.get_instancia()
        portal = _portal(cita)
        marca = confi.nombre_empresa or ''
        empresa = (portal.nombre if portal else '') or marca
        t = funciones_portal.con_marca(funciones_portal.textos(idioma), empresa, marca)
        base = funciones_tokens.base_publica()
        if evento != 'cancelada' and not url_cita:
            url_cita = funciones_tokens.url_cita(funciones_tokens.emitir('cita', cita=cita))
        with translation.override(idioma):
            datos = {
                **_datos_comunes(cita, confi, idioma, t['formato_fecha_larga']),
                't': t,
                'evento': evento,
                'por_cliente': por_cliente,
                'producto_nombre': funciones_portal.nombre_producto(cita.producto, idioma) if cita.producto_id else cita.titulo,
                'atencion': funciones_portal.atencion_de(cita.producto, t) if cita.producto_id else '',
                'saludo': funciones_portal.formatear(t['em_hola'], nombre=cita.cliente.nombres.split(' ')[0]),
                'texto': _texto_cliente(t, evento, por_cliente),
                'url_cita': url_cita,
                'url_cliente': url_cliente,
                'url_agendar': f'{base}/agendar/{cita.producto.slug}/' if cita.producto_id else f'{base}/',
                'ayuda_codigo': funciones_portal.formatear(t['em_codigo_ayuda'], sitio=f'{base}/mi-cita/'),
                'pie': funciones_portal.formatear(t['em_pie'], marca=confi.titulo or marca),
                'anterior': _anterior(anterior, t['formato_fecha_larga']),
            }
            asunto = funciones_portal.formatear(t[f'em_asunto_{evento}'], codigo=cita.codigo,
                                                fecha=date_format(cita.inicio, t['formato_fecha']), hora=f'{cita.inicio:%H:%M}')
            adjuntos = []
            if evento != 'cancelada':
                adjuntos.append({'filename': f'qr-{cita.codigo}.png', 'content': funciones_portal.qr_png(url_cita),
                                 'mimetype': 'image/png', 'cid': QR_CID})
                datos['qr_cid'] = QR_CID
            send_html_mail(asunto, 'email/cita_cliente.html', datos, [cita.cliente.correo], [], adjuntosrender=adjuntos)
    except Exception as ex:
        logger.warning('Correo al cliente de la cita %s (%s) falló: %s', cita.codigo, evento, ex)


def _al_lider(cita, evento, anterior=None, por_cliente=False, autor_id=None):
    try:
        lider = _lider(cita)
        if lider is None or lider.pk == autor_id:
            return
        confi = Configuracion.get_instancia()
        quien = 'El cliente' if por_cliente else 'El equipo'
        url_panel = f'/agenda/citas/{cita.pk}/'
        titulo = TITULOS_LIDER[evento]
        with translation.override('es'):
            fecha_corta = date_format(cita.inicio, r'l j \d\e F')
            cuerpo = f'{fecha_corta.capitalize()}, {cita.inicio:%H:%M} · {cita.titulo} ({cita.codigo}).'
            if evento != 'reservada':
                cuerpo = f'{quien} {"movió" if evento == "movida" else "canceló"} la cita. {cuerpo}'
            notificacion(titulo, cuerpo, lider, url_panel, 1 if evento == 'cancelada' else 2, tipo=1)
            if not lider.email:
                return
            datos = {
                **_datos_comunes(cita, confi, 'es', r'l j \d\e F \d\e Y'),
                'evento': evento,
                'titulo': titulo,
                'lider': lider,
                'quien': quien,
                'por_cliente': por_cliente,
                'anterior': _anterior(anterior, r'l j \d\e F \d\e Y'),
                'url_panel': f'{funciones_tokens.base_publica()}{url_panel}',
                'mensaje': cita.solicitud.mensaje if cita.solicitud_id else '',
                'telefono': cita.cliente.telefono or (cita.solicitud.telefono_para_llamar if cita.solicitud_id else ''),
            }
            send_html_mail(f'{titulo}: {cita.cliente.nombres} · {fecha_corta} {cita.inicio:%H:%M} · {cita.codigo}',
                           'email/cita_lider.html', datos, [lider.email], [])
    except Exception as ex:
        logger.warning('Aviso al líder de la cita %s (%s) falló: %s', cita.codigo, evento, ex)


def _cita(cita_pk):
    return (Cita.objects.select_related('cliente', 'cliente__portal_origen', 'producto', 'producto__portal',
                                        'producto__padre', 'equipo', 'equipo__lider', 'equipo__proyecto__lider',
                                        'organizador', 'solicitud')
            .get(pk=cita_pk))


def _portal(cita):
    return cita.producto.portal if cita.producto_id else cita.cliente.portal_origen


def _lider(cita):
    if cita.equipo_id is None:
        return None
    return cita.equipo.lider or (cita.equipo.proyecto.lider if cita.equipo.proyecto_id else None)


def _datos_comunes(cita, confi, idioma, formato_largo):
    return {
        'cita': cita,
        'cliente': cita.cliente,
        'fecha_larga': date_format(cita.inicio, formato_largo).capitalize(),
        'hora': f'{cita.inicio:%H:%M}',
        'hora_fin': f'{cita.fin:%H:%M}',
        'idioma': idioma,
        'nombreempresa': confi.titulo or confi.nombre_empresa or '',
        'logo': f'{funciones_tokens.base_publica()}{confi.logo_sistema_white.url}' if confi.logo_sistema_white else '',
    }


def _anterior(anterior, formato):
    if not anterior or not anterior[0]:
        return None
    inicio, fin = anterior
    return {'fecha': date_format(inicio, formato).capitalize(), 'hora': f'{inicio:%H:%M}', 'hora_fin': f'{fin:%H:%M}'}


def _texto_cliente(t, evento, por_cliente):
    if evento == 'reservada':
        return t['em_reservada_texto']
    return t[f'em_{evento}_texto_{"cliente" if por_cliente else "equipo"}']
