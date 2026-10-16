
from backcalendar import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from core.funciones import addData, secure_module, paginador
from django.contrib.auth.models import Group
from django.db.models import Prefetch, Q
from django.utils.timezone import activate

activate(settings.TIME_ZONE)
from seguridad.models import AudiUsuarioTabla
from django.contrib.admin.models import LogEntry


@login_required
@secure_module
def auditoria(request):
    data = {
        'modulo': 'Seguridad',
        'titulo': 'ACTIVIDAD DE USUARIOS',
        'titulo1': 'Listado de actividades de usuarios',
        'titulo2': 'Auditoria',
        'ruta': '/seguridad/auditoria/',
        'user': request.user.username,
    }
    model = AudiUsuarioTabla

    addData(request, data)

    criterio, filtros, desde, hasta, url_vars = request.GET.get('criterio', '').strip(), Q(id__gt=0), request.GET.get(
        'desde', ''), request.GET.get('hasta', ''), ''
    if criterio:
        filtros = filtros & (Q(user__username__icontains=criterio) | Q(change_message__icontains=criterio))
        data["criterio"] = criterio
        url_vars += '&criterio=' + criterio
    if desde and hasta:
        # __date: `hasta` sin hora se interpretaba como 00:00 y excluía TODO el día final
        # (buscar «hoy a hoy» daba 0 resultados aunque hubiera actividad).
        filtros = filtros & (Q(action_time__date__gte=desde) & Q(action_time__date__lte=hasta))
        data["desde"] = desde
        data['hasta'] = hasta
        url_vars += '&desde=' + desde + '&hasta=' + hasta
    #auditoria = AudiUsuarioTabla.objects.filter(filtros)
    # El listado muestra el usuario y su grupo en cada fila: sin select_related/prefetch cada fila
    # disparaba dos consultas más (el usuario y sus grupos).
    auditoria = LogEntry.objects.filter(filtros).select_related('user').prefetch_related(
        Prefetch('user__groups', queryset=Group.objects.order_by('id')))
    data["url_vars"] = url_vars
    paginador(request, auditoria, 15, data)
    return render(request, 'seguridad/auditoria/auditoria.html', data)
