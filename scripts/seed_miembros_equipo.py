"""Agrega a las personas de `seed_usuarios_equipo.EQUIPO` como responsables de todos los equipos
activos, para que `seed_turnos_equipo.py` les arme la semana tipo y el portal ofrezca horarios.

Correr después de `seed_usuarios_equipo.py` y antes de `seed_turnos_equipo.py`.
Idempotente: no duplica membresías activas (equipo + usuario).

Uso:  python scripts/seed_miembros_equipo.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backcalendar.settings')

import django

django.setup()

from django.db import transaction

from agenda.models import Equipo, MiembroEquipo
from autenticacion.models import Usuario
from scripts.seed_usuarios_equipo import EQUIPO


def run():
    with transaction.atomic():
        equipos = list(Equipo.objects.filter(status=True).order_by('id'))
        for nombre, apellido in EQUIPO:
            usuario = Usuario.objects.filter(first_name__iexact=nombre, last_name__iexact=apellido, status=True).first()
            if usuario is None:
                print(f'  ! {nombre} {apellido}: no existe (correr antes scripts/seed_usuarios_equipo.py)')
                continue
            for equipo in equipos:
                _, creado = MiembroEquipo.objects.get_or_create(equipo=equipo, usuario=usuario, status=True,
                                                                defaults={'rol': 'responsable'})
                print(f"  {'+' if creado else '='} {usuario.username} en {equipo}")
    print('Listo.')


if __name__ == '__main__':
    run()
