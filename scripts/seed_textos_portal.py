"""Textos del portal público en español, inglés y portugués (`TextoPortal`).

Idempotente: crea la clave si falta y repone las tres traducciones.

    python scripts/seed_textos_portal.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backcalendar.settings')

import django

django.setup()

from django.db import transaction

from agenda.models import TextoPortal

from agenda.textos_portal import TEXTOS


def run():
    with transaction.atomic():
        for clave, es, en, pt in TEXTOS:
            fila, creado = TextoPortal.objects.update_or_create(clave=clave, defaults={'es': es, 'en': en, 'pt': pt, 'status': True})
            print(f"  {'+' if creado else '~'} {clave}")
    print('Listo.')


if __name__ == '__main__':
    run()
