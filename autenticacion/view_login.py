from django.contrib.auth import logout
from django.shortcuts import redirect

from seguridad.cambiar_sesion_view import COOKIE_REGRESO


def logout_user(request):
    logout(request)
    # SEGURIDAD: el logout deliberado también corta cualquier suplantación en curso. La cookie
    # firmada de «regresar a mi sesión» sobrevivía al logout y, como regresarSesionView la
    # aceptaba, quedaba como una credencial de acceso password-less al usuario original.
    respuesta = redirect('/')
    respuesta.delete_cookie(COOKIE_REGRESO)
    return respuesta
