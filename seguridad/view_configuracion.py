import sys
from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect

from core.custom_models import FormError
from core.funciones import addData, secure_module, log, remover_caracteres_especiales_unicode, generar_nombre
from core.funciones_adicionales import salva_logs
from autenticacion.funciones_login_google import uri_retorno
from seguridad.forms import ConfiguracionForm, SECRETOS_CONEXIONES
from seguridad.models import Configuracion


@login_required
@secure_module
def configuracion(request):
    if Configuracion.objects.count() == 0:
        return redirect('/admin/seguridad/configuracion/add/')
    confi = Configuracion.get_instancia()

    data = {
        'titulo': 'Configuración del sitio',
        'modulo': 'Configuración',
        'ruta': request.path,
        'fecha': str(date.today())
    }
    addData(request, data)
    model = Configuracion
    Formulario = ConfiguracionForm

    if request.method == 'POST':
        res_json = []
        if 'action' in request.POST:
            action = request.POST["action"]
            try:
                with transaction.atomic():
                    if action == 'eliminar_icono':
                        c = model.objects.get(pk=int(request.POST["pk"]))
                        c.ico = ''
                        c.save(request)
                        log(f"Elimino icono {c.nombre_empresa}", request, "del")

                        return JsonResponse({'state': True})
                    elif action == 'eliminar_logo':
                        c = model.objects.get(pk=int(request.POST["pk"]))
                        c.logo_sistema = ''
                        c.save(request)
                        log(f"Elimino logo {c.nombre_empresa}", request, "del")
                        return JsonResponse({'state': True})
                    elif action == 'eliminar_logo_white':

                        c = model.objects.get(pk=int(request.POST["pk"]))
                        c.logo_sistema_white = ''
                        c.save(request)
                        log(f"Elimino logo {c.nombre_empresa}", request, "del")
                        return JsonResponse({'state': True})
                    elif action == 'eliminar_fondo_landing':
                        c = model.objects.get(pk=int(request.POST["pk"]))
                        c.fondo_landing = ''
                        c.save(request)
                        log(f"Elimino fondo de portada {c.nombre_empresa}", request, "del")
                        return JsonResponse({'state': True})
                    elif action == 'change':

                        form = Formulario(request.POST, request.FILES, instance=confi, request=request)
                        if form.is_valid():
                            if 'ico' in request.FILES:
                                file = request.FILES['ico']
                                nombredocumento = remover_caracteres_especiales_unicode('ico')
                                file._name = generar_nombre(nombredocumento, file._name)
                                form.instance.ico = file
                            if 'logo_sistema' in request.FILES:
                                file = request.FILES['logo_sistema']
                                nombredocumento = remover_caracteres_especiales_unicode('logo_sistema')
                                file._name = generar_nombre(nombredocumento, file._name)
                                form.instance.logo_sistema = file
                            if 'logo_sistema_white' in request.FILES:
                                file = request.FILES['logo_sistema_white']
                                nombredocumento = remover_caracteres_especiales_unicode('logo_sistema_white')
                                file._name = generar_nombre(nombredocumento, file._name)
                                form.instance.logo_sistema_white = file
                            if 'fondo_landing' in request.FILES:
                                file = request.FILES['fondo_landing']
                                nombredocumento = remover_caracteres_especiales_unicode('fondo_landing')
                                file._name = generar_nombre(nombredocumento, file._name)
                                form.instance.fondo_landing = file
                            form.save()
                            log(f"Edito Configuracion {form.instance.__str__()}", request, "change", obj=form.instance.id)

                            res_json.append({'error': False,
                                             "to": request.path
                                             })
                            messages.success(request, "Modificado correctamente.")
                        else:
                            raise FormError(form)
            except ValueError as ex:
                res_json.append({'error': True,
                                 "message": str(ex)
                                 })
            except FormError as ex:
                res_json.append(ex.dict_error)
            except Exception as ex:
                salva_logs(request, __file__, request.method,
                           action, type(ex).__name__,
                           'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
                res_json.append({'error': True,
                                 "message": "Intente Nuevamente"
                                 })
        return JsonResponse(res_json, safe=False)

    elif request.method == 'GET':
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'ver_secreto':
                campo = request.GET.get('campo', '')
                if campo not in SECRETOS_CONEXIONES:
                    return JsonResponse({'result': False, 'message': 'Campo no permitido.'})
                valor = getattr(model.objects.get(pk=confi.pk), campo) or ''
                log(f'Consultó el secreto «{model._meta.get_field(campo).verbose_name}» de la configuración', request, 'change', obj=confi.pk)
                return JsonResponse({'result': True, 'valor': valor})
        data["form"] = Formulario(instance=confi)
        data["pk"] = confi.pk
        data['tabs_config'] = [
            {'clave': 'general', 'titulo': 'Información General', 'icono': 'fa-building',
             'campos': ['nombre_empresa', 'alias', 'titulo', 'descripcion', 'telefono', 'email',
                        'web', 'email_notificacion', 'direccion']},
            {'clave': 'grafica', 'titulo': 'Identidad Gráfica', 'icono': 'fa-palette',
             'campos': ['ico', 'logo_sistema', 'logo_sistema_white', 'fondo_landing']},
            {'clave': 'plataforma', 'titulo': 'Configuración de plataforma', 'icono': 'fa-gears',
             'campos': ['pg_dump_cmd', 'backup_retencion']},
            {'clave': 'google', 'titulo': 'Conexión Google', 'icono': 'fa-calendar-check',
             'campos': ['google_client_id', 'google_client_secret', 'google_redirect_uri', 'conexion_google'],
             'nota': _nota_google(confi)},
            {'clave': 'teams', 'titulo': 'Conexión Teams', 'icono': 'fa-users',
             'campos': ['teams_client_id', 'teams_client_secret', 'teams_tenant_id', 'teams_redirect_uri'],
             'nota': NOTA_PENDIENTE.format('Microsoft Teams')},
            {'clave': 'zoom', 'titulo': 'Conexión Zoom', 'icono': 'fa-video',
             'campos': ['zoom_client_id', 'zoom_client_secret', 'zoom_redirect_uri'],
             'nota': NOTA_PENDIENTE.format('Zoom')},
        ]
        return render(request, 'seguridad/configuracion/form.html', data)
    return None


NOTA_PENDIENTE = ('Las claves de la aplicación de {} quedan guardadas aquí (el secreto, cifrado). La conexión de cada '
                  'persona con su cuenta se habilita en Conexiones cuando se active esa integración.')


def _nota_google(confi):
    """Texto de ayuda de la pestaña Google: qué URI registrar y de dónde salen hoy las claves."""
    nota = (f'Cliente OAuth de tipo «Aplicación web». En Google Cloud registra como URI de redirección '
            f'{confi.google_redirect_uri or settings.GOOGLE_OAUTH_REDIRECT_URI} y habilita la Google Calendar API.')
    nota += (f' Para iniciar sesión con Google, registra también {uri_retorno()} y carga los dominios '
             'permitidos en Dominios de correo.')
    if not confi.google_client_id and settings.GOOGLE_OAUTH_CLIENT_ID:
        nota += ' Hoy se usan las claves de credenciales.json; al guardar aquí un ID de cliente pasan a usarse estas.'
    if confi.google_client_id:
        nota += ' Si cambias el ID de cliente, cada persona tendrá que volver a conectar su Google en Conexiones.'
    return nota
