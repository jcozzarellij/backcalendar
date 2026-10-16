import sys
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from core.custom_models import FormError
from core.funciones import addData, log, paginador, secure_module
from core.funciones_adicionales import salva_logs
from .forms import ProyectoForm
from .funciones_permisos import es_lider_general
from .models import Equipo, Proyecto


@login_required
@secure_module
def proyectoView(request):
    data = {
        'titulo': 'Proyectos',
        'descripcion': 'Cada proyecto agrupa equipos y tiene un líder que organiza sus reuniones.',
        'modulo': 'Agenda',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)
    model = Proyecto
    Formulario = ProyectoForm
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            if not es_lider_general(request.user):
                raise ValueError('Solo el líder general administra los proyectos.')
            with transaction.atomic():
                if action == 'add':
                    form = Formulario(request.POST, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    log(f'Registró el proyecto {form.instance}', request, 'add', obj=form.instance.id)
                    messages.success(request, 'Proyecto registrado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'change':
                    filtro = model.objects.get(pk=int(request.POST['pk']), status=True)
                    form = Formulario(request.POST, instance=filtro, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    log(f'Editó el proyecto {filtro}', request, 'change', obj=filtro.id)
                    messages.success(request, 'Proyecto actualizado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'delete':
                    filtro = model.objects.get(pk=int(request.POST['id']), status=True)
                    if Equipo.objects.filter(status=True, proyecto=filtro).exists():
                        raise ValueError('El proyecto tiene equipos: elimínalos primero.')
                    filtro.status = False
                    filtro.save(request)
                    log(f'Eliminó el proyecto {filtro}', request, 'del', obj=filtro.id)
                    messages.success(request, 'Proyecto eliminado')
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
                return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
            except Exception as ex:
                salva_logs(request, __file__, request.method, action, type(ex).__name__,
                           'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
                return JsonResponse({'result': False, 'message': 'No se pudo cargar el formulario.'})
        criterio, filtros, url_vars = request.GET.get('criterio', '').strip(), Q(status=True), ''
        data['puede_crear'] = es_lider_general(request.user)
        if criterio:
            filtros &= Q(nombre__icontains=criterio) | Q(codigo__icontains=criterio)
            data['criterio'] = criterio
            url_vars += '&criterio=' + criterio
        listado = (model.objects.filter(filtros).select_related('lider')
                   .annotate(num_equipos=Count('equipos', filter=Q(equipos__status=True), distinct=True)))
        data['list_count'] = listado.count()
        data['url_vars'] = url_vars
        paginador(request, listado, 20, data, url_vars)
        return render(request, 'agenda/proyecto/listado.html', data)
