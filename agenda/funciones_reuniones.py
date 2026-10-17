"""Reuniones propias (fuera de las citas de Turno) en la plataforma que elija la persona desde su agenda.

Turno es la fuente de verdad: una reunión creada aquí se guarda en `Reunion` y luego se refleja en la
plataforma. Si la plataforma no responde o la conexión está caída, la reunión queda `pendiente` y la agenda
sigue funcionando; `sincronizar` la reintenta al guardar, desde el botón «Reintentar» y en el cron
`reconciliar_google`. Los eventos creados directamente en Google se editan en vivo (necesitan que Google
responda). Hoy solo Google; Teams y Zoom se suman con su rama en `sincronizar` y su clave en IMPLEMENTADAS.

Interfaz:
- `plataformas_de(usuario)` — cada plataforma con `disponible`, `motivo` y `aviso`, para el selector.
- `agenda_externa(usuario, desde, hasta, excluir=(), refrescar=False)` — (eventos, conectado, error) para pintar.
- `crear` / `editar` / `mover` / `eliminar` / `para_editar` — por referencia: `turno-<pk>` o el id de Google.
- `sincronizar(pk)` — refleja una reunión pendiente; nunca lanza. `sincronizar_pendientes()` para el cron.

Los errores para la persona salen como ValueError.
"""
import logging
import secrets
from datetime import datetime, timedelta

from django.db import transaction

from . import funciones_google
from .funciones_disponibilidad import eventos_google, invalidar_google
from .models import ConexionAplicacion, Reunion

logger = logging.getLogger(__name__)

PLATAFORMAS = (
    {'clave': 'google', 'nombre': 'Google Calendar', 'icono': 'fab fa-google', 'proveedor': 'google'},
    {'clave': 'teams', 'nombre': 'Microsoft Teams', 'icono': 'fab fa-microsoft', 'proveedor': 'microsoft'},
    {'clave': 'zoom', 'nombre': 'Zoom', 'icono': 'fas fa-video', 'proveedor': 'zoom'},
)
IMPLEMENTADAS = {'google'}
PREFIJO = 'turno-'
CAMPOS_SYNC = ['id_externo', 'enlace', 'enlace_videollamada', 'pendiente', 'error_sincronizacion', 'intentos',
               'ultima_sincronizacion']


def plataformas_de(usuario):
    conexiones = dict(ConexionAplicacion.objects.filter(status=True, usuario=usuario).values_list('proveedor', 'conectada'))
    resultado = []
    for p in PLATAFORMAS:
        motivo, aviso = '', ''
        if p['clave'] not in IMPLEMENTADAS:
            motivo = 'Próximamente'
        elif p['proveedor'] not in conexiones:
            motivo = 'Conecta tu cuenta en Conexiones'
        elif not conexiones[p['proveedor']]:
            aviso = 'La conexión está caída: la reunión se guarda en Turno y se sincroniza al reconectar.'
        resultado.append({**p, 'disponible': not motivo, 'motivo': motivo, 'aviso': aviso})
    return resultado


