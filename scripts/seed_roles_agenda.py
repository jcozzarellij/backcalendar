"""Perfiles de la agenda y los módulos que abre cada uno: Administrador de proyectos y Programador
(integrante del proyecto). El Administrador, que ve todo, lo siembra `scripts/seed_modulos.py`;
este script corre después porque necesita los `Modulo` ya creados.

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

from django.db import transaction

from agenda.funciones_permisos import ROL_ADMIN_PROYECTOS, ROL_PROGRAMADOR
from scripts.seed_modulos import asignar_grupo_modulos
from seguridad.models import Modulo

COMUNES = ['/agenda/mi-dia/', '/agenda/mi-agenda/', '/agenda/mis-turnos/', '/agenda/citas/', '/agenda/buscar/', '/agenda/alertas/', '/agenda/aplicaciones/']
GESTION = COMUNES + ['/agenda/agenda-equipo/', '/agenda/cola/', '/agenda/solicitudes/', '/agenda/clientes/', '/agenda/turnos-equipo/', '/agenda/proyectos/', '/agenda/equipos/', '/agenda/feriados/']
ROLES = {
    ROL_ADMIN_PROYECTOS: GESTION,
    ROL_PROGRAMADOR: COMUNES,
}


def run():
    with transaction.atomic():
        for nombre, urls in ROLES.items():
            modulos_por_url = {m.url: m for m in Modulo.objects.filter(status=True, url__in=urls)}
            faltan = sorted(set(urls) - set(modulos_por_url))
            if faltan:
                print(f'  ! {nombre}: sin registrar {faltan} (correr antes scripts/seed_modulos.py)')
            asignar_grupo_modulos(nombre, modulos_por_url, authoritative=False)
    print('Listo.')


if __name__ == '__main__':
    run()
