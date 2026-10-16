"""Envío de correo a partir de una plantilla HTML.

Renderiza y delega en `core.correos.despachar`, que es el único lugar donde se manda correo
(hilo capado). Antes esta función arrancaba un `EmailThread` propio
por llamada, sin tope, dentro del request.
"""
from django.core.mail import get_connection
from django.template.loader import get_template

from backcalendar.settings import EMAIL_USE_TLS, EMAIL_USE_SSL, EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, \
    EMAIL_HOST_PASSWORD, BASE_URL_PRODUCCION
from core.correos import armar, despachar


def conectar_cuenta():
    conectar = get_connection(use_tls=EMAIL_USE_TLS, use_ssl=EMAIL_USE_SSL, host=EMAIL_HOST, port=EMAIL_PORT,
                              username=EMAIL_HOST_USER, password=EMAIL_HOST_PASSWORD)
    return conectar


def send_html_mail(subject, html_template, datos, recipient_list, recipient_list_cc, adjuntosrender=None,
                   adjuntossave=None, coneccion=None):
    try:
        if not (recipient_list or recipient_list_cc):
            return
        template = get_template(html_template)
        datos['BASE_URL_PRODUCCION'] = BASE_URL_PRODUCCION
        html_content = template.render(datos)

        # `adjuntossave` acepta rutas o campos de archivo; se normaliza a rutas.
        rutas = []
        for adjunto in adjuntossave or []:
            rutas.append(adjunto if isinstance(adjunto, str) else adjunto.file.name)

        despachar(armar(
            subject, html_content,
            to=recipient_list, cc=recipient_list_cc,
            adjuntos_rutas=rutas, adjuntos_render=adjuntosrender,
        ))
    except Exception as ex:
        import logging
        logging.getLogger(__name__).warning('No se pudo preparar el correo «%s»: %s', subject, ex)