def agenda_externa(usuario, desde, hasta, excluir=(), refrescar=False):
    """Reuniones de Turno (siempre, desde la BD) más los eventos propios de Google (si responde)."""
    reuniones = list(Reunion.objects.filter(status=True, organizador=usuario, eliminada=False, inicio__lt=hasta, fin__gt=desde))
    externos, error = eventos_google(usuario, desde, hasta, excluir=list(excluir) + [r.id_externo for r in reuniones],
                                     refrescar=refrescar)
    eventos = [_presentar(r) for r in reuniones]
    eventos += [{**e, 'ref': e['id'], 'plataforma': 'google', 'origen': 'google', 'pendiente': '', 'error': ''}
                for e in externos or []]
    for e in eventos:
        e['minutos'] = max(5, int((e['fin'] - e['inicio']).total_seconds() // 60))
    eventos.sort(key=lambda e: (e['inicio'], e['fin']))
    return eventos, externos is not None or bool(reuniones), error


def crear(usuario, plataforma, datos, request=None):
    _plataforma(usuario, plataforma)
    inicio = datos['inicio']
    reunion = Reunion(organizador=usuario, plataforma=plataforma, titulo=datos['titulo'], inicio=inicio,
                      fin=inicio + timedelta(minutes=datos['duracion']), lugar=datos.get('lugar', ''),
                      descripcion=datos.get('descripcion', ''), invitados=', '.join(datos.get('invitados', [])),
                      color_id=datos.get('color', ''), con_videollamada=bool(datos.get('meet')), pendiente='crear')
    reunion.save(request)
    reunion.id_externo = _nuevo_id(reunion.pk)
    reunion.save(update_fields=['id_externo'])
    _sincronizar_al_confirmar(reunion.pk)
    return reunion


def editar(usuario, plataforma, ref, datos, todo_el_dia=False, request=None):
    reunion = _reunion(usuario, ref)
    if reunion is None:
        _plataforma(usuario, plataforma)
        horario = {} if todo_el_dia else {'inicio': datos['inicio'], 'fin': datos['inicio'] + timedelta(minutes=datos['duracion'])}
        _en_vivo(usuario, lambda c: funciones_google.actualizar_evento(
            c, ref, titulo=datos['titulo'], descripcion=datos.get('descripcion', ''), lugar=datos.get('lugar', ''),
            color_id=datos.get('color', ''), invitados=datos.get('invitados', []), estricto=False, **horario))
        return
    reunion.titulo = datos['titulo']
    reunion.inicio = datos['inicio']
    reunion.fin = datos['inicio'] + timedelta(minutes=datos['duracion'])
    reunion.lugar = datos.get('lugar', '')
    reunion.descripcion = datos.get('descripcion', '')
    reunion.invitados = ', '.join(datos.get('invitados', []))
    reunion.color_id = datos.get('color', '')
    _guardar_cambio(reunion, request)


def mover(usuario, plataforma, ref, inicio, fin, request=None):
    if fin <= inicio:
        raise ValueError('La hora final debe ser posterior a la inicial.')
    reunion = _reunion(usuario, ref)
    if reunion is None:
        _plataforma(usuario, plataforma)
        _en_vivo(usuario, lambda c: funciones_google.actualizar_evento(c, ref, inicio=inicio, fin=fin, estricto=False))
        return
    reunion.inicio, reunion.fin = inicio, fin
    _guardar_cambio(reunion, request)


def eliminar(usuario, plataforma, ref, request=None):
    reunion = _reunion(usuario, ref)
    if reunion is None:
        _plataforma(usuario, plataforma)
        _en_vivo(usuario, lambda c: funciones_google.eliminar_evento(c, ref))
        return
    reunion.eliminada = True
    reunion.pendiente = 'eliminar'
    reunion.save(request)
    _sincronizar_al_confirmar(reunion.pk)


def para_editar(usuario, plataforma, ref):
    reunion = _reunion(usuario, ref, bloquear=False)
    if reunion is not None:
        return _presentar(reunion)
    conexion = funciones_google.conexion_activa(usuario)
    if conexion is None:
        raise ValueError('Tu Google Calendar no está conectado: este evento solo se puede editar con la conexión activa.')
    try:
        return {**funciones_google.evento_editable(conexion, ref), 'ref': ref, 'origen': 'google', 'pendiente': '', 'error': ''}
    except funciones_google.ErrorGoogle as ex:
        raise ValueError(str(ex)) from ex


def reintentar(usuario, ref):
    reunion = _reunion(usuario, ref, bloquear=False)
    if reunion is None:
        raise ValueError('Solo las reuniones creadas en Turno se pueden reintentar.')
    if not sincronizar(reunion.pk):
        reunion.refresh_from_db(fields=['error_sincronizacion'])
        raise ValueError(f'Sigue pendiente: {reunion.error_sincronizacion or "la plataforma no respondió"}')


def sincronizar(pk):
    """Refleja en la plataforma el cambio pendiente de la reunión. Nunca lanza: deja el estado en la fila.
    Devuelve True si quedó al día."""
    reunion = Reunion.objects.select_related('organizador').filter(pk=pk, status=True).first()
    if reunion is None or not reunion.pendiente:
        return True
    try:
        if reunion.plataforma not in IMPLEMENTADAS:
            raise funciones_google.ErrorGoogle(f'{reunion.get_plataforma_display()} todavía no está disponible.')
        conexion = funciones_google.conexion_activa(reunion.organizador)
        if conexion is None:
            raise funciones_google.ErrorGoogle('La cuenta de Google no está conectada; se sincroniza al reconectar.')
        if reunion.pendiente == 'eliminar':
            funciones_google.eliminar_evento(conexion, reunion.id_externo)
        elif reunion.pendiente == 'crear':
            _, meet, enlace = funciones_google.crear_evento(
                conexion, reunion.titulo, reunion.inicio, reunion.fin, descripcion=reunion.descripcion,
                invitados=reunion.lista_invitados, meet=reunion.con_videollamada, request_id=f'reunion-{reunion.pk}',
                extra={'reunion_id': reunion.pk}, lugar=reunion.lugar, color_id=reunion.color_id, id_evento=reunion.id_externo)
            reunion.enlace_videollamada, reunion.enlace = meet or '', enlace or ''
        else:
            evento = funciones_google.actualizar_evento(
                conexion, reunion.id_externo, inicio=reunion.inicio, fin=reunion.fin, titulo=reunion.titulo,
                descripcion=reunion.descripcion, lugar=reunion.lugar, color_id=reunion.color_id,
                invitados=reunion.lista_invitados, estricto=False)
            reunion.enlace = evento.get('htmlLink') or reunion.enlace
            reunion.enlace_videollamada = evento.get('hangoutLink') or reunion.enlace_videollamada
        reunion.pendiente = ''
        reunion.error_sincronizacion = ''
        reunion.ultima_sincronizacion = datetime.now()
    except funciones_google.ErrorGoogle as ex:
        reunion.error_sincronizacion = str(ex)[:300]
        if not ex.reintentable:
            if reunion.pendiente == 'actualizar' and 'ya no existe' in str(ex):
                reunion.pendiente = 'crear'
                reunion.id_externo = _nuevo_id(reunion.pk)
            else:
                reunion.pendiente = ''
    except Exception as ex:
        logger.warning('Sincronizar la reunión %s falló: %s', reunion.pk, ex)
        reunion.error_sincronizacion = 'No se pudo sincronizar; se reintentará.'
    reunion.intentos += 1
    reunion.save(update_fields=CAMPOS_SYNC)
    invalidar_google(reunion.organizador)
    return not reunion.pendiente


def sincronizar_pendientes(limite=200):
    """Para el cron: reintenta las reuniones pendientes. Devuelve (revisadas, al_dia)."""
    pendientes = list(Reunion.objects.filter(status=True).exclude(pendiente='').order_by('inicio')
                      .values_list('pk', flat=True)[:limite])
    return len(pendientes), sum(1 for pk in pendientes if sincronizar(pk))


def _presentar(reunion):
    color = funciones_google.COLORES_EVENTO.get(reunion.color_id, ('', funciones_google.COLOR_CALENDARIO))[1]
    return {
        'id': reunion.id_externo, 'ref': f'{PREFIJO}{reunion.pk}', 'plataforma': reunion.plataforma, 'origen': 'turno',
        'titulo': reunion.titulo, 'inicio': reunion.inicio, 'fin': reunion.fin, 'todo_el_dia': False,
        'lugar': reunion.lugar, 'descripcion': reunion.descripcion, 'enlace': reunion.enlace,
        'meet': reunion.enlace_videollamada, 'color_id': reunion.color_id, 'color': color,
        'color_texto': funciones_google.texto_sobre(color), 'editable': True, 'recurrente': False,
        'invitados': reunion.lista_invitados, 'pendiente': reunion.get_pendiente_display() if reunion.pendiente else '',
        'error': reunion.error_sincronizacion,
    }


def _reunion(usuario, ref, bloquear=True):
    if not str(ref).startswith(PREFIJO):
        return None
    pk = str(ref)[len(PREFIJO):]
    consulta = Reunion.objects.select_for_update() if bloquear else Reunion.objects
    reunion = consulta.filter(pk=int(pk), status=True, organizador=usuario, eliminada=False).first() if pk.isdigit() else None
    if reunion is None:
        raise ValueError('La reunión ya no existe.')
    return reunion


def _guardar_cambio(reunion, request):
    if reunion.pendiente != 'crear':
        reunion.pendiente = 'actualizar'
    reunion.save(request)
    _sincronizar_al_confirmar(reunion.pk)


def _sincronizar_al_confirmar(pk):
    transaction.on_commit(lambda: sincronizar(pk))


def _nuevo_id(pk):
    return f'turno{pk}{secrets.token_hex(5)}'


def _plataforma(usuario, plataforma):
    elegida = next((p for p in plataformas_de(usuario) if p['clave'] == plataforma), None)
    if elegida is None:
        raise ValueError('Plataforma de reunión no válida.')
    if not elegida['disponible']:
        raise ValueError(f"{elegida['nombre']}: {elegida['motivo'].lower()}.")
    return elegida


def _en_vivo(usuario, funcion):
    """Cambio directo sobre un evento que solo existe en Google: necesita la conexión activa."""
    conexion = funciones_google.conexion_activa(usuario)
    if conexion is None:
        raise ValueError('Tu Google Calendar no está conectado: este evento se modifica cuando vuelva la conexión.')
    try:
        funcion(conexion)
    except funciones_google.ErrorGoogle as ex:
        raise ValueError(str(ex)) from ex
    invalidar_google(usuario)
