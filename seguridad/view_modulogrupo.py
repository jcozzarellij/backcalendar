import ast
import sys
from datetime import date
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import CharField, Prefetch, Value as V, Q
from django.db.models.functions import Concat
from django.http import JsonResponse
from django.shortcuts import render

from core.custom_models import FormError
from core.funciones import addData, paginador, secure_module, redirectAfterPostGet, log
from core.funciones_adicionales import ordenar_modulos_url, salva_logs
from seguridad.forms import ModuloGrupoForm
from seguridad.models import ModuloGrupo, Modulo
from django.contrib import messages


@login_required
@secure_module
def modulo_grupo(request):
    data = {
        'titulo': 'Secciones del sidebar',
        'modulo': 'Grupos de Urls',
        'ruta': request.path,
        'fecha': str(date.today())
    }
    addData(request, data)
    model = ModuloGrupo
    Formulario = ModuloGrupoForm

    if request.method == 'POST':
        res_json = []
        action = request.POST['action']
        try:
            if action == 'add':

                form = Formulario(request.POST, request=request)
                if form.is_valid():
                    try:
                        with transaction.atomic():
                            form.save()
                            mod_lista = request.POST.getlist('c_modulos', [])
                            for ml in mod_lista:
                                # SEGURIDAD: ast.literal_eval en vez de eval() — el input viene del POST
                                # y eval() permitía ejecución de código arbitrario (RCE). literal_eval
                                # sólo acepta literales (dict/list/str/num) y rechaza cualquier llamada.
                                datos = ast.literal_eval(ml)
                                # Sin `status` en la búsqueda, y con `status=True` al actualizar: es un
                                # get-or-create por URL. Si la fila existe dada de baja hay que
                                # ENCONTRARLA y reactivarla — filtrarla crearía una URL repetida, y no
                                # reactivarla dejaba al administrador agregando al sidebar una entrada
                                # que nunca aparecía.
                                mod = Modulo.objects.filter(url=datos["url"])
                                if mod.exists():
                                    mod.update(orden=datos["orden"], url=datos["url"], status=True)
                                    mod_obj = mod.first()
                                else:
                                    mod_obj = Modulo.objects.create(orden=datos["orden"], nombre=datos["nombre"],
                                                                    url=datos["url"])
                                form.instance.modulos.add(mod_obj)
                            log(f"Agrego modulo grupo {form.instance.__str__()}", request, "add", obj=form.instance.id)

                            res_json.append({'error': False,
                                             "to": redirectAfterPostGet(request)
                                             })
                    except ValueError as e:
                        res_json.append({'error': True,
                                         "message": str(e)
                                         })
                    except Exception as ex:
                        pass
                else:
                    raise FormError(form)

            elif action == 'change':

                modulo = ModuloGrupo.objects.get(pk=int(request.POST['pk']))

                form = Formulario(request.POST, instance=modulo, request=request)
                if form.is_valid():
                    try:
                        with transaction.atomic():
                            form.save()
                            mod_lista = request.POST.getlist('c_modulos', [])
                            for ml in mod_lista:
                                # SEGURIDAD: ast.literal_eval en vez de eval() (RCE) — ver nota en 'add'.
                                datos = ast.literal_eval(ml)
                                # Mismo get-or-create que en 'add': reactiva la fila dada de baja.
                                mod = Modulo.objects.filter(url=datos["url"])
                                if mod.exists():
                                    mod.update(orden=datos["orden"], url=datos["url"], status=True)
                                    mod_obj = mod.first()
                                else:
                                    mod_obj = Modulo.objects.create(orden=datos["orden"], nombre=datos["nombre"],
                                                                    url=datos["url"])
                                form.instance.modulos.add(mod_obj)
                            log(f"Modifico modulo grupo {form.instance.__str__()}", request, "change", obj=form.instance.id)

                            res_json.append({'error': False,
                                             "to": redirectAfterPostGet(request)
                                             })
                    except ValueError as e:
                        res_json.append({'error': True,
                                         "message": str(e)
                                         })
                    except Exception as ex:
                        pass
                else:
                    raise FormError(form)

            elif action == 'cambiar_prioridades':
                import json as _json
                cambios = _json.loads(request.POST.get('cambios', '[]'))
                with transaction.atomic():
                    for c in cambios:
                        ModuloGrupo.objects.filter(pk=int(c['id']), status=True).update(
                            prioridad=int(c.get('prioridad', 0))
                        )
                log(f"Prioridades actualizadas: {len(cambios)} grupo(s)", request, "change")
                return JsonResponse({'error': False, 'message': f'{len(cambios)} prioridad(es) actualizada(s).'})

            elif action == 'delete':

                modulo = ModuloGrupo.objects.get(pk=int(request.POST['id']))

                try:
                    with transaction.atomic():
                        modulo.status = False
                        modulo.save(request)
                        log(f"Elimino modulo grupo {modulo.__str__()}", request, "del")
                        res_json={"error":False}
                except ValueError as e:
                    messages.error(request, str(e))
                except Exception as ex:
                    pass

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
            data["action"] = action = request.GET['action']
            if action == 'add':

                data["form"] = form = Formulario()
                qs_modulos = form.fields["modulos"].queryset
                ordenar_modulos_url(data, qs_modulos)
                return render(request, 'seguridad/modulogrupo/form.html', data)

            elif action == 'change':

                pk = int(request.GET['pk'])
                modulo = ModuloGrupo.objects.get(pk=pk)
                data["pk"] = pk
                data["form"] = form = Formulario(instance=modulo)
                qs_modulos = form.fields["modulos"].queryset
                data["modulos_seleccionados"] = modulos_seleccionados = list(
                    modulo.modulos_activos().values_list('url', flat=True))
                ordenar_modulos_url(data, qs_modulos, modulos_seleccionados)
                return render(request, 'seguridad/modulogrupo/form.html', data)

            elif action == 'ver':

                pk = int(request.GET['pk'])
                modulo = ModuloGrupo.objects.get(pk=pk)
                data["pk"] = pk
                data["form"] = form = Formulario(instance=modulo, ver=True)
                qs_modulos = form.fields["modulos"].queryset
                data["modulos_seleccionados"] = modulos_seleccionados = list(
                    modulo.modulos_activos().values_list('url', flat=True))
                ordenar_modulos_url(data, qs_modulos, modulos_seleccionados)
                return render(request, 'seguridad/modulogrupo/form.html', data)

            elif action == 'change_modal':

                pk = int(request.GET['pk'])
                modulo = ModuloGrupo.objects.get(pk=pk)
                data["pk"] = pk
                data["action"] = 'change'
                data["form"] = form = Formulario(instance=modulo)
                qs_modulos = form.fields["modulos"].queryset
                data["modulos_seleccionados"] = modulos_seleccionados = list(
                    modulo.modulos_activos().values_list('url', flat=True))
                ordenar_modulos_url(data, qs_modulos, modulos_seleccionados)
                return render(request, 'seguridad/modulogrupo/form_modal.html', data)

            elif action == 'ver_modulos':
                pk = int(request.GET['pk'])
                modulo = ModuloGrupo.objects.get(pk=pk)
                return JsonResponse(list(modulo.modulos_activos().order_by('orden').annotate(
                    nombres=Concat('orden', V(', '), 'nombre', V(' ('), 'url', V(')'),
                                   output_field=CharField())).values('nombres')), safe=False)

        criterio, filtros, url_vars = request.GET.get('criterio', '').strip(), Q(status=True), ''
        if criterio:
            filtros = filtros & Q(nombre__icontains=criterio)
            data["criterio"] = criterio
            url_vars += '&criterio=' + criterio

        criterio_modulo = request.GET.get('criterio_modulo', '').strip()
        if criterio_modulo:
            filtros = filtros & Q(modulos__nombre__icontains=criterio_modulo, modulos__status=True)
            data["criterio_modulo"] = criterio_modulo
            url_vars += '&criterio_modulo=' + criterio_modulo

        # Cada fila lista sus módulos ordenados: se traen en una sola consulta para toda la página.
        modulos = ModuloGrupo.objects.filter(filtros).distinct().prefetch_related(
            Prefetch('modulos', queryset=Modulo.objects.order_by('orden'), to_attr='modulos_pagina'))
        data["url_vars"] = url_vars
        paginador(request, modulos.order_by('prioridad'), 20, data, url_vars)
        return render(request, 'seguridad/modulogrupo/listado.html', data)
