"""Genera las alertas internas «tu cita empieza pronto» (notificación + push) para el equipo.

Correr cada 5 minutos desde el crontab; respeta el interruptor del panel de crons (clave
`avisos_citas`) y deja su heartbeat.

    python manage.py avisos_citas
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crea las alertas de cita próxima para los participantes del equipo.'

    def handle(self, *args, **opts):
        from seguridad.funciones_cron import ejecutar_cron
        ejecutar_cron('avisos_citas', self._generar, log=self.stdout.write)

    def _generar(self):
        from agenda.funciones_alertas import generar_avisos
        creados = generar_avisos()
        self.stdout.write(f'Avisos creados: {creados}.')
