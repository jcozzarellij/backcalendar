"""Semana tipo de ejemplo para el equipo (lunes a viernes, 09:00–13:00 y 14:00–18:00) para que el
portal público tenga horarios que ofrecer. Idempotente: salta a quien ya tiene una semana tipo.

Uso: python scripts/seed_turnos_equipo.py
"""
import os
import sys
from datetime import date, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backcalendar.settings')

import django

django.setup()

from django.db import transaction

from agenda.models import FranjaTurno, MiembroEquipo, PatronTurno

FRANJAS = [(time(9, 0), time(13, 0)), (time(14, 0), time(18, 0))]


def run():
    usuarios = {m.usuario for m in MiembroEquipo.objects.filter(status=True).select_related('usuario')}
    with transaction.atomic():
        for usuario in sorted(usuarios, key=lambda u: u.username):
            if PatronTurno.objects.filter(status=True, usuario=usuario).exists():
                print(f'  = {usuario.username}: ya tiene semana tipo')
                continue
            patron = PatronTurno.objects.create(usuario=usuario, vigencia_desde=date.today().replace(day=1))
            for dia in range(5):
                for inicio, fin in FRANJAS:
                    FranjaTurno.objects.create(patron=patron, dia_semana=dia, hora_inicio=inicio, hora_fin=fin)
            print(f'  + {usuario.username}: lunes a viernes 09:00-13:00 y 14:00-18:00')
    print('Listo.')


if __name__ == '__main__':
    run()
