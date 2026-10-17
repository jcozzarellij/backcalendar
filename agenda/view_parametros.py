import sys
from datetime import date
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render

from core.funciones import addData, log, secure_module
from core.funciones_adicionales import salva_logs
from seguridad.models import PARAMETRO_GRUPO_CHOICES, ParametroSistema
from . import funciones_google
from .funciones_permisos import es_administrador
from .models import ConexionAplicacion

GRUPOS_AGENDA = ('tiempos', 'portal', 'cliente', 'recordatorios')


@login_required
@secure_module
def parametrosAgendaView(request):
    data = {
        'titulo': 'Configuración',
        'descripcion': 'Parámetros globales de la agenda. Solo el líder general puede cambiarlos y cada cambio queda registrado.',
        'modulo': 'Agenda',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)
    model = ParametroSistema
    puede_editar = es_administrador(request.user)
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if not puede_editar:
                    raise ValueError('Solo el líder general cambia la configuración.')
                if action == 'guardar':
                    cambios = []
                    for fila in model.objects.select_for_update().filter(status=True, editable=True, grupo__in=GRUPOS_AGENDA):
                        if f'valor_{fila.pk}' not in request.POST:
                            continue
                        nuevo = request.POST.get(f'valor_{fila.pk}', '').strip()
                        if fila.tipo == 'booleano':
                            nuevo = '1' if request.POST.get(f'valor_{fila.pk}') in ('1', 'on', 'true') else '0'
                        elif fila.tipo == 'entero':
                            if not nuevo.lstrip('-').isdigit():
                                raise ValueError(f'«{fila.etiqueta}» debe ser un número entero.')
                            if int(nuevo) < 0:
                                raise ValueError(f'«{fila.etiqueta}» no puede ser negativo.')
                        elif fila.tipo == 'decimal':
                            try:
                                Decimal(nuevo)
                            except InvalidOperation:
                                raise ValueError(f'«{fila.etiqueta}» debe ser un número.')
                        if fila.clave == 'recordatorio_horas_antes':
                            partes = [p.strip() for p in nuevo.split(',') if p.strip()]
                            if not all(p.isdigit() for p in partes):
                                raise ValueError('«Avisos al cliente antes de la cita» son horas separadas por coma, por ejemplo 24,1.')
                            nuevo = ','.join(partes)
                        if (fila.valor or '') != nuevo:
                            anterior = fila.valor
                            fila.valor = nuevo
                            fila.save(request)
                            cache.delete(model._cache_key(fila.clave))
                            cambios.append(f'{fila.etiqueta}: {anterior} → {nuevo}')
                    if cambios:
                        for cambio in cambios:
                            log(f'Configuración de la agenda · {cambio}', request, 'change')
                        messages.success(request, f'{len(cambios)} parámetro{"s" if len(cambios) != 1 else ""} actualizado{"s" if len(cambios) != 1 else ""}.')
                    else:
                        messages.success(request, 'No había cambios que guardar.')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'restaurar':
                    fila = model.objects.get(pk=int(request.POST['id']), status=True, grupo__in=GRUPOS_AGENDA)
                    anterior = fila.valor
                    fila.valor = fila.valor_default
                    fila.save(request)
                    cache.delete(model._cache_key(fila.clave))
                    log(f'Configuración de la agenda · {fila.etiqueta}: {anterior} → {fila.valor_default} (por defecto)', request, 'change', obj=fila.id)
                    messages.success(request, f'«{fila.etiqueta}» volvió a {fila.valor_default} {fila.unidad or ""}.')
                    res_json = {'error': False}
                else:
                    raise ValueError('Acción no permitida.')
        except ValueError as ex:
            res_json = [{'error': True, 'message': str(ex)}]
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json = [{'error': True, 'message': 'Intente nuevamente.'}]
        return JsonResponse(res_json, safe=False)
    elif request.method == 'GET':
        nombres = dict(PARAMETRO_GRUPO_CHOICES)
        grupos = []
        for clave in GRUPOS_AGENDA:
            filas = list(model.objects.filter(status=True, grupo=clave).order_by('orden', 'etiqueta'))
            if filas:
                grupos.append({'clave': clave, 'nombre': nombres.get(clave, clave).replace('Agenda: ', '').capitalize(),
                               'parametros': filas})
        conexiones = ConexionAplicacion.objects.filter(status=True, proveedor='google')
        data.update({
            'grupos_parametros': grupos,
            'puede_editar': puede_editar,
            'google_configurado': funciones_google.configurada(),
            'google_conectadas': conexiones.filter(conectada=True).count(),
            'google_total': conexiones.count(),
            'google_redirect': getattr(settings, 'GOOGLE_OAUTH_REDIRECT_URI', ''),
            'zona_horaria': settings.TIME_ZONE,
            'remitente': getattr(settings, 'DEFAULT_FROM_EMAIL', '') or getattr(settings, 'EMAIL_HOST_USER', ''),
            'push_configurado': bool(getattr(settings, 'WEBPUSH_SETTINGS', {}).get('VAPID_PUBLIC_KEY', '')),
            'historial': LogEntry.objects.filter(change_message__startswith='Configuración de la agenda').select_related('user').order_by('-action_time')[:12],
        })
        return render(request, 'agenda/parametros/listado.html', data)
