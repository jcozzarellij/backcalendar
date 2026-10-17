"""Usuarios del equipo de Turno. Renombra al administrador heredado y crea a las personas del
equipo con acceso al panel y el rol Miembro. La clave inicial es el usuario seguido de 2026 y
`cambio_clave=True` obliga a cambiarla en el primer ingreso.

Idempotente: busca por nombre y apellido; no toca claves de usuarios que ya existen.

Uso:  python scripts/seed_usuarios_equipo.py
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

from agenda.funciones_permisos import ROL_ADMINISTRADOR, ROL_PROGRAMADOR
from autenticacion.models import Usuario
from core.funciones import codnombre

ADMIN = {'first_name': 'Héctor', 'last_name': 'Llerena', 'email': 'hector.llerena@exducereonline.com'}
EQUIPO = [
    ('Pedro', 'Gutiérrez'),
    ('Jazmani', 'Correa'),
    ('John', 'Gómez'),
    ('Javier', 'Jadán'),
]


def run():
    with transaction.atomic():
        admin = Usuario.objects.filter(is_superuser=True, is_active=True).order_by('id').first()
        if admin and (admin.first_name != ADMIN['first_name'] or admin.last_name != ADMIN['last_name']):
            admin.first_name, admin.last_name = ADMIN['first_name'], ADMIN['last_name']
            if not admin.email or 'cne' in admin.email.lower():
                admin.email = ADMIN['email']
            admin.save()
            print(f'  ~ administrador renombrado: {admin.get_full_name()} ({admin.username})')
        administrador, _ = Group.objects.get_or_create(name=ROL_ADMINISTRADOR)
        if admin and not admin.groups.filter(pk=administrador.pk).exists():
            admin.groups.add(administrador)
        programador, _ = Group.objects.get_or_create(name=ROL_PROGRAMADOR)
        for nombre, apellido in EQUIPO:
            usuario = Usuario.objects.filter(first_name__iexact=nombre, last_name__iexact=apellido).first()
            if usuario is None:
                username = codnombre(nombre, apellido)
                usuario = Usuario.objects.create_user(username=username, password=f'{username}2026', first_name=nombre,
                                                      last_name=apellido, email='', is_staff=True, direccion='')
                usuario.cambio_clave = True
                usuario.save()
                print(f'  + {usuario.get_full_name()} -> usuario {usuario.username}')
            else:
                if not usuario.is_staff or not usuario.is_active:
                    usuario.is_staff = usuario.is_active = True
                    usuario.save()
                print(f'  ~ {usuario.get_full_name()} ya existe ({usuario.username})')
            if not usuario.groups.filter(pk=programador.pk).exists():
                usuario.groups.add(programador)
    print('Listo.')


if __name__ == '__main__':
    run()
