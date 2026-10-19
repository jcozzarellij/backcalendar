"""Avisa por correo y web push las citas y reuniones que empiezan en los próximos 10 minutos.

Correr cada minuto desde el crontab; respeta el interruptor del panel de crons (clave
`avisos_proximos`) y deja su heartbeat.

    python manage.py avisos_proximos
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Avisa por correo y push lo que empieza en los próximos 10 minutos.'

    def handle(self, *args, **opts):
        from seguridad.funciones_cron import ejecutar_cron
        ejecutar_cron('avisos_proximos', self._generar, log=self.stdout.write)

    def _generar(self):
        from agenda.funciones_avisos_proximos import enviar_avisos_proximos
        enviados, fallidos = enviar_avisos_proximos()
        self.stdout.write(f'Avisos enviados: {enviados}. Fallidos: {fallidos}.')
