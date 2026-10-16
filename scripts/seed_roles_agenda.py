"""Grupos (roles) de la agenda con los módulos que abre cada uno: Líder general, Líder de equipo,
Coordinador y Miembro. Corre después de `scripts/seed_modulos.py` (crea los `Modulo`).

Idempotente: crea el grupo y su `GroupModulo` si faltan y hace UNIÓN con los módulos ya asignados
(no quita los que alguien agregó desde el panel).

Uso:  python scripts/seed_roles_agenda.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backcalendar.settings')

import django

django.setup()

from django.contrib.auth.models import Group
from django.db import transaction

from agenda.funciones_permisos import ROL_COORDINADOR, ROL_LIDER_EQUIPO, ROL_LIDER_GENERAL, ROL_MIEMBRO
from seguridad.models import GroupModulo, Modulo

COMUNES = ['/agenda/mi-dia/', '/agenda/mi-agenda/', '/agenda/mis-turnos/', '/agenda/citas/', '/agenda/buscar/', '/agenda/alertas/', '/agenda/aplicaciones/']
ROLES = {
    ROL_LIDER_GENERAL: COMUNES + ['/agenda/agenda-equipo/', '/agenda/cola/', '/agenda/solicitudes/', '/agenda/clientes/', '/agenda/portales/', '/agenda/parametros/', '/agenda/turnos-equipo/', '/agenda/proyectos/', '/agenda/equipos/', '/agenda/feriados/',
                                  '/autenticacion/usuario/', '/seguridad/grupo/'],
    ROL_LIDER_EQUIPO: COMUNES + ['/agenda/agenda-equipo/', '/agenda/cola/', '/agenda/solicitudes/', '/agenda/clientes/', '/agenda/turnos-equipo/', '/agenda/proyectos/', '/agenda/equipos/', '/agenda/feriados/'],
    ROL_COORDINADOR: COMUNES + ['/agenda/agenda-equipo/', '/agenda/cola/', '/agenda/solicitudes/', '/agenda/clientes/', '/agenda/feriados/'],
    ROL_MIEMBRO: COMUNES,
}


def run():
    with transaction.atomic():
        for nombre, urls in ROLES.items():
            grupo, creado = Group.objects.get_or_create(name=nombre)
            gm, _ = GroupModulo.objects.get_or_create(group=grupo, defaults={'status': True})
            if not gm.status:
                gm.status = True
                gm.save()
            modulos = list(Modulo.objects.filter(status=True, url__in=urls))
            faltan = sorted(set(urls) - {m.url for m in modulos})
            existentes = set(gm.modulos.values_list('id', flat=True))
            nuevos = [m for m in modulos if m.id not in existentes]
            if nuevos:
                gm.modulos.add(*nuevos)
            print(f"  {'+' if creado else '~'} {nombre} (pk={grupo.pk}): {len(modulos)} módulos, +{len(nuevos)} nuevos"
                  + (f", sin registrar: {faltan}" if faltan else ''))
    print('Listo.')


if __name__ == '__main__':
    run()
