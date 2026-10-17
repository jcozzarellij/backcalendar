"""Motor de disponibilidad: turnos declarados − bloqueos propios − ocupado en Google − márgenes.

Interfaz:
- `espacios_libres(usuario, fecha, duracion=None, margen=0)` — inicios de espacio libres del día.
- `espacios_comunes(usuarios, fecha, duracion=None, margen=0)` — inicios en que coinciden todos.
- `espacios_libres_rango` / `espacios_comunes_rango(..., desde, hasta, ...)` — lo mismo para varios días: {fecha: inicios},
  con las consultas y la petición a Google hechas una vez para todo el rango.
- `ocupacion_rango(usuario, desde, hasta)` / `ocupacion_del_dia(usuario, fecha)` — bloques (inicio, fin, tipo)
  para pintar la agenda del equipo: tipo ∈ {'turno', 'cita', 'reunion', 'google', 'manual'}.
- `espacios_alguno_rango(usuarios, ...)` — inicios en que al menos uno está libre (modo «una persona»).
- `estado_en(usuario, inicio, fin)` — 'libre', 'ocupado' o 'fuera' de turno.
- `ocupados_google(usuario, desde, hasta)` — bloques ocupados en Google, cacheados.
- `eventos_google(usuario, desde, hasta, excluir=(), refrescar=False)` — eventos propios de Google para
  mostrar en la agenda del usuario, cacheados; (eventos o None sin conexión, error).

Todo en hora local naive (`USE_TZ=False`). Google se consulta por usuario con su propia conexión;
si no la tiene o falla, se ignora y la disponibilidad se calcula solo con lo propio.
"""
import logging
from datetime import datetime, timedelta

from django.core.cache import cache

from seguridad.models import ParametroSistema
from . import funciones_google
from .funciones_turnos import datos_turnos, duracion_turno, franjas_del_dia, franjas_en
from .models import BloqueOcupado, Reunion

logger = logging.getLogger(__name__)


def _parametro_int(clave, default):
    valor = ParametroSistema.valor_de(clave, default)
    try:
        return int(valor)
    except (TypeError, ValueError):
        return default


def ocupados_google(usuario, desde, hasta):
    """Bloques (inicio, fin) ocupados en el Google Calendar del usuario; lista vacía si no hay
    conexión o Google falla. Se cachea por usuario y día según `agenda_cache_disponibilidad_seg`."""
    conexion = funciones_google.conexion_activa(usuario)
    if conexion is None:
        return []
    clave = f'agenda:freebusy:{usuario.pk}:{_version_google(usuario)}:{desde:%Y%m%d%H%M}:{hasta:%Y%m%d%H%M}'
    cacheado = cache.get(clave)
    if cacheado is not None:
        return cacheado
    try:
        bloques = funciones_google.freebusy(conexion, desde, hasta)
    except funciones_google.ErrorGoogle as ex:
        logger.warning('freebusy de %s falló: %s', usuario, ex)
        return []
    cache.set(clave, bloques, _parametro_int('agenda_cache_disponibilidad_seg', 180))
    return bloques


def eventos_google(usuario, desde, hasta, excluir=(), refrescar=False):
    """Eventos del Google Calendar del usuario que no son citas de Turno, solo lectura. `excluir` son los
    `google_event_id` de las citas ya pintadas (las copias de invitado no traen `cita_id`). Devuelve
    (eventos, error): sin conexión, (None, ''); si Google falla, ([], mensaje) y la agenda sigue sin ellos."""
    conexion = funciones_google.conexion_activa(usuario)
    if conexion is None:
        return None, ''
    clave = f'agenda:eventos_google:{usuario.pk}:{_version_google(usuario)}:{desde:%Y%m%d%H%M}:{hasta:%Y%m%d%H%M}'
    eventos = None if refrescar else cache.get(clave)
    if eventos is None:
        try:
            eventos = funciones_google.listar_eventos(conexion, desde, hasta)
        except Exception as ex:
            logger.warning('eventos de Google de %s fallaron: %s', usuario, ex)
            mensaje = str(ex) if isinstance(ex, funciones_google.ErrorGoogle) else 'Google no respondió.'
            return [], mensaje
        cache.set(clave, eventos, _parametro_int('agenda_cache_disponibilidad_seg', 180))
    excluidos = {i for i in excluir if i}
    return [e for e in eventos if e['id'] not in excluidos], ''


