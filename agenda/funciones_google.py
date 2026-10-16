"""Conector de Google Calendar por usuario (OAuth): autorizar, renovar, libre/ocupado y eventos
con Meet. Las claves del cliente OAuth viven en `credenciales.json` (`GOOGLE_OAUTH_*`); el refresh
token de cada usuario, cifrado en `ConexionAplicacion`.

Interfaz:
- `configurada()` — hay cliente OAuth cargado.
- `url_autorizacion(request)` / `completar_autorizacion(request, usuario)` — flujo OAuth web.
- `probar(conexion)` — verifica el acceso al calendario y deja el estado en la conexión.
- `freebusy(conexion, desde, hasta)` — bloques ocupados como (inicio, fin) en hora local naive.
- `crear_evento(...)`, `actualizar_evento(...)`, `eliminar_evento(...)` — eventos con Meet.
- `desconectar(conexion)` — revoca el token y borra la conexión.
"""
import os
import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.utils import timezone

from .models import ConexionAplicacion

SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.freebusy',
    'https://www.googleapis.com/auth/calendar.calendarlist.readonly',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
]
CLAVE_ESTADO_SESION = 'google_oauth_state'
ZONA = ZoneInfo(settings.TIME_ZONE)


class ErrorGoogle(Exception):
    """Error al hablar con Google que la vista muestra al usuario tal cual (ya viene en español)."""


def configurada():
    return bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET)


def _config_cliente():
    return {'web': {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'redirect_uris': [settings.GOOGLE_OAUTH_REDIRECT_URI],
    }}


def _flujo(state=None):
    from google_auth_oauthlib.flow import Flow
    if settings.GOOGLE_OAUTH_REDIRECT_URI.startswith('http://'):
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    return Flow.from_client_config(_config_cliente(), scopes=SCOPES,
                                   redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI, state=state)


def url_autorizacion(request):
    if not configurada():
        raise ErrorGoogle('Google Calendar todavía no está configurado en el sistema.')
    estado = secrets.token_urlsafe(24)
    request.session[CLAVE_ESTADO_SESION] = estado
    url, _ = _flujo(state=estado).authorization_url(access_type='offline', prompt='consent',
                                                     include_granted_scopes='true')
    return url


def completar_autorizacion(request, usuario):
    """Canjea el `code` del callback, guarda el refresh token cifrado y devuelve la conexión."""
    estado = request.session.pop(CLAVE_ESTADO_SESION, None)
    if not estado or estado != request.GET.get('state'):
        raise ErrorGoogle('La autorización no coincide con la sesión. Vuelve a intentarlo.')
    if request.GET.get('error'):
        raise ErrorGoogle('Google no autorizó el acceso: ' + request.GET['error'])
    codigo = request.GET.get('code')
    if not codigo:
        raise ErrorGoogle('Google no devolvió el código de autorización.')
    flujo = _flujo(state=estado)
    try:
        flujo.fetch_token(code=codigo)
    except Exception as ex:
        raise ErrorGoogle('No se pudo completar la autorización con Google.') from ex
    credenciales = flujo.credentials
    if not credenciales.refresh_token:
        raise ErrorGoogle('Google no entregó el token de renovación. Quita el acceso de Turno en tu cuenta '
                          'de Google y vuelve a conectar.')
    cuenta = ''
    try:
        respuesta = requests.get('https://www.googleapis.com/oauth2/v3/userinfo',
                                 headers={'Authorization': f'Bearer {credenciales.token}'}, timeout=10)
        cuenta = (respuesta.json() or {}).get('email', '') if respuesta.ok else ''
    except requests.RequestException:
        cuenta = ''
    conexion = ConexionAplicacion.objects.filter(usuario=usuario, proveedor='google').first()
    if conexion is None:
        conexion = ConexionAplicacion(usuario=usuario, proveedor='google')
    conexion.status = True
    conexion.cuenta = cuenta
    conexion.refresh_token = credenciales.refresh_token
    conexion.scopes = ' '.join(credenciales.scopes or SCOPES)
    conexion.calendario_id = conexion.calendario_id or 'primary'
    conexion.conectada = True
    conexion.ultimo_error = ''
    conexion.ultima_verificacion = timezone.now()
    conexion.save(request)
    return conexion


def _marcar_error(conexion, mensaje, desconectar=False):
    conexion.ultimo_error = mensaje[:300]
    if desconectar:
        conexion.conectada = False
    conexion.save()
    if desconectar:
        try:
            from .funciones_alertas import avisar_google_desconectado
            avisar_google_desconectado(conexion)
        except Exception:
            pass


def credenciales_de(conexion):
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    if not conexion.conectada or not conexion.refresh_token:
        raise ErrorGoogle('La cuenta de Google no está conectada.')
    credenciales = Credentials(
        None, refresh_token=conexion.refresh_token, token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID, client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=conexion.scopes.split() or SCOPES,
    )
    try:
        credenciales.refresh(Request())
    except RefreshError as ex:
        detalle = str(ex)
        vencido = 'invalid_grant' in detalle
        _marcar_error(conexion, 'Google rechazó el token: hay que volver a conectar la cuenta.' if vencido
                      else f'No se pudo renovar el acceso a Google: {detalle}', desconectar=vencido)
        raise ErrorGoogle(conexion.ultimo_error) from ex
    return credenciales


def servicio_calendar(conexion):
    from googleapiclient.discovery import build
    return build('calendar', 'v3', credentials=credenciales_de(conexion), cache_discovery=False)


