"""Parámetros globales de la agenda en `seguridad.ParametroSistema` (grupos tiempos, portal,
cliente y recordatorios). Valores iniciales del estudio del micrositio (docs/plan_micrositio_agendas.md).

Idempotente: crea la clave si falta y refresca etiqueta, descripción, unidad y valor por defecto;
nunca pisa el `valor` que el administrador haya cambiado desde el panel.

Uso:  python scripts/seed_parametros_agenda.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backcalendar.settings')

import django

django.setup()

from django.db import transaction

from seguridad.models import ParametroSistema

PARAMETROS = [
    ('agenda_duracion_turno', 'Duración del turno', 'tiempos', 'entero', '40', 'min',
     'Largo de cada espacio de la agenda y valor por defecto de cada cita.', 10),
    ('agenda_antelacion_horas', 'Antelación mínima', 'tiempos', 'entero', '24', 'horas',
     'Horas entre el momento en que el cliente entra al portal y el primer espacio que se le ofrece.', 20),
    ('agenda_ventana_dias', 'Ventana de reserva', 'tiempos', 'entero', '14', 'días',
     'Hasta cuántos días adelante se puede agendar. Cada producto puede ampliarla.', 30),
    ('agenda_margen_min', 'Margen entre citas', 'tiempos', 'entero', '0', 'min',
     'Minutos libres antes y después de cada cita. Ajustable por producto.', 40),
    ('agenda_limite_dia', 'Máximo de citas por persona y día', 'tiempos', 'entero', '0', 'citas',
     '0 = sin límite. Ajustable por producto.', 50),
    ('agenda_aviso_previo_min', 'Aviso previo a la cita', 'tiempos', 'entero', '15', 'min',
     'Minutos antes en que aparece la alerta; cada persona puede ajustarlo.', 60),
    ('agenda_cache_disponibilidad_seg', 'Vigencia de la caché de disponibilidad', 'tiempos', 'entero', '180', 'segundos',
     'Cuánto se reutiliza la consulta de libre/ocupado de Google antes de volver a pedirla.', 70),
    ('portal_reserva_temporal_min', 'Reserva temporal del horario', 'portal', 'entero', '10', 'min',
     'Minutos que se aparta un horario mientras el cliente llena sus datos.', 10),
    ('portal_fechas_destacadas', 'Fechas próximas destacadas', 'portal', 'entero', '3', 'fechas',
     'Cuántas fechas próximas se muestran como tarjetas grandes antes del calendario.', 20),
    ('portal_solicitudes_por_ip', 'Solicitudes permitidas por IP', 'portal', 'entero', '20', 'por hora',
     'Tope de reservas desde una misma dirección en una hora, contra abuso.', 30),
    ('cliente_vigencia_enlace_meses', 'Vigencia del enlace personal', 'cliente', 'entero', '12', 'meses',
     'Cuánto dura el enlace «Mis citas» del cliente; se renueva con cada uso.', 10),
    ('cliente_reservas_activas', 'Reservas activas por cliente', 'cliente', 'entero', '2', 'citas',
     'Cuántas citas futuras puede tener un cliente a la vez.', 20),
    ('cliente_conservar_ip_dias', 'Conservación de la IP completa', 'cliente', 'entero', '90', 'días',
     'Pasado este plazo solo se guarda ciudad y país aproximados.', 30),
    ('recordatorio_horas_antes', 'Avisos al cliente antes de la cita', 'recordatorios', 'texto', '24,1', 'horas',
     'Horas antes de la cita en que se envía cada recordatorio, separadas por coma.', 10),
]


def run():
    creados = actualizados = 0
    with transaction.atomic():
        for orden_grupo, (clave, etiqueta, grupo, tipo, valor, unidad, descripcion, orden) in enumerate(PARAMETROS):
            fila, creado = ParametroSistema.objects.get_or_create(
                clave=clave,
                defaults={'etiqueta': etiqueta, 'grupo': grupo, 'tipo': tipo, 'valor': valor, 'valor_default': valor,
                          'unidad': unidad, 'descripcion': descripcion, 'orden': orden, 'status': True},
            )
            if creado:
                creados += 1
            else:
                fila.etiqueta, fila.grupo, fila.tipo = etiqueta, grupo, tipo
                fila.valor_default, fila.unidad, fila.descripcion, fila.orden = valor, unidad, descripcion, orden
                fila.status = True
                fila.save()
                actualizados += 1
            print(f"  {'+' if creado else '~'} {clave} = {fila.valor} {unidad}")
    print(f'Listo: {creados} creados, {actualizados} actualizados.')


if __name__ == '__main__':
    run()
