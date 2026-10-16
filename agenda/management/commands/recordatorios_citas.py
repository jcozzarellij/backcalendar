"""Envía los recordatorios de cita pendientes (ver `agenda/funciones_recordatorios.py`).

Pensado para correr cada 15 minutos desde el crontab; respeta el interruptor del panel de crons
(`TareaCron` clave `recordatorios_citas`) y deja su heartbeat.

    python manage.py recordatorios_citas
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Envía al cliente los recordatorios de las citas próximas.'

    def handle(self, *args, **opts):
        from seguridad.funciones_cron import ejecutar_cron
        ejecutar_cron('recordatorios_citas', self._enviar, log=self.stdout.write)

    def _enviar(self):
        from agenda.funciones_recordatorios import enviar_pendientes
        enviados, fallidos = enviar_pendientes()
        self.stdout.write(f'Recordatorios enviados: {enviados}. Fallidos: {fallidos}.')
        if fallidos:
            raise RuntimeError(f'{fallidos} recordatorio(s) no se pudieron enviar.')
