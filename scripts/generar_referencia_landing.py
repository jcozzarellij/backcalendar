"""Genera `static/referencias/landing_base.html`: el landing renderizado como HTML plano, sin etiquetas de Django,
con productos y contacto de ejemplo. Es la referencia visual de la línea de diseño del landing.

Idempotente: sobrescribe el archivo. No toca la base de datos.

Uso:  python scripts/generar_referencia_landing.py
"""
import os
import re
import sys
from datetime import date
from types import SimpleNamespace
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backcalendar.settings')

import django

django.setup()

from django.template.loader import render_to_string

from agenda.funciones_portal import con_marca, textos

ATENCION = '40 ' + textos('es')['minutos_video']

PRODUCTOS = [
    {'nombre': 'Qwana', 'descripcion': 'Conozca Qwana y resuelva sus dudas con el equipo.', 'slug': 'qwana',
     'sitio_web': 'https://kawana.app', 'atencion': ATENCION, 'partes': []},
    {'nombre': 'MoAI · Moodle con IA', 'descripcion': 'Vea cómo la inteligencia artificial ayuda en sus cursos de Moodle.',
     'slug': 'moai', 'sitio_web': 'https://moodle-assistant-demo.exducereonline.com', 'atencion': ATENCION, 'partes': []},
    {'nombre': 'Moodle', 'descripcion': 'Elija sobre qué parte de Moodle quiere conversar.', 'slug': 'moodle',
     'sitio_web': '', 'atencion': ATENCION, 'partes': [
        {'nombre': 'Plataforma web', 'descripcion': 'El sitio de Moodle que se usa en el computador.', 'slug': 'moodle-web',
         'atencion': ATENCION},
        {'nombre': 'Aplicación móvil', 'descripcion': 'La aplicación de Moodle para el teléfono.', 'slug': 'moodle-movil',
         'atencion': ATENCION},
    ]},
    {'nombre': 'Servidores', 'descripcion': 'Hospedaje y mantenimiento de su plataforma educativa.', 'slug': 'servidores',
     'sitio_web': 'https://exducereonline.com', 'atencion': ATENCION, 'partes': []},
]


def generar():
    t = con_marca(textos('es'), 'Exducere Online', 'Turno')
    html = render_to_string('public/landing.html', {
        'productos': PRODUCTOS,
        'total_productos': 9,
        'confi': SimpleNamespace(web='https://exducereonline.com', titulo='Turno de Exducere Online', descripcion='Agenda de citas del equipo de Exducere Online.', logo_sistema_white=None),
        't': t,
        'idioma': 'es',
        'contacto_telefono': '099 000 0000',
        'contacto_correo': '',
        'titulo': t['ld_hero_titulo'],
        'fecha': date.today(),
        'ruta': '/',
        'logo': '/static/images/turno/logo_turno_color.png',
        'nombreempresa': 'Turno de Exducere Online',
        'fecha_actual': date.today(),
    })
    html = re.sub(r'\n\s*\n+', '\n', html)
    destino = RAIZ / 'static' / 'referencias' / 'landing_base.html'
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding='utf-8')
    print(f'Referencia generada: {destino.relative_to(RAIZ)}')


if __name__ == '__main__':
    generar()
