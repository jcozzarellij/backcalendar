"""Turnos declarados: semana tipo con vigencia, excepciones y feriados.

Interfaz:
- `duracion_turno()` — minutos de cada espacio (parámetro global).
- `franjas_del_dia(usuario, fecha)` — horas disponibles declaradas ese día, ya descontadas las
  excepciones y los feriados. Es la base del motor de disponibilidad.
- `aplicar_semana_tipo(usuario, franjas_por_dia, desde, hasta, request)` — guarda una semana tipo y recorta
  las vigencias de las anteriores para que nunca se solapen.
"""
from datetime import datetime, time, timedelta

from django.db.models import Q

from seguridad.models import ParametroSistema
from .models import ExcepcionTurno, Feriado, FranjaTurno, PatronTurno

DURACION_TURNO_DEFAULT = 40
HORA_INICIO_REJILLA = time(7, 0)
HORA_FIN_REJILLA = time(20, 0)


def duracion_turno():
    valor = ParametroSistema.valor_de('agenda_duracion_turno', DURACION_TURNO_DEFAULT)
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        valor = DURACION_TURNO_DEFAULT
    return valor if 5 <= valor <= 240 else DURACION_TURNO_DEFAULT


def horas_rejilla(paso_min=None):
    """Horas de inicio de cada espacio de la rejilla de la semana tipo."""
    paso = timedelta(minutes=paso_min or duracion_turno())
    actual = datetime.combine(datetime.today(), HORA_INICIO_REJILLA)
    fin = datetime.combine(datetime.today(), HORA_FIN_REJILLA)
    horas = []
    while actual + paso <= fin:
        horas.append(actual.time())
        actual += paso
    return horas


def patron_vigente(usuario, fecha):
    return (PatronTurno.objects
            .filter(status=True, usuario=usuario, vigencia_desde__lte=fecha)
            .filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=fecha))
            .order_by('-vigencia_desde')
            .first())


def _es_feriado(usuario, fecha):
    equipos = usuario.membresias_agenda.filter(status=True).values_list('equipo_id', flat=True)
    return Feriado.objects.filter(status=True, fecha=fecha).filter(
        Q(equipo__isnull=True) | Q(equipo_id__in=list(equipos))).exists()


def franjas_del_dia(usuario, fecha):
    """Lista ordenada de (hora_inicio, hora_fin) que el usuario declaró disponibles ese día."""
    if _es_feriado(usuario, fecha):
        return []
    excepciones = list(ExcepcionTurno.objects.filter(
        status=True, usuario=usuario, fecha_desde__lte=fecha, fecha_hasta__gte=fecha))
    especiales = [e for e in excepciones if e.tipo == 'horario_especial' and e.hora_inicio and e.hora_fin]
    if especiales:
        return sorted((e.hora_inicio, e.hora_fin) for e in especiales)
    if any(not (e.hora_inicio and e.hora_fin) for e in excepciones):
        return []
    patron = patron_vigente(usuario, fecha)
    if not patron:
        return []
    franjas = [(f.hora_inicio, f.hora_fin) for f in
               patron.franjas.filter(status=True, dia_semana=fecha.weekday()).order_by('hora_inicio')]
    for e in excepciones:
        franjas = _restar(franjas, e.hora_inicio, e.hora_fin)
    return franjas


def _restar(franjas, inicio, fin):
    resultado = []
    for a, b in franjas:
        if fin <= a or inicio >= b:
            resultado.append((a, b))
            continue
        if a < inicio:
            resultado.append((a, inicio))
        if fin < b:
            resultado.append((fin, b))
    return resultado


def celdas_a_franjas(celdas, paso_min):
    """`celdas` = {dia_semana: [hora 'HH:MM', ...]}. Une los espacios contiguos en franjas."""
    paso = timedelta(minutes=paso_min)
    franjas = {}
    for dia, horas in celdas.items():
        inicios = sorted({datetime.strptime(h, '%H:%M') for h in horas})
        bloques = []
        for inicio in inicios:
            if bloques and bloques[-1][1] == inicio:
                bloques[-1][1] = inicio + paso
            else:
                bloques.append([inicio, inicio + paso])
        franjas[int(dia)] = [(a.time(), b.time()) for a, b in bloques]
    return franjas


def franjas_a_celdas(patron, paso_min):
    """Inversa de `celdas_a_franjas` para pintar la rejilla: {dia: ['HH:MM', ...]}."""
    paso = timedelta(minutes=paso_min)
    celdas = {d: [] for d in range(7)}
    if not patron:
        return celdas
    for f in patron.franjas.filter(status=True):
        actual = datetime.combine(datetime.today(), f.hora_inicio)
        fin = datetime.combine(datetime.today(), f.hora_fin)
        while actual + paso <= fin:
            celdas[f.dia_semana].append(actual.strftime('%H:%M'))
            actual += paso
    return celdas


def _dar_de_baja(patron, request):
    for franja in patron.franjas.filter(status=True):
        franja.status = False
        franja.save(request)
    patron.status = False
    patron.save(request)


def _copiar(patron, desde, hasta, request):
    copia = PatronTurno(usuario=patron.usuario, vigencia_desde=desde, vigencia_hasta=hasta)
    copia.save(request)
    for f in patron.franjas.filter(status=True):
        FranjaTurno(patron=copia, dia_semana=f.dia_semana, hora_inicio=f.hora_inicio, hora_fin=f.hora_fin).save(request)
    return copia


def aplicar_semana_tipo(usuario, franjas_por_dia, desde, hasta, request):
    """Crea la semana tipo [desde, hasta] y recorta las vigentes que se solapan. Debe correr
    dentro de `transaction.atomic()`; bloquea los patrones del usuario para que dos
    guardados simultáneos no dejen vigencias cruzadas."""
    if hasta and hasta < desde:
        raise ValueError('La fecha final debe ser igual o posterior a la inicial.')
    if not any(franjas_por_dia.values()):
        raise ValueError('Marca al menos un espacio antes de guardar.')
    un_dia = timedelta(days=1)
    existentes = (PatronTurno.objects.select_for_update()
                  .filter(status=True, usuario=usuario)
                  .filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=desde)))
    if hasta:
        existentes = existentes.filter(vigencia_desde__lte=hasta)
    for p in existentes:
        termina_despues = hasta is not None and (p.vigencia_hasta is None or p.vigencia_hasta > hasta)
        if p.vigencia_desde < desde:
            if termina_despues:
                _copiar(p, hasta + un_dia, p.vigencia_hasta, request)
            p.vigencia_hasta = desde - un_dia
            p.save(request)
        elif termina_despues:
            p.vigencia_desde = hasta + un_dia
            p.save(request)
        else:
            _dar_de_baja(p, request)
    patron = PatronTurno(usuario=usuario, vigencia_desde=desde, vigencia_hasta=hasta)
    patron.save(request)
    for dia, franjas in franjas_por_dia.items():
        for inicio, fin in franjas:
            FranjaTurno(patron=patron, dia_semana=dia, hora_inicio=inicio, hora_fin=fin).save(request)
    return patron
