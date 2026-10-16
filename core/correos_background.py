"""Envío de correo con HTML ya renderizado (texto plano + alternativa HTML).

Es la puerta que usan las alertas del sistema y las pantallas de recuperación de cuenta, que
arman el HTML por su cuenta. Delega en `core.correos.despachar`: acá ya no vive ninguna clase de
hilo propia, ni se inicializa la aplicación WSGI al importar (lo hacía, dentro de un módulo que
importan las vistas).
"""
from core.correos import armar, despachar


def enviar_correo_html(datos):
    despachar(armar(
        datos.get('subject'),
        datos.get('html_message'),
        to=datos.get('to'),
        texto=datos.get('plain_message'),
        formato='alternativa',
    ))
