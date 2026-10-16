"""Registra en el panel de crons la tarea de purga de históricos y sesiones.

Idempotente: usa `update_or_create` por `clave`, así que re-correrlo no duplica ni pisa el
`activo`/`schedule` que alguien haya cambiado desde /seguridad/crons/ (solo repone nombre,
comando, descripción y log).

    python manage.py shell -c "exec(open('scripts/seed_crons_mantenimiento.py').read())"
"""
from seguridad.models import TareaCron

TAREAS = [
    {
        'clave': 'purgar_historicos',
        'nombre': 'Purga de históricos y sesiones',
        'comando': 'python manage.py purgar_historicos',
        'schedule': '40 3 * * *',
        'icono': 'bi-trash3',
        'orden': 70,
        'descripcion': 'Borra los logs de cron anteriores a la retención (90 días) y las sesiones '
                       'vencidas.',
    },
    {
        'clave': 'recordatorios_citas',
        'nombre': 'Recordatorios de citas al cliente',
        'comando': 'python manage.py recordatorios_citas',
        'schedule': '*/15 * * * *',
        'icono': 'bi-bell',
        'orden': 80,
        'descripcion': 'Cada 15 minutos revisa las citas próximas y manda al cliente los avisos configurados en '
                       '«Parámetros» (por defecto 24 h y 1 h antes).',
    },
    {
        'clave': 'avisos_citas',
        'nombre': 'Avisos de cita próxima al equipo',
        'comando': 'python manage.py avisos_citas',
        'schedule': '*/5 * * * *',
        'icono': 'bi-alarm',
        'orden': 81,
        'descripcion': 'Cada 5 minutos crea la alerta «tu cita empieza pronto» (notificación y push) para cada '
                       'participante según sus minutos de aviso.',
    },
    {
        'clave': 'reconciliar_google',
        'nombre': 'Reconciliación con Google Calendar',
        'comando': 'python manage.py reconciliar_google',
        'schedule': '20 * * * *',
        'icono': 'bi-arrow-repeat',
        'orden': 82,
        'descripcion': 'Cada hora reintenta las citas que no llegaron a Google y refleja aquí lo que cambió allá: '
                       'eventos borrados (la cita queda pendiente), movidos (se mueve aquí) y respuestas de invitados.',
    },
    {
        'clave': 'mantenimiento_agenda',
        'nombre': 'Mantenimiento de la agenda',
        'comando': 'python manage.py mantenimiento_agenda',
        'schedule': '50 3 * * *',
        'icono': 'bi-shield-check',
        'orden': 83,
        'descripcion': 'Diario: anonimiza la IP de las reservas pasado el plazo de «Conservación de la IP completa» y '
                       'revoca los enlaces vencidos.',
    },
]

for datos in TAREAS:
    clave = datos.pop('clave')
    schedule = datos.pop('schedule')
    tarea, creada = TareaCron.objects.update_or_create(clave=clave, defaults=datos)
    if creada:
        tarea.schedule = schedule
        tarea.activo = True
        tarea.gestionado_crontab = True
        tarea.status = True
        tarea.save()
    print(f"{'creada ' if creada else 'ya estaba'} → {clave} ({tarea.schedule}) activo={tarea.activo}")
