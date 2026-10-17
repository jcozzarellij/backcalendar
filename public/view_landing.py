from datetime import datetime

from django.shortcuts import render

from agenda import funciones_portal
from core.funciones import addData


def landing(request):
    t = funciones_portal.textos(funciones_portal.idioma_de(request))
    data = {
        'titulo': t['ld_hero_titulo'],
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)
    portal = funciones_portal.portal_principal()
    t = funciones_portal.contexto_publico(request, data, portal)

    if request.method == 'POST':
        pass
    elif request.method == 'GET':
        if 'action' in request.GET:
            data["action"] = action = request.GET['action']
    data['portal'] = portal
    data['productos'], data['total_productos'] = funciones_portal.productos_destacados(portal, data['idioma'], t)
    return render(request, 'public/landing.html', data)


def catalogo(request):
    t = funciones_portal.textos(funciones_portal.idioma_de(request))
    data = {
        'titulo': t['ct_titulo'],
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)
    portal = funciones_portal.portal_principal()
    t = funciones_portal.contexto_publico(request, data, portal)

    if request.method == 'POST':
        pass
    elif request.method == 'GET':
        if 'action' in request.GET:
            data["action"] = action = request.GET['action']
    data['portal'] = portal
    data['productos'] = funciones_portal.productos_publicos(portal, data['idioma'], t)
    return render(request, 'public/catalogo.html', data)
