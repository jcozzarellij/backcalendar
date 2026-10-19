"""Inicio de sesión con Google (OAuth 2.0 + OpenID Connect, sin servicios externos). Reutiliza el
cliente OAuth de la configuración (el mismo de Google Calendar) con su propia URI de retorno.

Reglas: el switch `Configuracion.conexion_google` debe estar encendido, el correo de Google debe
estar verificado y su dominio cargado en `DominioCorreoPermitido`. Solo entran usuarios que ya
existen: la primera vez se busca el `Usuario` por email y se guarda el vínculo en `CuentaGoogle`
con el `sub` de Google; desde ahí se entra por el `sub`, aunque el email cambie.

Interfaz:
- `habilitado()` — el botón «Continuar con Google» debe mostrarse.
- `uri_retorno()` — URI que hay que registrar en Google Cloud.
- `url_inicio(request, siguiente)` — URL de Google a la que se redirige al usuario.
- `resolver_usuario(request)` — en el callback: devuelve el `Usuario` o lanza `ErrorLoginGoogle`.
"""
import os
import secrets

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import CuentaGoogle, Usuario

SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
CLAVE_SESION = 'google_login'


class ErrorLoginGoogle(Exception):
    """Motivo de rechazo que se muestra tal cual en /login/ (ya viene en español)."""


def habilitado():
    from agenda.funciones_google import configurada
    from seguridad.models import Configuracion
    return bool(Configuracion.get_instancia().conexion_google and configurada())


def uri_retorno():
    return f'{settings.BACKEND_PUBLIC_URL.rstrip("/")}/login/google/callback/'


def _cliente():
    from agenda.funciones_google import cliente_oauth
    return cliente_oauth()


def _flujo(cliente, state=None, code_verifier=None):
    from google_auth_oauthlib.flow import Flow
    redirect = uri_retorno()
    if redirect.startswith('http://'):
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    config = {'web': {
        'client_id': cliente['id'],
        'client_secret': cliente['secreto'],
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'redirect_uris': [redirect],
    }}
    return Flow.from_client_config(config, scopes=SCOPES, redirect_uri=redirect, state=state,
                                   code_verifier=code_verifier, autogenerate_code_verifier=False)


def _dominios_activos():
    from seguridad.models import DominioCorreoPermitido
    return list(DominioCorreoPermitido.objects.filter(status=True, activo=True).values_list('dominio', flat=True))


def url_inicio(request, siguiente=None):
    if not habilitado():
        raise ErrorLoginGoogle('El inicio de sesión con Google no está habilitado.')
    estado, nonce, verificador = secrets.token_urlsafe(24), secrets.token_urlsafe(24), secrets.token_urlsafe(64)
    request.session[CLAVE_SESION] = {'state': estado, 'nonce': nonce, 'verificador': verificador, 'next': siguiente or ''}
    extra = {}
    dominios = _dominios_activos()
    if len(dominios) == 1:
        extra['hd'] = dominios[0]
    url, _ = _flujo(_cliente(), state=estado, code_verifier=verificador).authorization_url(
        access_type='online', prompt='select_account', nonce=nonce, **extra)
    return url


def siguiente_guardado(request):
    return (request.session.pop(CLAVE_SESION, None) or {}).get('next') or ''


def resolver_usuario(request):
    """Valida el callback de Google y devuelve el usuario que inicia sesión."""
    guardado = request.session.pop(CLAVE_SESION, None) or {}
    request.session[CLAVE_SESION] = {'next': guardado.get('next', '')}
    if not habilitado():
        raise ErrorLoginGoogle('El inicio de sesión con Google no está habilitado.')
    if not guardado.get('state') or guardado['state'] != request.GET.get('state'):
        raise ErrorLoginGoogle('La solicitud no coincide con tu sesión. Vuelve a intentarlo.')
    if request.GET.get('error'):
        raise ErrorLoginGoogle('Cancelaste el inicio de sesión con Google.')
    codigo = request.GET.get('code')
    if not codigo:
        raise ErrorLoginGoogle('Google no devolvió el código de autorización.')

    cliente = _cliente()
    flujo = _flujo(cliente, state=guardado['state'], code_verifier=guardado.get('verificador'))
    try:
        flujo.fetch_token(code=codigo)
        datos = _verificar_id_token(flujo.credentials.id_token, cliente['id'])
    except ErrorLoginGoogle:
        raise
    except Exception as ex:
        raise ErrorLoginGoogle('No se pudo validar tu cuenta de Google. Vuelve a intentarlo.') from ex

    if datos.get('nonce') != guardado.get('nonce'):
        raise ErrorLoginGoogle('La respuesta de Google no corresponde a esta solicitud. Vuelve a intentarlo.')
    email = (datos.get('email') or '').strip().lower()
    if not email or not datos.get('email_verified'):
        raise ErrorLoginGoogle('Tu correo de Google no está verificado.')
    if email.rsplit('@', 1)[-1] not in _dominios_activos():
        raise ErrorLoginGoogle('Los correos de ese dominio no pueden iniciar sesión con Google.')

    usuario = _vincular(datos['sub'], email)
    if not (usuario.is_active and usuario.status):
        raise ErrorLoginGoogle('Tu usuario está inactivo. Comunícate con el administrador.')
    return usuario


def _verificar_id_token(token, client_id):
    from google.auth.transport import requests as transporte
    from google.oauth2 import id_token
    if not token:
        raise ErrorLoginGoogle('Google no devolvió la identidad de la cuenta.')
    return id_token.verify_oauth2_token(token, transporte.Request(), audience=client_id, clock_skew_in_seconds=10)


def _vincular(sub, email):
    with transaction.atomic():
        cuenta = CuentaGoogle.objects.select_for_update().select_related('usuario').filter(google_sub=sub, status=True).first()
        if cuenta is None:
            candidatos = list(Usuario.objects.filter(email__iexact=email, status=True, is_active=True)[:2])
            if not candidatos:
                raise ErrorLoginGoogle('No hay una cuenta asociada a este correo.')
            if len(candidatos) > 1:
                raise ErrorLoginGoogle('Este correo pertenece a más de un usuario. Pide al administrador que lo corrija.')
            usuario = candidatos[0]
            if CuentaGoogle.objects.filter(usuario=usuario, status=True).exists():
                raise ErrorLoginGoogle('Tu usuario ya está vinculado a otra cuenta de Google.')
            cuenta = CuentaGoogle(usuario=usuario, google_sub=sub)
        cuenta.email = email
        cuenta.ultimo_acceso = timezone.now()
        cuenta.save()
    return cuenta.usuario
