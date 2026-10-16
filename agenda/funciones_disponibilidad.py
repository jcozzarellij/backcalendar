"""Motor de disponibilidad: turnos declarados − bloqueos propios − ocupado en Google − márgenes.

Interfaz:
- `espacios_libres(usuario, fecha, duracion=None, margen=0)` — inicios de espacio libres del día.
- `espacios_comunes(usuarios, fecha, duracion=None, margen=0)` — inicios en que coinciden todos.
- `ocupacion_del_dia(usuario, fecha)` — bloques (inicio, fin, tipo) para pintar la agenda del equipo:
  tipo ∈ {'turno', 'cita', 'google', 'manual'}.
- `ocupados_google(usuario, desde, hasta)` — bloques ocupados en Google, cacheados.

Todo en hora local naive (`USE_TZ=False`). Google se consulta por usuario con su propia conexión;
si no la tiene o falla, se ignora y la disponibilidad se calcula solo con lo propio.
"""
import logging
from datetime import datetime, timedelta

from django.core.cache import cache

from seguridad.models import ParametroSistema
from . import funciones_google
from .funciones_turnos import duracion_turno, franjas_del_dia
from .models import BloqueOcupado, ConexionAplicacion

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
    conexion = ConexionAplicacion.objects.filter(status=True, usuario=usuario, proveedor='google', conectada=True).first()
    if conexion is None:
        return []
    clave = f'agenda:freebusy:{usuario.pk}:{desde:%Y%m%d%H%M}:{hasta:%Y%m%d%H%M}'
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


def invalidar_google(usuario):
    """Borra el caché de Google del usuario (tras crear o mover una cita)."""
    cache.delete_pattern(f'agenda:freebusy:{usuario.pk}:*') if hasattr(cache, 'delete_pattern') else None


def bloques_propios(usuario, desde, hasta):
    return [(b.inicio, b.fin) for b in BloqueOcupado.objects.filter(
        status=True, usuario=usuario, inicio__lt=hasta, fin__gt=desde).order_by('inicio')]


def _ocupado_en(inicio, fin, bloques, margen):
    holgura = timedelta(minutes=margen)
    return any(b_ini < fin + holgura and b_fin > inicio - holgura for b_ini, b_fin in bloques)


def espacios_libres(usuario, fecha, duracion=None, margen=0, paso=None, desde_hora=None):
    """Inicios (datetime) de los espacios libres de `usuario` en `fecha`, ordenados."""
    duracion = duracion or duracion_turno()
    paso = paso or duracion
    franjas = franjas_del_dia(usuario, fecha)
    if not franjas:
        return []
    dia_ini = datetime.combine(fecha, datetime.min.time())
    dia_fin = dia_ini + timedelta(days=1)
    bloques = bloques_propios(usuario, dia_ini, dia_fin) + ocupados_google(usuario, dia_ini, dia_fin)
    largo, salto = timedelta(minutes=duracion), timedelta(minutes=paso)
    libres = []
    for hora_ini, hora_fin in franjas:
        actual = datetime.combine(fecha, hora_ini)
        tope = datetime.combine(fecha, hora_fin)
        while actual + largo <= tope:
            if (desde_hora is None or actual >= desde_hora) and not _ocupado_en(actual, actual + largo, bloques, margen):
                libres.append(actual)
            actual += salto
    return libres


def espacios_comunes(usuarios, fecha, duracion=None, margen=0, paso=None, desde_hora=None):
    """Inicios en los que TODOS los usuarios están libres."""
    usuarios = list(usuarios)
    if not usuarios:
        return []
    comunes = None
    for usuario in usuarios:
        propios = set(espacios_libres(usuario, fecha, duracion, margen, paso, desde_hora))
        comunes = propios if comunes is None else comunes & propios
        if not comunes:
            return []
    return sorted(comunes)


def ocupacion_del_dia(usuario, fecha):
    """Bloques para la vista de equipo: turnos declarados y, dentro de ellos, lo ocupado."""
    dia_ini = datetime.combine(fecha, datetime.min.time())
    dia_fin = dia_ini + timedelta(days=1)
    bloques = [{'inicio': datetime.combine(fecha, a), 'fin': datetime.combine(fecha, b), 'tipo': 'turno'}
               for a, b in franjas_del_dia(usuario, fecha)]
    for b in BloqueOcupado.objects.filter(status=True, usuario=usuario, inicio__lt=dia_fin, fin__gt=dia_ini).select_related('cita'):
        bloques.append({'inicio': b.inicio, 'fin': b.fin, 'tipo': b.fuente, 'cita': b.cita})
    for inicio, fin in ocupados_google(usuario, dia_ini, dia_fin):
        bloques.append({'inicio': max(inicio, dia_ini), 'fin': min(fin, dia_fin), 'tipo': 'google'})
    return sorted(bloques, key=lambda b: (b['inicio'], b['tipo'] != 'turno'))


def primer_espacio(usuarios, desde, dias=14, duracion=None, margen=0, antelacion_horas=None):
    """Primer inicio común desde `desde` (datetime) dentro de `dias`, respetando la antelación."""
    antelacion = antelacion_horas if antelacion_horas is not None else _parametro_int('agenda_antelacion_horas', 24)
    minimo = desde + timedelta(hours=antelacion)
    fecha = minimo.date()
    for _ in range(dias + 1):
        espacios = espacios_comunes(usuarios, fecha, duracion, margen, desde_hora=minimo if fecha == minimo.date() else None)
        if espacios:
            return espacios[0]
        fecha += timedelta(days=1)
    return None
