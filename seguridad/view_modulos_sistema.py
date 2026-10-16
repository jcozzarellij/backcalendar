import json
import sys
from datetime import date
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template

from core.funciones import addData, secure_module, log, paginador
from core.funciones_adicionales import salva_logs
from seguridad.forms import ModuloForm
from seguridad.funciones_modulos import urls_pendientes_por_grupo
from seguridad.models import Modulo, ModuloGrupo, GroupModulo
from django.contrib import messages


@login_required
@secure_module
def modulossistemaView(request):
    data = {'titulo': 'Mantenimiento de Url',
            'modulo': 'Url',
            'ruta': request.path,
            'fecha': str(date.today())
            }
    model = Modulo
    Formulario = ModuloForm
    if request.method == 'POST':
        res_json = []
        action = request.POST['action']
        try:
            with transaction.atomic():
                if action == 'add':
                    form = Formulario(request.POST, request=request)
                    if form.is_valid():
                        form.save()
                        log(f"Registro un nuevo modulo {form.instance.__str__()}", request, "add")
                        res_json.append({'error': False,
                                         "reload": True
                                         })
                    else:
                        res_json.append({'error': True,
                                             "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "message": "Error en el formulario"
                                             })
                elif action == 'change':
                    modulo = model.objects.get(pk=int(request.POST['pk']))
                    form = Formulario(request.POST, request.FILES, instance=modulo,request=request)
                    if form.is_valid():
                        form.save()
                        log(f"Edito un modulo {form.instance.__str__()}", request, "change")
                        res_json.append({'error': False,
                                         "reload": True
                                         })
                    else:
                        res_json.append({'error': True,
                                             "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "message": "Error en el formulario"
                                             })
                elif action == 'delete':
                    modulo = model.objects.get(pk=int(request.POST['id']))
                    modulo.status = False
                    modulo.save(request)
                    log(f"Elimino modulo {modulo.__str__()}", request, "delete")
                    messages.success(request, f"Registro Eliminado")
                    res_json = {"error": False}
                elif action == 'act_orden':
                    try:
                        filtro = model.objects.get(pk=int(request.POST['id']))
                        filtro.orden = int(request.POST['valor'])
                        filtro.save(request)
                        log(f"Actualizo orden url {filtro.__str__()}", request, "change")
                        return HttpResponse(json.dumps({'result': True, 'orden': filtro.orden}))
                    except (ValueError, TypeError):
                        return HttpResponse(json.dumps({'result': False, 'mensaje': 'Orden inválido'}))
                    except Exception as ex:
                        return HttpResponse(json.dumps({'result': False, 'mensaje': str(ex)}))
                elif action == 'act_icono':
                    try:
                        filtro = model.objects.get(pk=int(request.POST['id']))
                        filtro.icono = request.POST.get('valor', '').strip()
                        filtro.save(request)
                        log(f"Actualizo ícono url {filtro.__str__()}", request, "change")
                        return HttpResponse(json.dumps({'result': True, 'icono': filtro.icono}))
                    except Exception as ex:
                        return HttpResponse(json.dumps({'result': False, 'mensaje': str(ex)}))
                elif action == 'guardar_grupos_modulo':
                    pk_modulo = int(request.POST.get('pk_modulo') or 0)
                    grupos_ids = [int(g) for g in request.POST.getlist('c_grupos', []) if g.isdigit()]
                    modulo = model.objects.filter(pk=pk_modulo, status=True).first()
                    if not modulo:
                        res_json.append({'error': True, 'message': 'Módulo no encontrado.'})
                    else:
                        grupos_actuales = set(ModuloGrupo.objects.filter(modulos=modulo, status=True).values_list('pk', flat=True))
                        grupos_nuevos = set(grupos_ids)
                        a_agregar = grupos_nuevos - grupos_actuales
                        a_quitar = grupos_actuales - grupos_nuevos
                        for gid in a_agregar:
                            mg = ModuloGrupo.objects.filter(pk=gid, status=True).first()
                            if mg:
                                mg.modulos.add(modulo)
                        for gid in a_quitar:
                            mg = ModuloGrupo.objects.filter(pk=gid, status=True).first()
                            if mg:
                                mg.modulos.remove(modulo)
                        log(f"Sincronizó grupos del módulo {modulo.__str__()}: +{len(a_agregar)} / -{len(a_quitar)}", request, "change")
                        res_json.append({
                            'error': False,
                            'message': f"Grupos actualizados (+{len(a_agregar)} / -{len(a_quitar)}).",
                            'reload': True
                        })
                elif action == 'guardar_roles_modulo':
                    pk_modulo = int(request.POST.get('pk_modulo') or 0)
                    roles_ids = [int(r) for r in request.POST.getlist('c_roles', []) if r.isdigit()]
                    modulo = model.objects.filter(pk=pk_modulo, status=True).first()
                    if not modulo:
                        res_json.append({'error': True, 'message': 'Módulo no encontrado.'})
                    else:
                        roles_actuales = set(GroupModulo.objects.filter(modulos=modulo, status=True).values_list('pk', flat=True))
                        roles_nuevos = set(roles_ids)
                        a_agregar = roles_nuevos - roles_actuales
                        a_quitar = roles_actuales - roles_nuevos
                        for rid in a_agregar:
                            gm = GroupModulo.objects.filter(pk=rid, status=True).first()
                            if gm:
                                gm.modulos.add(modulo)
                        for rid in a_quitar:
                            gm = GroupModulo.objects.filter(pk=rid, status=True).first()
                            if gm:
                                gm.modulos.remove(modulo)
                        log(f"Sincronizó roles del módulo {modulo.__str__()}: +{len(a_agregar)} / -{len(a_quitar)}", request, "change")
                        res_json.append({
                            'error': False,
                            'message': f"Roles actualizados (+{len(a_agregar)} / -{len(a_quitar)}).",
                            'reload': True
                        })
                elif action == 'extraer_urls':
                    # Confirmación desde el modal de vista previa: solo se registran las URLs
                    # SELECCIONADAS (c_urls), validadas contra las realmente pendientes — el
                    # POST nunca puede crear una URL arbitraria. Sin c_urls (compat) crea todas.
                    seleccionadas = set(request.POST.getlist('c_urls', []))
                    nuevas = []
                    existentes_urls = set(model.objects.values_list('url', flat=True))
                    for grupo in urls_pendientes_por_grupo(existentes_urls):
                        for idx, pendiente in enumerate(grupo['urls']):
                            if seleccionadas and pendiente['url'] not in seleccionadas:
                                continue
                            if pendiente['url'] in existentes_urls:
                                continue
                            model.objects.create(
                                orden=idx,
                                nombre=pendiente['nombre'],
                                url=pendiente['url'],
                            )
                            existentes_urls.add(pendiente['url'])
                            nuevas.append(pendiente['url'])
                    log(f"Extrajo {len(nuevas)} URLs nuevas del sistema", request, "add")
                    res_json.append({
                        'error': False,
                        'reload': bool(nuevas),
                        'message': f"{len(nuevas)} URL(s) nueva(s) registrada(s)." if nuevas else "No se registró ninguna URL nueva.",
                    })
        except ValueError as ex:
            res_json.append({'error': True,
                             "message": str(ex)
                             })
        except Exception as ex:
            salva_logs(request, __file__, request.method,
                       action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json.append({'error': True,
                             "message": "Intente Nuevamente"
                             })
        return JsonResponse(res_json, safe=False)
    elif request.method == 'GET':
        addData(request, data)
        if 'action' in request.GET:
            data["action"] = action = request.GET['action']
            if action == 'add':
                data["form"] = Formulario()
                template = get_template("seguridad/modulossistema/form.html")
                return JsonResponse({"result": True, 'data': template.render(data)})
            elif action == 'change':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['filtro'] = filtro = model.objects.get(pk=id)
                    form = Formulario(instance=filtro)
                    data['form'] = form
                    template = get_template("seguridad/modulossistema/form.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'ver':
                pk = int(request.GET['pk'])
                modulo = model.objects.get(pk=pk)
                data["pk"] = pk
                data["form"] = Formulario(instance=modulo, ver=True)
                return render(request, 'seguridad/modulossistema/form.html', data)
            elif action == 'grupos_modulo':
                pk_modulo = int(request.GET.get('id') or 0)
                modulo = model.objects.filter(pk=pk_modulo, status=True).first()
                if not modulo:
                    return JsonResponse({'result': False, 'message': 'Módulo no encontrado.'})
                grupos_actuales_ids = set(ModuloGrupo.objects.filter(modulos=modulo, status=True).values_list('pk', flat=True))
                data['modulo'] = modulo
                data['grupos'] = ModuloGrupo.objects.filter(status=True).order_by('prioridad', 'nombre')
                data['grupos_actuales_ids'] = grupos_actuales_ids
                template = get_template('seguridad/modulossistema/form_grupos.html')
                return JsonResponse({'result': True, 'data': template.render(data)})
            elif action == 'roles_modulo':
                pk_modulo = int(request.GET.get('id') or 0)
                modulo = model.objects.filter(pk=pk_modulo, status=True).first()
                if not modulo:
                    return JsonResponse({'result': False, 'message': 'Módulo no encontrado.'})
                roles_actuales_ids = set(GroupModulo.objects.filter(modulos=modulo, status=True).values_list('pk', flat=True))
                data['modulo'] = modulo
                data['roles'] = GroupModulo.objects.filter(status=True).select_related('group').order_by('group__name')
                data['roles_actuales_ids'] = roles_actuales_ids
                template = get_template('seguridad/modulossistema/form_roles.html')
                return JsonResponse({'result': True, 'data': template.render(data)})
            elif action == 'extraer_urls_preview':
                existentes_urls = set(model.objects.values_list('url', flat=True))
                grupos_urls = urls_pendientes_por_grupo(existentes_urls)
                data['grupos_urls'] = grupos_urls
                data['total_pendientes'] = sum(len(g['urls']) for g in grupos_urls)
                template = get_template('seguridad/modulossistema/form_extraer.html')
                return JsonResponse({'result': True, 'data': template.render(data)})

        criterio, filtros, url_vars =  request.GET.get('criterio', ''), Q(status=True), ''
        usadas = request.GET.get('usadas', '')
        grupo_id = request.GET.get('grupo', '')
        rol_id = request.GET.get('rol', '')
        grupos_n = request.GET.get('grupos_n', '')
        orden = request.GET.get('orden', 'id_desc')

        if grupos_n in ('mas2', '2', '1', '0'):
            data['grupos_n'] = grupos_n
            url_vars += f'&grupos_n={grupos_n}'
        else:
            grupos_n = ''

        if grupo_id.isdigit():
            data['grupo_sel'] = int(grupo_id)
            url_vars += f'&grupo={grupo_id}'
            filtros = filtros & Q(modulogrupo__id=int(grupo_id), modulogrupo__status=True)
        if rol_id.isdigit():
            data['rol_sel'] = int(rol_id)
            url_vars += f'&rol={rol_id}'
            filtros = filtros & Q(groupmodulo__id=int(rol_id), groupmodulo__status=True)
        if usadas in ('1', '0'):
            data['usadas'] = usadas
            url_vars += f'&usadas={usadas}'
            ids_usadas = list(
                x for x in ModuloGrupo.objects.filter(status=True).values_list('modulos__id', flat=True).distinct() if x
            )
            if usadas == '1':
                filtros = filtros & Q(id__in=ids_usadas)
            else:
                filtros = filtros & ~Q(id__in=ids_usadas)
        if criterio:
            filtros = filtros & (Q(nombre__icontains=criterio) | Q(url__icontains=criterio))
            data["criterio"] = criterio
            url_vars += '&criterio=' + criterio
        orden_map = {
            'id_desc': '-id',
            'id_asc': 'id',
            'nombre_asc': 'nombre',
            'nombre_desc': '-nombre',
            'fecha_asc': 'fecha_registro',
            'fecha_desc': '-fecha_registro',
        }
        order_field = orden_map.get(orden, '-id')
        data['orden'] = orden
        if orden != 'id_desc':
            url_vars += f'&orden={orden}'

        qs_modulos = (
            model.objects.filter(filtros)
            # Prefetch con el queryset ya filtrado, no `{% if g.status %}` en la plantilla:
            # con el `if`, una URL cuyos grupos estaban todos dados de baja pintaba una celda
            # vacía —el `{% empty %}` no se dispara si la lista trae filas ocultas— y el menú
            # mostraba grupos que ya no existen.
            .prefetch_related(
                Prefetch('modulogrupo_set', to_attr='grupos_activos',
                         queryset=ModuloGrupo.objects.filter(status=True).order_by('nombre')),
                Prefetch('groupmodulo_set', to_attr='roles_activos',
                         queryset=GroupModulo.objects.filter(status=True).select_related('group')),
            )
            .annotate(
                roles_count=Count('groupmodulo', filter=Q(groupmodulo__status=True), distinct=True),
                grupos_count=Count('modulogrupo', filter=Q(modulogrupo__status=True), distinct=True),
            )
            .distinct()
        )
        # Una URL repetida en muchos grupos del sidebar aparece duplicada en el menú del usuario:
        # este filtro las aísla para poder limpiarlas. Va después del annotate porque compara
        # contra la cuenta de grupos, no contra un campo de la tabla.
        if grupos_n == 'mas2':
            qs_modulos = qs_modulos.filter(grupos_count__gt=2)
        elif grupos_n == '2':
            qs_modulos = qs_modulos.filter(grupos_count=2)
        elif grupos_n == '1':
            qs_modulos = qs_modulos.filter(grupos_count=1)
        elif grupos_n == '0':
            qs_modulos = qs_modulos.filter(grupos_count=0)
        data["list_count"] = qs_modulos.count()
        data["url_vars"] = url_vars
        from datetime import datetime, timedelta
        data["umbral_reciente"] = datetime.now() - timedelta(days=7)
        ids_usadas_set = set(
            x for x in ModuloGrupo.objects.filter(status=True).values_list('modulos__id', flat=True).distinct() if x
        )
        data["ids_usadas"] = ids_usadas_set
        data["grupos_filtro"] = ModuloGrupo.objects.filter(status=True).order_by('nombre')
        data["roles_filtro"] = GroupModulo.objects.filter(status=True).select_related('group').order_by('group__name')
        paginador(request, qs_modulos.order_by(order_field), 20, data, url_vars)
        return render(request, 'seguridad/modulossistema/listado.html', data)
