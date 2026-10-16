from datetime import date


def menu_agenda(request):
    """Menú y contadores del micrositio de la agenda. Solo calcula en rutas `/agenda/` con sesión."""
    if not request.path.startswith('/agenda/') or not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}
    from seguridad.models import GroupModulo, Modulo, Notificacion
    from .models import Solicitud
    items = [
        ('/agenda/mi-dia/', 'Mi día', 'fa-sun'),
        ('/agenda/buscar/', 'Buscar', 'fa-search'),
        ('/agenda/mi-agenda/', 'Calendario', 'fa-calendar'),
        ('/agenda/mis-turnos/', 'Horarios', 'fa-clock'),
        ('/agenda/citas/', 'Citas', 'fa-video'),
        ('/agenda/agenda-equipo/', 'Agenda del equipo', 'fa-users'),
        ('/agenda/cola/', 'Cola de solicitudes', 'fa-inbox'),
        ('/agenda/solicitudes/', 'Solicitudes', 'fa-columns'),
        ('/agenda/portales/', 'Portales de reserva', 'fa-globe'),
        ('/agenda/clientes/', 'Clientes', 'fa-id-card'),
        ('/agenda/alertas/', 'Alertas', 'fa-bell'),
        ('/agenda/aplicaciones/', 'Conexiones', 'fa-plug'),
        ('/agenda/turnos-equipo/', 'Horarios del equipo', 'fa-user-clock'),
        ('/agenda/equipos/', 'Equipos', 'fa-people-group'),
        ('/agenda/proyectos/', 'Proyectos', 'fa-folder'),
        ('/agenda/feriados/', 'Feriados', 'fa-umbrella-beach'),
        ('/agenda/parametros/', 'Configuración', 'fa-sliders'),
    ]
    try:
        en_cola = Solicitud.objects.filter(status=True, estado='en_cola').count()
    except Exception:
        en_cola = 0
    try:
        alertas = Notificacion.objects.filter(status=True, destinatario=request.user, leido=False).count()
    except Exception:
        alertas = 0
    contadores = {'/agenda/cola/': en_cola, '/agenda/alertas/': alertas}
    if request.user.is_superuser:
        urls = {u for u, _, _ in items}
    else:
        try:
            ids = GroupModulo.objects.filter(status=True, group__in=request.user.groups.all()).values_list('modulos', flat=True)
            urls = set(Modulo.objects.filter(status=True, id__in=ids).values_list('url', flat=True))
        except Exception:
            urls = set()
    return {
        'menu_agenda': [{'url': u, 'nombre': n, 'icono': i, 'contador': contadores.get(u, 0)} for u, n, i in items],
        'urls_agenda': urls,
        'hoy_agenda': date.today(),
    }
