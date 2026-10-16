from django.contrib.auth import logout, login
from django.core import signing
from django.shortcuts import redirect
from django.contrib import messages
from autenticacion.models import Usuario
from core.funciones import log

# El respaldo del "regresar a mi sesión" viaja en una cookie FIRMADA, además de la sesión:
# la sesión se recambia entera en cada logout/login (y cualquier flujo que la pise en el
# medio — visto en producción 2026-08-19 — dejaba al admin sin camino de vuelta y encima
# se lo deslogueaba). La cookie va firmada con SECRET_KEY (infalsificable), es HttpOnly y
# caduca sola, así que solo existe si un superusuario hizo el cambio desde acá.
# Público (COOKIE_REGRESO) para que el logout pueda borrarla; el alias _COOKIE_REGRESO se
# conserva para el uso interno del módulo.
COOKIE_REGRESO = 'sesion_regreso'
_COOKIE_REGRESO = COOKIE_REGRESO
_SAL_REGRESO = 'seguridad.cambiar_sesion.regreso'
_MAX_EDAD_REGRESO = 60 * 60 * 8  # 8 horas: más que una jornada de soporte, menos que un olvido.


def cambiarSesionView(request):
    # SOLO superusuarios: sin este guard, cualquier sesión (incluso anónima) podía
    # volverse admin con /seguridad/cambiar-sesion/?pk=1 (hallazgo 2026-08-19).
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para cambiar de sesión.')
        return redirect('/panel/' if request.user.is_authenticated else '/')

    user_pk = request.GET.get('pk')
    path = request.GET.get('path') or '/'
    pkUserAnterior = request.user.pk
    try:
        userNuevaSesion = Usuario.objects.get(is_active=True, id=user_pk)
    except (Usuario.DoesNotExist, ValueError, TypeError):
        messages.error(request, 'El usuario elegido no existe o está inactivo.')
        return redirect('/panel/')

    # El ACTO de suplantar queda auditado (Héctor 2026-08-21): antes solo se marcaban las
    # acciones DURANTE la suplantación — entrar, mirar y salir no dejaba rastro. Se registra
    # ANTES del logout para que la fila quede atribuida al ADMIN real.
    log(f"SUPLANTACIÓN: {request.user.username} inicia sesión como {userNuevaSesion.username} "
        f"({userNuevaSesion.get_full_name()})", request, "change")
    logout(request)
    login(request, userNuevaSesion)
    request.session['user_anterior'] = pkUserAnterior
    request.session['url'] = path
    messages.success(request, "Ahora te encuentras logueado con el usuario {} - {}".format(userNuevaSesion.username,
                                                                                           userNuevaSesion.get_full_name()))
    respuesta = redirect('/panel/')
    respuesta.set_cookie(
        _COOKIE_REGRESO,
        signing.dumps({'user': pkUserAnterior, 'url': path}, salt=_SAL_REGRESO),
        max_age=_MAX_EDAD_REGRESO, httponly=True, secure=request.is_secure(), samesite='Lax',
    )
    return respuesta


def _leer_cookie_regreso(request):
    """pk del usuario original guardado en la cookie firmada, o None si no hay/expiró/es inválida."""
    crudo = request.COOKIES.get(_COOKIE_REGRESO)
    if not crudo:
        return None
    try:
        return signing.loads(crudo, salt=_SAL_REGRESO, max_age=_MAX_EDAD_REGRESO)
    except signing.BadSignature:
        return None


def regresarSesionView(request):
    # SEGURIDAD: la cookie firmada dice A QUÉ sesión volver, no ES una credencial de acceso.
    # Una request ANÓNIMA con la cookie presente lograba loguearse como el superusuario
    # original sin contraseña (la cookie sobrevivía al logout). Se exige que ya haya alguien
    # autenticado: el camino legítimo de regreso siempre parte de una sesión suplantada activa.
    if not request.user.is_authenticated:
        respuesta = redirect('/')
        respuesta.delete_cookie(_COOKIE_REGRESO)
        return respuesta

    respaldo = _leer_cookie_regreso(request) or {}
    pk_anterior = request.session.get('user_anterior') or respaldo.get('user')
    url_guardada = request.session.get('url') or respaldo.get('url') or '/panel/'
    path = request.GET.get('path') or url_guardada

    if not pk_anterior:
        # SIN logout: cerrarle la sesión al usuario porque no encontramos a dónde regresar
        # solo empeora las cosas (era el comportamiento viejo y desconcertaba).
        messages.warning(request, 'No se encontró una sesión anterior a la que regresar.')
        return redirect('/panel/' if request.user.is_authenticated else '/')

    try:
        userAnteriorSesion = Usuario.objects.get(is_active=True, id=pk_anterior)
    except Usuario.DoesNotExist:
        messages.error(request, 'No se pudo recuperar tu sesión anterior (el usuario ya no existe o está inactivo).')
        respuesta = redirect('/panel/' if request.user.is_authenticated else '/')
        respuesta.delete_cookie(_COOKIE_REGRESO)
        return respuesta

    if request.user.is_authenticated and request.session.get('user_anterior'):
        log(f"SUPLANTACIÓN: fin — {userAnteriorSesion.username} deja la sesión de "
            f"{request.user.username} y regresa a su cuenta", request, "change",
            user=userAnteriorSesion)
    logout(request)
    login(request, userAnteriorSesion)
    messages.success(request, "Regresaste a tu sesión {} - {}".format(userAnteriorSesion.username,
                                                                      userAnteriorSesion.get_full_name()))
    respuesta = redirect(path)
    respuesta.delete_cookie(_COOKIE_REGRESO)
    return respuesta
