"""Modo de asignación de cada equipo (`Equipo.modo_asignacion`): qué horas se ofrecen y a quién va la cita.

- 'equipo': la organiza el líder y asisten todos los responsables; se ofrecen las horas en que todos están libres.
- 'persona': queda a cargo de un responsable; se ofrecen las horas en que al menos uno está libre y se elige al
  libre con menos citas esa semana; si empatan, rota empezando por el siguiente a `Equipo.ultimo_asignado`.

Interfaz:
- `es_por_persona(equipo)`.
- `espacios_equipo_rango(equipo, desde, hasta, duracion=None, margen=0, paso=None, desde_hora=None)` — {fecha: inicios}.
- `primer_espacio_equipo(equipo, desde, dias=14, duracion=None, margen=0, antelacion_horas=None)`.
- `carga_semana(usuarios, fecha)` — {pk: citas activas como asistente en la semana (lunes a domingo) de `fecha`}.
- `elegir_persona(equipo, inicio, fin)` — el responsable libre que toca; None si nadie está libre.
- `organizador_para(equipo, inicio, fin, elegido=None, respaldo=None)` — quién organiza según el modo.
- `candidatos(equipo, inicio, fin)` — para «Asignar a»: pk, nombre, rol, estado, citas, google, sugerido.
"""
from datetime import datetime, timedelta

from django.db.models import Count

from .funciones_citas import personas_de, responsables_de
from .funciones_disponibilidad import _parametro_int, espacios_alguno_rango, espacios_comunes_rango, estado_en
from .models import ConexionAplicacion, ParticipanteCita


def es_por_persona(equipo):
    return equipo is not None and equipo.modo_asignacion == 'persona'


def espacios_equipo_rango(equipo, desde, hasta, duracion=None, margen=0, paso=None, desde_hora=None):
    responsables = responsables_de(equipo) if equipo else []
    if not responsables:
        return {}
    calcular = espacios_alguno_rango if es_por_persona(equipo) else espacios_comunes_rango
    return calcular(responsables, desde, hasta, duracion, margen, paso, desde_hora)


def primer_espacio_equipo(equipo, desde, dias=14, duracion=None, margen=0, antelacion_horas=None):
    antelacion = antelacion_horas if antelacion_horas is not None else _parametro_int('agenda_antelacion_horas', 24)
    minimo = desde + timedelta(hours=antelacion)
    por_dia = espacios_equipo_rango(equipo, minimo.date(), minimo.date() + timedelta(days=dias), duracion, margen,
                                    desde_hora=minimo)
    return next((espacios[0] for _, espacios in sorted(por_dia.items()) if espacios), None)


def carga_semana(usuarios, fecha):
    lunes = datetime.combine(fecha - timedelta(days=fecha.weekday()), datetime.min.time())
    filas = (ParticipanteCita.objects.filter(status=True, usuario__in=usuarios, cita__status=True,
                                             cita__inicio__gte=lunes, cita__inicio__lt=lunes + timedelta(days=7))
             .exclude(cita__estado='cancelada').exclude(rol='copia')
             .values('usuario').annotate(total=Count('cita', distinct=True)))
    return {f['usuario']: f['total'] for f in filas}


def elegir_persona(equipo, inicio, fin):
    responsables = responsables_de(equipo)
    return _que_toca(equipo, responsables, {u.pk: estado_en(u, inicio, fin) for u in responsables}, inicio)


def organizador_para(equipo, inicio, fin, elegido=None, respaldo=None):
    """`elegido` (pk) lo fija a mano y debe ser líder o responsable. Sin él: en modo persona, el que toca; en modo
    equipo, el líder (o el primer responsable, o el líder del proyecto)."""
    if elegido:
        personas = {u.pk: u for u in personas_de(equipo)}
        if int(elegido) not in personas:
            raise ValueError('Esa persona no es líder ni responsable del equipo elegido.')
        return personas[int(elegido)]
    if es_por_persona(equipo):
        persona = elegir_persona(equipo, inicio, fin)
        if persona is None:
            raise ValueError('Nadie del equipo está libre a esa hora. Elige otro horario o asígnala a mano.')
        return persona
    responsables = responsables_de(equipo)
    return (equipo.lider or (responsables[0] if responsables else None)
            or (equipo.proyecto.lider if equipo.proyecto_id else None) or respaldo)


def candidatos(equipo, inicio, fin):
    personas = personas_de(equipo)
    estados = {u.pk: estado_en(u, inicio, fin) for u in personas}
    carga = carga_semana(personas, inicio.date())
    con_google = set(ConexionAplicacion.objects.filter(status=True, proveedor='google', conectada=True,
                                                       usuario__in=personas).values_list('usuario_id', flat=True))
    responsables = responsables_de(equipo)
    ids_responsables = {u.pk for u in responsables}
    if es_por_persona(equipo):
        sugerido = _que_toca(equipo, responsables, estados, inicio)
    else:
        sugerido = organizador_para(equipo, inicio, fin)
    return [{
        'pk': u.pk, 'nombre': u.get_full_name() or u.username,
        'rol': 'Líder' if u.pk == equipo.lider_id or u.pk not in ids_responsables else 'Responsable',
        'estado': estados[u.pk], 'citas': carga.get(u.pk, 0), 'google': u.pk in con_google,
        'sugerido': sugerido is not None and u.pk == sugerido.pk,
    } for u in personas]


def _que_toca(equipo, responsables, estados, inicio):
    libres = [u for u in responsables if estados.get(u.pk) == 'libre']
    if not libres:
        return None
    carga = carga_semana(libres, inicio.date())
    orden = sorted(responsables, key=lambda u: u.pk)
    ids = [u.pk for u in orden]
    if equipo.ultimo_asignado_id in ids:
        corte = ids.index(equipo.ultimo_asignado_id) + 1
        orden = orden[corte:] + orden[:corte]
    turno = {u.pk: n for n, u in enumerate(orden)}
    return min(libres, key=lambda u: (carga.get(u.pk, 0), turno[u.pk]))
