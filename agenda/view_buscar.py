from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from core.funciones import addData, secure_module
from .funciones_busqueda import buscar


@login_required
@secure_module
def buscarView(request):
    data = {
        'titulo': 'Buscar',
        'descripcion': 'Clientes, citas y solicitudes por nombre, correo, teléfono o código.',
        'modulo': 'Agenda',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)
    if request.method == 'GET':
        texto = request.GET.get('q', '')
        resultado = buscar(texto, request.user)
        if request.GET.get('action') == 'rapida':
            return JsonResponse({'result': True, 'texto': resultado['texto'], 'total': resultado['total'], 'data': {
                'clientes': [{'texto': c.nombres, 'sub': c.correo, 'url': f'/agenda/clientes/{c.pk}/'} for c in resultado['clientes'][:5]],
                'citas': [{'texto': f'{c.codigo} · {c.titulo}', 'sub': f'{c.inicio:%d/%m/%Y %H:%M} · {c.get_estado_display()}', 'url': f'/agenda/citas/{c.pk}/'} for c in resultado['citas'][:5]],
                'solicitudes': [{'texto': f'{s.codigo} · {s.cliente.nombres}', 'sub': s.get_estado_display(), 'url': f'/agenda/solicitudes/?criterio={s.codigo}&estado='} for s in resultado['solicitudes'][:5]],
            }})
        data.update(resultado)
        return render(request, 'agenda/buscar/listado.html', data)
    return JsonResponse({'error': True, 'message': 'Acción no permitida.'})
