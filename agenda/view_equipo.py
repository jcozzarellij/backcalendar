import sys
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from core.custom_models import FormError
from core.funciones import addData, log, paginador, secure_module
from core.funciones_adicionales import salva_logs
from .forms import EquipoForm, MiembroEquipoForm
from .funciones_permisos import equipos_visibles, es_administrador, puede_gestionar_equipo
from .models import Equipo, Feriado, MiembroEquipo


@login_required
@secure_module
def equipoView(request):
    data = {
        'titulo': 'Equipos',
        'descripcion': 'Quiénes atienden cada proyecto: responsables y quienes van en copia.',
        'modulo': 'Agenda',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)
    model = Equipo
    Formulario = EquipoForm
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'add':
                    if not es_administrador(request.user):
                        raise ValueError('Solo el líder general crea equipos.')
                    form = Formulario(request.POST, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    log(f'Registró el equipo {form.instance}', request, 'add', obj=form.instance.id)
                    messages.success(request, 'Equipo registrado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'change':
                    filtro = model.objects.get(pk=int(request.POST['pk']), status=True)
                    if not puede_gestionar_equipo(request.user, filtro):
                        raise ValueError('No gestionas este equipo.')
                    form = Formulario(request.POST, instance=filtro, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    log(f'Editó el equipo {filtro}', request, 'change', obj=filtro.id)
                    messages.success(request, 'Equipo actualizado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'delete':
                    filtro = model.objects.get(pk=int(request.POST['id']), status=True)
                    if not es_administrador(request.user):
                        raise ValueError('Solo el líder general elimina equipos.')
                    for miembro in filtro.miembros.filter(status=True):
                        miembro.status = False
                        miembro.save(request)
                    if Feriado.objects.filter(status=True, equipo=filtro).exists():
                        raise ValueError('El equipo tiene feriados propios: elimínalos primero.')
                    filtro.status = False
                    filtro.save(request)
                    log(f'Eliminó el equipo {filtro}', request, 'del', obj=filtro.id)
                    messages.success(request, 'Equipo eliminado')
                    res_json = {'error': False}
                elif action == 'addmiembro':
                    equipo = model.objects.get(pk=int(request.POST['pk']), status=True)
                    if not puede_gestionar_equipo(request.user, equipo):
                        raise ValueError('No gestionas este equipo.')
                    form = MiembroEquipoForm(request.POST, request=request, equipo=equipo)
                    if not form.is_valid():
                        raise FormError(form)
                    form.instance.equipo = equipo
                    form.save()
                    log(f'Agregó a {form.instance.usuario} al equipo {equipo}', request, 'add', obj=form.instance.id)
                    messages.success(request, 'Miembro agregado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'rolmiembro':
                    miembro = MiembroEquipo.objects.get(pk=int(request.POST['id']), status=True)
                    if not puede_gestionar_equipo(request.user, miembro.equipo):
                        raise ValueError('No gestionas este equipo.')
                    miembro.rol = 'copia' if miembro.rol == 'responsable' else 'responsable'
                    miembro.save(request)
                    log(f'Cambió el rol de {miembro.usuario} en {miembro.equipo} a {miembro.get_rol_display()}',
                        request, 'change', obj=miembro.id)
                    res_json = {'error': False}
                elif action == 'delmiembro':
                    miembro = MiembroEquipo.objects.get(pk=int(request.POST['id']), status=True)
                    if not puede_gestionar_equipo(request.user, miembro.equipo):
                        raise ValueError('No gestionas este equipo.')
                    miembro.status = False
                    miembro.save(request)
                    log(f'Quitó a {miembro.usuario} del equipo {miembro.equipo}', request, 'del', obj=miembro.id)
                    messages.success(request, 'Miembro quitado')
                    res_json = {'error': False}
                else:
                    raise ValueError('Acción no permitida.')
        except ValueError as ex:
            res_json = [{'error': True, 'message': str(ex)}]
        except FormError as ex:
            res_json = [ex.dict_error]
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json = [{'error': True, 'message': 'Intente nuevamente.'}]
        return JsonResponse(res_json, safe=False)
    elif request.method == 'GET':
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            try:
                if action == 'add':
                    data['form'] = Formulario()
                    template = get_template('agenda/parciales/form_campos.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                elif action == 'change':
                    data['pk'] = pk = int(request.GET['pk'])
                    data['form'] = Formulario(instance=model.objects.get(pk=pk, status=True))
                    template = get_template('agenda/parciales/form_campos.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                elif action == 'addmiembro':
                    data['pk'] = pk = int(request.GET['pk'])
                    data['form'] = MiembroEquipoForm(equipo=model.objects.get(pk=pk, status=True))
                    template = get_template('agenda/parciales/form_campos.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
            except Exception as ex:
                salva_logs(request, __file__, request.method, action, type(ex).__name__,
                           'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
                return JsonResponse({'result': False, 'message': 'No se pudo cargar el formulario.'})
        criterio, filtros, url_vars = request.GET.get('criterio', '').strip(), Q(status=True), ''
        filtros &= Q(pk__in=equipos_visibles(request.user).values('pk'))
        data['puede_crear'] = es_administrador(request.user)
        if criterio:
            filtros &= Q(nombre__icontains=criterio) | Q(proyecto__nombre__icontains=criterio)
            data['criterio'] = criterio
            url_vars += '&criterio=' + criterio
        miembros = MiembroEquipo.objects.filter(status=True).select_related('usuario')
        listado = (model.objects.filter(filtros).select_related('proyecto', 'lider')
                   .prefetch_related(Prefetch('miembros', queryset=miembros, to_attr='miembros_activos'))
                   .annotate(num_miembros=Count('miembros', filter=Q(miembros__status=True), distinct=True)))
        data['list_count'] = listado.count()
        data['url_vars'] = url_vars
        paginador(request, listado, 20, data, url_vars)
        return render(request, 'agenda/equipo/listado.html', data)
