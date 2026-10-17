"""Roles de la agenda sobre los grupos de Django. El acceso a cada pantalla lo da `GroupModulo`
(`@secure_module`); estas funciones resuelven el alcance DENTRO de una pantalla: qué equipos ve,
de quién puede editar turnos, qué citas puede mover.

Perfiles (nombres de grupo): Administrador (ve todo), Administrador de proyectos y Programador (integrante del proyecto).
Una persona puede tener varios; se suman los permisos. El superusuario lo puede todo.
"""
from django.db.models import Q

from .models import Equipo

ROL_ADMINISTRADOR = 'Administrador'
ROL_ADMIN_PROYECTOS = 'Administrador de proyectos'
ROL_PROGRAMADOR = 'Programador'
ROLES_AGENDA = (ROL_ADMINISTRADOR, ROL_ADMIN_PROYECTOS, ROL_PROGRAMADOR)


def roles_de(usuario):
    if not usuario or not usuario.is_authenticated:
        return set()
    return set(usuario.groups.filter(name__in=ROLES_AGENDA).values_list('name', flat=True))


def es_administrador(usuario):
    return bool(usuario.is_superuser or ROL_ADMINISTRADOR in roles_de(usuario))


def es_admin_proyectos(usuario):
    return es_administrador(usuario) or ROL_ADMIN_PROYECTOS in roles_de(usuario)


def equipos_que_lidera(usuario):
    """Equipos donde el usuario es líder del equipo o de su proyecto."""
    return Equipo.objects.filter(Q(status=True) & (Q(lider=usuario) | Q(proyecto__lider=usuario)))


def es_lider_equipo(usuario, equipo=None):
    if es_administrador(usuario):
        return True
    if ROL_ADMIN_PROYECTOS not in roles_de(usuario):
        return False
    if equipo is None:
        return equipos_que_lidera(usuario).exists()
    return equipos_que_lidera(usuario).filter(pk=equipo.pk).exists()


def equipos_visibles(usuario):
    """Administrador y administrador de proyectos: todos. Los demás: los equipos donde participan o lideran."""
    if es_admin_proyectos(usuario):
        return Equipo.objects.filter(status=True)
    return Equipo.objects.filter(
        Q(status=True) & (Q(miembros__usuario=usuario, miembros__status=True) | Q(lider=usuario) | Q(proyecto__lider=usuario))
    ).distinct()


def puede_editar_turnos_de(usuario, otro):
    """Cada quien edita sus turnos; el administrador los de todos; quien lidera un equipo, los de ese equipo."""
    if usuario == otro or es_administrador(usuario):
        return True
    return equipos_que_lidera(usuario).filter(miembros__usuario=otro, miembros__status=True).exists()


def puede_gestionar_equipo(usuario, equipo):
    return es_administrador(usuario) or es_lider_equipo(usuario, equipo)
