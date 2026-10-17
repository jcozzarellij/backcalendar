from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from core.funciones import addData, secure_module
from .funciones_citas import responsables_de
from .funciones_disponibilidad import espacios_comunes
from .funciones_permisos import equipos_visibles, es_admin_proyectos
from .funciones_portal import tiempos_de
from .models import Solicitud


@login_required
@secure_module
def colaView(request):
    data = {
        'titulo': 'Cola de solicitudes',
        'descripcion': 'Solicitudes que no encontraron un espacio común dentro de su ventana. Elige un espacio y el sistema crea la cita con Meet y envía la invitación.',
        'modulo': 'Agenda',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)
    visibles = equipos_visibles(request.user)
    base = Solicitud.objects.filter(status=True, estado='en_cola')
    if not es_admin_proyectos(request.user):
        base = base.filter(Q(equipo__in=visibles) | Q(equipo__isnull=True))
    if request.method == 'GET':
        cola = list(base.select_related('cliente', 'producto', 'equipo', 'proyecto', 'producto__equipo').order_by('fecha_registro'))
        elegida = request.GET.get('solicitud', '')
        actual = next((s for s in cola if str(s.pk) == elegida), cola[0] if cola else None)
        sugeridos, duracion, equipo = [], None, None
        if actual is not None:
            equipo = actual.equipo or (actual.producto.equipo if actual.producto_id else None)
            if equipo is not None:
                t = tiempos_de(actual.producto) if actual.producto_id else None
                duracion = t['duracion'] if t else None
                responsables = responsables_de(equipo)
                fecha = date.today()
                minimo = datetime.now()
                for _ in range(14):
                    for h in espacios_comunes(responsables, fecha, duracion, t['margen'] if t else 0,
                                              desde_hora=minimo if fecha == minimo.date() else None):
                        sugeridos.append(h)
                        if len(sugeridos) >= 6:
                            break
                    if len(sugeridos) >= 6:
                        break
                    fecha += timedelta(days=1)
            actual.ventana_hasta = actual.fecha_registro + timedelta(hours=48)
        data.update({
            'cola': cola, 'actual': actual, 'equipo': equipo, 'sugeridos': sugeridos, 'duracion': duracion or 40,
            'equipos': visibles.select_related('proyecto'),
            'responsables': responsables_de(equipo) if equipo else [],
        })
        return render(request, 'agenda/cola/listado.html', data)
    return render(request, 'agenda/cola/listado.html', data)
