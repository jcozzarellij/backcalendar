"""Carga los feriados nacionales de Ecuador en `agenda.Feriado` (alcance: todos).

Fuente de fechas y nombres: API pública Nager.Date (https://date.nager.at), país EC. La API
devuelve la fecha original del feriado; este script aplica el traslado del Código del Trabajo
(reforma de 2016):
- cae martes -> lunes anterior; miércoles o jueves -> viernes de esa semana;
- cae sábado -> viernes anterior; domingo -> lunes siguiente;
- no se trasladan: 1 de enero, 25 de diciembre ni el carnaval.
Día de Difuntos (2 nov) e Independencia de Cuenca (3 nov) se tratan como bloque: si los dos caen
entre lunes y viernes se quedan; si no, se aplica la regla a cada uno. Si un traslado cae sobre
otro feriado, se deja la fecha original.

El Gobierno puede decretar otros traslados para un año puntual: revisar el decreto del año y
corregir a mano desde /agenda/feriados/.

Idempotente: no duplica (fecha + nombre, alcance todos).

Uso:  python scripts/seed_feriados_ecuador.py [--desde 2026] [--hasta 2030]
"""
import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backcalendar.settings')

import django

django.setup()

import requests
from django.db import transaction

from agenda.models import Feriado

API = 'https://date.nager.at/api/v3/PublicHolidays/{anio}/EC'
NOMBRES = {
    'Año Nuevo': 'Año Nuevo',
    'Carnaval': 'Carnaval',
    'Good Friday': 'Viernes Santo',
    "International Workers' Day": 'Día del Trabajo',
    'Batalla de Pichincha': 'Batalla de Pichincha',
    'Primer Grito de Independencia': 'Primer Grito de Independencia',
    'Independencia de Guayaquil': 'Independencia de Guayaquil',
    'Día de los Difuntos, Día de Muertos': 'Día de Difuntos',
    'Independencia de Cuenca': 'Independencia de Cuenca',
    'Día de Navidad': 'Navidad',
}


def trasladar(fecha):
    dia = fecha.weekday()
    if dia == 1:
        return fecha - timedelta(days=1)
    if dia in (2, 3):
        return fecha + timedelta(days=4 - dia)
    if dia == 5:
        return fecha - timedelta(days=1)
    if dia == 6:
        return fecha + timedelta(days=1)
    return fecha


def feriados_del_anio(anio):
    respuesta = requests.get(API.format(anio=anio), timeout=20)
    respuesta.raise_for_status()
    crudos = [(date.fromisoformat(f['date']), NOMBRES.get(f['localName'], f['localName'])) for f in respuesta.json()]
    noviembre = {f.day: f for f, _ in crudos if f.month == 11 and f.day in (2, 3)}
    bloque_quieto = len(noviembre) == 2 and all(f.weekday() < 5 for f in noviembre.values())
    originales = {f for f, _ in crudos}
    resultado = []
    for fecha, nombre in crudos:
        fijo = (fecha.month, fecha.day) in ((1, 1), (12, 25)) or nombre in ('Carnaval', 'Viernes Santo')
        if fecha.month == 11 and fecha.day in (2, 3) and bloque_quieto:
            fijo = True
        final = fecha if fijo else trasladar(fecha)
        if final != fecha and (final in originales or final in {r for r, _ in resultado}):
            final = fecha
        etiqueta = nombre if final == fecha else f'{nombre} (trasladado del {fecha:%d/%m})'
        resultado.append((final, etiqueta))
    return resultado


def run(desde, hasta):
    creados = existentes = 0
    with transaction.atomic():
        for anio in range(desde, hasta + 1):
            for fecha, nombre in feriados_del_anio(anio):
                if Feriado.objects.filter(status=True, equipo__isnull=True, fecha=fecha, nombre=nombre).exists():
                    existentes += 1
                    continue
                Feriado(fecha=fecha, nombre=nombre).save()
                creados += 1
                print(f'  + {fecha:%a %d/%m/%Y}  {nombre}')
    print(f'Listo: {creados} creados, {existentes} ya estaban.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Carga los feriados nacionales de Ecuador.')
    parser.add_argument('--desde', type=int, default=date.today().year)
    parser.add_argument('--hasta', type=int, default=2030)
    args = parser.parse_args()
    run(args.desde, args.hasta)
