"""Reconcilia las citas confirmadas con Google Calendar (ver `agenda/funciones_reconciliacion.py`).

Correr cada hora desde el crontab; respeta el interruptor del panel de crons (clave `reconciliar_google`).

    python manage.py reconciliar_google [--dias 30]
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Reintenta sincronizaciones fallidas y refleja aquí lo que cambió en Google Calendar.'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=30, help='Hasta cuántos días adelante revisar (30).')

    def handle(self, *args, **opts):
        from seguridad.funciones_cron import ejecutar_cron
        ejecutar_cron('reconciliar_google', lambda: self._reconciliar(opts['dias']), log=self.stdout.write)

    def _reconciliar(self, dias):
        from agenda.funciones_reconciliacion import reconciliar
        r = reconciliar(dias=dias)
        self.stdout.write('Revisadas {revisadas}, reintentadas {reintentadas}, borradas en Google {canceladas_en_google}, '
                          'movidas en Google {movidas_en_google}, respuestas {respuestas}, errores {errores}; '
                          'reuniones pendientes {p}, al día {a}.'.format(**r, p=r.get('reuniones_pendientes', 0),
                                                                         a=r.get('reuniones_al_dia', 0)))
