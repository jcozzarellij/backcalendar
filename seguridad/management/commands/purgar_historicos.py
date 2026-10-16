"""Purga las series de tiempo que crecen sin techo y las sesiones vencidas.

Los logs de cron se acumulan indefinidamente y `django_session` tampoco se limpia solo
(`SESSION_SAVE_EVERY_REQUEST` escribe en cada request).

Qué NO toca, a propósito:
- `AudiUsuarioTabla`: auditoría de quién tocó qué. No se purga.

    python manage.py purgar_historicos [--dias 90] [--dry-run]
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Borra logs de ejecución de cron antiguos y sesiones vencidas.'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=None,
                            help='Días de retención (90 por defecto).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Cuenta lo que borraría, sin borrar.')

    def handle(self, *args, **opts):
        from seguridad.funciones_cron import ejecutar_cron
        ejecutar_cron('purgar_historicos', lambda: self._purgar(opts), log=self.stdout.write)

    def _purgar(self, opts):
        from seguridad.models import CronLogEjecucion

        dias = opts['dias'] or 90
        seco = opts['dry_run']
        corte = timezone.now() - timedelta(days=dias)
        total = 0

        tareas = (
            ('Logs de cron', CronLogEjecucion.objects.filter(fecha__lt=corte.date())),
        )
        for nombre, queryset in tareas:
            if seco:
                cuantos = queryset.count()
            else:
                # Se borra de a tandas: un DELETE de cientos de miles de filas bloquea la tabla
                # y se come la memoria del proceso al materializar los objetos para las señales.
                cuantos = 0
                while True:
                    ids = list(queryset.values_list('pk', flat=True)[:5000])
                    if not ids:
                        break
                    borrados, _ = queryset.model.objects.filter(pk__in=ids).delete()
                    cuantos += borrados
            total += cuantos
            self.stdout.write(f'{nombre}: {cuantos} anteriores a {dias} días.')

        sesiones = self._purgar_sesiones(seco)
        self.stdout.write(f'Sesiones vencidas: {sesiones}.')

        etiqueta = 'Se borrarían' if seco else 'Borrados'
        self.stdout.write(self.style.SUCCESS(f'{etiqueta} {total + sesiones} registros.'))

    def _purgar_sesiones(self, seco):
        from django.contrib.sessions.models import Session
        vencidas = Session.objects.filter(expire_date__lt=timezone.now())
        if seco:
            return vencidas.count()
        borradas, _ = vencidas.delete()
        return borradas
