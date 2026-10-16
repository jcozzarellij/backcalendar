"""Portal principal «Exducere Online» con sus productos de ejemplo (docs/productos_para_publico).

Idempotente: busca por slug y actualiza nombres, descripciones y sitio; no toca los tiempos ni el
estado `activo` que se hayan cambiado desde el panel.

Uso:  python scripts/seed_portal_ejemplo.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backcalendar.settings')

import django

django.setup()

from django.db import transaction

from agenda.models import Equipo, MiembroEquipo, Portal, Producto, Proyecto
from autenticacion.models import Usuario

PORTAL = {
    'slug': 'exducere',
    'nombre': 'Exducere Online',
    'color_principal': '#005082',
    'sitios_autorizados': 'https://kawana.app\nhttps://moodle-assistant-demo.exducereonline.com\nhttps://exducereonline.com',
}

PRODUCTOS = [
    {
        'slug': 'kawana', 'orden': 10, 'sitio_web': 'https://kawana.app',
        'nombre': 'Kawana Proctoring', 'nombre_en': 'Kawana Proctoring', 'nombre_pt': 'Kawana Proctoring',
        'descripcion': 'Supervisión de exámenes en línea.',
        'descripcion_en': 'Online exam proctoring.',
        'descripcion_pt': 'Supervisão de provas on-line.',
        'subproductos': [],
    },
    {
        'slug': 'moodle-ia', 'orden': 20, 'sitio_web': 'https://moodle-assistant-demo.exducereonline.com',
        'nombre': 'Moodle con IA', 'nombre_en': 'Moodle with AI', 'nombre_pt': 'Moodle com IA',
        'descripcion': 'Su aula Moodle con un asistente de inteligencia artificial.',
        'descripcion_en': 'Your Moodle classroom with an AI assistant.',
        'descripcion_pt': 'Sua sala Moodle com um assistente de inteligência artificial.',
        'subproductos': [],
    },
    {
        'slug': 'moodle', 'orden': 30, 'sitio_web': 'https://exducereonline.com',
        'nombre': 'Moodle', 'nombre_en': 'Moodle', 'nombre_pt': 'Moodle',
        'descripcion': 'Plataforma de aulas virtuales, en la web y en el teléfono.',
        'descripcion_en': 'Virtual classroom platform, on the web and on the phone.',
        'descripcion_pt': 'Plataforma de salas virtuais, na web e no celular.',
        'subproductos': [
            {'slug': 'web', 'orden': 10, 'nombre': 'Plataforma web', 'nombre_en': 'Web platform',
             'nombre_pt': 'Plataforma web', 'descripcion': 'Moodle desde el navegador.',
             'descripcion_en': 'Moodle in the browser.', 'descripcion_pt': 'Moodle no navegador.'},
            {'slug': 'movil', 'orden': 20, 'nombre': 'Aplicación móvil', 'nombre_en': 'Mobile app',
             'nombre_pt': 'Aplicativo móvel', 'descripcion': 'Moodle en el teléfono.',
             'descripcion_en': 'Moodle on the phone.', 'descripcion_pt': 'Moodle no celular.'},
        ],
    },
    {
        'slug': 'servidores', 'orden': 40, 'sitio_web': 'https://exducereonline.com',
        'nombre': 'Servidores', 'nombre_en': 'Servers', 'nombre_pt': 'Servidores',
        'descripcion': 'Alojamiento y administración de servidores para su plataforma.',
        'descripcion_en': 'Hosting and server management for your platform.',
        'descripcion_pt': 'Hospedagem e administração de servidores para sua plataforma.',
        'subproductos': [],
    },
]

TEXTOS = ('nombre', 'nombre_en', 'nombre_pt', 'descripcion', 'descripcion_en', 'descripcion_pt', 'orden')


def guardar_producto(portal, padre, datos):
    producto = Producto.objects.filter(status=True, portal=portal, padre=padre, slug=datos['slug']).first()
    nuevo = producto is None
    if nuevo:
        producto = Producto(portal=portal, padre=padre, slug=datos['slug'])
    for campo in TEXTOS + ('sitio_web',):
        if campo in datos:
            setattr(producto, campo, datos[campo])
    producto.save()
    print(f"  {'+' if nuevo else '~'} {producto}")
    return producto


def equipo_para(producto, lider):
    """Un proyecto y un equipo por producto raíz; el superusuario entra como responsable para que
    el flujo funcione desde el primer día. Los subproductos heredan el equipo del padre."""
    proyecto = Proyecto.objects.filter(status=True, codigo=producto.slug).first()
    if proyecto is None:
        proyecto = Proyecto(codigo=producto.slug, nombre=producto.nombre, lider=lider)
        proyecto.save()
    equipo = Equipo.objects.filter(status=True, proyecto=proyecto).order_by('id').first()
    if equipo is None:
        equipo = Equipo(proyecto=proyecto, nombre=f'Equipo {producto.nombre}', lider=lider)
        equipo.save()
    if lider and not MiembroEquipo.objects.filter(status=True, equipo=equipo, usuario=lider).exists():
        MiembroEquipo(equipo=equipo, usuario=lider, rol='responsable').save()
    if producto.equipo_id != equipo.pk:
        producto.equipo = equipo
        producto.save()
    print(f'  = {producto} -> {equipo}')
    return equipo


def run():
    with transaction.atomic():
        lider = Usuario.objects.filter(is_superuser=True, is_active=True).order_by('id').first()
        portal = Portal.objects.filter(status=True, slug=PORTAL['slug']).first()
        if portal is None:
            portal = Portal(slug=PORTAL['slug'], principal=True)
        portal.nombre = PORTAL['nombre']
        portal.sitios_autorizados = PORTAL['sitios_autorizados']
        if not portal.pk:
            portal.color_principal = PORTAL['color_principal']
        portal.save()
        Portal.objects.filter(status=True, principal=True).exclude(pk=portal.pk).update(principal=False)
        print(f'Portal: {portal}')
        for datos in PRODUCTOS:
            producto = guardar_producto(portal, None, datos)
            equipo = equipo_para(producto, lider)
            for sub in datos['subproductos']:
                hijo = guardar_producto(portal, producto, dict(sub, sitio_web=datos['sitio_web']))
                if hijo.equipo_id != equipo.pk:
                    hijo.equipo = equipo
                    hijo.save()
    print('Listo.')


if __name__ == '__main__':
    run()