def _version_google(usuario):
    clave = f'agenda:google_version:{usuario.pk}'
    version = cache.get(clave)
    if version is None:
        version = 1
        cache.set(clave, version, None)
    return version


def invalidar_google(usuario):
    """Descarta el caché de Google del usuario (ocupado y eventos) tras crear, mover o borrar algo: sube su
    versión, así las claves viejas dejan de leerse sin tener que buscarlas (LocMemCache no tiene delete_pattern)."""
    clave = f'agenda:google_version:{usuario.pk}'
    try:
        cache.incr(clave)
    except ValueError:
        cache.set(clave, 2, None)


def bloques_propios(usuario, desde, hasta):
    """Lo ocupado según Turno: bloques de citas y manuales, más las reuniones propias (aunque todavía no
    estén en Google, así la agenda no ofrece esa hora si la plataforma está caída)."""
    bloques = [(b.inicio, b.fin) for b in BloqueOcupado.objects.filter(
        status=True, usuario=usuario, inicio__lt=hasta, fin__gt=desde)]
    bloques += list(Reunion.objects.filter(status=True, organizador=usuario, eliminada=False, inicio__lt=hasta,
                                           fin__gt=desde).values_list('inicio', 'fin'))
    return sorted(bloques)


def _ocupado_en(inicio, fin, bloques, margen):
    holgura = timedelta(minutes=margen)
    return any(b_ini < fin + holgura and b_fin > inicio - holgura for b_ini, b_fin in bloques)


def espacios_libres(usuario, fecha, duracion=None, margen=0, paso=None, desde_hora=None):
    """Inicios (datetime) de los espacios libres de `usuario` en `fecha`, ordenados."""
    return espacios_libres_rango(usuario, fecha, fecha, duracion, margen, paso, desde_hora)[fecha]


def espacios_libres_rango(usuario, desde, hasta, duracion=None, margen=0, paso=None, desde_hora=None):
    """{fecha: inicios libres} de cada día entre `desde` y `hasta`, con una sola carga de turnos y bloques."""
    duracion = duracion or duracion_turno()
    paso = paso or duracion
    datos = datos_turnos(usuario, desde, hasta)
    fechas = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
    franjas_por_dia = {fecha: franjas_en(datos, fecha) for fecha in fechas}
    bloques = []
    if any(franjas_por_dia.values()):
        rango_ini = datetime.combine(desde, datetime.min.time())
        rango_fin = datetime.combine(hasta, datetime.min.time()) + timedelta(days=1)
        bloques = bloques_propios(usuario, rango_ini, rango_fin) + ocupados_google(usuario, rango_ini, rango_fin)
    largo, salto = timedelta(minutes=duracion), timedelta(minutes=paso)
    salida = {}
    for fecha, franjas in franjas_por_dia.items():
        libres = []
        for hora_ini, hora_fin in franjas:
            actual = datetime.combine(fecha, hora_ini)
            tope = datetime.combine(fecha, hora_fin)
            while actual + largo <= tope:
                if (desde_hora is None or actual >= desde_hora) and not _ocupado_en(actual, actual + largo, bloques, margen):
                    libres.append(actual)
                actual += salto
        salida[fecha] = libres
    return salida


def espacios_comunes(usuarios, fecha, duracion=None, margen=0, paso=None, desde_hora=None):
    """Inicios en los que TODOS los usuarios están libres."""
    return espacios_comunes_rango(usuarios, fecha, fecha, duracion, margen, paso, desde_hora).get(fecha, [])


def espacios_comunes_rango(usuarios, desde, hasta, duracion=None, margen=0, paso=None, desde_hora=None):
    """{fecha: inicios en que TODOS los usuarios están libres} para cada día del rango."""
    usuarios = list(usuarios)
    if not usuarios:
        return {}
    comunes = None
    for usuario in usuarios:
        propios = {f: set(h) for f, h in espacios_libres_rango(usuario, desde, hasta, duracion, margen, paso, desde_hora).items()}
        comunes = propios if comunes is None else {f: comunes[f] & propios[f] for f in comunes}
        if not any(comunes.values()):
            break
    return {f: sorted(h) for f, h in comunes.items()}


def espacios_alguno_rango(usuarios, desde, hasta, duracion=None, margen=0, paso=None, desde_hora=None):
    """{fecha: inicios en que AL MENOS UNO de los usuarios está libre} para cada día del rango."""
    union = {}
    for usuario in usuarios:
        for f, horas in espacios_libres_rango(usuario, desde, hasta, duracion, margen, paso, desde_hora).items():
            union.setdefault(f, set()).update(horas)
    return {f: sorted(h) for f, h in union.items()}


