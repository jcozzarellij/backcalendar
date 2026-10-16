from datetime import datetime
from django.shortcuts import render
from core.funciones import addData


def terminosycondiciones(request):
    data = {
        'titulo': 'Terminos y Condiciones',
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)

    if request.method == 'POST':
        pass
    elif request.method == 'GET':
        if 'action' in request.GET:
            data["action"] = action = request.GET['action']
    return render(request, 'public/terminosycondiciones.html', data)


def proteccion_datos(request):
    """Hoja explicativa de la Ley de Protección de Datos (LOPDP Ecuador) y cómo se aplica —
    separada de la página de privacidad/términos (que cubre el detalle operativo del servicio)."""
    data = {
        'titulo': 'Ley de Protección de Datos',
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)
    return render(request, 'public/proteccion_datos.html', data)
