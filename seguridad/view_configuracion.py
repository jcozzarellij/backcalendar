import sys
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect

from core.custom_models import FormError
from core.funciones import addData, secure_module, log, remover_caracteres_especiales_unicode, generar_nombre
from core.funciones_adicionales import salva_logs
from seguridad.forms import ConfiguracionForm
from seguridad.models import Configuracion


@login_required
@secure_module
def configuracion(request):
    if Configuracion.objects.count() == 0:
        return redirect('/admin/seguridad/configuracion/add/')
    confi = Configuracion.get_instancia()

    data = {
        'titulo': 'Configuración del Sistema {}'.format(confi.nombre_empresa),
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
        ]
        return render(request, 'seguridad/configuracion/form.html', data)
    return None
