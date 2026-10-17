"""Único punto de envío de correo del proyecto.

Antes convivían dos implementaciones con la misma idea y el mismo nombre de clase:
`core.email_config.EmailThread` y `core.correos_background.EmailThread`. Las dos arrancaban un
hilo del sistema operativo por cada correo, sin cola ni tope, desde dentro del request — y como
los formularios públicos (registro, recuperar usuario, recuperar contraseña) mandan correo, cada
POST anónimo creaba un hilo y una conexión SMTP. Ahora las dos puertas de entrada arman el mismo
diccionario y lo despachan por acá.

Cómo se despacha: un hilo daemon CAPADO por semáforo. El cupo existe para que una ráfaga de correos no multiplique hilos dentro
     del worker web: los que no consiguen lugar se envían en línea, más lento pero acotado.
"""
import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)

_SEM_CORREO = threading.BoundedSemaphore(4)
_ESPERA_SLOT_SEG = 20


def armar(subject, html, *, to=None, cc=None, texto='', formato='html',
          adjuntos_rutas=None, adjuntos_render=None):
    """Normaliza un correo al diccionario que entienden el task y el hilo. Cada `adjuntos_render` es
    `{'filename', 'content', 'mimetype'}`; con `'cid'` va como imagen en línea para `<img src="cid:...">`."""
    return {
        'subject': subject or '',
        'html': html or '',
        'texto': texto or '',
        'formato': formato,
        'to': list(to or []),
        'cc': list(cc or []),
        'adjuntos_rutas': list(adjuntos_rutas or []),
        'adjuntos_render': list(adjuntos_render or []),
    }


def enviar_ahora(datos):
    """Envía el correo en el hilo que llame. Lo usa el hilo de despacho."""
    from django.core.mail import EmailMessage, EmailMultiAlternatives

    destinatarios = datos.get('to') or []
    copias = datos.get('cc') or []
    if not destinatarios and not copias:
        return False

    if datos.get('formato') == 'alternativa':
        msg = EmailMultiAlternatives(datos['subject'], datos.get('texto') or '',
                                     settings.DEFAULT_FROM_EMAIL, destinatarios)
        msg.mixed_subtype = 'related'
        msg.attach_alternative(datos.get('html') or '', 'text/html')
    else:
        msg = EmailMessage(datos['subject'], datos.get('html') or '',
                           settings.DEFAULT_FROM_EMAIL, destinatarios, bcc=copias)
        msg.content_subtype = 'html'

    for adjunto in datos.get('adjuntos_render') or []:
        if adjunto.get('cid'):
            msg.attach(_imagen_en_linea(adjunto))
            msg.mixed_subtype = 'related'
        else:
            msg.attach(adjunto.get('filename'), adjunto.get('content'), adjunto.get('mimetype'))
    for ruta in datos.get('adjuntos_rutas') or []:
        try:
            msg.attach_file(ruta)
        except Exception:
            logger.warning('correo: no pude adjuntar %s', ruta)

    try:
        msg.send()
        return True
    except Exception as ex:
        # El SMTP puede estar sin configurar (550) sin que eso sea un fallo del flujo que lo
        # disparó: el registro o la alerta ya se completaron. Queda en el log, no rompe nada.
        logger.warning('correo: no se pudo enviar «%s» (%s)', datos.get('subject'), ex)
        return False


def _imagen_en_linea(adjunto):
    """Imagen que el HTML muestra con `<img src="cid:...">` (p. ej. el QR de una cita), no como adjunto suelto."""
    from email.mime.image import MIMEImage
    imagen = MIMEImage(adjunto['content'], _subtype=(adjunto.get('mimetype') or 'image/png').split('/')[-1])
    imagen.add_header('Content-ID', f"<{adjunto['cid']}>")
    imagen.add_header('Content-Disposition', 'inline', filename=adjunto.get('filename') or f"{adjunto['cid']}.png")
    return imagen


def _en_hilo(datos):
    if not _SEM_CORREO.acquire(timeout=_ESPERA_SLOT_SEG):
        logger.warning('correo: sin cupo de hilo, «%s» se envía en línea.', datos.get('subject'))
        enviar_ahora(datos)
        return
    try:
        enviar_ahora(datos)
    finally:
        _SEM_CORREO.release()


def despachar(datos):
    """Manda el correo fuera del request. Nunca lanza: un correo caído no tumba el flujo."""
    try:
        threading.Thread(target=_en_hilo, args=(datos,), daemon=True).start()
    except Exception:
        logger.exception('correo: fallo despachando «%s»', datos.get('subject'))
