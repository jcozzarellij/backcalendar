import json
from datetime import date
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from core.funciones import addData, log, salva_auditoria, secure_module
from seguridad.models import ModuloGrupo, Modulo, GroupModulo
from django.contrib import messages


@login_required
@secure_module
def arbol_modulo_grupo(request):
    data = {'titulo': 'Grupos de Urls',
            'modulo': 'Grupos de Urls',
            'ruta': request.path,
            'ruta_val': request.path,
            'group': 'Seguridad',
            'fecha': str(date.today())
            }
    addData(request, data)
    model = ModuloGrupo


    if request.method == 'POST':
        res_json = []
        action = request.POST['action']
        if action == 'eliminar_url':
            try:
                filtro = Modulo.objects.get(pk=int(request.POST['id']), status=True)
                filtro.status = False
                filtro.save(request)
                salva_auditoria(request, filtro, 3, f'Eliminó la URL "{filtro.nombre}" ({filtro.url}) desde el árbol de grupos')
                return JsonResponse({'error': False, 'message': f'URL "{filtro.nombre}" eliminada del sidebar.'})
            except Modulo.DoesNotExist:
                return JsonResponse({'error': True, 'message': 'La URL no existe o ya fue eliminada.'})
            except Exception:
                return JsonResponse({'error': True, 'message': 'Intente Nuevamente'})
        if action == 'cambiar_lugar_grupo':

                try:
                    with transaction.atomic():
                        c_modulos = request.POST.getlist('c_modulos', [])
                        cambios = 0
                        for x in c_modulos:
                            cm = json.loads(x)
                            try:
                                pk_destino = int(cm.get("pk_destino") or 0)
                                pk_modulo = int(cm.get("pk_modulo") or 0)
                                orden_nuevo = int(cm.get("orden") or 0)
                            except (TypeError, ValueError):
                                continue
                            if pk_destino <= 0 or pk_modulo <= 0:
                                continue
                            mg_destino = ModuloGrupo.objects.filter(pk=pk_destino, status=True).first()
                            modulo = Modulo.objects.filter(pk=pk_modulo, status=True).first()
                            if not mg_destino or not modulo:
                                continue
                            grupos_actuales = set(ModuloGrupo.objects.filter(modulos=modulo, status=True).values_list('pk', flat=True))
                            if grupos_actuales == {pk_destino} and modulo.orden == orden_nuevo:
                                continue
                            if modulo.orden != orden_nuevo:
                                modulo.orden = orden_nuevo
                                modulo.save(request)
                            for mg_otro in ModuloGrupo.objects.filter(modulos=modulo, status=True).exclude(pk=pk_destino):
                                mg_otro.modulos.remove(modulo)
                            mg_destino.modulos.add(modulo)
                            cambios += 1
                        if cambios:
                            log(f'Reubicó {cambios} URL(s) entre grupos del sidebar', request, 'change')
                            messages.success(request, f"{cambios} URL(s) reubicadas entre grupos.")
                        else:
                            messages.info(request, "No se detectaron cambios.")
                except ValueError as e:
                    messages.error(request, str(e))
                except Exception as ex:
                    messages.error(request, "Ocurrió un error. Intente nuevamente.")

                return redirect(request.path)

    elif request.method == 'GET':

            modulos = ModuloGrupo.objects.filter(status=True).order_by('prioridad')
            data['listado'] = modulos
            roles = list(
                GroupModulo.objects.filter(status=True).select_related('group')
                .prefetch_related('modulos').order_by('group__name')
            )
            data['roles'] = roles
            data['modulos_por_rol'] = {
                str(gm.pk): [m.pk for m in gm.modulos_activos()] for gm in roles
            }
            return render(request, 'seguridad/modulogrupo/listado_arbol.html', data)
