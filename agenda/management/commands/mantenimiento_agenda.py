"""Mantenimiento diario de la agenda: anonimiza la IP de las capturas técnicas pasado
`cliente_conservar_ip_dias` y revoca los tokens de acceso vencidos hace más de 30 días.

    python manage.py mantenimiento_agenda
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Anonimiza IPs viejas y revoca tokens vencidos de la agenda.'

    def handle(self, *args, **opts):
        from seguridad.funciones_cron import ejecutar_cron
        ejecutar_cron('mantenimiento_agenda', self._mantener, log=self.stdout.write)

    def _mantener(self):
        from datetime import datetime, timedelta
        from seguridad.models import ParametroSistema
        from agenda.models import CapturaTecnica, TokenAcceso
        try:
            dias = int(ParametroSistema.valor_de('cliente_conservar_ip_dias', 90))
        except (TypeError, ValueError):
            dias = 90
        corte = datetime.now() - timedelta(days=dias)
        capturas = 0
        for c in CapturaTecnica.objects.filter(status=True, anonimizada=False, fecha_registro__lt=corte):
            partes = c.ip.split('.')
            c.ip = '.'.join(partes[:2] + ['0', '0']) if len(partes) == 4 else (c.ip.split(':')[0] + '::' if c.ip else '')
            c.anonimizada = True
            c.save(update_fields=['ip', 'anonimizada'])
            capturas += 1
        tokens = TokenAcceso.objects.filter(status=True, revocado=False, vence__lt=datetime.now() - timedelta(days=30)).update(revocado=True)
        self.stdout.write(f'IPs anonimizadas: {capturas}. Tokens revocados: {tokens}.')
