from datetime import datetime

from django.shortcuts import render

from agenda import funciones_portal
from core.funciones import addData


def landing(request):
    data = _contexto_publico(request, 'ld_hero_titulo')
    data['productos'], data['total_productos'] = funciones_portal.productos_destacados(data['portal'], data['idioma'], data['t'])
    return render(request, 'public/landing.html', data)


def catalogo(request):
    data = _contexto_publico(request, 'ct_titulo')
    data['productos'] = funciones_portal.productos_publicos(data['portal'], data['idioma'], data['t'])
    return render(request, 'public/catalogo.html', data)


def _contexto_publico(request, clave_titulo):
    """Datos comunes de landing y catálogo: los de `funciones_portal.contexto_publico` con el portal principal."""
    data = {'ruta': request.path, 'fecha': datetime.now()}
    addData(request, data)
    portal = funciones_portal.portal_principal()
    t = funciones_portal.contexto_publico(request, data, portal)
    data.update({'titulo': t[clave_titulo], 'portal': portal})
    return data
