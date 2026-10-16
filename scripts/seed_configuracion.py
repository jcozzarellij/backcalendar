"""Crea la fila única de `seguridad.Configuracion` si la base es nueva, con datos genéricos.

Idempotente: si ya existe una configuración no toca nada (los nombres, logos y correos se
editan desde /seguridad/configuracion/).

    python manage.py shell -c "exec(open('scripts/seed_configuracion.py').read())"
"""
from seguridad.models import Configuracion

if Configuracion.objects.exists():
    print('ya existe la configuración del sitio; no se toca.')
else:
    Configuracion.objects.create(
        nombre_empresa='Turno',
        alias='Turno',
        titulo='Turno de Exducere Online',
        descripcion='Agenda de citas del equipo de Exducere Online.',
        email_notificacion='',
    )
    Configuracion.limpiar_cache()
    print('configuración del sitio creada.')
