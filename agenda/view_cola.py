from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from core.funciones import addData, secure_module
from .forms import CitaRapidaForm
from .funciones_asignacion import es_por_persona, espacios_equipo_rango
from .funciones_citas import responsables_de
from .funciones_permisos import equipos_visibles, es_admin_proyectos
from .funciones_portal import tiempos_de
from .models import Solicitud


@login_required
@secure_module
def colaView(request):
    data = {
        'titulo': 'Cola de solicitudes',
        'descripcion': 'Solicitudes que no encontraron un espacio común dentro de su ventana. Elige un espacio, a quién se asigna y en qué plataforma; el sistema crea la cita con su videollamada y envía la invitación.',
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
                minimo = datetime.now()
                por_dia = espacios_equipo_rango(equipo, minimo.date(), minimo.date() + timedelta(days=13), duracion,
                                                t['margen'] if t else 0, desde_hora=minimo)
                sugeridos = [h for _, horas in sorted(por_dia.items()) for h in horas][:6]
            actual.ventana_hasta = actual.fecha_registro + timedelta(hours=48)
        data.update({
            'cola': cola, 'actual': actual, 'equipo': equipo, 'sugeridos': sugeridos, 'duracion': duracion or 40,
            'equipos': visibles.select_related('proyecto'),
            'responsables': responsables_de(equipo) if equipo else [],
            'por_persona': es_por_persona(equipo),
            'plataformas': CitaRapidaForm()['plataforma'],
        })
        return render(request, 'agenda/cola/listado.html', data)
    return render(request, 'agenda/cola/listado.html', data)
