from datetime import datetime

from django.shortcuts import render

from agenda import funciones_portal
from agenda.models import Portal
from core.funciones import addData


def landing(request):
    data = _contexto_publico(request, 'ld_titulo')
    data['productos'], data['total_productos'] = funciones_portal.productos_destacados(data['portal'], data['idioma'], data['t'])
    return render(request, 'public/landing.html', data)


def catalogo(request):
    data = _contexto_publico(request, 'ct_titulo')
    data['productos'] = funciones_portal.productos_publicos(data['portal'], data['idioma'], data['t'])
    return render(request, 'public/catalogo.html', data)


def _contexto_publico(request, clave_titulo):
    """Idioma, textos, portal principal y contacto (teléfono del portal, si no el de la empresa; correo de la empresa)."""
    idioma = funciones_portal.idioma_de(request)
    textos = funciones_portal.textos(idioma)
    data = {'titulo': textos[clave_titulo], 'ruta': request.path, 'fecha': datetime.now()}
    addData(request, data)
    portal = Portal.objects.filter(status=True, activo=True, principal=True).first()
    data.update({
        'idioma': idioma,
        't': textos,
        'portal': portal,
        'contacto_telefono': (portal.telefono_atencion if portal else '') or data['telefonoempresa'],
        'contacto_correo': data['confi'].email or '',
    })
    return data
