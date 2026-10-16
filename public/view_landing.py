from datetime import datetime, timedelta

from django.db.models import Prefetch
from django.shortcuts import render

from agenda.models import Portal, Producto
from core.funciones import addData


def landing(request):
    data = {
        'titulo': 'Agende su cita',
        'ruta': request.path,
        'fecha': datetime.now(),
    }
    addData(request, data)
    portal = Portal.objects.filter(status=True, activo=True, principal=True).first()
    productos = []
    if portal:
        subproductos = Producto.objects.filter(status=True, activo=True).order_by('orden', 'nombre')
        productos = list(Producto.objects.filter(status=True, activo=True, portal=portal, padre__isnull=True)
                         .prefetch_related(Prefetch('subproductos', queryset=subproductos, to_attr='subproductos_activos'))
                         .order_by('orden', 'nombre'))
    hoy = datetime.now().date()
    fecha_ejemplo = hoy + timedelta(days=(3 - hoy.weekday()) % 7 or 7)
    ejemplo = next((p for p in productos if p.slug == 'moodle'), productos[0] if productos else None)
    data['portal'] = portal
    data['productos'] = productos
    data['fecha_ejemplo'] = fecha_ejemplo
    data['fechas_ejemplo'] = [hoy + timedelta(days=d) for d in range(1, 8) if (hoy + timedelta(days=d)).weekday() < 5][:3]
    data['producto_ejemplo'] = ejemplo.nombre if ejemplo else 'Exducere Online'
    return render(request, 'public/landing.html', data)