def estado_en(usuario, inicio, fin, margen=0):
    """'libre', 'ocupado' o 'fuera' (fuera de su turno declarado) para el intervalo [inicio, fin)."""
    if _ocupado_en(inicio, fin, bloques_propios(usuario, inicio, fin) + ocupados_google(usuario, inicio, fin), margen):
        return 'ocupado'
    dentro = any(datetime.combine(inicio.date(), a) <= inicio and datetime.combine(inicio.date(), b) >= fin
                 for a, b in franjas_del_dia(usuario, inicio.date()))
    return 'libre' if dentro else 'fuera'


def ocupacion_rango(usuario, desde, hasta):
    """{fecha: bloques} para la agenda del equipo: turnos declarados y, dentro de ellos, lo ocupado (citas,
    bloqueos manuales, reuniones propias aunque estén pendientes de sincronizar, y lo ocupado en Google).
    Una consulta por fuente para todo el rango."""
    fechas = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
    rango_ini = datetime.combine(desde, datetime.min.time())
    rango_fin = datetime.combine(hasta, datetime.min.time()) + timedelta(days=1)
    datos = datos_turnos(usuario, desde, hasta)
    por_dia = {f: [{'inicio': datetime.combine(f, a), 'fin': datetime.combine(f, b), 'tipo': 'turno'} for a, b in franjas_en(datos, f)]
               for f in fechas}
    ocupados = [{'inicio': b.inicio, 'fin': b.fin, 'tipo': b.fuente, 'cita': b.cita} for b in BloqueOcupado.objects.filter(
        status=True, usuario=usuario, inicio__lt=rango_fin, fin__gt=rango_ini).select_related('cita')]
    ocupados += [{'inicio': r.inicio, 'fin': r.fin, 'tipo': 'reunion', 'reunion': r} for r in Reunion.objects.filter(
        status=True, organizador=usuario, eliminada=False, inicio__lt=rango_fin, fin__gt=rango_ini)]
    propios = [(b['inicio'], b['fin']) for b in ocupados]
    ocupados += [{'inicio': i, 'fin': f, 'tipo': 'google'} for g in ocupados_google(usuario, rango_ini, rango_fin)
                 for i, f in _restar_intervalos(g, propios)]
    for b in ocupados:
        for f in fechas:
            dia_ini = datetime.combine(f, datetime.min.time())
            if b['inicio'] < dia_ini + timedelta(days=1) and b['fin'] > dia_ini:
                por_dia[f].append({**b, 'inicio': max(b['inicio'], dia_ini), 'fin': min(b['fin'], dia_ini + timedelta(days=1))})
    return {f: sorted(bl, key=lambda b: (b['inicio'], b['tipo'] != 'turno')) for f, bl in por_dia.items()}


def _restar_intervalos(intervalo, otros):
    """Partes de `intervalo` que no cubre ninguno de `otros` (lo ocupado en Google que no es una cita o
    reunión de Turno ya pintada); descarta restos de menos de un minuto."""
    partes = [intervalo]
    for o_ini, o_fin in otros:
        nuevas = []
        for p_ini, p_fin in partes:
            if o_fin <= p_ini or o_ini >= p_fin:
                nuevas.append((p_ini, p_fin))
                continue
            if o_ini > p_ini:
                nuevas.append((p_ini, o_ini))
            if o_fin < p_fin:
                nuevas.append((o_fin, p_fin))
        partes = nuevas
    return [(a, b) for a, b in partes if b - a >= timedelta(minutes=1)]


def ocupacion_del_dia(usuario, fecha):
    """Bloques de un día para la vista de equipo (ver `ocupacion_rango`)."""
    return ocupacion_rango(usuario, fecha, fecha)[fecha]


def primer_espacio(usuarios, desde, dias=14, duracion=None, margen=0, antelacion_horas=None):
    """Primer inicio común desde `desde` (datetime) dentro de `dias`, respetando la antelación."""
    antelacion = antelacion_horas if antelacion_horas is not None else _parametro_int('agenda_antelacion_horas', 24)
    minimo = desde + timedelta(hours=antelacion)
    por_dia = espacios_comunes_rango(usuarios, minimo.date(), minimo.date() + timedelta(days=dias), duracion, margen,
                                     desde_hora=minimo)
    return next((espacios[0] for _, espacios in sorted(por_dia.items()) if espacios), None)
