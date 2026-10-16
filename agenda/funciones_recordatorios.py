"""Recordatorios al cliente antes de la cita (cron `recordatorios_citas`).

`enviar_pendientes(ahora=None)` recorre las citas confirmadas próximas y, por cada hora configurada en
`recordatorio_horas_antes` (ej. «24,1»), manda un correo si todavía no se envió ese aviso. Cada envío
queda en `EnvioRecordatorio` (inmutable), que es también la guarda contra duplicados. Devuelve
(enviados, fallidos).
"""
import logging
from datetime import datetime, timedelta

from django.template.loader import get_template
from django.utils.formats import date_format

from core import correos
from seguridad.models import Configuracion, ParametroSistema
from . import funciones_tokens
from .models import Cita, EnvioRecordatorio

logger = logging.getLogger(__name__)
TOLERANCIA_MIN = 30


def horas_configuradas():
    crudo = ParametroSistema.valor_de('recordatorio_horas_antes', '24,1') or ''
    horas = []
    for parte in str(crudo).split(','):
        parte = parte.strip()
        if parte.isdigit() and int(parte) > 0:
            horas.append(int(parte))
    return sorted(set(horas), reverse=True)


def enviar_pendientes(ahora=None):
    ahora = ahora or datetime.now()
    enviados = fallidos = 0
    horas = horas_configuradas()
    if not horas:
        return 0, 0
    tope = ahora + timedelta(hours=max(horas)) + timedelta(minutes=TOLERANCIA_MIN)
    citas = (Cita.objects.filter(status=True, estado='confirmada', inicio__gt=ahora, inicio__lte=tope)
             .select_related('cliente', 'producto', 'equipo'))
    for cita in citas:
        if not cita.cliente.correo:
            continue
        ya = set(EnvioRecordatorio.objects.filter(cita=cita, exito=True).values_list('tipo', flat=True))
        for h in horas:
            tipo = f'{h}h'
            if tipo in ya:
                continue
            momento = cita.inicio - timedelta(hours=h)
            if momento > ahora:
                continue
            if ahora - momento > timedelta(hours=max(1, h // 2)):
                continue
            try:
                _enviar(cita, h)
                EnvioRecordatorio.objects.create(cita=cita, tipo=tipo, exito=True, detalle=cita.cliente.correo)
                enviados += 1
            except Exception as ex:
                logger.warning('Recordatorio %s de %s falló: %s', tipo, cita.codigo, ex)
                EnvioRecordatorio.objects.create(cita=cita, tipo=tipo, exito=False, detalle=str(ex)[:300])
                fallidos += 1
    return enviados, fallidos


def _enviar(cita, horas):
    confi = Configuracion.get_instancia()
    token = funciones_tokens.emitir('cita', cita=cita)
    contexto = {
        'cita': cita,
        'cliente': cita.cliente,
        'producto': cita.producto,
        'horas': horas,
        'fecha_larga': date_format(cita.inicio, r'l j \d\e F \d\e Y').capitalize(),
        'hora': cita.inicio.strftime('%H:%M'),
        'url_cita': funciones_tokens.url_cita(token),
        'nombreempresa': confi.nombre_empresa or 'Turno',
        'sucursal': confi.nombre_empresa or 'Turno',
    }
    html = get_template('email/cita_recordatorio.html').render(contexto)
    cuando = 'mañana' if horas >= 20 else f'en {horas} hora{"s" if horas != 1 else ""}'
    asunto = f'Recordatorio: su cita es {cuando}, {cita.inicio:%d/%m %H:%M} · {cita.codigo}'
    correos.enviar_ahora(correos.armar(asunto, html, to=[cita.cliente.correo]))
