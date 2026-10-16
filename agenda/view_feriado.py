import sys
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from core.custom_models import FormError
from core.funciones import addData, log, paginador, secure_module
from core.funciones_adicionales import salva_logs
from .forms import FeriadoForm
from .models import Feriado


@login_required
@secure_module
def feriadoView(request):
    data = {
        'titulo': 'Feriados',
        'descripcion': 'Días no laborables: nadie recibe citas en ellos.',
        'modulo': 'Agenda',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)
    model = Feriado
    Formulario = FeriadoForm
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'add':
                    form = Formulario(request.POST, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    log(f'Registró el feriado {form.instance}', request, 'add', obj=form.instance.id)
                    messages.success(request, 'Feriado registrado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'change':
                    filtro = model.objects.get(pk=int(request.POST['pk']), status=True)
                    form = Formulario(request.POST, instance=filtro, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    log(f'Editó el feriado {filtro}', request, 'change', obj=filtro.id)
                    messages.success(request, 'Feriado actualizado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'delete':
                    filtro = model.objects.get(pk=int(request.POST['id']), status=True)
                    filtro.status = False
                    filtro.save(request)
                    log(f'Eliminó el feriado {filtro}', request, 'del', obj=filtro.id)
                    messages.success(request, 'Feriado eliminado')
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
        anio = request.GET.get('anio', '').strip()
        anio = int(anio) if anio.isdigit() else date.today().year
        data['anio'] = anio
        data['anios'] = list(range(date.today().year - 1, date.today().year + 3))
        url_vars = f'&anio={anio}'
        listado = model.objects.filter(Q(status=True), fecha__year=anio).select_related('equipo__proyecto')
        data['list_count'] = listado.count()
        data['url_vars'] = url_vars
        paginador(request, listado, 30, data, url_vars)
        return render(request, 'agenda/feriado/listado.html', data)
