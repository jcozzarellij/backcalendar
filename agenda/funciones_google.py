"""Conector de Google Calendar por usuario (OAuth): autorizar, renovar, libre/ocupado y eventos
con Meet. Las claves del cliente OAuth se administran en /seguridad/configuracion/ (pestaña Google,
secreto cifrado); si ahí están vacías se usan las de `credenciales.json` (`GOOGLE_OAUTH_*`). El refresh
token de cada usuario va cifrado en `ConexionAplicacion`.

Interfaz:
- `cliente_oauth()` — {'id', 'secreto', 'redirect', 'origen'} del cliente OAuth vigente.
- `configurada()` — hay cliente OAuth cargado.
- `url_autorizacion(request)` / `completar_autorizacion(request, usuario)` — flujo OAuth web.
- `probar(conexion)` — verifica el acceso al calendario y deja el estado en la conexión.
- `freebusy(conexion, desde, hasta)` — bloques ocupados como (inicio, fin) en hora local naive.
- `crear_evento(...)`, `actualizar_evento(...)`, `eliminar_evento(...)` — eventos con Meet.
- `listar_eventos(conexion, desde, hasta)` — eventos propios del calendario (no los de Turno), con su color.
- `evento_editable(conexion, id)` — un evento propio para editar; `conexion_activa(usuario)`.
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


TIEMPO_LIMITE = 10


class ErrorGoogle(Exception):
    """Error al hablar con Google que la vista muestra al usuario tal cual (ya viene en español).
    `reintentable` es False cuando reintentar no sirve (permiso denegado, evento inexistente)."""

    def __init__(self, mensaje, reintentable=True):
        super().__init__(mensaje)
        self.reintentable = reintentable


def cliente_oauth():
    from seguridad.models import Configuracion
    confi = Configuracion.get_instancia()
    if confi.google_client_id:
        return {'id': confi.google_client_id, 'secreto': confi.google_client_secret,
                'redirect': confi.google_redirect_uri or settings.GOOGLE_OAUTH_REDIRECT_URI, 'origen': 'configuracion'}
    return {'id': settings.GOOGLE_OAUTH_CLIENT_ID, 'secreto': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'redirect': settings.GOOGLE_OAUTH_REDIRECT_URI, 'origen': 'credenciales' if settings.GOOGLE_OAUTH_CLIENT_ID else ''}


def configurada():
    cliente = cliente_oauth()
    return bool(cliente['id'] and cliente['secreto'])


def _config_cliente(cliente):
    return {'web': {
        'client_id': cliente['id'],
        'client_secret': cliente['secreto'],
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'redirect_uris': [cliente['redirect']],
    }}


def _flujo(state=None, code_verifier=None):
    from google_auth_oauthlib.flow import Flow
    cliente = cliente_oauth()
    if cliente['redirect'].startswith('http://'):
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    return Flow.from_client_config(_config_cliente(cliente), scopes=SCOPES, redirect_uri=cliente['redirect'], state=state,
                                   code_verifier=code_verifier, autogenerate_code_verifier=False)


def url_autorizacion(request):
    """El `code_verifier` (PKCE) se guarda en sesión junto al `state`: Google exige el mismo en el canje."""
    if not configurada():
        raise ErrorGoogle('Google Calendar todavía no está configurado en el sistema.')
    estado, verificador = secrets.token_urlsafe(24), secrets.token_urlsafe(64)
    request.session[CLAVE_ESTADO_SESION] = {'state': estado, 'verificador': verificador}
    url, _ = _flujo(state=estado, code_verifier=verificador).authorization_url(
        access_type='offline', prompt='consent', include_granted_scopes='true')
    return url


def completar_autorizacion(request, usuario):
    """Canjea el `code` del callback, guarda el refresh token cifrado y devuelve la conexión."""
    guardado = request.session.pop(CLAVE_ESTADO_SESION, None)
    guardado = guardado if isinstance(guardado, dict) else {}
    estado = guardado.get('state')
    if not estado or estado != request.GET.get('state'):
        raise ErrorGoogle('La autorización no coincide con la sesión. Vuelve a intentarlo.')
    if request.GET.get('error'):
        raise ErrorGoogle('Google no autorizó el acceso: ' + request.GET['error'])
    codigo = request.GET.get('code')
    if not codigo:
        raise ErrorGoogle('Google no devolvió el código de autorización.')
    flujo = _flujo(state=estado, code_verifier=guardado.get('verificador'))
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
    cliente = cliente_oauth()
    credenciales = Credentials(
        None, refresh_token=conexion.refresh_token, token_uri='https://oauth2.googleapis.com/token',
        client_id=cliente['id'], client_secret=cliente['secreto'],
        scopes=conexion.scopes.split() or SCOPES,
    )
    sesion = Request()
    try:
        credenciales.refresh(lambda *a, **k: sesion(*a, **{**k, 'timeout': TIEMPO_LIMITE}))
    except RefreshError as ex:
        detalle = str(ex)
        vencido = 'invalid_grant' in detalle or 'unauthorized_client' in detalle
        _marcar_error(conexion, 'Google rechazó el token: hay que volver a conectar la cuenta.' if vencido
                      else f'No se pudo renovar el acceso a Google: {detalle}', desconectar=vencido)
        raise ErrorGoogle(conexion.ultimo_error, reintentable=not vencido) from ex
    except Exception as ex:
        _marcar_error(conexion, 'Google no respondió al renovar el acceso; se reintentará.')
        raise ErrorGoogle(conexion.ultimo_error) from ex
    return credenciales


def servicio_calendar(conexion):
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp
    from googleapiclient.discovery import build
    http = AuthorizedHttp(credenciales_de(conexion), http=httplib2.Http(timeout=TIEMPO_LIMITE))
    return build('calendar', 'v3', http=http, cache_discovery=False)


def _ejecutar(conexion, peticion, estricto=True):
    """Ejecuta la petición; todo fallo sale como ErrorGoogle, nunca como excepción de red. Con
    `estricto=False` (cambios que pide la persona sobre un evento puntual), un 403 o 404 es un permiso o un
    evento que ya no existe: se informa sin marcar la conexión como caída y sin reintentar."""
    from googleapiclient.errors import HttpError
    try:
        return peticion.execute(num_retries=1)
    except HttpError as ex:
        codigo = getattr(ex.resp, 'status', '')
        if not estricto and codigo == 403:
            raise ErrorGoogle('Google no permite modificar este evento: solo su organizador puede hacerlo.',
                              reintentable=False) from ex
        if not estricto and codigo in (404, 410):
            raise ErrorGoogle('El evento ya no existe en Google Calendar.', reintentable=False) from ex
        mensaje = f'Google respondió {codigo} al consultar el calendario.'
        _marcar_error(conexion, mensaje, desconectar=codigo in (401, 403))
        raise ErrorGoogle(mensaje, reintentable=codigo not in (400, 401, 403)) from ex
    except Exception as ex:
        _marcar_error(conexion, 'Google no respondió a tiempo; se reintentará.')
        raise ErrorGoogle('Google no respondió a tiempo. Lo guardado en Turno no se pierde.') from ex


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


def _cuerpo_evento(titulo, inicio, fin, descripcion='', invitados=(), meet=True, request_id=None, extra=None,
                   lugar='', color_id=''):
    cuerpo = {
        'summary': titulo,
        'description': descripcion or '',
        'start': {'dateTime': _a_iso(inicio), 'timeZone': settings.TIME_ZONE},
        'end': {'dateTime': _a_iso(fin), 'timeZone': settings.TIME_ZONE},
        'attendees': [{'email': correo} for correo in invitados if correo],
        'reminders': {'useDefault': True},
    }
    if lugar:
        cuerpo['location'] = lugar
    if color_id in COLORES_EVENTO:
        cuerpo['colorId'] = color_id
    if extra:
        cuerpo['extendedProperties'] = {'private': {k: str(v) for k, v in extra.items()}}
    if meet:
        cuerpo['conferenceData'] = {'createRequest': {
            'requestId': request_id or secrets.token_urlsafe(12),
            'conferenceSolutionKey': {'type': 'hangoutsMeet'},
        }}
    return cuerpo


def crear_evento(conexion, titulo, inicio, fin, descripcion='', invitados=(), meet=True, request_id=None,
                 extra=None, avisar=True, lugar='', color_id='', id_evento=None):
    """Crea el evento en el calendario de la conexión. Devuelve (id_evento, enlace_meet, enlace_evento).
    Con `id_evento` (base32hex, fijado por Turno) un reintento no duplica: si Google ya lo tiene (409),
    devuelve ese evento."""
    from googleapiclient.errors import HttpError
    servicio = servicio_calendar(conexion)
    cuerpo = _cuerpo_evento(titulo, inicio, fin, descripcion, invitados, meet, request_id, extra, lugar, color_id)
    if id_evento:
        cuerpo['id'] = id_evento
    calendario = conexion.calendario_id or 'primary'
    try:
        evento = servicio.events().insert(calendarId=calendario, body=cuerpo, conferenceDataVersion=1,
                                          sendUpdates='all' if avisar else 'none').execute(num_retries=1)
    except HttpError as ex:
        if not (id_evento and getattr(ex.resp, 'status', None) == 409):
            return _ejecutar(conexion, _Fallida(ex))
        evento = _ejecutar(conexion, servicio.events().get(calendarId=calendario, eventId=id_evento))
    except Exception as ex:
        return _ejecutar(conexion, _Fallida(ex))
    return evento.get('id'), evento.get('hangoutLink', ''), evento.get('htmlLink', '')


class _Fallida:
    """Petición ya fallada, para reusar en `_ejecutar` la traducción de errores a ErrorGoogle."""

    def __init__(self, error):
        self.error = error

    def execute(self, **kwargs):
        raise self.error


def actualizar_evento(conexion, id_evento, inicio=None, fin=None, titulo=None, descripcion=None, avisar=True,
                      lugar=None, color_id=None, invitados=None, estricto=True):
    """Cambia solo lo que llega distinto de None. `color_id=''` vuelve al color del calendario."""
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
    if lugar is not None:
        cambios['location'] = lugar
    if color_id is not None:
        cambios['colorId'] = color_id if color_id in COLORES_EVENTO else None
    if invitados is not None:
        cambios['attendees'] = [{'email': correo} for correo in invitados if correo]
    return _ejecutar(conexion, servicio.events().patch(
        calendarId=conexion.calendario_id or 'primary', eventId=id_evento, body=cambios,
        sendUpdates='all' if avisar else 'none',
    ), estricto=estricto)


def eliminar_evento(conexion, id_evento, avisar=True):
    from googleapiclient.errors import HttpError
    servicio = servicio_calendar(conexion)
    try:
        servicio.events().delete(calendarId=conexion.calendario_id or 'primary', eventId=id_evento,
                                 sendUpdates='all' if avisar else 'none').execute(num_retries=1)
    except HttpError as ex:
        codigo = getattr(ex.resp, 'status', None)
        if codigo == 403:
            raise ErrorGoogle('Google no permite eliminar este evento: solo su organizador puede hacerlo.',
                              reintentable=False) from ex
        if codigo not in (404, 410):
            raise ErrorGoogle('Google no permitió cancelar el evento.') from ex
    except Exception as ex:
        raise ErrorGoogle('Google no respondió a tiempo al eliminar el evento.') from ex


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


COLORES_EVENTO = {
    '1': ('Lavanda', '#7986cb'), '2': ('Salvia', '#33b679'), '3': ('Uva', '#8e24aa'), '4': ('Flamenco', '#e67c73'),
    '5': ('Plátano', '#f6bf26'), '6': ('Mandarina', '#f4511e'), '7': ('Pavo real', '#039be5'), '8': ('Grafito', '#616161'),
    '9': ('Arándano', '#3f51b5'), '10': ('Albahaca', '#0b8043'), '11': ('Tomate', '#d50000'),
}
COLOR_CALENDARIO = '#039be5'
CAMPOS_EVENTO = ('nextPageToken,items(id,status,summary,description,location,htmlLink,hangoutLink,start,end,colorId,'
                 'recurringEventId,guestsCanModify,organizer(self),extendedProperties/private,'
                 'attendees(email,self,responseStatus))')


def texto_sobre(fondo):
    """Tinta legible sobre el color: blanco o casi negro, la de mayor contraste (WCAG)."""
    def canal(c):
        c = int(c, 16) / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(fondo[i:i + 2]) for i in (1, 3, 5))
    luz = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return '#ffffff' if (1.05 / (luz + 0.05)) >= ((luz + 0.05) / 0.05) else '#1f1f1f'


def conexion_activa(usuario):
    return ConexionAplicacion.objects.filter(status=True, usuario=usuario, proveedor='google', conectada=True).first()


def evento_editable(conexion, id_evento):
    """Evento propio (no de Turno) listo para el formulario de edición; ErrorGoogle si no se puede editar."""
    servicio = servicio_calendar(conexion)
    crudo = _ejecutar(conexion, servicio.events().get(calendarId=conexion.calendario_id or 'primary', eventId=id_evento),
                      estricto=False)
    evento = _evento_local(crudo)
    if evento is None:
        raise ErrorGoogle('Este evento lo maneja Turno o ya no está activo: edítalo desde su cita.')
    if not evento['editable']:
        raise ErrorGoogle('Google no permite modificar este evento: solo su organizador puede hacerlo.')
    return evento


def listar_eventos(conexion, desde, hasta, maximo=250):
    """Eventos del calendario entre `desde` y `hasta`, con los recurrentes ya expandidos. Omite los
    cancelados, los que el usuario rechazó y los que creó Turno (llevan `cita_id`). Cada evento es un dict
    en hora local naive: id, titulo, inicio, fin, todo_el_dia, lugar, descripcion, enlace, meet, color_id,
    color, color_texto, editable (el usuario es organizador), recurrente e invitados."""
    servicio = servicio_calendar(conexion)
    eventos, pagina = [], None
    while len(eventos) < maximo:
        respuesta = _ejecutar(conexion, servicio.events().list(
            calendarId=conexion.calendario_id or 'primary', timeMin=_a_iso(desde), timeMax=_a_iso(hasta),
            timeZone=settings.TIME_ZONE, singleEvents=True, orderBy='startTime', maxResults=250,
            pageToken=pagina, fields=CAMPOS_EVENTO,
        ))
        eventos.extend(e for e in map(_evento_local, respuesta.get('items', [])) if e)
        pagina = respuesta.get('nextPageToken')
        if not pagina:
            break
    return eventos[:maximo]


def _evento_local(evento):
    privadas = (evento.get('extendedProperties') or {}).get('private', {})
    if evento.get('status') == 'cancelled' or privadas.get('cita_id') or privadas.get('reunion_id'):
        return None
    if any(a.get('self') and a.get('responseStatus') == 'declined' for a in evento.get('attendees', [])):
        return None
    inicio, fin = evento.get('start') or {}, evento.get('end') or {}
    if inicio.get('dateTime') and fin.get('dateTime'):
        todo_el_dia, ini, fn = False, _a_local(inicio['dateTime']), _a_local(fin['dateTime'])
    elif inicio.get('date'):
        todo_el_dia = True
        ini = datetime.fromisoformat(inicio['date'])
        fn = datetime.fromisoformat(fin.get('date') or inicio['date'])
    else:
        return None
    color_id = evento.get('colorId', '')
    color = COLORES_EVENTO.get(color_id, ('', COLOR_CALENDARIO))[1]
    return {
        'id': evento.get('id', ''),
        'titulo': evento.get('summary') or '(Sin título)',
        'inicio': ini,
        'fin': fn,
        'todo_el_dia': todo_el_dia,
        'lugar': evento.get('location', ''),
        'descripcion': evento.get('description', ''),
        'enlace': evento.get('htmlLink', ''),
        'meet': evento.get('hangoutLink', ''),
        'color_id': color_id if color_id in COLORES_EVENTO else '',
        'color': color,
        'color_texto': texto_sobre(color),
        'editable': bool((evento.get('organizer') or {}).get('self') or evento.get('guestsCanModify')),
        'recurrente': bool(evento.get('recurringEventId')),
        'invitados': [a['email'] for a in evento.get('attendees', []) if a.get('email') and not a.get('self')],
    }


def obtener_evento(conexion, id_evento):
    """Evento tal como está hoy en Google: dict con `status` ('confirmed'/'cancelled'), `start`, `end`,
    `attendees` (con `responseStatus`) y `hangoutLink`."""
    servicio = servicio_calendar(conexion)
    return _ejecutar(conexion, servicio.events().get(calendarId=conexion.calendario_id or 'primary', eventId=id_evento))
