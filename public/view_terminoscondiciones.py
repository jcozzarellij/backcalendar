from datetime import datetime

from django.shortcuts import render

from agenda import funciones_portal
from core.funciones import addData

SECCIONES_TERMINOS = (('acceso', 'lg_t1', False), ('uso', 'lg_t2', False), ('cambios', 'lg_t3', False),
                      ('contacto', 'lg_t4', True))
SECCIONES_DATOS = (('datos', 'lg_d1', False), ('uso', 'lg_d2', False), ('seguridad', 'lg_d3', False),
                   ('derechos', 'lg_d4', True))


def terminosycondiciones(request):
    t = funciones_portal.textos(funciones_portal.idioma_de(request))
    data = {
        'titulo': t['lg_titulo_terminos'],
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)
    t = funciones_portal.contexto_publico(request, data, funciones_portal.portal_principal())
    confi = data['confi']

    if request.method == 'POST':
        pass
    elif request.method == 'GET':
        if 'action' in request.GET:
            data["action"] = action = request.GET['action']
    data.update({
        'bajada': t['lg_bajada_terminos'],
        'documento': 'terminos',
        'texto_propio': confi.terminosycondiciones or '',
        'actualizado': confi.fecha_modificacion if confi.terminosycondiciones else None,
        'secciones': _secciones(t, SECCIONES_TERMINOS),
        'correo_legal': confi.email_notificacion or confi.email or '',
    })
    return render(request, 'public/legal.html', data)


def proteccion_datos(request):
    """Cómo se tratan los datos personales en la plataforma (LOPDP Ecuador), separado de los términos de uso."""
    t = funciones_portal.textos(funciones_portal.idioma_de(request))
    data = {
        'titulo': t['lg_titulo_datos'],
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)
    t = funciones_portal.contexto_publico(request, data, funciones_portal.portal_principal())
    confi = data['confi']

    if request.method == 'POST':
        pass
    elif request.method == 'GET':
        if 'action' in request.GET:
            data["action"] = action = request.GET['action']
    data.update({
        'bajada': t['lg_bajada_datos'],
        'documento': 'datos',
        'secciones': _secciones(t, SECCIONES_DATOS),
        'correo_legal': confi.email_notificacion or confi.email or '',
    })
    return render(request, 'public/legal.html', data)


def _secciones(t, definicion):
    return [{'id': ancla, 'titulo': t[f'{clave}_titulo'], 'texto': t[clave], 'con_correo': con_correo}
            for ancla, clave, con_correo in definicion]
