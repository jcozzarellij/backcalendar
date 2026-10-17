import sys
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from core.funciones import addData, log, secure_module
from core.funciones_adicionales import salva_logs
from . import funciones_google
from .funciones_google import ErrorGoogle
from .models import PROVEEDOR_APLICACION, ConexionAplicacion

RUTA_APLICACIONES = '/agenda/aplicaciones/'


@login_required
@secure_module
def aplicacionesView(request):
    data = {
        'titulo': 'Conexiones',
        'descripcion': 'Conecta tu calendario y tus herramientas de videollamada.',
        'modulo': 'Agenda',
        'ruta': RUTA_APLICACIONES,
        'fecha': str(date.today()),
    }
    addData(request, data)
    model = ConexionAplicacion
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'probar':
                    conexion = model.objects.get(pk=int(request.POST['id']), usuario=request.user, status=True)
                    nombre = funciones_google.probar(conexion)
                    messages.success(request, f'Google responde: calendario «{nombre}».')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'desconectar':
                    conexion = model.objects.get(pk=int(request.POST['id']), usuario=request.user, status=True)
                    funciones_google.desconectar(conexion, request)
                    log(f'Desconectó {conexion.get_proveedor_display()} ({conexion.cuenta})', request, 'del', obj=conexion.id)
                    messages.success(request, 'Cuenta desconectada.')
                    res_json.append({'error': False, 'reload': True})
                else:
                    raise ValueError('Acción no permitida.')
        except ErrorGoogle as ex:
            res_json = [{'error': True, 'message': str(ex)}]
        except ValueError as ex:
            res_json = [{'error': True, 'message': str(ex)}]
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json = [{'error': True, 'message': 'Intente nuevamente.'}]
        return JsonResponse(res_json, safe=False)
    elif request.method == 'GET':
        if request.path.rstrip('/').endswith('/google'):
            try:
                conexion = funciones_google.completar_autorizacion(request, request.user)
                log(f'Conectó Google Calendar ({conexion.cuenta})', request, 'add', obj=conexion.id)
                messages.success(request, f'Google Calendar conectado como {conexion.cuenta or "tu cuenta"}.')
            except ErrorGoogle as ex:
                messages.error(request, str(ex))
            except Exception as ex:
                salva_logs(request, __file__, request.method, 'google_callback', type(ex).__name__,
                           'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
                messages.error(request, 'No se pudo completar la conexión con Google.')
            return HttpResponseRedirect(RUTA_APLICACIONES)
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            try:
                if action == 'conectar_google':
                    return HttpResponseRedirect(funciones_google.url_autorizacion(request))
                return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
            except ErrorGoogle as ex:
                messages.error(request, str(ex))
                return HttpResponseRedirect(RUTA_APLICACIONES)
            except Exception as ex:
                salva_logs(request, __file__, request.method, action, type(ex).__name__,
                           'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
                messages.error(request, 'No se pudo iniciar la conexión.')
                return HttpResponseRedirect(RUTA_APLICACIONES)
        conexiones = {c.proveedor: c for c in model.objects.filter(status=True, usuario=request.user)}
        data['proveedores'] = [
            {'clave': clave, 'nombre': nombre, 'conexion': conexiones.get(clave), 'disponible': clave == 'google'}
            for clave, nombre in PROVEEDOR_APLICACION
        ]
        data['google_configurado'] = funciones_google.configurada()
        data['google_redirect_uri'] = funciones_google.cliente_oauth()['redirect']
        return render(request, 'agenda/aplicaciones/listado.html', data)