def _ejecutar(conexion, peticion):
    from googleapiclient.errors import HttpError
    try:
        return peticion.execute(num_retries=2)
    except HttpError as ex:
        codigo = getattr(ex.resp, 'status', '')
        mensaje = f'Google respondió {codigo} al consultar el calendario.'
        _marcar_error(conexion, mensaje, desconectar=codigo in (401, 403))
        raise ErrorGoogle(mensaje) from ex


def probar(conexion):
    servicio = servicio_calendar(conexion)
    calendario = _ejecutar(conexion, servicio.calendarList().get(calendarId=conexion.calendario_id or 'primary'))
    conexion.conectada = True
    conexion.ultimo_error = ''
    conexion.ultima_verificacion = timezone.now()
    if calendario.get('id') and '@' in calendario['id'] and not conexion.cuenta:
        conexion.cuenta = calendario['id']
    conexion.save()
    return calendario.get('summary') or calendario.get('id') or 'calendario'


def _a_iso(dt):
    return dt.replace(tzinfo=ZONA).isoformat() if dt.tzinfo is None else dt.astimezone(ZONA).isoformat()


def _a_local(texto):
    return datetime.fromisoformat(texto.replace('Z', '+00:00')).astimezone(ZONA).replace(tzinfo=None)


def freebusy(conexion, desde, hasta):
    servicio = servicio_calendar(conexion)
    calendario = conexion.calendario_id or 'primary'
    respuesta = _ejecutar(conexion, servicio.freebusy().query(body={
        'timeMin': _a_iso(desde), 'timeMax': _a_iso(hasta), 'timeZone': settings.TIME_ZONE,
        'items': [{'id': calendario}],
    }))
    ocupados = (respuesta.get('calendars') or {}).get(calendario, {}).get('busy', [])
    return [(_a_local(b['start']), _a_local(b['end'])) for b in ocupados]


def _cuerpo_evento(titulo, inicio, fin, descripcion='', invitados=(), meet=True, request_id=None, extra=None):
    cuerpo = {
        'summary': titulo,
        'description': descripcion or '',
        'start': {'dateTime': _a_iso(inicio), 'timeZone': settings.TIME_ZONE},
        'end': {'dateTime': _a_iso(fin), 'timeZone': settings.TIME_ZONE},
        'attendees': [{'email': correo} for correo in invitados if correo],
        'reminders': {'useDefault': True},
    }
    if extra:
        cuerpo['extendedProperties'] = {'private': {k: str(v) for k, v in extra.items()}}
    if meet:
        cuerpo['conferenceData'] = {'createRequest': {
            'requestId': request_id or secrets.token_urlsafe(12),
            'conferenceSolutionKey': {'type': 'hangoutsMeet'},
        }}
    return cuerpo


def crear_evento(conexion, titulo, inicio, fin, descripcion='', invitados=(), meet=True, request_id=None,
                 extra=None, avisar=True):
    """Crea el evento en el calendario de la conexión. Devuelve (id_evento, enlace_meet, enlace_evento)."""
    servicio = servicio_calendar(conexion)
    evento = _ejecutar(conexion, servicio.events().insert(
        calendarId=conexion.calendario_id or 'primary',
        body=_cuerpo_evento(titulo, inicio, fin, descripcion, invitados, meet, request_id, extra),
        conferenceDataVersion=1, sendUpdates='all' if avisar else 'none',
    ))
    return evento.get('id'), evento.get('hangoutLink', ''), evento.get('htmlLink', '')


def actualizar_evento(conexion, id_evento, inicio=None, fin=None, titulo=None, descripcion=None, avisar=True):
    servicio = servicio_calendar(conexion)
    cambios = {}
    if inicio is not None:
        cambios['start'] = {'dateTime': _a_iso(inicio), 'timeZone': settings.TIME_ZONE}
    if fin is not None:
        cambios['end'] = {'dateTime': _a_iso(fin), 'timeZone': settings.TIME_ZONE}
    if titulo is not None:
        cambios['summary'] = titulo
    if descripcion is not None:
        cambios['description'] = descripcion
    return _ejecutar(conexion, servicio.events().patch(
        calendarId=conexion.calendario_id or 'primary', eventId=id_evento, body=cambios,
        sendUpdates='all' if avisar else 'none',
    ))


def eliminar_evento(conexion, id_evento, avisar=True):
    from googleapiclient.errors import HttpError
    servicio = servicio_calendar(conexion)
    try:
        servicio.events().delete(calendarId=conexion.calendario_id or 'primary', eventId=id_evento,
                                 sendUpdates='all' if avisar else 'none').execute(num_retries=2)
    except HttpError as ex:
        if getattr(ex.resp, 'status', None) not in (404, 410):
            raise ErrorGoogle('Google no permitió cancelar el evento.') from ex


def desconectar(conexion, request=None):
    token = conexion.refresh_token
    if token:
        try:
            requests.post('https://oauth2.googleapis.com/revoke', params={'token': token},
                          headers={'content-type': 'application/x-www-form-urlencoded'}, timeout=10)
        except requests.RequestException:
            pass
    conexion.refresh_token = ''
    conexion.conectada = False
    conexion.ultimo_error = ''
    conexion.status = False
    conexion.save(request)


def obtener_evento(conexion, id_evento):
    """Evento tal como está hoy en Google: dict con `status` ('confirmed'/'cancelled'), `start`, `end`,
    `attendees` (con `responseStatus`) y `hangoutLink`."""
    servicio = servicio_calendar(conexion)
    return _ejecutar(conexion, servicio.events().get(calendarId=conexion.calendario_id or 'primary', eventId=id_evento))
