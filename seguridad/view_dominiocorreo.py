import sys
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from autenticacion.models import CuentaGoogle
from core.custom_models import FormError
from core.funciones import addData, log, secure_module, solo_administrador
from core.funciones_adicionales import salva_logs
from .forms import DominioCorreoPermitidoForm
from .models import Configuracion, DominioCorreoPermitido


@login_required
@secure_module
@solo_administrador
def dominiocorreoView(request):
    data = {
        'titulo': 'Dominios de correo',
        'descripcion': 'Correos de Google con los que se puede iniciar sesión y cuentas ya vinculadas.',
        'modulo': 'Seguridad',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)
    model = DominioCorreoPermitido
    Formulario = DominioCorreoPermitidoForm
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
                    log(f'Registró el dominio de correo {form.instance}', request, 'add', obj=form.instance.id)
                    messages.success(request, 'Dominio registrado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'change':
                    filtro = model.objects.get(pk=int(request.POST['pk']), status=True)
                    form = Formulario(request.POST, instance=filtro, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    log(f'Editó el dominio de correo {filtro}', request, 'change', obj=filtro.id)
                    messages.success(request, 'Dominio actualizado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'delete':
                    filtro = model.objects.get(pk=int(request.POST['id']), status=True)
                    filtro.status = False
                    filtro.save(request)
                    log(f'Eliminó el dominio de correo {filtro}', request, 'del', obj=filtro.id)
                    messages.success(request, 'Dominio eliminado')
                    res_json = {'error': False}
                elif action == 'desvincular':
                    cuenta = CuentaGoogle.objects.select_related('usuario').get(pk=int(request.POST['id']), status=True)
                    cuenta.status = False
                    cuenta.save(request)
                    log(f'Desvinculó la cuenta de Google {cuenta}', request, 'del', obj=cuenta.id)
                    messages.success(request, 'Cuenta de Google desvinculada')
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
        criterio, filtros = request.GET.get('criterio', '').strip(), Q(status=True)
        if criterio:
            filtros &= Q(usuario__username__icontains=criterio) | Q(email__icontains=criterio) | \
                       Q(usuario__first_name__icontains=criterio) | Q(usuario__last_name__icontains=criterio)
            data['criterio'] = criterio
        data['listado'] = model.objects.filter(status=True)
        data['cuentas'] = CuentaGoogle.objects.filter(filtros).select_related('usuario').order_by('-ultimo_acceso')[:200]
        data['login_google_activo'] = Configuracion.get_instancia().conexion_google
        return render(request, 'seguridad/dominiocorreo/listado.html', data)
