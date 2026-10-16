"""Roles de la agenda sobre los grupos de Django. El acceso a cada pantalla lo da `GroupModulo`
(`@secure_module`); estas funciones resuelven el alcance DENTRO de una pantalla: qué equipos ve,
de quién puede editar turnos, qué citas puede mover.

Roles (nombres de grupo): Líder general, Líder de equipo, Coordinador, Miembro.
Una persona puede tener varios; se suman los permisos. El superusuario lo puede todo.
"""
from django.db.models import Q

from .models import Equipo

ROL_LIDER_GENERAL = 'Líder general'
ROL_LIDER_EQUIPO = 'Líder de equipo'
ROL_COORDINADOR = 'Coordinador'
ROL_MIEMBRO = 'Miembro'
ROLES_AGENDA = (ROL_LIDER_GENERAL, ROL_LIDER_EQUIPO, ROL_COORDINADOR, ROL_MIEMBRO)


def roles_de(usuario):
    if not usuario or not usuario.is_authenticated:
        return set()
    return set(usuario.groups.filter(name__in=ROLES_AGENDA).values_list('name', flat=True))


def es_lider_general(usuario):
    return bool(usuario.is_superuser or ROL_LIDER_GENERAL in roles_de(usuario))


def es_coordinador(usuario):
    return es_lider_general(usuario) or ROL_COORDINADOR in roles_de(usuario)


def equipos_que_lidera(usuario):
    """Equipos donde el usuario es líder del equipo o de su proyecto."""
    return Equipo.objects.filter(Q(status=True) & (Q(lider=usuario) | Q(proyecto__lider=usuario)))


def es_lider_equipo(usuario, equipo=None):
    if es_lider_general(usuario):
        return True
    if ROL_LIDER_EQUIPO not in roles_de(usuario):
        return False
    if equipo is None:
        return equipos_que_lidera(usuario).exists()
    return equipos_que_lidera(usuario).filter(pk=equipo.pk).exists()


def equipos_visibles(usuario):
    """Líder general y coordinador: todos. Los demás: los equipos donde participan o lideran."""
    if es_coordinador(usuario):
        return Equipo.objects.filter(status=True)
    return Equipo.objects.filter(
        Q(status=True) & (Q(miembros__usuario=usuario, miembros__status=True) | Q(lider=usuario) | Q(proyecto__lider=usuario))
    ).distinct()


def puede_editar_turnos_de(usuario, otro):
    """Cada quien edita sus turnos; el líder general los de todos; el líder de equipo los de su equipo."""
    if usuario == otro or es_lider_general(usuario):
        return True
    return equipos_que_lidera(usuario).filter(miembros__usuario=otro, miembros__status=True).exists()


def puede_gestionar_equipo(usuario, equipo):
    return es_lider_general(usuario) or es_lider_equipo(usuario, equipo)
